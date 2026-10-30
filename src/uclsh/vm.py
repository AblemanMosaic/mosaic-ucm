from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from .artifact import verify_artifact_host
from .canonical import I64_MAX, I64_MIN, MAX_CONTAINER_ITEMS, MAX_DEPTH, MAX_TEXT_BYTES, canonical_bytes, root
from .errors import UCLSHRefusal, require
from .kernel import Kernel


@dataclass
class _Frame:
    control: list[tuple[Any, ...]] = field(default_factory=list)
    values: list[Any] = field(default_factory=list)
    expected_returns: list[tuple[str, str]] = field(default_factory=list)


class Machine:
    """Deterministic UCL VM using explicit language-level stacks."""

    _PARSER_CURSOR_FUNCTIONS = frozenset(
        {
            "json_parse_array",
            "json_parse_digits",
            "json_parse_escape",
            "json_parse_hex4",
            "json_parse_literal",
            "json_parse_number",
            "json_parse_object",
            "json_parse_string",
            "json_parse_value",
        }
    )

    def __init__(self, artifact: dict[str, Any], kernel: Kernel | None = None) -> None:
        try:
            self.kernel = kernel or Kernel()
            verify_artifact_host(artifact, self.kernel.descriptor["root"], self.kernel.primitive_names)
            self.artifact = deepcopy(artifact)
            self.module = self.artifact["body"]["module"]
            # verify_artifact_host already performs the complete module check.
            self.functions = {item["id"]: item for item in self.module["functions"]}
            self.constants = {item["id"]: deepcopy(item["value"]) for item in self.module["constants"]}
            for value in self.constants.values():
                self._check_runtime_value(value)
            self.steps = 0
            self.depth = 0
        except RecursionError as exc:
            raise UCLSHRefusal("HOST_RECURSION_LIMIT_TYPED", "$.machine.init") from exc

    def call(self, function_id: str, args: list[Any]) -> Any:
        initial_depth = self.depth
        frames: list[_Frame] = []
        # A call has its own deterministic resource budget. Reusing a Machine
        # must not make an otherwise-valid call depend on earlier calls.
        self.steps = 0
        # value, canonical byte size, raw UTF-8 text bytes (text only), and
        # maximum descendant depth relative to this value.
        size_cache: dict[int, tuple[Any, int, int | None, int]] = {}
        try:
            require(function_id in self.functions, "FUNCTION_UNKNOWN", "$.call", function_id)
            first_function = self.functions[function_id]
            require(len(args) == len(first_function["params"]), "FUNCTION_ARITY", "$.call", function_id)
            for index, (param, value) in enumerate(zip(first_function["params"], args, strict=True)):
                self._check_declared_value(param["type"], value, size_cache, f"$.call.args[{index}]")
            first = _Frame()
            self._enter(first, function_id, args, size_cache)
            frames.append(first)
            while frames:
                frame = frames[-1]
                signal = self._advance(frame, size_cache, public_frame=len(frames) == 1)
                kind = signal[0]
                if kind == "CALL":
                    _, callee_id, callee_args, tail = signal
                    if tail:
                        self._enter(frame, callee_id, callee_args, size_cache)
                    else:
                        child = _Frame()
                        self._enter(child, callee_id, callee_args, size_cache)
                        frames.append(child)
                    continue
                require(kind == "DONE", "VM_SIGNAL_INVALID")
                result = signal[1]
                for expected_id, expected_type in frame.expected_returns:
                    require(self._matches(expected_type, result), "FUNCTION_RETURN_TYPE", f"$.call.{expected_id}", expected_type)
                # A frame result crosses a structural context boundary.  An
                # intermediate cache entry may have been measured while the
                # same object was nested under a builder envelope, so remeasure
                # it from depth zero before it becomes a returned value.
                # The self-hosted compiler's parser uses one private cursor
                # envelope, {value,index}, while constructing a public JSON
                # value.  Its payload may be exactly MAX_DEPTH deep, making
                # the private envelope MAX_DEPTH+1.  Admit that one sealed,
                # implementation-only shape between parser helpers; every
                # public function result is still checked at MAX_DEPTH.
                public_return = len(frames) == 1
                # Every declaration in a tail-call chain remains a type
                # obligation, but only the original caller determines the
                # public return envelope.  A callee declared ARTIFACT must
                # prove the envelope is well formed; it cannot widen an outer
                # ANY/MAP contract from MAX_DEPTH to MAX_DEPTH+1.
                if self._declares_artifact_return(frame.expected_returns):
                    self._check_artifact_envelope(result, path="$.call.return")
                outer_return_type = frame.expected_returns[0][1]
                if outer_return_type != "ARTIFACT":
                    result_depth_limit = MAX_DEPTH + 1 if self._is_private_parser_cursor(frame.expected_returns, result, public_return=public_return) else MAX_DEPTH
                    self._check_runtime_value(result, depth_limit=result_depth_limit)
                self.depth -= len(frame.expected_returns)
                frames.pop()
                if not frames:
                    return self._copy_runtime_value(result)
                frames[-1].values.append(result)
            raise AssertionError("unreachable")
        except MemoryError as exc:
            raise UCLSHRefusal("HOST_MEMORY_LIMIT_TYPED", "$.call") from exc
        except RecursionError as exc:
            raise UCLSHRefusal("HOST_RECURSION_LIMIT_TYPED", "$.call") from exc
        finally:
            self.depth = initial_depth

    def _enter(self, frame: _Frame, function_id: str, args: list[Any], size_cache: dict[int, tuple[Any, int, int | None, int]]) -> None:
        require(self.depth + 1 <= self.module["resources"]["max_depth"], "CALL_DEPTH_EXHAUSTED")
        require(function_id in self.functions, "FUNCTION_UNKNOWN", "$.call", function_id)
        function = self.functions[function_id]
        require(len(args) == len(function["params"]), "FUNCTION_ARITY", "$.call", function_id)
        for index, (param, value) in enumerate(zip(function["params"], args, strict=True)):
            require(self._matches(param["type"], value), "FUNCTION_ARGUMENT_TYPE", f"$.call.{function_id}[{index}]", param["type"])
            self._check_declared_value(param["type"], value, size_cache=size_cache, path=f"$.call.{function_id}[{index}]")
        self.depth += 1
        frame.expected_returns.append((function_id, function["returns"]))
        env = {param["id"]: value for param, value in zip(function["params"], args, strict=True)}
        frame.control = [("EVAL", function["body"], env, True)]
        frame.values = []

    def _advance(self, frame: _Frame, size_cache: dict[int, tuple[Any, int, int | None, int]], *, public_frame: bool) -> tuple[Any, ...]:
        while frame.control:
            command = frame.control.pop()
            tag = command[0]
            if tag == "EVAL":
                _, expr, env, tail = command
                self._step()
                op = expr["op"]
                if op == "LIT":
                    self._check_runtime_value(expr["value"], size_cache)
                    frame.values.append(expr["value"])
                elif op == "VAR":
                    require(expr["name"] in env, "VARIABLE_UNBOUND", "$.eval", expr["name"])
                    frame.values.append(env[expr["name"]])
                elif op == "CONST":
                    require(expr["name"] in self.constants, "CONSTANT_UNBOUND", "$.eval", expr["name"])
                    frame.values.append(self.constants[expr["name"]])
                elif op == "LET":
                    frame.control.append(("LET_BIND", expr["name"], expr["body"], env, tail))
                    frame.control.append(("EVAL", expr["value"], env, False))
                elif op == "IF":
                    frame.control.append(("IF_SELECT", expr["then"], expr["else"], env, tail))
                    frame.control.append(("EVAL", expr["condition"], env, False))
                elif op == "LIST":
                    items = expr["items"]
                    frame.control.append(("BUILD_LIST", len(items)))
                    for item in reversed(items):
                        frame.control.append(("EVAL", item, env, False))
                elif op == "MAP":
                    fields = expr["fields"]
                    frame.control.append(("BUILD_MAP", tuple(item["key"] for item in fields)))
                    for item in reversed(fields):
                        frame.control.append(("EVAL", item["value"], env, False))
                elif op == "GET":
                    frame.control.append(("APPLY", "GET", "GET", 2, False))
                    frame.control.append(("EVAL", expr["key"], env, False))
                    frame.control.append(("EVAL", expr["value"], env, False))
                else:
                    require(op in {"CALL", "BUILTIN"}, "EXPRESSION_OP_UNKNOWN")
                    args = expr["args"]
                    frame.control.append(("APPLY", op, expr["name"], len(args), tail))
                    for item in reversed(args):
                        frame.control.append(("EVAL", item, env, False))
                continue
            if tag == "LET_BIND":
                _, name, body, env, tail = command
                value = frame.values.pop()
                frame.control.append(("EVAL", body, {**env, name: value}, tail))
            elif tag == "IF_SELECT":
                _, then_expr, else_expr, env, tail = command
                condition = frame.values.pop()
                require(type(condition) is bool, "IF_CONDITION_NOT_BOOL")
                frame.control.append(("EVAL", then_expr if condition else else_expr, env, tail))
            elif tag == "BUILD_LIST":
                count = command[1]
                values = frame.values[-count:] if count else []
                if count:
                    del frame.values[-count:]
                self._check_runtime_value(values, size_cache, depth_limit=MAX_DEPTH)
                frame.values.append(values)
            elif tag == "BUILD_MAP":
                keys = command[1]
                count = len(keys)
                values = frame.values[-count:] if count else []
                if count:
                    del frame.values[-count:]
                result = dict(zip(keys, values, strict=True))
                if self._is_artifact_envelope(result):
                    self._check_artifact_envelope(result, size_cache=size_cache)
                elif self._is_private_parser_cursor(frame.expected_returns, result, public_return=public_frame):
                    self._check_runtime_value(result, size_cache, depth_limit=MAX_DEPTH + 1)
                else:
                    self._check_runtime_value(result, size_cache, depth_limit=MAX_DEPTH)
                frame.values.append(result)
            else:
                require(tag == "APPLY", "VM_COMMAND_INVALID")
                _, op, name, count, tail = command
                args = frame.values[-count:] if count else []
                if count:
                    del frame.values[-count:]
                if op == "CALL":
                    return ("CALL", name, args, tail)
                result = self._invoke_primitive(name, args, size_cache)
                frame.values.append(result)
        require(len(frame.values) == 1, "VM_VALUE_STACK_INVALID")
        return ("DONE", frame.values.pop())

    @staticmethod
    def _matches(value_type: str, value: Any) -> bool:
        if value_type == "ANY": return True
        if value_type == "NULL": return value is None
        if value_type == "BOOL": return type(value) is bool
        if value_type == "I64": return type(value) is int and type(value) is not bool and -(2**63) <= value <= 2**63 - 1
        if value_type == "TEXT": return type(value) is str
        if value_type == "LIST": return type(value) is list
        if value_type == "MAP": return type(value) is dict
        if value_type == "ROOT": return type(value) is str and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)
        if value_type == "ARTIFACT": return type(value) is dict and set(value) == {"body", "root"}
        return False

    def _is_private_parser_cursor(self, expected_returns: list[tuple[str, str]], result: Any, *, public_return: bool) -> bool:
        return (
            not public_return
            and self.artifact["body"].get("semantic_root") == self.kernel.selfhost_compiler_semantic_root
            and bool(expected_returns)
            and all(function_id in self._PARSER_CURSOR_FUNCTIONS for function_id, _ in expected_returns)
            and type(result) is dict
            and set(result) == {"value", "index"}
            and type(result["index"]) is int
            and type(result["index"]) is not bool
            and result["index"] >= 0
        )

    @staticmethod
    def _is_artifact_envelope(value: Any) -> bool:
        return (
            type(value) is dict
            and set(value) == {"body", "root"}
            and type(value["body"]) is dict
            and type(value["root"]) is str
            and len(value["root"]) == 64
            and all(character in "0123456789abcdef" for character in value["root"])
        )

    @staticmethod
    def _declares_artifact_return(expected_returns: list[tuple[str, str]]) -> bool:
        # Tail calls append the callee declaration to this list.  Every
        # accumulated contract remains in force; in particular an outer
        # ARTIFACT contract cannot be erased by an ANY/MAP callee, and an
        # ARTIFACT callee cannot skip its own envelope check under an outer
        # ANY frame.
        return any(value_type == "ARTIFACT" for _, value_type in expected_returns)

    def _check_artifact_envelope(
        self,
        value: Any,
        size_cache: dict[int, tuple[Any, int, int | None, int]] | None = None,
        path: str = "$.runtime.artifact",
    ) -> None:
        require(self._is_artifact_envelope(value), "ARTIFACT_ENVELOPE_INVALID", path)
        self._check_runtime_value(value["body"], size_cache, f"{path}.body", depth_limit=MAX_DEPTH)
        require(value["root"] == root(value["body"]), "ARTIFACT_ROOT_MISMATCH", path)
        self._check_runtime_value(value, size_cache, path, depth_limit=MAX_DEPTH + 1)

    def _check_declared_value(
        self,
        value_type: str,
        value: Any,
        size_cache: dict[int, tuple[Any, int, int | None, int]] | None = None,
        path: str = "$.runtime.value",
    ) -> None:
        if value_type == "ARTIFACT":
            self._check_artifact_envelope(value, size_cache=size_cache, path=path)
        else:
            self._check_runtime_value(value, size_cache, path, depth_limit=MAX_DEPTH)

    def _step(self) -> None:
        self.steps += 1
        require(self.steps <= self.module["resources"]["max_steps"], "STEP_BUDGET_EXHAUSTED")

    def _check_runtime_value(
        self,
        value: Any,
        size_cache: dict[int, tuple[Any, int, int | None, int]] | None = None,
        path: str = "$.runtime.value",
        depth_limit: int = MAX_DEPTH,
    ) -> int:
        """Apply language and per-module limits at every value-producing boundary."""
        try:
            size, _ = self._measure_runtime_value(value, path, size_cache, 0, depth_limit)
            require(size <= self.module["resources"]["max_value_bytes"], "VALUE_BUDGET_EXHAUSTED", path)
            return size
        except MemoryError as exc:
            raise UCLSHRefusal("HOST_MEMORY_LIMIT_TYPED", path) from exc
        except RecursionError as exc:
            raise UCLSHRefusal("HOST_RECURSION_LIMIT_TYPED", path) from exc

    def _measure_runtime_value(
        self,
        value: Any,
        path: str,
        size_cache: dict[int, tuple[Any, int, int | None, int]] | None,
        depth: int,
        depth_limit: int = MAX_DEPTH,
    ) -> tuple[int, int]:
        # Iterative post-order traversal makes the language limit independent of
        # Python's call stack.  MAX_DEPTH is the single ceiling used by the
        # parser, canonical encoder, literals, arguments, constants and every
        # primitive result.
        results: dict[int, tuple[Any, int, int | None, int]] = {}
        active: set[int] = set()
        stack: list[tuple[str, Any, str, int]] = [("VISIT", value, path, depth)]

        while stack:
            action, current, current_path, current_depth = stack.pop()
            require(current_depth <= depth_limit, "VALUE_DEPTH_EXCEEDED", current_path)
            current_id = id(current)
            if action == "FINISH":
                active.remove(current_id)
                size = 2 + max(0, len(current) - 1)
                descendant_depth = 0
                if type(current) is list:
                    for item in current:
                        cached = results[id(item)]
                        require(cached[0] is item, "VM_RESOURCE_ACCOUNTING_INVALID", current_path)
                        size += cached[1]
                        descendant_depth = max(descendant_depth, cached[3] + 1)
                else:
                    for key, item in current.items():
                        key_cached = results[id(key)]
                        item_cached = results[id(item)]
                        require(key_cached[0] is key and item_cached[0] is item, "VM_RESOURCE_ACCOUNTING_INVALID", current_path)
                        size += key_cached[1] + 1 + item_cached[1]
                        descendant_depth = max(descendant_depth, key_cached[3] + 1, item_cached[3] + 1)
                entry = (current, size, None, descendant_depth)
                results[current_id] = entry
                if size_cache is not None:
                    size_cache[current_id] = entry
                continue

            cached = size_cache.get(current_id) if size_cache is not None else None
            if cached is not None and cached[0] is current:
                require(current_depth + cached[3] <= depth_limit, "VALUE_DEPTH_EXCEEDED", current_path, f"depth={current_depth}+relative={cached[3]} limit={depth_limit}")
                results[current_id] = cached
                continue
            if current is None:
                results[current_id] = (current, 4, None, 0)
                continue
            if type(current) is bool:
                results[current_id] = (current, 4 if current else 5, None, 0)
                continue
            if type(current) is int:
                require(I64_MIN <= current <= I64_MAX, "INTEGER_OUT_OF_RANGE", current_path)
                results[current_id] = (current, len(str(current)), None, 0)
                continue
            if type(current) is str:
                raw_size = 0
                json_size = 2
                for character in current:
                    point = ord(character)
                    require(not 0xD800 <= point <= 0xDFFF, "LONE_SURROGATE", current_path)
                    if character in {'"', "\\"} or character in {"\b", "\f", "\n", "\r", "\t"}:
                        raw_size += 1
                        json_size += 2
                    elif point < 0x20:
                        raw_size += 1
                        json_size += 6
                    elif point < 0x80:
                        raw_size += 1
                        json_size += 1
                    elif point < 0x800:
                        raw_size += 2
                        json_size += 2
                    elif point < 0x10000:
                        raw_size += 3
                        json_size += 3
                    else:
                        raw_size += 4
                        json_size += 4
                require(raw_size <= MAX_TEXT_BYTES, "TEXT_TOO_LARGE", current_path)
                entry = (current, json_size, raw_size, 0)
                results[current_id] = entry
                if size_cache is not None:
                    size_cache[current_id] = entry
                continue
            if type(current) not in {list, dict}:
                raise UCLSHRefusal("VALUE_TYPE_UNSUPPORTED", current_path, type(current).__name__)
            require(current_id not in active, "VALUE_CYCLE_UNSUPPORTED", current_path)
            require(len(current) <= MAX_CONTAINER_ITEMS, "CONTAINER_TOO_LARGE", current_path)
            active.add(current_id)
            stack.append(("FINISH", current, current_path, current_depth))
            children: list[tuple[Any, str]] = []
            if type(current) is list:
                children = [(item, f"{current_path}[{index}]") for index, item in enumerate(current)]
            else:
                for key, item in current.items():
                    require(type(key) is str and bool(key), "MAP_KEY_INVALID", current_path)
                    children.extend(((key, f"{current_path}.<key>"), (item, f"{current_path}.{key}")))
            for child, child_path in reversed(children):
                stack.append(("VISIT", child, child_path, current_depth + 1))

        entry = results[id(value)]
        require(entry[0] is value, "VM_RESOURCE_ACCOUNTING_INVALID", path)
        return entry[1], entry[3]

    @staticmethod
    def _copy_runtime_value(value: Any) -> Any:
        """Copy a validated runtime value without using the host call stack."""
        if type(value) not in {list, dict}:
            return value
        result: Any = [] if type(value) is list else {}
        stack: list[tuple[Any, Any]] = [(value, result)]
        while stack:
            source, target = stack.pop()
            if type(source) is list:
                for item in source:
                    if type(item) is list:
                        child: Any = []
                        target.append(child)
                        stack.append((item, child))
                    elif type(item) is dict:
                        child = {}
                        target.append(child)
                        stack.append((item, child))
                    else:
                        target.append(item)
            else:
                for key, item in source.items():
                    if type(item) is list:
                        child = []
                        target[key] = child
                        stack.append((item, child))
                    elif type(item) is dict:
                        child = {}
                        target[key] = child
                        stack.append((item, child))
                    else:
                        target[key] = item
        return result

    def _invoke_primitive(
        self,
        name: str,
        args: list[Any],
        size_cache: dict[int, tuple[Any, int, int | None, int]],
    ) -> Any:
        """Preflight growing primitives, then validate and account for every result."""
        path = f"$.primitive.{name}"
        known_size: int | None = None
        known_raw_text: int | None = None

        if name == "TEXT_CONCAT" and len(args) == 2 and all(type(item) is str for item in args):
            parts: list[tuple[int, int]] = []
            for item in args:
                cached = size_cache.get(id(item))
                if cached is not None and cached[0] is item and cached[2] is not None:
                    parts.append((cached[1], cached[2]))
                else:
                    encoded = item.encode("utf-8", errors="strict")
                    parts.append((len(canonical_bytes(item)), len(encoded)))
            known_size = parts[0][0] + parts[1][0] - 2
            known_raw_text = parts[0][1] + parts[1][1]
            require(known_raw_text <= MAX_TEXT_BYTES, "TEXT_TOO_LARGE", path)
            require(known_size <= self.module["resources"]["max_value_bytes"], "VALUE_BUDGET_EXHAUSTED", path)
        elif name == "LIST_APPEND" and len(args) == 2 and type(args[0]) is list:
            base_size = self._check_runtime_value(args[0], size_cache, f"{path}[0]")
            item_size = self._check_runtime_value(args[1], size_cache, f"{path}[1]")
            require(len(args[0]) + 1 <= MAX_CONTAINER_ITEMS, "CONTAINER_TOO_LARGE", path)
            known_size = base_size + item_size + (1 if args[0] else 0)
            require(known_size <= self.module["resources"]["max_value_bytes"], "VALUE_BUDGET_EXHAUSTED", path)
        elif name == "MAP_PUT" and len(args) == 3 and type(args[0]) is dict and type(args[1]) is str and bool(args[1]):
            base, key, item = args
            base_size = self._check_runtime_value(base, size_cache, f"{path}[0]")
            key_size = len(canonical_bytes(key))
            item_size = self._check_runtime_value(item, size_cache, f"{path}[2]")
            new_entry_size = key_size + 1 + item_size
            if key in base:
                old_entry_size = key_size + 1 + self._check_runtime_value(base[key], size_cache, f"{path}.old")
                known_size = base_size - old_entry_size + new_entry_size
            else:
                require(len(base) + 1 <= MAX_CONTAINER_ITEMS, "CONTAINER_TOO_LARGE", path)
                known_size = base_size + new_entry_size + (1 if base else 0)
            require(known_size <= self.module["resources"]["max_value_bytes"], "VALUE_BUDGET_EXHAUSTED", path)
        elif name == "CANONICAL_BYTES_HEX" and len(args) == 1:
            input_size = self._check_runtime_value(args[0], size_cache, f"{path}[0]")
            known_raw_text = input_size * 2
            known_size = known_raw_text + 2
            require(known_raw_text <= MAX_TEXT_BYTES, "TEXT_TOO_LARGE", path)
            require(known_size <= self.module["resources"]["max_value_bytes"], "VALUE_BUDGET_EXHAUSTED", path)

        try:
            result = self.kernel.invoke(name, args)
        except MemoryError as exc:
            raise UCLSHRefusal("HOST_MEMORY_LIMIT_TYPED", path) from exc

        if known_size is None:
            self._check_runtime_value(result, size_cache, path)
        else:
            if type(result) is str:
                require(known_raw_text is not None, "VM_RESOURCE_ACCOUNTING_INVALID", path)
            elif type(result) is list:
                require(len(result) <= MAX_CONTAINER_ITEMS, "CONTAINER_TOO_LARGE", path)
            elif type(result) is dict:
                require(len(result) <= MAX_CONTAINER_ITEMS, "CONTAINER_TOO_LARGE", path)
            else:
                require(False, "VM_RESOURCE_ACCOUNTING_INVALID", path)
            # Resource shortcuts never bypass the language depth ceiling.  The
            # result is measured once to derive and enforce its relative depth;
            # its preflighted byte size remains authoritative.
            _, result_depth = self._measure_runtime_value(result, path, size_cache, 0)
            require(result_depth <= MAX_DEPTH, "VALUE_DEPTH_EXCEEDED", path)
            size_cache[id(result)] = (result, known_size, known_raw_text, result_depth)

        if name in {"TEXT_CONCAT", "LIST_APPEND", "MAP_PUT"}:
            for item in args:
                cached = size_cache.get(id(item))
                if cached is not None and cached[0] is item and item is not result:
                    size_cache.pop(id(item), None)
        return result

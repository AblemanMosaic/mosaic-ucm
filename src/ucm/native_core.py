"""Closed UCM Native Core profile and Python correspondence reference.

The profile is deliberately integer-only and effect-free.  Python authors and
verifies the canonical instruction projection; ``native/ucm_native_core.c`` is
the independent C17 execution realization.  Neither realization grants an
effect or widens the full UCL-SH language.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
from typing import Any

from uclop.canonical import exact_keys, require, root


PROGRAM_SCHEMA = "mosaic.ucm.native-core-program.v0.1"
PROFILE_SCHEMA = "mosaic.ucm.native-core-profile.v0.1"
PROJECTION_MAGIC = "UCM-NATIVE-CORE\t1\tI64"
MAX_INSTRUCTIONS = 4096
MAX_REGISTERS = 256
MAX_STACK = 1024
MAX_STEPS = 1_000_000
I64_MIN = -(2**63)
I64_MAX = 2**63 - 1
OPS = {
    "PUSH": 1, "LOAD": 1, "STORE": 1,
    "ADD": 0, "SUB": 0, "MUL": 0, "DIV": 0, "MOD": 0,
    "EQ": 0, "LT": 0, "AND": 0, "OR": 0, "NOT": 0,
    "DUP": 0, "DROP": 0, "JZ": 1, "JMP": 1, "HALT": 0,
}
BOUNDARY = {
    "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    "real_a5": False, "g0": "CLOSED",
}


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def native_core_profile() -> dict[str, Any]:
    body = {
        "schema": PROFILE_SCHEMA,
        "profile_id": "UCM_NATIVE_CORE_I64_V0_1",
        "language_standard": "C17",
        "value_model": "SIGNED_I64_AND_CANONICAL_BOOLEAN_0_OR_1",
        "instructions": sorted(OPS),
        "limits": {
            "max_instructions": MAX_INSTRUCTIONS,
            "max_registers": MAX_REGISTERS,
            "max_stack": MAX_STACK,
            "max_steps": MAX_STEPS,
        },
        "effects": [],
        "python_role": "AUTHORING_REFERENCE_AND_CORRESPONDENCE_ORACLE",
        "native_role": "EXECUTION_AUTHORITY_FOR_THIS_CLOSED_PROFILE_ONLY",
        "full_ucl_sh_claimed": False,
        **BOUNDARY,
    }
    return {**body, "profile_root": root(body)}


def _i64(value: Any, code: str) -> int:
    require(type(value) is int and type(value) is not bool and I64_MIN <= value <= I64_MAX, code)
    return value


def validate_native_program(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "program_id", "profile_root", "registers", "max_steps",
        "instructions", "expected_result_i64", "standing", "authority_effect",
        "real_a5", "g0", "program_root",
    })
    require(item["schema"] == PROGRAM_SCHEMA, "NATIVE_PROGRAM_SCHEMA_INVALID")
    require(type(item["program_id"]) is str and re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_.:-]{0,127}", item["program_id"]),
        "NATIVE_PROGRAM_ID_INVALID")
    require(item["profile_root"] == native_core_profile()["profile_root"],
            "NATIVE_PROGRAM_PROFILE_MISMATCH")
    require(type(item["registers"]) is list and len(item["registers"]) <= MAX_REGISTERS,
            "NATIVE_REGISTER_SET_INVALID")
    registers = [_i64(v, "NATIVE_REGISTER_VALUE_INVALID") for v in item["registers"]]
    require(type(item["max_steps"]) is int and type(item["max_steps"]) is not bool
            and 1 <= item["max_steps"] <= MAX_STEPS, "NATIVE_STEP_BOUND_INVALID")
    require(type(item["instructions"]) is list
            and 1 <= len(item["instructions"]) <= MAX_INSTRUCTIONS,
            "NATIVE_INSTRUCTION_SET_INVALID")
    instructions: list[dict[str, Any]] = []
    for index, raw in enumerate(item["instructions"]):
        require(type(raw) is dict and type(raw.get("op")) is str, "NATIVE_INSTRUCTION_INVALID")
        op = raw["op"]
        require(op in OPS, "NATIVE_OPCODE_UNKNOWN", detail=op)
        expected = {"op"} | ({"arg"} if OPS[op] else set())
        require(set(raw) == expected, "NATIVE_INSTRUCTION_SHAPE_INVALID", detail=f"{index}:{op}")
        row = {"op": op}
        if OPS[op]:
            arg = _i64(raw["arg"], "NATIVE_INSTRUCTION_ARGUMENT_INVALID")
            if op in {"LOAD", "STORE"}:
                require(0 <= arg < len(registers), "NATIVE_REGISTER_INDEX_INVALID")
            elif op in {"JZ", "JMP"}:
                require(0 <= arg < len(item["instructions"]), "NATIVE_JUMP_TARGET_INVALID")
            row["arg"] = arg
        instructions.append(row)
    require(instructions[-1]["op"] == "HALT", "NATIVE_TERMINAL_HALT_REQUIRED")
    _i64(item["expected_result_i64"], "NATIVE_EXPECTED_RESULT_INVALID")
    for key, expected in BOUNDARY.items():
        require(item[key] == expected, "NATIVE_PROGRAM_BOUNDARY_INVALID")
    body = {key: deepcopy(val) for key, val in item.items() if key != "program_root"}
    require(item["program_root"] == root(body), "NATIVE_PROGRAM_ROOT_MISMATCH")
    body["registers"] = registers
    body["instructions"] = instructions
    return {**body, "program_root": item["program_root"]}


def build_native_program(*, program_id: str, registers: list[int], max_steps: int,
                         instructions: list[dict[str, Any]],
                         expected_result_i64: int) -> dict[str, Any]:
    body = {
        "schema": PROGRAM_SCHEMA, "program_id": program_id,
        "profile_root": native_core_profile()["profile_root"],
        "registers": deepcopy(registers), "max_steps": max_steps,
        "instructions": deepcopy(instructions),
        "expected_result_i64": expected_result_i64, **BOUNDARY,
    }
    return validate_native_program({**body, "program_root": root(body)})


def lower_native_program(value: Any) -> bytes:
    program = validate_native_program(value)
    instruction_lines = [
        row["op"] + (("\t" + str(row["arg"])) if "arg" in row else "")
        for row in program["instructions"]
    ]
    code = ("\n".join(instruction_lines) + "\n").encode("ascii")
    header = [
        PROJECTION_MAGIC,
        "PROGRAM\t" + program["program_id"],
        "REGISTERS\t" + str(len(program["registers"]))
            + "".join("\t" + str(value) for value in program["registers"]),
        "MAX_STEPS\t" + str(program["max_steps"]),
        "INSTRUCTIONS\t" + str(len(program["instructions"])),
        "CODE_SHA256\t" + _sha(code),
        "BEGIN",
    ]
    body = ("\n".join(header) + "\n").encode("ascii") + code
    return body + f"END\t{len(program['instructions'])}\t{_sha(body)}\n".encode("ascii")


def _checked(value: int, code: str) -> int:
    require(I64_MIN <= value <= I64_MAX, code)
    return value


def execute_native_reference(value: Any) -> dict[str, Any]:
    program = validate_native_program(value)
    projection = lower_native_program(program)
    registers = list(program["registers"])
    stack: list[int] = []
    pc = 0
    steps = 0

    def pop(code: str) -> int:
        require(bool(stack), code)
        return stack.pop()

    while True:
        require(0 <= pc < len(program["instructions"]), "NATIVE_PC_INVALID")
        steps += 1
        require(steps <= program["max_steps"], "NATIVE_STEP_BOUND_EXHAUSTED")
        row = program["instructions"][pc]
        op = row["op"]
        pc += 1
        if op == "PUSH": stack.append(row["arg"])
        elif op == "LOAD": stack.append(registers[row["arg"]])
        elif op == "STORE": registers[row["arg"]] = pop("NATIVE_STACK_UNDERFLOW")
        elif op == "DUP":
            require(bool(stack), "NATIVE_STACK_UNDERFLOW"); stack.append(stack[-1])
        elif op == "DROP": pop("NATIVE_STACK_UNDERFLOW")
        elif op == "NOT":
            a = pop("NATIVE_STACK_UNDERFLOW"); require(a in {0, 1}, "NATIVE_BOOL_REQUIRED"); stack.append(1 - a)
        elif op in {"ADD", "SUB", "MUL", "DIV", "MOD", "EQ", "LT", "AND", "OR"}:
            right = pop("NATIVE_STACK_UNDERFLOW"); left = pop("NATIVE_STACK_UNDERFLOW")
            if op == "ADD": result = _checked(left + right, "NATIVE_I64_OVERFLOW")
            elif op == "SUB": result = _checked(left - right, "NATIVE_I64_OVERFLOW")
            elif op == "MUL": result = _checked(left * right, "NATIVE_I64_OVERFLOW")
            elif op in {"DIV", "MOD"}:
                require(right != 0, "NATIVE_DIVISION_BY_ZERO")
                require(not (left == I64_MIN and right == -1), "NATIVE_I64_OVERFLOW")
                quotient = abs(left) // abs(right) * (-1 if (left < 0) != (right < 0) else 1)
                result = quotient if op == "DIV" else left - quotient * right
            elif op == "EQ": result = int(left == right)
            elif op == "LT": result = int(left < right)
            else:
                require(left in {0, 1} and right in {0, 1}, "NATIVE_BOOL_REQUIRED")
                result = (left & right) if op == "AND" else (left | right)
            stack.append(result)
        elif op == "JZ":
            condition = pop("NATIVE_STACK_UNDERFLOW")
            require(condition in {0, 1}, "NATIVE_BOOL_REQUIRED")
            if condition == 0: pc = row["arg"]
        elif op == "JMP": pc = row["arg"]
        else:
            require(op == "HALT", "NATIVE_OPCODE_UNKNOWN")
            require(len(stack) == 1, "NATIVE_TERMINAL_STACK_INVALID")
            result = stack[0]
            require(result == program["expected_result_i64"], "NATIVE_EXPECTED_RESULT_MISMATCH")
            return {
                "program_sha256": _sha(projection), "result_i64": result,
                "status": "PASS", "steps": steps,
            }
        require(len(stack) <= MAX_STACK, "NATIVE_STACK_BOUND_EXHAUSTED")


def detect_c17_compiler() -> dict[str, Any]:
    for name in ("clang", "gcc", "cc"):
        path = shutil.which(name)
        if path:
            version = subprocess.run([path, "--version"], capture_output=True,
                                     text=True, timeout=10)
            first = (version.stdout or version.stderr).splitlines()[0]
            return {"available": True, "name": name, "path": path,
                    "version": first}
    return {"available": False, "name": None, "path": None, "version": None}


def compile_native_core(*, source: pathlib.Path, output: pathlib.Path,
                        compiler: dict[str, Any] | None = None) -> dict[str, Any]:
    selected = compiler or detect_c17_compiler()
    require(selected.get("available") is True, "NATIVE_C17_COMPILER_UNAVAILABLE")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [selected["path"], "-std=c17", "-O2", "-Wall", "-Wextra",
               "-Wpedantic", "-Werror", str(source), "-o", str(output)]
    run = subprocess.run(command, capture_output=True, text=True, timeout=60)
    require(run.returncode == 0, "NATIVE_C17_BUILD_REFUSED", detail=run.stderr[-4000:])
    return {"compiler": selected, "command": command,
            "source_sha256": _sha(source.read_bytes()),
            "binary_sha256": _sha(output.read_bytes())}


def execute_native_binary(*, binary: pathlib.Path, projection: pathlib.Path) -> dict[str, Any]:
    expected_projection_sha256 = _sha(projection.read_bytes())
    run = subprocess.run([str(binary), str(projection), expected_projection_sha256], capture_output=True,
                         text=True, timeout=30)
    require(run.returncode == 0, "NATIVE_EXECUTION_REFUSED", detail=run.stderr[-4000:])
    result = json.loads(run.stdout)
    require(type(result) is dict and set(result) == {
        "program_sha256", "result_i64", "status", "steps"},
        "NATIVE_RESULT_SHAPE_INVALID")
    require(result["status"] == "PASS", "NATIVE_RESULT_STATUS_INVALID")
    return result


def verify_native_correspondence(*, programs: list[dict[str, Any]], binary: pathlib.Path,
                                 work_dir: pathlib.Path) -> dict[str, Any]:
    require(type(programs) is list and bool(programs), "NATIVE_CORPUS_EMPTY")
    work_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for raw in programs:
        program = validate_native_program(raw)
        projection = lower_native_program(program)
        target = work_dir / (program["program_id"] + ".ucln")
        target.write_bytes(projection)
        reference = execute_native_reference(program)
        native = execute_native_binary(binary=binary, projection=target)
        require(native == reference, "NATIVE_CORRESPONDENCE_DIVERGENCE",
                detail=program["program_id"])
        rows.append({
            "program_id": program["program_id"],
            "program_root": program["program_root"],
            "projection_sha256": _sha(projection),
            "result": reference,
        })
    body = {
        "schema": "mosaic.ucm.native-core-correspondence.v0.1",
        "profile_root": native_core_profile()["profile_root"],
        "binary_sha256": _sha(binary.read_bytes()),
        "programs": rows, "program_count": len(rows),
        "all_correspond": True, **BOUNDARY,
    }
    return {**body, "correspondence_root": root(body)}

from __future__ import annotations

import re
from typing import Any

from .canonical import root, validate_value
from .errors import refuse, require


MODULE_FIELDS = {
    "schema",
    "module_id",
    "language_version",
    "profile",
    "imports",
    "effects",
    "resources",
    "constants",
    "functions",
    "entrypoint",
    "compiler_contract",
    "holds",
}
HOLD_FIELDS = {
    "real_a5",
    "g0",
    "standing",
    "admission",
    "release",
    "publication",
    "production",
    "host_mutation",
}
VALUE_TYPES = {"ANY", "NULL", "BOOL", "I64", "TEXT", "LIST", "MAP", "ROOT", "ARTIFACT"}
EXPR_OPS = {"LIT", "VAR", "CONST", "LET", "IF", "LIST", "MAP", "GET", "CALL", "BUILTIN"}
ID_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]{0,127}$")
PRIMITIVE_TYPE_CONTRACTS = {
    "ASSERT_TRUE": (["BOOL", "TEXT", "ANY"], "ANY"), "BOOL_AND": (["BOOL", "BOOL"], "BOOL"), "BOOL_NOT": (["BOOL"], "BOOL"),
    "CANONICAL_BYTES_HEX": (["ANY"], "TEXT"), "CODEPOINT": (["TEXT"], "I64"), "EQUAL": (["ANY", "ANY"], "BOOL"),
    "FROM_CODEPOINT": (["I64"], "TEXT"), "GET": (["ANY", "ANY"], "ANY"), "HASH_TEXT": (["TEXT"], "ROOT"), "HASH_VALUE": (["ANY"], "ROOT"),
    "HMAC_SIGN_DOMAIN": (["TEXT", "ANY", "TEXT"], "MAP"), "HMAC_VERIFY_DOMAIN": (["TEXT", "ANY", "TEXT", "MAP"], "BOOL"),
    "IDENTIFIER_VALID": (["TEXT"], "BOOL"), "I64_ADD": (["I64", "I64"], "I64"), "I64_DIV": (["I64", "I64"], "I64"),
    "I64_LESS": (["I64", "I64"], "BOOL"), "I64_MOD": (["I64", "I64"], "I64"), "I64_MUL": (["I64", "I64"], "I64"),
    "I64_SUB": (["I64", "I64"], "I64"), "LIST_APPEND": (["LIST", "ANY"], "LIST"), "LIST_LENGTH": (["ANY"], "I64"),
    "MAP_HAS": (["MAP", "TEXT"], "BOOL"), "MAP_KEYS_SORTED": (["MAP"], "LIST"), "MAP_PUT": (["MAP", "TEXT", "ANY"], "MAP"),
    "TEXT_AT": (["TEXT", "I64"], "TEXT"), "TEXT_CONCAT": (["TEXT", "TEXT"], "TEXT"), "TEXT_LENGTH": (["TEXT"], "I64"),
    "TEXT_SLICE": (["TEXT", "I64", "I64"], "TEXT"), "TYPE_IS": (["ANY", "TEXT"], "BOOL"),
}
EXPECTED_COMPILER_PASS_GRAPH = [
    {"id": "P01", "kind": "PARSE", "predecessor": None, "callable": "parse_source", "input_slots": ["source_text"], "output_slot": "parsed", "requires": []},
    {"id": "P02", "kind": "SCHEMA_VALIDATE", "predecessor": "P01", "callable": "validate_schema", "input_slots": ["parsed"], "output_slot": "schema_checked", "requires": ["parsed"]},
    {"id": "P03", "kind": "TYPE_EFFECT_CHECK", "predecessor": "P02", "callable": "check_type_effect", "input_slots": ["schema_checked"], "output_slot": "typed", "requires": ["schema_checked"]},
    {"id": "P04", "kind": "PACKAGE", "predecessor": "P03", "callable": "package_module", "input_slots": ["source_text", "typed"], "output_slot": "compiled_artifact", "requires": ["typed"]},
    {"id": "P05", "kind": "VERIFY", "predecessor": "P04", "callable": "verify_artifact", "input_slots": ["compiled_artifact"], "output_slot": "verification", "requires": ["compiled_artifact"]},
]
EXPECTED_GRAMMAR = {
    "id": "STRICT_JSON_UCL_SH_V1", "encoding": "UTF8_NO_BOM", "objects": "UNIQUE_TEXT_KEYS",
    "numbers": "SIGNED_I64_ONLY", "floats": "REFUSED", "non_finite": "REFUSED", "surrogates": "REFUSED",
    "normalization": "EXACT_CODEPOINT_SEQUENCE", "max_nesting": 123,
}
REQUIRED_EFFECT_HOLDS = ["A5", "ADMIT", "HOST", "NETWORK", "PUBLISH", "RELEASE", "STANDING"]


def _exact(value: dict[str, Any], allowed: set[str], required: set[str], path: str) -> None:
    missing = sorted(required - set(value))
    extra = sorted(set(value) - allowed)
    require(not missing, "REQUIRED_FIELD_MISSING", path, ",".join(missing))
    require(not extra, "UNKNOWN_FIELD", path, ",".join(extra))


def _identifier(value: Any, path: str) -> str:
    require(type(value) is str and ID_PATTERN.fullmatch(value) is not None, "IDENTIFIER_INVALID", path)
    return value


def _text_list(value: Any, path: str, *, allow_empty: bool = True) -> list[str]:
    require(type(value) is list and (allow_empty or bool(value)), "TEXT_LIST_INVALID", path)
    for index, item in enumerate(value):
        require(type(item) is str and bool(item), "TEXT_REQUIRED", f"{path}[{index}]")
    require(len(value) == len(set(value)), "DUPLICATE_LIST_ITEM", path)
    return value


def _literal_type(value: Any) -> str:
    if value is None:
        return "NULL"
    if type(value) is bool:
        return "BOOL"
    if type(value) is int:
        return "I64"
    if type(value) is str:
        return "TEXT"
    if type(value) is list:
        return "LIST"
    return "MAP"


def _compatible(expected: str, actual: str) -> bool:
    return expected == "ANY" or actual == "ANY" or expected == actual or ({expected, actual} == {"MAP", "ARTIFACT"})


def infer(expr: dict[str, Any], scope: dict[str, str], path: str, functions: dict[str, Any], constants: dict[str, str]) -> str:
    op = expr["op"]
    if op == "LIT":
        return _literal_type(expr["value"])
    if op == "VAR":
        return scope[expr["name"]]
    if op == "CONST":
        return constants[expr["name"]]
    if op == "LET":
        value_type = infer(expr["value"], scope, f"{path}.value", functions, constants)
        return infer(expr["body"], {**scope, expr["name"]: value_type}, f"{path}.body", functions, constants)
    if op == "IF":
        condition = infer(expr["condition"], scope, f"{path}.condition", functions, constants)
        require(_compatible("BOOL", condition), "IF_CONDITION_TYPE_STATIC", f"{path}.condition", condition)
        then_type = infer(expr["then"], scope, f"{path}.then", functions, constants)
        else_type = infer(expr["else"], scope, f"{path}.else", functions, constants)
        require(_compatible(then_type, else_type), "IF_BRANCH_TYPE_STATIC", path, f"{then_type}!={else_type}")
        return else_type if then_type == "ANY" else then_type
    if op == "LIST":
        for index, item in enumerate(expr["items"]):
            infer(item, scope, f"{path}.items[{index}]", functions, constants)
        return "LIST"
    if op == "MAP":
        for index, field in enumerate(expr["fields"]):
            infer(field["value"], scope, f"{path}.fields[{index}].value", functions, constants)
        return "ARTIFACT" if {field["key"] for field in expr["fields"]} == {"body", "root"} else "MAP"
    if op == "GET":
        container = infer(expr["value"], scope, f"{path}.value", functions, constants)
        key = infer(expr["key"], scope, f"{path}.key", functions, constants)
        require(container in {"ANY", "MAP", "LIST"}, "GET_CONTAINER_TYPE_STATIC", path, container)
        require(key in {"ANY", "TEXT", "I64"}, "GET_KEY_TYPE_STATIC", path, key)
        return "ANY"
    if op == "CALL":
        expected = [item["type"] for item in functions[expr["name"]]["params"]]
        returns = functions[expr["name"]]["returns"]
    else:
        expected, returns = PRIMITIVE_TYPE_CONTRACTS[expr["name"]]
    for index, (arg, expected_type) in enumerate(zip(expr["args"], expected, strict=True)):
        actual = infer(arg, scope, f"{path}.args[{index}]", functions, constants)
        require(_compatible(expected_type, actual), "ARGUMENT_TYPE_STATIC", f"{path}.args[{index}]", f"{expected_type}!={actual}")
    return returns


def _expression(expr: Any, path: str, depth: int = 0) -> None:
    require(depth <= 256, "EXPRESSION_DEPTH_EXCEEDED", path)
    require(type(expr) is dict, "EXPRESSION_NOT_OBJECT", path)
    op = expr.get("op")
    require(op in EXPR_OPS, "EXPRESSION_OP_UNKNOWN", f"{path}.op", str(op))
    if op == "LIT":
        _exact(expr, {"op", "value"}, {"op", "value"}, path)
        validate_value(expr["value"], f"{path}.value")
    elif op in {"VAR", "CONST"}:
        _exact(expr, {"op", "name"}, {"op", "name"}, path)
        _identifier(expr["name"], f"{path}.name")
    elif op == "LET":
        _exact(expr, {"op", "name", "value", "body"}, {"op", "name", "value", "body"}, path)
        _identifier(expr["name"], f"{path}.name")
        _expression(expr["value"], f"{path}.value", depth + 1)
        _expression(expr["body"], f"{path}.body", depth + 1)
    elif op == "IF":
        _exact(expr, {"op", "condition", "then", "else"}, {"op", "condition", "then", "else"}, path)
        _expression(expr["condition"], f"{path}.condition", depth + 1)
        _expression(expr["then"], f"{path}.then", depth + 1)
        _expression(expr["else"], f"{path}.else", depth + 1)
    elif op == "LIST":
        _exact(expr, {"op", "items"}, {"op", "items"}, path)
        require(type(expr["items"]) is list, "EXPRESSION_ITEMS_INVALID", f"{path}.items")
        for index, item in enumerate(expr["items"]):
            _expression(item, f"{path}.items[{index}]", depth + 1)
    elif op == "MAP":
        _exact(expr, {"op", "fields"}, {"op", "fields"}, path)
        require(type(expr["fields"]) is list, "EXPRESSION_FIELDS_INVALID", f"{path}.fields")
        keys: list[str] = []
        for index, field in enumerate(expr["fields"]):
            field_path = f"{path}.fields[{index}]"
            require(type(field) is dict, "MAP_FIELD_INVALID", field_path)
            _exact(field, {"key", "value"}, {"key", "value"}, field_path)
            require(type(field["key"]) is str and bool(field["key"]), "MAP_KEY_INVALID", f"{field_path}.key")
            keys.append(field["key"])
            _expression(field["value"], f"{field_path}.value", depth + 1)
        require(len(keys) == len(set(keys)), "DUPLICATE_MAP_FIELD", path)
    elif op == "GET":
        _exact(expr, {"op", "value", "key"}, {"op", "value", "key"}, path)
        _expression(expr["value"], f"{path}.value", depth + 1)
        _expression(expr["key"], f"{path}.key", depth + 1)
    else:
        _exact(expr, {"op", "name", "args"}, {"op", "name", "args"}, path)
        _identifier(expr["name"], f"{path}.name")
        require(type(expr["args"]) is list, "CALL_ARGS_INVALID", f"{path}.args")
        for index, arg in enumerate(expr["args"]):
            _expression(arg, f"{path}.args[{index}]", depth + 1)


def validate_module(document: Any) -> dict[str, Any]:
    require(type(document) is dict, "MODULE_NOT_OBJECT")
    _exact(document, MODULE_FIELDS, MODULE_FIELDS, "$")
    require(document["schema"] == "ucl.selfhost.module.v1", "MODULE_SCHEMA_UNSUPPORTED", "$.schema")
    _identifier(document["module_id"], "$.module_id")
    require(type(document["language_version"]) is int and type(document["language_version"]) is not bool and document["language_version"] == 1, "LANGUAGE_VERSION_UNSUPPORTED", "$.language_version")
    require(document["profile"] == "UCL-SH-1", "LANGUAGE_PROFILE_UNSUPPORTED", "$.profile")
    _text_list(document["imports"], "$.imports")
    require(not document["imports"], "IMPORTS_NOT_AVAILABLE_IN_BOOTSTRAP", "$.imports")

    effects = document["effects"]
    require(type(effects) is dict, "EFFECTS_NOT_OBJECT", "$.effects")
    _exact(effects, {"ceiling", "allow", "forbid"}, {"ceiling", "allow", "forbid"}, "$.effects")
    require(effects["ceiling"] == "NONE", "EFFECT_CEILING_FORBIDDEN", "$.effects.ceiling")
    require(effects["allow"] == [], "EFFECT_ALLOW_MUST_BE_EMPTY", "$.effects.allow")
    forbidden = _text_list(effects["forbid"], "$.effects.forbid", allow_empty=False)
    require(forbidden == REQUIRED_EFFECT_HOLDS, "HARD_EFFECT_HOLD_SET_INVALID", "$.effects.forbid")

    resources = document["resources"]
    require(type(resources) is dict, "RESOURCES_NOT_OBJECT", "$.resources")
    _exact(resources, {"max_steps", "max_depth", "max_value_bytes"}, {"max_steps", "max_depth", "max_value_bytes"}, "$.resources")
    for name, maximum in (("max_steps", 10_000_000), ("max_depth", 4096), ("max_value_bytes", 64 * 1024 * 1024)):
        value = resources[name]
        require(type(value) is int and type(value) is not bool and 0 < value <= maximum, "RESOURCE_LIMIT_INVALID", f"$.resources.{name}")

    constants = document["constants"]
    require(type(constants) is list, "CONSTANTS_NOT_LIST", "$.constants")
    constant_ids: list[str] = []
    for index, item in enumerate(constants):
        path = f"$.constants[{index}]"
        require(type(item) is dict, "CONSTANT_INVALID", path)
        _exact(item, {"id", "value"}, {"id", "value"}, path)
        constant_ids.append(_identifier(item["id"], f"{path}.id"))
        validate_value(item["value"], f"{path}.value")
    require(len(constant_ids) == len(set(constant_ids)), "DUPLICATE_CONSTANT", "$.constants")

    functions = document["functions"]
    require(type(functions) is list and bool(functions), "FUNCTIONS_INVALID", "$.functions")
    function_ids: list[str] = []
    for index, function in enumerate(functions):
        path = f"$.functions[{index}]"
        require(type(function) is dict, "FUNCTION_INVALID", path)
        _exact(function, {"id", "params", "returns", "effect", "body"}, {"id", "params", "returns", "effect", "body"}, path)
        function_ids.append(_identifier(function["id"], f"{path}.id"))
        require(type(function["params"]) is list, "PARAMS_INVALID", f"{path}.params")
        params: list[str] = []
        for pindex, param in enumerate(function["params"]):
            ppath = f"{path}.params[{pindex}]"
            require(type(param) is dict, "PARAM_INVALID", ppath)
            _exact(param, {"id", "type"}, {"id", "type"}, ppath)
            params.append(_identifier(param["id"], f"{ppath}.id"))
            require(param["type"] in VALUE_TYPES, "VALUE_TYPE_UNKNOWN", f"{ppath}.type")
        require(len(params) == len(set(params)), "DUPLICATE_PARAMETER", f"{path}.params")
        require(function["returns"] in VALUE_TYPES, "VALUE_TYPE_UNKNOWN", f"{path}.returns")
        require(function["effect"] == "NONE", "FUNCTION_EFFECT_FORBIDDEN", f"{path}.effect")
        _expression(function["body"], f"{path}.body")
    require(len(function_ids) == len(set(function_ids)), "DUPLICATE_FUNCTION", "$.functions")
    require(document["entrypoint"] in function_ids, "ENTRYPOINT_UNKNOWN", "$.entrypoint")

    contract = document["compiler_contract"]
    require(type(contract) is dict, "COMPILER_CONTRACT_INVALID", "$.compiler_contract")
    contract_fields = {"accepted_schema", "grammar", "module_schema", "instruction_signatures", "pass_graph", "trusted_primitives", "canonicalization"}
    _exact(contract, contract_fields, contract_fields, "$.compiler_contract")
    require(contract["accepted_schema"] == "ucl.selfhost.module.v1", "ACCEPTED_SCHEMA_INVALID", "$.compiler_contract.accepted_schema")
    require(contract["grammar"] == EXPECTED_GRAMMAR, "GRAMMAR_INVALID", "$.compiler_contract.grammar")
    require(type(contract["module_schema"]) is dict and contract["module_schema"].get("exact_fields") == sorted(MODULE_FIELDS), "MODULE_SCHEMA_CONTRACT_INVALID", "$.compiler_contract.module_schema")
    require(type(contract["instruction_signatures"]) is list and bool(contract["instruction_signatures"]), "SIGNATURES_INVALID", "$.compiler_contract.instruction_signatures")
    require(contract["pass_graph"] == EXPECTED_COMPILER_PASS_GRAPH, "PASS_GRAPH_PIN_MISMATCH", "$.compiler_contract.pass_graph")
    _text_list(contract["trusted_primitives"], "$.compiler_contract.trusted_primitives", allow_empty=False)
    require(type(contract["canonicalization"]) is dict and contract["canonicalization"].get("profile") == "JCS-I64-EXACT-UTF8-V1", "CANONICALIZATION_CONTRACT_INVALID", "$.compiler_contract.canonicalization")

    holds = document["holds"]
    require(type(holds) is dict, "HOLDS_NOT_OBJECT", "$.holds")
    _exact(holds, HOLD_FIELDS, HOLD_FIELDS, "$.holds")
    require(holds["real_a5"] == "HOLD", "REAL_A5_MUST_REMAIN_HELD", "$.holds.real_a5")
    require(holds["g0"] == "CLOSED", "G0_MUST_REMAIN_CLOSED", "$.holds.g0")
    for field in HOLD_FIELDS - {"real_a5", "g0"}:
        require(holds[field] == "EXCLUDED", "EXCLUDED_BOUNDARY_REQUIRED", f"$.holds.{field}")
    return document


def check_module(document: dict[str, Any], primitive_names: set[str]) -> dict[str, Any]:
    validate_module(document)
    contract = document["compiler_contract"]
    require(contract["trusted_primitives"] == sorted(primitive_names), "TRUSTED_PRIMITIVE_SET_MISMATCH", "$.compiler_contract.trusted_primitives")
    signatures = contract["instruction_signatures"]
    signature_names: list[str] = []
    for index, signature in enumerate(signatures):
        path = f"$.compiler_contract.instruction_signatures[{index}]"
        require(type(signature) is dict, "SIGNATURE_INVALID", path)
        _exact(signature, {"name", "arity", "effect", "deterministic"}, {"name", "arity", "effect", "deterministic"}, path)
        signature_names.append(_identifier(signature["name"], f"{path}.name"))
        require(type(signature["arity"]) is int and type(signature["arity"]) is not bool and 0 <= signature["arity"] <= 8, "SIGNATURE_ARITY_INVALID", f"{path}.arity")
        require(signature["effect"] == "NONE" and signature["deterministic"] is True, "SIGNATURE_EFFECT_INVALID", path)
    require(signature_names == sorted(primitive_names), "SIGNATURE_REGISTRY_MISMATCH", "$.compiler_contract.instruction_signatures")

    passes = contract["pass_graph"]
    functions = {item["id"]: item for item in document["functions"]}
    owns_compiler_passes = document["module_id"] == "ucl.selfhost.compiler"
    if owns_compiler_passes:
        require(passes == EXPECTED_COMPILER_PASS_GRAPH, "PASS_GRAPH_PIN_MISMATCH", "$.compiler_contract.pass_graph")
    require([item.get("id") for item in passes if type(item) is dict] == [f"P{index:02d}" for index in range(1, len(passes) + 1)], "PASS_GRAPH_IDENTITIES_INVALID", "$.compiler_contract.pass_graph")
    allowed_kinds = {"PARSE", "SCHEMA_VALIDATE", "TYPE_EFFECT_CHECK", "PACKAGE", "VERIFY"}
    for index, item in enumerate(passes):
        path = f"$.compiler_contract.pass_graph[{index}]"
        require(type(item) is dict, "PASS_INVALID", path)
        pass_fields = {"id", "kind", "predecessor", "callable", "input_slots", "output_slot", "requires"}
        _exact(item, pass_fields, pass_fields, path)
        require(item["kind"] in allowed_kinds, "PASS_KIND_INVALID", f"{path}.kind")
        require(item["predecessor"] == (None if index == 0 else passes[index - 1]["id"]), "PASS_PREDECESSOR_INVALID", f"{path}.predecessor")
        input_slots = _text_list(item["input_slots"], f"{path}.input_slots", allow_empty=False)
        if owns_compiler_passes:
            require(item["callable"] in functions, "PASS_CALLABLE_INVALID", f"{path}.callable")
            require(len(input_slots) == len(functions[item["callable"]]["params"]), "PASS_CALLABLE_ARITY_INVALID", f"{path}.input_slots")
        _identifier(item["output_slot"], f"{path}.output_slot")
        _text_list(item["requires"], f"{path}.requires")
        require(item["requires"] == ([] if index == 0 else [passes[index - 1]["output_slot"]]), "PASS_REQUIREMENTS_INVALID", f"{path}.requires")
    constants = {item["id"] for item in document["constants"]}
    constant_types = {item["id"]: _literal_type(item["value"]) for item in document["constants"]}

    def walk(expr: dict[str, Any], scope: set[str], path: str) -> None:
        op = expr["op"]
        if op == "VAR":
            require(expr["name"] in scope, "VARIABLE_UNBOUND", path, expr["name"])
        elif op == "CONST":
            require(expr["name"] in constants, "CONSTANT_UNBOUND", path, expr["name"])
        elif op == "LET":
            walk(expr["value"], scope, f"{path}.value")
            walk(expr["body"], scope | {expr["name"]}, f"{path}.body")
        elif op == "IF":
            walk(expr["condition"], scope, f"{path}.condition")
            walk(expr["then"], scope, f"{path}.then")
            walk(expr["else"], scope, f"{path}.else")
        elif op == "LIST":
            for index, item in enumerate(expr["items"]):
                walk(item, scope, f"{path}.items[{index}]")
        elif op == "MAP":
            for index, field in enumerate(expr["fields"]):
                walk(field["value"], scope, f"{path}.fields[{index}].value")
        elif op == "GET":
            walk(expr["value"], scope, f"{path}.value")
            walk(expr["key"], scope, f"{path}.key")
        elif op == "CALL":
            require(expr["name"] in functions, "FUNCTION_UNKNOWN", path, expr["name"])
            require(len(expr["args"]) == len(functions[expr["name"]]["params"]), "FUNCTION_ARITY", path, expr["name"])
            for index, arg in enumerate(expr["args"]):
                walk(arg, scope, f"{path}.args[{index}]")
        elif op == "BUILTIN":
            require(expr["name"] in primitive_names, "PRIMITIVE_UNKNOWN", path, expr["name"])
            signature = next(item for item in signatures if item["name"] == expr["name"])
            require(len(expr["args"]) == signature["arity"], "PRIMITIVE_ARITY_STATIC", path, expr["name"])
            for index, arg in enumerate(expr["args"]):
                walk(arg, scope, f"{path}.args[{index}]")

    for index, function in enumerate(document["functions"]):
        scope = {item["id"] for item in function["params"]}
        walk(function["body"], scope, f"$.functions[{index}].body")
        typed_scope = {item["id"]: item["type"] for item in function["params"]}
        actual = infer(function["body"], typed_scope, f"$.functions[{index}].body", functions, constant_types)
        require(_compatible(function["returns"], actual), "FUNCTION_RETURN_TYPE_STATIC", f"$.functions[{index}].body", f"{function['returns']}!={actual}")

    body = {
        "schema": "ucl.selfhost.static_result.v1",
        "module_id": document["module_id"],
        "semantic_root": root(document),
        "functions": sorted(functions),
        "constants": sorted(constants),
        "effect": "NONE",
        "standing": "INFORMATION_ONLY",
    }
    return {"body": body, "root": root(body)}


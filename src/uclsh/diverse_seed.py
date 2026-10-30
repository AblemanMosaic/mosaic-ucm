from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any

from .errors import UCLSHRefusal, require

EXPECTED_TOP_LEVEL = {"compiler_contract", "constants", "effects", "entrypoint", "functions", "holds", "imports", "language_version", "module_id", "profile", "resources", "schema"}
ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]{0,127}$")
I64_MIN, I64_MAX = -(2**63), 2**63 - 1
META_KERNEL_ROOT = "c98066286cb535a5750674ea505057fff7ad1a53cf29f918fc6b3dfa19ade317"
VALUE_TYPES = {"NULL", "BOOL", "I64", "TEXT", "LIST", "MAP", "ROOT", "ARTIFACT", "ANY"}
RESOURCE_MAXIMA = {"max_steps": 10_000_000, "max_depth": 4096, "max_value_bytes": 64 * 1024 * 1024}
EXPECTED_GRAMMAR = {"id": "STRICT_JSON_UCL_SH_V1", "encoding": "UTF8_NO_BOM", "objects": "UNIQUE_TEXT_KEYS", "numbers": "SIGNED_I64_ONLY", "floats": "REFUSED", "non_finite": "REFUSED", "surrogates": "REFUSED", "normalization": "EXACT_CODEPOINT_SEQUENCE", "max_nesting": 123}
ALLOWED_PASS_KINDS = {"PARSE", "SCHEMA_VALIDATE", "TYPE_EFFECT_CHECK", "PACKAGE", "VERIFY"}
PRIMITIVE_TYPES = {
    "ASSERT_TRUE": (["BOOL", "TEXT", "ANY"], "ANY"), "BOOL_AND": (["BOOL", "BOOL"], "BOOL"), "BOOL_NOT": (["BOOL"], "BOOL"), "CANONICAL_BYTES_HEX": (["ANY"], "TEXT"),
    "CODEPOINT": (["TEXT"], "I64"), "EQUAL": (["ANY", "ANY"], "BOOL"), "FROM_CODEPOINT": (["I64"], "TEXT"), "GET": (["ANY", "ANY"], "ANY"),
    "HASH_TEXT": (["TEXT"], "ROOT"), "HASH_VALUE": (["ANY"], "ROOT"), "HMAC_SIGN_DOMAIN": (["TEXT", "ANY", "TEXT"], "MAP"),
    "HMAC_VERIFY_DOMAIN": (["TEXT", "ANY", "TEXT", "MAP"], "BOOL"), "IDENTIFIER_VALID": (["TEXT"], "BOOL"), "I64_ADD": (["I64", "I64"], "I64"),
    "I64_DIV": (["I64", "I64"], "I64"), "I64_LESS": (["I64", "I64"], "BOOL"), "I64_MOD": (["I64", "I64"], "I64"), "I64_MUL": (["I64", "I64"], "I64"),
    "I64_SUB": (["I64", "I64"], "I64"), "LIST_APPEND": (["LIST", "ANY"], "LIST"), "LIST_LENGTH": (["ANY"], "I64"), "MAP_HAS": (["MAP", "TEXT"], "BOOL"),
    "MAP_KEYS_SORTED": (["MAP"], "LIST"), "MAP_PUT": (["MAP", "TEXT", "ANY"], "MAP"), "TEXT_AT": (["TEXT", "I64"], "TEXT"),
    "TEXT_CONCAT": (["TEXT", "TEXT"], "TEXT"), "TEXT_LENGTH": (["TEXT"], "I64"), "TEXT_SLICE": (["TEXT", "I64", "I64"], "TEXT"), "TYPE_IS": (["ANY", "TEXT"], "BOOL"),
}
EXPECTED_PASS_GRAPH = [
    {"id": "P01", "kind": "PARSE", "predecessor": None, "callable": "parse_source", "input_slots": ["source_text"], "output_slot": "parsed", "requires": []},
    {"id": "P02", "kind": "SCHEMA_VALIDATE", "predecessor": "P01", "callable": "validate_schema", "input_slots": ["parsed"], "output_slot": "schema_checked", "requires": ["parsed"]},
    {"id": "P03", "kind": "TYPE_EFFECT_CHECK", "predecessor": "P02", "callable": "check_type_effect", "input_slots": ["schema_checked"], "output_slot": "typed", "requires": ["schema_checked"]},
    {"id": "P04", "kind": "PACKAGE", "predecessor": "P03", "callable": "package_module", "input_slots": ["source_text", "typed"], "output_slot": "compiled_artifact", "requires": ["typed"]},
    {"id": "P05", "kind": "VERIFY", "predecessor": "P04", "callable": "verify_artifact", "input_slots": ["compiled_artifact"], "output_slot": "verification", "requires": ["compiled_artifact"]},
]

def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        require(key not in out, "DIVERSE_DUPLICATE_JSON_KEY", "$", key)
        out[key] = value
    return out

def _int(raw: str) -> int:
    require(raw.isascii() and all(ch in "-0123456789" for ch in raw), "DIVERSE_INTEGER_TOKEN")
    value = int(raw)
    require(I64_MIN <= value <= I64_MAX, "DIVERSE_INTEGER_RANGE")
    return value

def _reject_number(raw: str) -> None:
    raise UCLSHRefusal("DIVERSE_NON_INTEGER_NUMBER", detail=raw)

def _value(value: Any, depth: int = 0) -> None:
    require(depth <= 123, "DIVERSE_VALUE_DEPTH")
    if value is None or type(value) in {bool, int, str}:
        if type(value) is int: require(I64_MIN <= value <= I64_MAX, "DIVERSE_INTEGER_RANGE")
        if type(value) is str: require(not any(0xD800 <= ord(ch) <= 0xDFFF for ch in value), "DIVERSE_SURROGATE")
        return
    require(type(value) in {list, dict}, "DIVERSE_VALUE_TYPE")
    if type(value) is dict:
        require(all(type(key) is str and bool(key) for key in value), "DIVERSE_MAP_KEY")
    for item in (value if type(value) is list else value.values()): _value(item, depth + 1)

def _loads(raw: str) -> Any:
    require(not raw.startswith("\ufeff"), "DIVERSE_BOM")
    try: value = json.loads(raw, object_pairs_hook=_pairs, parse_int=_int, parse_float=_reject_number, parse_constant=_reject_number)
    except UCLSHRefusal: raise
    except Exception as exc: raise UCLSHRefusal("DIVERSE_PARSE_FAILED", detail=type(exc).__name__) from exc
    _value(value)
    return value

def _bytes(value: Any) -> bytes:
    _value(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

def _root(value: Any) -> str: return hashlib.sha256(_bytes(value)).hexdigest()
def _sha(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()

def _literal_type(value: Any) -> str:
    if value is None: return "NULL"
    if type(value) is bool: return "BOOL"
    if type(value) is int: return "I64"
    if type(value) is str: return "TEXT"
    if type(value) is list: return "LIST"
    return "MAP"

def _compatible(expected: str, actual: str) -> bool:
    return expected == "ANY" or actual == "ANY" or expected == actual or {expected, actual} == {"MAP", "ARTIFACT"}

def _exact(value: Any, fields: set[str], code: str) -> None:
    require(type(value) is dict and set(value) == fields, code)

def _walk(expr: Any, scope: dict[str, str], constants: dict[str, str], functions: dict[str, Any]) -> str:
    require(type(expr) is dict and type(expr.get("op")) is str, "DIVERSE_EXPRESSION")
    op = expr["op"]
    if op == "LIT":
        _exact(expr, {"op", "value"}, "DIVERSE_EXPR_FIELDS")
        return _literal_type(expr["value"])
    if op == "VAR":
        _exact(expr, {"op", "name"}, "DIVERSE_EXPR_FIELDS")
        require(expr.get("name") in scope, "DIVERSE_VARIABLE_UNBOUND")
        return scope[expr["name"]]
    if op == "CONST":
        _exact(expr, {"op", "name"}, "DIVERSE_EXPR_FIELDS")
        require(expr.get("name") in constants, "DIVERSE_CONSTANT_UNBOUND")
        return constants[expr["name"]]
    if op == "LET":
        _exact(expr, {"op", "name", "value", "body"}, "DIVERSE_EXPR_FIELDS")
        require(type(expr["name"]) is str and ID.fullmatch(expr["name"]) is not None, "DIVERSE_IDENTIFIER")
        actual = _walk(expr["value"], scope, constants, functions)
        return _walk(expr["body"], {**scope, expr["name"]: actual}, constants, functions)
    if op == "IF":
        _exact(expr, {"op", "condition", "then", "else"}, "DIVERSE_EXPR_FIELDS")
        require(_compatible("BOOL", _walk(expr["condition"], scope, constants, functions)), "DIVERSE_IF_TYPE")
        left = _walk(expr["then"], scope, constants, functions); right = _walk(expr["else"], scope, constants, functions)
        require(_compatible(left, right), "DIVERSE_BRANCH_TYPE")
        return right if left == "ANY" else left
    if op == "LIST":
        _exact(expr, {"op", "items"}, "DIVERSE_EXPR_FIELDS")
        for item in expr["items"]: _walk(item, scope, constants, functions)
        return "LIST"
    if op == "MAP":
        _exact(expr, {"op", "fields"}, "DIVERSE_EXPR_FIELDS")
        keys: list[str] = []
        for field in expr["fields"]:
            _exact(field, {"key", "value"}, "DIVERSE_MAP_FIELD")
            require(type(field["key"]) is str and bool(field["key"]), "DIVERSE_MAP_KEY")
            keys.append(field["key"]); _walk(field["value"], scope, constants, functions)
        require(len(keys) == len(set(keys)), "DIVERSE_MAP_DUPLICATE")
        return "ARTIFACT" if {field["key"] for field in expr["fields"]} == {"body", "root"} else "MAP"
    if op == "GET":
        _exact(expr, {"op", "value", "key"}, "DIVERSE_EXPR_FIELDS")
        container = _walk(expr["value"], scope, constants, functions); key_type = _walk(expr["key"], scope, constants, functions)
        require(container in {"MAP", "ARTIFACT", "LIST", "ANY"}, "DIVERSE_GET_CONTAINER_TYPE")
        require(key_type in {"TEXT", "I64", "ANY"}, "DIVERSE_GET_KEY_TYPE")
        return "ANY"
    require(op in {"CALL", "BUILTIN"}, "DIVERSE_EXPRESSION_OP")
    _exact(expr, {"op", "name", "args"}, "DIVERSE_EXPR_FIELDS")
    name, args = expr.get("name"), expr.get("args")
    require(type(args) is list, "DIVERSE_ARGS")
    if op == "CALL":
        require(name in functions, "DIVERSE_FUNCTION_UNKNOWN")
        expected = [item["type"] for item in functions[name]["params"]]; returns = functions[name]["returns"]
    else:
        require(name in PRIMITIVE_TYPES, "DIVERSE_PRIMITIVE_UNKNOWN")
        require(len(args) == len(PRIMITIVE_TYPES[name][0]), "DIVERSE_PRIMITIVE_ARITY")
        expected, returns = PRIMITIVE_TYPES[name]
    require(len(args) == len(expected), "DIVERSE_FUNCTION_ARITY")
    for arg, expected_type in zip(args, expected, strict=True):
        require(_compatible(expected_type, _walk(arg, scope, constants, functions)), "DIVERSE_ARGUMENT_TYPE")
    return returns

def _independent_validate(document: Any) -> None:
    require(type(document) is dict and set(document) == EXPECTED_TOP_LEVEL, "DIVERSE_TOP_LEVEL_FIELDS")
    require(document["schema"] == "ucl.selfhost.module.v1" and document["language_version"] == 1 and type(document["language_version"]) is int, "DIVERSE_SCHEMA")
    require(type(document["module_id"]) is str and ID.fullmatch(document["module_id"]) is not None, "DIVERSE_MODULE_ID")
    require(document["profile"] == "UCL-SH-1" and document["imports"] == [], "DIVERSE_PROFILE")
    require(document["effects"] == {"allow": [], "ceiling": "NONE", "forbid": ["A5", "ADMIT", "HOST", "NETWORK", "PUBLISH", "RELEASE", "STANDING"]}, "DIVERSE_EFFECTS")
    require(document["holds"] == {"admission": "EXCLUDED", "g0": "CLOSED", "host_mutation": "EXCLUDED", "production": "EXCLUDED", "publication": "EXCLUDED", "real_a5": "HOLD", "release": "EXCLUDED", "standing": "EXCLUDED"}, "DIVERSE_HOLDS")
    resources = document["resources"]
    _exact(resources, set(RESOURCE_MAXIMA), "DIVERSE_RESOURCES")
    for name, maximum in RESOURCE_MAXIMA.items():
        require(type(resources[name]) is int and type(resources[name]) is not bool and 0 < resources[name] <= maximum, "DIVERSE_RESOURCE_LIMIT")
    contract = document["compiler_contract"]
    _exact(contract, {"accepted_schema", "grammar", "module_schema", "instruction_signatures", "pass_graph", "trusted_primitives", "canonicalization"}, "DIVERSE_COMPILER_CONTRACT")
    require(contract["accepted_schema"] == "ucl.selfhost.module.v1", "DIVERSE_ACCEPTED_SCHEMA")
    require(contract["grammar"] == EXPECTED_GRAMMAR, "DIVERSE_GRAMMAR")
    require(type(contract["module_schema"]) is dict and contract["module_schema"].get("exact_fields") == sorted(EXPECTED_TOP_LEVEL), "DIVERSE_MODULE_SCHEMA")
    require(type(contract["canonicalization"]) is dict and contract["canonicalization"].get("profile") == "JCS-I64-EXACT-UTF8-V1", "DIVERSE_CANONICALIZATION")
    primitive_names = sorted(PRIMITIVE_TYPES)
    require(contract["trusted_primitives"] == primitive_names, "DIVERSE_PRIMITIVES")
    signatures = contract["instruction_signatures"]
    require(type(signatures) is list and len(signatures) == len(primitive_names), "DIVERSE_SIGNATURES")
    for signature, name in zip(signatures, primitive_names, strict=True):
        _exact(signature, {"name", "arity", "effect", "deterministic"}, "DIVERSE_SIGNATURE_FIELDS")
        require(signature == {"name": name, "arity": len(PRIMITIVE_TYPES[name][0]), "effect": "NONE", "deterministic": True}, "DIVERSE_SIGNATURES")
    require(contract["pass_graph"] == EXPECTED_PASS_GRAPH, "DIVERSE_PASS_GRAPH_PIN")
    for index, item in enumerate(contract["pass_graph"]):
        _exact(item, {"id", "kind", "predecessor", "callable", "input_slots", "output_slot", "requires"}, "DIVERSE_PASS_FIELDS")
        require(item["id"] == f"P{index + 1:02d}", "DIVERSE_PASS_IDENTITIES")
        require(item["kind"] in ALLOWED_PASS_KINDS, "DIVERSE_PASS_KIND")
        require(item["predecessor"] == (None if index == 0 else contract["pass_graph"][index - 1]["id"]), "DIVERSE_PASS_PREDECESSOR")
        require(type(item["input_slots"]) is list and bool(item["input_slots"]) and all(type(value) is str and value for value in item["input_slots"]), "DIVERSE_PASS_INPUTS")
        require(item["requires"] == ([] if index == 0 else [contract["pass_graph"][index - 1]["output_slot"]]), "DIVERSE_PASS_REQUIREMENTS")
    require(type(document["constants"]) is list, "DIVERSE_CONSTANTS")
    for item in document["constants"]:
        _exact(item, {"id", "value"}, "DIVERSE_CONSTANT_FIELDS")
        require(type(item["id"]) is str and ID.fullmatch(item["id"]) is not None, "DIVERSE_IDENTIFIER")
    constants = {item["id"]: _literal_type(item["value"]) for item in document["constants"]}
    require(len(constants) == len(document["constants"]), "DIVERSE_DUPLICATE_CONSTANT")
    require(type(document["functions"]) is list and bool(document["functions"]), "DIVERSE_FUNCTION_IDENTITIES")
    functions = {item.get("id"): item for item in document["functions"] if type(item) is dict}
    require(functions and len(functions) == len(document["functions"]), "DIVERSE_FUNCTION_IDENTITIES")
    require(document["entrypoint"] in functions, "DIVERSE_ENTRYPOINT")
    for name, function in functions.items():
        _exact(function, {"id", "params", "returns", "effect", "body"}, "DIVERSE_FUNCTION_FIELDS")
        require(type(name) is str and ID.fullmatch(name) is not None and function["effect"] == "NONE", "DIVERSE_FUNCTION_CONTRACT")
        require(function["returns"] in VALUE_TYPES, "DIVERSE_VALUE_TYPE")
        require(type(function["params"]) is list, "DIVERSE_PARAMS")
        for item in function["params"]:
            _exact(item, {"id", "type"}, "DIVERSE_PARAM_FIELDS")
            require(type(item["id"]) is str and ID.fullmatch(item["id"]) is not None and item["type"] in VALUE_TYPES, "DIVERSE_PARAM_CONTRACT")
        scope = {item["id"]: item["type"] for item in function["params"]}
        require(len(scope) == len(function["params"]), "DIVERSE_PARAMS")
        actual = _walk(function["body"], scope, constants, functions)
        require(_compatible(function["returns"], actual), "DIVERSE_RETURN_TYPE")

def _profile(document: dict[str, Any], kernel_root: str) -> dict[str, Any]:
    contract = document["compiler_contract"]
    return {"schema": "ucl.selfhost.compiler_profile.v1", "language_profile": "UCL-SH-1", "meta_kernel_root": kernel_root, "grammar_root": _root(contract["grammar"]), "module_schema_root": _root(contract["module_schema"]), "instruction_signatures_root": _root(contract["instruction_signatures"]), "pass_graph_root": _root(contract["pass_graph"]), "effect": "NONE"}

def compile_module_text_diverse(raw: bytes | str) -> dict[str, Any]:
    text = raw.decode("utf-8", errors="strict") if type(raw) is bytes else raw
    document = _loads(text)
    _independent_validate(document)
    profile = _profile(document, META_KERNEL_ROOT)
    interface = [{"id": item["id"], "params": item["params"], "returns": item["returns"], "effect": item["effect"]} for item in document["functions"]]
    body = {"schema": "ucl.selfhost.compiled_module.v1", "source_root": _sha(text.encode("utf-8")), "semantic_root": _root(document), "compiler_profile_root": _root(profile), "meta_kernel_root": META_KERNEL_ROOT, "module": deepcopy(document), "interface": interface, "trusted_primitives": sorted(PRIMITIVE_TYPES), "effect": "NONE", "standing": "INFORMATION_ONLY"}
    return {"body": body, "root": _root(body)}

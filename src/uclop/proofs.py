from __future__ import annotations

from itertools import product
from typing import Any

from .canonical import exact_keys, require, root


OPS = {"VAR", "NOT", "AND", "OR", "IMPLIES"}


def _vars(expr: Any, *, maximum_depth: int = 96) -> set[str]:
    result: set[str] = set()
    pending = [(expr, 0)]
    while pending:
        current, depth = pending.pop()
        require(depth <= maximum_depth, "FORMULA_DEPTH_EXCEEDED")
        node = exact_keys(current, {"op", "args"} if type(current) is dict and current.get("op") != "VAR" else {"op", "name"}, "$.formula")
        require(node["op"] in OPS, "FORMULA_OP_UNSUPPORTED")
        if node["op"] == "VAR":
            require(type(node["name"]) is str and node["name"], "FORMULA_VARIABLE_INVALID")
            result.add(node["name"]); continue
        require(type(node["args"]) is list, "FORMULA_ARGS_INVALID")
        require(len(node["args"]) == (1 if node["op"] == "NOT" else 2), "FORMULA_ARITY_INVALID")
        pending.extend((item, depth + 1) for item in node["args"])
    return result


def evaluate(expr: dict[str, Any], assignment: dict[str, bool]) -> bool:
    _vars(expr)
    values: dict[int, bool] = {}
    pending = [(expr, False)]
    while pending:
        node, visited = pending.pop()
        key = id(node); op = node["op"]
        if op == "VAR":
            require(node["name"] in assignment and type(assignment[node["name"]]) is bool, "ASSIGNMENT_MISSING", detail=node["name"])
            values[key] = assignment[node["name"]]; continue
        if not visited:
            pending.append((node, True)); pending.extend((item, False) for item in reversed(node["args"])); continue
        args = [values[id(item)] for item in node["args"]]
        if op == "NOT": values[key] = not args[0]
        elif op == "AND": values[key] = args[0] and args[1]
        elif op == "OR": values[key] = args[0] or args[1]
        elif op == "IMPLIES": values[key] = (not args[0]) or args[1]
    return values[id(expr)]


def prove(formula: dict[str, Any], *, maximum_variables: int = 12) -> dict[str, Any]:
    names = sorted(_vars(formula))
    require(len(names) <= maximum_variables, "PROOF_VARIABLE_BOUND_EXHAUSTED")
    formula_root = root(formula)
    false_rows = []
    for bits in product((False, True), repeat=len(names)):
        assignment = dict(zip(names, bits, strict=True))
        if not evaluate(formula, assignment):
            false_rows.append(assignment)
    body = {
        "schema": "ucl.op.truth_table_proof.v1",
        "rule": "BOUNDED_TRUTH_TABLE",
        "formula_root": formula_root,
        "variables": names,
        "valid": not false_rows,
        "counterexample": false_rows[0] if false_rows else None,
        "rows_checked": 2 ** len(names),
    }
    return {**body, "proof_root": root(body)}


def check(formula: dict[str, Any], proof: dict[str, Any], *, maximum_variables: int = 12) -> dict[str, Any]:
    require(proof.get("schema") == "ucl.op.truth_table_proof.v1" and proof.get("rule") == "BOUNDED_TRUTH_TABLE", "PROOF_RULE_UNSUPPORTED")
    require(proof.get("formula_root") == root(formula), "PROOF_FORMULA_ROOT_MISMATCH")
    expected = prove(formula, maximum_variables=maximum_variables)
    require(proof == expected, "PROOF_CONTENT_INVALID")
    body = {"schema": "ucl.op.proof_check.v1", "formula_root": root(formula), "proof_root": proof["proof_root"], "status": "PASS", "valid": proof["valid"], "authority_effect": "NONE"}
    return {**body, "check_root": root(body)}

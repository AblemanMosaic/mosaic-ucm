"""Native, deterministic, proof-carrying verification for bounded UCM contracts.

The v1 kernel is deliberately small. It accepts linear integer transition
contracts, compiles them to verification conditions, and checks explicit
Fourier-Motzkin contradiction certificates. Search is replaceable; the kernel
and the content bindings decide whether a result is a proof.
"""
from __future__ import annotations

from copy import deepcopy
from math import gcd
import re
from typing import Any

from .canonical import exact_keys, require, require_root, root


CONTRACT_SCHEMA = "ucl.proof.transition_contract.v1"
COMPILED_SCHEMA = "ucl.proof.compiled_vc_set.v1"
CERTIFICATE_SCHEMA = "ucl.proof.linear_integer_certificate.v1"
PROOF_SCHEMA = "ucl.proof.bundle.v1"
CHECK_SCHEMA = "ucl.proof.check.v1"
SOLVER_REQUEST_SCHEMA = "ucl.proof.solver_request.v1"
SOLVER_RESPONSE_SCHEMA = "ucl.proof.solver_response.v1"
MAX_VARIABLES = 64
MAX_BODY = 256
MAX_FORMULA_DEPTH = 64
MAX_TERM_NODES = 2048
MAX_TRACE_ROWS = 20_000
MAX_ARITHMETIC = 2**63 - 1
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}\Z")
_COMPARATORS = {"LE", "LT", "GE", "GT", "EQ"}
THEORY = {
    "schema": "ucl.proof.linear_integer_theory.v1",
    "sorts": ["INT"],
    "terms": ["ADD", "INT", "MUL_CONST", "SUB", "VAR"],
    "formulas": ["AND", "EQ", "GE", "GT", "LE", "LT", "TRUE"],
    "statements": ["ASSERT", "ASSIGN", "LOOP"],
    "strict_integer_inequality_encoding": "UNIT_OFFSET",
    "certificate_rule": "FOURIER_MOTZKIN_INTEGER_SOUND_V1",
    "kernel": "LINEAR_INTEGER_FOURIER_MOTZKIN_CERTIFICATE_CHECKER_V1",
    "limits": {"variables": MAX_VARIABLES, "statements": MAX_BODY,
               "syntax_nodes": MAX_TERM_NODES, "formula_depth": MAX_FORMULA_DEPTH,
               "trace_rows": MAX_TRACE_ROWS},
}
THEORY_ROOT = root(THEORY)


def _syntax_node_count(*values: Any) -> int:
    """Count source-language AST nodes without recursion or host-size inference."""
    count = 0
    pending = list(values)
    while pending:
        current = pending.pop()
        if type(current) is dict:
            if type(current.get("op")) is str:
                count += 1
                require(count <= MAX_TERM_NODES, "PROOF_SYNTAX_NODE_LIMIT_EXCEEDED")
            pending.extend(current.values())
        elif type(current) is list:
            pending.extend(current)
    return count


def _name(value: Any, path: str) -> str:
    require(type(value) is str and _NAME.fullmatch(value) is not None, "PROOF_IDENTIFIER_INVALID", path)
    return value


def _term(value: Any, variables: set[str], path: str = "$.term", depth: int = 0) -> dict[str, Any]:
    require(depth <= MAX_FORMULA_DEPTH, "PROOF_TERM_DEPTH_EXCEEDED", path)
    require(type(value) is dict and type(value.get("op")) is str, "PROOF_TERM_INVALID", path)
    op = value["op"]
    if op == "VAR":
        item = exact_keys(value, {"op", "name"}, path)
        require(type(item["name"]) is str and item["name"] in variables, "PROOF_VARIABLE_UNKNOWN", path, str(item["name"]))
    elif op == "INT":
        item = exact_keys(value, {"op", "value"}, path)
        require(type(item["value"]) is int and -MAX_ARITHMETIC <= item["value"] <= MAX_ARITHMETIC,
                "PROOF_INTEGER_INVALID", path)
    elif op == "ADD":
        item = exact_keys(value, {"op", "args"}, path)
        require(type(item["args"]) is list and 2 <= len(item["args"]) <= 16, "PROOF_TERM_ARITY_INVALID", path)
        for index, arg in enumerate(item["args"]):
            _term(arg, variables, f"{path}.args[{index}]", depth + 1)
    elif op == "SUB":
        item = exact_keys(value, {"op", "args"}, path)
        require(type(item["args"]) is list and len(item["args"]) == 2, "PROOF_TERM_ARITY_INVALID", path)
        for index, arg in enumerate(item["args"]):
            _term(arg, variables, f"{path}.args[{index}]", depth + 1)
    elif op == "MUL_CONST":
        item = exact_keys(value, {"op", "coefficient", "arg"}, path)
        require(type(item["coefficient"]) is int and -MAX_ARITHMETIC <= item["coefficient"] <= MAX_ARITHMETIC,
                "PROOF_COEFFICIENT_INVALID", path)
        _term(item["arg"], variables, f"{path}.arg", depth + 1)
    else:
        require(False, "PROOF_TERM_OP_UNSUPPORTED", path, op)
    return deepcopy(value)


def _formula(value: Any, variables: set[str], path: str = "$.formula", depth: int = 0) -> dict[str, Any]:
    require(depth <= MAX_FORMULA_DEPTH, "PROOF_FORMULA_DEPTH_EXCEEDED", path)
    require(type(value) is dict and type(value.get("op")) is str, "PROOF_FORMULA_INVALID", path)
    op = value["op"]
    if op == "TRUE":
        exact_keys(value, {"op"}, path)
    elif op == "AND":
        item = exact_keys(value, {"op", "args"}, path)
        require(type(item["args"]) is list and 2 <= len(item["args"]) <= 64, "PROOF_FORMULA_ARITY_INVALID", path)
        for index, arg in enumerate(item["args"]):
            _formula(arg, variables, f"{path}.args[{index}]", depth + 1)
    elif op in _COMPARATORS:
        item = exact_keys(value, {"op", "args"}, path)
        require(type(item["args"]) is list and len(item["args"]) == 2, "PROOF_FORMULA_ARITY_INVALID", path)
        for index, arg in enumerate(item["args"]):
            _term(arg, variables, f"{path}.args[{index}]", depth + 1)
    else:
        require(False, "PROOF_FORMULA_OP_UNSUPPORTED", path, op)
    return deepcopy(value)


def _linear(value: dict[str, Any]) -> tuple[dict[str, int], int]:
    op = value["op"]
    if op == "VAR":
        return {value["name"]: 1}, 0
    if op == "INT":
        return {}, value["value"]
    if op == "MUL_CONST":
        coefficients, constant = _linear(value["arg"])
        factor = value["coefficient"]
        return {name: factor * coefficient for name, coefficient in coefficients.items()}, factor * constant
    left, left_constant = _linear(value["args"][0])
    if op == "ADD":
        result, constant = {}, 0
        for arg in value["args"]:
            current, current_constant = _linear(arg)
            constant += current_constant
            for name, coefficient in current.items():
                result[name] = result.get(name, 0) + coefficient
        return {name: coefficient for name, coefficient in result.items() if coefficient}, constant
    right, right_constant = _linear(value["args"][1])
    result = dict(left)
    for name, coefficient in right.items():
        result[name] = result.get(name, 0) - coefficient
    return {name: coefficient for name, coefficient in result.items() if coefficient}, left_constant - right_constant


def _normal_constraint(coefficients: dict[str, int], bound: int) -> dict[str, Any]:
    coefficients = {name: coefficient for name, coefficient in coefficients.items() if coefficient}
    values = [abs(value) for value in coefficients.values()] + [abs(bound)]
    divisor = 0
    for value in values:
        divisor = gcd(divisor, value)
    if divisor > 1:
        coefficients = {name: value // divisor for name, value in coefficients.items()}
        bound //= divisor
    require(all(abs(value) <= MAX_ARITHMETIC for value in [*coefficients.values(), bound]),
            "PROOF_ARITHMETIC_LIMIT_EXCEEDED")
    return {"coefficients": [{"variable": name, "coefficient": coefficients[name]} for name in sorted(coefficients)],
            "bound": bound}


def _constraint_parts(constraint: dict[str, Any]) -> tuple[dict[str, int], int]:
    item = exact_keys(constraint, {"coefficients", "bound"}, "$.constraint")
    require(type(item["coefficients"]) is list and type(item["bound"]) is int, "PROOF_CONSTRAINT_INVALID")
    coefficients: dict[str, int] = {}
    prior = ""
    for row in item["coefficients"]:
        row = exact_keys(row, {"variable", "coefficient"}, "$.constraint.coefficients")
        require(type(row["variable"]) is str and row["variable"] > prior and type(row["coefficient"]) is int
                and row["coefficient"] != 0, "PROOF_CONSTRAINT_INVALID")
        prior = row["variable"]
        coefficients[row["variable"]] = row["coefficient"]
    require(_normal_constraint(coefficients, item["bound"]) == item, "PROOF_CONSTRAINT_NOT_NORMALIZED")
    return coefficients, item["bound"]


def _atom_constraints(atom: dict[str, Any]) -> list[dict[str, Any]]:
    left, left_constant = _linear(atom["args"][0])
    right, right_constant = _linear(atom["args"][1])
    coefficients = dict(left)
    for name, coefficient in right.items():
        coefficients[name] = coefficients.get(name, 0) - coefficient
    base_bound = right_constant - left_constant
    op = atom["op"]
    if op == "LE":
        return [_normal_constraint(coefficients, base_bound)]
    if op == "LT":
        return [_normal_constraint(coefficients, base_bound - 1)]
    reverse = {name: -coefficient for name, coefficient in coefficients.items()}
    if op == "GE":
        return [_normal_constraint(reverse, -base_bound)]
    if op == "GT":
        return [_normal_constraint(reverse, -base_bound - 1)]
    return [_normal_constraint(coefficients, base_bound), _normal_constraint(reverse, -base_bound)]


def _atoms(formula: dict[str, Any]) -> list[dict[str, Any]]:
    if formula["op"] == "TRUE":
        return []
    if formula["op"] == "AND":
        result: list[dict[str, Any]] = []
        for arg in formula["args"]:
            result.extend(_atoms(arg))
        return result
    return [formula]


def _sub_term(value: dict[str, Any], mapping: dict[str, dict[str, Any]]) -> dict[str, Any]:
    op = value["op"]
    if op == "VAR":
        return deepcopy(mapping[value["name"]])
    if op == "INT":
        return deepcopy(value)
    if op == "MUL_CONST":
        return {"op": op, "coefficient": value["coefficient"], "arg": _sub_term(value["arg"], mapping)}
    return {"op": op, "args": [_sub_term(arg, mapping) for arg in value["args"]]}


def _sub_formula(value: dict[str, Any], mapping: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if value["op"] == "TRUE":
        return {"op": "TRUE"}
    if value["op"] == "AND":
        return {"op": "AND", "args": [_sub_formula(arg, mapping) for arg in value["args"]]}
    return {"op": value["op"], "args": [_sub_term(arg, mapping) for arg in value["args"]]}


def _negate_atom(value: dict[str, Any]) -> dict[str, Any]:
    inverse = {"LE": "GT", "LT": "GE", "GE": "LT", "GT": "LE"}
    require(value["op"] in inverse, "PROOF_LOOP_CONDITION_NEGATION_UNSUPPORTED")
    return {"op": inverse[value["op"]], "args": deepcopy(value["args"])}


def make_contract(*, contract_id: str, subject_root: str, obligation_id: str,
                  variables: list[dict[str, Any]], assumptions: list[dict[str, Any]],
                  precondition: dict[str, Any], body: list[dict[str, Any]],
                  postcondition: dict[str, Any]) -> dict[str, Any]:
    base = {"schema": CONTRACT_SCHEMA, "theory_root": THEORY_ROOT,
            "contract_id": contract_id, "subject_root": subject_root,
            "obligation_id": obligation_id, "variables": deepcopy(variables),
            "assumptions": deepcopy(assumptions), "precondition": deepcopy(precondition),
            "body": deepcopy(body), "postcondition": deepcopy(postcondition),
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**base, "contract_root": root(base)}


def _validated_contract(value: Any) -> tuple[dict[str, Any], list[str]]:
    item = exact_keys(value, {"schema", "theory_root", "contract_id", "subject_root", "obligation_id", "variables",
        "assumptions", "precondition", "body", "postcondition", "standing", "authority_effect", "contract_root"}, "$.contract")
    require(item["schema"] == CONTRACT_SCHEMA and item["theory_root"] == THEORY_ROOT
            and item["standing"] == "INFORMATION_ONLY"
            and item["authority_effect"] == "NONE", "PROOF_CONTRACT_BOUNDARY_INVALID")
    _name(item["contract_id"], "$.contract.contract_id")
    _name(item["obligation_id"], "$.contract.obligation_id")
    require_root(item["subject_root"], "$.contract.subject_root")
    require(type(item["variables"]) is list and 1 <= len(item["variables"]) <= MAX_VARIABLES,
            "PROOF_VARIABLE_SET_INVALID")
    names: list[str] = []
    for index, row in enumerate(item["variables"]):
        row = exact_keys(row, {"name", "sort"}, f"$.contract.variables[{index}]")
        name = _name(row["name"], f"$.contract.variables[{index}].name")
        require(row["sort"] == "INT" and name not in names, "PROOF_VARIABLE_SET_INVALID")
        names.append(name)
    require(names == sorted(names), "PROOF_VARIABLES_NOT_CANONICAL")
    variables = set(names)
    require(type(item["assumptions"]) is list and len(item["assumptions"]) <= 64, "PROOF_ASSUMPTION_SET_INVALID")
    for index, formula in enumerate(item["assumptions"]):
        _formula(formula, variables, f"$.contract.assumptions[{index}]")
    _formula(item["precondition"], variables, "$.contract.precondition")
    _formula(item["postcondition"], variables, "$.contract.postcondition")
    require(type(item["body"]) is list and len(item["body"]) <= MAX_BODY, "PROOF_BODY_INVALID")
    statement_ids: set[str] = set()
    for index, statement in enumerate(item["body"]):
        require(type(statement) is dict and type(statement.get("op")) is str, "PROOF_STATEMENT_INVALID")
        op = statement["op"]
        path = f"$.contract.body[{index}]"
        if op == "ASSIGN":
            statement = exact_keys(statement, {"op", "target", "value"}, path)
            require(statement["target"] in variables, "PROOF_ASSIGN_TARGET_INVALID", path)
            _term(statement["value"], variables, path + ".value")
        elif op == "ASSERT":
            statement = exact_keys(statement, {"op", "id", "formula"}, path)
            identifier = _name(statement["id"], path + ".id")
            require(identifier not in statement_ids, "PROOF_STATEMENT_ID_DUPLICATE", path)
            statement_ids.add(identifier)
            _formula(statement["formula"], variables, path + ".formula")
        elif op == "LOOP":
            statement = exact_keys(statement, {"op", "id", "condition", "invariant", "decreases", "body"}, path)
            identifier = _name(statement["id"], path + ".id")
            require(identifier not in statement_ids, "PROOF_STATEMENT_ID_DUPLICATE", path)
            statement_ids.add(identifier)
            condition = _formula(statement["condition"], variables, path + ".condition")
            require(condition["op"] in {"LE", "LT", "GE", "GT"}, "PROOF_LOOP_CONDITION_INVALID", path)
            _formula(statement["invariant"], variables, path + ".invariant")
            _term(statement["decreases"], variables, path + ".decreases")
            require(type(statement["body"]) is list and 1 <= len(statement["body"]) <= MAX_BODY,
                    "PROOF_LOOP_BODY_INVALID", path)
            for nested_index, nested in enumerate(statement["body"]):
                nested = exact_keys(nested, {"op", "target", "value"}, f"{path}.body[{nested_index}]")
                require(nested["op"] == "ASSIGN" and nested["target"] in variables,
                        "PROOF_LOOP_BODY_INVALID", path)
                _term(nested["value"], variables, f"{path}.body[{nested_index}].value")
        else:
            require(False, "PROOF_STATEMENT_OP_UNSUPPORTED", path, op)
    _syntax_node_count(item["assumptions"], item["precondition"], item["body"], item["postcondition"])
    expected_root = root({key: value for key, value in item.items() if key != "contract_root"})
    require(item["contract_root"] == expected_root, "PROOF_CONTRACT_ROOT_MISMATCH")
    return deepcopy(item), names


def compile_contract(contract: Any) -> dict[str, Any]:
    item, names = _validated_contract(contract)
    variables = set(names)
    mapping = {name: {"op": "VAR", "name": name} for name in names}
    context = [deepcopy(formula) for formula in item["assumptions"]] + [deepcopy(item["precondition"])]
    vcs: list[dict[str, Any]] = []

    def emit(identifier: str, kind: str, antecedents: list[dict[str, Any]], goal: dict[str, Any]) -> None:
        antecedent_constraints: list[dict[str, Any]] = []
        antecedent_roots: list[str] = []
        for formula in antecedents:
            antecedent_roots.append(root(formula))
            for atom in _atoms(formula):
                antecedent_constraints.extend(_atom_constraints(atom))
        unique = {root(value): value for value in antecedent_constraints}
        antecedent_constraints = [unique[key] for key in sorted(unique)]
        goals: list[dict[str, Any]] = []
        for atom in _atoms(goal):
            goals.extend(_atom_constraints(atom))
        if not goals:
            return
        for index, goal_constraint in enumerate(goals):
            body = {"schema": "ucl.proof.verification_condition.v1",
                    "vc_id": identifier + (f".{index + 1}" if len(goals) > 1 else ""),
                    "kind": kind, "antecedent_formula_roots": antecedent_roots,
                    "goal_formula_root": root(goal), "antecedent_constraints": antecedent_constraints,
                    "goal_constraint": goal_constraint}
            vcs.append({**body, "vc_root": root(body)})

    for index, statement in enumerate(item["body"]):
        if statement["op"] == "ASSIGN":
            mapping[statement["target"]] = _sub_term(statement["value"], mapping)
        elif statement["op"] == "ASSERT":
            asserted = _sub_formula(statement["formula"], mapping)
            emit("ASSERT." + statement["id"], "ASSERTION", context, asserted)
            context.append(asserted)
        else:
            invariant_at_entry = _sub_formula(statement["invariant"], mapping)
            emit("LOOP." + statement["id"] + ".INIT", "LOOP_INVARIANT_INIT", context, invariant_at_entry)
            identity = {name: {"op": "VAR", "name": name} for name in names}
            loop_map = deepcopy(identity)
            for nested in statement["body"]:
                loop_map[nested["target"]] = _sub_term(nested["value"], loop_map)
            invariant = deepcopy(statement["invariant"])
            condition = deepcopy(statement["condition"])
            emit("LOOP." + statement["id"] + ".PRESERVE", "LOOP_INVARIANT_PRESERVATION",
                 [invariant, condition], _sub_formula(invariant, loop_map))
            zero = {"op": "INT", "value": 0}
            emit("LOOP." + statement["id"] + ".NONNEGATIVE", "LOOP_DECREASES_NONNEGATIVE",
                 [invariant, condition], {"op": "GE", "args": [deepcopy(statement["decreases"]), zero]})
            emit("LOOP." + statement["id"] + ".DECREASES", "LOOP_DECREASES_STRICT",
                 [invariant, condition], {"op": "LT", "args": [_sub_term(statement["decreases"], loop_map), deepcopy(statement["decreases"])]})
            mapping = {name: {"op": "VAR", "name": f"{name}@{statement['id']}@exit"} for name in names}
            extended = variables | set(value["name"] for value in mapping.values())
            # Generated names never enter the source contract but remain explicit in the VCs.
            _formula(_sub_formula(statement["invariant"], mapping), extended)
            context = [_sub_formula(statement["invariant"], mapping),
                       _sub_formula(_negate_atom(statement["condition"]), mapping)]
    postcondition = _sub_formula(item["postcondition"], mapping)
    emit("POST", "POSTCONDITION", context, postcondition)
    require(vcs and len(vcs) <= 1024, "PROOF_VC_SET_INVALID")
    body = {"schema": COMPILED_SCHEMA, "theory_root": THEORY_ROOT,
            "contract_root": item["contract_root"],
            "subject_root": item["subject_root"], "obligation_id": item["obligation_id"],
            "assumption_roots": [root(value) for value in item["assumptions"]],
            "verification_conditions": vcs, "vc_count": len(vcs),
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "compiled_root": root(body)}


def _negated(constraint: dict[str, Any]) -> dict[str, Any]:
    coefficients, bound = _constraint_parts(constraint)
    return _normal_constraint({name: -value for name, value in coefficients.items()}, -bound - 1)


def _combine(positive: dict[str, Any], negative: dict[str, Any], variable: str) -> tuple[dict[str, Any], int, int]:
    p_coefficients, p_bound = _constraint_parts(positive)
    n_coefficients, n_bound = _constraint_parts(negative)
    require(p_coefficients.get(variable, 0) > 0 and n_coefficients.get(variable, 0) < 0,
            "PROOF_ELIMINATION_SIGNS_INVALID")
    positive_multiplier = -n_coefficients[variable]
    negative_multiplier = p_coefficients[variable]
    names = set(p_coefficients) | set(n_coefficients)
    coefficients = {name: positive_multiplier * p_coefficients.get(name, 0)
                    + negative_multiplier * n_coefficients.get(name, 0) for name in names}
    result = _normal_constraint(coefficients, positive_multiplier * p_bound + negative_multiplier * n_bound)
    require(all(row["variable"] != variable for row in result["coefficients"]), "PROOF_ELIMINATION_FAILED")
    return result, positive_multiplier, negative_multiplier


def _search_certificate(vc: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    inputs = [*deepcopy(vc["antecedent_constraints"]), _negated(vc["goal_constraint"])]
    rows: list[dict[str, Any]] = []
    active: list[tuple[str, dict[str, Any]]] = []
    for index, constraint in enumerate(inputs):
        row_id = f"I{index:05d}"
        row = {"row_id": row_id, "kind": "INPUT", "input_index": index, "constraint": constraint}
        rows.append(row); active.append((row_id, constraint))
        coefficients, bound = _constraint_parts(constraint)
        if not coefficients and bound < 0:
            return _certificate(vc, inputs, rows, row_id), "PROVED"
    variables = sorted({row["variable"] for constraint in inputs for row in constraint["coefficients"]})
    counter = 0
    for variable in variables:
        positive, negative, zero = [], [], []
        for row_id, constraint in active:
            coefficients, _ = _constraint_parts(constraint)
            coefficient = coefficients.get(variable, 0)
            (positive if coefficient > 0 else negative if coefficient < 0 else zero).append((row_id, constraint))
        derived: list[tuple[str, dict[str, Any]]] = []
        seen = {root(constraint) for _, constraint in zero}
        for positive_id, positive_constraint in positive:
            for negative_id, negative_constraint in negative:
                if len(rows) >= MAX_TRACE_ROWS:
                    return None, "PROOF_SEARCH_ROW_LIMIT"
                try:
                    constraint, p_multiplier, n_multiplier = _combine(positive_constraint, negative_constraint, variable)
                except Exception as error:
                    if getattr(error, "code", "") == "PROOF_ARITHMETIC_LIMIT_EXCEEDED":
                        return None, "PROOF_SEARCH_ARITHMETIC_LIMIT"
                    raise
                digest = root(constraint)
                if digest in seen:
                    continue
                seen.add(digest)
                row_id = f"D{counter:05d}"; counter += 1
                row = {"row_id": row_id, "kind": "ELIMINATE", "parents": [positive_id, negative_id],
                       "variable": variable, "multipliers": [p_multiplier, n_multiplier],
                       "constraint": constraint}
                rows.append(row); derived.append((row_id, constraint))
                coefficients, bound = _constraint_parts(constraint)
                if not coefficients and bound < 0:
                    return _certificate(vc, inputs, rows, row_id), "PROVED"
        active = zero + derived
    return None, "PROOF_NOT_DERIVED"


def _certificate(vc: dict[str, Any], inputs: list[dict[str, Any]], rows: list[dict[str, Any]], terminal: str) -> dict[str, Any]:
    body = {"schema": CERTIFICATE_SCHEMA, "vc_root": vc["vc_root"], "inputs": inputs,
            "trace": rows, "terminal_row": terminal, "rule": "FOURIER_MOTZKIN_INTEGER_SOUND_V1"}
    return {**body, "certificate_root": root(body)}


def _check_certificate(vc: dict[str, Any], certificate: Any) -> None:
    item = exact_keys(certificate, {"schema", "vc_root", "inputs", "trace", "terminal_row", "rule", "certificate_root"}, "$.certificate")
    require(item["schema"] == CERTIFICATE_SCHEMA and item["rule"] == "FOURIER_MOTZKIN_INTEGER_SOUND_V1",
            "PROOF_CERTIFICATE_SCHEMA_INVALID")
    require(item["vc_root"] == vc["vc_root"], "PROOF_CERTIFICATE_VC_MISMATCH")
    expected_inputs = [*deepcopy(vc["antecedent_constraints"]), _negated(vc["goal_constraint"])]
    require(item["inputs"] == expected_inputs, "PROOF_CERTIFICATE_INPUT_MISMATCH")
    require(type(item["trace"]) is list and len(item["trace"]) <= MAX_TRACE_ROWS, "PROOF_TRACE_INVALID")
    known: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(item["trace"]):
        require(type(row) is dict and type(row.get("row_id")) is str and row["row_id"] not in known,
                "PROOF_TRACE_ROW_INVALID")
        if row.get("kind") == "INPUT":
            row = exact_keys(row, {"row_id", "kind", "input_index", "constraint"}, "$.certificate.trace")
            require(type(row["input_index"]) is int and 0 <= row["input_index"] < len(expected_inputs)
                    and row["constraint"] == expected_inputs[row["input_index"]], "PROOF_TRACE_INPUT_INVALID")
        elif row.get("kind") == "ELIMINATE":
            row = exact_keys(row, {"row_id", "kind", "parents", "variable", "multipliers", "constraint"}, "$.certificate.trace")
            require(type(row["parents"]) is list and len(row["parents"]) == 2
                    and all(parent in known for parent in row["parents"]), "PROOF_TRACE_PARENT_INVALID")
            expected, p_multiplier, n_multiplier = _combine(known[row["parents"][0]], known[row["parents"][1]], row["variable"])
            require(row["multipliers"] == [p_multiplier, n_multiplier] and row["constraint"] == expected,
                    "PROOF_TRACE_DERIVATION_INVALID")
        else:
            require(False, "PROOF_TRACE_RULE_UNSUPPORTED")
        _constraint_parts(row["constraint"])
        known[row["row_id"]] = row["constraint"]
    require(item["terminal_row"] in known, "PROOF_TERMINAL_ROW_MISSING")
    coefficients, bound = _constraint_parts(known[item["terminal_row"]])
    require(not coefficients and bound < 0, "PROOF_TERMINAL_NOT_CONTRADICTION")
    require(item["certificate_root"] == root({key: value for key, value in item.items() if key != "certificate_root"}),
            "PROOF_CERTIFICATE_ROOT_MISMATCH")


def prove_contract(contract: Any) -> dict[str, Any]:
    item, _ = _validated_contract(contract)
    compiled = compile_contract(item)
    proofs = []
    for vc in compiled["verification_conditions"]:
        certificate, diagnostic = _search_certificate(vc)
        if certificate is None:
            proofs.append({"vc_id": vc["vc_id"], "vc_root": vc["vc_root"], "status": "UNKNOWN",
                           "diagnostic": diagnostic, "certificate": None})
        else:
            proofs.append({"vc_id": vc["vc_id"], "vc_root": vc["vc_root"], "status": "PROVED",
                           "diagnostic": None, "certificate": certificate})
    all_proved = all(row["status"] == "PROVED" for row in proofs)
    outcome = ("ASSUMPTION_BOUND" if item["assumptions"] else "PROVED") if all_proved else "UNKNOWN"
    body = {"schema": PROOF_SCHEMA, "theory_root": THEORY_ROOT,
            "contract_root": item["contract_root"],
            "compiled_root": compiled["compiled_root"], "subject_root": item["subject_root"],
            "obligation_id": item["obligation_id"], "proofs": proofs, "outcome": outcome,
            "assumption_roots": compiled["assumption_roots"], "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE"}
    return {**body, "proof_bundle_root": root(body)}


def evidence_subject(contract: Any) -> dict[str, Any]:
    item, _ = _validated_contract(contract)
    return {"kind": "NATIVE_DEDUCTIVE_CONTRACT", "theory_root": THEORY_ROOT,
            "subject_root": item["subject_root"],
            "contract_root": item["contract_root"], "obligation_id": item["obligation_id"]}


def verify_proof(contract: Any, proof_bundle: Any) -> dict[str, Any]:
    item, _ = _validated_contract(contract)
    compiled = compile_contract(item)
    proof = exact_keys(proof_bundle, {"schema", "theory_root", "contract_root", "compiled_root", "subject_root",
        "obligation_id", "proofs", "outcome", "assumption_roots", "standing", "authority_effect",
        "proof_bundle_root"}, "$.proof")
    require(proof["schema"] == PROOF_SCHEMA and proof["theory_root"] == THEORY_ROOT
            and proof["standing"] == "INFORMATION_ONLY"
            and proof["authority_effect"] == "NONE", "PROOF_BUNDLE_BOUNDARY_INVALID")
    require(proof["contract_root"] == item["contract_root"] and proof["compiled_root"] == compiled["compiled_root"]
            and proof["subject_root"] == item["subject_root"] and proof["obligation_id"] == item["obligation_id"]
            and proof["assumption_roots"] == compiled["assumption_roots"], "PROOF_BUNDLE_SUBJECT_MISMATCH")
    require(type(proof["proofs"]) is list and len(proof["proofs"]) == compiled["vc_count"], "PROOF_BUNDLE_COUNT_MISMATCH")
    statuses = []
    for vc, row in zip(compiled["verification_conditions"], proof["proofs"], strict=True):
        row = exact_keys(row, {"vc_id", "vc_root", "status", "diagnostic", "certificate"}, "$.proof.proofs")
        require(row["vc_id"] == vc["vc_id"] and row["vc_root"] == vc["vc_root"], "PROOF_BUNDLE_VC_MISMATCH")
        require(row["status"] in {"PROVED", "UNKNOWN"}, "PROOF_BUNDLE_STATUS_INVALID")
        if row["status"] == "PROVED":
            require(row["diagnostic"] is None and row["certificate"] is not None, "PROOF_CERTIFICATE_MISSING")
            _check_certificate(vc, row["certificate"])
        else:
            require(type(row["diagnostic"]) is str and row["diagnostic"] and row["certificate"] is None,
                    "PROOF_UNKNOWN_RECORD_INVALID")
        statuses.append(row["status"])
    expected = (("ASSUMPTION_BOUND" if item["assumptions"] else "PROVED")
                if all(status == "PROVED" for status in statuses) else "UNKNOWN")
    require(proof["outcome"] == expected, "PROOF_OUTCOME_MISMATCH")
    require(proof["proof_bundle_root"] == root({key: value for key, value in proof.items() if key != "proof_bundle_root"}),
            "PROOF_BUNDLE_ROOT_MISMATCH")
    body = {"schema": CHECK_SCHEMA, "theory_root": THEORY_ROOT,
            "contract_root": item["contract_root"],
            "compiled_root": compiled["compiled_root"], "proof_bundle_root": proof["proof_bundle_root"],
            "evidence_subject": evidence_subject(item), "outcome": expected,
            "kernel": "LINEAR_INTEGER_FOURIER_MOTZKIN_CERTIFICATE_CHECKER_V1",
            "status": "PASS_CHECKED", "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "check_root": root(body)}


def make_solver_request(contract: Any) -> dict[str, Any]:
    item, _ = _validated_contract(contract)
    compiled = compile_contract(item)
    body = {"schema": SOLVER_REQUEST_SCHEMA, "theory_root": THEORY_ROOT,
            "contract_root": item["contract_root"],
            "compiled_root": compiled["compiled_root"],
            "vc_roots": [vc["vc_root"] for vc in compiled["verification_conditions"]],
            "required_certificate_schema": CERTIFICATE_SCHEMA,
            "adapter_trust": "UNTRUSTED_SEARCH_ONLY_KERNEL_RECHECK_REQUIRED",
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "request_root": root(body)}


def verify_solver_response(contract: Any, request: Any, response: Any) -> dict[str, Any]:
    expected = make_solver_request(contract)
    require(request == expected, "PROOF_SOLVER_REQUEST_MISMATCH")
    item = exact_keys(response, {"schema", "request_root", "solver_identity", "proof_bundle",
        "standing", "authority_effect", "response_root"}, "$.solver_response")
    require(item["schema"] == SOLVER_RESPONSE_SCHEMA and item["request_root"] == expected["request_root"]
            and type(item["solver_identity"]) is dict and item["standing"] == "INFORMATION_ONLY"
            and item["authority_effect"] == "NONE", "PROOF_SOLVER_RESPONSE_INVALID")
    require(item["response_root"] == root({key: value for key, value in item.items() if key != "response_root"}),
            "PROOF_SOLVER_RESPONSE_ROOT_MISMATCH")
    return verify_proof(contract, item["proof_bundle"])

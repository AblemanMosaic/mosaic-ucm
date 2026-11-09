"""Substrate-neutral realization spaces with deterministic admissibility and choice.

This module is deliberately finite and certificate-oriented.  UCL obligations remain
hard constraints.  Tessera's existing intent projection remains unchanged; the
``preference_projection`` below is a new, versioned adapter and makes no claim that
the historical Tessera language already implements optimization.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import canonical_bytes, exact_keys, require, require_root, root
from .maturity_semantics import BOUNDARY, ceiling, seal, verify_ceiling


AXIS_KINDS = {"BOOLEAN", "ENUM", "INTEGER", "ROOT", "STRING"}
CONSTRAINT_KINDS = {"EQUALS", "FORBIDS_COMBINATION", "IN", "NOT_EQUALS", "RANGE", "REQUIRES"}
DIRECTIONS = {"MAXIMIZE", "MINIMIZE"}
CAPABILITIES = [
    "CHECK_ADMISSIBILITY", "COMPARE_REALIZATIONS", "DESCRIBE_SPACE",
    "ESTIMATE_CONSEQUENCES", "EXPLAIN_SELECTION", "PREPARE_ADAPTATION",
    "PROJECT_TO_UCL_TESSERA", "REPRODUCE_SELECTION", "TRACE_PRESERVATION",
]


def _text(value: Any, code: str, maximum: int = 512) -> str:
    require(type(value) is str and 0 < len(value) <= maximum, code)
    return value


def _axis(axis: Any) -> dict[str, Any]:
    item = exact_keys(axis, {"id", "kind", "domain", "default", "description"}, "$.axis")
    identifier = _text(item["id"], "REALIZATION_AXIS_ID_INVALID", 128)
    require(item["kind"] in AXIS_KINDS, "REALIZATION_AXIS_KIND_INVALID", identifier)
    _text(item["description"], "REALIZATION_AXIS_DESCRIPTION_INVALID", 1024)
    domain = item["domain"]
    kind = item["kind"]
    if kind == "BOOLEAN":
        require(domain == [False, True], "REALIZATION_BOOLEAN_DOMAIN_INVALID", identifier)
    elif kind == "INTEGER":
        exact_keys(domain, {"minimum", "maximum"}, f"$.axis.{identifier}.domain")
        require(type(domain["minimum"]) is int and type(domain["maximum"]) is int
                and domain["minimum"] <= domain["maximum"], "REALIZATION_INTEGER_DOMAIN_INVALID", identifier)
    elif kind == "ROOT":
        require(domain == {"algorithm": "sha256", "length": 64}, "REALIZATION_ROOT_DOMAIN_INVALID", identifier)
    else:
        require(type(domain) is list and 0 < len(domain) <= 256
                and all(type(v) is str and v for v in domain) and len(domain) == len(set(domain)),
                "REALIZATION_FINITE_DOMAIN_INVALID", identifier)
    _axis_value(item, item["default"])
    return deepcopy(item)


def _axis_value(axis: dict[str, Any], value: Any) -> None:
    kind, domain = axis["kind"], axis["domain"]
    if kind == "BOOLEAN":
        require(type(value) is bool, "REALIZATION_AXIS_VALUE_INVALID", axis["id"])
    elif kind == "INTEGER":
        require(type(value) is int and domain["minimum"] <= value <= domain["maximum"],
                "REALIZATION_AXIS_VALUE_INVALID", axis["id"])
    elif kind == "ROOT":
        require_root(value, f"$.configuration.{axis['id']}")
    elif kind in {"ENUM", "STRING"}:
        require(type(value) is str and value in domain, "REALIZATION_AXIS_VALUE_INVALID", axis["id"])


def _constraint(value: Any, axes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    item = exact_keys(value, {"id", "kind", "terms", "rationale"}, "$.constraint")
    _text(item["id"], "REALIZATION_CONSTRAINT_ID_INVALID", 128)
    require(item["kind"] in CONSTRAINT_KINDS and type(item["terms"]) is dict,
            "REALIZATION_CONSTRAINT_INVALID", item["id"])
    _text(item["rationale"], "REALIZATION_CONSTRAINT_RATIONALE_INVALID", 1024)
    terms, kind = item["terms"], item["kind"]
    if kind in {"EQUALS", "NOT_EQUALS", "IN", "RANGE"}:
        required = {"axis", "value"} if kind != "RANGE" else {"axis", "minimum", "maximum"}
        exact_keys(terms, required, f"$.constraint.{item['id']}.terms")
        require(terms["axis"] in axes, "REALIZATION_CONSTRAINT_AXIS_UNKNOWN", item["id"])
        axis = axes[terms["axis"]]
        if kind in {"EQUALS", "NOT_EQUALS"}:
            _axis_value(axis, terms["value"])
        elif kind == "IN":
            require(type(terms["value"]) is list and bool(terms["value"]),
                    "REALIZATION_CONSTRAINT_OPERAND_INVALID", item["id"])
            for operand in terms["value"]:
                _axis_value(axis, operand)
        else:
            require(axis["kind"] == "INTEGER" and type(terms["minimum"]) is int
                    and type(terms["maximum"]) is int and terms["minimum"] <= terms["maximum"],
                    "REALIZATION_CONSTRAINT_OPERAND_INVALID", item["id"])
            _axis_value(axis, terms["minimum"]); _axis_value(axis, terms["maximum"])
    elif kind == "REQUIRES":
        exact_keys(terms, {"if", "then"}, f"$.constraint.{item['id']}.terms")
        for clause in (terms["if"], terms["then"]):
            exact_keys(clause, {"axis", "equals"}, f"$.constraint.{item['id']}.clause")
            require(clause["axis"] in axes, "REALIZATION_CONSTRAINT_AXIS_UNKNOWN", item["id"])
            _axis_value(axes[clause["axis"]], clause["equals"])
    else:
        exact_keys(terms, {"assignments"}, f"$.constraint.{item['id']}.terms")
        require(type(terms["assignments"]) is dict and len(terms["assignments"]) >= 2
                and set(terms["assignments"]) <= set(axes), "REALIZATION_CONSTRAINT_ASSIGNMENTS_INVALID", item["id"])
        for axis_id, operand in terms["assignments"].items():
            _axis_value(axes[axis_id], operand)
    return deepcopy(item)


def make_space_contract(*, contract_id: str, subject_root: str, axes: list[dict[str, Any]],
                        hard_constraints: list[dict[str, Any]], objectives: list[dict[str, Any]],
                        identity_axes: list[str], allowed_effects: list[str] | None = None) -> dict[str, Any]:
    _text(contract_id, "REALIZATION_CONTRACT_ID_INVALID", 128)
    require_root(subject_root)
    require(type(axes) is list and 0 < len(axes) <= 128, "REALIZATION_AXES_INVALID")
    checked_axes = [_axis(item) for item in axes]
    ids = [item["id"] for item in checked_axes]
    require(len(ids) == len(set(ids)), "REALIZATION_AXIS_DUPLICATE")
    axis_map = {item["id"]: item for item in checked_axes}
    checked_constraints = [_constraint(item, axis_map) for item in hard_constraints]
    constraint_ids = [item["id"] for item in checked_constraints]
    require(len(constraint_ids) == len(set(constraint_ids)), "REALIZATION_CONSTRAINT_DUPLICATE")
    checked_objectives = []
    for value in objectives:
        item = exact_keys(value, {"id", "metric", "direction", "priority", "rationale"}, "$.objective")
        _text(item["id"], "REALIZATION_OBJECTIVE_ID_INVALID", 128)
        _text(item["metric"], "REALIZATION_OBJECTIVE_METRIC_INVALID", 128)
        require(item["direction"] in DIRECTIONS and type(item["priority"]) is int and 0 <= item["priority"] <= 1000,
                "REALIZATION_OBJECTIVE_INVALID", item["id"])
        _text(item["rationale"], "REALIZATION_OBJECTIVE_RATIONALE_INVALID", 1024)
        checked_objectives.append(deepcopy(item))
    require(len({item["id"] for item in checked_objectives}) == len(checked_objectives), "REALIZATION_OBJECTIVE_DUPLICATE")
    require(type(identity_axes) is list and identity_axes == sorted(set(identity_axes))
            and set(identity_axes) <= set(ids), "REALIZATION_IDENTITY_AXES_INVALID")
    body = {
        "schema": "ucl.ucm.realization_space_contract.v1", "contract_id": contract_id,
        "subject_root": subject_root, "axes": checked_axes, "hard_constraints": checked_constraints,
        "objectives": checked_objectives, "identity_axes": identity_axes, "capabilities": CAPABILITIES,
        "semantic_status": {
            "realization_funnel": "GENERATED_UCM_ARCHITECTURAL_SYNTHESIS",
            "cm1": "ADMISSIBLE_CONFIGURATION_SET; NOT_CANONICAL_CORPUS_TERM_BINDING",
            "cm2": "DETERMINISTIC_PREFERENCE_SELECTION; NOT_CANONICAL_CORPUS_TERM_BINDING",
        },
        "authority_ceiling": ceiling(allowed_effects=[] if allowed_effects is None else allowed_effects), **BOUNDARY,
    }
    return seal(body)


def verify_space_contract(value: Any, *, expected_root: str | None = None) -> dict[str, Any]:
    require(type(value) is dict and value.get("schema") == "ucl.ucm.realization_space_contract.v1", "REALIZATION_CONTRACT_SCHEMA_INVALID")
    rebuilt = make_space_contract(contract_id=value.get("contract_id"), subject_root=value.get("subject_root"),
        axes=value.get("axes"), hard_constraints=value.get("hard_constraints"), objectives=value.get("objectives"),
        identity_axes=value.get("identity_axes"), allowed_effects=value.get("authority_ceiling", {}).get("allowed_effects"))
    require(canonical_bytes(value) == canonical_bytes(rebuilt), "REALIZATION_CONTRACT_RECONSTRUCTION_MISMATCH")
    if expected_root is not None:
        require(value["root"] == require_root(expected_root), "REALIZATION_CONTRACT_PIN_MISMATCH")
    verify_ceiling(value["authority_ceiling"])
    return rebuilt


def _configuration(contract: dict[str, Any], value: Any) -> dict[str, Any]:
    require(type(value) is dict and set(value) == {axis["id"] for axis in contract["axes"]}, "REALIZATION_CONFIGURATION_AXES_MISMATCH")
    for axis in contract["axes"]:
        _axis_value(axis, value[axis["id"]])
    return deepcopy(value)


def _holds(constraint: dict[str, Any], config: dict[str, Any]) -> bool:
    kind, terms = constraint["kind"], constraint["terms"]
    if kind == "EQUALS": return config[terms["axis"]] == terms["value"]
    if kind == "NOT_EQUALS": return config[terms["axis"]] != terms["value"]
    if kind == "IN": return config[terms["axis"]] in terms["value"]
    if kind == "RANGE": return terms["minimum"] <= config[terms["axis"]] <= terms["maximum"]
    if kind == "REQUIRES":
        antecedent = config[terms["if"]["axis"]] == terms["if"]["equals"]
        return not antecedent or config[terms["then"]["axis"]] == terms["then"]["equals"]
    return not all(config[key] == value for key, value in terms["assignments"].items())


def check_admissibility(contract_value: dict[str, Any], configuration: Any) -> dict[str, Any]:
    contract = verify_space_contract(contract_value)
    config = _configuration(contract, configuration)
    rows = [{"constraint_id": item["id"], "status": "PASS" if _holds(item, config) else "FAIL"}
            for item in contract["hard_constraints"]]
    body = {"schema": "ucl.ucm.realization_admissibility.v1", "contract_root": contract["root"],
        "configuration": config, "configuration_root": root(config), "checks": rows,
        "status": "PASS_ADMISSIBLE" if all(row["status"] == "PASS" for row in rows) else "REFUSED_INADMISSIBLE",
        **BOUNDARY}
    return seal(body)


def select_realization(contract_value: dict[str, Any], candidates: Any) -> dict[str, Any]:
    contract = verify_space_contract(contract_value)
    require(type(candidates) is list and 0 < len(candidates) <= 10000, "REALIZATION_CANDIDATES_INVALID")
    rows = []
    metric_ids = {item["metric"] for item in contract["objectives"]}
    for candidate in candidates:
        exact_keys(candidate, {"configuration", "metrics"}, "$.candidate")
        require(type(candidate["metrics"]) is dict and set(candidate["metrics"]) == metric_ids
                and all(type(v) is int for v in candidate["metrics"].values()), "REALIZATION_METRICS_INVALID")
        admissibility = check_admissibility(contract, candidate["configuration"])
        rows.append({"configuration": deepcopy(candidate["configuration"]), "configuration_root": admissibility["configuration_root"],
                     "metrics": deepcopy(candidate["metrics"]), "admissibility_root": admissibility["root"], "status": admissibility["status"]})
    rows.sort(key=lambda row: (row["configuration_root"], root(row["metrics"])))
    admissible = [row for row in rows if row["status"] == "PASS_ADMISSIBLE"]
    require(bool(admissible), "REALIZATION_NO_ADMISSIBLE_CANDIDATE")
    objectives = sorted(contract["objectives"], key=lambda item: (-item["priority"], item["id"]))
    def rank(row: dict[str, Any]) -> tuple:
        scores = [row["metrics"][item["metric"]] * (-1 if item["direction"] == "MAXIMIZE" else 1) for item in objectives]
        return (*scores, row["configuration_root"])
    selected = min(admissible, key=rank)
    body = {"schema": "ucl.ucm.realization_selection.v1", "contract_root": contract["root"],
        "candidate_set_root": root(rows), "evaluations": rows, "objective_order": [item["id"] for item in objectives],
        "selected_configuration": selected["configuration"], "selected_configuration_root": selected["configuration_root"],
        "selection_rule": "LEXICOGRAPHIC_PRIORITY_THEN_CONFIGURATION_ROOT", "status": "PASS_SELECTED", **BOUNDARY}
    return seal(body)


def project_to_ucl_tessera(contract_value: dict[str, Any]) -> dict[str, Any]:
    contract = verify_space_contract(contract_value)
    hard = [{"obligation_id": item["id"], "formula": deepcopy(item), "source": contract["root"]}
            for item in contract["hard_constraints"]]
    preferences = [{"preference_id": item["id"], "metric": item["metric"], "direction": item["direction"],
                    "priority": item["priority"], "source": contract["root"]} for item in contract["objectives"]]
    return seal({"schema": "ucl.tessera.realization_projection.v1", "contract_root": contract["root"],
        "ucl_hard_obligations": hard, "tessera_preferences": preferences,
        "compatibility": {"historical_ucl_semantics": "UNCHANGED", "historical_tessera_intent_projection": "UNCHANGED",
                          "equivalence_claim": "NONE; THIS_IS_A_VERSIONED_ADAPTER"}, **BOUNDARY})


def trace_adaptation(contract_value: dict[str, Any], before: Any, after: Any) -> dict[str, Any]:
    contract = verify_space_contract(contract_value)
    first, second = _configuration(contract, before), _configuration(contract, after)
    preserved = [axis for axis in contract["identity_axes"] if first[axis] == second[axis]]
    changed = [axis["id"] for axis in contract["axes"] if first[axis["id"]] != second[axis["id"]]]
    before_check, after_check = check_admissibility(contract, first), check_admissibility(contract, second)
    body = {"schema": "ucl.ucm.realization_adaptation_receipt.v1", "contract_root": contract["root"],
        "before_root": root(first), "after_root": root(second), "changed_axes": changed,
        "preserved_identity_axes": preserved, "identity_preserved": preserved == contract["identity_axes"],
        "before_status": before_check["status"], "after_status": after_check["status"],
        "status": "PASS_PRESERVED" if preserved == contract["identity_axes"] and after_check["status"] == "PASS_ADMISSIBLE" else "REFUSED_NOT_PRESERVED",
        **BOUNDARY}
    return seal(body)

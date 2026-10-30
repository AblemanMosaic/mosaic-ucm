"""Executable, substrate-neutral Realization Space Contract v0.1.

A result says PASS_ADMISSIBLE only after every declared hard constraint in
the supported v0.1 subset has been evaluated. Unsupported semantics refuse.
"""
from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from uclop.canonical import canonical_bytes, require, root

BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE", "real_a5": False, "g0": "CLOSED"}
CAPABILITIES = {
    "ENUMERATE", "VALIDATE", "NORMALIZE", "SELECT", "LOWER", "COMPARE",
    "EXPLAIN", "RECEIPT", "PROJECT", "TRACE",
}
AXIS_TYPES = {"BOOLEAN", "INTEGER", "ENUM", "SEED", "ROOT"}
OWNERSHIP = {"AUTHORIAL", "USER", "ADAPTIVE", "RUNTIME", "DERIVED", "EVIDENCE_ONLY"}
MUTABILITY = {"FROZEN", "INSTANCE", "SESSION", "FRAME", "EDIT", "DERIVED"}
CONTINUITY = {"DISCRETE", "NOT_INTERPOLABLE"}
CONSTRAINT_KINDS = {"INVARIANT", "DEPENDENCY", "EXCLUSION", "COMPATIBILITY", "BUDGET", "CLAIM_BOUNDARY"}
OPERATORS = {"EQUALS", "NOT_EQUALS", "IN", "RANGE", "REQUIRES", "FORBIDS_COMBINATION"}
SELECTION_POLICIES = {"EXACT_DEFAULTS", "OBJECTIVE_PRIORITY", "LEXICOGRAPHIC_CONFIGURATION_ROOT"}
ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9_.:-]*$")


def _body_root(value: dict[str, Any]) -> str:
    return root({key: item for key, item in value.items() if key != "root"})


def _exact(value: Any, required: set[str], optional: set[str], code: str) -> dict[str, Any]:
    require(type(value) is dict and required <= set(value) <= required | optional, code)
    return value


def _identifier(value: Any, code: str) -> str:
    require(type(value) is str and ID_PATTERN.fullmatch(value) is not None, code)
    return value


def _text(value: Any, code: str) -> str:
    require(type(value) is str and bool(value), code)
    return value


def _strings(value: Any, code: str, *, allow_empty: bool = True) -> list[str]:
    require(type(value) is list and (allow_empty or bool(value)), code)
    require(all(type(item) is str and bool(item) for item in value), code)
    require(len(value) == len(set(value)), code)
    return value


def _root_value(value: Any) -> bool:
    return type(value) is str and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _axis_valid(axis: dict[str, Any], candidate: Any) -> bool:
    kind, domain = axis["value_type"], axis["domain"]
    if kind == "BOOLEAN":
        return type(candidate) is bool
    if kind == "INTEGER":
        if type(candidate) is not int:
            return False
        low, high = domain["minimum"], domain["maximum"]
        if candidate <= low if domain.get("exclusive_minimum", False) else candidate < low:
            return False
        if candidate >= high if domain.get("exclusive_maximum", False) else candidate > high:
            return False
        return "step" not in domain or (candidate - low) % domain["step"] == 0
    if kind == "ENUM":
        return type(candidate) is str and candidate in domain["values"]
    if kind == "SEED":
        return type(candidate) is int and 0 <= candidate <= 2**63 - 1
    return _root_value(candidate)


def _validate_axis(value: Any) -> dict[str, Any]:
    required = {"id", "label", "value_type", "domain", "default", "ownership", "mutability", "continuity", "authority_effect"}
    optional = {"description", "unit", "dependencies", "cost_metrics", "ui_hint"}
    axis = _exact(value, required, optional, "RSC_AXIS_SCHEMA_REFUSED")
    _identifier(axis["id"], "RSC_AXIS_ID_REFUSED")
    _text(axis["label"], "RSC_AXIS_LABEL_REFUSED")
    require(axis["value_type"] in AXIS_TYPES, "RSC_AXIS_TYPE_UNSUPPORTED", detail=str(axis["value_type"]))
    require(axis["ownership"] in OWNERSHIP and axis["mutability"] in MUTABILITY, "RSC_AXIS_CONTROL_REFUSED")
    require(axis["continuity"] in CONTINUITY and axis["authority_effect"] == "NONE", "RSC_AXIS_CONTROL_REFUSED")
    domain, kind = axis["domain"], axis["value_type"]
    if kind == "BOOLEAN":
        require(domain == {}, "RSC_BOOLEAN_DOMAIN_REFUSED")
    elif kind == "INTEGER":
        domain = _exact(domain, {"minimum", "maximum"}, {"exclusive_minimum", "exclusive_maximum", "step"}, "RSC_INTEGER_DOMAIN_REFUSED")
        require(type(domain["minimum"]) is int and type(domain["maximum"]) is int and domain["minimum"] <= domain["maximum"], "RSC_INTEGER_DOMAIN_REFUSED")
        require(type(domain.get("exclusive_minimum", False)) is bool and type(domain.get("exclusive_maximum", False)) is bool, "RSC_INTEGER_DOMAIN_REFUSED")
        require("step" not in domain or (type(domain["step"]) is int and domain["step"] > 0), "RSC_INTEGER_DOMAIN_REFUSED")
    elif kind == "ENUM":
        domain = _exact(domain, {"values"}, set(), "RSC_ENUM_DOMAIN_REFUSED")
        _strings(domain["values"], "RSC_ENUM_DOMAIN_REFUSED", allow_empty=False)
    elif kind == "SEED":
        require(domain == {}, "RSC_SEED_DOMAIN_REFUSED")
    else:
        require(domain == {"algorithm": "sha256", "length": 64}, "RSC_ROOT_DOMAIN_REFUSED")
    if "dependencies" in axis:
        _strings(axis["dependencies"], "RSC_AXIS_DEPENDENCY_REFUSED")
    if "cost_metrics" in axis:
        _strings(axis["cost_metrics"], "RSC_AXIS_COST_REFUSED")
    for key in ("description", "unit", "ui_hint"):
        require(key not in axis or type(axis[key]) is str, "RSC_AXIS_SCHEMA_REFUSED")
    require(_axis_valid(axis, axis["default"]), "RSC_AXIS_DEFAULT_REFUSED", detail=axis["id"])
    return deepcopy(axis)


def _clause(value: Any, axes: dict[str, dict[str, Any]], code: str) -> dict[str, Any]:
    item = _exact(value, {"axis", "equals"}, set(), code)
    require(item["axis"] in axes and _axis_valid(axes[item["axis"]], item["equals"]), code)
    return item


def _validate_constraint(value: Any, axes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    item = _exact(
        value,
        {"id", "kind", "severity", "operator", "terms", "explanation", "refusal_code"},
        set(),
        "RSC_CONSTRAINT_SCHEMA_REFUSED",
    )
    _identifier(item["id"], "RSC_CONSTRAINT_ID_REFUSED")
    _identifier(item["refusal_code"], "RSC_CONSTRAINT_CODE_REFUSED")
    require(item["kind"] in CONSTRAINT_KINDS and item["severity"] in {"HARD", "ADVISORY"}, "RSC_CONSTRAINT_KIND_REFUSED")
    require(item["operator"] in OPERATORS, "RSC_CONSTRAINT_OPERATOR_UNSUPPORTED")
    _text(item["explanation"], "RSC_CONSTRAINT_EXPLANATION_REFUSED")
    terms, operator = item["terms"], item["operator"]
    if operator in {"EQUALS", "NOT_EQUALS"}:
        terms = _exact(terms, {"axis", "value"}, set(), "RSC_CONSTRAINT_TERMS_REFUSED")
        require(terms["axis"] in axes and _axis_valid(axes[terms["axis"]], terms["value"]), "RSC_CONSTRAINT_TERMS_REFUSED")
    elif operator == "IN":
        terms = _exact(terms, {"axis", "values"}, set(), "RSC_CONSTRAINT_TERMS_REFUSED")
        require(terms["axis"] in axes and type(terms["values"]) is list and bool(terms["values"]), "RSC_CONSTRAINT_TERMS_REFUSED")
        require(all(_axis_valid(axes[terms["axis"]], operand) for operand in terms["values"]), "RSC_CONSTRAINT_TERMS_REFUSED")
    elif operator == "RANGE":
        terms = _exact(terms, {"axis", "minimum", "maximum"}, set(), "RSC_CONSTRAINT_TERMS_REFUSED")
        require(terms["axis"] in axes and axes[terms["axis"]]["value_type"] == "INTEGER", "RSC_CONSTRAINT_TERMS_REFUSED")
        require(type(terms["minimum"]) is int and type(terms["maximum"]) is int and terms["minimum"] <= terms["maximum"], "RSC_CONSTRAINT_TERMS_REFUSED")
        require(_axis_valid(axes[terms["axis"]], terms["minimum"]) and _axis_valid(axes[terms["axis"]], terms["maximum"]), "RSC_CONSTRAINT_TERMS_REFUSED")
    elif operator == "REQUIRES":
        terms = _exact(terms, {"if", "then"}, set(), "RSC_CONSTRAINT_TERMS_REFUSED")
        _clause(terms["if"], axes, "RSC_CONSTRAINT_TERMS_REFUSED")
        _clause(terms["then"], axes, "RSC_CONSTRAINT_TERMS_REFUSED")
    else:
        terms = _exact(terms, {"assignments"}, set(), "RSC_CONSTRAINT_TERMS_REFUSED")
        assignments = terms["assignments"]
        require(type(assignments) is dict and len(assignments) >= 2 and set(assignments) <= set(axes), "RSC_CONSTRAINT_TERMS_REFUSED")
        require(all(_axis_valid(axes[key], operand) for key, operand in assignments.items()), "RSC_CONSTRAINT_TERMS_REFUSED")
    return deepcopy(item)


def _constraint_holds(item: dict[str, Any], configuration: dict[str, Any]) -> bool:
    operator, terms = item["operator"], item["terms"]
    if operator == "EQUALS":
        return configuration[terms["axis"]] == terms["value"]
    if operator == "NOT_EQUALS":
        return configuration[terms["axis"]] != terms["value"]
    if operator == "IN":
        return configuration[terms["axis"]] in terms["values"]
    if operator == "RANGE":
        return terms["minimum"] <= configuration[terms["axis"]] <= terms["maximum"]
    if operator == "REQUIRES":
        antecedent = configuration[terms["if"]["axis"]] == terms["if"]["equals"]
        return not antecedent or configuration[terms["then"]["axis"]] == terms["then"]["equals"]
    return not all(configuration[key] == operand for key, operand in terms["assignments"].items())


def _validate_subject(contract: dict[str, Any]) -> None:
    subject = _exact(
        contract["subject"],
        {"subject_id", "subject_schema", "authority_owner", "source_roots", "preserved_identity", "forbidden_overrides"},
        {"coordinate_frame"},
        "RSC_SUBJECT_REFUSED",
    )
    _identifier(subject["subject_id"], "RSC_SUBJECT_REFUSED")
    _text(subject["subject_schema"], "RSC_SUBJECT_REFUSED")
    _identifier(subject["authority_owner"], "RSC_SUBJECT_REFUSED")
    _strings(subject["source_roots"], "RSC_SUBJECT_REFUSED", allow_empty=False)
    _strings(subject["preserved_identity"], "RSC_SUBJECT_REFUSED")
    _strings(subject["forbidden_overrides"], "RSC_SUBJECT_REFUSED")
    require("coordinate_frame" not in subject or type(subject["coordinate_frame"]) is dict, "RSC_SUBJECT_REFUSED")
    possibility = _exact(contract["possibility"], {"intended_variation", "excluded_claims"}, set(), "RSC_POSSIBILITY_REFUSED")
    _strings(possibility["intended_variation"], "RSC_POSSIBILITY_REFUSED")
    _strings(possibility["excluded_claims"], "RSC_POSSIBILITY_REFUSED")


def _validate_objectives(contract: dict[str, Any]) -> None:
    objectives = contract.get("objectives", [])
    require(type(objectives) is list, "RSC_OBJECTIVES_REFUSED")
    ids = []
    for objective in objectives:
        item = _exact(objective, {"metric_id", "direction", "priority", "measurement", "scope"}, {"unit"}, "RSC_OBJECTIVE_REFUSED")
        ids.append(_identifier(item["metric_id"], "RSC_OBJECTIVE_REFUSED"))
        require(item["direction"] in {"MINIMIZE", "MAXIMIZE"} and type(item["priority"]) is int and item["priority"] >= 0, "RSC_OBJECTIVE_REFUSED")
        _text(item["measurement"], "RSC_OBJECTIVE_REFUSED")
        require(item["scope"] in {"PORTABLE", "HOST", "SCENE", "SESSION", "HUMAN_SUBJECTIVE"}, "RSC_OBJECTIVE_REFUSED")
        require("unit" not in item or type(item["unit"]) is str, "RSC_OBJECTIVE_REFUSED")
    require(len(ids) == len(set(ids)), "RSC_OBJECTIVE_DUPLICATE")


def _validate_lowering_and_evidence(contract: dict[str, Any]) -> None:
    lowering = _exact(contract["lowering"], {"targets", "allowed_results"}, set(), "RSC_LOWERING_REFUSED")
    require(type(lowering["targets"]) is list and bool(lowering["targets"]), "RSC_LOWERING_REFUSED")
    for target in lowering["targets"]:
        item = _exact(
            target,
            {"target_id", "adapter_version", "required_capabilities", "preservation_criteria", "known_losses", "fallbacks"},
            {"runtime_family", "optional_capabilities"},
            "RSC_LOWERING_REFUSED",
        )
        _identifier(item["target_id"], "RSC_LOWERING_REFUSED")
        _text(item["adapter_version"], "RSC_LOWERING_REFUSED")
        if "runtime_family" in item:
            _identifier(item["runtime_family"], "RSC_LOWERING_REFUSED")
        for key in ("required_capabilities", "preservation_criteria", "known_losses", "fallbacks"):
            _strings(item[key], "RSC_LOWERING_REFUSED")
        if "optional_capabilities" in item:
            _strings(item["optional_capabilities"], "RSC_LOWERING_REFUSED")
    results = _strings(lowering["allowed_results"], "RSC_LOWERING_REFUSED", allow_empty=False)
    require(set(results) <= {"EXACT", "BOUNDED", "FALLBACK", "LOSSY", "REFUSED"}, "RSC_LOWERING_REFUSED")
    evidence = _exact(contract["evidence"], {"required_roots", "required_fields", "non_claims"}, {"metrics"}, "RSC_EVIDENCE_REFUSED")
    for key in ("required_roots", "required_fields", "non_claims"):
        _strings(evidence[key], "RSC_EVIDENCE_REFUSED")
    if "metrics" in evidence:
        _strings(evidence["metrics"], "RSC_EVIDENCE_REFUSED")


def validate_contract(value: Any, *, expected_root: str | None = None) -> dict[str, Any]:
    required = {"schema", "contract_id", "contract_version", "subject", "possibility", "axes", "constraints", "capabilities", "selection", "lowering", "evidence", "authority"}
    optional = {"description", "objectives", "preferred_regions", "adaptation", "revision", "root"}
    contract = _exact(value, required, optional, "RSC_SCHEMA_REFUSED")
    require(contract["schema"] == "mosaic.realization-space-contract.v0.1", "RSC_SCHEMA_REFUSED")
    _identifier(contract["contract_id"], "RSC_CONTRACT_ID_REFUSED")
    _text(contract["contract_version"], "RSC_CONTRACT_VERSION_REFUSED")
    require("description" not in contract or type(contract["description"]) is str, "RSC_SCHEMA_REFUSED")
    _validate_subject(contract)
    require(type(contract["axes"]) is list and bool(contract["axes"]), "RSC_AXES_REFUSED")
    axes = [_validate_axis(axis) for axis in contract["axes"]]
    require(len({axis["id"] for axis in axes}) == len(axes), "RSC_AXIS_DUPLICATE")
    axis_map = {axis["id"]: axis for axis in axes}
    require(type(contract["constraints"]) is list, "RSC_CONSTRAINTS_REFUSED")
    constraints = [_validate_constraint(item, axis_map) for item in contract["constraints"]]
    require(len({item["id"] for item in constraints}) == len(constraints), "RSC_CONSTRAINT_DUPLICATE")
    _validate_objectives(contract)
    require(contract.get("preferred_regions", []) == [], "RSC_PREFERRED_REGIONS_UNSUPPORTED")
    capabilities = _strings(contract["capabilities"], "RSC_CAPABILITY_UNSUPPORTED")
    require(set(capabilities) <= CAPABILITIES, "RSC_CAPABILITY_UNSUPPORTED")
    selection = _exact(contract["selection"], {"default_policy", "seed_required_for_non_unique"}, {"policies", "fallback_policy", "seed"}, "RSC_SELECTION_POLICY_REFUSED")
    policies = selection.get("policies", [selection["default_policy"]])
    _strings(policies, "RSC_SELECTION_POLICY_REFUSED", allow_empty=False)
    require(set(policies) <= SELECTION_POLICIES and selection["default_policy"] in policies, "RSC_SELECTION_POLICY_REFUSED")
    require(type(selection["seed_required_for_non_unique"]) is bool, "RSC_SELECTION_POLICY_REFUSED")
    require(selection.get("fallback_policy", "REFUSE") in {"REFUSE", "DECLARED_ONLY"}, "RSC_SELECTION_POLICY_REFUSED")
    require("seed" not in selection or (type(selection["seed"]) is int and selection["seed"] >= 0), "RSC_SELECTION_SEED_REFUSED")
    if selection["default_policy"] == "OBJECTIVE_PRIORITY":
        require(bool(contract.get("objectives", [])), "RSC_SELECTION_OBJECTIVES_REQUIRED")
    _validate_lowering_and_evidence(contract)
    authority = _exact(contract["authority"], {"standing", "authority_effect", "self_admission", "release_gate", "track_a_dependency"}, {"claim_boundary"}, "RSC_CLAIM_BOUNDARY_REFUSED")
    _text(authority["standing"], "RSC_CLAIM_BOUNDARY_REFUSED")
    require("claim_boundary" not in authority or type(authority["claim_boundary"]) is str, "RSC_CLAIM_BOUNDARY_REFUSED")
    require(authority["authority_effect"] == "NONE" and authority["self_admission"] is False and authority["release_gate"] is False and authority["track_a_dependency"] == "NONE", "RSC_CLAIM_BOUNDARY_REFUSED")
    if "adaptation" in contract:
        adaptation = _exact(contract["adaptation"], {"enabled", "policies"}, set(), "RSC_ADAPTATION_REFUSED")
        require(type(adaptation["enabled"]) is bool and adaptation["policies"] == [], "RSC_ADAPTATION_UNSUPPORTED")
    if "revision" in contract:
        revision = _exact(contract["revision"], set(), {"predecessor_root", "trigger_evidence_roots", "migration", "unresolved_questions"}, "RSC_REVISION_REFUSED")
        require("predecessor_root" not in revision or _root_value(revision["predecessor_root"]), "RSC_REVISION_REFUSED")
        require("migration" not in revision or type(revision["migration"]) is str, "RSC_REVISION_REFUSED")
        for key in ("trigger_evidence_roots", "unresolved_questions"):
            if key in revision:
                _strings(revision[key], "RSC_REVISION_REFUSED")
    computed = _body_root(contract)
    if "root" in contract:
        require(contract["root"] == computed, "RSC_CONTRACT_ROOT_REFUSED")
    if expected_root is not None:
        require(computed == expected_root, "RSC_CONTRACT_ROOT_REFUSED")
    canonical_bytes(contract)
    return {**deepcopy(contract), "root": computed}


def validate_configuration(contract: dict[str, Any], configuration: Any) -> dict[str, Any]:
    contract = validate_contract(contract)
    require(type(configuration) is dict, "RSC_AXIS_TYPE_REFUSED")
    by_id = {axis["id"]: axis for axis in contract["axes"]}
    require(set(configuration) == set(by_id), "RSC_AXIS_SET_REFUSED")
    for axis_id, candidate in configuration.items():
        require(_axis_valid(by_id[axis_id], candidate), "RSC_AXIS_DOMAIN_REFUSED", f"$.{axis_id}")
    checks = [
        {
            "constraint_id": item["id"],
            "severity": item["severity"],
            "status": "PASS" if _constraint_holds(item, configuration) else "FAIL",
            "refusal_code": item["refusal_code"],
        }
        for item in contract["constraints"]
    ]
    hard_ok = all(row["status"] == "PASS" for row in checks if row["severity"] == "HARD")
    body = {
        "schema": "mosaic.realization-configuration.v0.1",
        "contract_root": contract["root"],
        "configuration": deepcopy(configuration),
        "configuration_root": root(configuration),
        "constraint_checks": checks,
        "status": "PASS_ADMISSIBLE" if hard_ok else "REFUSED_INADMISSIBLE",
        "checked_semantics": ["AXIS_DOMAINS", "HARD_CONSTRAINTS"],
        "evidence_requirements": deepcopy(contract["evidence"]),
        **BOUNDARY,
    }
    return {**body, "root": root(body)}


def select_configuration(contract: dict[str, Any], candidates: Any) -> dict[str, Any]:
    contract = validate_contract(contract)
    require(type(candidates) is list and bool(candidates), "RSC_SELECTION_EMPTY")
    policy = contract["selection"]["default_policy"]
    objective_ids = {item["metric_id"] for item in contract.get("objectives", [])}
    evaluations = []
    for candidate in candidates:
        if type(candidate) is dict and set(candidate) == {"configuration", "metrics"}:
            configuration, metrics = candidate["configuration"], candidate["metrics"]
        else:
            configuration, metrics = candidate, {}
        if policy == "OBJECTIVE_PRIORITY":
            require(type(metrics) is dict and set(metrics) == objective_ids and all(type(value) is int for value in metrics.values()), "RSC_SELECTION_METRICS_REFUSED")
        else:
            require(metrics == {}, "RSC_SELECTION_METRICS_UNEXPECTED")
        checked = validate_configuration(contract, configuration)
        evaluations.append({
            "configuration": deepcopy(configuration),
            "configuration_root": checked["configuration_root"],
            "metrics": deepcopy(metrics),
            "check_root": checked["root"],
            "status": checked["status"],
        })
    evaluations.sort(key=lambda row: (row["configuration_root"], root(row["metrics"])))
    require(len({(row["configuration_root"], root(row["metrics"])) for row in evaluations}) == len(evaluations), "RSC_SELECTION_DUPLICATE_CANDIDATE")
    admissible = [row for row in evaluations if row["status"] == "PASS_ADMISSIBLE"]
    require(bool(admissible), "RSC_SELECTION_EMPTY")
    objective_order: list[str] = []
    if policy == "EXACT_DEFAULTS":
        defaults = {axis["id"]: axis["default"] for axis in contract["axes"]}
        matches = [row for row in admissible if row["configuration"] == defaults]
        require(len(matches) == 1, "RSC_EXACT_DEFAULTS_UNAVAILABLE")
        selected = matches[0]
    elif policy == "LEXICOGRAPHIC_CONFIGURATION_ROOT":
        selected = min(admissible, key=lambda row: row["configuration_root"])
    else:
        objectives = sorted(contract["objectives"], key=lambda item: (-item["priority"], item["metric_id"]))
        objective_order = [item["metric_id"] for item in objectives]

        def score(row: dict[str, Any]) -> tuple[int, ...]:
            return tuple(row["metrics"][item["metric_id"]] * (-1 if item["direction"] == "MAXIMIZE" else 1) for item in objectives)

        best = min(score(row) for row in admissible)
        ties = sorted((row for row in admissible if score(row) == best), key=lambda row: row["configuration_root"])
        if len(ties) > 1 and contract["selection"]["seed_required_for_non_unique"]:
            require("seed" in contract["selection"], "RSC_SELECTION_SEED_REQUIRED")
            selected = ties[contract["selection"]["seed"] % len(ties)]
        else:
            selected = ties[0]
    body = {
        "schema": "mosaic.realization-selection.v0.1",
        "contract_root": contract["root"],
        "policy": policy,
        "candidate_set_root": root(evaluations),
        "evaluations": evaluations,
        "objective_order": objective_order,
        "selected_configuration": selected["configuration"],
        "selected_configuration_root": selected["configuration_root"],
        "status": "PASS_SELECTED",
        **BOUNDARY,
    }
    return {**body, "root": root(body)}


def project_to_ucl_tessera(contract: dict[str, Any]) -> dict[str, Any]:
    contract = validate_contract(contract)
    body = {
        "schema": "mosaic.ucl-tessera.realization-projection.v0.1",
        "contract_root": contract["root"],
        "ucl_hard_obligations": [
            {"obligation_id": item["id"], "constraint": deepcopy(item), "subject_root": root(contract["subject"])}
            for item in contract["constraints"] if item["severity"] == "HARD"
        ],
        "tessera_preferences": deepcopy(contract.get("objectives", [])),
        "correspondence": "VERSIONED_PUBLIC_ADAPTER; RETAINED_LANGUAGE_SEMANTICS_UNCHANGED",
        "non_claims": ["NOT_A_COMPILATION", "NOT_A_PRESERVATION_PROOF", "NOT_TARGET_EXECUTION"],
        **BOUNDARY,
    }
    return {**body, "root": root(body)}


def trace_preservation(contract: dict[str, Any], before: Any, after: Any) -> dict[str, Any]:
    contract = validate_contract(contract)
    first, second = validate_configuration(contract, before), validate_configuration(contract, after)
    changed = sorted(axis["id"] for axis in contract["axes"] if before[axis["id"]] != after[axis["id"]])
    frozen = sorted(axis["id"] for axis in contract["axes"] if axis["mutability"] == "FROZEN" and axis["id"] in changed)
    status = "PASS_PRESERVED" if second["status"] == "PASS_ADMISSIBLE" and not frozen else "REFUSED_NOT_PRESERVED"
    body = {
        "schema": "mosaic.realization-preservation.v0.1",
        "contract_root": contract["root"],
        "before_check_root": first["root"],
        "after_check_root": second["root"],
        "changed_axes": changed,
        "frozen_axis_violations": frozen,
        "preserved_subject_identity": deepcopy(contract["subject"]["preserved_identity"]),
        "non_claims": ["NOT_AN_IMPLEMENTATION_SEMANTICS_PROOF", "NOT_A_COMPILER_PROOF"],
        "status": status,
        **BOUNDARY,
    }
    return {**body, "root": root(body)}

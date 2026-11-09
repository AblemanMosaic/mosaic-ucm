"""Pure authoring aids for UCM realization and AMCAS contracts."""
from __future__ import annotations

from copy import deepcopy
from itertools import product
from typing import Any

from uclop.canonical import exact_keys, require, root

from .amcas import BOUNDARY, validate_contract as validate_amcas_contract
from .realization import validate_configuration, validate_contract as validate_realization_contract


def _issue(code: str, severity: str, path: str, explanation: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "path": path,
            "explanation": explanation}


def _finite_domain(axis: dict[str, Any]) -> list[Any] | None:
    kind = axis["value_type"]
    if kind == "BOOLEAN":
        return [False, True]
    if kind == "ENUM":
        return list(axis["domain"]["values"])
    if kind == "INTEGER":
        low, high = axis["domain"]["minimum"], axis["domain"]["maximum"]
        step = axis["domain"].get("step", 1)
        values = list(range(low, high + 1, step))
        return values if len(values) <= 16 else None
    return None


def lint_realization_contract(value: Any) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    try:
        contract = validate_realization_contract(value)
    except Exception as error:
        issues.append(_issue(getattr(error, "code", type(error).__name__), "ERROR", "$",
                             str(error)))
        body = {"schema": "mosaic.ucm.contract-lint.v0.1", "contract_kind": "REALIZATION",
                "contract_root": None, "complexity": None, "issues": issues,
                "status": "REFUSED_INVALID", **BOUNDARY}
        return {**body, "lint_root": root(body)}

    axes = contract["axes"]
    referenced = set()
    for constraint in contract["constraints"]:
        terms = constraint["terms"]
        if "axis" in terms:
            referenced.add(terms["axis"])
        if "if" in terms:
            referenced.update((terms["if"]["axis"], terms["then"]["axis"]))
        if "assignments" in terms:
            referenced.update(terms["assignments"])
    for axis in axes:
        if axis["id"] not in referenced:
            issues.append(_issue("RSC_LINT_UNCONSTRAINED_AXIS", "WARNING",
                                 f"$.axes[{axis['id']}]",
                                 "Axis does not participate in any declared constraint."))
    hard = [row for row in contract["constraints"] if row["severity"] == "HARD"]
    if not hard:
        issues.append(_issue("RSC_LINT_NO_HARD_CONSTRAINTS", "ERROR", "$.constraints",
                             "CM1-style admissibility cannot be established without a hard constraint."))
    codes = [row["refusal_code"] for row in contract["constraints"]]
    if len(codes) != len(set(codes)):
        issues.append(_issue("RSC_LINT_REFUSAL_CODE_REUSED", "WARNING", "$.constraints",
                             "Multiple constraints share a refusal code and may be hard to diagnose."))
    evidence = contract["evidence"]
    if not evidence["required_roots"] and not evidence["required_fields"]:
        issues.append(_issue("RSC_LINT_EMPTY_EVIDENCE_CONTRACT", "ERROR", "$.evidence",
                             "The contract has no rooted or field-level evidence requirement."))

    domains = [_finite_domain(axis) for axis in axes]
    combinations = 1
    for domain in domains:
        combinations *= len(domain) if domain is not None else 257
    if all(domain is not None for domain in domains) and combinations <= 256:
        admissible = 0
        for values in product(*domains):
            configuration = {axis["id"]: value for axis, value in zip(axes, values)}
            if validate_configuration(contract, configuration)["status"] == "PASS_ADMISSIBLE":
                admissible += 1
        if admissible == 0:
            issues.append(_issue("RSC_LINT_UNSATISFIABLE", "ERROR", "$.constraints",
                                 "No configuration in the finite contract domain is admissible."))
        elif hard and admissible == combinations:
            issues.append(_issue("RSC_LINT_HARD_CONSTRAINTS_VACUOUS", "ERROR", "$.constraints",
                                 "Every finite-domain configuration passes the hard constraints."))

    complexity = {
        "axes": len(axes), "constraints": len(contract["constraints"]),
        "hard_constraints": len(hard), "objectives": len(contract.get("objectives", [])),
        "lowering_targets": len(contract["lowering"]["targets"]),
    }
    complexity["score"] = (complexity["axes"] * 2 + complexity["constraints"] * 3
                           + complexity["objectives"] * 2 + complexity["lowering_targets"])
    complexity["band"] = "LOW" if complexity["score"] <= 20 else (
        "MEDIUM" if complexity["score"] <= 60 else "HIGH")
    body = {"schema": "mosaic.ucm.contract-lint.v0.1", "contract_kind": "REALIZATION",
            "contract_root": contract["root"], "complexity": complexity,
            "issues": sorted(issues, key=lambda row: (row["severity"], row["code"], row["path"])),
            "status": "PASS" if not any(row["severity"] == "ERROR" for row in issues)
            else "REFUSED_SEMANTIC_LINT", **BOUNDARY}
    return {**body, "lint_root": root(body)}


def lint_amcas_contract(value: Any) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    try:
        contract = validate_amcas_contract(value)
    except Exception as error:
        issues.append(_issue(getattr(error, "code", type(error).__name__), "ERROR", "$", str(error)))
        body = {"schema": "mosaic.ucm.contract-lint.v0.1", "contract_kind": "AMCAS",
                "contract_root": None, "complexity": None, "issues": issues,
                "status": "REFUSED_INVALID", **BOUNDARY}
        return {**body, "lint_root": root(body)}
    requirements = contract["cm1"]["requirements"]
    required = [row for row in requirements if row["applicability"] == "REQUIRED"]
    if not required:
        issues.append(_issue("AMCAS_LINT_NO_REQUIRED_CM1", "ERROR", "$.cm1.requirements",
                             "The contract has no required CM1 obligation."))
    if any(row["subject_root"] != contract["subject"]["source_root"]
           and row["evidence_required"] is False for row in required):
        issues.append(_issue("AMCAS_LINT_UNBOUND_REQUIREMENT_WITHOUT_EVIDENCE", "ERROR",
                             "$.cm1.requirements",
                             "A required obligation targets another subject without evidence."))
    if not contract["acceptance"]:
        issues.append(_issue("AMCAS_LINT_NO_ACCEPTANCE", "ERROR", "$.acceptance",
                             "No acceptance evidence is defined."))
    complexity = {"cm1_requirements": len(requirements),
                  "cm2_preferences": len(contract["cm2"]["preferences"]),
                  "capabilities": len(contract["capabilities"]),
                  "effects": len(contract["effects"]),
                  "acceptance": len(contract["acceptance"])}
    complexity["score"] = sum(complexity.values())
    complexity["band"] = "LOW" if complexity["score"] <= 20 else (
        "MEDIUM" if complexity["score"] <= 60 else "HIGH")
    body = {"schema": "mosaic.ucm.contract-lint.v0.1", "contract_kind": "AMCAS",
            "contract_root": contract["contract_root"], "complexity": complexity,
            "issues": sorted(issues, key=lambda row: (row["severity"], row["code"], row["path"])),
            "status": "PASS" if not any(row["severity"] == "ERROR" for row in issues)
            else "REFUSED_SEMANTIC_LINT", **BOUNDARY}
    return {**body, "lint_root": root(body)}


def _flatten(value: Any, path: str = "$") -> dict[str, Any]:
    if type(value) is dict:
        rows: dict[str, Any] = {}
        for key in sorted(value):
            rows.update(_flatten(value[key], f"{path}.{key}"))
        return rows
    if type(value) is list:
        rows = {}
        for index, item in enumerate(value):
            rows.update(_flatten(item, f"{path}[{index}]"))
        return rows
    return {path: value}


def semantic_contract_diff(before: Any, after: Any) -> dict[str, Any]:
    require(type(before) is dict and type(after) is dict, "UCM_CONTRACT_DIFF_INPUT_INVALID")
    left, right = _flatten(before), _flatten(after)
    changes = []
    for path in sorted(set(left) | set(right)):
        if left.get(path) == right.get(path) and path in left and path in right:
            continue
        if any(token in path for token in ("authority", "ceiling", "standing", "effect_class")):
            classification = "AUTHORITY_ADJACENT"
        elif any(token in path for token in ("cm1", "constraint", "evidence", "acceptance")):
            classification = "ADMISSIBILITY"
        elif any(token in path for token in ("cm2", "objective", "selection")):
            classification = "PREFERENCE"
        else:
            classification = "STRUCTURAL"
        changes.append({"path": path, "before": left.get(path), "after": right.get(path),
                        "classification": classification})
    body = {"schema": "mosaic.ucm.semantic-contract-diff.v0.1",
            "before_root": root(before), "after_root": root(after), "changes": changes,
            "change_counts": {name: sum(row["classification"] == name for row in changes)
                              for name in ("AUTHORITY_ADJACENT", "ADMISSIBILITY", "PREFERENCE", "STRUCTURAL")},
            "status": "IDENTICAL" if not changes else "CHANGED", **BOUNDARY}
    return {**body, "diff_root": root(body)}


def validate_policy_pack(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "pack_id", "version", "requirements", "pack_root"})
    require(item["schema"] == "mosaic.ucm.amcas-policy-pack.v0.1",
            "UCM_POLICY_PACK_SCHEMA_INVALID")
    require(type(item["pack_id"]) is str and item["pack_id"]
            and type(item["version"]) is str and item["version"], "UCM_POLICY_PACK_ID_INVALID")
    require(type(item["requirements"]) is list and bool(item["requirements"]),
            "UCM_POLICY_PACK_EMPTY")
    ids = []
    for requirement in item["requirements"]:
        row = exact_keys(requirement, {"id", "kind", "statement", "verifier",
                                       "evidence_required", "applicability"})
        ids.append(row["id"])
        require(all(type(row[key]) is str and row[key] for key in
                    ("id", "kind", "statement", "verifier", "applicability"))
                and type(row["evidence_required"]) is bool,
                "UCM_POLICY_PACK_REQUIREMENT_INVALID")
    require(len(ids) == len(set(ids)), "UCM_POLICY_PACK_REQUIREMENT_DUPLICATE")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "pack_root"}
    require(item["pack_root"] == root(body), "UCM_POLICY_PACK_ROOT_INVALID")
    return deepcopy(item)


def apply_policy_packs(contract: Any, packs: list[Any]) -> dict[str, Any]:
    validated = validate_amcas_contract(contract)
    require(type(packs) is list and bool(packs), "UCM_POLICY_PACKS_INVALID")
    result = deepcopy(validated)
    current = {row["id"] for row in result["cm1"]["requirements"]}
    applied = []
    for raw in packs:
        pack = validate_policy_pack(raw)
        for template in pack["requirements"]:
            require(template["id"] not in current, "UCM_POLICY_PACK_COLLISION")
            current.add(template["id"])
            result["cm1"]["requirements"].append({**deepcopy(template),
                                                    "subject_root": result["subject"]["source_root"]})
        applied.append(pack["pack_root"])
    result["cm1"]["requirements"].sort(key=lambda row: row["id"])
    result["contract_root"] = root({key: raw for key, raw in result.items()
                                    if key != "contract_root"})
    validated_result = validate_amcas_contract(result)
    body = {"schema": "mosaic.ucm.policy-pack-application.v0.1",
            "predecessor_contract_root": validated["contract_root"],
            "policy_pack_roots": applied, "contract": validated_result,
            "status": "PASS_APPLIED", **BOUNDARY}
    return {**body, "application_root": root(body)}


def inspect_policy_pack_composition(packs: list[Any]) -> dict[str, Any]:
    """Report cross-pack ID conflicts before a contract is modified."""
    require(type(packs) is list and bool(packs), "UCM_POLICY_PACKS_INVALID")
    validated = [validate_policy_pack(value) for value in packs]
    by_id: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for pack in validated:
        for requirement in pack["requirements"]:
            by_id.setdefault(requirement["id"], []).append(
                (pack["pack_root"], requirement))
    duplicates, conflicts = [], []
    for requirement_id, rows in sorted(by_id.items()):
        if len(rows) < 2:
            continue
        roots = {root(requirement) for _, requirement in rows}
        record = {"requirement_id": requirement_id,
                  "pack_roots": [pack_root for pack_root, _ in rows],
                  "requirement_roots": sorted(roots)}
        (duplicates if len(roots) == 1 else conflicts).append(record)
    body = {
        "schema": "mosaic.ucm.policy-pack-composition-check.v0.1",
        "pack_roots": [pack["pack_root"] for pack in validated],
        "identical_duplicates": duplicates, "conflicts": conflicts,
        "status": "PASS_COMPOSABLE" if not conflicts else "REFUSED_POLICY_CONFLICT",
        **BOUNDARY,
    }
    return {**body, "composition_root": root(body)}

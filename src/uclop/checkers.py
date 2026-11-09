from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import exact_keys, require, root
from .eligibility import verify_result
from .proofs import check as check_proof
from .deductive_proofs import evidence_subject as deductive_evidence_subject, verify_proof as verify_deductive_proof


CHECKER_SPECS = {
    "EXACT_PROPOSITIONAL_PROOF_V1": {
        "evidence_kind": "PROPOSITIONAL_PROOF",
        "dispositions": ["DISCHARGED"],
        "implementation": "uclop.checkers:_check_propositional_proof",
    },
    "EXACT_ELIGIBILITY_WITNESS_V1": {
        "evidence_kind": "ELIGIBILITY_WITNESS",
        "dispositions": ["DISCHARGED"],
        "implementation": "uclop.checkers:_check_eligibility_witness",
    },
    "EXACT_REPLACEMENT_DOMINANCE_V1": {
        "evidence_kind": "OBLIGATION_REPLACEMENT_DOMINANCE",
        "dispositions": ["REPLACED"],
        "implementation": "uclop.checkers:_check_replacement_dominance",
    },
    "EXACT_NATIVE_DEDUCTIVE_PROOF_V1": {
        "evidence_kind": "NATIVE_DEDUCTIVE_PROOF",
        "dispositions": ["DISCHARGED"],
        "implementation": "uclop.checkers:_check_native_deductive_proof",
    },
}
CHECKER_REGISTRY = {
    checker_id: {**spec, "checker_root": root({"checker_id": checker_id, **spec})}
    for checker_id, spec in sorted(CHECKER_SPECS.items())
}
CHECKER_REGISTRY_ROOT = root(CHECKER_REGISTRY)


def _check_propositional_proof(payload: Any) -> dict[str, Any]:
    item = exact_keys(payload, {"formula", "proof"}, "$.evidence.payload")
    checked = check_proof(item["formula"], item["proof"])
    require(checked["valid"] is True, "EVIDENCE_PROOF_NOT_VALID")
    return {
        "checker_result": checked,
        "checked_material_roots": [root(item["formula"]), item["proof"]["proof_root"]],
        "evidence_subject": {"kind": "PROPOSITIONAL_FORMULA", "formula_root": root(item["formula"])},
    }


def _check_eligibility_witness(payload: Any) -> dict[str, Any]:
    item = exact_keys(payload, {"problem", "result", "required_outcome"}, "$.evidence.payload")
    require(type(item["required_outcome"]) is bool, "EVIDENCE_REQUIRED_OUTCOME_INVALID")
    checked = verify_result(item["problem"], item["result"])
    require(item["result"]["eligible"] is item["required_outcome"], "EVIDENCE_OUTCOME_MISMATCH")
    return {
        "checker_result": checked,
        "checked_material_roots": [root(item["problem"]), item["result"]["result_root"]],
        "evidence_subject": {
            "kind": "ELIGIBILITY_DECISION",
            "problem_root": root(item["problem"]),
            "required_outcome": item["required_outcome"],
        },
    }


def _check_native_deductive_proof(payload: Any) -> dict[str, Any]:
    item = exact_keys(payload, {"contract", "proof_bundle"}, "$.evidence.payload")
    checked = verify_deductive_proof(item["contract"], item["proof_bundle"])
    require(checked["outcome"] == "PROVED", "EVIDENCE_DEDUCTIVE_PROOF_NOT_UNCONDITIONAL")
    return {
        "checker_result": checked,
        "checked_material_roots": [item["contract"]["contract_root"], item["proof_bundle"]["proof_bundle_root"]],
        "evidence_subject": deductive_evidence_subject(item["contract"]),
    }


_SEVERITY = {"LOW": 0, "MED": 1, "HIGH": 2, "CRITICAL": 3}


def _check_replacement_dominance(
    payload: Any,
    source_obligation: dict[str, Any],
    target_obligations: list[dict[str, Any]],
) -> dict[str, Any]:
    item = exact_keys(payload, {"rationale", "policy"}, "$.evidence.payload")
    require(item["policy"] == "NO_WEAKENING_EXACT_SEMANTICS_V1", "REPLACEMENT_POLICY_UNSUPPORTED")
    require(type(item["rationale"]) is str and item["rationale"], "REPLACEMENT_RATIONALE_INVALID")
    require(bool(target_obligations), "REPLACEMENT_TARGET_REQUIRED")
    required = set(source_obligation["required_evidence"])
    assumptions = set(source_obligation["assumptions"])
    for target in target_obligations:
        require(target["kind"] == source_obligation["kind"], "REPLACEMENT_KIND_WEAKENED")
        require(target["statement"] == source_obligation["statement"], "REPLACEMENT_STATEMENT_WEAKENED")
        require(set(target["assumptions"]) == assumptions, "REPLACEMENT_ASSUMPTIONS_CHANGED")
        require(set(target["required_evidence"]) >= required, "REPLACEMENT_EVIDENCE_WEAKENED")
        require(_SEVERITY[target["severity"]] >= _SEVERITY[source_obligation["severity"]], "REPLACEMENT_SEVERITY_WEAKENED")
        require(target.get("evidence_subject") == source_obligation.get("evidence_subject"), "REPLACEMENT_EVIDENCE_SUBJECT_CHANGED")
    return {
        "checker_result": {
            "status": "PASS_DOMINANCE",
            "source_obligation_root": root(source_obligation),
            "target_obligation_roots": [root(item) for item in target_obligations],
        },
        "checked_material_roots": [root(source_obligation), *[root(item) for item in target_obligations]],
        "evidence_subject": {
            "kind": "OBLIGATION_REPLACEMENT",
            "source_obligation_id": source_obligation["id"],
            "target_obligation_ids": sorted(item["id"] for item in target_obligations),
            "policy": item["policy"],
        },
    }


def make_evidence_material(
    checker_id: str,
    *,
    obligation_id: str,
    disposition: str,
    source_inventory_root: str,
    target_inventory_root: str,
    target_obligation_ids: list[str],
    evidence_subject: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    body = {
        "schema": "ucl.op.transformation_evidence.v1",
        "checker_id": checker_id,
        "obligation_id": obligation_id,
        "disposition": disposition,
        "source_inventory_root": source_inventory_root,
        "target_inventory_root": target_inventory_root,
        "target_obligation_ids": sorted(target_obligation_ids),
        "evidence_subject": deepcopy(evidence_subject),
        "payload": deepcopy(payload),
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "evidence_root": root(body)}


def evaluate_evidence(
    material: Any,
    *,
    source_inventory_root: str,
    target_inventory_root: str,
    source_obligation: dict[str, Any],
    target_obligations: list[dict[str, Any]],
    disposition: str,
) -> dict[str, Any]:
    item = exact_keys(
        material,
        {
            "schema",
            "checker_id",
            "obligation_id",
            "disposition",
            "source_inventory_root",
            "target_inventory_root",
            "target_obligation_ids",
            "evidence_subject",
            "payload",
            "standing",
            "authority_effect",
            "evidence_root",
        },
        "$.evidence",
    )
    require(item["schema"] == "ucl.op.transformation_evidence.v1", "TRANSFORMATION_EVIDENCE_SCHEMA_INVALID")
    require(item["checker_id"] in CHECKER_REGISTRY, "TRANSFORMATION_CHECKER_UNKNOWN")
    require(item["obligation_id"] == source_obligation["id"], "TRANSFORMATION_EVIDENCE_SUBJECT_MISMATCH")
    require(item["disposition"] == disposition, "TRANSFORMATION_EVIDENCE_DISPOSITION_MISMATCH")
    require(item["source_inventory_root"] == source_inventory_root, "TRANSFORMATION_EVIDENCE_SOURCE_MISMATCH")
    require(item["target_inventory_root"] == target_inventory_root, "TRANSFORMATION_EVIDENCE_TARGET_MISMATCH")
    require(item["target_obligation_ids"] == sorted(target["id"] for target in target_obligations), "TRANSFORMATION_EVIDENCE_TARGET_IDS_MISMATCH")
    require(item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "TRANSFORMATION_EVIDENCE_EFFECT_FORBIDDEN")
    expected_root = root({key: value for key, value in item.items() if key != "evidence_root"})
    require(item["evidence_root"] == expected_root, "TRANSFORMATION_EVIDENCE_ROOT_MISMATCH")
    spec = CHECKER_REGISTRY[item["checker_id"]]
    require(disposition in spec["dispositions"], "TRANSFORMATION_CHECKER_DISPOSITION_UNSUPPORTED")
    require(spec["evidence_kind"] in source_obligation["required_evidence"], "TRANSFORMATION_CHECKER_NOT_REQUIRED")
    if item["checker_id"] == "EXACT_PROPOSITIONAL_PROOF_V1":
        observed = _check_propositional_proof(item["payload"])
    elif item["checker_id"] == "EXACT_ELIGIBILITY_WITNESS_V1":
        observed = _check_eligibility_witness(item["payload"])
    elif item["checker_id"] == "EXACT_REPLACEMENT_DOMINANCE_V1":
        observed = _check_replacement_dominance(item["payload"], source_obligation, target_obligations)
    elif item["checker_id"] == "EXACT_NATIVE_DEDUCTIVE_PROOF_V1":
        observed = _check_native_deductive_proof(item["payload"])
    else:  # pragma: no cover - registry and dispatch are intentionally closed together.
        raise AssertionError("CHECKER_REGISTRY_DISPATCH_DIVERGED")
    require(item["evidence_subject"] == observed["evidence_subject"], "TRANSFORMATION_EVIDENCE_SUBJECT_MISMATCH")
    evidence_subject_root = root(observed["evidence_subject"])
    if disposition == "DISCHARGED":
        require(source_obligation.get("evidence_subject") == observed["evidence_subject"], "OBLIGATION_EVIDENCE_SUBJECT_MISMATCH")
    body = {
        "schema": "ucl.op.obligation_evidence_receipt.v3",
        "checker_id": item["checker_id"],
        "checker_root": spec["checker_root"],
        "checker_registry_root": CHECKER_REGISTRY_ROOT,
        "evidence_root": item["evidence_root"],
        "obligation_id": source_obligation["id"],
        "disposition": disposition,
        "source_inventory_root": source_inventory_root,
        "target_inventory_root": target_inventory_root,
        "target_obligation_ids": sorted(target["id"] for target in target_obligations),
        "evidence_subject_root": evidence_subject_root,
        "checked_material_roots": observed["checked_material_roots"],
        "checker_result_root": root(observed["checker_result"]),
        "status": "PASS_CHECKED",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "receipt_root": root(body)}

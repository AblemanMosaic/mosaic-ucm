"""Anchored Stage I4 preparation for the c4 successor.

The c4 surface keeps execution authority outside UCM.  Every run contract is
bound to an externally supplied trust-anchor root and to an authority policy
whose only accepted state in this release is ``NOT_GRANTED``.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY
from .native_runner import validate_binding
from .stage4_c3 import (
    build_run_contract as build_c3_run_contract,
    validate_execution_context,
    validate_review_policy,
)


TRUST_ANCHORS_SCHEMA = "mosaic.ucm.stage-i4-trust-anchors.v0.1"
AUTHORITY_POLICY_SCHEMA = "mosaic.ucm.stage-i4-execution-authority-policy.v0.1"
RUN_CONTRACT_SCHEMA = "mosaic.ucm.stage-i4-run-contract.v0.4"


def _identifier(value: Any, code: str) -> str:
    require(type(value) is str and value == value.strip() and 0 < len(value) <= 192
            and all(ch.isalnum() or ch in "._:-" for ch in value), code)
    return value


def validate_authority_policy(value: Any, *, expected_root: str) -> dict[str, Any]:
    """Validate the externally pinned, authority-none policy for c4."""
    item = exact_keys(value, {
        "schema", "policy_id", "jurisdiction_root", "generation",
        "execution_authorized", "allowed_effect_classes", "reason_code",
        "standing", "authority_effect", "real_a5", "g0",
        "authority_policy_root",
    })
    require(item["schema"] == AUTHORITY_POLICY_SCHEMA,
            "STAGE_I4_AUTHORITY_POLICY_SCHEMA_INVALID")
    _identifier(item["policy_id"], "STAGE_I4_AUTHORITY_POLICY_ID_INVALID")
    require_root(item["jurisdiction_root"])
    require(type(item["generation"]) is int and item["generation"] >= 1,
            "STAGE_I4_AUTHORITY_POLICY_GENERATION_INVALID")
    require(item["execution_authorized"] is False
            and item["allowed_effect_classes"] == []
            and item["reason_code"] == "EXECUTION_AUTHORITY_NOT_GRANTED",
            "STAGE_I4_AUTHORITY_POLICY_CEILING_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_AUTHORITY_CEILING_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items()
            if key != "authority_policy_root"}
    require(item["authority_policy_root"] == root(body)
            and item["authority_policy_root"] == require_root(expected_root),
            "STAGE_I4_AUTHORITY_POLICY_ROOT_INVALID")
    return deepcopy(item)


def validate_trust_anchors(value: Any, *, expected_root: str) -> dict[str, Any]:
    """Validate anchors against an expected root supplied outside the object."""
    item = exact_keys(value, {
        "schema", "anchor_id", "review_policy_root", "execution_context_root",
        "native_runner_binding_root", "native_runner_source_sha256",
        "native_runner_source_manifest_root", "authority_policy_root",
        "jurisdiction_root", "standing", "authority_effect", "real_a5", "g0",
        "trust_anchors_root",
    })
    require(item["schema"] == TRUST_ANCHORS_SCHEMA,
            "STAGE_I4_TRUST_ANCHORS_SCHEMA_INVALID")
    _identifier(item["anchor_id"], "STAGE_I4_TRUST_ANCHORS_ID_INVALID")
    for key in ("review_policy_root", "execution_context_root",
                "native_runner_binding_root", "native_runner_source_sha256",
                "native_runner_source_manifest_root", "authority_policy_root",
                "jurisdiction_root"):
        require_root(item[key])
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_AUTHORITY_CEILING_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items()
            if key != "trust_anchors_root"}
    require(item["trust_anchors_root"] == root(body)
            and item["trust_anchors_root"] == require_root(expected_root),
            "STAGE_I4_TRUST_ANCHORS_ROOT_INVALID")
    return deepcopy(item)


def _c3_view(contract: dict[str, Any]) -> dict[str, Any]:
    """Return the legacy semantic body for compatibility validation."""
    body = {key: deepcopy(value) for key, value in contract.items()
            if key not in {"run_contract_root", "trust_anchors",
                           "execution_authority_policy"}}
    body["schema"] = "mosaic.ucm.stage-i4-run-contract.v0.3"
    return {**body, "run_contract_root": root(body)}


def validate_run_contract(value: Any, *, expected_trust_anchors_root: str) -> dict[str, Any]:
    from .stage4_semantics import validate_run_contract_shape as validate_c3_shape

    item = exact_keys(value, {
        "schema", "application_id", "eligibility_root", "instruction_root",
        "plan_root", "review_policy_root", "review_archive_sha256",
        "relation_case_map_root", "case_selection", "case_schedule",
        "execution_context", "native_runner_binding", "effect_membrane",
        "gate_requirements", "mode", "application_contact_authorized",
        "execution_authorized", "composition_authorized", "trust_anchors",
        "execution_authority_policy", "standing", "authority_effect",
        "real_a5", "g0", "run_contract_root",
    })
    require(item["schema"] == RUN_CONTRACT_SCHEMA,
            "STAGE_I4_RUN_CONTRACT_SCHEMA_INVALID")
    require(item["run_contract_root"] == root({
        key: deepcopy(raw) for key, raw in item.items()
        if key != "run_contract_root"
    }), "STAGE_I4_RUN_CONTRACT_ROOT_INVALID")
    anchors = validate_trust_anchors(item["trust_anchors"],
                                     expected_root=expected_trust_anchors_root)
    policy = validate_authority_policy(
        item["execution_authority_policy"],
        expected_root=anchors["authority_policy_root"],
    )
    validate_c3_shape(_c3_view(item))
    context = validate_execution_context(item["execution_context"])
    binding = validate_binding(item["native_runner_binding"])
    require(item["review_policy_root"] == anchors["review_policy_root"]
            and context["context_root"] == anchors["execution_context_root"]
            and context["jurisdiction_root"] == anchors["jurisdiction_root"]
            and binding["binding_root"] == anchors["native_runner_binding_root"]
            and policy["jurisdiction_root"] == anchors["jurisdiction_root"]
            and binding["source_sha256"] == anchors["native_runner_source_sha256"]
            and binding["source_manifest_root"] == anchors["native_runner_source_manifest_root"]
            and policy["execution_authorized"] is False,
            "STAGE_I4_RUN_CONTRACT_TRUST_BINDING_INVALID")
    return deepcopy(item)


def build_run_contract(*, eligibility: Any, plan: Any, instruction: Any,
                       review_archive: bytes, review_policy: Any,
                       relation_case_map: Any, execution_context: Any,
                       native_runner_binding: Any, selection: Any,
                       trust_anchors: Any, expected_trust_anchors_root: str,
                       execution_authority_policy: Any) -> dict[str, Any]:
    """Build the c4 contract by rederiving c3 semantics and adding anchors."""
    policy = validate_review_policy(review_policy)
    context = validate_execution_context(execution_context)
    binding = validate_binding(native_runner_binding)
    anchors = validate_trust_anchors(trust_anchors,
                                     expected_root=expected_trust_anchors_root)
    authority = validate_authority_policy(
        execution_authority_policy,
        expected_root=anchors["authority_policy_root"],
    )
    require(policy["policy_root"] == anchors["review_policy_root"]
            and context["context_root"] == anchors["execution_context_root"]
            and context["jurisdiction_root"] == anchors["jurisdiction_root"]
            and authority["jurisdiction_root"] == anchors["jurisdiction_root"]
            and binding["binding_root"] == anchors["native_runner_binding_root"]
            and binding["source_sha256"] == anchors["native_runner_source_sha256"]
            and binding["source_manifest_root"] == anchors["native_runner_source_manifest_root"],
            "STAGE_I4_TRUST_INPUT_MISMATCH")
    legacy = build_c3_run_contract(
        eligibility=eligibility, plan=plan, instruction=instruction,
        review_archive=review_archive, review_policy=policy,
        relation_case_map=relation_case_map, execution_context=context,
        native_runner_binding=binding, selection=selection,
    )
    body = {key: deepcopy(raw) for key, raw in legacy.items()
            if key != "run_contract_root"}
    body["schema"] = RUN_CONTRACT_SCHEMA
    body["trust_anchors"] = anchors
    body["execution_authority_policy"] = authority
    contract = {**body, "run_contract_root": root(body)}
    return validate_run_contract(
        contract, expected_trust_anchors_root=expected_trust_anchors_root)


def build_terminal_refusal(*, run_contract: Any,
                           expected_trust_anchors_root: str) -> dict[str, Any]:
    """Build a complete, cross-linked G1/G2/G3 refusal operation."""
    from .native_runner_c4 import build_preflight

    contract = validate_run_contract(
        run_contract, expected_trust_anchors_root=expected_trust_anchors_root)
    preflight = build_preflight(
        run_contract=contract, trust_anchors=contract["trust_anchors"],
        expected_trust_anchors_root=expected_trust_anchors_root,
        execution_authority_policy=contract["execution_authority_policy"],
    )
    require(preflight["decision"] == "REFUSE",
            "STAGE_I4_REFUSAL_PREFLIGHT_INVALID")
    g1_body = {
        "schema": "mosaic.ucm.integration-g1-receipt.v0.1",
        "gate": "G1_SENTINEL",
        "run_contract_root": contract["run_contract_root"],
        "context_root": contract["execution_context"]["context_root"],
        "trust_anchors_root": contract["trust_anchors"]["trust_anchors_root"],
        "preflight_root": preflight["preflight_root"],
        "decision": "REFUSE", "reason_codes": [preflight["reason_code"]],
        **BOUNDARY,
    }
    g1 = {**g1_body, "receipt_root": root(g1_body)}
    g2_body = {
        "schema": "mosaic.ucm.integration-g2-receipt.v0.1",
        "gate": "G2_WITNESS", "run_contract_root": contract["run_contract_root"],
        "g1_root": g1["receipt_root"], "dispatch_root": None,
        "native_receipt_root": None, "completion_status": "REFUSED",
        "recovery_status": "NOT_REQUIRED", "case_results": [],
        "observed_effect_classes": [], **BOUNDARY,
    }
    g2 = {**g2_body, "receipt_root": root(g2_body)}
    g3_body = {
        "schema": "mosaic.ucm.integration-g3-receipt.v0.1",
        "gate": "G3_DIAGNOSTIC", "run_contract_root": contract["run_contract_root"],
        "g2_root": g2["receipt_root"], "classification": "REFUSED",
        "finding_codes": [preflight["reason_code"]],
        "next_action": "ESTABLISH_EXTERNAL_AUTHORITY_AND_PINNED_NATIVE_BINDING",
        **BOUNDARY,
    }
    g3 = {**g3_body, "receipt_root": root(g3_body)}
    body = {
        "schema": "mosaic.ucm.stage-i4-terminal-operation.v0.2",
        "run_contract_root": contract["run_contract_root"],
        "trust_anchors_root": contract["trust_anchors"]["trust_anchors_root"],
        "execution_context_root": contract["execution_context"]["context_root"],
        "native_preflight": preflight, "g1_sentinel": g1,
        "g2_witness": g2, "g3_diagnostic": g3,
        "terminal_status": "REFUSED", "effects_observed": [],
        "native_effect_executor_preserved": True, **BOUNDARY,
    }
    return {**body, "operation_root": root(body)}


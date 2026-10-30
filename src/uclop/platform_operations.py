from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import exact_keys, require, require_root, root


REFERENCE_GUARD_KIND = "PYTHON_AUDIT_HOOK_REFERENCE_MECHANICS"
PROTECTED_EXECUTION_KIND = "EXTERNAL_OS_SANDBOX_REQUIRED"


def make_deployment_proposal(
    *, subject_root: str, application_root: str, artifact_root: str,
    target_profile_root: str, rollback_plan_root: str, requested_stage: str,
    source_root: str, qualification_root: str,
) -> dict[str, Any]:
    require(requested_stage in {"S0_NATIVE_REPLAY", "S1_PROTECTED_LOCAL", "S2_INFORMATION_ONLY_FEDERATION"}, "DEPLOYMENT_STAGE_CEILING_EXCEEDED")
    body = {
        "schema": "ucl.ucm.application_deployment_proposal.v1",
        "subject_root": require_root(subject_root),
        "application_root": require_root(application_root),
        "artifact_root": require_root(artifact_root),
        "target_profile_root": require_root(target_profile_root),
        "rollback_plan_root": require_root(rollback_plan_root),
        "requested_stage": requested_stage,
        "source_root": require_root(source_root),
        "qualification_root": require_root(qualification_root),
        "required_execution_boundary": PROTECTED_EXECUTION_KIND,
        "status": "UNBOUND_PROPOSAL",
        "installed": False,
        "released": False,
        "production_active": False,
        "effect_observed": "NONE",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "proposal_root": root(body)}


def verify_deployment_proposal(value: Any, *, expected_subject_root: str, expected_source_root: str, expected_qualification_root: str) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "subject_root", "application_root", "artifact_root", "target_profile_root",
        "rollback_plan_root", "requested_stage", "source_root", "qualification_root",
        "required_execution_boundary", "status", "installed", "released", "production_active",
        "effect_observed", "standing", "authority_effect", "proposal_root",
    }, "$.deployment_proposal")
    rebuilt = make_deployment_proposal(
        subject_root=item["subject_root"], application_root=item["application_root"], artifact_root=item["artifact_root"],
        target_profile_root=item["target_profile_root"], rollback_plan_root=item["rollback_plan_root"],
        requested_stage=item["requested_stage"], source_root=item["source_root"], qualification_root=item["qualification_root"],
    )
    require(item == rebuilt, "DEPLOYMENT_PROPOSAL_INVALID")
    require(item["subject_root"] == require_root(expected_subject_root), "DEPLOYMENT_SUBJECT_MISMATCH")
    require(item["source_root"] == require_root(expected_source_root), "DEPLOYMENT_SOURCE_MISMATCH")
    require(item["qualification_root"] == require_root(expected_qualification_root), "DEPLOYMENT_QUALIFICATION_MISMATCH")
    return deepcopy({key: item[key] for key in item if key != "proposal_root"})


def make_protected_execution_receipt(
    *, proposal: dict[str, Any], observed_artifact_root: str, boundary_kind: str,
    invocation_count: int, retry_count: int, network_calls: int, outside_writes: int,
    result_root: str, rollback_plan_root: str,
) -> dict[str, Any]:
    require(proposal.get("proposal_root") == root({key: value for key, value in proposal.items() if key != "proposal_root"}), "DEPLOYMENT_PROPOSAL_INVALID")
    require(boundary_kind == PROTECTED_EXECUTION_KIND, "PROTECTED_EXECUTION_BOUNDARY_INSUFFICIENT")
    for value, code in ((invocation_count, "INVOCATION_COUNT_INVALID"), (retry_count, "RETRY_COUNT_INVALID"), (network_calls, "NETWORK_COUNT_INVALID"), (outside_writes, "OUTSIDE_WRITE_COUNT_INVALID")):
        require(type(value) is int and type(value) is not bool and value >= 0, code)
    require(invocation_count == 1 and retry_count == 0 and network_calls == 0 and outside_writes == 0, "PROTECTED_EXECUTION_OBSERVATION_INVALID")
    require(observed_artifact_root == proposal["artifact_root"], "PROTECTED_EXECUTION_ARTIFACT_MISMATCH")
    require(rollback_plan_root == proposal["rollback_plan_root"], "PROTECTED_EXECUTION_ROLLBACK_MISMATCH")
    body = {
        "schema": "ucl.ucm.protected_execution_receipt.v1",
        "proposal_root": proposal["proposal_root"],
        "subject_root": proposal["subject_root"],
        "observed_artifact_root": require_root(observed_artifact_root),
        "boundary_kind": boundary_kind,
        "invocation_count": invocation_count,
        "retry_count": retry_count,
        "network_calls": network_calls,
        "outside_writes": outside_writes,
        "result_root": require_root(result_root),
        "rollback_plan_root": require_root(rollback_plan_root),
        "status": "PASS_REFERENCE_ONLY",
        "persistent_host_modified": False,
        "effect_observed": "NONE",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "receipt_root": root(body)}


def verify_protected_execution_receipt(value: Any, *, proposal: dict[str, Any], expected_result_root: str) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "proposal_root", "subject_root", "observed_artifact_root", "boundary_kind",
        "invocation_count", "retry_count", "network_calls", "outside_writes", "result_root",
        "rollback_plan_root", "status", "persistent_host_modified", "effect_observed",
        "standing", "authority_effect", "receipt_root",
    }, "$.protected_execution_receipt")
    rebuilt = make_protected_execution_receipt(
        proposal=proposal, observed_artifact_root=item["observed_artifact_root"], boundary_kind=item["boundary_kind"],
        invocation_count=item["invocation_count"], retry_count=item["retry_count"], network_calls=item["network_calls"],
        outside_writes=item["outside_writes"], result_root=item["result_root"], rollback_plan_root=item["rollback_plan_root"],
    )
    require(item == rebuilt and item["result_root"] == require_root(expected_result_root), "PROTECTED_EXECUTION_RECEIPT_INVALID")
    return deepcopy({key: item[key] for key in item if key != "receipt_root"})


def make_acceptance_receipt(
    *, proposal: dict[str, Any], execution_receipt: dict[str, Any], rollback_receipt_root: str,
    reviewer_verdict_root: str, decision_root: str,
) -> dict[str, Any]:
    require(proposal.get("proposal_root") == execution_receipt.get("proposal_root"), "ACCEPTANCE_PROPOSAL_MISMATCH")
    require(execution_receipt.get("status") == "PASS_REFERENCE_ONLY" and execution_receipt.get("receipt_root") == root({key: value for key, value in execution_receipt.items() if key != "receipt_root"}), "ACCEPTANCE_EXECUTION_INVALID")
    body = {
        "schema": "ucl.ucm.application_acceptance_receipt.v1",
        "proposal_root": proposal["proposal_root"],
        "execution_receipt_root": execution_receipt["receipt_root"],
        "rollback_receipt_root": require_root(rollback_receipt_root),
        "reviewer_verdict_root": require_root(reviewer_verdict_root),
        "decision_root": require_root(decision_root),
        "accepted_stage": proposal["requested_stage"],
        "status": "INFORMATION_ONLY_ACCEPTED",
        "installed": False,
        "released": False,
        "production_active": False,
        "real_a5": False,
        "g0": "CLOSED",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "acceptance_root": root(body)}


def verify_acceptance_receipt(
    value: Any, *, expected_proposal_root: str, expected_execution_receipt_root: str,
    expected_rollback_receipt_root: str, expected_reviewer_verdict_root: str, expected_decision_root: str,
) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "proposal_root", "execution_receipt_root", "rollback_receipt_root",
        "reviewer_verdict_root", "decision_root", "accepted_stage", "status", "installed",
        "released", "production_active", "real_a5", "g0", "standing", "authority_effect", "acceptance_root",
    }, "$.acceptance_receipt")
    body = {key: item[key] for key in item if key != "acceptance_root"}
    require(item["schema"] == "ucl.ucm.application_acceptance_receipt.v1" and item["acceptance_root"] == root(body), "ACCEPTANCE_RECEIPT_INVALID")
    expected = {
        "proposal_root": expected_proposal_root, "execution_receipt_root": expected_execution_receipt_root,
        "rollback_receipt_root": expected_rollback_receipt_root, "reviewer_verdict_root": expected_reviewer_verdict_root,
        "decision_root": expected_decision_root,
    }
    for field, expected_root in expected.items():
        require(item[field] == require_root(expected_root), "ACCEPTANCE_RECEIPT_BINDING_MISMATCH", detail=field)
    require(item["accepted_stage"] in {"S0_NATIVE_REPLAY", "S1_PROTECTED_LOCAL", "S2_INFORMATION_ONLY_FEDERATION"}, "ACCEPTANCE_STAGE_INVALID")
    require(item["status"] == "INFORMATION_ONLY_ACCEPTED" and item["installed"] is False and item["released"] is False and item["production_active"] is False and item["real_a5"] is False and item["g0"] == "CLOSED" and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "ACCEPTANCE_AUTHORITY_INVALID")
    return deepcopy(body)


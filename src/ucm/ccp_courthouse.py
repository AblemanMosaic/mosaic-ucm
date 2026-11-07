"""Exact CCP admission boundary for P/PPI and Courthouse vNext.

This module composes existing point-of-use admissibility records with the
portable Courthouse Workflow IR.  It remains pure and non-authorizing: an
``ADMIT`` decision permits submission to Courthouse preflight, never an
effect.  Courthouse retains capability resolution and authority, while G1,
G2, and G3 retain effect custody.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .ccp_admissibility import validate_admissibility_decision
from .courthouse_workflow import (
    compile_workflow_ir,
    validate_workflow_request,
    validate_workflow_result,
)
from .system import BOUNDARY


ADMISSION_SCHEMA = "mosaic.ucm.ccp-courthouse-admission-envelope.v0.1"
SUBMISSION_SCHEMA = "mosaic.ucm.ccp-courthouse-workflow-submission.v0.1"
STATUS_SCHEMA = "mosaic.ucm.pippi-courthouse-admission-status.v0.1"

_RECORD_KEYS = {
    "jurisdiction_profile", "enforcement_perimeter", "correspondence",
    "evidence_snapshot", "current_use_snapshot", "decision",
}
_ANCHOR_KEYS = {
    "expected_subject_root", "expected_jurisdiction_profile_root",
    "expected_enforcement_perimeter_root", "expected_correspondence_root",
    "expected_policy_root", "expected_schema_registry_root",
    "expected_trust_root", "expected_checkpoint_root",
}


def _boundary(item: dict[str, Any], code: str) -> None:
    require({key: item[key] for key in BOUNDARY} == BOUNDARY, code)


def _anchor_args(anchors: dict[str, Any]) -> dict[str, str]:
    item = exact_keys(anchors, _ANCHOR_KEYS)
    for value in item.values():
        require_root(value)
    return deepcopy(item)


def build_courthouse_admission_envelope(
        *, workflow_request: dict[str, Any], acceptance_case_root: str,
        work_unit_root: str, jurisdiction_profile: dict[str, Any],
        enforcement_perimeter: dict[str, Any], correspondence: dict[str, Any],
        evidence_snapshot: dict[str, Any], current_use_snapshot: dict[str, Any],
        decision: dict[str, Any], expected_subject_root: str,
        expected_jurisdiction_profile_root: str,
        expected_enforcement_perimeter_root: str,
        expected_correspondence_root: str, expected_policy_root: str,
        expected_schema_registry_root: str, expected_trust_root: str,
        expected_checkpoint_root: str) -> dict[str, Any]:
    """Bind an ADMIT decision to one exact P/PPI work unit and workflow."""
    request = validate_workflow_request(workflow_request)
    require_root(acceptance_case_root); require_root(work_unit_root)
    anchors = _anchor_args({
        "expected_subject_root": expected_subject_root,
        "expected_jurisdiction_profile_root":
            expected_jurisdiction_profile_root,
        "expected_enforcement_perimeter_root":
            expected_enforcement_perimeter_root,
        "expected_correspondence_root": expected_correspondence_root,
        "expected_policy_root": expected_policy_root,
        "expected_schema_registry_root": expected_schema_registry_root,
        "expected_trust_root": expected_trust_root,
        "expected_checkpoint_root": expected_checkpoint_root,
    })
    checked = validate_admissibility_decision(
        decision, current_use_snapshot=current_use_snapshot,
        evidence_snapshot=evidence_snapshot,
        jurisdiction_profile=jurisdiction_profile,
        enforcement_perimeter=enforcement_perimeter,
        correspondence=correspondence, **anchors)
    require(checked["decision"] == "ADMIT"
            and checked["effect_authorized"] is False,
            "CCP_COURTHOUSE_DECISION_NOT_ADMISSIBLE")

    profile = jurisdiction_profile
    perimeter = enforcement_perimeter
    use = current_use_snapshot
    evidence = evidence_snapshot
    require(request["subject_root"] == anchors["expected_subject_root"]
            == profile["subject_root"] == use["subject_root"],
            "CCP_COURTHOUSE_SUBJECT_MISMATCH")
    require(request["application_id"] == profile["application_id"],
            "CCP_COURTHOUSE_APPLICATION_MISMATCH")
    require(request["operation_id"] == use["operation"]
            and request["operation_id"] in profile["allowed_operations"]
            and request["operation_id"] in perimeter["intercepted_operations"],
            "CCP_COURTHOUSE_OPERATION_MISMATCH")
    requested_effects = sorted({row["effect_class"]
                                for row in request["requested_capabilities"]})
    require(requested_effects == use["requested_effect_classes"],
            "CCP_COURTHOUSE_EFFECT_SET_MISMATCH")
    governance = profile["governance_jurisdiction"]
    require(request["identity_binding"]["jurisdiction_root"]
            == governance["jurisdiction_root"],
            "CCP_COURTHOUSE_JURISDICTION_MISMATCH")
    require(anchors["expected_policy_root"] in request["policy_pack_roots"],
            "CCP_COURTHOUSE_POLICY_NOT_BOUND")
    require(perimeter["qualification_status"] == "QUALIFIED_SCOPED",
            "CCP_COURTHOUSE_PERIMETER_NOT_QUALIFIED")
    require(evidence["authenticated_epoch"] == use["authenticated_epoch"],
            "CCP_COURTHOUSE_EPOCH_MISMATCH")

    records = {
        "jurisdiction_profile": deepcopy(jurisdiction_profile),
        "enforcement_perimeter": deepcopy(enforcement_perimeter),
        "correspondence": deepcopy(correspondence),
        "evidence_snapshot": deepcopy(evidence_snapshot),
        "current_use_snapshot": deepcopy(current_use_snapshot),
        "decision": deepcopy(checked),
    }
    body = {
        "schema": ADMISSION_SCHEMA,
        "acceptance_case_root": acceptance_case_root,
        "work_unit_root": work_unit_root,
        "workflow_request_root": request["request_root"],
        "operation_id": request["operation_id"],
        "application_id": request["application_id"],
        "subject_root": request["subject_root"],
        "requested_effect_classes": requested_effects,
        "authenticated_epoch": use["authenticated_epoch"],
        "anchors": anchors,
        "records": records,
        "admission_status": "ADMISSIBLE_FOR_COURTHOUSE_PREFLIGHT",
        "authority_status": "EXTERNAL_AUTHORITY_STILL_REQUIRED",
        "effect_authorized": False,
        "non_claims": [
            "NOT_AUTHORITY_GRANT", "NOT_G1_PASS", "NOT_EXECUTION",
            "NOT_COURTHOUSE_ADMISSION", "NOT_GLOBAL_ENFORCEMENT",
        ],
        **BOUNDARY,
    }
    return {**body, "admission_envelope_root": root(body)}


def validate_courthouse_admission_envelope(value: Any,
                                            workflow_request: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "acceptance_case_root", "work_unit_root",
        "workflow_request_root", "operation_id", "application_id",
        "subject_root", "requested_effect_classes", "authenticated_epoch",
        "anchors", "records", "admission_status", "authority_status",
        "effect_authorized", "non_claims", "standing", "authority_effect",
        "real_a5", "g0", "admission_envelope_root",
    })
    require(item["schema"] == ADMISSION_SCHEMA,
            "CCP_COURTHOUSE_ADMISSION_SCHEMA_INVALID")
    records = exact_keys(item["records"], _RECORD_KEYS)
    anchors = _anchor_args(item["anchors"])
    expected = build_courthouse_admission_envelope(
        workflow_request=workflow_request,
        acceptance_case_root=item["acceptance_case_root"],
        work_unit_root=item["work_unit_root"],
        jurisdiction_profile=records["jurisdiction_profile"],
        enforcement_perimeter=records["enforcement_perimeter"],
        correspondence=records["correspondence"],
        evidence_snapshot=records["evidence_snapshot"],
        current_use_snapshot=records["current_use_snapshot"],
        decision=records["decision"], **anchors)
    require(item == expected, "CCP_COURTHOUSE_ADMISSION_INVALID")
    return deepcopy(item)


def compile_admissible_workflow_submission(
        *, workflow_request: dict[str, Any],
        admission_envelope: dict[str, Any]) -> dict[str, Any]:
    request = validate_workflow_request(workflow_request)
    admission = validate_courthouse_admission_envelope(
        admission_envelope, request)
    workflow = compile_workflow_ir(request)
    required_g1_roots = sorted({
        admission["admission_envelope_root"],
        admission["records"]["decision"]["decision_root"],
        admission["records"]["current_use_snapshot"][
            "current_use_snapshot_root"],
    })
    admission_step_body = {
        "schema": "aok.workflow.point-of-use-admissibility-ir.v0.1",
        "step_id": "POINT_OF_USE_ADMISSIBILITY",
        "position": "AFTER_DURABLE_INTENT_BEFORE_G1_SENTINEL",
        "admission_envelope_root": admission["admission_envelope_root"],
        "decision_root": admission["records"]["decision"]["decision_root"],
        "decision": "ADMIT",
        "authenticated_epoch": admission["authenticated_epoch"],
        "effect_authorized": False,
        "courthouse_reverification_required": True,
    }
    admission_step = {**admission_step_body,
                      "admission_step_root": root(admission_step_body)}
    body = {
        "schema": SUBMISSION_SCHEMA,
        "workflow_request": request,
        "compiled_workflow": workflow,
        "admission_envelope": admission,
        "admission_step": admission_step,
        "required_g1_evidence_roots": required_g1_roots,
        "courthouse_lattice_status": "EXTERNAL_RESOLUTION_REQUIRED",
        "dispatch_status": "NOT_DISPATCHED",
        "effect_authorized": False,
        "non_claims": [
            "NOT_INSTALLED_COURTHOUSE_ROUTE", "NOT_AUTHORITY_GRANT",
            "NOT_G1_PASS", "NOT_EXECUTION",
        ],
        **BOUNDARY,
    }
    return {**body, "submission_root": root(body)}


def validate_admissible_workflow_submission(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "workflow_request", "compiled_workflow",
        "admission_envelope", "admission_step",
        "required_g1_evidence_roots", "courthouse_lattice_status",
        "dispatch_status", "effect_authorized", "non_claims", "standing",
        "authority_effect", "real_a5", "g0", "submission_root",
    })
    require(item["schema"] == SUBMISSION_SCHEMA,
            "CCP_COURTHOUSE_SUBMISSION_SCHEMA_INVALID")
    expected = compile_admissible_workflow_submission(
        workflow_request=item["workflow_request"],
        admission_envelope=item["admission_envelope"])
    require(item == expected, "CCP_COURTHOUSE_SUBMISSION_INVALID")
    return deepcopy(item)


def validate_admissible_workflow_result(*, submission: Any,
                                        result: Any) -> dict[str, Any]:
    checked = validate_admissible_workflow_submission(submission)
    imported = validate_workflow_result(
        checked["workflow_request"], checked["compiled_workflow"], result)
    g1_evidence = set(result["g1"]["evidence_roots"])
    require(set(checked["required_g1_evidence_roots"]) <= g1_evidence,
            "CCP_COURTHOUSE_G1_ADMISSION_EVIDENCE_MISSING")
    body = {
        "schema": "mosaic.ucm.ccp-courthouse-result-import.v0.1",
        "submission_root": checked["submission_root"],
        "admission_envelope_root": checked["admission_envelope"][
            "admission_envelope_root"],
        "workflow_import_root": imported["import_root"],
        "terminal_status": imported["terminal_status"],
        "status": "PASS_BOUND_CORRESPONDENCE"
        if imported["status"] == "PASS_CORRESPONDENCE"
        else "RECORDED_BOUND_NONPASS",
        "effect_authorized_by_ucm": False,
        **BOUNDARY,
    }
    return {**body, "import_root": root(body)}


def build_pippi_admission_status(*, submission: Any) -> dict[str, Any]:
    checked = validate_admissible_workflow_submission(submission)
    admission = checked["admission_envelope"]
    decision = admission["records"]["decision"]
    body = {
        "schema": STATUS_SCHEMA,
        "submission_root": checked["submission_root"],
        "acceptance_case_root": admission["acceptance_case_root"],
        "work_unit_root": admission["work_unit_root"],
        "application_id": admission["application_id"],
        "operation_id": admission["operation_id"],
        "subject_root": admission["subject_root"],
        "admissibility": "CURRENT_ADMIT",
        "authority": "EXTERNAL_NOT_ESTABLISHED",
        "execution": "NOT_DISPATCHED",
        "courthouse_route": "STAGED_NOT_INSTALLED",
        "reason_codes": deepcopy(decision["reason_codes"]),
        "required_g1_evidence_roots": deepcopy(
            checked["required_g1_evidence_roots"]),
        "human_summary": (
            "Current evidence permits Courthouse preflight. Separate "
            "Courthouse authority and a bound G1 PASS remain required."),
        "projection_is_evidence": False,
        "projection_is_authority": False,
        **BOUNDARY,
    }
    return {**body, "status_root": root(body)}

"""Stage I4 preparation with exact evidence and three-gate receipts.

This module validates records only. It cannot contact an application, execute a
route, or grant an effect capability.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import io
from typing import Any
import zipfile

from uclop.canonical import Refusal, exact_keys, require, require_root, root, strict_loads
from .amcas import BOUNDARY
from .artifacts import verify_deterministic_zip
from .stage3 import validate_instruction, validate_plan

ELIGIBILITY_SCHEMA = "mosaic.ucm.stage-i4-eligibility.v0.2"
RUN_CONTRACT_SCHEMA = "mosaic.ucm.stage-i4-shadow-run-contract.v0.2"
OBSERVATION_SCHEMA = "mosaic.ucm.stage-i4-shadow-observation.v0.2"
REVIEW_SCHEMA = "mosaic.ucm.stage-i3-review-disposition.v0.1"
REVIEW_ARCHIVE_SCHEMA = "mosaic.ucm.stage-i3-review-archive.v0.1"
REVIEW_ARCHIVE_ROLE = "UCM_AMCAS_STAGE_I3_REVIEW_EVIDENCE"
G1_SCHEMA = "mosaic.ucm.integration-g1-sentinel.v0.1"
G2_SCHEMA = "mosaic.ucm.integration-g2-witness.v0.1"
G3_SCHEMA = "mosaic.ucm.integration-g3-diagnostic.v0.1"
AUTHORITY_SCHEMA = "mosaic.ucm.shadow-execution-authority.v0.1"
QUALIFIED_VERDICT = "QUALIFIED_RECOMMENDATION_ONLY"
REVIEW_POLICY_ID = "UCM.AMCAS.STAGE_I3.INDEPENDENT_REVIEW.v1"
SHADOW_EFFECT_CLASSES = {"PURE_COMPUTATION", "READ_ONLY"}
FORBIDDEN_EFFECT_CLASSES = {"LOCAL_ARTIFACT_PREPARATION", "WRITE_WORKSPACE",
    "DELETE_WORKSPACE", "NETWORK", "INSTALL", "PERSISTENT_HOST_STATE",
    "AUTHORITY_CHANGE"}


def _text(value: Any, code: str, maximum: int = 4096) -> str:
    require(type(value) is str and 0 < len(value) <= maximum
            and value == value.strip(), code)
    return value


def _identifier(value: Any, code: str) -> str:
    value = _text(value, code, 192)
    require(all(ch.isalnum() or ch in "._:-" for ch in value), code)
    return value


def _unique_text_list(value: Any, code: str) -> list[str]:
    require(type(value) is list, code)
    require(all(type(row) is str and bool(row) and row == row.strip()
                for row in value), code)
    require(len(value) == len(set(value)), code)
    return value


def _sha(raw: bytes) -> str:
    require(type(raw) is bytes, "STAGE_I4_ARCHIVE_BYTES_REQUIRED")
    return hashlib.sha256(raw).hexdigest()


def _archive_member(raw: bytes, name: str) -> bytes:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            require(archive.namelist().count(name) == 1,
                    "STAGE_I4_REVIEW_MEMBER_INVALID", detail=name)
            return archive.read(name)
    except (zipfile.BadZipFile, KeyError, OSError) as error:
        require(False, "STAGE_I4_REVIEW_ARCHIVE_INVALID",
                detail=type(error).__name__)
    raise AssertionError("unreachable")


def validate_review_disposition(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "review_class", "reviewer_policy_id",
        "reviewer_identity_root", "reviewed_subject_root",
        "reviewed_qualification_root", "reviewed_source_root", "applications",
        "verdict", "findings", "limitations", "standing", "authority_effect",
        "real_a5", "g0", "disposition_root"})
    require(item["schema"] == REVIEW_SCHEMA, "STAGE_I4_REVIEW_SCHEMA_INVALID")
    require(item["review_class"] in {"INDEPENDENT_REVIEW",
        "OPERATOR_REPRODUCED", "BUILDER_SELF_REVIEW"},
        "STAGE_I4_REVIEW_CLASS_INVALID")
    require(item["reviewer_policy_id"] == REVIEW_POLICY_ID,
            "STAGE_I4_REVIEW_POLICY_INVALID")
    for key in ("reviewer_identity_root", "reviewed_subject_root",
                "reviewed_qualification_root", "reviewed_source_root"):
        require_root(item[key])
    require(type(item["applications"]) is list and bool(item["applications"]),
            "STAGE_I4_REVIEW_APPLICATIONS_INVALID")
    seen: set[str] = set()
    for raw in item["applications"]:
        row = exact_keys(raw, {"application_id", "instruction_root", "plan_root"})
        app = _identifier(row["application_id"],
                          "STAGE_I4_REVIEW_APPLICATION_ID_INVALID")
        require(app not in seen, "STAGE_I4_REVIEW_APPLICATION_DUPLICATE")
        seen.add(app); require_root(row["instruction_root"]); require_root(row["plan_root"])
    require(item["verdict"] in {QUALIFIED_VERDICT, "HOLD_FOR_REPAIR",
        "INCOMPLETE_REVIEW", "NOT_QUALIFIED"}, "STAGE_I4_REVIEW_VERDICT_INVALID")
    require(type(item["findings"]) is list, "STAGE_I4_REVIEW_FINDINGS_INVALID")
    finding_ids: set[str] = set()
    for raw in item["findings"]:
        finding = exact_keys(raw, {"id", "severity", "status", "summary"})
        finding_id = _identifier(finding["id"], "STAGE_I4_REVIEW_FINDING_ID_INVALID")
        require(finding_id not in finding_ids, "STAGE_I4_REVIEW_FINDING_DUPLICATE")
        finding_ids.add(finding_id)
        require(finding["severity"] in {"HIGH", "MED", "LOW", "INFO"}
                and finding["status"] in {"OPEN", "CLOSED", "ACCEPTED_LIMITATION"},
                "STAGE_I4_REVIEW_FINDING_INVALID")
        _text(finding["summary"], "STAGE_I4_REVIEW_FINDING_SUMMARY_INVALID")
    _unique_text_list(item["limitations"], "STAGE_I4_REVIEW_LIMITATIONS_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_AUTHORITY_CEILING_INVALID")
    if item["verdict"] == QUALIFIED_VERDICT:
        require(item["review_class"] == "INDEPENDENT_REVIEW",
                "STAGE_I4_TERMINAL_REVIEW_NOT_INDEPENDENT")
        require(not any(row["status"] == "OPEN" and row["severity"] in {"HIGH", "MED"}
                        for row in item["findings"]),
                "STAGE_I4_TERMINAL_REVIEW_BLOCKING_FINDING")
    body = {key: deepcopy(raw) for key, raw in item.items()
            if key != "disposition_root"}
    require(item["disposition_root"] == root(body),
            "STAGE_I4_REVIEW_DISPOSITION_ROOT_INVALID")
    return deepcopy(item)


def verify_review_archive(raw: bytes) -> dict[str, Any]:
    try:
        verify_deterministic_zip(raw, expected_schema=REVIEW_ARCHIVE_SCHEMA,
                                 expected_role=REVIEW_ARCHIVE_ROLE)
    except Refusal:
        raise
    except ValueError as error:
        raise Refusal("STAGE_I4_REVIEW_ARCHIVE_INVALID",
                      detail=str(error)) from error
    disposition = validate_review_disposition(
        strict_loads(_archive_member(raw, "REVIEW-DISPOSITION.json")))
    return {"archive_sha256": _sha(raw), "disposition": disposition}


def _review_application(disposition: dict[str, Any], app: str) -> dict[str, Any]:
    matches = [row for row in disposition["applications"]
               if row["application_id"] == app]
    require(len(matches) == 1, "STAGE_I4_REVIEW_SUBJECT_APPLICATION_MISSING")
    return matches[0]


def validate_eligibility(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "application_id",
        "stage_i3_instruction_root", "stage_i3_plan_root",
        "stage_i3_review_archive_sha256", "stage_i3_review_disposition_root",
        "stage_i3_review_class", "stage_i3_review_verdict",
        "stage_i3_plan_status", "unresolved_holds",
        "eligible_for_shadow_preparation", "eligible_for_shadow_execution",
        "reason_codes", "native_semantic_authority_preserved",
        "native_effect_executors_preserved", "execution_authorized",
        "composition_authorized", "standing", "authority_effect", "real_a5",
        "g0", "eligibility_root"})
    require(item["schema"] == ELIGIBILITY_SCHEMA, "STAGE_I4_ELIGIBILITY_SCHEMA_INVALID")
    _identifier(item["application_id"], "STAGE_I4_APPLICATION_ID_INVALID")
    for key in ("stage_i3_instruction_root", "stage_i3_plan_root",
                "stage_i3_review_archive_sha256", "stage_i3_review_disposition_root"):
        require_root(item[key])
    require(item["stage_i3_review_class"] in {"INDEPENDENT_REVIEW",
        "OPERATOR_REPRODUCED", "BUILDER_SELF_REVIEW"},
        "STAGE_I4_REVIEW_CLASS_INVALID")
    require(item["stage_i3_review_verdict"] in {QUALIFIED_VERDICT,
        "HOLD_FOR_REPAIR", "INCOMPLETE_REVIEW", "NOT_QUALIFIED"},
        "STAGE_I4_REVIEW_VERDICT_INVALID")
    require(item["stage_i3_plan_status"] in {"READY_FOR_SHADOW_REVIEW",
        "HOLD_FOR_REPAIR", "NO_APPLICABLE_SHADOW_ROUTE"},
        "STAGE_I4_PLAN_STATUS_INVALID")
    _unique_text_list(item["unresolved_holds"], "STAGE_I4_HOLDS_INVALID")
    _unique_text_list(item["reason_codes"], "STAGE_I4_REASON_CODES_INVALID")
    preparation = item["stage_i3_plan_status"] == "READY_FOR_SHADOW_REVIEW"
    execution = (preparation and item["stage_i3_review_class"] == "INDEPENDENT_REVIEW"
                 and item["stage_i3_review_verdict"] == QUALIFIED_VERDICT
                 and not item["unresolved_holds"])
    reasons: list[str] = []
    if not preparation: reasons.append("STAGE_I3_PLAN_NOT_REVIEW_READY")
    if item["stage_i3_review_class"] != "INDEPENDENT_REVIEW":
        reasons.append("INDEPENDENT_REVIEW_REQUIRED")
    if item["stage_i3_review_verdict"] != QUALIFIED_VERDICT:
        reasons.append("STAGE_I3_TERMINAL_REVIEW_REQUIRED")
    if item["unresolved_holds"]: reasons.append("UNRESOLVED_PLAN_HOLDS")
    if not reasons: reasons.append("ELIGIBILITY_CONDITIONS_SATISFIED")
    require(item["eligible_for_shadow_preparation"] is preparation
            and item["eligible_for_shadow_execution"] is execution
            and item["reason_codes"] == reasons,
            "STAGE_I4_ELIGIBILITY_DERIVATION_INVALID")
    require(item["native_semantic_authority_preserved"] is True
            and item["native_effect_executors_preserved"] is True
            and item["execution_authorized"] is False
            and item["composition_authorized"] is False,
            "STAGE_I4_ELIGIBILITY_AUTHORITY_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_AUTHORITY_CEILING_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "eligibility_root"}
    require(item["eligibility_root"] == root(body), "STAGE_I4_ELIGIBILITY_ROOT_INVALID")
    return deepcopy(item)


def derive_eligibility(*, instruction: Any, plan: Any,
                       review_archive: bytes) -> dict[str, Any]:
    instruction = validate_instruction(instruction)
    plan = validate_plan(plan, expected_instruction=instruction)
    review = verify_review_archive(review_archive); disposition = review["disposition"]
    reviewed = _review_application(disposition, plan["application_id"])
    require(reviewed["instruction_root"] == instruction["instruction_root"]
            and reviewed["plan_root"] == plan["plan_root"],
            "STAGE_I4_REVIEW_SUBJECT_BINDING_INVALID")
    preparation = plan["plan_status"] == "READY_FOR_SHADOW_REVIEW"
    execution = (preparation and disposition["review_class"] == "INDEPENDENT_REVIEW"
                 and disposition["verdict"] == QUALIFIED_VERDICT and not plan["holds"])
    reasons: list[str] = []
    if not preparation: reasons.append("STAGE_I3_PLAN_NOT_REVIEW_READY")
    if disposition["review_class"] != "INDEPENDENT_REVIEW":
        reasons.append("INDEPENDENT_REVIEW_REQUIRED")
    if disposition["verdict"] != QUALIFIED_VERDICT:
        reasons.append("STAGE_I3_TERMINAL_REVIEW_REQUIRED")
    if plan["holds"]: reasons.append("UNRESOLVED_PLAN_HOLDS")
    if not reasons: reasons.append("ELIGIBILITY_CONDITIONS_SATISFIED")
    body = {"schema": ELIGIBILITY_SCHEMA, "application_id": plan["application_id"],
        "stage_i3_instruction_root": instruction["instruction_root"],
        "stage_i3_plan_root": plan["plan_root"],
        "stage_i3_review_archive_sha256": review["archive_sha256"],
        "stage_i3_review_disposition_root": disposition["disposition_root"],
        "stage_i3_review_class": disposition["review_class"],
        "stage_i3_review_verdict": disposition["verdict"],
        "stage_i3_plan_status": plan["plan_status"],
        "unresolved_holds": deepcopy(plan["holds"]),
        "eligible_for_shadow_preparation": preparation,
        "eligible_for_shadow_execution": execution, "reason_codes": reasons,
        "native_semantic_authority_preserved": True,
        "native_effect_executors_preserved": True,
        "execution_authorized": False, "composition_authorized": False, **BOUNDARY}
    return validate_eligibility({**body, "eligibility_root": root(body)})


def _held_relations(plan: dict[str, Any]) -> list[str]:
    return sorted(row["schema_root"] for row in plan["relation_dispositions"]
                  if row["disposition"] == "HOLD")


def _case_dependencies(case: dict[str, Any]) -> list[str]:
    roots = [req.split(":", 1)[1] for req in case["evidence_requirements"]
             if req.startswith("RELATION:")]
    for value in roots: require_root(value)
    return sorted(set(roots))


def validate_run_contract(value: Any, *, expected_eligibility: Any,
                          expected_plan: Any, expected_instruction: Any,
                          expected_review_archive: bytes) -> dict[str, Any]:
    instruction = validate_instruction(expected_instruction)
    plan = validate_plan(expected_plan, expected_instruction=instruction)
    derived = derive_eligibility(instruction=instruction, plan=plan,
                                 review_archive=expected_review_archive)
    eligibility = validate_eligibility(expected_eligibility)
    require(eligibility == derived, "STAGE_I4_ELIGIBILITY_REDERIVATION_INVALID")
    item = exact_keys(value, {"schema", "application_id", "eligibility_root",
        "instruction_root", "plan_root", "review_archive_sha256", "plan_status",
        "unresolved_holds", "held_relation_roots", "case_schedule",
        "effect_membrane", "gate_requirements", "mode",
        "application_contact_authorized", "execution_authorized",
        "composition_authorized", "standing", "authority_effect", "real_a5",
        "g0", "run_contract_root"})
    require(item["schema"] == RUN_CONTRACT_SCHEMA, "STAGE_I4_RUN_CONTRACT_SCHEMA_INVALID")
    require(item["application_id"] == plan["application_id"]
            and item["eligibility_root"] == eligibility["eligibility_root"]
            and item["instruction_root"] == instruction["instruction_root"]
            and item["plan_root"] == plan["plan_root"]
            and item["review_archive_sha256"] == eligibility["stage_i3_review_archive_sha256"]
            and item["plan_status"] == plan["plan_status"]
            and item["unresolved_holds"] == plan["holds"]
            and item["held_relation_roots"] == _held_relations(plan),
            "STAGE_I4_RUN_CONTRACT_BINDING_INVALID")
    require(eligibility["eligible_for_shadow_execution"] is True,
            "STAGE_I4_SHADOW_EXECUTION_INELIGIBLE")
    require(type(item["case_schedule"]) is list, "STAGE_I4_CASE_SCHEDULE_INVALID")
    expected_cases = {row["id"]: row for row in plan["correspondence_cases"]}
    projections = {row["capability_id"]: row for row in plan["capability_projections"]}
    seen: set[str] = set()
    for raw in item["case_schedule"]:
        row = exact_keys(raw, {"case_id", "capability_id", "input_root",
            "native_route", "ucm_projection", "effect_class",
            "relation_dependencies", "expected_native_decision",
            "expected_ucm_decision", "expected_native_result_root",
            "expected_ucm_result_root", "expected_equivalence"})
        case_id = _identifier(row["case_id"], "STAGE_I4_CASE_ID_INVALID")
        require(case_id in expected_cases and case_id not in seen,
                "STAGE_I4_CASE_SCHEDULE_COVERAGE_INVALID")
        seen.add(case_id); case = expected_cases[case_id]
        projection = projections[case["capability_id"]]
        require(row == {"case_id": case_id, "capability_id": case["capability_id"],
            "input_root": case["input_root"], "native_route": projection["native_route"],
            "ucm_projection": projection["ucm_projection"],
            "effect_class": projection["effect_class"],
            "relation_dependencies": _case_dependencies(case),
            "expected_native_decision": case["expected_native_decision"],
            "expected_ucm_decision": case["expected_ucm_decision"],
            "expected_native_result_root": case["expected_native_result_root"],
            "expected_ucm_result_root": case["expected_ucm_result_root"],
            "expected_equivalence": case["expected_equivalence"]},
            "STAGE_I4_CASE_SCHEDULE_BINDING_INVALID")
        require(projection["effect_class"] in SHADOW_EFFECT_CLASSES,
                "STAGE_I4_CASE_EFFECT_OUTSIDE_MEMBRANE")
        require(not set(row["relation_dependencies"]).intersection(item["held_relation_roots"]),
                "STAGE_I4_CASE_DEPENDS_ON_HELD_RELATION")
    require(seen == set(expected_cases), "STAGE_I4_CASE_SCHEDULE_COVERAGE_INVALID")
    membrane = exact_keys(item["effect_membrane"], {"allowed_effect_classes",
        "forbidden_effect_classes", "network_allowed", "installation_allowed",
        "persistent_host_state_allowed", "workspace_mutation_allowed",
        "native_effect_executors_preserved"})
    _unique_text_list(membrane["allowed_effect_classes"], "STAGE_I4_EFFECT_MEMBRANE_INVALID")
    _unique_text_list(membrane["forbidden_effect_classes"], "STAGE_I4_EFFECT_MEMBRANE_INVALID")
    require(set(membrane["allowed_effect_classes"]) == SHADOW_EFFECT_CLASSES
            and set(membrane["forbidden_effect_classes"]) == FORBIDDEN_EFFECT_CLASSES
            and all(membrane[key] is False for key in ("network_allowed",
                "installation_allowed", "persistent_host_state_allowed",
                "workspace_mutation_allowed"))
            and membrane["native_effect_executors_preserved"] is True,
            "STAGE_I4_EFFECT_MEMBRANE_INVALID")
    require(item["gate_requirements"] == ["UCM.INTEGRATION.G1",
        "UCM.INTEGRATION.G2", "UCM.INTEGRATION.G3"],
        "STAGE_I4_GATE_REQUIREMENTS_INVALID")
    require(item["mode"] == "SEALED_SHADOW_REHEARSAL"
            and item["application_contact_authorized"] is False
            and item["execution_authorized"] is False
            and item["composition_authorized"] is False,
            "STAGE_I4_RUN_AUTHORITY_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_AUTHORITY_CEILING_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "run_contract_root"}
    require(item["run_contract_root"] == root(body), "STAGE_I4_RUN_CONTRACT_ROOT_INVALID")
    return deepcopy(item)


def build_run_contract(*, eligibility: Any, plan: Any, instruction: Any,
                       review_archive: bytes) -> dict[str, Any]:
    instruction = validate_instruction(instruction)
    plan = validate_plan(plan, expected_instruction=instruction)
    eligibility = validate_eligibility(eligibility)
    projections = {row["capability_id"]: row for row in plan["capability_projections"]}
    schedule = []
    for case in plan["correspondence_cases"]:
        projection = projections[case["capability_id"]]
        schedule.append({"case_id": case["id"], "capability_id": case["capability_id"],
            "input_root": case["input_root"], "native_route": projection["native_route"],
            "ucm_projection": projection["ucm_projection"],
            "effect_class": projection["effect_class"],
            "relation_dependencies": _case_dependencies(case),
            "expected_native_decision": case["expected_native_decision"],
            "expected_ucm_decision": case["expected_ucm_decision"],
            "expected_native_result_root": case["expected_native_result_root"],
            "expected_ucm_result_root": case["expected_ucm_result_root"],
            "expected_equivalence": case["expected_equivalence"]})
    body = {"schema": RUN_CONTRACT_SCHEMA, "application_id": plan["application_id"],
        "eligibility_root": eligibility["eligibility_root"],
        "instruction_root": instruction["instruction_root"], "plan_root": plan["plan_root"],
        "review_archive_sha256": _sha(review_archive), "plan_status": plan["plan_status"],
        "unresolved_holds": deepcopy(plan["holds"]),
        "held_relation_roots": _held_relations(plan), "case_schedule": schedule,
        "effect_membrane": {"allowed_effect_classes": sorted(SHADOW_EFFECT_CLASSES),
            "forbidden_effect_classes": sorted(FORBIDDEN_EFFECT_CLASSES),
            "network_allowed": False, "installation_allowed": False,
            "persistent_host_state_allowed": False, "workspace_mutation_allowed": False,
            "native_effect_executors_preserved": True},
        "gate_requirements": ["UCM.INTEGRATION.G1", "UCM.INTEGRATION.G2",
            "UCM.INTEGRATION.G3"], "mode": "SEALED_SHADOW_REHEARSAL",
        "application_contact_authorized": False, "execution_authorized": False,
        "composition_authorized": False, **BOUNDARY}
    return validate_run_contract({**body, "run_contract_root": root(body)},
        expected_eligibility=eligibility, expected_plan=plan,
        expected_instruction=instruction, expected_review_archive=review_archive)


def _validate_gate_boundary(item: dict[str, Any]) -> None:
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_AUTHORITY_CEILING_INVALID")


def validate_g1(value: Any, contract: dict[str, Any]) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "run_contract_root", "application_id",
        "case_ids", "capability_ids", "effect_classes", "policy_id", "generation",
        "decision", "reason_codes", "rollback_root", "budget_root", "standing",
        "authority_effect", "real_a5", "g0", "g1_root"})
    require(item["schema"] == G1_SCHEMA and item["run_contract_root"] == contract["run_contract_root"]
            and item["application_id"] == contract["application_id"],
            "STAGE_I4_G1_BINDING_INVALID")
    for key in ("case_ids", "capability_ids", "effect_classes", "reason_codes"):
        _unique_text_list(item[key], "STAGE_I4_G1_INVENTORY_INVALID")
    require(item["case_ids"] == [row["case_id"] for row in contract["case_schedule"]]
            and item["capability_ids"] == sorted({row["capability_id"] for row in contract["case_schedule"]})
            and item["effect_classes"] == sorted({row["effect_class"] for row in contract["case_schedule"]}),
            "STAGE_I4_G1_INVENTORY_INVALID")
    _identifier(item["policy_id"], "STAGE_I4_G1_POLICY_INVALID")
    require(type(item["generation"]) is int and item["generation"] >= 1,
            "STAGE_I4_G1_GENERATION_INVALID")
    require(item["decision"] in {"ALLOW", "REFUSE", "HOLD"}, "STAGE_I4_G1_DECISION_INVALID")
    require_root(item["rollback_root"]); require_root(item["budget_root"]); _validate_gate_boundary(item)
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "g1_root"}
    require(item["g1_root"] == root(body), "STAGE_I4_G1_ROOT_INVALID")
    return deepcopy(item)


def validate_g2(value: Any, contract: dict[str, Any], g1: dict[str, Any]) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "run_contract_root", "g1_root",
        "application_id", "case_results", "observed_effect_classes", "output_roots",
        "recovery_status", "completion_status", "standing", "authority_effect",
        "real_a5", "g0", "g2_root"})
    require(item["schema"] == G2_SCHEMA and item["run_contract_root"] == contract["run_contract_root"]
            and item["g1_root"] == g1["g1_root"]
            and item["application_id"] == contract["application_id"],
            "STAGE_I4_G2_BINDING_INVALID")
    require(type(item["case_results"]) is list, "STAGE_I4_G2_CASE_RESULTS_INVALID")
    scheduled = {row["case_id"] for row in contract["case_schedule"]}
    seen: set[str] = set(); result_roots: set[str] = set()
    for raw in item["case_results"]:
        row = exact_keys(raw, {"case_id", "native_decision", "ucm_decision",
            "native_result_root", "ucm_result_root"})
        case_id = _identifier(row["case_id"], "STAGE_I4_G2_CASE_ID_INVALID")
        require(case_id in scheduled and case_id not in seen,
                "STAGE_I4_G2_CASE_RESULTS_INVALID")
        seen.add(case_id)
        _text(row["native_decision"], "STAGE_I4_G2_DECISION_INVALID")
        _text(row["ucm_decision"], "STAGE_I4_G2_DECISION_INVALID")
        require_root(row["native_result_root"]); require_root(row["ucm_result_root"])
        result_roots.update((row["native_result_root"], row["ucm_result_root"]))
    require(seen == scheduled, "STAGE_I4_G2_CASE_RESULTS_INVALID")
    _unique_text_list(item["observed_effect_classes"], "STAGE_I4_G2_EFFECTS_INVALID")
    require(set(item["observed_effect_classes"]).issubset(SHADOW_EFFECT_CLASSES),
            "STAGE_I4_G2_EFFECTS_INVALID")
    _unique_text_list(item["output_roots"], "STAGE_I4_G2_OUTPUTS_INVALID")
    for value_root in item["output_roots"]: require_root(value_root)
    require(item["output_roots"] == sorted(result_roots),
            "STAGE_I4_G2_OUTPUTS_INVALID")
    require(item["recovery_status"] in {"NOT_REQUIRED", "COMPLETE", "REFUSED"}
            and item["completion_status"] in {"COMPLETE", "REFUSED", "INCOMPLETE"},
            "STAGE_I4_G2_STATUS_INVALID")
    _validate_gate_boundary(item)
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "g2_root"}
    require(item["g2_root"] == root(body), "STAGE_I4_G2_ROOT_INVALID")
    return deepcopy(item)


def validate_g3(value: Any, contract: dict[str, Any], g2: dict[str, Any]) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "run_contract_root", "g2_root",
        "application_id", "classification", "finding_codes", "next_action",
        "standing", "authority_effect", "real_a5", "g0", "g3_root"})
    require(item["schema"] == G3_SCHEMA and item["run_contract_root"] == contract["run_contract_root"]
            and item["g2_root"] == g2["g2_root"]
            and item["application_id"] == contract["application_id"],
            "STAGE_I4_G3_BINDING_INVALID")
    require(item["classification"] in {"PASS", "DIVERGED", "REFUSED", "INCOMPLETE"},
            "STAGE_I4_G3_CLASSIFICATION_INVALID")
    _unique_text_list(item["finding_codes"], "STAGE_I4_G3_FINDINGS_INVALID")
    _identifier(item["next_action"], "STAGE_I4_G3_NEXT_ACTION_INVALID"); _validate_gate_boundary(item)
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "g3_root"}
    require(item["g3_root"] == root(body), "STAGE_I4_G3_ROOT_INVALID")
    return deepcopy(item)


def validate_execution_authority(value: Any, contract: dict[str, Any]) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "run_contract_root", "issuer_policy_id",
        "scope", "generation", "authorized", "reason_code", "standing",
        "authority_effect", "real_a5", "g0", "authority_root"})
    require(item["schema"] == AUTHORITY_SCHEMA
            and item["run_contract_root"] == contract["run_contract_root"],
            "STAGE_I4_EXECUTION_AUTHORITY_BINDING_INVALID")
    _identifier(item["issuer_policy_id"], "STAGE_I4_EXECUTION_AUTHORITY_ISSUER_INVALID")
    require(item["scope"] == "SHADOW_REHEARSAL"
            and type(item["generation"]) is int and item["generation"] >= 1
            and item["authorized"] is False
            and item["reason_code"] == "AUTHORITY_CEILING_NONE",
            "STAGE_I4_EXECUTION_AUTHORITY_INVALID")
    _validate_gate_boundary(item)
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "authority_root"}
    require(item["authority_root"] == root(body), "STAGE_I4_EXECUTION_AUTHORITY_ROOT_INVALID")
    return deepcopy(item)


def validate_observation(value: Any, *, expected_run_contract: Any,
                         expected_eligibility: Any, expected_plan: Any,
                         expected_instruction: Any,
                         expected_review_archive: bytes) -> dict[str, Any]:
    contract = validate_run_contract(expected_run_contract,
        expected_eligibility=expected_eligibility, expected_plan=expected_plan,
        expected_instruction=expected_instruction,
        expected_review_archive=expected_review_archive)
    item = exact_keys(value, {"schema", "application_id", "run_contract_root",
        "case_observations", "g1_sentinel", "g2_witness", "g3_diagnostic",
        "observed_effect_classes", "pairwise_status", "expected_conformance_status",
        "comparison_status", "execution_authority", "standing", "authority_effect",
        "real_a5", "g0", "observation_root"})
    require(item["schema"] == OBSERVATION_SCHEMA
            and item["application_id"] == contract["application_id"]
            and item["run_contract_root"] == contract["run_contract_root"],
            "STAGE_I4_OBSERVATION_BINDING_INVALID")
    g1 = validate_g1(item["g1_sentinel"], contract)
    g2 = validate_g2(item["g2_witness"], contract, g1)
    g3 = validate_g3(item["g3_diagnostic"], contract, g2)
    validate_execution_authority(item["execution_authority"], contract)
    require(type(item["case_observations"]) is list, "STAGE_I4_OBSERVATIONS_INVALID")
    scheduled = {row["case_id"]: row for row in contract["case_schedule"]}
    seen: set[str] = set(); all_equal = True; all_expected = True
    for raw in item["case_observations"]:
        row = exact_keys(raw, {"case_id", "native_decision", "ucm_decision",
            "native_result_root", "ucm_result_root", "pairwise_equivalent",
            "native_expected_conformant", "ucm_expected_conformant"})
        case_id = _identifier(row["case_id"], "STAGE_I4_OBSERVATION_CASE_INVALID")
        require(case_id in scheduled and case_id not in seen,
                "STAGE_I4_OBSERVATION_COVERAGE_INVALID")
        seen.add(case_id); expected = scheduled[case_id]
        require_root(row["native_result_root"]); require_root(row["ucm_result_root"])
        _text(row["native_decision"], "STAGE_I4_NATIVE_DECISION_INVALID")
        _text(row["ucm_decision"], "STAGE_I4_UCM_DECISION_INVALID")
        equivalent = (row["native_decision"] == row["ucm_decision"]
                      and row["native_result_root"] == row["ucm_result_root"])
        native_expected = (row["native_decision"] == expected["expected_native_decision"]
                           and row["native_result_root"] == expected["expected_native_result_root"])
        ucm_expected = (row["ucm_decision"] == expected["expected_ucm_decision"]
                        and row["ucm_result_root"] == expected["expected_ucm_result_root"])
        require(row["pairwise_equivalent"] is equivalent
                and row["native_expected_conformant"] is native_expected
                and row["ucm_expected_conformant"] is ucm_expected,
                "STAGE_I4_CASE_RESULT_DERIVATION_INVALID")
        all_equal = all_equal and equivalent
        all_expected = all_expected and native_expected and ucm_expected
    require(seen == set(scheduled), "STAGE_I4_OBSERVATION_COVERAGE_INVALID")
    _unique_text_list(item["observed_effect_classes"], "STAGE_I4_OBSERVED_EFFECT_INVALID")
    require(item["observed_effect_classes"] == g2["observed_effect_classes"]
            and set(item["observed_effect_classes"]).issubset(SHADOW_EFFECT_CLASSES),
            "STAGE_I4_OBSERVED_EFFECT_INVALID")
    pairwise = "EQUIVALENT" if all_equal else "DIVERGED"
    conformance = "CONFORMANT" if all_expected else "NONCONFORMANT"
    overall = "PASS" if all_equal and all_expected else "FAIL"
    require(item["pairwise_status"] == pairwise
            and item["expected_conformance_status"] == conformance
            and item["comparison_status"] == overall,
            "STAGE_I4_COMPARISON_STATUS_INVALID")
    require(g3["classification"] == ("PASS" if overall == "PASS" else "DIVERGED"),
            "STAGE_I4_G3_RESULT_MISMATCH")
    _validate_gate_boundary(item)
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "observation_root"}
    require(item["observation_root"] == root(body), "STAGE_I4_OBSERVATION_ROOT_INVALID")
    return deepcopy(item)

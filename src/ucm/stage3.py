"""Stage I3 planning-only shadow correspondence contracts.

Stage I3 plans describe how a native application and its UCM projection would
be compared.  They do not execute either side, connect applications, or grant
an effect capability.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY, EFFECT_CLASSES


INSTRUCTION_SCHEMA = "mosaic.ucm.stage-i3-shadow-instruction.v0.1"
PLAN_SCHEMA = "mosaic.ucm.stage-i3-shadow-plan.v0.1"
PLAN_STATUSES = {"READY_FOR_SHADOW_REVIEW", "HOLD_FOR_REPAIR",
                 "NO_APPLICABLE_SHADOW_ROUTE"}
RELATION_DISPOSITIONS = {"PLAN", "EXCLUDE", "HOLD"}
CONTROL_PLANE_DISPOSITIONS = {"RETAIN", "ADAPT", "REPLACE_AFTER_EQUIVALENCE"}


def required_instruction_evidence(instruction_value: Any) -> set[str]:
    """Roots a Stage I3 plan must carry to remain reproducible."""
    checked = validate_instruction(instruction_value)
    return {checked[key] for key in (
        "instruction_root", "pipeline_release_sha256",
        "predecessor_portfolio_sha256", "portfolio_status_root",
        "preflight_root", "court_root", "court_evidence_sha256",
        "stage_i1_artifact_sha256", "stage_i2_artifact_sha256",
    )}


def _text(value: Any, code: str, maximum: int = 4096) -> str:
    require(type(value) is str and 0 < len(value) <= maximum
            and value == value.strip(), code)
    return value


def _identifier(value: Any, code: str) -> str:
    value = _text(value, code, 192)
    require(all(ch.isalnum() or ch in "._:-" for ch in value), code)
    return value


def validate_instruction(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "application_id", "thread_id", "pipeline_release_sha256",
        "predecessor_portfolio_sha256", "portfolio_status_root", "preflight_root",
        "court_root", "court_evidence_sha256", "stage_i1_artifact_sha256",
        "stage_i2_artifact_sha256", "stage_i1_status", "matched_relations",
        "cm1_requirements", "cm2_priorities", "requested_plan_fields", "mode",
        "execution_authorized", "composition_authorized", "standing",
        "authority_effect", "real_a5", "g0", "instruction_root",
    })
    require(item["schema"] == INSTRUCTION_SCHEMA, "STAGE_I3_INSTRUCTION_SCHEMA_INVALID")
    _identifier(item["application_id"], "STAGE_I3_APPLICATION_ID_INVALID")
    _text(item["thread_id"], "STAGE_I3_THREAD_ID_INVALID", 256)
    for key in ("pipeline_release_sha256", "predecessor_portfolio_sha256",
                "portfolio_status_root", "preflight_root", "court_root",
                "court_evidence_sha256", "stage_i1_artifact_sha256",
                "stage_i2_artifact_sha256"):
        require_root(item[key])
    require(item["stage_i1_status"] in {"READY_FOR_REVIEW", "HOLD_FOR_REPAIR"},
            "STAGE_I3_STAGE_I1_STATUS_INVALID")
    require(type(item["matched_relations"]) is list, "STAGE_I3_RELATIONS_INVALID")
    seen_relations = set()
    for raw in item["matched_relations"]:
        row = exact_keys(raw, {"provider_application_id", "consumer_application_id",
                               "interface_id", "schema_root", "required", "status"})
        require(row["consumer_application_id"] == item["application_id"]
                and type(row["required"]) is bool and row["status"] == "MATCHED",
                "STAGE_I3_RELATION_BINDING_INVALID")
        require_root(row["schema_root"])
        relation = (row["provider_application_id"], row["interface_id"],
                    row["schema_root"])
        require(relation not in seen_relations, "STAGE_I3_RELATION_DUPLICATE")
        seen_relations.add(relation)
    require(type(item["cm1_requirements"]) is list and len(item["cm1_requirements"]) >= 6
            and len(item["cm1_requirements"]) == len(set(item["cm1_requirements"]))
            and all(type(row) is str and row for row in item["cm1_requirements"]),
            "STAGE_I3_CM1_INVALID")
    require(type(item["cm2_priorities"]) is list and bool(item["cm2_priorities"])
            and len(item["cm2_priorities"]) == len(set(item["cm2_priorities"]))
            and all(type(row) is str and row for row in item["cm2_priorities"]),
            "STAGE_I3_CM2_INVALID")
    required_fields = {"capability_projections", "correspondence_cases",
                       "relation_dispositions", "required_evidence_roots", "holds",
                       "exclusions", "next_action"}
    require(type(item["requested_plan_fields"]) is list
            and set(item["requested_plan_fields"]) == required_fields,
            "STAGE_I3_REQUESTED_FIELDS_INVALID")
    require(item["mode"] == "PLAN_ONLY" and item["execution_authorized"] is False
            and item["composition_authorized"] is False,
            "STAGE_I3_INSTRUCTION_AUTHORITY_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I3_AUTHORITY_CEILING_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "instruction_root"}
    require(item["instruction_root"] == root(body), "STAGE_I3_INSTRUCTION_ROOT_INVALID")
    return deepcopy(item)


def instruction(*, application: dict[str, Any], pipeline_release_sha256: str,
                predecessor_portfolio_sha256: str, portfolio_status_root: str,
                preflight_root: str, court_root: str, court_evidence_sha256: str,
                stage_i1_artifact_sha256: str, stage_i2_artifact_sha256: str,
                stage_i1_status: str, matched_relations: list[dict[str, Any]]) -> dict[str, Any]:
    body = {
        "schema": INSTRUCTION_SCHEMA,
        "application_id": application["id"],
        "thread_id": application["thread_id"],
        "pipeline_release_sha256": pipeline_release_sha256,
        "predecessor_portfolio_sha256": predecessor_portfolio_sha256,
        "portfolio_status_root": portfolio_status_root,
        "preflight_root": preflight_root,
        "court_root": court_root,
        "court_evidence_sha256": court_evidence_sha256,
        "stage_i1_artifact_sha256": stage_i1_artifact_sha256,
        "stage_i2_artifact_sha256": stage_i2_artifact_sha256,
        "stage_i1_status": stage_i1_status,
        "matched_relations": deepcopy(matched_relations),
        "cm1_requirements": [
            "PRESERVE_NATIVE_SEMANTIC_AUTHORITY",
            "PRESERVE_NATIVE_EFFECT_EXECUTORS",
            "BIND_EXACT_STAGE_I1_AND_STAGE_I2_SUBJECTS",
            "PLAN_WITHOUT_APPLICATION_EXECUTION",
            "NO_COMPOSITION_OR_CAPABILITY_GRANT",
            "DISCLOSE_ALL_INHERITED_HOLDS_AND_EXCLUSIONS",
            "REQUIRE_ROOTED_INPUTS_AND_EXPECTED_RESULTS",
        ],
        "cm2_priorities": [
            "MINIMIZE_ADAPTER_SURFACE",
            "MINIMIZE_SEMANTIC_DISTANCE",
            "MAXIMIZE_REUSE_OF_NATIVE_COURTS_AND_RECEIPTS",
        ],
        "requested_plan_fields": [
            "capability_projections", "correspondence_cases", "relation_dispositions",
            "required_evidence_roots", "holds", "exclusions", "next_action",
        ],
        "mode": "PLAN_ONLY", "execution_authorized": False,
        "composition_authorized": False, **BOUNDARY,
    }
    return validate_instruction({**body, "instruction_root": root(body)})


def plan_template(instruction_value: Any) -> dict[str, Any]:
    checked = validate_instruction(instruction_value)
    body = {
        "schema": PLAN_SCHEMA,
        "application_id": checked["application_id"],
        "instruction_root": checked["instruction_root"],
        "stage_i1_artifact_sha256": checked["stage_i1_artifact_sha256"],
        "stage_i2_artifact_sha256": checked["stage_i2_artifact_sha256"],
        "plan_status": "HOLD_FOR_REPAIR" if checked["stage_i1_status"] == "HOLD_FOR_REPAIR"
                       else "READY_FOR_SHADOW_REVIEW",
        "capability_projections": [], "correspondence_cases": [],
        "relation_dispositions": [
            {"provider_application_id": row["provider_application_id"],
             "interface_id": row["interface_id"], "schema_root": row["schema_root"],
             "disposition": "HOLD", "reason": "SESSION_REVIEW_REQUIRED"}
            for row in checked["matched_relations"]
        ],
        "required_evidence_roots": sorted(required_instruction_evidence(checked)),
        "holds": (["INHERITED_STAGE_I1_HOLD"]
                  if checked["stage_i1_status"] == "HOLD_FOR_REPAIR" else []),
        "exclusions": ["NO_APPLICATION_EXECUTION", "NO_CROSS_APPLICATION_CONNECTION",
                       "NO_CAPABILITY_GRANT", "NO_DEPLOYMENT"],
        "next_action": "COMPLETE_STAGE_I3_PLAN_AND_RETURN_FOR_REVIEW",
        "native_semantic_authority_preserved": True,
        "native_effect_executors_preserved": True,
        "shadow_execution_requested": False,
        "composition_requested": False,
        **BOUNDARY,
    }
    return {**body, "plan_root": root(body)}


def validate_plan(value: Any, *, expected_instruction: Any) -> dict[str, Any]:
    expected = validate_instruction(expected_instruction)
    item = exact_keys(value, {
        "schema", "application_id", "instruction_root", "stage_i1_artifact_sha256",
        "stage_i2_artifact_sha256", "plan_status", "capability_projections",
        "correspondence_cases", "relation_dispositions", "required_evidence_roots",
        "holds", "exclusions", "next_action", "native_semantic_authority_preserved",
        "native_effect_executors_preserved", "shadow_execution_requested",
        "composition_requested", "standing", "authority_effect", "real_a5", "g0",
        "plan_root",
    })
    require(item["schema"] == PLAN_SCHEMA, "STAGE_I3_PLAN_SCHEMA_INVALID")
    for key in ("application_id", "instruction_root", "stage_i1_artifact_sha256",
                "stage_i2_artifact_sha256"):
        require(item[key] == expected[key], "STAGE_I3_PLAN_BINDING_INVALID")
    require(item["plan_status"] in PLAN_STATUSES, "STAGE_I3_PLAN_STATUS_INVALID")
    if expected["stage_i1_status"] == "HOLD_FOR_REPAIR":
        require(item["plan_status"] == "HOLD_FOR_REPAIR"
                and "INHERITED_STAGE_I1_HOLD" in item["holds"],
                "STAGE_I3_INHERITED_HOLD_LOST")
    require(type(item["capability_projections"]) is list,
            "STAGE_I3_CAPABILITY_PROJECTIONS_INVALID")
    capability_ids = set()
    for raw in item["capability_projections"]:
        row = exact_keys(raw, {"capability_id", "native_route", "ucm_projection",
                               "effect_class", "input_schema_root", "output_schema_root",
                               "control_plane_disposition", "case_ids"})
        capability_id = _identifier(row["capability_id"], "STAGE_I3_CAPABILITY_ID_INVALID")
        require(capability_id not in capability_ids, "STAGE_I3_CAPABILITY_DUPLICATE")
        capability_ids.add(capability_id)
        _text(row["native_route"], "STAGE_I3_NATIVE_ROUTE_INVALID")
        _text(row["ucm_projection"], "STAGE_I3_UCM_PROJECTION_INVALID")
        require(row["effect_class"] in EFFECT_CLASSES,
                "STAGE_I3_EFFECT_CLASS_INVALID")
        require_root(row["input_schema_root"]); require_root(row["output_schema_root"])
        require(row["control_plane_disposition"] in CONTROL_PLANE_DISPOSITIONS,
                "STAGE_I3_CONTROL_PLANE_DISPOSITION_INVALID")
        require(type(row["case_ids"]) is list and bool(row["case_ids"])
                and len(row["case_ids"]) == len(set(row["case_ids"]))
                and all(type(case_id) is str and case_id for case_id in row["case_ids"]),
                "STAGE_I3_CASE_IDS_INVALID")
    case_ids = set()
    for raw in item["correspondence_cases"]:
        row = exact_keys(raw, {"id", "capability_id", "input_root",
                               "expected_native_decision", "expected_ucm_decision",
                               "expected_native_result_root", "expected_ucm_result_root",
                               "expected_equivalence", "evidence_requirements"})
        case_id = _identifier(row["id"], "STAGE_I3_CASE_ID_INVALID")
        require(case_id not in case_ids and row["capability_id"] in capability_ids,
                "STAGE_I3_CASE_BINDING_INVALID")
        case_ids.add(case_id); require_root(row["input_root"])
        _text(row["expected_native_decision"], "STAGE_I3_NATIVE_DECISION_INVALID")
        _text(row["expected_ucm_decision"], "STAGE_I3_UCM_DECISION_INVALID")
        require_root(row["expected_native_result_root"])
        require_root(row["expected_ucm_result_root"])
        require(row["expected_equivalence"] is True,
                "STAGE_I3_EXPECTED_EQUIVALENCE_INVALID")
        require(row["expected_native_decision"] == row["expected_ucm_decision"]
                and row["expected_native_result_root"] == row["expected_ucm_result_root"],
                "STAGE_I3_EXPECTED_RESULT_DIVERGENCE")
        require(type(row["evidence_requirements"]) is list
                and all(type(requirement) is str and requirement
                        for requirement in row["evidence_requirements"]),
                "STAGE_I3_EVIDENCE_REQUIREMENTS_INVALID")
    case_capability = {row["id"]: row["capability_id"]
                       for row in item["correspondence_cases"]}
    projected_case_ids = []
    for row in item["capability_projections"]:
        for case_id in row["case_ids"]:
            require(case_id in case_capability
                    and case_capability[case_id] == row["capability_id"],
                    "STAGE_I3_CAPABILITY_CASE_OWNERSHIP_INVALID")
            projected_case_ids.append(case_id)
    require(len(projected_case_ids) == len(case_ids)
            and len(projected_case_ids) == len(set(projected_case_ids))
            and set(projected_case_ids) == case_ids,
            "STAGE_I3_CAPABILITY_CASE_COVERAGE_INVALID")
    expected_relations = {(row["provider_application_id"], row["interface_id"],
                           row["schema_root"]) for row in expected["matched_relations"]}
    observed_relations = set()
    for raw in item["relation_dispositions"]:
        row = exact_keys(raw, {"provider_application_id", "interface_id", "schema_root",
                               "disposition", "reason"})
        require_root(row["schema_root"])
        relation = (row["provider_application_id"], row["interface_id"],
                    row["schema_root"])
        require(relation not in observed_relations,
                "STAGE_I3_RELATION_DISPOSITION_DUPLICATE")
        observed_relations.add(relation)
        require(row["disposition"] in RELATION_DISPOSITIONS
                and type(row["reason"]) is str and row["reason"],
                "STAGE_I3_RELATION_DISPOSITION_INVALID")
    require(observed_relations == expected_relations,
            "STAGE_I3_RELATION_COVERAGE_INVALID")
    for key in ("required_evidence_roots",):
        require(type(item[key]) is list and len(item[key]) == len(set(item[key])),
                "STAGE_I3_EVIDENCE_ROOTS_INVALID")
        for evidence_root in item[key]: require_root(evidence_root)
    require(required_instruction_evidence(expected).issubset(
        set(item["required_evidence_roots"])),
        "STAGE_I3_REQUIRED_EVIDENCE_MISSING")
    for key in ("holds", "exclusions"):
        require(type(item[key]) is list and len(item[key]) == len(set(item[key]))
                and all(type(row) is str and row for row in item[key]),
                "STAGE_I3_LIST_INVALID")
    require(type(item["next_action"]) is str and item["next_action"],
            "STAGE_I3_NEXT_ACTION_INVALID")
    require(item["native_semantic_authority_preserved"] is True
            and item["native_effect_executors_preserved"] is True
            and item["shadow_execution_requested"] is False
            and item["composition_requested"] is False,
            "STAGE_I3_PLAN_AUTHORITY_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I3_AUTHORITY_CEILING_INVALID")
    if item["plan_status"] != "NO_APPLICABLE_SHADOW_ROUTE":
        require(bool(item["capability_projections"]) and bool(item["correspondence_cases"]),
                "STAGE_I3_PLAN_EMPTY")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "plan_root"}
    require(item["plan_root"] == root(body), "STAGE_I3_PLAN_ROOT_INVALID")
    return deepcopy(item)

"""Stage I4 c3 exact preparation, review, relation, and gate contracts.

The c3 surface is intentionally information-only.  It can prepare and validate
the complete execution envelope and can verify a future native receipt, but it
cannot grant authority or execute an application itself.
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
from .native_runner import build_preflight, validate_binding
from .stage3 import validate_instruction, validate_plan
from .stage4 import QUALIFIED_VERDICT, validate_review_disposition


REVIEW_POLICY_SCHEMA = "mosaic.ucm.stage-i4-review-trust-policy.v0.1"
REVIEW_ARCHIVE_SCHEMA = "mosaic.ucm.stage-i4-trusted-review-archive.v0.1"
REVIEW_ARCHIVE_ROLE = "UCM_AMCAS_TRUSTED_REVIEW_EVIDENCE"
ELIGIBILITY_SCHEMA = "mosaic.ucm.stage-i4-eligibility.v0.3"
RELATION_MAP_SCHEMA = "mosaic.ucm.stage-i4-relation-case-map.v0.1"
CONTEXT_SCHEMA = "mosaic.ucm.stage-i4-execution-context.v0.1"
RUN_CONTRACT_SCHEMA = "mosaic.ucm.stage-i4-run-contract.v0.3"
TERMINAL_SCHEMA = "mosaic.ucm.stage-i4-terminal-operation.v0.1"
REVIEW_FILES = {
    "REPORT.md", "FINDINGS.json", "RECOMPUTE.json", "REVIEW-DISPOSITION.json",
}
SHADOW_EFFECT_CLASSES = {"PURE_COMPUTATION", "READ_ONLY"}


def _sha(raw: bytes) -> str:
    require(type(raw) is bytes, "STAGE_I4_BYTES_REQUIRED")
    return hashlib.sha256(raw).hexdigest()


def _identifier(value: Any, code: str) -> str:
    require(type(value) is str and value == value.strip() and 0 < len(value) <= 192
            and all(ch.isalnum() or ch in "._:-" for ch in value), code)
    return value


def _text_list(value: Any, code: str, *, nonempty: bool = False) -> list[str]:
    require(type(value) is list and (bool(value) or not nonempty)
            and all(type(row) is str and row == row.strip() and bool(row) for row in value)
            and len(value) == len(set(value)), code)
    return value


def _member(raw: bytes, name: str) -> bytes:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            require(archive.namelist().count(name) == 1,
                    "STAGE_I4_REVIEW_MEMBER_INVALID", detail=name)
            return archive.read(name)
    except (zipfile.BadZipFile, KeyError, OSError) as error:
        raise Refusal("STAGE_I4_REVIEW_ARCHIVE_INVALID", detail=type(error).__name__) from error


def validate_review_policy(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "policy_id", "reviewer_identity_root", "accepted_review_classes",
        "expected_archive_sha256", "expected_subject_root", "expected_source_root",
        "expected_qualification_root", "expected_disposition_root",
        "expected_file_sha256", "standing", "authority_effect", "real_a5", "g0",
        "policy_root",
    })
    require(item["schema"] == REVIEW_POLICY_SCHEMA,
            "STAGE_I4_REVIEW_TRUST_POLICY_SCHEMA_INVALID")
    _identifier(item["policy_id"], "STAGE_I4_REVIEW_TRUST_POLICY_ID_INVALID")
    for key in ("reviewer_identity_root", "expected_archive_sha256",
                "expected_subject_root", "expected_source_root",
                "expected_qualification_root", "expected_disposition_root"):
        require_root(item[key])
    require(item["accepted_review_classes"] == ["INDEPENDENT_REVIEW"],
            "STAGE_I4_REVIEW_CLASS_POLICY_INVALID")
    require(type(item["expected_file_sha256"]) is dict
            and set(item["expected_file_sha256"]) == REVIEW_FILES,
            "STAGE_I4_REVIEW_FILE_POLICY_INVALID")
    for value_root in item["expected_file_sha256"].values():
        require_root(value_root)
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_AUTHORITY_CEILING_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "policy_root"}
    require(item["policy_root"] == root(body), "STAGE_I4_REVIEW_POLICY_ROOT_INVALID")
    return deepcopy(item)


def verify_trusted_review_archive(raw: bytes, *, policy: Any) -> dict[str, Any]:
    checked_policy = validate_review_policy(policy)
    require(_sha(raw) == checked_policy["expected_archive_sha256"],
            "STAGE_I4_REVIEW_ARCHIVE_PIN_MISMATCH")
    manifest = verify_deterministic_zip(raw, expected_schema=REVIEW_ARCHIVE_SCHEMA,
                                        expected_role=REVIEW_ARCHIVE_ROLE)
    require({row["path"] for row in manifest["files"]} == REVIEW_FILES,
            "STAGE_I4_REVIEW_FILE_SET_INVALID")
    observed = {path: _sha(_member(raw, path)) for path in REVIEW_FILES}
    require(observed == checked_policy["expected_file_sha256"],
            "STAGE_I4_REVIEW_FILE_PIN_MISMATCH")
    disposition = validate_review_disposition(
        strict_loads(_member(raw, "REVIEW-DISPOSITION.json")))
    findings = exact_keys(strict_loads(_member(raw, "FINDINGS.json")), {
        "schema", "verdict", "findings", "standing", "authority_effect",
        "real_a5", "g0", "findings_root",
    })
    require(findings["schema"] == "mosaic.ucm.stage-i4-review-findings.v0.1"
            and findings["verdict"] == disposition["verdict"]
            and findings["findings"] == disposition["findings"]
            and {key: findings[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_REVIEW_FINDINGS_BINDING_INVALID")
    require(findings["findings_root"] == root({key: deepcopy(value) for key, value
            in findings.items() if key != "findings_root"}),
            "STAGE_I4_REVIEW_FINDINGS_ROOT_INVALID")
    recompute = exact_keys(strict_loads(_member(raw, "RECOMPUTE.json")), {
        "schema", "reviewed_subject_root", "reviewed_source_root",
        "reviewed_qualification_root", "status", "standing", "authority_effect",
        "real_a5", "g0", "recompute_root",
    })
    require(recompute["schema"] == "mosaic.ucm.stage-i4-review-recompute.v0.1"
            and recompute["reviewed_subject_root"] == disposition["reviewed_subject_root"]
            and recompute["reviewed_source_root"] == disposition["reviewed_source_root"]
            and recompute["reviewed_qualification_root"] == disposition["reviewed_qualification_root"]
            and recompute["status"] == "PASS"
            and {key: recompute[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_REVIEW_RECOMPUTE_BINDING_INVALID")
    require(recompute["recompute_root"] == root({key: deepcopy(value) for key, value
            in recompute.items() if key != "recompute_root"}),
            "STAGE_I4_REVIEW_RECOMPUTE_ROOT_INVALID")
    try:
        report = _member(raw, "REPORT.md").decode("utf-8")
    except UnicodeDecodeError as error:
        raise Refusal("STAGE_I4_REVIEW_REPORT_INVALID", detail="UTF8") from error
    require(("Verdict: `" + disposition["verdict"] + "`") in report,
            "STAGE_I4_REVIEW_REPORT_VERDICT_INVALID")
    require(disposition["review_class"] in checked_policy["accepted_review_classes"]
            and disposition["reviewer_identity_root"] == checked_policy["reviewer_identity_root"]
            and disposition["reviewed_subject_root"] == checked_policy["expected_subject_root"]
            and disposition["reviewed_source_root"] == checked_policy["expected_source_root"]
            and disposition["reviewed_qualification_root"] == checked_policy["expected_qualification_root"]
            and disposition["disposition_root"] == checked_policy["expected_disposition_root"],
            "STAGE_I4_REVIEW_PROVENANCE_INVALID")
    return {
        "archive_sha256": _sha(raw),
        "manifest_root": manifest["manifest_root"],
        "policy_root": checked_policy["policy_root"],
        "disposition": disposition,
        "file_sha256": observed,
        "findings_root": findings["findings_root"],
        "recompute_root": recompute["recompute_root"],
    }


def _review_application(disposition: dict[str, Any], application_id: str) -> dict[str, Any]:
    rows = [row for row in disposition["applications"]
            if row["application_id"] == application_id]
    require(len(rows) == 1, "STAGE_I4_REVIEW_SUBJECT_APPLICATION_MISSING")
    return rows[0]


def derive_eligibility(*, instruction: Any, plan: Any, review_archive: bytes,
                       review_policy: Any) -> dict[str, Any]:
    checked_instruction = validate_instruction(instruction)
    checked_plan = validate_plan(plan, expected_instruction=checked_instruction)
    review = verify_trusted_review_archive(review_archive, policy=review_policy)
    disposition = review["disposition"]
    reviewed = _review_application(disposition, checked_plan["application_id"])
    require(reviewed["instruction_root"] == checked_instruction["instruction_root"]
            and reviewed["plan_root"] == checked_plan["plan_root"],
            "STAGE_I4_REVIEW_SUBJECT_BINDING_INVALID")
    preparation = checked_plan["plan_status"] == "READY_FOR_SHADOW_REVIEW"
    execution = (preparation and disposition["verdict"] == QUALIFIED_VERDICT
                 and not checked_plan["holds"])
    reasons: list[str] = []
    if not preparation:
        reasons.append("STAGE_I3_PLAN_NOT_REVIEW_READY")
    if disposition["verdict"] != QUALIFIED_VERDICT:
        reasons.append("STAGE_I3_TERMINAL_REVIEW_REQUIRED")
    if checked_plan["holds"]:
        reasons.append("UNRESOLVED_PLAN_HOLDS")
    if not reasons:
        reasons.append("ELIGIBILITY_CONDITIONS_SATISFIED")
    body = {
        "schema": ELIGIBILITY_SCHEMA,
        "application_id": checked_plan["application_id"],
        "instruction_root": checked_instruction["instruction_root"],
        "plan_root": checked_plan["plan_root"],
        "review_archive_sha256": review["archive_sha256"],
        "review_manifest_root": review["manifest_root"],
        "review_policy_root": review["policy_root"],
        "review_disposition_root": disposition["disposition_root"],
        "reviewed_subject_root": disposition["reviewed_subject_root"],
        "reviewed_source_root": disposition["reviewed_source_root"],
        "reviewed_qualification_root": disposition["reviewed_qualification_root"],
        "reviewer_identity_root": disposition["reviewer_identity_root"],
        "review_class": disposition["review_class"],
        "review_verdict": disposition["verdict"],
        "unresolved_holds": deepcopy(checked_plan["holds"]),
        "eligible_for_shadow_preparation": preparation,
        "eligible_for_shadow_execution": execution,
        "reason_codes": reasons,
        "native_semantic_authority_preserved": True,
        "native_effect_executors_preserved": True,
        "execution_authorized": False,
        "composition_authorized": False,
        **BOUNDARY,
    }
    return {**body, "eligibility_root": root(body)}


def _relation_id(application_id: str, row: dict[str, Any]) -> str:
    return root({
        "provider_application_id": row["provider_application_id"],
        "consumer_application_id": application_id,
        "interface_id": row["interface_id"],
        "schema_root": row["schema_root"],
    })


def validate_relation_case_map(value: Any, *, expected_plan: Any,
                               expected_instruction: Any) -> dict[str, Any]:
    instruction = validate_instruction(expected_instruction)
    plan = validate_plan(expected_plan, expected_instruction=instruction)
    item = exact_keys(value, {
        "schema", "application_id", "plan_root", "relations", "case_dependencies",
        "standing", "authority_effect", "real_a5", "g0", "map_root",
    })
    require(item["schema"] == RELATION_MAP_SCHEMA
            and item["application_id"] == plan["application_id"]
            and item["plan_root"] == plan["plan_root"],
            "STAGE_I4_RELATION_MAP_BINDING_INVALID")
    expected_relations = {}
    for row in plan["relation_dispositions"]:
        relation_id = _relation_id(plan["application_id"], row)
        expected_relations[relation_id] = {
            "relation_id": relation_id,
            "provider_application_id": row["provider_application_id"],
            "consumer_application_id": plan["application_id"],
            "interface_id": row["interface_id"],
            "schema_root": row["schema_root"],
            "disposition": row["disposition"],
        }
    require(type(item["relations"]) is list, "STAGE_I4_RELATION_MAP_INVALID")
    observed_relations = {}
    for raw in item["relations"]:
        row = exact_keys(raw, {"relation_id", "provider_application_id",
                               "consumer_application_id", "interface_id",
                               "schema_root", "disposition"})
        require_root(row["relation_id"])
        require(row["relation_id"] not in observed_relations,
                "STAGE_I4_RELATION_MAP_DUPLICATE")
        observed_relations[row["relation_id"]] = row
    require(observed_relations == expected_relations,
            "STAGE_I4_RELATION_MAP_COVERAGE_INVALID")
    expected_cases = {row["id"] for row in plan["correspondence_cases"]}
    require(type(item["case_dependencies"]) is list,
            "STAGE_I4_CASE_DEPENDENCY_MAP_INVALID")
    observed_cases: dict[str, list[str]] = {}
    for raw in item["case_dependencies"]:
        row = exact_keys(raw, {"case_id", "relation_ids"})
        _identifier(row["case_id"], "STAGE_I4_CASE_ID_INVALID")
        require(row["case_id"] not in observed_cases,
                "STAGE_I4_CASE_DEPENDENCY_DUPLICATE")
        _text_list(row["relation_ids"], "STAGE_I4_CASE_DEPENDENCY_INVALID")
        for relation_id in row["relation_ids"]:
            require_root(relation_id)
            require(relation_id in expected_relations
                    and expected_relations[relation_id]["disposition"] == "PLAN",
                    "STAGE_I4_CASE_DEPENDS_ON_HELD_RELATION")
        observed_cases[row["case_id"]] = row["relation_ids"]
    require(set(observed_cases) == expected_cases,
            "STAGE_I4_CASE_DEPENDENCY_COVERAGE_INVALID")
    planned = {key for key, row in expected_relations.items()
               if row["disposition"] == "PLAN"}
    covered = {relation_id for rows in observed_cases.values() for relation_id in rows}
    require(planned.issubset(covered), "STAGE_I4_PLANNED_RELATION_UNCOVERED")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_AUTHORITY_CEILING_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "map_root"}
    require(item["map_root"] == root(body), "STAGE_I4_RELATION_MAP_ROOT_INVALID")
    return deepcopy(item)


def validate_execution_context(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "identity_root", "session_root", "jurisdiction_root", "generation",
        "policy_root", "budget_root", "rollback_root", "standing",
        "authority_effect", "real_a5", "g0", "context_root",
    })
    require(item["schema"] == CONTEXT_SCHEMA, "STAGE_I4_CONTEXT_SCHEMA_INVALID")
    for key in ("identity_root", "session_root", "jurisdiction_root", "policy_root",
                "budget_root", "rollback_root"):
        require_root(item[key])
    require(type(item["generation"]) is int and item["generation"] >= 1,
            "STAGE_I4_CONTEXT_GENERATION_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_AUTHORITY_CEILING_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "context_root"}
    require(item["context_root"] == root(body), "STAGE_I4_CONTEXT_ROOT_INVALID")
    return deepcopy(item)


def _validate_selection(value: Any, *, all_case_ids: set[str],
                        relation_map: dict[str, Any]) -> dict[str, Any]:
    item = exact_keys(value, {"mode", "selected_case_ids", "omitted_case_ids",
                              "covered_relation_ids", "selection_basis_roots", "rationale"})
    require(item["mode"] in {"FULL", "BOUNDED"}, "STAGE_I4_SELECTION_MODE_INVALID")
    _text_list(item["selected_case_ids"], "STAGE_I4_SELECTION_INVALID", nonempty=True)
    _text_list(item["omitted_case_ids"], "STAGE_I4_SELECTION_INVALID")
    _text_list(item["covered_relation_ids"], "STAGE_I4_SELECTION_INVALID")
    _text_list(item["selection_basis_roots"], "STAGE_I4_SELECTION_INVALID")
    for value_root in item["covered_relation_ids"] + item["selection_basis_roots"]:
        require_root(value_root)
    require(set(item["selected_case_ids"]).isdisjoint(item["omitted_case_ids"])
            and set(item["selected_case_ids"]) | set(item["omitted_case_ids"]) == all_case_ids,
            "STAGE_I4_SELECTION_COVERAGE_INVALID")
    dependencies = {row["case_id"]: row["relation_ids"]
                    for row in relation_map["case_dependencies"]}
    covered = sorted({relation_id for case_id in item["selected_case_ids"]
                      for relation_id in dependencies[case_id]})
    planned = sorted(row["relation_id"] for row in relation_map["relations"]
                     if row["disposition"] == "PLAN")
    require(item["covered_relation_ids"] == covered and set(planned).issubset(covered),
            "STAGE_I4_SELECTION_RELATION_COVERAGE_INVALID")
    if item["mode"] == "FULL":
        require(not item["omitted_case_ids"] and set(item["selected_case_ids"]) == all_case_ids,
                "STAGE_I4_FULL_SELECTION_INVALID")
    else:
        require(bool(item["omitted_case_ids"]) and bool(item["selection_basis_roots"])
                and type(item["rationale"]) is str and bool(item["rationale"].strip()),
                "STAGE_I4_BOUNDED_SELECTION_INVALID")
    return deepcopy(item)


def build_run_contract(*, eligibility: Any, plan: Any, instruction: Any,
                       review_archive: bytes, review_policy: Any,
                       relation_case_map: Any, execution_context: Any,
                       native_runner_binding: Any, selection: Any) -> dict[str, Any]:
    checked_instruction = validate_instruction(instruction)
    checked_plan = validate_plan(plan, expected_instruction=checked_instruction)
    derived = derive_eligibility(instruction=checked_instruction, plan=checked_plan,
                                 review_archive=review_archive,
                                 review_policy=review_policy)
    require(eligibility == derived, "STAGE_I4_ELIGIBILITY_REDERIVATION_INVALID")
    require(derived["eligible_for_shadow_execution"],
            "STAGE_I4_EXECUTION_ELIGIBILITY_REQUIRED")
    relation_map = validate_relation_case_map(relation_case_map,
        expected_plan=checked_plan, expected_instruction=checked_instruction)
    context = validate_execution_context(execution_context)
    binding = validate_binding(native_runner_binding)
    all_cases = {row["id"] for row in checked_plan["correspondence_cases"]}
    checked_selection = _validate_selection(selection, all_case_ids=all_cases,
                                            relation_map=relation_map)
    selected = set(checked_selection["selected_case_ids"])
    dependencies = {row["case_id"]: row["relation_ids"]
                    for row in relation_map["case_dependencies"]}
    projections = {row["capability_id"]: row for row in checked_plan["capability_projections"]}
    schedule = []
    for case in checked_plan["correspondence_cases"]:
        if case["id"] not in selected:
            continue
        projection = projections[case["capability_id"]]
        require(projection["effect_class"] in SHADOW_EFFECT_CLASSES,
                "STAGE_I4_CASE_EFFECT_OUTSIDE_MEMBRANE")
        schedule.append({
            "case_id": case["id"], "capability_id": case["capability_id"],
            "input_root": case["input_root"], "native_route": projection["native_route"],
            "ucm_projection": projection["ucm_projection"],
            "effect_class": projection["effect_class"],
            "relation_ids": dependencies[case["id"]],
            "expected_native_decision": case["expected_native_decision"],
            "expected_ucm_decision": case["expected_ucm_decision"],
            "expected_native_result_root": case["expected_native_result_root"],
            "expected_ucm_result_root": case["expected_ucm_result_root"],
        })
    body = {
        "schema": RUN_CONTRACT_SCHEMA,
        "application_id": checked_plan["application_id"],
        "eligibility_root": derived["eligibility_root"],
        "instruction_root": checked_instruction["instruction_root"],
        "plan_root": checked_plan["plan_root"],
        "review_policy_root": derived["review_policy_root"],
        "review_archive_sha256": derived["review_archive_sha256"],
        "relation_case_map_root": relation_map["map_root"],
        "case_selection": checked_selection,
        "case_schedule": schedule,
        "execution_context": context,
        "native_runner_binding": binding,
        "effect_membrane": {
            "allowed_effect_classes": sorted(SHADOW_EFFECT_CLASSES),
            "native_effect_executor": binding["native_owner"],
            "fallback_execution_allowed": False,
        },
        "gate_requirements": ["UCM.INTEGRATION.G1", "UCM.INTEGRATION.G2",
                              "UCM.INTEGRATION.G3"],
        "mode": "SEALED_SHADOW_PREPARATION",
        "application_contact_authorized": False,
        "execution_authorized": False,
        "composition_authorized": False,
        **BOUNDARY,
    }
    return {**body, "run_contract_root": root(body)}


def build_terminal_refusal(*, run_contract: Any) -> dict[str, Any]:
    contract = exact_keys(run_contract, {
        "schema", "application_id", "eligibility_root", "instruction_root", "plan_root",
        "review_policy_root", "review_archive_sha256", "relation_case_map_root",
        "case_selection", "case_schedule", "execution_context", "native_runner_binding",
        "effect_membrane", "gate_requirements", "mode", "application_contact_authorized",
        "execution_authorized", "composition_authorized", "standing", "authority_effect",
        "real_a5", "g0", "run_contract_root",
    })
    require(contract["schema"] == RUN_CONTRACT_SCHEMA
            and contract["run_contract_root"] == root({
                key: deepcopy(raw) for key, raw in contract.items()
                if key != "run_contract_root"
            }), "STAGE_I4_RUN_CONTRACT_INVALID")
    context = validate_execution_context(contract["execution_context"])
    preflight = build_preflight(
        run_contract_root=contract["run_contract_root"],
        execution_context_root=context["context_root"],
        binding=contract["native_runner_binding"],
        requested_effect_classes=sorted({row["effect_class"] for row in contract["case_schedule"]}),
        execution_authorized=contract["execution_authorized"],
    )
    require(preflight["decision"] == "REFUSE", "STAGE_I4_REFUSAL_PREFLIGHT_INVALID")
    g1_body = {
        "gate": "G1_SENTINEL", "run_contract_root": contract["run_contract_root"],
        "context_root": context["context_root"], "preflight_root": preflight["preflight_root"],
        "decision": "REFUSE", "reason_codes": [preflight["reason_code"]], **BOUNDARY,
    }
    g1 = {**g1_body, "receipt_root": root(g1_body)}
    g2_body = {
        "gate": "G2_WITNESS", "g1_root": g1["receipt_root"],
        "native_receipt_root": None, "completion_status": "REFUSED",
        "recovery_status": "NOT_REQUIRED", "case_results": [], **BOUNDARY,
    }
    g2 = {**g2_body, "receipt_root": root(g2_body)}
    g3_body = {
        "gate": "G3_DIAGNOSTIC", "g2_root": g2["receipt_root"],
        "classification": "REFUSED", "finding_codes": [preflight["reason_code"]],
        "next_action": "ESTABLISH_PINNED_NATIVE_RUNNER_AND_EXPLICIT_AUTHORITY",
        **BOUNDARY,
    }
    g3 = {**g3_body, "receipt_root": root(g3_body)}
    body = {
        "schema": TERMINAL_SCHEMA,
        "run_contract_root": contract["run_contract_root"],
        "execution_context_root": context["context_root"],
        "native_preflight": preflight,
        "g1_sentinel": g1,
        "g2_witness": g2,
        "g3_diagnostic": g3,
        "terminal_status": "REFUSED",
        "effects_observed": [],
        "native_effect_executor_preserved": True,
        **BOUNDARY,
    }
    return {**body, "operation_root": root(body)}

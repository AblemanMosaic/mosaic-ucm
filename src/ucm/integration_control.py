"""Fixed-denominator repair and test control-plane contracts."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY


PLAN_SCHEMA = "mosaic.ucm.integration-control-plan.v0.1"
RESULT_SCHEMA = "mosaic.ucm.integration-control-result.v0.1"
LANES = {"STATIC", "TARGETED", "QUALIFICATION", "OPERATOR_TIER1", "INDEPENDENT_REVIEW"}
DISPOSITIONS = {"CLOSED", "ACCEPTED", "CARRIED", "REFUSED"}


def _id(value: Any, code: str) -> str:
    require(type(value) is str and value == value.strip() and 0 < len(value) <= 192
            and all(ch.isalnum() or ch in "._:-" for ch in value), code)
    return value


def build_control_plan(*, subject_root: str, finding_ids: list[str],
                       impact_surface_ids: list[str], test_ids: list[str],
                       selected_lanes: list[str], progress_contract_root: str,
                       qualification_required: bool) -> dict[str, Any]:
    require_root(subject_root)
    require_root(progress_contract_root)
    for rows, code in ((finding_ids, "CONTROL_FINDINGS_INVALID"),
                       (impact_surface_ids, "CONTROL_IMPACTS_INVALID"),
                       (test_ids, "CONTROL_TESTS_INVALID")):
        require(type(rows) is list and rows == sorted(set(rows)) and bool(rows), code)
        for value in rows:
            _id(value, code)
    require(type(selected_lanes) is list and selected_lanes == sorted(set(selected_lanes))
            and bool(selected_lanes) and set(selected_lanes) <= LANES,
            "CONTROL_LANES_INVALID")
    require(type(qualification_required) is bool, "CONTROL_QUALIFICATION_FLAG_INVALID")
    require(("QUALIFICATION" in selected_lanes) == qualification_required,
            "CONTROL_QUALIFICATION_LANE_MISMATCH")
    body = {"schema": PLAN_SCHEMA, "subject_root": subject_root,
            "finding_ids": list(finding_ids),
            "impact_surface_ids": list(impact_surface_ids),
            "test_ids": list(test_ids), "selected_lanes": list(selected_lanes),
            "fixed_denominator": len(test_ids),
            "progress_contract_root": progress_contract_root,
            "progress_is_semantic": False,
            "qualification_required": qualification_required, **BOUNDARY}
    return {**body, "control_plan_root": root(body)}


def validate_control_plan(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "subject_root", "finding_ids",
        "impact_surface_ids", "test_ids", "selected_lanes", "fixed_denominator",
        "progress_contract_root", "progress_is_semantic", "qualification_required",
        "standing", "authority_effect", "real_a5", "g0", "control_plan_root"})
    expected = build_control_plan(subject_root=item["subject_root"],
        finding_ids=item["finding_ids"], impact_surface_ids=item["impact_surface_ids"],
        test_ids=item["test_ids"], selected_lanes=item["selected_lanes"],
        progress_contract_root=item["progress_contract_root"],
        qualification_required=item["qualification_required"])
    require(item == expected and item["progress_is_semantic"] is False,
            "CONTROL_PLAN_INVALID")
    return deepcopy(item)


def build_control_result(*, plan: dict[str, Any], test_results: list[dict[str, Any]],
                         finding_dispositions: list[dict[str, Any]]) -> dict[str, Any]:
    plan = validate_control_plan(plan)
    require(type(test_results) is list, "CONTROL_TEST_RESULTS_INVALID")
    by_test: dict[str, dict[str, Any]] = {}
    for row in test_results:
        item = exact_keys(row, {"test_id", "status", "evidence_root"})
        _id(item["test_id"], "CONTROL_TEST_ID_INVALID")
        require(item["status"] in {"PASS", "FAIL", "NOT_RUN"},
                "CONTROL_TEST_STATUS_INVALID")
        require_root(item["evidence_root"])
        require(item["test_id"] not in by_test, "CONTROL_TEST_ID_DUPLICATE")
        by_test[item["test_id"]] = deepcopy(item)
    require(sorted(by_test) == plan["test_ids"], "CONTROL_TEST_DENOMINATOR_MISMATCH")
    require(type(finding_dispositions) is list, "CONTROL_DISPOSITIONS_INVALID")
    by_finding: dict[str, dict[str, Any]] = {}
    for row in finding_dispositions:
        item = exact_keys(row, {"finding_id", "disposition", "evidence_roots"})
        _id(item["finding_id"], "CONTROL_FINDING_ID_INVALID")
        require(item["disposition"] in DISPOSITIONS, "CONTROL_DISPOSITION_INVALID")
        require(type(item["evidence_roots"]) is list
                and item["evidence_roots"] == sorted(set(item["evidence_roots"]))
                and bool(item["evidence_roots"]), "CONTROL_FINDING_EVIDENCE_INVALID")
        for evidence_root in item["evidence_roots"]:
            require_root(evidence_root)
        require(item["finding_id"] not in by_finding, "CONTROL_FINDING_ID_DUPLICATE")
        by_finding[item["finding_id"]] = deepcopy(item)
    require(sorted(by_finding) == plan["finding_ids"],
            "CONTROL_FINDING_DENOMINATOR_MISMATCH")
    ordered_tests = [by_test[test_id] for test_id in plan["test_ids"]]
    ordered_findings = [by_finding[finding_id] for finding_id in plan["finding_ids"]]
    status = "PASS" if all(row["status"] == "PASS" for row in ordered_tests) and all(
        row["disposition"] in {"CLOSED", "ACCEPTED", "CARRIED"}
        for row in ordered_findings) else "HOLD_FOR_REPAIR"
    body = {"schema": RESULT_SCHEMA, "control_plan_root": plan["control_plan_root"],
            "subject_root": plan["subject_root"], "test_results": ordered_tests,
            "finding_dispositions": ordered_findings,
            "completed_denominator": sum(row["status"] != "NOT_RUN" for row in ordered_tests),
            "fixed_denominator": plan["fixed_denominator"], "status": status, **BOUNDARY}
    return {**body, "control_result_root": root(body)}


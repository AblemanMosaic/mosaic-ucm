"""Semantic update and rollback contracts; preparation only, never deployment authority."""
from __future__ import annotations
from copy import deepcopy
from typing import Any

from .canonical import canonical_bytes, exact_keys, require, require_root, root
from .maturity_semantics import BOUNDARY, seal
from .operational_explanation import verify_semantic_change_plan


def make_rollback_rehearsal(*, predecessor_root: str, successor_root: str,
                            mutated_root: str, restored_root: str,
                            action_roots: list[str]) -> dict[str, Any]:
    for value in (predecessor_root, successor_root, mutated_root, restored_root): require_root(value)
    require(type(action_roots) is list and action_roots == sorted(set(action_roots)) and bool(action_roots),
            "OPERATIONAL_ROLLBACK_ACTIONS_INVALID")
    for value in action_roots: require_root(value)
    require(mutated_root != predecessor_root and restored_root == predecessor_root,
            "OPERATIONAL_ROLLBACK_NOT_RESTORATIVE")
    return seal({"schema": "ucl.ucm.operational_rollback_rehearsal.v1",
        "predecessor_root": predecessor_root, "successor_root": successor_root,
        "mutated_root": mutated_root, "restored_root": restored_root,
        "action_roots": action_roots, "status": "PASS_RESTORED", **BOUNDARY})


def verify_rollback_rehearsal(value: Any, *, expected_root: str) -> dict[str, Any]:
    require(type(value) is dict and value.get("schema") == "ucl.ucm.operational_rollback_rehearsal.v1",
            "OPERATIONAL_ROLLBACK_INVALID")
    rebuilt = make_rollback_rehearsal(predecessor_root=value.get("predecessor_root"),
        successor_root=value.get("successor_root"), mutated_root=value.get("mutated_root"),
        restored_root=value.get("restored_root"), action_roots=value.get("action_roots"))
    require(canonical_bytes(value) == canonical_bytes(rebuilt) and value["root"] == require_root(expected_root),
            "OPERATIONAL_ROLLBACK_RECONSTRUCTION_MISMATCH")
    return rebuilt


def make_court_result(*, subject_root: str, checker_root: str,
                      cases: list[dict[str, str]]) -> dict[str, Any]:
    require_root(subject_root); require_root(checker_root)
    require(type(cases) is list and bool(cases), "OPERATIONAL_COURT_CASES_INVALID")
    rows=[]; identifiers=set()
    for row in cases:
        item=exact_keys(row, {"id", "status", "diagnostic"}, "$.cases")
        require(type(item["id"]) is str and item["id"] and item["id"] not in identifiers,
                "OPERATIONAL_COURT_CASE_ID_INVALID")
        require(item["status"] in {"PASS", "FAIL"} and type(item["diagnostic"]) is str,
                "OPERATIONAL_COURT_CASE_INVALID")
        identifiers.add(item["id"]); rows.append(deepcopy(item))
    rows.sort(key=lambda row: row["id"])
    status="PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL"
    return seal({"schema": "ucl.ucm.operational_court_result.v1", "subject_root": subject_root,
        "checker_root": checker_root, "cases": rows, "case_count": len(rows), "status": status, **BOUNDARY})


def verify_court_result(value: Any, *, expected_root: str) -> dict[str, Any]:
    require(type(value) is dict and value.get("schema") == "ucl.ucm.operational_court_result.v1",
            "OPERATIONAL_COURT_RESULT_INVALID")
    rebuilt = make_court_result(subject_root=value.get("subject_root"), checker_root=value.get("checker_root"),
        cases=value.get("cases"))
    require(canonical_bytes(value) == canonical_bytes(rebuilt) and value["root"] == require_root(expected_root),
            "OPERATIONAL_COURT_RECONSTRUCTION_MISMATCH")
    return rebuilt


def make_update_plan(*, predecessor_root: str, successor_root: str, semantic_change_root: str,
                     semantic_inventory_root: str,
                     rollback_artifact_root: str, required_court_roots: list[str],
                     allowed_effects: list[str] | None = None) -> dict[str, Any]:
    for value in (predecessor_root, successor_root, semantic_change_root, semantic_inventory_root,
                  rollback_artifact_root): require_root(value)
    require(predecessor_root != successor_root, "OPERATIONAL_UPDATE_NO_CHANGE")
    require(type(required_court_roots) is list and required_court_roots == sorted(set(required_court_roots))
            and bool(required_court_roots), "OPERATIONAL_UPDATE_COURTS_INVALID")
    for value in required_court_roots: require_root(value)
    effects = [] if allowed_effects is None else allowed_effects
    require(type(effects) is list and effects == sorted(set(effects)) and set(effects) <= {"READ_WORKSPACE", "WRITE_WORKSPACE", "DELETE_WORKSPACE", "LOCAL_PROCESS"},
            "OPERATIONAL_UPDATE_EFFECTS_INVALID")
    return seal({"schema": "ucl.ucm.operational_update_plan.v1", "predecessor_root": predecessor_root,
        "successor_root": successor_root, "semantic_change_root": semantic_change_root,
        "semantic_inventory_root": semantic_inventory_root,
        "rollback_artifact_root": rollback_artifact_root, "required_court_roots": required_court_roots,
        "allowed_effects": effects, "entry_state": "PREPARED_UNBOUND", "activation": False, **BOUNDARY})


def evaluate_update(plan: Any, evidence: Any, *, expected_plan_root: str) -> dict[str, Any]:
    require(type(plan) is dict and plan.get("schema") == "ucl.ucm.operational_update_plan.v1", "OPERATIONAL_UPDATE_PLAN_INVALID")
    rebuilt = make_update_plan(predecessor_root=plan.get("predecessor_root"), successor_root=plan.get("successor_root"),
        semantic_change_root=plan.get("semantic_change_root"), semantic_inventory_root=plan.get("semantic_inventory_root"),
        rollback_artifact_root=plan.get("rollback_artifact_root"),
        required_court_roots=plan.get("required_court_roots"), allowed_effects=plan.get("allowed_effects"))
    require(canonical_bytes(plan) == canonical_bytes(rebuilt)
            and plan["root"] == require_root(expected_plan_root), "OPERATIONAL_UPDATE_PLAN_PIN_MISMATCH")
    item = exact_keys(evidence, {"semantic_change", "evidence_contracts", "rollback_rehearsal",
                                 "court_records", "source_root"})
    semantic=verify_semantic_change_plan(item["semantic_change"], expected_root=plan["semantic_change_root"],
        expected_inventory_contract_root=plan["semantic_inventory_root"],
        evidence_contracts=item["evidence_contracts"])
    require(semantic.get("root") == plan["semantic_change_root"]
            and semantic.get("predecessor_root") == plan["predecessor_root"]
            and semantic.get("successor_root") == plan["successor_root"]
            and semantic.get("status") == "PASS_CONSERVATIVE", "OPERATIONAL_UPDATE_SEMANTIC_EVIDENCE_MISMATCH")
    rollback=verify_rollback_rehearsal(item["rollback_rehearsal"], expected_root=plan["rollback_artifact_root"])
    require(rollback.get("root") == plan["rollback_artifact_root"]
            and rollback.get("predecessor_root") == plan["predecessor_root"]
            and rollback.get("successor_root") == plan["successor_root"]
            and rollback.get("restored_root") == plan["predecessor_root"]
            and rollback.get("status") == "PASS_RESTORED", "OPERATIONAL_UPDATE_ROLLBACK_EVIDENCE_MISMATCH")
    require(item["source_root"] == plan["successor_root"], "OPERATIONAL_UPDATE_SOURCE_MISMATCH")
    require(type(item["court_records"]) is list, "OPERATIONAL_UPDATE_COURT_RESULTS_INVALID")
    rows = {}
    for row in item["court_records"]:
        require(type(row) is dict and type(row.get("root")) is str, "OPERATIONAL_UPDATE_COURT_RESULT_INVALID")
        checked = verify_court_result(row, expected_root=row["root"])
        require(checked.get("subject_root") == plan["successor_root"]
                and checked.get("status") in {"PASS", "FAIL"}, "OPERATIONAL_UPDATE_COURT_RESULT_INVALID")
        digest = checked["root"]
        require(digest not in rows, "OPERATIONAL_UPDATE_COURT_RESULT_INVALID")
        rows[digest] = checked
    require(set(rows) == set(plan["required_court_roots"]), "OPERATIONAL_UPDATE_COURT_SET_MISMATCH")
    status = "PASS_PREPARED" if all(row["status"] == "PASS" for row in rows.values()) else "REFUSED_COURT_FAILURE"
    return seal({"schema": "ucl.ucm.operational_update_evaluation.v2", "plan_root": plan["root"],
        "evidence": deepcopy(item), "status": status, "activation": False,
        "acceptance_semantics": "PREPARED_FOR_SEPARATE_GOVERNED_STAGE_ONLY", **BOUNDARY})

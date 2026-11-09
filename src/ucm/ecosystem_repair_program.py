"""Track coherent ecosystem audit repairs without claiming review or authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import require, root
from ucm.amcas import BOUNDARY
from ucm.ecosystem_current_state import build_ecosystem_current_state


ACCEPTANCE = ["CURRENT_SOURCE_STAGE_I1_REISSUE_WITH_EXACT_SUBJECT_BINDING",
    "ALL_HIGH_PRIORITY_HOLDS_DISPOSITIONED_IN_ONE_COHERENT_BATCH",
    "ALL_OTHER_OPEN_HOLDS_EXPLICITLY_REPAIRED_ACCEPTED_OR_CARRIED",
    "COURT_OUTCOMES_DERIVED_FROM_EXECUTED_ASSERTIONS",
    "FOCUSED_AND_REGRESSION_TEST_IDENTITIES_RECORDED",
    "REQUESTED_LOWERED_AND_EFFECTIVE_STATE_ROOTS_SEPARATED",
    "NO_APPLICATION_EXECUTION_OR_AUTHORITY_CLAIM_DURING_SEALING",
    "EXACT_SUCCESSOR_RETURN_AND_APPEND_ONLY_JOURNAL_REQUIRED"]


def build_ecosystem_repair_program(successors: dict[str, Any], audits: dict[str, Any],
                                   repairs: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    require(build_ecosystem_current_state(successors, audits, repairs) == current,
            "ECOSYSTEM_REPAIR_CURRENT_STATE_MISMATCH")
    state_by_id = {row["application_id"]: row for row in current["applications"]}
    repair_by_id = {row["application_id"]: row for row in repairs["repairs"]}
    batches = []
    for audit in audits["audits"]:
        high, open_holds = audit["high_priority_hold_ids"], audit["open_hold_ids"]
        require(len(high) == audit["open_high_priority_holds"]
                and len(open_holds) == audit["open_findings"]
                and len(set(open_holds)) == len(open_holds) and set(high).issubset(open_holds),
                "ECOSYSTEM_REPAIR_HOLD_SET_INVALID")
        returned = repair_by_id.get(audit["application_id"])
        body = {"application_id": audit["application_id"],
            "audit_package_filename": audit["package_filename"],
            "audit_return_sha256": audit["return_sha256"],
            "audit_report_root": audit["report_root"],
            "review_governance_root": audit["review_governance_root"],
            "current_state_row_root": state_by_id[audit["application_id"]]["current_state_row_root"],
            "status": ("BATCH_REPAIR_RETURNED_PENDING_INDEPENDENT_REVIEW"
                       if returned else "BATCH_REPAIR_REQUIRED"),
            "batch_policy": "ONE_COHERENT_BATCH_BEFORE_NEXT_REVIEW",
            "high_priority_hold_ids": deepcopy(high),
            "other_open_hold_ids": [item for item in open_holds if item not in set(high)],
            "acceptance_requirements": deepcopy(ACCEPTANCE),
            "repair_return_present": returned is not None,
            "repair_return_sha256": returned["artifact_sha256"] if returned else None,
            "repair_receipt_root": returned["receipt_root"] if returned else None,
            "repairs_claimed": returned["repairs_claimed"] if returned else 0,
            "preserved_external_hold_ids":
                deepcopy(returned["preserved_external_hold_ids"]) if returned else [],
            "application_execution_authorized": False,
            "independent_review_claimed": False, **BOUNDARY}
        batches.append({**body, "repair_instruction_root": root(body)})
    body = {"schema": "mosaic.ucm.ecosystem-audit-repair-program.v0.2",
        "successor_outcome_register_root": successors["outcome_register_root"],
        "audit_return_register_root": audits["audit_register_root"],
        "repair_return_register_root": repairs["repair_register_root"],
        "current_state_root": current["current_state_root"],
        "repair_batch_count": len(batches), "repair_batches": batches,
        "application_execution_authorized": False, "all_holds_cleared": False, **BOUNDARY}
    return {**body, "repair_program_root": root(body)}

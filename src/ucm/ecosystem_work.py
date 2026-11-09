"""Derive the next bounded work lane from reconciled ecosystem outcomes."""
from __future__ import annotations

from typing import Any

from uclop.canonical import require, root


LANES = {
    "STATIC_READINESS_ONLY": (
        "READINESS_REVIEW_LANE",
        "REVIEW_EXACT_READINESS_RETURN_WITHOUT_APPLICATION_EXECUTION",
    ),
    "REBIND_REQUIRED": (
        "SOURCE_ROUTE_REBIND_LANE",
        "BIND_CURRENT_SOURCE_AND_EXACT_NATIVE_ROUTES_THEN_REISSUE_PLAN",
    ),
    "RETURN_REPAIR_REQUIRED": (
        "RETURN_RECOVERY_LANE",
        "RECONCILE_EXISTING_CUSTODY_AND_COMPLETE_A_NEW_EXACT_RETURN",
    ),
    "REPAIR_OR_REVIEW_REQUIRED": (
        "REPAIR_REVIEW_LANE",
        "COMPLETE_NAMED_REPAIRS_OR_REVIEW_ADDRESSED_ITEMS_WITH_HOLDS_PRESERVED",
    ),
}


def build_next_work_program(outcomes: Any) -> dict[str, Any]:
    require(type(outcomes) is dict
            and outcomes.get("fixed_denominator") == 7
            and outcomes.get("all_returns_received") is True,
            "ECOSYSTEM_WORK_OUTCOMES_INVALID")
    rows = []
    for outcome in outcomes["applications"]:
        disposition = outcome["coordinator_disposition"]
        require(disposition in LANES, "ECOSYSTEM_WORK_DISPOSITION_INVALID")
        lane, next_action = LANES[disposition]
        hold_ids = [item["hold_id"] for item in outcome["holds"]]
        gap_ids = [item["gap_id"] for item in outcome["unresolved_gaps"]]
        rows.append({
            "application_id": outcome["application_id"],
            "return_envelope_root": outcome["return_envelope_root"],
            "source_disposition": disposition,
            "work_lane": lane,
            "work_status": "NOT_STARTED",
            "next_action": next_action,
            "open_hold_ids": hold_ids,
            "unresolved_gap_ids": gap_ids,
            "static_review_required": True,
            "independent_review_required_before_execution": True,
            "execution_authorized": False,
            "hold_clearance_authorized": False,
        })
    body = {
        "schema": "mosaic.ucm.ecosystem-next-work-program.v0.1",
        "outcome_register_root": outcomes["outcome_register_root"],
        "fixed_denominator": 7,
        "applications": sorted(rows, key=lambda item: item["application_id"]),
        "application_execution_authorized": False,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
        "real_a5": False,
        "g0": "CLOSED",
    }
    return {**body, "work_program_root": root(body)}


def build_next_dispatch(program: Any, prior_dispatch: Any) -> dict[str, Any]:
    require(type(program) is dict and type(prior_dispatch) is dict,
            "ECOSYSTEM_NEXT_DISPATCH_INPUT_INVALID")
    require(program.get("fixed_denominator") == 7
            and prior_dispatch.get("fixed_denominator") == 7,
            "ECOSYSTEM_NEXT_DISPATCH_DENOMINATOR_INVALID")
    threads = {row["application_id"]: row["thread_id"]
               for row in prior_dispatch["applications"]}
    require(set(threads) == {row["application_id"]
                             for row in program["applications"]},
            "ECOSYSTEM_NEXT_DISPATCH_ROSTER_INVALID")
    rows = [{
        "application_id": row["application_id"],
        "thread_id": threads[row["application_id"]],
        "work_lane": row["work_lane"],
        "next_action": row["next_action"],
        "return_envelope_root": row["return_envelope_root"],
        "dispatch_transport_status": "ACCEPTED_BY_THREAD_TOOL",
        "application_execution_authorized": False,
        "hold_clearance_authorized": False,
    } for row in program["applications"]]
    body = {
        "schema": "mosaic.ucm.ecosystem-next-work-dispatch.v0.1",
        "work_program_root": program["work_program_root"],
        "prior_dispatch_root": prior_dispatch["dispatch_root"],
        "fixed_denominator": 7,
        "applications": rows,
        "transport_acceptance_is_not_work_completion": True,
        "application_execution_authorized": False,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
        "real_a5": False,
        "g0": "CLOSED",
    }
    return {**body, "dispatch_root": root(body)}

"""Derive non-authorizing current ecosystem state from append-only registers."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import require, require_root, root
from ucm.amcas import BOUNDARY
from ucm.ecosystem_successor_outcomes import APPLICATIONS


def _boundary(value: dict[str, Any], diagnostic: str) -> None:
    require(all(value.get(key) == expected for key, expected in BOUNDARY.items()), diagnostic)


def _rooted(value: dict[str, Any], field: str, diagnostic: str) -> None:
    require_root(value.get(field))
    require(value[field] == root({key: deepcopy(item) for key, item in value.items()
                                  if key != field}), diagnostic)


def build_ecosystem_current_state(successors: dict[str, Any],
                                  audits: dict[str, Any],
                                  repairs: dict[str, Any]) -> dict[str, Any]:
    """Overlay audits and later repairs while retaining every source register."""
    for value, diagnostic in ((successors, "ECOSYSTEM_CURRENT_SUCCESSOR_BOUNDARY_INVALID"),
                              (audits, "ECOSYSTEM_CURRENT_AUDIT_BOUNDARY_INVALID"),
                              (repairs, "ECOSYSTEM_CURRENT_REPAIR_BOUNDARY_INVALID")):
        _boundary(value, diagnostic)
    require(successors.get("schema") == "mosaic.ucm.ecosystem-successor-outcome-register.v0.1"
            and successors.get("fixed_denominator") == len(APPLICATIONS)
            and successors.get("received_count") == len(APPLICATIONS)
            and successors.get("pending_count") == 0
            and successors.get("all_returns_received") is True
            and successors.get("all_holds_cleared") is False
            and successors.get("application_execution_authorized") is False,
            "ECOSYSTEM_CURRENT_SUCCESSOR_REGISTER_INVALID")
    _rooted(successors, "outcome_register_root", "ECOSYSTEM_CURRENT_SUCCESSOR_ROOT_INVALID")
    successor_rows = successors.get("applications")
    require(type(successor_rows) is list
            and [row.get("application_id") for row in successor_rows] == list(APPLICATIONS),
            "ECOSYSTEM_CURRENT_SUCCESSOR_ROWS_INVALID")
    require(audits.get("schema") == "mosaic.ucm.ecosystem-audit-return-register.v0.1"
            and audits.get("fixed_application_denominator") == len(APPLICATIONS)
            and audits.get("application_execution_authorized") is False
            and audits.get("all_holds_cleared") is False,
            "ECOSYSTEM_CURRENT_AUDIT_REGISTER_INVALID")
    _rooted(audits, "audit_register_root", "ECOSYSTEM_CURRENT_AUDIT_ROOT_INVALID")
    audit_rows = audits.get("audits")
    require(type(audit_rows) is list and audits.get("audit_return_count") == len(audit_rows)
            and audits.get("audited_application_count") == len(audit_rows),
            "ECOSYSTEM_CURRENT_AUDIT_ROWS_INVALID")
    audit_by_id = {}
    for row in audit_rows:
        require(type(row) is dict and row.get("application_id") in APPLICATIONS
                and row["application_id"] not in audit_by_id
                and row.get("status") == "HOLD_FOR_REPAIR"
                and row.get("execution_eligible") is False
                and row.get("open_findings", 0) > 0
                and row.get("open_high_priority_holds", 0) > 0,
                "ECOSYSTEM_CURRENT_AUDIT_ROW_INVALID")
        audit_by_id[row["application_id"]] = row
    require(audits.get("applications_without_audit_return")
            == [item for item in APPLICATIONS if item not in audit_by_id],
            "ECOSYSTEM_CURRENT_AUDIT_DENOMINATOR_INVALID")
    require(repairs.get("schema") == "mosaic.ucm.ecosystem-repair-return-register.v0.1"
            and repairs.get("fixed_application_denominator") == len(APPLICATIONS)
            and repairs.get("application_execution_authorized") is False
            and repairs.get("all_holds_cleared") is False,
            "ECOSYSTEM_CURRENT_REPAIR_REGISTER_INVALID")
    _rooted(repairs, "repair_register_root", "ECOSYSTEM_CURRENT_REPAIR_ROOT_INVALID")
    repair_rows = repairs.get("repairs")
    require(type(repair_rows) is list
            and repairs.get("repair_return_count") == len(repair_rows)
            and repairs.get("repaired_application_count") == len(repair_rows),
            "ECOSYSTEM_CURRENT_REPAIR_ROWS_INVALID")
    repair_by_id = {}
    for row in repair_rows:
        application_id = row.get("application_id")
        require(application_id in audit_by_id and application_id not in repair_by_id
                and row.get("claimed_status") == "HOLD_FOR_REPAIR"
                and row.get("execution_eligible") is False
                and row.get("hold_clearance") == "NONE"
                and row.get("independent_review_claimed") is False
                and row.get("predecessor_audit_return_sha256")
                    == audit_by_id[application_id]["return_sha256"]
                and row.get("repaired_hold_ids") == audit_by_id[application_id]["open_hold_ids"],
                "ECOSYSTEM_CURRENT_REPAIR_ROW_INVALID")
        repair_by_id[application_id] = row
    require(repairs.get("applications_without_repair_return")
            == [item for item in APPLICATIONS if item not in repair_by_id],
            "ECOSYSTEM_CURRENT_REPAIR_DENOMINATOR_INVALID")
    rows = []
    for predecessor in successor_rows:
        application_id = predecessor["application_id"]
        require(predecessor.get("execution_eligible") is False
                and predecessor.get("hold_clearance") == "NONE",
                "ECOSYSTEM_CURRENT_PREDECESSOR_AUTHORITY_INVALID")
        audit, repair = audit_by_id.get(application_id), repair_by_id.get(application_id)
        if repair:
            effective = {"status": "HOLD_FOR_REPAIR",
                "content_review_status": repair["content_review_status"],
                "coordinator_disposition": "INDEPENDENT_REVIEW_AND_EXTERNAL_HOLD_RESOLUTION_REQUIRED",
                "open_findings": 0, "open_high_priority_holds": 0,
                "repaired_findings": repair["repairs_claimed"],
                "remaining_external_holds": len(repair["preserved_external_hold_ids"]),
                "preserved_external_hold_ids": repair["preserved_external_hold_ids"],
                "latest_repair_return_sha256": repair["artifact_sha256"],
                "latest_repair_receipt_root": repair["receipt_root"],
                "latest_repair_qualification_root": repair["qualification_root"]}
        elif audit:
            effective = {"status": "HOLD_FOR_REPAIR",
                "content_review_status": audit["content_review_status"],
                "coordinator_disposition": "REPAIR_OR_INDEPENDENT_REVIEW_REQUIRED",
                "open_findings": audit["open_findings"],
                "open_high_priority_holds": audit["open_high_priority_holds"],
                "repaired_findings": 0, "remaining_external_holds": None,
                "preserved_external_hold_ids": [], "latest_repair_return_sha256": None,
                "latest_repair_receipt_root": None, "latest_repair_qualification_root": None}
        else:
            effective = {"status": predecessor["claimed_status"],
                "content_review_status": predecessor["content_review_status"],
                "coordinator_disposition": predecessor["coordinator_disposition"],
                "open_findings": None, "open_high_priority_holds": None,
                "repaired_findings": 0, "remaining_external_holds": None,
                "preserved_external_hold_ids": [], "latest_repair_return_sha256": None,
                "latest_repair_receipt_root": None, "latest_repair_qualification_root": None}
        row_body = {"application_id": application_id,
            "predecessor_outcome_root": root(predecessor),
            "predecessor_claimed_status": predecessor["claimed_status"],
            "predecessor_hold_count": len(predecessor["holds"]),
            "audit_overlay_present": audit is not None,
            "repair_overlay_present": repair is not None,
            "latest_audit_return_sha256": audit["return_sha256"] if audit else None,
            "latest_audit_report_root": audit["report_root"] if audit else None,
            "latest_audit_review_governance_root": audit["review_governance_root"] if audit else None,
            **effective, "hold_clearance": "NONE", "execution_eligible": False, **BOUNDARY}
        rows.append({**row_body, "current_state_row_root": root(row_body)})
    body = {"schema": "mosaic.ucm.ecosystem-integration-current-state.v0.2",
        "successor_outcome_register_root": successors["outcome_register_root"],
        "audit_return_register_root": audits["audit_register_root"],
        "repair_return_register_root": repairs["repair_register_root"],
        "fixed_application_denominator": len(APPLICATIONS), "application_count": len(rows),
        "audit_overlay_count": len(audit_by_id), "repair_overlay_count": len(repair_by_id),
        "applications_on_hold": [row["application_id"] for row in rows
                                 if row["status"] == "HOLD_FOR_REPAIR"],
        "all_holds_cleared": False, "application_execution_authorized": False,
        "applications": rows, **BOUNDARY}
    return {**body, "current_state_root": root(body)}

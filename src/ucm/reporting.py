"""Evidence-derived reports for UCM-AMCAS integration campaigns."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import root

from .amcas import BOUNDARY, REPORT_SCHEMA


def build_report(campaign, *, portable_artifacts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    contract = campaign.contract()
    compiled = campaign.compiled()
    events = campaign.journal.verify()
    checkpoint = campaign.journal.checkpoint()
    dispositions = {event["payload"].get("obligation_id"): event["payload"]
                    for event in events if event["event_type"] == "REQUIREMENT_DISPOSITIONED"}
    requirements = []
    for obligation in compiled["obligations"]:
        disposition = dispositions.get(obligation["id"])
        requirements.append({
            "obligation_id": obligation["id"], "required": obligation["required"],
            "subject_root": obligation["subject_root"],
            "status": disposition.get("status", "UNRESOLVED") if disposition else "UNRESOLVED",
            "evidence_roots": disposition.get("evidence_roots", []) if disposition else [],
        })
    operation_ids = sorted({event["payload"].get("operation_id") for event in events
                            if type(event["payload"].get("operation_id")) is str})
    operations = []
    for operation_id in operation_ids:
        rows = [event for event in events if event["payload"].get("operation_id") == operation_id]
        operations.append({"operation_id": operation_id,
                           "gate_events": [event["event_type"] for event in rows],
                           "terminal": bool(rows and rows[-1]["event_type"] == "DIAGNOSTIC_RECORDED"),
                           "event_roots": [event["event_root"] for event in rows]})
    findings = [deepcopy(event["payload"]) for event in events
                if event["event_type"] == "FINDING_RECORDED"]
    capabilities = []
    for capability in contract["capabilities"]:
        used = any(event["event_type"] == "OPERATION_PLANNED"
                   and event["payload"]["operation"]["capability_id"] == capability["id"]
                   for event in events)
        capabilities.append({"id": capability["id"], "required": capability["required"],
                             "route": capability["route"],
                             "status": "EXERCISED" if used else "NOT_EXERCISED"})
    ready = (all(not row["required"] or row["status"] == "PASS" for row in requirements)
             and not checkpoint["open_operations"])
    body = {
        "schema": REPORT_SCHEMA, "contract_root": contract["contract_root"],
        "ir_root": compiled["ir_root"], "journal_head": checkpoint["head"]["head"],
        "application_source_root": contract["subject"]["source_root"],
        "requirements": requirements, "capabilities": capabilities,
        "operations": operations, "findings": findings,
        "limitations": [
            "NATIVE_AOK_CAPABILITY_LATTICE_UNAVAILABLE_IN_BUILD_SESSION",
            "NATIVE_UGK_RECEIPT_VERIFIER_NOT_BOUND",
            "NO_EXTERNAL_EFFECT_OR_CAPABILITY_AUTHORITY_GRANTED",
            "MOSAIC_ID_CONTEXT_AND_NAMESPACE_REQUIRE_LOCAL_ADMISSION",
        ],
        "portable_artifacts": deepcopy(portable_artifacts or []),
        "status": "READY_FOR_REVIEW" if ready else "IN_PROGRESS", **BOUNDARY,
    }
    return {**body, "report_root": root(body)}

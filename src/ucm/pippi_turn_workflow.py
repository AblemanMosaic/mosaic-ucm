"""Common turn records in the existing P/PPI project journal.

Legacy opening/report bytes remain inputs.  The richer submission and optional
CMBA assessment are immutable successor records, never rewritten history.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, root, strict_loads
from .pippi_adaptive import build_turn_report, reconcile_turn, validate_turn_opening, validate_turn_report
from .pippi_global import BOUNDARY
from .pippi_turn_record import build_turn_record, validate_turn_record, project_turn_record


REPORT_FIELDS = {"opening", "summary", "changed_paths", "artifact_roots", "evidence_roots",
                 "unresolved_items", "next_action", "claim_class"}
DETAIL_FIELDS = {"claims", "evidence", "coverage", "objectives", "acceptance_dispositions", "native_turn_roots"}


def build_turn_submission(request: dict[str, Any]) -> dict[str, Any]:
    require(type(request) is dict and REPORT_FIELDS <= set(request)
            and set(request) <= REPORT_FIELDS | {"turn_details", "supersedes_turn_bundle_root"},
            "PIPPI_TURN_SUBMISSION_FIELDS_INVALID")
    opening = validate_turn_opening(request["opening"])
    report = build_turn_report(**{key: request[key] for key in REPORT_FIELDS})
    details = request.get("turn_details", {key: [] for key in DETAIL_FIELDS})
    exact_keys(details, DETAIL_FIELDS)
    record = build_turn_record(opening=opening, report=report, **details)
    return build_turn_bundle(opening=opening, report=report, turn_record=record,
        supersedes_turn_bundle_root=request.get("supersedes_turn_bundle_root"))


def build_turn_bundle(*, opening: dict[str, Any], report: dict[str, Any],
                      turn_record: dict[str, Any],
                      supersedes_turn_bundle_root: str | None = None) -> dict[str, Any]:
    opening = validate_turn_opening(opening)
    report = validate_turn_report(report, opening=opening)
    record = validate_turn_record(turn_record, opening=opening, report=report)
    require(supersedes_turn_bundle_root is None or
            (type(supersedes_turn_bundle_root) is str
             and len(supersedes_turn_bundle_root) == 64
             and all(ch in "0123456789abcdef" for ch in supersedes_turn_bundle_root)),
            "PIPPI_TURN_SUPERSESSION_ROOT_INVALID")
    body = {"schema": "mosaic.ucm.pippi-turn-record-bundle.v0.2",
            "project_id": opening["project_id"], "project_root": opening["project_root"],
            "sequence": opening["sequence"], "turn_opening_root": opening["turn_opening_root"],
            "turn_report_root": report["turn_report_root"], "turn_record_root": record["turn_record_root"],
            "supersedes_turn_bundle_root": supersedes_turn_bundle_root,
            "opening": opening, "report": report, "turn_record": record, **BOUNDARY}
    return {**body, "turn_bundle_root": root(body)}


def validate_turn_bundle(value: Any) -> dict[str, Any]:
    require(type(value) is dict, "PIPPI_TURN_BUNDLE_INVALID")
    if value.get("schema") == "mosaic.ucm.pippi-turn-record-bundle.v0.1":
        opening = validate_turn_opening(value.get("opening"))
        report = validate_turn_report(value.get("report"), opening=opening)
        record = validate_turn_record(value.get("turn_record"), opening=opening, report=report)
        body = {"schema": "mosaic.ucm.pippi-turn-record-bundle.v0.1",
                "project_id": opening["project_id"], "project_root": opening["project_root"],
                "sequence": opening["sequence"], "turn_opening_root": opening["turn_opening_root"],
                "turn_report_root": report["turn_report_root"],
                "turn_record_root": record["turn_record_root"],
                "opening": opening, "report": report, "turn_record": record, **BOUNDARY}
        expected = {**body, "turn_bundle_root": root(body)}
    else:
        expected = build_turn_bundle(opening=value.get("opening"), report=value.get("report"),
            turn_record=value.get("turn_record"),
            supersedes_turn_bundle_root=value.get("supersedes_turn_bundle_root"))
    require(value == expected, "PIPPI_TURN_BUNDLE_INVALID")
    return expected


def reconcile_common_turn(*, opening: dict[str, Any], report: dict[str, Any],
                          turn_record: dict[str, Any], current_project_root: str,
                          current_journal_head: str | None) -> dict[str, Any]:
    record = validate_turn_record(turn_record, opening=opening, report=report)
    native = reconcile_turn(opening=opening, report=report,
        current_project_root=current_project_root, current_journal_head=current_journal_head)
    body = {"schema": "mosaic.ucm.pippi-turn-record-reconciliation.v0.1",
            "project_id": opening["project_id"], "project_root": current_project_root,
            "turn_opening_root": opening["turn_opening_root"],
            "turn_report_root": report["turn_report_root"], "turn_record_root": record["turn_record_root"],
            "native_reconciliation": native, "reporting_status": record["status"],
            "missing_information": record["missing_information"],
            "state": "RECONCILED", "acceptance_case_closed": False,
            "effect_authorized": False, **BOUNDARY}
    return {**body, "reconciliation_root": root(body)}


def build_assessment_attachment(*, opening: dict[str, Any], report: dict[str, Any],
                                turn_record: dict[str, Any], assessment: dict[str, Any],
                                expected_wheel_sha256: str) -> dict[str, Any]:
    from .pippi_cmba import validate_cmba_turn_assessment
    record = validate_turn_record(turn_record, opening=opening, report=report)
    validated = validate_cmba_turn_assessment(assessment, opening=opening, report=report,
        turn_record=record, expected_wheel_sha256=expected_wheel_sha256)
    body = {"schema": "mosaic.ucm.pippi-turn-assessment-attachment.v0.1",
            "project_id": opening["project_id"], "project_root": opening["project_root"],
            "turn_record_root": record["turn_record_root"], "assessment": validated,
            "validation_method": "RECOMPUTED_EXACT_BOUND_CMBA_ASSESSMENT",
            "acceptance_case_closed": False, "effect_authorized": False, **BOUNDARY}
    return {**body, "attachment_root": root(body)}


def validate_assessment_attachment(value: Any, *, bundle: dict[str, Any]) -> dict[str, Any]:
    require(type(value) is dict and type(value.get("assessment")) is dict,
            "PIPPI_TURN_ASSESSMENT_ATTACHMENT_INVALID")
    identity = value["assessment"].get("cmba_identity")
    require(type(identity) is dict and type(identity.get("wheel_sha256")) is str,
            "PIPPI_TURN_ASSESSMENT_ATTACHMENT_INVALID")
    expected = build_assessment_attachment(opening=bundle["opening"], report=bundle["report"],
        turn_record=bundle["turn_record"], assessment=value["assessment"],
        expected_wheel_sha256=identity["wheel_sha256"])
    require(value == expected, "PIPPI_TURN_ASSESSMENT_ATTACHMENT_INVALID")
    return expected


def project_turn_history(hub, project_id: str) -> dict[str, Any]:
    """Read exact project records without creating folders or advancing heads."""
    project = hub.get_project(project_id)
    directory = hub.turns / project_id
    events = hub._events()
    committed_events = {row["payload"].get("turn_bundle_root"): row["sequence"] for row in events
                        if row["event_type"] == "TURN_RECORD_SUBMITTED"
                        and row["payload"].get("project_id") == project_id}
    assessment_events = {row["payload"].get("attachment_root"): row["sequence"] for row in events
                         if row["event_type"] == "TURN_ASSESSMENT_ATTACHED"
                         and row["payload"].get("project_id") == project_id}
    records = []
    if directory.is_dir():
        for path in sorted(directory.glob("turn-record-*.json"), key=lambda p: p.name):
            bundle = validate_turn_bundle(strict_loads(path.read_bytes()))
            require(bundle["project_id"] == project_id, "PIPPI_TURN_BUNDLE_PROJECT_MISMATCH")
            # An interrupted write is visible as uncommitted custody, not hidden.
            projection = project_turn_record(bundle["turn_record"], opening=bundle["opening"],
                                             report=bundle["report"], view="HUMAN")
            assessments = []
            for attachment_path in sorted(directory.glob("turn-assessment-*.json"), key=lambda p: p.name):
                raw_attachment = strict_loads(attachment_path.read_bytes())
                if raw_attachment.get("turn_record_root") != bundle["turn_record_root"]:
                    continue
                attachment = validate_assessment_attachment(raw_attachment, bundle=bundle)
                assessments.append({"attachment_root": attachment["attachment_root"],
                    "assessment_root": attachment["assessment"]["assessment_root"],
                    "outcome": attachment["assessment"]["outcome"],
                    "claim_ceiling": attachment["assessment"]["claim_ceiling"],
                    "journal_committed": attachment["attachment_root"] in assessment_events,
                    "journal_event_sequence": assessment_events.get(attachment["attachment_root"])})
            assessments.sort(key=lambda row: (row["journal_event_sequence"] is None,
                                               row["journal_event_sequence"] or 0,
                                               row["attachment_root"]))
            records.append({"turn_bundle_root": bundle["turn_bundle_root"],
                "turn_record_root": bundle["turn_record_root"], "turn_opening_root": bundle["turn_opening_root"],
                "sequence": bundle["sequence"], "project_root": bundle["project_root"],
                "is_current_project_revision": bundle["project_root"] == project["project_root"],
                "journal_committed": bundle["turn_bundle_root"] in committed_events,
                "journal_event_sequence": committed_events.get(bundle["turn_bundle_root"]),
                "supersedes_turn_bundle_root": bundle.get("supersedes_turn_bundle_root"),
                "assessments": assessments,
                "projection": projection})
    superseded = {row["supersedes_turn_bundle_root"] for row in records
                  if row["journal_committed"] and row["supersedes_turn_bundle_root"] is not None}
    by_root = {row["turn_bundle_root"]: row for row in records}
    for row in records:
        successors = sorted(candidate["turn_bundle_root"] for candidate in records
                            if candidate["journal_committed"]
                            and candidate["supersedes_turn_bundle_root"] == row["turn_bundle_root"])
        require(len(successors) <= 1, "PIPPI_TURN_SUPERSESSION_FORK_INVALID")
        row["superseded_by_turn_bundle_root"] = successors[0] if successors else None
        row["active_report"] = row["journal_committed"] and row["turn_bundle_root"] not in superseded
        if row["supersedes_turn_bundle_root"] is not None:
            require(row["supersedes_turn_bundle_root"] in by_root,
                    "PIPPI_TURN_SUPERSESSION_TARGET_MISSING")
    records.sort(key=lambda row: (row["journal_event_sequence"] is None,
                                  row["journal_event_sequence"] or 0,
                                  row["turn_bundle_root"]))
    body = {"schema": "mosaic.ucm.pippi-project-turn-history.v0.1", "project_id": project_id,
            "project_root": project["project_root"], "records": records,
            "record_count": len(records), "projection_is_evidence": False, **BOUNDARY}
    return {**body, "history_root": root(body)}


def turn_continuation_context(hub, project_id: str) -> dict[str, Any]:
    """Show missing closes and missing information on the next opening."""
    hub.get_project(project_id)
    events = [row for row in hub._events() if row["payload"].get("project_id") == project_id]
    directory = hub.turns / project_id
    opened = {row["payload"].get("turn_opening_root") for row in events if row["event_type"] == "TURN_OPENED"}
    committed_closes = {row["payload"].get("reconciliation_root") for row in events
                        if row["event_type"] == "TURN_RECONCILED"}
    closed = set()
    if directory.is_dir():
        for path in sorted(directory.glob("reconciliation-*.json"), key=lambda p: p.name):
            record = strict_loads(path.read_bytes())
            body = {key: value for key, value in record.items() if key != "reconciliation_root"}
            require(record.get("reconciliation_root") == root(body), "PIPPI_RECONCILIATION_CUSTODY_INVALID")
            require(record.get("project_root") is not None, "PIPPI_RECONCILIATION_CUSTODY_INVALID")
            if record["reconciliation_root"] in committed_closes:
                closed.add(record.get("turn_opening_root"))
    pending = sorted(value for value in opened - closed if value is not None)
    history = project_turn_history(hub, project_id)
    missing = [{"turn_record_root": row["turn_record_root"],
                "missing_information": row["projection"]["missing_information"]}
               for row in history["records"] if row["is_current_project_revision"] and row["active_report"]
               and row["projection"]["missing_information"]]
    body = {"schema": "mosaic.ucm.pippi-turn-continuation-context.v0.1",
            "project_id": project_id, "pending_opening_roots": pending,
            "information_requests": missing,
            "instruction": "File or explicitly reconcile each prior opening; preserve unknown facts and supply the requested reporting information.",
            "status": "PREVIOUS_TURN_CLOSE_REQUIRED" if pending else "READY",
            "effects_authorized": False, **BOUNDARY}
    return {**body, "continuation_context_root": root(body)}

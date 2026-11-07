"""Exact, append-only reconciliation of later ecosystem audit returns.

Audit returns qualify an already-received application integration without
rewriting its earlier custody chain. Reconciliation proves exact bytes and
internal bindings; it never converts self-reported review into independent
review, clears a hold, or authorizes execution.
"""
from __future__ import annotations

import hashlib
import io
import zipfile
from typing import Any

from uclop.canonical import canonical_bytes, require, require_root, root, strict_loads

from ucm.amcas import BOUNDARY
from ucm.artifacts import verify_deterministic_zip
from ucm.ecosystem_successor_outcomes import APPLICATIONS
from ucm.stage1 import verify_stage1_bundle


RETURN_SCHEMA = "mosaic.ucm.stage-i1-bundle.v0.2"
RETURN_ROLE = "APPLICATION_STAGE_I1_RETURN"
JOURNAL_SCHEMA = "mosaic.ucm.integration-journal-archive.v0.1"
JOURNAL_ROLE = "CANONICAL_INTEGRATION_JOURNAL"
REQUIRED_RETURN_FILES = {
    "AMCAS-CONTRACT.json", "CAPABILITY-EFFECT-INVENTORY.json",
    "CONTENT-GRAPH.json", "CONTROL-PLANE-DISPOSITION.json",
    "CORRESPONDENCE-COURT.json", "INTEGRATION-IR.json", "JOURNAL.zip",
    "SESSION-REPORT.json", "STAGE-I1-INDEX.json", "SUBJECT-BINDING.json",
    "THR-CAS-MANIFEST.json",
}


def _canonical_record(archive: zipfile.ZipFile, name: str) -> dict[str, Any]:
    raw = archive.read(name)
    value = strict_loads(raw)
    require(type(value) is dict and canonical_bytes(value) == raw,
            "ECOSYSTEM_AUDIT_RECORD_NONCANONICAL")
    return value


def _rooted(value: dict[str, Any], field: str, diagnostic: str) -> None:
    require(field in value and root({key: item for key, item in value.items()
                                     if key != field}) == value[field], diagnostic)


def _boundary(value: dict[str, Any], diagnostic: str) -> None:
    require(all(value.get(key) == expected for key, expected in BOUNDARY.items()),
            diagnostic)


def _journal(raw: bytes, report: dict[str, Any]) -> dict[str, Any]:
    manifest = verify_deterministic_zip(
        raw, expected_schema=JOURNAL_SCHEMA, expected_role=JOURNAL_ROLE)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        head = _canonical_record(archive, "journal/HEAD.json")
        governance = _canonical_record(archive, "review/GOVERNANCE-HOLDS.json")
        observation = _canonical_record(
            archive, "review/FOCUSED-TEST-OBSERVATION.json")
        audit_path = report["audit"]["path"]
        audit_raw = archive.read(audit_path)
        events_raw = archive.read("journal/EVENTS.jsonl")
    _rooted(head, "root", "ECOSYSTEM_AUDIT_JOURNAL_HEAD_INVALID")
    _boundary(head, "ECOSYSTEM_AUDIT_JOURNAL_BOUNDARY_INVALID")
    require(head.get("events_sha256") == hashlib.sha256(events_raw).hexdigest()
            and type(head.get("sequence")) is int
            and type(head["sequence"]) is not bool and head["sequence"] > 0,
            "ECOSYSTEM_AUDIT_JOURNAL_HEAD_INVALID")
    require(hashlib.sha256(audit_raw).hexdigest() == report["audit"]["sha256"]
            and len(audit_raw) == report["audit"]["bytes"],
            "ECOSYSTEM_AUDIT_REVIEW_BINDING_INVALID")
    for value in (governance, observation):
        _boundary(value, "ECOSYSTEM_AUDIT_REVIEW_BOUNDARY_INVALID")
        require(value.get("application_id") == report["application_id"],
                "ECOSYSTEM_AUDIT_APPLICATION_MISMATCH")
    accounting = report["test_accounting"]
    require(observation.get("passed") == accounting["focused_passed"]
            and observation.get("tests") == accounting["focused_total"]
            and observation.get("open_findings") == accounting["open_findings"]
            and observation.get("high_priority_open_findings")
                == accounting["open_high_priority_holds"]
            and observation.get("audit_sha256") == report["audit"]["sha256"],
            "ECOSYSTEM_AUDIT_TEST_ACCOUNTING_MISMATCH")
    require(governance.get("status") == report["status"]
            and governance.get("execution_eligible") is False
            and governance.get("execution_authorized") is False
            and governance.get("repairs_performed") is False
            and governance.get("test_passes_clear_holds") is False,
            "ECOSYSTEM_AUDIT_GOVERNANCE_INVALID")
    open_findings = governance.get("open_findings")
    require(type(open_findings) is list
            and len(open_findings) == accounting["open_findings"]
            and len({row.get("hold_id") for row in open_findings}) == len(open_findings)
            and all(type(row) is dict and row.get("status") == "OPEN"
                    and row.get("blocks_execution") is True for row in open_findings),
            "ECOSYSTEM_AUDIT_FINDINGS_INVALID")
    p1 = [row for row in open_findings if row.get("priority") == "P1"]
    require(len(p1) == accounting["open_high_priority_holds"]
            and governance.get("high_priority_holds")
                == [row["hold_id"] for row in p1],
            "ECOSYSTEM_AUDIT_PRIORITY_HOLDS_INVALID")
    return {
        "journal_sha256": hashlib.sha256(raw).hexdigest(),
        "journal_manifest_root": manifest["manifest_root"],
        "journal_head": head["head"],
        "journal_sequence": head["sequence"],
        "review_governance_root": governance["governance_root"],
        "test_observation_root": observation["test_observation_root"],
        "open_hold_ids": [row["hold_id"] for row in open_findings],
        "high_priority_hold_ids": [row["hold_id"] for row in p1],
    }


def verify_audit_return(raw: bytes) -> dict[str, Any]:
    """Verify one exact Stage I1 audit return and derive a non-authorizing row."""
    stage1 = verify_stage1_bundle(raw)
    manifest = verify_deterministic_zip(
        raw, expected_schema=RETURN_SCHEMA, expected_role=RETURN_ROLE)
    require({row["path"] for row in manifest["files"]} == REQUIRED_RETURN_FILES,
            "ECOSYSTEM_AUDIT_RETURN_FILE_SET_INVALID")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        report = _canonical_record(archive, "SESSION-REPORT.json")
        index = _canonical_record(archive, "STAGE-I1-INDEX.json")
        journal_raw = archive.read("JOURNAL.zip")
    _rooted(report, "report_root", "ECOSYSTEM_AUDIT_REPORT_ROOT_INVALID")
    _rooted(index, "index_root", "ECOSYSTEM_AUDIT_INDEX_ROOT_INVALID")
    _boundary(report, "ECOSYSTEM_AUDIT_REPORT_BOUNDARY_INVALID")
    _boundary(index, "ECOSYSTEM_AUDIT_INDEX_BOUNDARY_INVALID")
    application_id = report.get("application_id")
    require(application_id in APPLICATIONS
            and index.get("application_id") == application_id,
            "ECOSYSTEM_AUDIT_APPLICATION_INVALID")
    require(report.get("return_kind") == "SUCCESSOR_HARDENING_REVIEW_QUALIFICATION"
            and report.get("status") == "HOLD_FOR_REPAIR"
            and report.get("execution_eligible") is False
            and report.get("execution_authorized") is False
            and report.get("application_executed_during_sealing") is False
            and report.get("repairs_performed") is False
            and report.get("native_effect_executor_retained") is True,
            "ECOSYSTEM_AUDIT_REPORT_STATUS_INVALID")
    accounting = report.get("test_accounting")
    require(type(accounting) is dict
            and set(accounting) == {"focused_passed", "focused_total",
                                    "open_findings", "open_high_priority_holds",
                                    "passing_tests_establish_full_integration"}
            and accounting["focused_passed"] == accounting["focused_total"]
            and accounting["focused_total"] > 0
            and accounting["open_findings"] > 0
            and accounting["open_high_priority_holds"] > 0
            and accounting["passing_tests_establish_full_integration"] is False,
            "ECOSYSTEM_AUDIT_TEST_ACCOUNTING_INVALID")
    findings = report.get("findings")
    require(type(findings) is list and len(findings) == accounting["open_findings"]
            and len({row.get("hold_id") for row in findings}) == len(findings)
            and all(type(row) is dict and row.get("status") == "OPEN"
                    for row in findings), "ECOSYSTEM_AUDIT_FINDINGS_INVALID")
    audit = report.get("audit")
    require(type(audit) is dict and set(audit) == {"path", "sha256", "bytes"}
            and type(audit["path"]) is str and audit["path"].startswith("review/")
            and type(audit["bytes"]) is int and audit["bytes"] > 0,
            "ECOSYSTEM_AUDIT_REVIEW_BINDING_INVALID")
    require_root(audit["sha256"])
    journal = _journal(journal_raw, report)
    require(index.get("status") == report["status"]
            and index.get("session_report_root") == report["report_root"]
            and index.get("contract_root") == report["contract_root"]
            and index.get("ir_root") == report["ir_root"]
            and index.get("H_m") == stage1["thr_commitments"]["H_m"]
            and index.get("H_s") == stage1["thr_commitments"]["H_s"]
            and index.get("H_c") == stage1["thr_commitments"]["H_c"]
            and index.get("journal_sha256") == journal["journal_sha256"],
            "ECOSYSTEM_AUDIT_INDEX_BINDING_INVALID")
    for field in ("application_root", "review_governance_root",
                  "current_reviewed_slice_root", "predecessor_root"):
        require_root(report[field])
    return {
        "application_id": application_id,
        "status": report["status"],
        "return_sha256": hashlib.sha256(raw).hexdigest(),
        "manifest_root": manifest["manifest_root"],
        "report_root": report["report_root"],
        "application_root": report["application_root"],
        "semantic_root": index["H_m"],
        "state_root": index["H_s"],
        "governance_root": index["H_c"],
        "review_governance_root": report["review_governance_root"],
        "reviewed_slice_root": report["current_reviewed_slice_root"],
        "predecessor_root": report["predecessor_root"],
        "audit_sha256": audit["sha256"],
        "focused_tests_passed": accounting["focused_passed"],
        "focused_tests_total": accounting["focused_total"],
        "open_findings": accounting["open_findings"],
        "open_high_priority_holds": accounting["open_high_priority_holds"],
        "execution_eligible": False,
        "content_review_status": "EXACT_SELF_REPORTED_AUDIT_RECONCILED_NOT_INDEPENDENT_REVIEW",
        **journal,
    }


def build_audit_return_register(packages: dict[str, bytes]) -> dict[str, Any]:
    rows = []
    seen = set()
    for filename, raw in sorted(packages.items()):
        row = verify_audit_return(raw)
        require(row["application_id"] not in seen,
                "ECOSYSTEM_AUDIT_APPLICATION_DUPLICATE")
        seen.add(row["application_id"])
        rows.append({"package_filename": filename, **row})
    body = {
        "schema": "mosaic.ucm.ecosystem-audit-return-register.v0.1",
        "fixed_application_denominator": len(APPLICATIONS),
        "audit_return_count": len(rows),
        "audited_application_count": len(seen),
        "applications_without_audit_return": [item for item in APPLICATIONS
                                                if item not in seen],
        "application_execution_authorized": False,
        "all_holds_cleared": False,
        "audits": rows,
        **BOUNDARY,
    }
    return {**body, "audit_register_root": root(body)}

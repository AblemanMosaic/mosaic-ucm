"""Exact, append-only ecosystem repair-return custody and reconciliation."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import io
from typing import Any
import zipfile

from uclop.canonical import require, require_root, root, strict_loads

from ucm.amcas import BOUNDARY
from ucm.artifacts import verify_deterministic_zip
from ucm.ecosystem_successor_outcomes import APPLICATIONS


PACKAGE_SCHEMA = "mosaic.ucm.ecosystem-repair-return-package.v0.1"
PACKAGE_ROLE = "UCM_ECOSYSTEM_REPAIR_RETURN_PACKAGE"
RETURN_SCHEMA = "mosaic.ucm.ecosystem-repair-return-envelope.v0.1"
REGISTER_SCHEMA = "mosaic.ucm.ecosystem-repair-return-register.v0.1"
EXTERNAL_HOLDS = (
    "AOK_STANDING_UNBOUND",
    "CASE_BOUNDED_CORRESPONDENCE_NOT_FULL_SEMANTIC_EQUIVALENCE",
    "COMPOSITION_AUTHORITY_ABSENT",
    "IDENTITY_UNBOUND",
    "JURISDICTION_UNBOUND",
    "LOOPBACK_STATUS_AUTHENTICATION_MISMATCH",
    "NATIVE_ROUTE_BINDINGS_INCOMPLETE",
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _boundary(value: dict[str, Any], diagnostic: str) -> None:
    require(all(value.get(key) == expected for key, expected in BOUNDARY.items()),
            diagnostic)


def _archive_members(raw: bytes) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            return {info.filename: archive.read(info) for info in archive.infolist()
                    if not info.is_dir()}
    except (zipfile.BadZipFile, OSError, RuntimeError) as error:
        raise ValueError("ECOSYSTEM_REPAIR_RETURN_ARCHIVE_INVALID") from error


def receive_repair_return(audits: dict[str, Any], *, application_id: str,
                          artifact_raw: bytes, artifact_filename: str,
                          receipt_raw: bytes) -> dict[str, Any]:
    """Verify an exact coherent repair successor without clearing its holds."""
    _boundary(audits, "ECOSYSTEM_REPAIR_AUDIT_BOUNDARY_INVALID")
    require(audits.get("schema") == "mosaic.ucm.ecosystem-audit-return-register.v0.1",
            "ECOSYSTEM_REPAIR_AUDIT_REGISTER_INVALID")
    audit_rows = [row for row in audits.get("audits", [])
                  if row.get("application_id") == application_id]
    require(len(audit_rows) == 1, "ECOSYSTEM_REPAIR_AUDIT_ROW_MISSING")
    audit = audit_rows[0]
    receipt = strict_loads(receipt_raw)
    require(receipt.get("schema")
            == "mosaic.mwe.drawing-pipeline-repair-successor-receipt.v0.1"
            and receipt.get("status") == "PASS_REPAIRED_WITH_PRESERVED_EXTERNAL_HOLDS",
            "ECOSYSTEM_REPAIR_RECEIPT_INVALID")
    _boundary(receipt, "ECOSYSTEM_REPAIR_RECEIPT_BOUNDARY_INVALID")
    receipt_body = {key: deepcopy(value) for key, value in receipt.items()
                    if key != "receipt_root"}
    require(receipt.get("receipt_root") == root(receipt_body),
            "ECOSYSTEM_REPAIR_RECEIPT_ROOT_INVALID")
    require(receipt.get("return_sha256") == _sha(artifact_raw)
            and receipt.get("return_bytes") == len(artifact_raw),
            "ECOSYSTEM_REPAIR_RETURN_BYTES_MISMATCH")
    manifest = verify_deterministic_zip(
        artifact_raw, expected_schema="mosaic.ucm.stage-i1-bundle.v0.2",
        expected_role="APPLICATION_STAGE_I1_RETURN")
    members = _archive_members(artifact_raw)
    require({"SESSION-REPORT.json", "STAGE-I1-INDEX.json"} <= set(members),
            "ECOSYSTEM_REPAIR_REQUIRED_RECORD_MISSING")
    report = strict_loads(members["SESSION-REPORT.json"])
    index = strict_loads(members["STAGE-I1-INDEX.json"])
    for item in (report, index):
        _boundary(item, "ECOSYSTEM_REPAIR_RECORD_BOUNDARY_INVALID")
        require(item.get("application_id") == application_id,
                "ECOSYSTEM_REPAIR_APPLICATION_MISMATCH")
    require(report.get("status") == "HOLD_FOR_REPAIR"
            and index.get("status") == "HOLD_FOR_REPAIR"
            and report.get("execution_authorized") is False
            and report.get("execution_eligible") is False
            and report.get("application_executed_during_sealing") is False,
            "ECOSYSTEM_REPAIR_AUTHORITY_INVALID")
    require(report.get("predecessor_sha256") == audit["return_sha256"]
            and report.get("predecessor_manifest_root") == audit["manifest_root"],
            "ECOSYSTEM_REPAIR_PREDECESSOR_MISMATCH")
    findings = report.get("findings")
    require(type(findings) is list and len(findings) == audit["open_findings"]
            and receipt.get("findings_repaired") == len(findings),
            "ECOSYSTEM_REPAIR_FINDING_COUNT_INVALID")
    repaired_ids = [row.get("hold_id") for row in findings]
    require(repaired_ids == audit["open_hold_ids"]
            and len(set(repaired_ids)) == len(repaired_ids)
            and all(type(row.get("disposition")) is str
                    and row["disposition"].startswith("REPAIRED")
                    for row in findings),
            "ECOSYSTEM_REPAIR_FINDING_SET_INVALID")
    limitations = report.get("limitations")
    require(type(limitations) is list and all(type(item) is str for item in limitations)
            and set(EXTERNAL_HOLDS).issubset(limitations),
            "ECOSYSTEM_REPAIR_EXTERNAL_HOLDS_MISSING")
    require(report.get("current_source_stage_i1_reissued") is True
            and receipt.get("current_source_stage_i1_reissued") is True
            and receipt.get("repair_result_root") == report.get("repair_result_root")
            and receipt.get("qualification_root") == report.get("qualification_root")
            and receipt.get("report_root") == report.get("report_root")
            and receipt.get("verification", {}).get("manifest_root")
                == manifest["manifest_root"],
            "ECOSYSTEM_REPAIR_CROSS_RECORD_MISMATCH")
    body = {
        "schema": RETURN_SCHEMA,
        "application_id": application_id,
        "artifact_filename": artifact_filename,
        "artifact_sha256": _sha(artifact_raw),
        "artifact_bytes": len(artifact_raw),
        "artifact_manifest_root": manifest["manifest_root"],
        "receipt_sha256": _sha(receipt_raw),
        "receipt_root": receipt["receipt_root"],
        "predecessor_audit_return_sha256": audit["return_sha256"],
        "predecessor_audit_report_root": audit["report_root"],
        "repaired_hold_ids": repaired_ids,
        "repairs_claimed": len(repaired_ids),
        "preserved_external_hold_ids": list(EXTERNAL_HOLDS),
        "preserved_limitations": deepcopy(limitations),
        "current_source_stage_i1_reissued": True,
        "current_source_v2_root": report["current_source_v2_root"],
        "stage_i1_subject_root": report["application_root"],
        "subject_binding_root": index["subject_binding_root"],
        "qualification_root": report["qualification_root"],
        "repair_result_root": report["repair_result_root"],
        "governance_root": receipt["governance_root"],
        "focused_tests": deepcopy(receipt["focused_tests"]),
        "full_tests": deepcopy(receipt["full_tests"]),
        "test_accounting": deepcopy(report["test_accounting"]),
        "claimed_status": "HOLD_FOR_REPAIR",
        "content_review_status":
            "EXACT_SELF_REPORTED_REPAIR_RECONCILED_NOT_INDEPENDENT_REVIEW",
        "independent_review_claimed": False,
        "hold_clearance": "NONE",
        "execution_eligible": False,
        "application_execution_authorized": False,
        **BOUNDARY,
    }
    return {**body, "return_envelope_root": root(body)}


def build_repair_return_register(audits: dict[str, Any],
                                 packages: dict[str, bytes]) -> dict[str, Any]:
    rows = []
    observed: set[str] = set()
    for package_filename, package in sorted(packages.items()):
        manifest = verify_deterministic_zip(
            package, expected_schema=PACKAGE_SCHEMA, expected_role=PACKAGE_ROLE)
        members = _archive_members(package)
        envelope = strict_loads(members["REPAIR-RETURN-ENVELOPE.json"])
        artifact_names = [name for name in members if name.startswith("returned/")
                          and name.endswith(".zip")]
        require(len(artifact_names) == 1 and "RETURN-RECEIPT.json" in members,
                "ECOSYSTEM_REPAIR_PACKAGE_CONTENT_INVALID")
        rebuilt = receive_repair_return(
            audits, application_id=envelope["application_id"],
            artifact_raw=members[artifact_names[0]],
            artifact_filename=artifact_names[0].split("/", 1)[1],
            receipt_raw=members["RETURN-RECEIPT.json"])
        require(rebuilt == envelope, "ECOSYSTEM_REPAIR_ENVELOPE_MISMATCH")
        application_id = envelope["application_id"]
        require(application_id not in observed, "ECOSYSTEM_REPAIR_APPLICATION_DUPLICATE")
        observed.add(application_id)
        row_body = {
            **deepcopy(envelope),
            "package_filename": package_filename,
            "package_sha256": _sha(package),
            "package_manifest_root": manifest["manifest_root"],
        }
        rows.append({**row_body, "repair_return_row_root": root(row_body)})
    body = {
        "schema": REGISTER_SCHEMA,
        "fixed_application_denominator": len(APPLICATIONS),
        "repair_return_count": len(rows),
        "repaired_application_count": len(rows),
        "applications_without_repair_return": [item for item in APPLICATIONS
                                                if item not in observed],
        "repairs": rows,
        "all_holds_cleared": False,
        "application_execution_authorized": False,
        **BOUNDARY,
    }
    return {**body, "repair_register_root": root(body)}

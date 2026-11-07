"""Static reconciliation of exact ecosystem successor-work returns.

This module reads returned evidence but does not treat builder assertions as
independent review, clear any hold, or authorize application execution.
"""
from __future__ import annotations

import hashlib
import io
import zipfile
from typing import Any

from uclop.canonical import canonical_bytes, require, root, strict_loads
from ucm.amcas import BOUNDARY
from ucm.artifacts import verify_deterministic_zip
from ucm.ecosystem_successor_returns import PACKAGE_ROLE, PACKAGE_SCHEMA


APPLICATIONS = (
    "MOSAIC.2D_3D",
    "MOSAIC.AAC",
    "MOSAIC.FIELD_MODELER",
    "MOSAIC.MEDIA_CENTER",
    "MOSAIC.MEMORY_VAULT",
    "MOSAIC.MESSENGER_CRYSTAL",
    "MOSAIC.READER",
)

RECORD_SPECS = {
    "MOSAIC.2D_3D": {
        "path": "REBIND-ENVELOPE.json",
        "status": "successor_plan_status",
        "hold_fields": ("preserved_holds", "added_technical_holds"),
    },
    "MOSAIC.AAC": {
        "path": "MOSAIC-AAC-STAGE-I3-NATIVE-REPAIR-DISPOSITION.json",
        "status": "status",
        "hold_fields": ("holds",),
    },
    "MOSAIC.FIELD_MODELER": {
        "path": "MFF-STAGE-I4-REFINEMENT-RETURN.json",
        "status": "status",
        "hold_fields": ("holds",),
    },
    "MOSAIC.MEDIA_CENTER": {
        "path": "REVIEW-BOUNDARY-RETURN.json",
        "status": "status",
        "hold_fields": ("holds",),
    },
    "MOSAIC.MEMORY_VAULT": {
        "path": "KIT-MANIFEST.json",
        "status": None,
        "hold_fields": ("open_holds",),
    },
    "MOSAIC.MESSENGER_CRYSTAL": {
        "path": "MOSAIC-MESSENGER-CRYSTAL-REPAIR-DESIGN-RETURN.json",
        "status": "status",
        "hold_fields": ("hold_dispositions",),
    },
    "MOSAIC.READER": {
        "path": "REPAIR-REVIEW-BOUNDARY.json",
        "status": None,
        "hold_fields": ("holds",),
    },
}


def _package_content(raw: bytes) -> tuple[dict[str, Any], bytes]:
    verify_deterministic_zip(
        raw, expected_schema=PACKAGE_SCHEMA, expected_role=PACKAGE_ROLE)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        envelope_raw = archive.read("RETURN-ENVELOPE.json")
        envelope = strict_loads(envelope_raw)
        require(canonical_bytes(envelope) == envelope_raw,
                "ECOSYSTEM_SUCCESSOR_OUTCOME_ENVELOPE_NONCANONICAL")
        require(root({key: value for key, value in envelope.items()
                      if key != "return_envelope_root"})
                == envelope["return_envelope_root"],
                "ECOSYSTEM_SUCCESSOR_OUTCOME_ENVELOPE_ROOT_INVALID")
        inner = archive.read("returned/" + envelope["artifact_filename"])
    require(hashlib.sha256(inner).hexdigest() == envelope["artifact_sha256"]
            and len(inner) == envelope["artifact_bytes"],
            "ECOSYSTEM_SUCCESSOR_OUTCOME_INNER_INVALID")
    return envelope, inner


def _record(application_id: str, inner: bytes) -> tuple[str, dict[str, Any]]:
    spec = RECORD_SPECS[application_id]
    try:
        with zipfile.ZipFile(io.BytesIO(inner)) as archive:
            record_raw = archive.read(spec["path"])
    except (zipfile.BadZipFile, KeyError, OSError, RuntimeError) as error:
        raise ValueError("ECOSYSTEM_SUCCESSOR_OUTCOME_RECORD_INVALID") from error
    return spec["path"], strict_loads(record_raw)


def _holds(record: dict[str, Any], fields: tuple[str, ...]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for field in fields:
        values = record.get(field, [])
        require(type(values) is list, "ECOSYSTEM_SUCCESSOR_OUTCOME_HOLDS_INVALID")
        for value in values:
            if type(value) is str:
                hold_id, status = value, "OPEN"
            else:
                require(type(value) is dict,
                        "ECOSYSTEM_SUCCESSOR_OUTCOME_HOLD_INVALID")
                hold_id = value.get("hold_id", value.get("hold",
                          value.get("inherited_exact_hold")))
                require(value.get("hold_cleared",
                        value.get("clearance_granted", False)) is False,
                        "ECOSYSTEM_SUCCESSOR_OUTCOME_CLEARANCE_INVALID")
                status = value.get("status", "OPEN")
            require(type(hold_id) is str and bool(hold_id)
                    and type(status) is str and bool(status),
                    "ECOSYSTEM_SUCCESSOR_OUTCOME_HOLD_ID_INVALID")
            output.append({"hold_id": hold_id, "reported_status": status,
                           "coordinator_clearance": "NONE"})
    return output


def _disposition(claimed_status: str) -> str:
    if claimed_status == "HOLD_FOR_REPAIR":
        return "REPAIR_OR_INDEPENDENT_REVIEW_REQUIRED"
    if claimed_status == "ADDRESSED_PENDING_REVIEW":
        return "INDEPENDENT_REVIEW_REQUIRED"
    if claimed_status == "RETURNED_INFORMATION_ONLY":
        return "IMPORT_OR_EQUIVALENCE_REVIEW_REQUIRED"
    if claimed_status == "DRIFT_RECORDED":
        return "REBIND_REQUIRED"
    if claimed_status == "INCOMPLETE_RETURN":
        return "RETURN_REPAIR_REQUIRED"
    return "STATIC_REVIEW_REQUIRED"


def build_successor_outcome_register(packages: dict[str, bytes]) -> dict[str, Any]:
    """Reconcile available exact returns against the fixed seven-app denominator."""
    received: dict[str, dict[str, Any]] = {}
    for filename, package in sorted(packages.items()):
        envelope, inner = _package_content(package)
        application_id = envelope["application_id"]
        require(application_id in APPLICATIONS and application_id not in received,
                "ECOSYSTEM_SUCCESSOR_OUTCOME_APPLICATION_INVALID")
        require(envelope.get("standing") == "INFORMATION_ONLY"
                and envelope.get("authority_effect") == "NONE"
                and envelope.get("real_a5") is False
                and envelope.get("g0") == "CLOSED",
                "ECOSYSTEM_SUCCESSOR_OUTCOME_BOUNDARY_INVALID")
        if application_id not in RECORD_SPECS:
            received[application_id] = {
                "return_status": "RECEIVED_AWAITING_STATIC_ADAPTER",
                "content_review_status": "PENDING",
                "claimed_status": envelope["claimed_status"],
                "package_filename": filename,
                "package_sha256": hashlib.sha256(package).hexdigest(),
                "return_envelope_root": envelope["return_envelope_root"],
                "record_path": None,
                "record_sha256": None,
                "subject_status": None,
                "coordinator_disposition": _disposition(envelope["claimed_status"]),
                "holds": [],
            }
            continue
        record_path, record = _record(application_id, inner)
        record_boundary = record.get("authority_boundary", record)
        require(record_boundary.get("standing") == "INFORMATION_ONLY"
                and record_boundary.get("authority_effect") == "NONE",
                "ECOSYSTEM_SUCCESSOR_OUTCOME_RECORD_BOUNDARY_INVALID")
        if "real_a5" in record_boundary:
            require(record_boundary["real_a5"] is False,
                    "ECOSYSTEM_SUCCESSOR_OUTCOME_RECORD_A5_INVALID")
        if "g0" in record_boundary:
            require(record_boundary["g0"] == "CLOSED",
                    "ECOSYSTEM_SUCCESSOR_OUTCOME_RECORD_G0_INVALID")
        spec = RECORD_SPECS[application_id]
        status_key = spec["status"]
        subject_status = (record.get(status_key) if status_key is not None
                          else envelope["claimed_status"])
        require(type(subject_status) is str and bool(subject_status),
                "ECOSYSTEM_SUCCESSOR_OUTCOME_STATUS_INVALID")
        record_raw = canonical_bytes(record)
        received[application_id] = {
            "return_status": "STATIC_RECONCILED_UNVERIFIED",
            "content_review_status": "STATIC_RECONCILED_NOT_INDEPENDENT_REVIEW",
            "claimed_status": envelope["claimed_status"],
            "package_filename": filename,
            "package_sha256": hashlib.sha256(package).hexdigest(),
            "return_envelope_root": envelope["return_envelope_root"],
            "record_path": record_path,
            "record_sha256": hashlib.sha256(record_raw).hexdigest(),
            "subject_status": subject_status,
            "coordinator_disposition": _disposition(envelope["claimed_status"]),
            "holds": _holds(record, spec["hold_fields"]),
        }

    rows = []
    for application_id in APPLICATIONS:
        rows.append({
            "application_id": application_id,
            **received.get(application_id, {
                "return_status": "PENDING",
                "content_review_status": "PENDING",
                "claimed_status": None,
                "package_filename": None,
                "package_sha256": None,
                "return_envelope_root": None,
                "record_path": None,
                "record_sha256": None,
                "subject_status": None,
                "coordinator_disposition": "RETURN_PENDING",
                "holds": [],
            }),
            "execution_eligible": False,
            "hold_clearance": "NONE",
        })
    body = {
        "schema": "mosaic.ucm.ecosystem-successor-outcome-register.v0.1",
        "fixed_denominator": len(APPLICATIONS),
        "received_count": len(received),
        "pending_count": len(APPLICATIONS) - len(received),
        "all_returns_received": len(received) == len(APPLICATIONS),
        "all_content_independently_reviewed": False,
        "all_holds_cleared": False,
        "application_execution_authorized": False,
        "applications": rows,
        **BOUNDARY,
    }
    return {**body, "outcome_register_root": root(body)}

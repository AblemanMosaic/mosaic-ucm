"""Static, non-authorizing reconciliation of the seven ecosystem returns."""
from __future__ import annotations

import hashlib
import io
import zipfile
from typing import Any

from uclop.canonical import require, root, strict_loads
from ucm.artifacts import verify_deterministic_zip


RECORD_PATHS = {
    "MOSAIC.2D_3D": "MOSAIC-2D_3D-STAGE-I4-NATIVE-RUNNER-READINESS.json",
    "MOSAIC.AAC": "MOSAIC-AAC-STAGE-I3-REPAIR-DISPOSITION.json",
    "MOSAIC.FIELD_MODELER": "MOSAIC-FIELD_MODELER-STAGE-I4-READINESS.json",
    "MOSAIC.MEDIA_CENTER": None,
    "MOSAIC.MEMORY_VAULT": "READINESS-RETURN.json",
    "MOSAIC.MESSENGER_CRYSTAL": None,
    "MOSAIC.READER": "MOSAIC-READER-STAGE-I3-REPAIR-DISPOSITION.json",
}


def _returned_bytes(package: bytes) -> tuple[dict[str, Any], bytes]:
    verify_deterministic_zip(
        package,
        expected_schema="mosaic.ucm.ecosystem-session-return-package.v0.1",
        expected_role="UCM_ECOSYSTEM_SESSION_RETURN_PACKAGE",
    )
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        envelope = strict_loads(archive.read("RETURN-ENVELOPE.json"))
        names = [name for name in archive.namelist() if name.startswith("returned/")]
        require(len(names) == 1, "ECOSYSTEM_OUTCOME_RETURNED_ARTIFACT_INVALID")
        return envelope, archive.read(names[0])


def _content_record(application_id: str, returned: bytes) -> dict[str, Any]:
    path = RECORD_PATHS[application_id]
    if path is None:
        return strict_loads(returned)
    try:
        with zipfile.ZipFile(io.BytesIO(returned)) as archive:
            return strict_loads(archive.read(path))
    except (zipfile.BadZipFile, KeyError, OSError, RuntimeError) as error:
        raise ValueError("ECOSYSTEM_OUTCOME_INNER_ARTIFACT_INVALID") from error


def _holds(record: dict[str, Any]) -> list[dict[str, Any]]:
    values = record.get("holds", record.get("hold_dispositions", []))
    require(type(values) is list, "ECOSYSTEM_OUTCOME_HOLDS_INVALID")
    output = []
    for value in values:
        if type(value) is str:
            output.append({"hold_id": value, "status": "OPEN"})
            continue
        require(type(value) is dict, "ECOSYSTEM_OUTCOME_HOLD_INVALID")
        hold_id = value.get("hold", value.get("hold_id", value.get("inherited_exact_hold")))
        require(type(hold_id) is str and bool(hold_id), "ECOSYSTEM_OUTCOME_HOLD_ID_INVALID")
        require(value.get("hold_cleared", value.get("clearance_granted", False)) is False,
                "ECOSYSTEM_OUTCOME_HOLD_CLEARANCE_INVALID")
        output.append({"hold_id": hold_id, "status": value.get("status", "OPEN")})
    return output


def _disposition(claimed_status: str, record_status: str) -> str:
    if claimed_status == "DRIFT_RECORDED":
        return "REBIND_REQUIRED"
    if claimed_status == "INCOMPLETE_RETURN":
        return "RETURN_REPAIR_REQUIRED"
    if claimed_status == "HOLD_FOR_REPAIR" or "HOLD" in record_status:
        return "REPAIR_OR_REVIEW_REQUIRED"
    return "STATIC_READINESS_ONLY"


def build_outcome_register(packages: dict[str, bytes]) -> dict[str, Any]:
    rows = []
    seen = set()
    for filename, package in sorted(packages.items()):
        envelope, returned = _returned_bytes(package)
        application_id = envelope["application_id"]
        require(application_id in RECORD_PATHS and application_id not in seen,
                "ECOSYSTEM_OUTCOME_APPLICATION_INVALID")
        seen.add(application_id)
        record = _content_record(application_id, returned)
        require(record.get("standing") == "INFORMATION_ONLY"
                and record.get("authority_effect") == "NONE"
                and record.get("real_a5") is False
                and record.get("g0") == "CLOSED",
                "ECOSYSTEM_OUTCOME_BOUNDARY_INVALID")
        holds = _holds(record)
        status = record.get("status", record.get("readiness_status",
                            record.get("plan_status", envelope["claimed_status"])))
        require(type(status) is str and bool(status), "ECOSYSTEM_OUTCOME_STATUS_INVALID")
        gaps = record.get("unresolved_gaps", [])
        require(type(gaps) is list, "ECOSYSTEM_OUTCOME_GAPS_INVALID")
        rows.append({
            "application_id": application_id,
            "package_filename": filename,
            "package_sha256": hashlib.sha256(package).hexdigest(),
            "return_envelope_root": envelope["return_envelope_root"],
            "claimed_status": envelope["claimed_status"],
            "subject_status": status,
            "coordinator_disposition": _disposition(envelope["claimed_status"], status),
            "content_review_status": "STATIC_RECONCILED_NOT_INDEPENDENT_REVIEW",
            "execution_eligible": False,
            "hold_clearance": "NONE",
            "holds": holds,
            "unresolved_gaps": gaps,
        })
    require(seen == set(RECORD_PATHS), "ECOSYSTEM_OUTCOME_DENOMINATOR_INVALID")
    body = {
        "schema": "mosaic.ucm.ecosystem-integration-outcome-register.v0.1",
        "fixed_denominator": 7,
        "all_returns_received": True,
        "all_content_independently_reviewed": False,
        "application_execution_authorized": False,
        "applications": sorted(rows, key=lambda item: item["application_id"]),
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
        "real_a5": False,
        "g0": "CLOSED",
    }
    return {**body, "outcome_register_root": root(body)}

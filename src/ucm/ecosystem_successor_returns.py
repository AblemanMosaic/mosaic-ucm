"""Exact, non-authorizing custody for ecosystem successor-work returns."""
from __future__ import annotations

import hashlib
import io
import zipfile
from typing import Any

from uclop.canonical import canonical_bytes, require, root, strict_loads
from ucm.amcas import BOUNDARY
from ucm.artifacts import verify_deterministic_zip


CLAIMED_STATUSES = {
    "ADDRESSED_PENDING_REVIEW", "READY_FOR_REVIEW", "HOLD_FOR_REPAIR",
    "DRIFT_RECORDED", "RETURNED_INFORMATION_ONLY", "INCOMPLETE_RETURN",
}
PACKAGE_SCHEMA = "mosaic.ucm.ecosystem-successor-return-package.v0.1"
PACKAGE_ROLE = "UCM_ECOSYSTEM_SUCCESSOR_RETURN_PACKAGE"


def receive_successor_return(
    dispatch: Any,
    *,
    application_id: str,
    artifact_raw: bytes,
    artifact_filename: str,
    claimed_status: str,
) -> dict[str, Any]:
    require(type(dispatch) is dict, "ECOSYSTEM_SUCCESSOR_DISPATCH_INVALID")
    require(root({key: value for key, value in dispatch.items()
                  if key != "dispatch_root"}) == dispatch.get("dispatch_root"),
            "ECOSYSTEM_SUCCESSOR_DISPATCH_ROOT_INVALID")
    require(dispatch.get("application_execution_authorized") is False
            and dispatch.get("transport_acceptance_is_not_work_completion") is True,
            "ECOSYSTEM_SUCCESSOR_DISPATCH_AUTHORITY_INVALID")
    rows = [row for row in dispatch["applications"]
            if row["application_id"] == application_id]
    require(len(rows) == 1, "ECOSYSTEM_SUCCESSOR_APPLICATION_INVALID")
    require(type(artifact_raw) is bytes and len(artifact_raw) > 0,
            "ECOSYSTEM_SUCCESSOR_ARTIFACT_EMPTY")
    require(type(artifact_filename) is str and artifact_filename
            and "/" not in artifact_filename and "\\" not in artifact_filename,
            "ECOSYSTEM_SUCCESSOR_FILENAME_INVALID")
    require(claimed_status in CLAIMED_STATUSES,
            "ECOSYSTEM_SUCCESSOR_CLAIMED_STATUS_INVALID")
    row = rows[0]
    body = {
        "schema": "mosaic.ucm.ecosystem-successor-return-envelope.v0.1",
        "dispatch_root": dispatch["dispatch_root"],
        "work_program_root": dispatch["work_program_root"],
        "application_id": application_id,
        "thread_id": row["thread_id"],
        "work_lane": row["work_lane"],
        "next_action": row["next_action"],
        "prior_return_envelope_root": row["return_envelope_root"],
        "artifact_filename": artifact_filename,
        "artifact_sha256": hashlib.sha256(artifact_raw).hexdigest(),
        "artifact_bytes": len(artifact_raw),
        "claimed_status": claimed_status,
        "integration_status": "RECEIVED_UNVERIFIED",
        "content_review_status": "PENDING",
        "application_execution_observed": "NOT_ESTABLISHED",
        "hold_clearance": "NOT_ESTABLISHED",
        "non_claims": [
            "NOT_CONTENT_VALIDATION", "NOT_HOLD_CLEARANCE",
            "NOT_APPLICATION_EXECUTION_EVIDENCE", "NOT_AUTHORITY",
        ],
        **BOUNDARY,
    }
    return {**body, "return_envelope_root": root(body)}


def build_successor_return_index(
    dispatch: Any, packages: dict[str, bytes]
) -> dict[str, Any]:
    require(root({key: value for key, value in dispatch.items()
                  if key != "dispatch_root"}) == dispatch.get("dispatch_root"),
            "ECOSYSTEM_SUCCESSOR_INDEX_DISPATCH_INVALID")
    dispatch_rows = {row["application_id"]: row
                     for row in dispatch["applications"]}
    received: dict[str, dict[str, Any]] = {}
    for filename, raw in sorted(packages.items()):
        manifest = verify_deterministic_zip(
            raw, expected_schema=PACKAGE_SCHEMA, expected_role=PACKAGE_ROLE)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            envelope_raw = archive.read("RETURN-ENVELOPE.json")
            envelope = strict_loads(envelope_raw)
            require(canonical_bytes(envelope) == envelope_raw,
                    "ECOSYSTEM_SUCCESSOR_ENVELOPE_NONCANONICAL")
            require(root({key: value for key, value in envelope.items()
                          if key != "return_envelope_root"})
                    == envelope["return_envelope_root"],
                    "ECOSYSTEM_SUCCESSOR_ENVELOPE_ROOT_INVALID")
            require(envelope["dispatch_root"] == dispatch["dispatch_root"],
                    "ECOSYSTEM_SUCCESSOR_ENVELOPE_DISPATCH_INVALID")
            application_id = envelope["application_id"]
            require(application_id in dispatch_rows,
                    "ECOSYSTEM_SUCCESSOR_APPLICATION_UNKNOWN")
            require(envelope["prior_return_envelope_root"]
                    == dispatch_rows[application_id]["return_envelope_root"],
                    "ECOSYSTEM_SUCCESSOR_PRIOR_RETURN_INVALID")
            inner = archive.read("returned/" + envelope["artifact_filename"])
            require(hashlib.sha256(inner).hexdigest() == envelope["artifact_sha256"]
                    and len(inner) == envelope["artifact_bytes"],
                    "ECOSYSTEM_SUCCESSOR_INNER_ARTIFACT_INVALID")
        require(application_id not in received,
                "ECOSYSTEM_SUCCESSOR_APPLICATION_DUPLICATE")
        received[application_id] = {
            "return_status": "RECEIVED_UNVERIFIED",
            "package_filename": filename,
            "package_sha256": hashlib.sha256(raw).hexdigest(),
            "package_manifest_root": manifest["manifest_root"],
            "return_envelope_root": envelope["return_envelope_root"],
            "claimed_status": envelope["claimed_status"],
            "content_review_status": "PENDING",
        }
    rows = []
    for row in dispatch["applications"]:
        state = received.get(row["application_id"], {
            "return_status": "PENDING", "package_filename": None,
            "package_sha256": None, "package_manifest_root": None,
            "return_envelope_root": None, "claimed_status": None,
            "content_review_status": "PENDING",
        })
        rows.append({
            "application_id": row["application_id"],
            "thread_id": row["thread_id"],
            "work_lane": row["work_lane"],
            "prior_return_envelope_root": row["return_envelope_root"],
            **state,
        })
    body = {
        "schema": "mosaic.ucm.ecosystem-successor-return-index.v0.1",
        "dispatch_root": dispatch["dispatch_root"],
        "fixed_denominator": len(rows),
        "received_count": len(received),
        "pending_count": len(rows) - len(received),
        "applications": rows,
        "all_content_reviewed": False,
        "application_execution_authorized": False,
        **BOUNDARY,
    }
    return {**body, "return_index_root": root(body)}

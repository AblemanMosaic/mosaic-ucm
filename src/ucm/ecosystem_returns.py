"""Non-authorizing receipt envelope for exact ecosystem session returns."""
from __future__ import annotations

import hashlib
import io
import zipfile
from typing import Any

from uclop.canonical import require, root
from ucm.amcas import BOUNDARY
from ucm.artifacts import verify_deterministic_zip


CLAIMED_STATUSES = {
    "READY_FOR_REVIEW", "HOLD_FOR_REPAIR", "DRIFT_RECORDED",
    "RETURNED_INFORMATION_ONLY", "INCOMPLETE_RETURN",
}


def receive_session_return(
    dispatch: Any,
    *,
    application_id: str,
    artifact_raw: bytes,
    artifact_filename: str,
    claimed_status: str,
) -> dict:
    require(type(dispatch) is dict, "ECOSYSTEM_RETURN_DISPATCH_INVALID")
    require(root({key: value for key, value in dispatch.items()
                  if key != "dispatch_root"}) == dispatch.get("dispatch_root"),
            "ECOSYSTEM_RETURN_DISPATCH_ROOT_INVALID")
    require(dispatch.get("application_execution_authorized") is False
            and dispatch.get("stage_i3_shadow_authorized") is False,
            "ECOSYSTEM_RETURN_DISPATCH_AUTHORITY_INVALID")
    rows = [row for row in dispatch["applications"]
            if row["application_id"] == application_id]
    require(len(rows) == 1, "ECOSYSTEM_RETURN_APPLICATION_INVALID")
    require(type(artifact_raw) is bytes and len(artifact_raw) > 0,
            "ECOSYSTEM_RETURN_ARTIFACT_EMPTY")
    require(type(artifact_filename) is str and artifact_filename
            and "/" not in artifact_filename and "\\" not in artifact_filename,
            "ECOSYSTEM_RETURN_FILENAME_INVALID")
    require(claimed_status in CLAIMED_STATUSES,
            "ECOSYSTEM_RETURN_CLAIMED_STATUS_INVALID")
    row = rows[0]
    body = {
        "schema": "mosaic.ucm.ecosystem-session-return-envelope.v0.1",
        "dispatch_root": dispatch["dispatch_root"],
        "reconciliation_root": dispatch["reconciliation_root"],
        "application_id": application_id,
        "thread_id": row["thread_id"],
        "work_class": row["work_class"],
        "controlling_instruction_sha256": row["pipeline_bound_instruction_sha256"],
        "controlling_plan_sha256": row["pipeline_bound_plan_sha256"],
        "prior_plan_status": row["plan_status"],
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


def build_return_index(dispatch: Any, packages: dict[str, bytes]) -> dict:
    require(root({key: value for key, value in dispatch.items()
                  if key != "dispatch_root"}) == dispatch.get("dispatch_root"),
            "ECOSYSTEM_RETURN_INDEX_DISPATCH_INVALID")
    received: dict[str, dict] = {}
    for filename, raw in sorted(packages.items()):
        manifest = verify_deterministic_zip(
            raw, expected_schema="mosaic.ucm.ecosystem-session-return-package.v0.1",
            expected_role="UCM_ECOSYSTEM_SESSION_RETURN_PACKAGE")
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            envelope_raw = archive.read("RETURN-ENVELOPE.json")
            from uclop.canonical import canonical_bytes, strict_loads
            envelope = strict_loads(envelope_raw)
            require(canonical_bytes(envelope) == envelope_raw,
                    "ECOSYSTEM_RETURN_ENVELOPE_NONCANONICAL")
            require(root({key: value for key, value in envelope.items()
                          if key != "return_envelope_root"})
                    == envelope["return_envelope_root"],
                    "ECOSYSTEM_RETURN_ENVELOPE_ROOT_INVALID")
            require(envelope["dispatch_root"] == dispatch["dispatch_root"],
                    "ECOSYSTEM_RETURN_ENVELOPE_DISPATCH_INVALID")
            inner = archive.read("returned/" + envelope["artifact_filename"])
            require(hashlib.sha256(inner).hexdigest() == envelope["artifact_sha256"]
                    and len(inner) == envelope["artifact_bytes"],
                    "ECOSYSTEM_RETURN_INNER_ARTIFACT_INVALID")
        application_id = envelope["application_id"]
        require(application_id not in received,
                "ECOSYSTEM_RETURN_APPLICATION_DUPLICATE")
        received[application_id] = {
            "return_status": "RECEIVED_UNVERIFIED",
            "package_filename": filename,
            "package_sha256": hashlib.sha256(raw).hexdigest(),
            "package_manifest_root": manifest["manifest_root"],
            "return_envelope_root": envelope["return_envelope_root"],
            "claimed_status": envelope["claimed_status"],
            "content_review_status": envelope["content_review_status"],
        }
    rows = []
    for dispatch_row in dispatch["applications"]:
        application_id = dispatch_row["application_id"]
        state = received.get(application_id, {
            "return_status": "PENDING", "package_filename": None,
            "package_sha256": None, "package_manifest_root": None,
            "return_envelope_root": None, "claimed_status": None,
            "content_review_status": "PENDING",
        })
        rows.append({
            "application_id": application_id,
            "thread_id": dispatch_row["thread_id"],
            "work_class": dispatch_row["work_class"],
            "controlling_plan_sha256": dispatch_row["pipeline_bound_plan_sha256"],
            **state,
        })
    require(set(received).issubset({row["application_id"] for row in dispatch["applications"]}),
            "ECOSYSTEM_RETURN_INDEX_UNKNOWN_APPLICATION")
    body = {
        "schema": "mosaic.ucm.ecosystem-session-return-index.v0.1",
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

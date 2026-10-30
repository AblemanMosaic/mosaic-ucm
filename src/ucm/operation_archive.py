"""Portable deterministic operation custody archive."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any
import zipfile

from uclop.canonical import canonical_bytes, exact_keys, require, root, strict_loads

from .amcas import BOUNDARY
from .artifacts import deterministic_zip, verify_deterministic_zip
from .operation_gateway import OperationGateway, validate_operation_history
from .operation_proofs import build_operation_proof_bundle, verify_operation_proof_bundle
from .thr_cas import build_thr_manifest, verify_thr_manifest


SCHEMA = "mosaic.ucm.operational-archive.v0.1"
ROLE = "UCM_OPERATIONAL_CUSTODY_ARCHIVE"


def build_operation_archive(gateway: OperationGateway, *, operation_id: str,
                            expected_issuer_public_key_hex: str,
                            expected_jurisdiction_root: str,
                            expected_revocation_registry_root: str) -> bytes:
    events = gateway.journal.verify()
    checked = validate_operation_history(
        operation_id=operation_id, events=events,
        expected_issuer_public_key_hex=expected_issuer_public_key_hex,
        expected_jurisdiction_root=expected_jurisdiction_root,
        expected_revocation_registry_root=expected_revocation_registry_root)
    state = checked["state"]
    require(state["terminal"], "OPERATION_ARCHIVE_REQUIRES_TERMINAL_STATE")
    operation_events = [row for row in events
        if row.get("payload", {}).get("operation_id") == operation_id
        and row.get("event_type", "").startswith("OPERATION_")]
    proof = build_operation_proof_bundle(
        operation_id=operation_id, events=events,
        expected_issuer_public_key_hex=expected_issuer_public_key_hex,
        expected_jurisdiction_root=expected_jurisdiction_root,
        expected_revocation_registry_root=expected_revocation_registry_root)
    require(proof["status"] == "PASS", "OPERATION_ARCHIVE_PROOF_INCOMPLETE")
    payloads = {
        "OPERATION-CONTRACT.json": canonical_bytes(checked["contract"]),
        "OPERATION-STATE.json": canonical_bytes(state),
        "OPERATION-EVENTS.json": canonical_bytes(operation_events),
        "OPERATION-PROOF.json": canonical_bytes(proof),
        "README.txt": ("UCM operational custody archive v0.1\n"
                       "Receipt-mediated external execution; UCM is not the executor.\n"
                       "INFORMATION_ONLY; authority effect NONE; real A5 false; G0 closed.\n").encode("ascii"),
    }
    thr = build_thr_manifest(
        application_id=checked["contract"]["application_id"], payloads=payloads,
        meaning={"operation_id": operation_id,
                 "action_id": checked["contract"]["action_id"],
                 "terminal_state": state["state"]},
        admissibility={"contract_root": checked["contract"]["contract_root"],
                       "permit_root": checked["contract"]["permit"]["permit_root"],
                       "proof_root": proof["proof_root"]},
        locality={"jurisdiction_root": checked["contract"]["jurisdiction_root"],
                  "subject_identity_root": checked["contract"]["subject_identity_root"],
                  "session_root": checked["contract"]["session_root"]},
        receipts={"state_root": state["state_root"],
                  "g1_root": state["g1_root"], "dispatch_root": state["dispatch_root"],
                  "terminal_receipt_root": state["terminal_receipt_root"],
                  "g2_root": state["g2_root"], "g3_root": state["g3_root"]})
    payloads["THR-MANIFEST.json"] = canonical_bytes(thr)
    return deterministic_zip(payloads, schema=SCHEMA, artifact_role=ROLE)


def verify_operation_archive(raw: bytes, *,
                             expected_issuer_public_key_hex: str,
                             expected_jurisdiction_root: str,
                             expected_revocation_registry_root: str) -> dict[str, Any]:
    manifest = verify_deterministic_zip(raw, expected_schema=SCHEMA,
                                        expected_role=ROLE)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        payloads = {name: archive.read(name) for name in archive.namelist()
                    if name != "MANIFEST.json"}
    contract = strict_loads(payloads["OPERATION-CONTRACT.json"])
    state = strict_loads(payloads["OPERATION-STATE.json"])
    events = strict_loads(payloads["OPERATION-EVENTS.json"])
    proof = strict_loads(payloads["OPERATION-PROOF.json"])
    thr = strict_loads(payloads.pop("THR-MANIFEST.json"))
    checked = validate_operation_history(
        operation_id=contract["operation_id"], events=events,
        expected_issuer_public_key_hex=expected_issuer_public_key_hex,
        expected_jurisdiction_root=expected_jurisdiction_root,
        expected_revocation_registry_root=expected_revocation_registry_root)
    require(checked["contract"] == contract and checked["state"] == state,
            "OPERATION_ARCHIVE_STATE_INVALID")
    verify_operation_proof_bundle(
        proof, events=events,
        expected_issuer_public_key_hex=expected_issuer_public_key_hex,
        expected_jurisdiction_root=expected_jurisdiction_root,
        expected_revocation_registry_root=expected_revocation_registry_root)
    verify_thr_manifest(thr, payloads=payloads)
    body = {"schema": "mosaic.ucm.operational-archive-verification.v0.1",
            "archive_sha256": hashlib.sha256(raw).hexdigest(),
            "manifest_root": manifest["manifest_root"],
            "operation_id": contract["operation_id"],
            "contract_root": contract["contract_root"],
            "state_root": state["state_root"], "proof_root": proof["proof_root"],
            "thr_body_root": thr["h_body"], "status": "PASS", **BOUNDARY}
    return {**body, "verification_root": root(body)}

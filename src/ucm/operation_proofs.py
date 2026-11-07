"""Small re-derived proof ledger for the receipt-mediated operation path."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, root

from .amcas import BOUNDARY
from .operation_gateway import validate_operation_history


SCHEMA = "mosaic.ucm.operational-proof-bundle.v0.1"


def build_operation_proof_bundle(*, operation_id: str, events: Any,
                                 expected_issuer_public_key_hex: str,
                                 expected_jurisdiction_root: str,
                                 expected_revocation_registry_root: str) -> dict[str, Any]:
    checked = validate_operation_history(
        operation_id=operation_id, events=events,
        expected_issuer_public_key_hex=expected_issuer_public_key_hex,
        expected_jurisdiction_root=expected_jurisdiction_root,
        expected_revocation_registry_root=expected_revocation_registry_root)
    state = checked["state"]
    obligations = [
        {"id": "PERMIT_AND_REVOCATION_BOUND", "status": "PASS"},
        {"id": "CONTRACT_AND_IDEMPOTENCY_BOUND", "status": "PASS"},
        {"id": "G1_PRECEDES_EXTERNAL_DISPATCH", "status":
            "PASS" if state["g1_root"] else "PENDING"},
        {"id": "DISPATCH_IS_EXACTLY_ONCE", "status":
            "PASS" if state["dispatch_root"] else "PENDING"},
        {"id": "EXECUTOR_TERMINAL_RECEIPT_BOUND", "status":
            "PASS" if state["terminal_receipt_root"] else "PENDING"},
        {"id": "G2_AND_G3_DERIVED", "status":
            "PASS" if state["g2_root"] and state["g3_root"] else "PENDING"},
        {"id": "TERMINAL_STATE_REDERIVED", "status":
            "PASS" if state["terminal"] else "PENDING"},
    ]
    body = {
        "schema": SCHEMA, "operation_id": operation_id,
        "contract_root": checked["contract"]["contract_root"],
        "state_root": state["state_root"], "event_roots": checked["event_roots"],
        "obligations": obligations,
        "status": "PASS" if all(row["status"] == "PASS" for row in obligations)
        else "INCOMPLETE", **BOUNDARY,
    }
    return {**body, "proof_root": root(body)}


def verify_operation_proof_bundle(value: Any, *, events: Any,
                                  expected_issuer_public_key_hex: str,
                                  expected_jurisdiction_root: str,
                                  expected_revocation_registry_root: str) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "operation_id", "contract_root",
        "state_root", "event_roots", "obligations", "status", "standing",
        "authority_effect", "real_a5", "g0", "proof_root"})
    expected = build_operation_proof_bundle(
        operation_id=item["operation_id"], events=events,
        expected_issuer_public_key_hex=expected_issuer_public_key_hex,
        expected_jurisdiction_root=expected_jurisdiction_root,
        expected_revocation_registry_root=expected_revocation_registry_root)
    require(item == expected, "OPERATION_PROOF_BUNDLE_INVALID")
    return deepcopy(item)

from __future__ import annotations

import tempfile
from pathlib import Path
import os
import subprocess
import sys
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from uclop.canonical import canonical_bytes, root
from ucm.amcas import BOUNDARY
from ucm.operation_archive import build_operation_archive, verify_operation_archive
from ucm.operation_gateway import (
    DISPATCH_SCHEMA, PERMIT_SCHEMA, REVOCATION_SCHEMA, TERMINAL_SCHEMA,
    OperationGateway, build_operation_contract, validate_operation_history,
)
from ucm.operation_proofs import build_operation_proof_bundle
from ucm.capabilities import invoke
from ucm.system import capability_registry


ISSUER = Ed25519PrivateKey.from_private_bytes(b"\x11" * 32)
EXECUTOR = Ed25519PrivateKey.from_private_bytes(b"\x22" * 32)


def public(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def signed(body: dict, key: Ed25519PrivateKey, root_field: str) -> dict:
    signature = key.sign(canonical_bytes(body)).hex()
    return {**body, "signature_hex": signature,
            root_field: root({**body, "signature_hex": signature})}


def fixture(now: int = 100) -> tuple[dict, dict, dict]:
    jurisdiction = root({"jurisdiction": "TEST"})
    revocation_body = {
        "schema": REVOCATION_SCHEMA, "issuer_public_key_hex": public(ISSUER),
        "jurisdiction_root": jurisdiction, "generation": 1, "sequence": 1,
        "valid_at": now, "revoked_permit_roots": [],
        "predecessor_root": "0" * 64, **BOUNDARY,
    }
    revocation = signed(revocation_body, ISSUER, "revocation_registry_root")
    permit_body = {
        "schema": PERMIT_SCHEMA, "permit_id": "permit:test:1",
        "issuer_public_key_hex": public(ISSUER),
        "subject_identity_root": root({"subject": "user"}),
        "session_root": root({"session": "agent"}),
        "jurisdiction_root": jurisdiction, "application_id": "APP.TEST",
        "action_id": "WRITE.RESULT", "request_root": root({"request": 1}),
        "executor_public_key_hex": public(EXECUTOR),
        "allowed_effect_classes": ["WRITE_WORKSPACE"],
        "budget": {"max_cases": 3, "max_duration_ms": 10000,
                   "max_output_bytes": 4096},
        "rollback_root": root({"rollback": "restore"}), "generation": 1,
        "nonce": root({"nonce": 1}), "issued_at": 90, "not_before": 95,
        "expires_at": 200, "revocation_registry_root": revocation["revocation_registry_root"],
        **BOUNDARY,
    }
    permit = signed(permit_body, ISSUER, "permit_root")
    contract = build_operation_contract(
        operation_id="op:test:1", permit=permit, revocation_registry=revocation,
        expected_issuer_public_key_hex=public(ISSUER),
        expected_jurisdiction_root=jurisdiction,
        expected_revocation_registry_root=revocation["revocation_registry_root"],
        requested_effect_classes=["WRITE_WORKSPACE"],
        idempotency_key=root({"idempotency": 1}),
        expected_result_root=root({"result": "expected"}), now=now)
    return revocation, permit, contract


def dispatch_receipt(prepared: dict, contract: dict, *, started_at: int = 101) -> dict:
    body = {
        "schema": DISPATCH_SCHEMA, "operation_id": contract["operation_id"],
        "contract_root": contract["contract_root"],
        "g1_root": prepared["g1"]["receipt_root"],
        "dispatch_authorization_root": prepared["dispatch_authorization"]["receipt_root"],
        "idempotency_key": contract["idempotency_key"],
        "dispatch_nonce": prepared["dispatch_authorization"]["dispatch_nonce"],
        "started_at": started_at, "status": "DISPATCHED", **BOUNDARY,
    }
    return signed(body, EXECUTOR, "receipt_root")


def terminal_receipt(dispatched: dict, contract: dict, *, ended_at: int = 102) -> dict:
    body = {
        "schema": TERMINAL_SCHEMA, "operation_id": contract["operation_id"],
        "contract_root": contract["contract_root"],
        "dispatch_root": dispatched["dispatch_receipt"]["receipt_root"],
        "terminal_status": "COMPLETED", "result_root": contract["expected_result_root"],
        "output_bytes": 128, "completed_cases": 1,
        "observed_effect_classes": ["WRITE_WORKSPACE"], "ended_at": ended_at,
        "receipt_nonce": root({"receipt": ended_at}), **BOUNDARY,
    }
    return signed(body, EXECUTOR, "receipt_root")


class OperationalGatewayPositiveTests(unittest.TestCase):
    def test_library_agent_cli_and_registry_share_one_contract_surface(self) -> None:
        revocation, permit, contract = fixture()
        payload = {
            "operation_id": contract["operation_id"], "permit": permit,
            "revocation_registry": revocation,
            "expected_issuer_public_key_hex": public(ISSUER),
            "expected_jurisdiction_root": contract["jurisdiction_root"],
            "expected_revocation_registry_root": revocation["revocation_registry_root"],
            "requested_effect_classes": ["WRITE_WORKSPACE"],
            "idempotency_key": contract["idempotency_key"],
            "expected_result_root": contract["expected_result_root"], "now": 100,
        }
        request = {"schema": "mosaic.ucm.request.v0.1",
                   "surface": "BUILD_OPERATIONAL_CONTRACT", "payload": payload,
                   "request_id": root({"surface": "BUILD_OPERATIONAL_CONTRACT",
                                       "payload": payload})}
        agent = invoke(request)
        self.assertEqual(contract, agent["result"])
        surfaces = {row["name"]: row for row in capability_registry()["surfaces"]}
        self.assertEqual("PURE_COMPUTATION",
                         surfaces["BUILD_OPERATIONAL_CONTRACT"]["effect_scope"])
        self.assertEqual("LOCAL_ARTIFACT_PREPARATION",
                         surfaces["PREPARE_OPERATIONAL_GATEWAY"]["effect_scope"])
        with tempfile.TemporaryDirectory() as raw:
            payload_path = Path(raw) / "payload.json"
            out = Path(raw) / "response.json"
            payload_path.write_bytes(canonical_bytes(payload))
            environment = {**os.environ,
                           "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
                           "PYTHONDONTWRITEBYTECODE": "1"}
            subprocess.run([sys.executable, "-m", "ucm.cli", "operational-invoke",
                "BUILD_OPERATIONAL_CONTRACT", str(payload_path), "--out", str(out)],
                cwd=Path(__file__).resolve().parents[1], check=True,
                capture_output=True, text=True, env=environment)
            self.assertEqual(canonical_bytes(agent), out.read_bytes())

    def test_complete_restart_proof_and_portable_archive(self) -> None:
        revocation, _, contract = fixture()
        with tempfile.TemporaryDirectory() as raw:
            gateway = OperationGateway(Path(raw))
            prepared = gateway.prepare(contract,
                expected_issuer_public_key_hex=public(ISSUER),
                expected_jurisdiction_root=contract["jurisdiction_root"],
                expected_revocation_registry_root=revocation["revocation_registry_root"])
            # A byte-identical retry is idempotent and does not add events.
            count = len(gateway.journal.verify())
            gateway.prepare(contract, expected_issuer_public_key_hex=public(ISSUER),
                expected_jurisdiction_root=contract["jurisdiction_root"],
                expected_revocation_registry_root=revocation["revocation_registry_root"])
            self.assertEqual(count, len(gateway.journal.verify()))
            dispatched = gateway.record_dispatch(
                contract["operation_id"], dispatch_receipt(prepared, contract))
            # Restart from durable state before recording the terminal receipt.
            gateway = OperationGateway(Path(raw))
            result = gateway.record_terminal(contract["operation_id"],
                terminal_receipt(dispatched, contract))
            self.assertEqual("COMPLETED", result["state"]["state"])
            checked = validate_operation_history(operation_id=contract["operation_id"],
                events=gateway.journal.verify(),
                expected_issuer_public_key_hex=public(ISSUER),
                expected_jurisdiction_root=contract["jurisdiction_root"],
                expected_revocation_registry_root=revocation["revocation_registry_root"])
            self.assertEqual("COMPLETED", checked["state"]["state"])
            proof = build_operation_proof_bundle(operation_id=contract["operation_id"],
                events=gateway.journal.verify(),
                expected_issuer_public_key_hex=public(ISSUER),
                expected_jurisdiction_root=contract["jurisdiction_root"],
                expected_revocation_registry_root=revocation["revocation_registry_root"])
            self.assertEqual("PASS", proof["status"])
            archive = build_operation_archive(gateway,
                operation_id=contract["operation_id"],
                expected_issuer_public_key_hex=public(ISSUER),
                expected_jurisdiction_root=contract["jurisdiction_root"],
                expected_revocation_registry_root=revocation["revocation_registry_root"])
            verification = verify_operation_archive(archive,
                expected_issuer_public_key_hex=public(ISSUER),
                expected_jurisdiction_root=contract["jurisdiction_root"],
                expected_revocation_registry_root=revocation["revocation_registry_root"])
            self.assertEqual("PASS", verification["status"])

    def test_uncertain_result_is_reconciled_without_redispatch(self) -> None:
        revocation, _, contract = fixture()
        with tempfile.TemporaryDirectory() as raw:
            gateway = OperationGateway(Path(raw))
            prepared = gateway.prepare(contract,
                expected_issuer_public_key_hex=public(ISSUER),
                expected_jurisdiction_root=contract["jurisdiction_root"],
                expected_revocation_registry_root=revocation["revocation_registry_root"])
            dispatched = gateway.record_dispatch(contract["operation_id"],
                dispatch_receipt(prepared, contract))
            uncertain = gateway.mark_uncertain(contract["operation_id"],
                                                reason_code="CONNECTION_LOST")
            self.assertTrue(uncertain["state"]["requires_reconciliation"])
            gateway = OperationGateway(Path(raw))
            result = gateway.reconcile(contract["operation_id"],
                terminal_receipt(dispatched, contract))
            self.assertEqual("COMPLETED", result["state"]["state"])
            self.assertFalse(result["state"]["redispatch_allowed"])

    def test_cancel_before_external_dispatch(self) -> None:
        revocation, _, contract = fixture()
        with tempfile.TemporaryDirectory() as raw:
            gateway = OperationGateway(Path(raw))
            gateway.prepare(contract, expected_issuer_public_key_hex=public(ISSUER),
                expected_jurisdiction_root=contract["jurisdiction_root"],
                expected_revocation_registry_root=revocation["revocation_registry_root"])
            result = gateway.cancel(contract["operation_id"], reason_code="USER_CANCELLED")
            self.assertEqual("CANCELLED", result["state"]["state"])
            self.assertTrue(result["state"]["terminal"])


if __name__ == "__main__":
    unittest.main()

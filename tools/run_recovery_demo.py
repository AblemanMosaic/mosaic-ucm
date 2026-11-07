"""Positive, no-effect demonstration of uncertain recovery across sessions."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from uclop.canonical import canonical_bytes, root  # noqa: E402
from ucm.amcas import BOUNDARY  # noqa: E402
from ucm.operation_archive import build_operation_archive, verify_operation_archive  # noqa: E402
from ucm.operation_gateway import (DISPATCH_SCHEMA, PERMIT_SCHEMA, REVOCATION_SCHEMA,
                                   TERMINAL_SCHEMA, OperationGateway,
                                   build_operation_contract)  # noqa: E402


ISSUER = Ed25519PrivateKey.from_private_bytes(b"\x71" * 32)
EXECUTOR = Ed25519PrivateKey.from_private_bytes(b"\x72" * 32)


def public(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def signed(body: dict, key: Ed25519PrivateKey, root_field: str) -> dict:
    signature = key.sign(canonical_bytes(body)).hex()
    signed_body = {**body, "signature_hex": signature}
    return {**signed_body, root_field: root(signed_body)}


def build_fixture() -> tuple[dict, dict]:
    jurisdiction = root({"jurisdiction": "UCM_RECOVERY_DEMO"})
    revocation = signed({
        "schema": REVOCATION_SCHEMA, "issuer_public_key_hex": public(ISSUER),
        "jurisdiction_root": jurisdiction, "generation": 1, "sequence": 1,
        "valid_at": 100, "revoked_permit_roots": [], "predecessor_root": "0" * 64,
        **BOUNDARY,
    }, ISSUER, "revocation_registry_root")
    permit = signed({
        "schema": PERMIT_SCHEMA, "permit_id": "permit:recovery-demo:1",
        "issuer_public_key_hex": public(ISSUER),
        "subject_identity_root": root({"subject": "UNBOUND_DEMO"}),
        "session_root": root({"session": "SESSION_A"}),
        "jurisdiction_root": jurisdiction, "application_id": "UCM.DEMO",
        "action_id": "WRITE.DEMO.RESULT", "request_root": root({"request": 1}),
        "executor_public_key_hex": public(EXECUTOR),
        "allowed_effect_classes": ["WRITE_WORKSPACE"],
        "budget": {"max_cases": 1, "max_duration_ms": 1000,
                   "max_output_bytes": 1024},
        "rollback_root": root({"rollback": "DEMO_ONLY"}), "generation": 1,
        "nonce": root({"nonce": 1}), "issued_at": 90, "not_before": 95,
        "expires_at": 200, "revocation_registry_root": revocation["revocation_registry_root"],
        **BOUNDARY,
    }, ISSUER, "permit_root")
    contract = build_operation_contract(
        operation_id="operation:recovery-demo:1", permit=permit,
        revocation_registry=revocation,
        expected_issuer_public_key_hex=public(ISSUER),
        expected_jurisdiction_root=jurisdiction,
        expected_revocation_registry_root=revocation["revocation_registry_root"],
        requested_effect_classes=["WRITE_WORKSPACE"],
        idempotency_key=root({"idempotency": "recovery-demo:1"}),
        expected_result_root=root({"result": "DEMO_COMPLETE"}), now=100)
    return revocation, contract


def dispatch(prepared: dict, contract: dict) -> dict:
    return signed({
        "schema": DISPATCH_SCHEMA, "operation_id": contract["operation_id"],
        "contract_root": contract["contract_root"],
        "g1_root": prepared["g1"]["receipt_root"],
        "dispatch_authorization_root": prepared["dispatch_authorization"]["receipt_root"],
        "idempotency_key": contract["idempotency_key"],
        "dispatch_nonce": prepared["dispatch_authorization"]["dispatch_nonce"],
        "started_at": 101, "status": "DISPATCHED", **BOUNDARY,
    }, EXECUTOR, "receipt_root")


def terminal(dispatched: dict, contract: dict) -> dict:
    return signed({
        "schema": TERMINAL_SCHEMA, "operation_id": contract["operation_id"],
        "contract_root": contract["contract_root"],
        "dispatch_root": dispatched["dispatch_receipt"]["receipt_root"],
        "terminal_status": "COMPLETED", "result_root": contract["expected_result_root"],
        "output_bytes": 64, "completed_cases": 1,
        "observed_effect_classes": ["WRITE_WORKSPACE"], "ended_at": 102,
        "receipt_nonce": root({"receipt": 102}), **BOUNDARY,
    }, EXECUTOR, "receipt_root")


def run(output: Path) -> dict:
    temporary = Path(tempfile.mkdtemp(prefix="ucm-recovery-demo-"))
    try:
        workspace = temporary / "portable-workspace"
        revocation, contract = build_fixture()
        session_a = OperationGateway(workspace)
        prepared = session_a.prepare(
            contract, expected_issuer_public_key_hex=public(ISSUER),
            expected_jurisdiction_root=contract["jurisdiction_root"],
            expected_revocation_registry_root=revocation["revocation_registry_root"])
        dispatched = session_a.record_dispatch(contract["operation_id"],
                                                dispatch(prepared, contract))
        uncertain = session_a.mark_uncertain(contract["operation_id"],
                                             reason_code="SESSION_INTERRUPTED")
        before_count = len(session_a.journal.verify())

        # Session B opens the same portable custody and reconciles the signed
        # terminal receipt. No prepare or dispatch method is called again.
        session_b = OperationGateway(workspace)
        recovered = session_b.reconcile(contract["operation_id"],
                                        terminal(dispatched, contract))
        after_count = len(session_b.journal.verify())
        archive = build_operation_archive(
            session_b, operation_id=contract["operation_id"],
            expected_issuer_public_key_hex=public(ISSUER),
            expected_jurisdiction_root=contract["jurisdiction_root"],
            expected_revocation_registry_root=revocation["revocation_registry_root"])
        verified = verify_operation_archive(
            archive, expected_issuer_public_key_hex=public(ISSUER),
            expected_jurisdiction_root=contract["jurisdiction_root"],
            expected_revocation_registry_root=revocation["revocation_registry_root"])
        body = {
            "schema": "mosaic.ucm.recovery-demo-result.v0.1",
            "operation_id": contract["operation_id"],
            "contract_root": contract["contract_root"],
            "uncertain_state_root": uncertain["state"]["state_root"],
            "final_state_root": recovered["state"]["state_root"],
            "events_before_recovery": before_count,
            "events_after_recovery": after_count,
            "redispatch_performed": False,
            "portable_archive_sha256": __import__("hashlib").sha256(archive).hexdigest(),
            "portable_archive_status": verified["status"],
            "status": "PASS_RECOVERED_WITHOUT_REDISPATCH",
            **BOUNDARY,
        }
        result = {**body, "result_root": root(body)}
        output.mkdir(parents=True, exist_ok=True)
        if any(output.iterdir()):
            raise SystemExit("UCM_RECOVERY_DEMO_OUTPUT_NOT_EMPTY")
        (output / "RECOVERY-DEMO-RESULT.json").write_bytes(canonical_bytes(result) + b"\n")
        (output / "OPERATION-ARCHIVE.zip").write_bytes(archive)
        return result
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(canonical_bytes(run(args.output.resolve())).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

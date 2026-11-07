from __future__ import annotations

from copy import deepcopy
import tempfile
from pathlib import Path
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from uclop.canonical import canonical_bytes, root
from ucm.amcas import BOUNDARY
from ucm.operation_gateway import (
    DISPATCH_SCHEMA,
    PERMIT_SCHEMA,
    REVOCATION_SCHEMA,
    TERMINAL_SCHEMA,
    OperationGateway,
    build_operation_contract,
)
from ucm.operation_proofs import build_operation_proof_bundle
from ucm.pippi import (
    build_attested_pippi_context,
    build_pippi_context,
    effective_integration_mode,
    validate_pippi_context,
)
from ucm.pippi_global import PippiHub, build_onboarding
from ucm.pippi_host import (
    CHANNELS,
    HOST_ATTESTATION_SCHEMA,
    LAUNCH_RESULT_SCHEMA,
    build_host_adapter_policy,
    build_host_launch_proposal,
    build_host_mediation_attestation,
    validate_host_launch_result,
)
from ucm.pippi_integrations import (
    INTEGRATION_IDS,
    bind_external_integration,
    default_integration_availability_registry,
    validate_integration_availability_registry,
)
from ucm.system import capability_registry


ATTESTOR = Ed25519PrivateKey.from_private_bytes(b"\x31" * 32)
ISSUER = Ed25519PrivateKey.from_private_bytes(b"\x32" * 32)
EXECUTOR = Ed25519PrivateKey.from_private_bytes(b"\x33" * 32)


def public(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def signed(body: dict, key: Ed25519PrivateKey, root_field: str) -> dict:
    signature = key.sign(canonical_bytes(body)).hex()
    return {**body, "signature_hex": signature,
            root_field: root({**body, "signature_hex": signature})}


def host_fixture() -> tuple[dict, dict, str, str]:
    session_root = root({"session": "pippi-host-test"})
    subject_root = root({"project": "pippi-host-test"})
    policy = build_host_adapter_policy(
        policy_id="PIPPI.HOST.TEST",
        adapter_registry_root=root({"adapters": ["FIXTURE"]}),
        attestor_public_key_hex=public(ATTESTOR),
        operation_issuer_public_key_hex=public(ISSUER),
        operation_jurisdiction_root=root({"jurisdiction": "PIPPI.TEST"}),
        operation_revocation_registry_root=root({"placeholder": "replaced below"}),
        maximum_validity_ns=1_000,
    )
    # The operation revocation root is a trust anchor in the host policy. Build
    # it first, then rebuild the policy with that exact immutable root.
    revocation_body = {
        "schema": REVOCATION_SCHEMA,
        "issuer_public_key_hex": public(ISSUER),
        "jurisdiction_root": policy["operation_jurisdiction_root"],
        "generation": 1, "sequence": 1, "valid_at": 100,
        "revoked_permit_roots": [], "predecessor_root": "0" * 64,
        **BOUNDARY,
    }
    revocation = signed(revocation_body, ISSUER, "revocation_registry_root")
    policy = build_host_adapter_policy(
        policy_id="PIPPI.HOST.TEST",
        adapter_registry_root=policy["adapter_registry_root"],
        attestor_public_key_hex=public(ATTESTOR),
        operation_issuer_public_key_hex=public(ISSUER),
        operation_jurisdiction_root=policy["operation_jurisdiction_root"],
        operation_revocation_registry_root=revocation["revocation_registry_root"],
        maximum_validity_ns=1_000,
    )
    unsigned = {
        "schema": HOST_ATTESTATION_SCHEMA,
        "host_policy_root": policy["host_policy_root"],
        "adapter_id": "FIXTURE.ADAPTER",
        "adapter_source_root": root({"source": "fixture-adapter"}),
        "adapter_registry_root": policy["adapter_registry_root"],
        "session_root": session_root,
        "subject_root": subject_root,
        "mediated_channels": sorted(CHANNELS),
        "issued_at_ns": 100,
        "expires_at_ns": 200,
        "attestor_public_key_hex": public(ATTESTOR),
        "attestation_grants_authority": False,
        **BOUNDARY,
    }
    attestation = build_host_mediation_attestation(
        policy=policy,
        adapter_id=unsigned["adapter_id"],
        adapter_source_root=unsigned["adapter_source_root"],
        session_root=session_root,
        subject_root=subject_root,
        mediated_channels=unsigned["mediated_channels"],
        issued_at_ns=unsigned["issued_at_ns"],
        expires_at_ns=unsigned["expires_at_ns"],
        signature_hex=ATTESTOR.sign(canonical_bytes(unsigned)).hex(),
    )
    return policy, attestation, session_root, subject_root


def operation_result(policy: dict, attestation: dict, proposal: dict) -> dict:
    revocation_body = {
        "schema": REVOCATION_SCHEMA,
        "issuer_public_key_hex": public(ISSUER),
        "jurisdiction_root": policy["operation_jurisdiction_root"],
        "generation": 1, "sequence": 1, "valid_at": 100,
        "revoked_permit_roots": [], "predecessor_root": "0" * 64,
        **BOUNDARY,
    }
    revocation = signed(revocation_body, ISSUER, "revocation_registry_root")
    projection = {"status": "LAUNCHED", "kind": proposal["kind"]}
    projection_root = root(projection)
    permit_body = {
        "schema": PERMIT_SCHEMA,
        "permit_id": "permit:pippi-host-test",
        "issuer_public_key_hex": public(ISSUER),
        "subject_identity_root": proposal["project_root"],
        "session_root": proposal["session_root"],
        "jurisdiction_root": policy["operation_jurisdiction_root"],
        "application_id": "PIPPI.DASHBOARD",
        "action_id": f"HOST.{proposal['kind']}",
        "request_root": proposal["proposal_root"],
        "executor_public_key_hex": public(EXECUTOR),
        "allowed_effect_classes": proposal["requested_effect_classes"],
        "budget": {"max_cases": 1, "max_duration_ms": 10_000,
                   "max_output_bytes": 65_536},
        "rollback_root": root({"rollback": "fixture"}),
        "generation": 1, "nonce": root({"nonce": proposal["proposal_root"]}),
        "issued_at": 90, "not_before": 95, "expires_at": 200,
        "revocation_registry_root": revocation["revocation_registry_root"],
        **BOUNDARY,
    }
    permit = signed(permit_body, ISSUER, "permit_root")
    operation_id = "op:pippi-host-test"
    contract = build_operation_contract(
        operation_id=operation_id, permit=permit,
        revocation_registry=revocation,
        expected_issuer_public_key_hex=public(ISSUER),
        expected_jurisdiction_root=policy["operation_jurisdiction_root"],
        expected_revocation_registry_root=revocation["revocation_registry_root"],
        requested_effect_classes=proposal["requested_effect_classes"],
        idempotency_key=root({"proposal": proposal["proposal_root"]}),
        expected_result_root=projection_root, now=100,
    )
    with tempfile.TemporaryDirectory() as raw:
        gateway = OperationGateway(Path(raw))
        prepared = gateway.prepare(
            contract,
            expected_issuer_public_key_hex=public(ISSUER),
            expected_jurisdiction_root=policy["operation_jurisdiction_root"],
            expected_revocation_registry_root=revocation["revocation_registry_root"],
        )
        dispatch_body = {
            "schema": DISPATCH_SCHEMA, "operation_id": operation_id,
            "contract_root": contract["contract_root"],
            "g1_root": prepared["g1"]["receipt_root"],
            "dispatch_authorization_root": prepared["dispatch_authorization"]["receipt_root"],
            "idempotency_key": contract["idempotency_key"],
            "dispatch_nonce": prepared["dispatch_authorization"]["dispatch_nonce"],
            "started_at": 101, "status": "DISPATCHED", **BOUNDARY,
        }
        dispatched = gateway.record_dispatch(
            operation_id, signed(dispatch_body, EXECUTOR, "receipt_root"))
        terminal_body = {
            "schema": TERMINAL_SCHEMA, "operation_id": operation_id,
            "contract_root": contract["contract_root"],
            "dispatch_root": dispatched["dispatch_receipt"]["receipt_root"],
            "terminal_status": "COMPLETED", "result_root": projection_root,
            "output_bytes": 1, "completed_cases": 1,
            "observed_effect_classes": proposal["requested_effect_classes"],
            "ended_at": 102, "receipt_nonce": root({"receipt": 102}), **BOUNDARY,
        }
        gateway.record_terminal(
            operation_id, signed(terminal_body, EXECUTOR, "receipt_root"))
        events = gateway.journal.verify()
        proof = build_operation_proof_bundle(
            operation_id=operation_id, events=events,
            expected_issuer_public_key_hex=public(ISSUER),
            expected_jurisdiction_root=policy["operation_jurisdiction_root"],
            expected_revocation_registry_root=revocation["revocation_registry_root"],
        )
    body = {
        "schema": LAUNCH_RESULT_SCHEMA,
        "proposal_root": proposal["proposal_root"],
        "host_attestation_root": attestation["host_attestation_root"],
        "operation_id": operation_id, "events": events, "proof_bundle": proof,
        "result_projection": projection, "result_projection_root": projection_root,
        "status": "PASS", **BOUNDARY,
    }
    return {**body, "launch_result_root": root(body)}


class PippiHostBoundaryTests(unittest.TestCase):
    def test_channel_declaration_alone_never_establishes_enforced_host(self):
        context = build_pippi_context(
            session_root=root({"session": 1}), subject_root=root({"subject": 1}),
            policy_roots=[], capability_registry_root=root({"registry": 1}),
            profile_root=root({"profile": 1}), jurisdiction_root=root({"jurisdiction": 1}),
            retained_context_roots=[], mediated_channels=sorted(CHANNELS),
        )
        self.assertEqual(context["integration_mode"], "SIDECAR_PARTIAL")
        self.assertEqual(effective_integration_mode(context), "SIDECAR_PARTIAL")

    def test_signed_attestation_is_required_for_enforced_host(self):
        policy, attestation, session_root, subject_root = host_fixture()
        context = build_attested_pippi_context(
            session_root=session_root, subject_root=subject_root,
            policy_roots=[policy["host_policy_root"]],
            capability_registry_root=root({"registry": 1}),
            profile_root=root({"profile": 1}),
            jurisdiction_root=root({"jurisdiction": 1}),
            retained_context_roots=[],
            expected_host_policy_root=policy["host_policy_root"], host_policy=policy,
            host_attestation=attestation, now_ns=150,
        )
        self.assertEqual(validate_pippi_context(context), context)
        self.assertEqual(effective_integration_mode(context), "SIDECAR_PARTIAL")
        self.assertEqual(effective_integration_mode(
            context, expected_host_policy_root=policy["host_policy_root"]),
            "ENFORCED_HOST")
        with self.assertRaisesRegex(ValueError, "PIPPI_HOST_POLICY_ANCHOR_MISMATCH"):
            build_attested_pippi_context(
                session_root=session_root, subject_root=subject_root,
                policy_roots=[policy["host_policy_root"]],
                capability_registry_root=root({"registry": 1}),
                profile_root=root({"profile": 1}),
                jurisdiction_root=root({"jurisdiction": 1}),
                retained_context_roots=[], expected_host_policy_root="0" * 64,
                host_policy=policy, host_attestation=attestation, now_ns=150)
        expired = deepcopy(context)
        expired["attestation_checked_at_ns"] = 250
        body = {key: value for key, value in expired.items() if key != "context_root"}
        expired["context_root"] = root(body)
        with self.assertRaisesRegex(ValueError, "PIPPI_HOST_ATTESTATION_BINDING_INVALID"):
            validate_pippi_context(expired)

    def test_host_launch_requires_complete_operational_proof(self):
        policy, attestation, session_root, subject_root = host_fixture()
        proposal = build_host_launch_proposal(
            project_root=subject_root, session_root=session_root,
            host_policy_root=policy["host_policy_root"],
            host_attestation_root=attestation["host_attestation_root"],
            kind="APPLICATION", payload={"command": ["sample.exe"]},
            expected_hub_head="0" * 64,
        )
        result = operation_result(policy, attestation, proposal)
        self.assertEqual(validate_host_launch_result(
            result, proposal=proposal, policy=policy,
            attestation=attestation, now_ns=150), result)
        changed = deepcopy(result)
        changed["result_projection"] = {"status": "LAUNCHED", "kind": "VERIFICATION"}
        body = {key: value for key, value in changed.items() if key != "launch_result_root"}
        changed["launch_result_root"] = root(body)
        with self.assertRaisesRegex(ValueError, "PIPPI_LAUNCH_RESULT_ROOT_INVALID"):
            validate_host_launch_result(changed, proposal=proposal, policy=policy,
                                        attestation=attestation, now_ns=150)

    def test_integration_registry_distinguishes_declared_from_bound(self):
        registry = default_integration_availability_registry()
        self.assertEqual(validate_integration_availability_registry(registry), registry)
        self.assertEqual({row["integration_id"] for row in registry["entries"]},
                         INTEGRATION_IDS)
        gateway = next(row for row in registry["entries"]
                       if row["integration_id"] == "UCM_OPERATIONAL_GATEWAY")
        self.assertEqual(gateway["status"], "DECLARED_UNBOUND")
        bound = bind_external_integration(
            registry=registry, integration_id="UCM_OPERATIONAL_GATEWAY",
            binding_root=root({"host-policy": 1}), evidence_roots=[root({"evidence": 1})],
        )
        gateway = next(row for row in bound["entries"]
                       if row["integration_id"] == "UCM_OPERATIONAL_GATEWAY")
        self.assertEqual(gateway["status"], "BOUND_EXTERNAL")

    def test_new_host_surfaces_are_active_and_hub_defaults_fail_closed(self):
        names = {row["name"] for row in capability_registry()["surfaces"]}
        self.assertTrue({
            "BUILD_PIPPI_HOST_ADAPTER_POLICY",
            "BUILD_ATTESTED_PIPPI_CONTEXT",
            "BUILD_PIPPI_HOST_LAUNCH_PROPOSAL",
            "VALIDATE_PIPPI_HOST_LAUNCH_RESULT",
            "BUILD_PIPPI_INTEGRATION_REGISTRY",
            "BIND_PIPPI_EXTERNAL_INTEGRATION",
        } <= names)
        with tempfile.TemporaryDirectory() as raw:
            hub = PippiHub(Path(raw))
            hub.initialize(build_onboarding(
                governor_label="fixture", mosaic_id=None, dkn_public_key=None,
                github_account=None, github_credential_reference=None))
            self.assertEqual(hub.integration("UCM_OPERATIONAL_GATEWAY")["status"],
                             "DECLARED_UNBOUND")


if __name__ == "__main__":
    unittest.main()

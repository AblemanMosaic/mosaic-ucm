"""Evidence-bound host mediation and dashboard launch envelopes.

This module never launches a process.  It verifies that a host adapter was
named by a pinned policy and that a completed launch is backed by the existing
UCM operational-gateway history and proof bundle.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Protocol

from uclop.canonical import canonical_bytes, exact_keys, require, require_root, root

from .amcas import BOUNDARY


HOST_POLICY_SCHEMA = "mosaic.ucm.pippi-host-adapter-policy.v0.1"
HOST_ATTESTATION_SCHEMA = "mosaic.ucm.pippi-host-mediation-attestation.v0.1"
LAUNCH_PROPOSAL_SCHEMA = "mosaic.ucm.pippi-host-launch-proposal.v0.1"
LAUNCH_RESULT_SCHEMA = "mosaic.ucm.pippi-host-launch-result.v0.1"
CHANNELS = {"MODEL_INPUT", "MODEL_DRAFT", "VISIBLE_OUTPUT", "TOOL_PROPOSAL",
            "TOOL_DISPATCH", "TOOL_RESULT", "JOURNAL_WRITE"}
LAUNCH_EFFECTS = {
    "APPLICATION": ["PROCESS"],
    "VERIFICATION": ["PROCESS", "READ_STATE"],
    "GITHUB": ["NETWORK", "PROCESS"],
    "FILE_TREE": ["PROCESS", "READ_STATE"],
    "README": ["PROCESS", "READ_STATE"],
    "DOCUMENT": ["PROCESS", "READ_STATE"],
    "REVIEW_LOCAL": ["PROCESS", "READ_STATE", "WRITE_WORKSPACE"],
}


def _identifier(value: Any, code: str) -> str:
    require(type(value) is str and value == value.strip() and 0 < len(value) <= 192
            and all(ch.isalnum() or ch in "._:-/@+" for ch in value), code)
    return value


def _public_key(value: Any, code: str) -> str:
    require(type(value) is str and len(value) == 64, code)
    try:
        bytes.fromhex(value)
    except ValueError:
        require(False, code)
    return value


def _signature(value: Any, code: str) -> str:
    require(type(value) is str and len(value) == 128, code)
    try:
        bytes.fromhex(value)
    except ValueError:
        require(False, code)
    return value


def _verify(public_key_hex: str, signature_hex: str, message: bytes, code: str) -> None:
    _public_key(public_key_hex, code); _signature(signature_hex, code)
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as error:
        raise ValueError("PIPPI_HOST_DEPENDENCY_MISSING_CRYPTOGRAPHY") from error
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex)).verify(
            bytes.fromhex(signature_hex), message)
    except InvalidSignature:
        require(False, code)


def build_host_adapter_policy(*, policy_id: str, adapter_registry_root: str,
                              attestor_public_key_hex: str,
                              operation_issuer_public_key_hex: str,
                              operation_jurisdiction_root: str,
                              operation_revocation_registry_root: str,
                              maximum_validity_ns: int) -> dict[str, Any]:
    _identifier(policy_id, "PIPPI_HOST_POLICY_ID_INVALID")
    for value in (adapter_registry_root, operation_jurisdiction_root,
                  operation_revocation_registry_root):
        require_root(value)
    _public_key(attestor_public_key_hex, "PIPPI_HOST_ATTESTOR_KEY_INVALID")
    _public_key(operation_issuer_public_key_hex, "PIPPI_HOST_OPERATION_ISSUER_INVALID")
    require(type(maximum_validity_ns) is int and maximum_validity_ns > 0,
            "PIPPI_HOST_VALIDITY_INVALID")
    body = {"schema": HOST_POLICY_SCHEMA, "policy_id": policy_id,
            "adapter_registry_root": adapter_registry_root,
            "attestor_public_key_hex": attestor_public_key_hex,
            "operation_issuer_public_key_hex": operation_issuer_public_key_hex,
            "operation_jurisdiction_root": operation_jurisdiction_root,
            "operation_revocation_registry_root": operation_revocation_registry_root,
            "required_channels": sorted(CHANNELS),
            "maximum_validity_ns": maximum_validity_ns,
            "policy_grants_authority": False, **BOUNDARY}
    return {**body, "host_policy_root": root(body)}


def validate_host_adapter_policy(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "policy_id", "adapter_registry_root",
        "attestor_public_key_hex", "operation_issuer_public_key_hex",
        "operation_jurisdiction_root", "operation_revocation_registry_root",
        "required_channels", "maximum_validity_ns", "policy_grants_authority",
        "standing", "authority_effect", "real_a5", "g0", "host_policy_root"})
    expected = build_host_adapter_policy(policy_id=item["policy_id"],
        adapter_registry_root=item["adapter_registry_root"],
        attestor_public_key_hex=item["attestor_public_key_hex"],
        operation_issuer_public_key_hex=item["operation_issuer_public_key_hex"],
        operation_jurisdiction_root=item["operation_jurisdiction_root"],
        operation_revocation_registry_root=item["operation_revocation_registry_root"],
        maximum_validity_ns=item["maximum_validity_ns"])
    require(item == expected, "PIPPI_HOST_POLICY_INVALID")
    return deepcopy(item)


def build_host_mediation_attestation(*, policy: dict[str, Any], adapter_id: str,
                                     adapter_source_root: str, session_root: str,
                                     subject_root: str, mediated_channels: list[str],
                                     issued_at_ns: int, expires_at_ns: int,
                                     signature_hex: str) -> dict[str, Any]:
    policy = validate_host_adapter_policy(policy)
    _identifier(adapter_id, "PIPPI_HOST_ADAPTER_ID_INVALID")
    for value in (adapter_source_root, session_root, subject_root): require_root(value)
    require(mediated_channels == sorted(CHANNELS), "PIPPI_HOST_CHANNELS_INCOMPLETE")
    require(type(issued_at_ns) is int and type(expires_at_ns) is int
            and 0 <= issued_at_ns < expires_at_ns
            and expires_at_ns - issued_at_ns <= policy["maximum_validity_ns"],
            "PIPPI_HOST_VALIDITY_INVALID")
    unsigned = {"schema": HOST_ATTESTATION_SCHEMA,
        "host_policy_root": policy["host_policy_root"], "adapter_id": adapter_id,
        "adapter_source_root": adapter_source_root,
        "adapter_registry_root": policy["adapter_registry_root"],
        "session_root": session_root, "subject_root": subject_root,
        "mediated_channels": list(mediated_channels),
        "issued_at_ns": issued_at_ns, "expires_at_ns": expires_at_ns,
        "attestor_public_key_hex": policy["attestor_public_key_hex"],
        "attestation_grants_authority": False, **BOUNDARY}
    _verify(policy["attestor_public_key_hex"], signature_hex,
            canonical_bytes(unsigned), "PIPPI_HOST_ATTESTATION_SIGNATURE_INVALID")
    signed = {**unsigned, "signature_hex": signature_hex}
    return {**signed, "host_attestation_root": root(signed)}


def validate_host_mediation_attestation(value: Any, *, policy: dict[str, Any],
                                        expected_session_root: str,
                                        expected_subject_root: str,
                                        now_ns: int) -> dict[str, Any]:
    policy = validate_host_adapter_policy(policy)
    item = exact_keys(value, {"schema", "host_policy_root", "adapter_id",
        "adapter_source_root", "adapter_registry_root", "session_root",
        "subject_root", "mediated_channels", "issued_at_ns", "expires_at_ns",
        "attestor_public_key_hex", "attestation_grants_authority", "standing",
        "authority_effect", "real_a5", "g0", "signature_hex",
        "host_attestation_root"})
    require(item["schema"] == HOST_ATTESTATION_SCHEMA
            and item["host_policy_root"] == policy["host_policy_root"]
            and item["adapter_registry_root"] == policy["adapter_registry_root"]
            and item["attestor_public_key_hex"] == policy["attestor_public_key_hex"]
            and item["session_root"] == require_root(expected_session_root)
            and item["subject_root"] == require_root(expected_subject_root)
            and type(now_ns) is int and item["issued_at_ns"] <= now_ns < item["expires_at_ns"],
            "PIPPI_HOST_ATTESTATION_BINDING_INVALID")
    expected = build_host_mediation_attestation(policy=policy,
        adapter_id=item["adapter_id"], adapter_source_root=item["adapter_source_root"],
        session_root=item["session_root"], subject_root=item["subject_root"],
        mediated_channels=item["mediated_channels"], issued_at_ns=item["issued_at_ns"],
        expires_at_ns=item["expires_at_ns"], signature_hex=item["signature_hex"])
    require(item == expected, "PIPPI_HOST_ATTESTATION_INVALID")
    return deepcopy(item)


def build_host_launch_proposal(*, project_root: str, session_root: str,
                               host_policy_root: str, host_attestation_root: str,
                               kind: str, payload: dict[str, Any],
                               expected_hub_head: str) -> dict[str, Any]:
    for value in (project_root, session_root, host_policy_root,
                  host_attestation_root, expected_hub_head): require_root(value)
    require(kind in LAUNCH_EFFECTS, "PIPPI_LAUNCH_KIND_INVALID")
    require(type(payload) is dict, "PIPPI_LAUNCH_PAYLOAD_INVALID")
    body = {"schema": LAUNCH_PROPOSAL_SCHEMA, "project_root": project_root,
            "session_root": session_root, "host_policy_root": host_policy_root,
            "host_attestation_root": host_attestation_root, "kind": kind,
            "payload": deepcopy(payload),
            "requested_effect_classes": LAUNCH_EFFECTS[kind],
            "expected_hub_head": expected_hub_head,
            "dispatch_authorized": False, **BOUNDARY}
    return {**body, "proposal_root": root(body)}


def validate_host_launch_proposal(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "project_root", "session_root",
        "host_policy_root", "host_attestation_root", "kind", "payload",
        "requested_effect_classes", "expected_hub_head", "dispatch_authorized",
        "standing", "authority_effect", "real_a5", "g0", "proposal_root"})
    expected = build_host_launch_proposal(project_root=item["project_root"],
        session_root=item["session_root"], host_policy_root=item["host_policy_root"],
        host_attestation_root=item["host_attestation_root"], kind=item["kind"],
        payload=item["payload"], expected_hub_head=item["expected_hub_head"])
    require(item == expected, "PIPPI_LAUNCH_PROPOSAL_INVALID")
    return deepcopy(item)


def validate_host_launch_result(value: Any, *, proposal: dict[str, Any],
                                policy: dict[str, Any], attestation: dict[str, Any],
                                now_ns: int) -> dict[str, Any]:
    """Re-derive a launch result from the existing operational history."""
    proposal = validate_host_launch_proposal(proposal)
    policy = validate_host_adapter_policy(policy)
    attestation = validate_host_mediation_attestation(attestation, policy=policy,
        expected_session_root=proposal["session_root"],
        expected_subject_root=proposal["project_root"], now_ns=now_ns)
    item = exact_keys(value, {"schema", "proposal_root", "host_attestation_root",
        "operation_id", "events", "proof_bundle", "result_projection",
        "result_projection_root",
        "status", "standing", "authority_effect", "real_a5", "g0", "launch_result_root"})
    require(item["schema"] == LAUNCH_RESULT_SCHEMA
            and item["proposal_root"] == proposal["proposal_root"]
            and item["host_attestation_root"] == attestation["host_attestation_root"]
            and item["status"] == "PASS", "PIPPI_LAUNCH_RESULT_BINDING_INVALID")
    from .operation_gateway import validate_operation_history
    from .operation_proofs import verify_operation_proof_bundle
    checked = validate_operation_history(operation_id=item["operation_id"],
        events=item["events"],
        expected_issuer_public_key_hex=policy["operation_issuer_public_key_hex"],
        expected_jurisdiction_root=policy["operation_jurisdiction_root"],
        expected_revocation_registry_root=policy["operation_revocation_registry_root"])
    proof = verify_operation_proof_bundle(item["proof_bundle"], events=item["events"],
        expected_issuer_public_key_hex=policy["operation_issuer_public_key_hex"],
        expected_jurisdiction_root=policy["operation_jurisdiction_root"],
        expected_revocation_registry_root=policy["operation_revocation_registry_root"])
    contract, state = checked["contract"], checked["state"]
    require(proof["status"] == "PASS" and state["state"] == "COMPLETED"
            and contract["request_root"] == proposal["proposal_root"]
            and contract["subject_identity_root"] == proposal["project_root"]
            and contract["session_root"] == proposal["session_root"]
            and contract["requested_effect_classes"] == proposal["requested_effect_classes"],
            "PIPPI_LAUNCH_OPERATION_INVALID")
    terminal = [row for row in item["events"] if row.get("event_type")
                in {"OPERATION_TERMINAL_RECORDED", "OPERATION_RECONCILED"}]
    require(type(item["result_projection"]) is dict
            and item["result_projection_root"] == root(item["result_projection"])
            and len(terminal) == 1
            and item["result_projection_root"] == terminal[0]["payload"]["terminal_receipt"]["result_root"],
            "PIPPI_LAUNCH_RESULT_ROOT_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "launch_result_root"}
    require(item["launch_result_root"] == root(body), "PIPPI_LAUNCH_RESULT_INVALID")
    return deepcopy(item)


class HostLaunchAdapter(Protocol):
    def binding(self) -> tuple[dict[str, Any], dict[str, Any], int]: ...
    def dispatch(self, proposal: dict[str, Any], progress: Any = None) -> dict[str, Any]: ...


class RefusingHostLaunchAdapter:
    def binding(self) -> tuple[dict[str, Any], dict[str, Any], int]:
        raise ValueError("PIPPI_HOST_ADAPTER_UNBOUND")

    def dispatch(self, proposal: dict[str, Any], progress: Any = None) -> dict[str, Any]:
        raise ValueError("PIPPI_HOST_ADAPTER_UNBOUND")

from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclsh.evidence import key_root, signed, verify_signed
from uclsh.errors import UCLSHRefusal

from .canonical import Refusal, exact_keys, require, require_root, root


ROLES = ("H_M", "H_J", "RECOVERY", "GOVERNOR")
CONSTITUTION_DOMAIN = "UCL_UCM_OPERATIONAL_CONSTITUTION_V1"
A5_DOMAIN = "UCL_UCM_A5_PROPOSAL_V1"
PAIR_DOMAIN = "UCL_UCM_OPERATIONAL_PAIR_V1"
STANDING_DOMAIN = "UCL_UCM_STANDING_PROPOSAL_V1"
LIFECYCLE_DOMAIN = "UCL_UCM_OPERATIONAL_LIFECYCLE_V1"


def _verify_signed(record: Any, domain: str, key: str) -> Any:
    try:
        return verify_signed(record, domain, key)
    except UCLSHRefusal as error:
        raise Refusal(error.code, error.path, error.detail) from error


def _verified_role_keys(
    constitution: Any,
    keys: dict[str, str],
    expected_root: str,
) -> dict[str, str]:
    """Verify the constitution and return its exact role-to-key-root binding."""
    body = verify_constitution(constitution, keys, expected_root)
    descriptors = {item["role"]: item["public_key_root"] for item in body["keys"]}
    require(set(descriptors) == set(ROLES), "CONSTITUTION_KEYS_INVALID")
    require(len(set(descriptors.values())) == len(ROLES), "OPERATIONAL_KEYS_NOT_INDEPENDENT")
    return descriptors


def key_descriptor(role: str, key_hex: str, custody_ref: str) -> dict[str, Any]:
    require(role in ROLES, "OPERATIONAL_ROLE_INVALID")
    require(type(custody_ref) is str and custody_ref, "CUSTODY_REF_INVALID")
    return {
        "schema": "ucl.ucm.operational_key_descriptor.v1",
        "role": role,
        "algorithm": "FIXTURE_HMAC_SHA256_REPLACEABLE_BY_ED25519_ADAPTER",
        "public_key_root": key_root(key_hex),
        "custody_ref": custody_ref,
        "private_material_embedded": False,
        "standing": "INFORMATION_ONLY",
    }


def make_constitution(
    keys: dict[str, str],
    custody_refs: dict[str, str],
    *,
    decision_root: str,
    predecessor_root: str,
) -> dict[str, Any]:
    require(set(keys) == set(ROLES) and set(custody_refs) == set(ROLES), "OPERATIONAL_ROLE_SET_INVALID")
    descriptors = [key_descriptor(role, keys[role], custody_refs[role]) for role in ROLES]
    roots = [item["public_key_root"] for item in descriptors]
    require(len(set(roots)) == len(roots), "OPERATIONAL_KEYS_NOT_INDEPENDENT")
    body = {
        "schema": "ucl.ucm.operational_constitution.v1",
        "decision_root": require_root(decision_root),
        "predecessor_root": require_root(predecessor_root),
        "keys": descriptors,
        "sequence": 0,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
        "real_a5": False,
        "g0": "CLOSED",
    }
    approvals = {
        role: signed(f"{CONSTITUTION_DOMAIN}:{role}", body, keys[role])
        for role in ROLES
    }
    record = {"body": body, "body_root": root(body), "approvals": approvals}
    return {**record, "constitution_root": root(record)}


def verify_constitution(record: Any, keys: dict[str, str], expected_root: str) -> dict[str, Any]:
    item = exact_keys(record, {"body", "body_root", "approvals", "constitution_root"}, "$.constitution")
    require(item["body_root"] == root(item["body"]), "CONSTITUTION_BODY_ROOT_MISMATCH")
    require(item["constitution_root"] == root({k: item[k] for k in ("body", "body_root", "approvals")}), "CONSTITUTION_ROOT_MISMATCH")
    require(item["constitution_root"] == require_root(expected_root), "CONSTITUTION_PIN_MISMATCH")
    require(set(keys) == set(ROLES) and set(item["approvals"]) == set(ROLES), "CONSTITUTION_APPROVAL_SET_INVALID")
    body = exact_keys(item["body"], {"schema", "decision_root", "predecessor_root", "keys", "sequence", "standing", "authority_effect", "real_a5", "g0"}, "$.constitution.body")
    require(body["schema"] == "ucl.ucm.operational_constitution.v1" and body["sequence"] == 0, "CONSTITUTION_BODY_INVALID")
    require_root(body["decision_root"], "$.constitution.body.decision_root")
    require_root(body["predecessor_root"], "$.constitution.body.predecessor_root")
    require(body.get("standing") == "INFORMATION_ONLY" and body.get("authority_effect") == "NONE", "CONSTITUTION_EFFECT_FORBIDDEN")
    require(body.get("real_a5") is False and body.get("g0") == "CLOSED", "CONSTITUTION_BOUNDARY_INVALID")
    descriptors = body.get("keys")
    require(type(descriptors) is list and len(descriptors) == len(ROLES), "CONSTITUTION_KEYS_INVALID")
    by_role = {entry.get("role"): entry for entry in descriptors if type(entry) is dict}
    require(set(by_role) == set(ROLES), "CONSTITUTION_KEYS_INVALID")
    require(len({entry["public_key_root"] for entry in descriptors}) == len(ROLES), "OPERATIONAL_KEYS_NOT_INDEPENDENT")
    for role in ROLES:
        exact_keys(by_role[role], {"schema", "role", "algorithm", "public_key_root", "custody_ref", "private_material_embedded", "standing"}, f"$.constitution.body.keys.{role}")
        require(by_role[role]["schema"] == "ucl.ucm.operational_key_descriptor.v1", "CONSTITUTION_KEY_DESCRIPTOR_INVALID")
        require(by_role[role]["private_material_embedded"] is False and by_role[role]["standing"] == "INFORMATION_ONLY", "CONSTITUTION_KEY_DESCRIPTOR_INVALID")
        require(by_role[role]["public_key_root"] == key_root(keys[role]), "CONSTITUTION_KEY_BINDING_MISMATCH")
        require(_verify_signed(item["approvals"][role], f"{CONSTITUTION_DOMAIN}:{role}", keys[role]) == body, "CONSTITUTION_APPROVAL_INVALID")
    return deepcopy(body)


def make_a5_proposal(
    *,
    constitution_root: str,
    host_identity_root: str,
    os_identity_root: str,
    principal_identity_root: str,
    executable_root: str,
    evidence_root: str,
    nonce: str,
    sequence: int,
    predecessor_root: str,
    recovery_key: str,
    governor_key: str,
) -> dict[str, Any]:
    require(type(nonce) is str and nonce, "A5_NONCE_INVALID")
    require(type(sequence) is int and type(sequence) is not bool and sequence > 0, "A5_SEQUENCE_INVALID")
    body = {
        "schema": "ucl.ucm.a5_binding_proposal.v1",
        "constitution_root": require_root(constitution_root),
        "host_identity_root": require_root(host_identity_root),
        "os_identity_root": require_root(os_identity_root),
        "principal_identity_root": require_root(principal_identity_root),
        "executable_root": require_root(executable_root),
        "evidence_root": require_root(evidence_root),
        "nonce": nonce,
        "sequence": sequence,
        "predecessor_root": require_root(predecessor_root),
        "proposal_only": True,
        "real_a5": False,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    approvals = {
        "RECOVERY": signed(f"{A5_DOMAIN}:RECOVERY", body, recovery_key),
        "GOVERNOR": signed(f"{A5_DOMAIN}:GOVERNOR", body, governor_key),
    }
    record = {"body": body, "body_root": root(body), "approvals": approvals}
    return {**record, "a5_proposal_root": root(record)}


def verify_a5_proposal(
    record: Any,
    *,
    constitution: Any,
    keys: dict[str, str],
    seen_nonces: set[str],
    expected_sequence: int,
    expected_predecessor: str,
    expected_constitution_root: str,
) -> dict[str, Any]:
    item = exact_keys(record, {"body", "body_root", "approvals", "a5_proposal_root"}, "$.a5")
    body = exact_keys(item["body"], {"schema", "constitution_root", "host_identity_root", "os_identity_root", "principal_identity_root", "executable_root", "evidence_root", "nonce", "sequence", "predecessor_root", "proposal_only", "real_a5", "standing", "authority_effect"}, "$.a5.body")
    require(body["schema"] == "ucl.ucm.a5_binding_proposal.v1", "A5_SCHEMA_INVALID")
    require(type(body["sequence"]) is int and type(body["sequence"]) is not bool and body["sequence"] > 0, "A5_SEQUENCE_INVALID")
    require(type(body["nonce"]) is str and body["nonce"], "A5_NONCE_INVALID")
    for key in ("constitution_root", "host_identity_root", "os_identity_root", "principal_identity_root", "executable_root", "evidence_root", "predecessor_root"):
        require_root(body[key], f"$.a5.body.{key}")
    require(item["body_root"] == root(body), "A5_BODY_ROOT_MISMATCH")
    require(item["a5_proposal_root"] == root({k: item[k] for k in ("body", "body_root", "approvals")}), "A5_PROPOSAL_ROOT_MISMATCH")
    constitution_root = constitution.get("constitution_root") if type(constitution) is dict else None
    expected_constitution_root = require_root(expected_constitution_root)
    require(constitution_root == expected_constitution_root, "CONSTITUTION_PIN_MISMATCH")
    descriptors = _verified_role_keys(constitution, keys, expected_constitution_root)
    require(body.get("constitution_root") == constitution_root, "A5_CONSTITUTION_MISMATCH")
    require(body.get("sequence") == expected_sequence and body.get("predecessor_root") == require_root(expected_predecessor), "A5_LINEAGE_MISMATCH")
    require(body.get("nonce") not in seen_nonces, "A5_NONCE_REPLAY")
    require(body.get("proposal_only") is True and body.get("real_a5") is False, "A5_EFFECT_FORBIDDEN")
    require(body.get("standing") == "INFORMATION_ONLY" and body.get("authority_effect") == "NONE", "A5_EFFECT_FORBIDDEN")
    require(set(item["approvals"]) == {"RECOVERY", "GOVERNOR"}, "A5_APPROVAL_SET_INVALID")
    recovery_key, governor_key = keys["RECOVERY"], keys["GOVERNOR"]
    require(key_root(recovery_key) == descriptors["RECOVERY"], "A5_RECOVERY_KEY_ROLE_MISMATCH")
    require(key_root(governor_key) == descriptors["GOVERNOR"], "A5_GOVERNOR_KEY_ROLE_MISMATCH")
    require(descriptors["RECOVERY"] != descriptors["GOVERNOR"], "A5_APPROVAL_ROLES_NOT_DISTINCT")
    require(_verify_signed(item["approvals"]["RECOVERY"], f"{A5_DOMAIN}:RECOVERY", recovery_key) == body, "A5_RECOVERY_APPROVAL_INVALID")
    require(_verify_signed(item["approvals"]["GOVERNOR"], f"{A5_DOMAIN}:GOVERNOR", governor_key) == body, "A5_GOVERNOR_APPROVAL_INVALID")
    seen_nonces.add(body["nonce"])
    return {"status": "VERIFIED_PROPOSAL_ONLY", "a5_proposal_root": item["a5_proposal_root"], "real_a5": False, "standing": "INFORMATION_ONLY"}


def make_pair_attestation(*, constitution_root: str, hm_commitment_root: str, hj_commitment_root: str, hm_epoch: int, hj_epoch: int, decision_root: str, hm_key: str, hj_key: str) -> dict[str, Any]:
    require(type(hm_epoch) is int and type(hm_epoch) is not bool and hm_epoch > 0, "PAIR_EPOCH_INVALID")
    require(type(hj_epoch) is int and type(hj_epoch) is not bool and hj_epoch > 0, "PAIR_EPOCH_INVALID")
    body = {
        "schema": "ucl.ucm.operational_exact_pair.v1",
        "constitution_root": require_root(constitution_root),
        "hm_commitment_root": require_root(hm_commitment_root),
        "hj_commitment_root": require_root(hj_commitment_root),
        "hm_epoch": hm_epoch,
        "hj_epoch": hj_epoch,
        "decision_root": require_root(decision_root),
        "hm_key_root": key_root(hm_key),
        "hj_key_root": key_root(hj_key),
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    approvals = {"H_M": signed(f"{PAIR_DOMAIN}:H_M", body, hm_key), "H_J": signed(f"{PAIR_DOMAIN}:H_J", body, hj_key)}
    record = {"body": body, "body_root": root(body), "approvals": approvals}
    return {**record, "pair_root": root(record)}


def verify_pair_attestation(
    record: Any,
    *,
    constitution: Any,
    keys: dict[str, str],
    decision_root: str,
    hm_epoch: int,
    hj_epoch: int,
    allowed_pair_roots: set[str],
    expected_constitution_root: str,
) -> dict[str, Any]:
    item = exact_keys(record, {"body", "body_root", "approvals", "pair_root"}, "$.pair")
    body = exact_keys(item["body"], {"schema", "constitution_root", "hm_commitment_root", "hj_commitment_root", "hm_epoch", "hj_epoch", "decision_root", "hm_key_root", "hj_key_root", "standing", "authority_effect"}, "$.pair.body")
    require(body["schema"] == "ucl.ucm.operational_exact_pair.v1", "PAIR_SCHEMA_INVALID")
    require(item["body_root"] == root(body) and item["pair_root"] == root({k: item[k] for k in ("body", "body_root", "approvals")}), "PAIR_ROOT_MISMATCH")
    require(item["pair_root"] in allowed_pair_roots, "PAIR_NOT_LISTED")
    constitution_root = constitution.get("constitution_root") if type(constitution) is dict else None
    expected_constitution_root = require_root(expected_constitution_root)
    require(constitution_root == expected_constitution_root, "CONSTITUTION_PIN_MISMATCH")
    descriptors = _verified_role_keys(constitution, keys, expected_constitution_root)
    require(body.get("constitution_root") == constitution_root and body.get("decision_root") == require_root(decision_root), "PAIR_DECISION_MISMATCH")
    require(body.get("hm_epoch") == hm_epoch and type(body.get("hm_epoch")) is int and type(hm_epoch) is int and type(hm_epoch) is not bool, "PAIR_EPOCH_MISMATCH")
    require(body.get("hj_epoch") == hj_epoch and type(body.get("hj_epoch")) is int and type(hj_epoch) is int and type(hj_epoch) is not bool, "PAIR_EPOCH_MISMATCH")
    hm_key, hj_key = keys["H_M"], keys["H_J"]
    require(body["hm_key_root"] == descriptors["H_M"] == key_root(hm_key), "PAIR_HM_KEY_ROLE_MISMATCH")
    require(body["hj_key_root"] == descriptors["H_J"] == key_root(hj_key), "PAIR_HJ_KEY_ROLE_MISMATCH")
    require(descriptors["H_M"] != descriptors["H_J"], "PAIR_APPROVAL_ROLES_NOT_DISTINCT")
    require(set(item["approvals"]) == {"H_M", "H_J"}, "PAIR_APPROVAL_SET_INVALID")
    require(body.get("standing") == "INFORMATION_ONLY" and body.get("authority_effect") == "NONE", "PAIR_EFFECT_FORBIDDEN")
    require(_verify_signed(item["approvals"]["H_M"], f"{PAIR_DOMAIN}:H_M", hm_key) == body, "PAIR_HM_SIGNATURE_INVALID")
    require(_verify_signed(item["approvals"]["H_J"], f"{PAIR_DOMAIN}:H_J", hj_key) == body, "PAIR_HJ_SIGNATURE_INVALID")
    return {"status": "VERIFIED_INFORMATION_ONLY", "pair_root": item["pair_root"], "standing": "INFORMATION_ONLY"}


def prepare_standing_proposal(
    *,
    constitution: Any,
    keys: dict[str, str],
    a5_proposal: Any,
    pair_attestation: Any,
    compilation_root: str,
    execution_root: str,
    decision_root: str,
    expected_a5_sequence: int,
    expected_a5_predecessor: str,
    hm_epoch: int,
    hj_epoch: int,
    allowed_pair_roots: set[str],
    expected_constitution_root: str,
) -> dict[str, Any]:
    constitution_root = constitution.get("constitution_root") if type(constitution) is dict else None
    expected_constitution_root = require_root(expected_constitution_root)
    require(constitution_root == expected_constitution_root, "CONSTITUTION_PIN_MISMATCH")
    _verified_role_keys(constitution, keys, expected_constitution_root)
    a5_verified = verify_a5_proposal(
        a5_proposal,
        constitution=constitution,
        keys=keys,
        seen_nonces=set(),
        expected_sequence=expected_a5_sequence,
        expected_predecessor=expected_a5_predecessor,
        expected_constitution_root=expected_constitution_root,
    )
    pair_verified = verify_pair_attestation(
        pair_attestation,
        constitution=constitution,
        keys=keys,
        decision_root=decision_root,
        hm_epoch=hm_epoch,
        hj_epoch=hj_epoch,
        allowed_pair_roots=allowed_pair_roots,
        expected_constitution_root=expected_constitution_root,
    )
    body = {
        "schema": "ucl.ucm.standing_proposal.v1",
        "constitution_root": require_root(constitution_root),
        "a5_proposal_root": require_root(a5_verified["a5_proposal_root"]),
        "pair_root": require_root(pair_verified["pair_root"]),
        "compilation_root": require_root(compilation_root),
        "execution_root": require_root(execution_root),
        "requested_standing": "EXPERIMENTAL_CANDIDATE",
        "decision_applied": False,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
        "real_a5": False,
        "g0": "CLOSED",
    }
    approval = signed(f"{STANDING_DOMAIN}:GOVERNOR_PROPOSAL", body, keys["GOVERNOR"])
    record = {"body": body, "body_root": root(body), "governor_proposal_signature": approval}
    return {**record, "standing_proposal_root": root(record)}


def verify_standing_proposal(
    record: Any,
    *,
    constitution: Any,
    keys: dict[str, str],
    a5_proposal: Any,
    pair_attestation: Any,
    decision_root: str,
    expected_a5_sequence: int,
    expected_a5_predecessor: str,
    hm_epoch: int,
    hj_epoch: int,
    allowed_pair_roots: set[str],
    expected_constitution_root: str,
) -> dict[str, Any]:
    item = exact_keys(record, {"body", "body_root", "governor_proposal_signature", "standing_proposal_root"}, "$.standing_proposal")
    body = exact_keys(item["body"], {"schema", "constitution_root", "a5_proposal_root", "pair_root", "compilation_root", "execution_root", "requested_standing", "decision_applied", "standing", "authority_effect", "real_a5", "g0"}, "$.standing_proposal.body")
    require(body["schema"] == "ucl.ucm.standing_proposal.v1", "STANDING_PROPOSAL_SCHEMA_INVALID")
    require(item["body_root"] == root(body), "STANDING_PROPOSAL_BODY_ROOT_MISMATCH")
    require(item["standing_proposal_root"] == root({key: item[key] for key in ("body", "body_root", "governor_proposal_signature")}), "STANDING_PROPOSAL_ROOT_MISMATCH")
    constitution_root = constitution.get("constitution_root") if type(constitution) is dict else None
    expected_constitution_root = require_root(expected_constitution_root)
    require(constitution_root == expected_constitution_root, "CONSTITUTION_PIN_MISMATCH")
    descriptors = _verified_role_keys(constitution, keys, expected_constitution_root)
    require(body["constitution_root"] == constitution_root, "STANDING_PROPOSAL_CONSTITUTION_MISMATCH")
    a5_verified = verify_a5_proposal(a5_proposal, constitution=constitution, keys=keys, seen_nonces=set(), expected_sequence=expected_a5_sequence, expected_predecessor=expected_a5_predecessor, expected_constitution_root=expected_constitution_root)
    pair_verified = verify_pair_attestation(pair_attestation, constitution=constitution, keys=keys, decision_root=decision_root, hm_epoch=hm_epoch, hj_epoch=hj_epoch, allowed_pair_roots=allowed_pair_roots, expected_constitution_root=expected_constitution_root)
    require(body["a5_proposal_root"] == a5_verified["a5_proposal_root"], "STANDING_PROPOSAL_A5_UNVERIFIED")
    require(body["pair_root"] == pair_verified["pair_root"], "STANDING_PROPOSAL_PAIR_UNVERIFIED")
    for key in ("a5_proposal_root", "pair_root", "compilation_root", "execution_root"):
        require_root(body[key], f"$.standing_proposal.body.{key}")
    require(body["decision_applied"] is False and body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE", "STANDING_PROPOSAL_EFFECT_FORBIDDEN")
    require(body["real_a5"] is False and body["g0"] == "CLOSED", "STANDING_PROPOSAL_BOUNDARY_INVALID")
    governor_key = keys["GOVERNOR"]
    require(key_root(governor_key) == descriptors["GOVERNOR"], "STANDING_PROPOSAL_GOVERNOR_ROLE_MISMATCH")
    require(_verify_signed(item["governor_proposal_signature"], f"{STANDING_DOMAIN}:GOVERNOR_PROPOSAL", governor_key) == body, "STANDING_PROPOSAL_SIGNATURE_INVALID")
    return {"status": "VERIFIED_PROPOSAL_ONLY", "standing_proposal_root": item["standing_proposal_root"], "standing": "INFORMATION_ONLY"}


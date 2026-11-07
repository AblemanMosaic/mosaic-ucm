"""Versioned workbench contracts. Existing canonical dialects are unchanged."""
from __future__ import annotations

import copy
import hashlib
import re
from typing import Any

from .canonical import exact_keys, require, require_root, root

ROOT_KINDS = frozenset({"PROJECT", "SOURCE", "IMPLEMENTATION", "REGISTRY", "POLICY", "NAMESPACE", "SCHEMA", "ARTIFACT", "EVIDENCE", "OBLIGATION", "SEMANTIC", "STATE", "CHARTER", "GRANT", "CONTRACT", "RECEIPT", "PUBLIC_KEY"})
FORBIDDEN_SECRET_FIELDS = frozenset({"secret", "token", "seed", "privatekey", "privatekeyhex", "signingkey", "apikey", "accesstoken", "refreshkey", "password", "credential", "privateseed", "clientsecret"})


def typed_root(kind: str, digest: str, *, dialect: str = "uclop-json-v1") -> dict[str, Any]:
    require(type(kind) is str and kind in ROOT_KINDS, "WORKBENCH_ROOT_KIND_INVALID")
    require(type(dialect) is str and dialect in {"uclop-json-v1", "bytes-sha256-v1"}, "WORKBENCH_CANONICAL_DIALECT_INVALID")
    return {"schema": "ucl.ucm.workbench.root_ref.v1", "kind": kind, "algorithm": "sha256", "digest": require_root(digest), "canonical_dialect": dialect}


def validate_root_ref(value: Any, kind: str | None = None) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "kind", "algorithm", "digest", "canonical_dialect"})
    require(item == typed_root(item["kind"], item["digest"], dialect=item["canonical_dialect"]), "WORKBENCH_ROOT_REF_INVALID")
    require(kind is None or item["kind"] == kind, "WORKBENCH_ROOT_KIND_MISMATCH")
    return copy.deepcopy(item)


def artifact_ref(data: bytes) -> dict[str, Any]:
    require(type(data) is bytes, "WORKBENCH_ARTIFACT_BYTES_REQUIRED")
    return typed_root("ARTIFACT", hashlib.sha256(data).hexdigest(), dialect="bytes-sha256-v1")


def reject_raw_secrets(value: Any, *, allowed_paths: frozenset[tuple[str, ...]] = frozenset()) -> None:
    """Reject credential-shaped material, with exact paths for typed non-secret seeds."""
    pending = [(value, ())]
    while pending:
        item, path = pending.pop()
        if type(item) is dict:
            for name, child in item.items():
                require(type(name) is str, "WORKBENCH_FIELD_INVALID")
                normalized = re.sub(r"[^a-z0-9]", "", name.lower())
                child_path = (*path, name)
                allowed = child_path in allowed_paths and normalized == "seed" and type(child) is int and child >= 0
                require(normalized not in FORBIDDEN_SECRET_FIELDS or allowed, "WORKBENCH_RAW_SECRET_FORBIDDEN")
                pending.append((child, child_path))
        elif type(item) is list:
            pending.extend((child, (*path, str(index))) for index, child in enumerate(item))
        elif type(item) is str:
            require("PRIVATE KEY" not in item and not re.fullmatch(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", item), "WORKBENCH_RAW_SECRET_FORBIDDEN")


def obligation_identity(*, obligation_id: str, subject: dict[str, Any], formula: dict[str, Any], jurisdiction: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    require(type(obligation_id) is str and 0 < len(obligation_id) <= 128, "WORKBENCH_OBLIGATION_ID_INVALID")
    validate_root_ref(subject, "EVIDENCE")
    validate_root_ref(formula, "SEMANTIC")
    validate_root_ref(jurisdiction, "NAMESPACE")
    validate_root_ref(provenance, "CONTRACT")
    body = {"schema": "ucl.ucm.workbench.obligation_identity.v1", "obligation_id": obligation_id, "evidence_subject": subject, "formula": formula, "jurisdiction": jurisdiction, "provenance": provenance}
    return {**copy.deepcopy(body), "root": root(body)}


def verify_obligation_identity(value: Any, *, expected: dict[str, Any] | None = None) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "obligation_id", "evidence_subject", "formula", "jurisdiction", "provenance", "root"})
    rebuilt = obligation_identity(obligation_id=item["obligation_id"], subject=item["evidence_subject"], formula=item["formula"], jurisdiction=item["jurisdiction"], provenance=item["provenance"])
    require(item == rebuilt, "WORKBENCH_OBLIGATION_IDENTITY_INVALID")
    require(expected is None or item == expected, "WORKBENCH_OBLIGATION_IMMUTABLE_FIELD_CHANGED")
    return copy.deepcopy(item)


def result_receipt(*, execution_status: str, observed_effects: list[str], inputs: list[dict[str, Any]], outputs: list[dict[str, Any]], recovery_required: bool = False) -> dict[str, Any]:
    require(type(execution_status) is str and execution_status in {"PASS", "REFUSED", "FAIL", "PENDING_RECOVERY", "INTERRUPTED", "INFORMATION_ONLY"}, "WORKBENCH_EXECUTION_STATUS_INVALID")
    require(type(observed_effects) is list and all(type(x) is str and x in {"READ_WORKSPACE", "WRITE_WORKSPACE", "DELETE_WORKSPACE"} for x in observed_effects), "WORKBENCH_OBSERVED_EFFECT_INVALID")
    require(len(observed_effects) == len(set(observed_effects)), "WORKBENCH_OBSERVED_EFFECT_DUPLICATE")
    require(type(recovery_required) is bool and (execution_status != "PENDING_RECOVERY" or recovery_required), "WORKBENCH_RECOVERY_STATUS_INVALID")
    require(type(inputs) is list and type(outputs) is list, "WORKBENCH_RECEIPT_REFS_INVALID")
    for value in inputs + outputs:
        validate_root_ref(value)
    body = {"schema": "ucl.ucm.workbench.result.v1", "execution_status": execution_status, "observed_effects": sorted(observed_effects), "authority_effect": "NONE", "standing": "INFORMATION_ONLY", "constitutional_acceptance": "NOT_GRANTED", "recovery_required": recovery_required, "inputs": copy.deepcopy(inputs), "outputs": copy.deepcopy(outputs)}
    return {**body, "root": root(body)}


def verify_result_receipt(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "execution_status", "observed_effects", "authority_effect", "standing", "constitutional_acceptance", "recovery_required", "inputs", "outputs", "root"})
    rebuilt = result_receipt(execution_status=item["execution_status"], observed_effects=item["observed_effects"], inputs=item["inputs"], outputs=item["outputs"], recovery_required=item["recovery_required"])
    require(item == rebuilt, "WORKBENCH_RESULT_RECEIPT_INVALID")
    return copy.deepcopy(item)


def thr_correspondence(value: Any, *, expected_contract_root: str) -> dict[str, Any]:
    """Preserve native commitments; this adapter does not replace UGK verification.

    In particular h_body is a native domain-separated commitment to ALL source
    receipt fields, not the SHA-256 root of this small correspondence record.
    """
    item = exact_keys(value, {"schema", "contract_root", "source_receipt", "H_s", "H_c", "H_m", "H_j", "H_r", "h_body"})
    require(item["schema"] == "ucl.ucm.workbench.thr_correspondence.v1" and item["contract_root"] == require_root(expected_contract_root), "WORKBENCH_THR_CONTRACT_MISMATCH")
    validate_root_ref(item["source_receipt"], "RECEIPT")
    for field in ("H_s", "H_c", "H_m", "H_j", "H_r", "h_body"):
        require_root(item[field])
    body = {"schema": "ucl.ucm.workbench.thr_adapter_result.v1", "correspondence": copy.deepcopy(item), "status": "CORRESPONDENCE_ONLY", "source_receipt_verified": False, "required_verifier": "PINNED_NATIVE_UGK_RECEIPT_VERIFIER", "authority_effect": "NONE", "standing": "INFORMATION_ONLY"}
    return {**body, "adapter_root": root(body)}


def verify_role_lineage(events: Any, *, expected_head: str, authority_key_root: str, authority_public_key_hex: str, genesis_root: str) -> dict[str, Any]:
    from .custody import verify_asymmetric
    require(type(events) is list, "WORKBENCH_ROLE_LINEAGE_INVALID")
    prior = require_root(genesis_root)
    retired: set[str] = set()
    active: dict[str, str] = {}
    for index, event in enumerate(events, 1):
        signed = exact_keys(event, {"body", "body_root", "signature", "key_root", "signature_algorithm"})
        require(type(signed["body"]) is dict and type(signed["signature"]) is str and len(signed["signature"]) == 88, "WORKBENCH_SIGNED_RECORD_INVALID")
        body = verify_asymmetric(event, "UCL_UCM_WORKBENCH_ROLE_LINEAGE_V1", expected_key_root=authority_key_root, public_key_hex=authority_public_key_hex)
        exact_keys(body, {"schema", "sequence", "predecessor", "role", "operation", "key_root"})
        require(body["schema"] == "ucl.ucm.workbench.role_lineage.v1" and type(body["sequence"]) is int and body["sequence"] == index and body["predecessor"] == prior, "WORKBENCH_ROLE_LINEAGE_CHAIN_INVALID")
        require(type(body["role"]) is str and bool(body["role"]), "WORKBENCH_ROLE_INVALID")
        key = require_root(body["key_root"])
        if body["operation"] == "SEAT":
            require(key not in retired and key not in active.values(), "WORKBENCH_ROLE_KEY_REUSE")
            require(body["role"] not in active, "WORKBENCH_ROLE_ALREADY_SEATED")
            active[body["role"]] = key
        else:
            require(body["operation"] == "RETIRE" and active.get(body["role"]) == key, "WORKBENCH_ROLE_RETIREMENT_INVALID")
            retired.add(key)
            del active[body["role"]]
        prior = root(event)
    require(prior == require_root(expected_head), "WORKBENCH_ROLE_LINEAGE_STALE")
    return {"active": active, "retired": sorted(retired), "head": prior}

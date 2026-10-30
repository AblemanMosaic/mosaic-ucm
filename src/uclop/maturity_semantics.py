"""Shared maturity contracts with lossless adapters to the frozen workbench ABI.

Digest labels describe how an existing digest was made.  They never rehash it,
change a domain separator, verify an opaque native commitment, or grant authority.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any

from .canonical import canonical_bytes, exact_keys, require, require_root, root
from .custody import public_key_root
from .workbench_contracts import (
    ROOT_KINDS, obligation_identity, typed_root, validate_root_ref,
    verify_obligation_identity, verify_result_receipt, verify_role_lineage,
)

BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE", "real_a5": False, "g0": "CLOSED"}
DIALECTS = {
    ("sha256", "uclop-json-v1"),
    ("sha256", "bytes-sha256-v1"),
    ("sha256", "uclsh-json-v1"),
    ("blake3", "dkn-v1-native"),
}
EXECUTION = frozenset({"NOT_STARTED", "RUNNING", "PASS", "FAIL", "REFUSED", "INTERRUPTED", "PENDING_RECOVERY", "INFORMATION_ONLY"})
ASSESSMENT = frozenset({"UNREVIEWED", "INCOMPLETE_REVIEW", "HOLD_FOR_REPAIR", "QUALIFIED_RECOMMENDATION_ONLY", "NOT_QUALIFIED"})
COMPLETION_ORDER = ("BLOCKED", "PENDING", "IN_PROGRESS", "COMPLETE")
LOCAL_EFFECTS = frozenset({"READ_WORKSPACE", "WRITE_WORKSPACE", "DELETE_WORKSPACE", "LOCAL_PROCESS"})


def seal(body: dict[str, Any]) -> dict[str, Any]:
    return {**deepcopy(body), "root": root(body)}


def checked(value: Any, keys: set[str], schema: str) -> dict[str, Any]:
    item = exact_keys(value, keys | {"root"})
    require(item["schema"] == schema, "MATURITY_SCHEMA_INVALID")
    body = {key: value for key, value in item.items() if key != "root"}
    require(item["root"] == root(body), "MATURITY_RECORD_ROOT_INVALID")
    return deepcopy(item)


def digest_ref(kind: str, digest: str, *, algorithm: str = "sha256", dialect: str = "uclop-json-v1") -> dict:
    require(type(kind) is str and kind in ROOT_KINDS, "MATURITY_ROOT_KIND_INVALID")
    require(type(algorithm) is str and type(dialect) is str and (algorithm, dialect) in DIALECTS, "MATURITY_DIGEST_DIALECT_INVALID")
    return {"schema": "ucl.ucm.maturity.digest_ref.v1", "kind": kind, "algorithm": algorithm,
            "dialect": dialect, "digest": require_root(digest)}


def verify_digest_ref(value: Any, *, kind: str | None = None) -> dict:
    item = exact_keys(value, {"schema", "kind", "algorithm", "dialect", "digest"})
    rebuilt = digest_ref(item["kind"], item["digest"], algorithm=item["algorithm"], dialect=item["dialect"])
    require(item == rebuilt and (kind is None or kind == item["kind"]), "MATURITY_DIGEST_REFERENCE_MISMATCH")
    return rebuilt


def from_legacy_root(value: Any) -> dict:
    old = validate_root_ref(value)
    return digest_ref(old["kind"], old["digest"], algorithm=old["algorithm"], dialect=old["canonical_dialect"])


def to_legacy_root(value: Any) -> dict:
    item = verify_digest_ref(value)
    require(item["algorithm"] == "sha256" and item["dialect"] in {"uclop-json-v1", "bytes-sha256-v1"}, "MATURITY_LEGACY_DIALECT_UNREPRESENTABLE")
    return typed_root(item["kind"], item["digest"], dialect=item["dialect"])


def bytes_ref(data: bytes, kind: str = "ARTIFACT") -> dict:
    require(type(data) is bytes, "MATURITY_EXACT_BYTES_REQUIRED")
    return digest_ref(kind, hashlib.sha256(data).hexdigest(), dialect="bytes-sha256-v1")


def ceiling(*, allowed_effects: list[str] | None = None, stage_limit: str = "LOCAL_EXPERIMENTAL") -> dict:
    effects = [] if allowed_effects is None else allowed_effects
    require(type(effects) is list and all(type(item) is str and item in LOCAL_EFFECTS for item in effects)
            and len(effects) == len(set(effects)), "MATURITY_EFFECT_CEILING_INVALID")
    require(type(stage_limit) is str and stage_limit in {"PURE_COMPUTATION", "READ_ONLY", "LOCAL_EXPERIMENTAL", "PROPOSAL_ONLY"}, "MATURITY_STAGE_CEILING_INVALID")
    require(stage_limit != "PURE_COMPUTATION" or not effects, "MATURITY_PURE_EFFECT_CONFLICT")
    require(stage_limit != "READ_ONLY" or set(effects) <= {"READ_WORKSPACE"}, "MATURITY_READ_ONLY_EFFECT_CONFLICT")
    return seal({"schema": "ucl.ucm.maturity.authority_ceiling.v1", "allowed_effects": sorted(effects),
                 "stage_limit": stage_limit, "binding": "UNBOUND", **BOUNDARY})


def verify_ceiling(value: Any) -> dict:
    item = exact_keys(value, {"schema", "allowed_effects", "stage_limit", "binding", "standing", "authority_effect", "real_a5", "g0", "root"})
    require(canonical_bytes(item) == canonical_bytes(ceiling(allowed_effects=item["allowed_effects"], stage_limit=item["stage_limit"])), "MATURITY_AUTHORITY_CEILING_CHANGED")
    return deepcopy(item)


def enforce_effects(value: Any, observed: list[str]) -> None:
    item = verify_ceiling(value)
    require(type(observed) is list and all(type(x) is str for x in observed)
            and len(observed) == len(set(observed)) and set(observed) <= set(item["allowed_effects"]), "MATURITY_EFFECT_CEILING_EXCEEDED")


def result_state(*, execution: list[str], completion: str, assessment: list[str] | None = None,
                 observed_effects: list[str] | None = None, recovery_required: bool = False,
                 inputs: list[dict] | None = None, outputs: list[dict] | None = None) -> dict:
    reviews = ["UNREVIEWED"] if assessment is None else assessment
    effects = [] if observed_effects is None else observed_effects
    require(type(execution) is list and execution and all(type(x) is str and x in EXECUTION for x in execution)
            and len(execution) == len(set(execution)), "MATURITY_EXECUTION_STATE_INVALID")
    require(type(reviews) is list and reviews and all(type(x) is str and x in ASSESSMENT for x in reviews)
            and len(reviews) == len(set(reviews)), "MATURITY_ASSESSMENT_STATE_INVALID")
    require(type(completion) is str and completion in COMPLETION_ORDER and type(recovery_required) is bool, "MATURITY_COMPLETION_STATE_INVALID")
    enforce_effects(ceiling(allowed_effects=sorted(LOCAL_EFFECTS)), effects)
    require("PENDING_RECOVERY" not in execution or recovery_required, "MATURITY_RECOVERY_STATE_INVALID")
    require(completion != "COMPLETE" or (set(execution) == {"PASS"} and not recovery_required), "MATURITY_COMPLETION_NOT_ESTABLISHED")
    refs = []
    for supplied in ([] if inputs is None else inputs, [] if outputs is None else outputs):
        require(type(supplied) is list, "MATURITY_RESULT_REFERENCES_INVALID")
        checked_refs = [verify_digest_ref(item) for item in supplied]
        require(len(checked_refs) == len({root(item) for item in checked_refs}), "MATURITY_RESULT_REFERENCE_DUPLICATE")
        refs.append(sorted(checked_refs, key=root))
    return seal({"schema": "ucl.ucm.maturity.result_state.v1", "execution": sorted(execution),
        "completion": completion, "assessment": sorted(reviews), "observed_effects": sorted(effects),
        "recovery_required": recovery_required, "inputs": refs[0], "outputs": refs[1],
        "constitutional_acceptance": "NOT_GRANTED", **BOUNDARY})


def verify_result_state(value: Any) -> dict:
    item = exact_keys(value, {"schema", "execution", "completion", "assessment", "observed_effects", "recovery_required", "inputs", "outputs", "constitutional_acceptance", "standing", "authority_effect", "real_a5", "g0", "root"})
    rebuilt = result_state(**{key: item[key] for key in ("execution", "completion", "assessment", "observed_effects", "recovery_required", "inputs", "outputs")})
    require(canonical_bytes(item) == canonical_bytes(rebuilt), "MATURITY_RESULT_STATE_INVALID")
    return rebuilt


def join_result_states(*values: dict) -> dict:
    """Join independent observations: outcome sets grow; completion stays conservative.

    Union plus the minimum completion order is associative, commutative and
    idempotent. A failed, pending or uncertain input cannot become complete.
    """
    require(bool(values), "MATURITY_RESULT_JOIN_EMPTY")
    rows = [verify_result_state(value) for value in values]
    def refs(field):
        merged = {root(item): item for row in rows for item in row[field]}
        return [merged[key] for key in sorted(merged)]
    return result_state(execution=sorted({item for row in rows for item in row["execution"]}),
        completion=min((row["completion"] for row in rows), key=COMPLETION_ORDER.index),
        assessment=sorted({item for row in rows for item in row["assessment"]}),
        observed_effects=sorted({item for row in rows for item in row["observed_effects"]}),
        recovery_required=any(row["recovery_required"] for row in rows), inputs=refs("inputs"), outputs=refs("outputs"))


def from_legacy_result(value: Any) -> dict:
    old = verify_result_receipt(value)
    # A legacy PASS establishes execution only, never plan completion/review.
    return result_state(execution=[old["execution_status"]], completion="PENDING",
        observed_effects=old["observed_effects"], recovery_required=old["recovery_required"],
        inputs=[from_legacy_root(x) for x in old["inputs"]], outputs=[from_legacy_root(x) for x in old["outputs"]])


def bind_obligation(*, obligation_id: str, subject: dict, formula: dict, jurisdiction: dict, provenance: dict) -> dict:
    identity = obligation_identity(obligation_id=obligation_id, subject=to_legacy_root(subject),
        formula=to_legacy_root(formula), jurisdiction=to_legacy_root(jurisdiction), provenance=to_legacy_root(provenance))
    return seal({"schema": "ucl.ucm.maturity.obligation_binding.v1", "identity": identity,
                 "identity_root": identity["root"], "verification": "NOT_YET_DISCHARGED", **BOUNDARY})


def verify_obligation_binding(value: Any, *, expected_identity: dict) -> dict:
    item = checked(value, {"schema", "identity", "identity_root", "verification", "standing", "authority_effect", "real_a5", "g0"}, "ucl.ucm.maturity.obligation_binding.v1")
    identity = verify_obligation_identity(item["identity"], expected=expected_identity)
    require(item["identity_root"] == identity["root"] and item["verification"] == "NOT_YET_DISCHARGED"
            and all(type(item[key]) is type(val) and item[key] == val for key, val in BOUNDARY.items()), "MATURITY_OBLIGATION_BINDING_INVALID")
    return item


def evidence_claim(binding: dict, material: bytes, *, expected_identity: dict) -> dict:
    item = verify_obligation_binding(binding, expected_identity=expected_identity)
    return seal({"schema": "ucl.ucm.maturity.evidence_claim.v1", "obligation_identity_root": item["identity_root"],
        "binding_root": item["root"], "evidence": bytes_ref(material, "EVIDENCE"),
        "evidence_subject": from_legacy_root(item["identity"]["evidence_subject"]),
        "disposition": "PENDING_REGISTERED_CHECKER", **BOUNDARY})


def identity_lineage(events: list[dict], *, expected_head: str, authority_key_root: str,
                     authority_public_key_hex: str, genesis_root: str, independent_roles: bool = True) -> dict:
    require(type(independent_roles) is bool and independent_roles, "MATURITY_ROLE_INDEPENDENCE_REQUIRED")
    require(public_key_root(authority_public_key_hex) == require_root(authority_key_root), "MATURITY_LINEAGE_AUTHORITY_PIN_MISMATCH")
    folded = verify_role_lineage(events, expected_head=expected_head, authority_key_root=authority_key_root,
        authority_public_key_hex=authority_public_key_hex, genesis_root=genesis_root)
    require(authority_key_root not in folded["active"].values()
            and authority_key_root not in folded["retired"], "MATURITY_ROLE_AUTHORITY_COLLISION")
    return seal({"schema": "ucl.ucm.maturity.identity_lineage.v1", "genesis_root": require_root(genesis_root),
        "authority_key_root": require_root(authority_key_root), "head": folded["head"],
        "active": folded["active"], "retired": folded["retired"], "scope": "PINNED_GENESIS_HISTORY", **BOUNDARY})


def contract_registry() -> dict:
    return seal({"schema": "ucl.ucm.maturity.semantic_contract_registry.v1",
        "contracts": ["DIGEST_REFERENCE", "RESULT_STATE_LATTICE", "AUTHORITY_CEILING", "OBLIGATION_EVIDENCE_CLAIM_BINDING", "ROLE_KEY_LINEAGE"],
        "legacy_abi": "EXACT_ROUNDTRIP_WHERE_REPRESENTABLE", "ucl_semantics_changed": False,
        "algorithms_and_domain_separators_changed": False, "ratification": "NOT_GRANTED", **BOUNDARY})

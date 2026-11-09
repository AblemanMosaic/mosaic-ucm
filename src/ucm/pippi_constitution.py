"""Constitutional atlas, pipeline model, and portable collaboration records.

This module makes P/PPI's accumulated standards navigable without collapsing
their distinct semantics.  Co-projections reinforce one another; none is
treated as interchangeable with another.  Every builder is pure and grants no
authority.  Provider dispatch, secret custody, and effects remain external.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any

from uclop.canonical import canonical_bytes, exact_keys, require, root

from .identity import mosaic_id, validate_signing_key, verify_passport
from .pippi_adaptive import mediation_library
from .pippi_global import BOUNDARY


ATLAS_SCHEMA = "mosaic.ucm.pippi-constitutional-standards-atlas.v0.1"
PIPELINE_SCHEMA = "mosaic.ucm.pippi-pipeline-model.v0.1"
CHANGE_SCHEMA = "mosaic.ucm.pippi-constitutional-change-capsule.v0.1"
PUBLICATION_SCHEMA = "mosaic.ucm.pippi-storage-publication-receipt.v0.1"
RETRIEVAL_SCHEMA = "mosaic.ucm.pippi-storage-retrieval-receipt.v0.1"


def _sha(value: Any, code: str) -> str:
    require(type(value) is str and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value), code)
    return value


def _ident(value: Any, code: str, *, maximum: int = 192) -> str:
    require(type(value) is str and bool(value.strip()) and value == value.strip()
            and len(value) <= maximum, code)
    return value


def _strings(values: Any, code: str, *, roots: bool = False) -> list[str]:
    require(type(values) is list and values == sorted(set(values)), code)
    for value in values:
        _ident(value, code)
        if roots:
            _sha(value, code)
    return list(values)


def _identity_from_key(*, public_key_hex: str, declared_identity_root: str,
                       code: str) -> str:
    """Bind a declared MosaicID identity to the key that actually signs."""
    validate_signing_key(public_key_hex)
    _sha(declared_identity_root, code)
    derived = mosaic_id(public_key_hex)
    require(declared_identity_root == derived, code)
    return derived


def _file_sha256(path_value: Any) -> str:
    require(type(path_value) is str and bool(path_value.strip()),
            "PIPPI_RETRIEVAL_ARTIFACT_PATH_INVALID")
    path = Path(path_value)
    require(path.is_file(), "PIPPI_RETRIEVAL_ARTIFACT_MISSING")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        require(False, "PIPPI_RETRIEVAL_ARTIFACT_UNREADABLE",
                detail=type(error).__name__)
    return digest.hexdigest()


_RULE_MODEL = {
    "AUTHORITY_BOUNDARY": ("CM1", ["AMCAS", "UGK", "CCP", "OPERATIONAL_GATEWAY"],
        ["BUILD_PIPPI_CONTEXT", "EVALUATE_CURRENT_ADMISSIBILITY"],
        ["authority_policy_root", "jurisdiction_root"],
        ["UNDECLARED_EFFECT", "AUTHORITY_GRANT_UNAVAILABLE"],
        ["Plans can be mistaken for permission", "Admissibility can be mistaken for dispatch authority"]),
    "VERSION_POLICY": ("CM1", ["PIPPI", "DKN", "THR"],
        ["BUILD_PIPPI_CONTEXT"], ["predecessor_root", "version_approval_root"],
        ["IMPLICIT_VERSION_BUMP", "REVISION_PREDECESSOR_MISMATCH"],
        ["Agents can silently launder a public version change"]),
    "PROJECT_ENTRYPOINTS": ("CM1", ["AMCAS", "PIPPI", "DEPENDENCY_EVIDENCE_GRAPH"],
        ["PREPARE_GOVERNED_WORK_PACKAGE"], ["project_root", "entrypoint_root"],
        ["ENTRYPOINT_UNDECLARED"], ["The wrong launcher or verifier can be selected"]),
    "ARCHIVE_POLICY": ("CM1", ["THR", "DKN", "SEMCRYS", "MEMORY_VAULT"],
        ["BUILD_PIPPI_PROJECT_CAPSULE"], ["state_root", "semantic_root", "governance_root"],
        ["PRIVATE_MATERIAL_REFUSED", "ARCHIVE_CUSTODY_INCOMPLETE"],
        ["Progress can be laundered as evidence", "Duplicate history can bloat active releases"]),
    "COURTHOUSE_ROUTING": ("CM1", ["PIPPI", "CCP", "COURTHOUSE_WORKFLOW_IR"],
        ["COMPILE_ADMISSIBLE_COURTHOUSE_WORKFLOW"], ["admission_envelope_root", "workflow_root"],
        ["CROSS_JURISDICTION_BYPASS"], ["Remote work can bypass receipted correspondence"]),
    "VISIBILITY_POLICY": ("CM1", ["PIPPI", "MOSAIC_UI", "CONSTITUTIONAL_LAUNCHER"],
        ["BUILD_PIPPI_HUMAN_PROJECTION"], ["projection_root", "journal_head"],
        ["USER_VIEW_STATE_DRIFT"], ["A human can see a stale or context-free status"]),
    "SEVEN_CHANNEL_COVERAGE": ("DIAGNOSTIC", ["PIPPI", "HOST_ADAPTER"],
        ["BUILD_ATTESTED_PIPPI_CONTEXT"], ["host_attestation_root"],
        ["ENFORCED_HOST_UNSUBSTANTIATED"], ["A sidecar can overclaim tool or output interposition"]),
    "UGK_FGA": ("CM1", ["UGK", "PIPPI", "PIPELINE_STATE_MODEL"],
        ["BUILD_PROCESS_CHECKPOINT"], ["predecessor_root", "transition_root", "successor_root"],
        ["TRANSITION_NOT_IN_MODEL"], ["A state change can lose its predecessor or receipt"]),
    "UGK_THREE_HASH_RULE": ("CM1", ["UGK", "THR", "DKN"],
        ["BUILD_PROCESS_THR_MANIFEST"], ["state_root", "semantic_root", "governance_root"],
        ["COMMITMENT_DOMAIN_COLLAPSED"], ["Equal bytes can be mistaken for equal meaning or authority"]),
    "UGK_IEL": ("CM1", ["UGK", "PIPPI", "OPERATIONAL_GATEWAY"],
        ["BUILD_PROCESS_CHECKPOINT"], ["expected_head", "recovery_receipt_root"],
        ["VALIDATE_BEFORE_MUTATE_REQUIRED", "UNCERTAIN_EFFECT_REDISPATCH_REFUSED"],
        ["An uncertain effect can be replayed or corrupt state can be overwritten"]),
    "UGK_CLAIM_DISCIPLINE": ("DIAGNOSTIC", ["UGK", "PIPPI", "COURT_EXECUTION"],
        ["BUILD_PIPPI_TURN_REPORT"], ["evidence_roots"],
        ["CLAIM_CLASS_UNSUPPORTED"], ["Implementation can be reported as execution or deployment"]),
    "ACCEPTANCE_CASE_SELECTION": ("CM1", ["PIPPI", "PROCESS_GOVERNANCE", "DEPENDENCY_EVIDENCE_GRAPH"],
        ["PREPARE_GOVERNED_WORK_PACKAGE"], ["acceptance_case_root", "work_selection_root"],
        ["WORK_WITHOUT_ACCEPTANCE_CASE", "INFRASTRUCTURE_WITHOUT_BLOCK"],
        ["Shared infrastructure can expand without closing a user-visible case"]),
    "EXECUTION_CONTEXT_DISCIPLINE": ("CM1", ["PIPPI", "PORTABILITY_DETERMINISM"],
        ["BUILD_PIPPI_EXECUTION_CONTEXT"], ["execution_context_root"],
        ["EXECUTION_CONTEXT_UNBOUND"], ["Shell, path, encoding, or filesystem assumptions can drift"]),
    "PORTABILITY_DETERMINISM": ("CM1", ["PIPPI", "PORTABILITY_GATE", "THR"],
        ["EVALUATE_PIPPI_PORTABILITY_GATE"], ["windows_witness_root", "wsl_witness_root"],
        ["PORTABILITY_WITNESS_MISSING", "PLATFORM_OUTPUT_DIVERGENCE"],
        ["One platform can silently define canonical bytes for all platforms"]),
}


_CO_PROJECTIONS = (
    ("AUTHORITY_AND_ADMISSIBILITY", ["AMCAS", "UGK", "CCP", "OPERATIONAL_GATEWAY"],
     "AMCAS states application obligations, UGK constrains transitions, CCP checks present use, and the gateway alone mediates effects."),
    ("SEMANTIC_AND_REALIZATION", ["AMCAS", "REALIZATION_SPACE", "DEPENDENCY_EVIDENCE_GRAPH", "UCL_TESSERA"],
     "Application intent, admissible configurations, dependency closure, and compiled obligations remain separately checkable."),
    ("IDENTITY_CUSTODY_AND_LOCALITY", ["MOSAIC_ID", "DKN", "THR", "SEMCRYS", "MEMORY_VAULT"],
     "Signer identity, namespace, commitment domains, semantic compression, and byte custody are related but non-equivalent."),
    ("PROCESS_AND_CORRESPONDENCE", ["PIPPI", "PROCESS_GOVERNANCE", "CCP", "COURTHOUSE_WORKFLOW_IR"],
     "Local work selection and context lead to point-of-use checks and receipted cross-jurisdiction correspondence."),
    ("HUMAN_VISIBILITY", ["PIPPI", "MOSAIC_UI", "CONSTITUTIONAL_LAUNCHER"],
     "The same governed state receives project, progress, launch, and diagnostic projections without creating alternate authority."),
)


def build_constitutional_standards_atlas() -> dict[str, Any]:
    library = mediation_library()
    rules = []
    for rule in library["rules"]:
        model = _RULE_MODEL[rule["rule_id"]]
        rules.append({**deepcopy(rule), "classification": model[0],
            "co_projection_systems": model[1], "capability_surfaces": model[2],
            "required_evidence_fields": model[3], "refusal_codes": model[4],
            "ablation_failure_modes": model[5]})
    co_projections = [{"projection_id": item[0], "system_ids": item[1],
                       "relationship": item[2], "identity_equivalence_claimed": False}
                      for item in _CO_PROJECTIONS]
    body = {"schema": ATLAS_SCHEMA, "version": "v0.1", "engineering_revision": "r033",
            "mediation_library_root": library["mediation_library_root"],
            "rules": rules, "co_projections": co_projections,
            "rule_count": len(rules), "co_projection_count": len(co_projections),
            "ablation_evidence_status": "HISTORICAL_EVIDENCE_REFERENCED_NOT_REEXECUTED",
            "co_projection_policy": "MUTUAL_REINFORCEMENT_WITHOUT_SEMANTIC_COLLAPSE",
            **BOUNDARY}
    return {**body, "atlas_root": root(body)}


def validate_constitutional_standards_atlas(value: Any) -> dict[str, Any]:
    expected = build_constitutional_standards_atlas()
    require(value == expected, "PIPPI_STANDARDS_ATLAS_INVALID")
    return deepcopy(expected)


_STATES = (
    ("REGISTERED", "Project identity and entrypoints are recorded."),
    ("ORIENTED", "Applicable standards, capabilities, and host coverage are pinned."),
    ("BOUND", "Subject, jurisdiction, identity, and policy roots are bound."),
    ("PLANNED", "A work unit names one acceptance case and verification surface."),
    ("PREFLIGHTED", "Dependencies, current evidence, and effect ceilings are checked."),
    ("DISPATCH_PREPARED", "G1 and durable dispatch intent exist; no terminal result is inferred."),
    ("EFFECT_OBSERVED", "External executor receipts are imported without replay."),
    ("DIAGNOSED", "G2/G3 and acceptance results are classified."),
    ("SEALED", "Journal, artifacts, commitments, and review boundary are frozen."),
    ("PUBLICATION_PROPOSED", "Storage-neutral targets and credentials are planned; dispatch remains held."),
    ("PUBLISHED", "A separately authorized provider receipt is verified and journaled."),
)


_TRANSITIONS = (
    ("ORIENT_PROJECT", "REGISTERED", "ORIENTED", ["AUTHORITY_BOUNDARY", "SEVEN_CHANNEL_COVERAGE"], "NONE", "NOT_REQUIRED", None),
    ("BIND_CONSTITUTION", "ORIENTED", "BOUND", ["AUTHORITY_BOUNDARY", "UGK_THREE_HASH_RULE"], "NONE", "REQUIRED", None),
    ("SELECT_WORK", "BOUND", "PLANNED", ["ACCEPTANCE_CASE_SELECTION", "PROJECT_ENTRYPOINTS"], "NONE", "REQUIRED", None),
    ("PREFLIGHT_WORK", "PLANNED", "PREFLIGHTED", ["EXECUTION_CONTEXT_DISCIPLINE", "PORTABILITY_DETERMINISM", "UGK_IEL"], "NONE", "REQUIRED", None),
    ("PREPARE_DISPATCH", "PREFLIGHTED", "DISPATCH_PREPARED", ["AUTHORITY_BOUNDARY", "COURTHOUSE_ROUTING", "UGK_FGA"], "PROPOSED_EXTERNAL_EFFECT", "REQUIRED", "G1_SENTINEL"),
    ("IMPORT_EFFECT", "DISPATCH_PREPARED", "EFFECT_OBSERVED", ["UGK_IEL", "UGK_THREE_HASH_RULE"], "RECEIPT_IMPORT_ONLY", "REQUIRED", "G2_WITNESS"),
    ("DIAGNOSE_RESULT", "EFFECT_OBSERVED", "DIAGNOSED", ["UGK_CLAIM_DISCIPLINE", "VISIBILITY_POLICY"], "NONE", "REQUIRED", "G3_DIAGNOSTIC"),
    ("SEAL_REVISION", "DIAGNOSED", "SEALED", ["ARCHIVE_POLICY", "VERSION_POLICY", "PORTABILITY_DETERMINISM"], "LOCAL_WRITE_PROPOSED", "REQUIRED", None),
    ("PROPOSE_PUBLICATION", "SEALED", "PUBLICATION_PROPOSED", ["ARCHIVE_POLICY", "AUTHORITY_BOUNDARY", "VERSION_POLICY"], "PROVIDER_EFFECT_PROPOSED", "REQUIRED", None),
    ("IMPORT_PUBLICATION_RECEIPT", "PUBLICATION_PROPOSED", "PUBLISHED", ["UGK_IEL", "UGK_CLAIM_DISCIPLINE"], "RECEIPT_IMPORT_ONLY", "REQUIRED", None),
)


def build_pipeline_model() -> dict[str, Any]:
    atlas = build_constitutional_standards_atlas()
    states = [{"state_id": state, "plain_language": text} for state, text in _STATES]
    transitions = [{"transition_id": row[0], "from_state": row[1], "to_state": row[2],
                    "required_rule_ids": row[3], "effect_class": row[4],
                    "ccp_current_use": row[5], "receipt_gate": row[6],
                    "automatic_authority_grant": False} for row in _TRANSITIONS]
    body = {"schema": PIPELINE_SCHEMA, "version": "v0.1", "engineering_revision": "r033",
            "atlas_root": atlas["atlas_root"], "states": states, "transitions": transitions,
            "initial_state": "REGISTERED", "terminal_states": ["PUBLISHED"],
            "state_count": len(states), "transition_count": len(transitions), **BOUNDARY}
    return {**body, "pipeline_model_root": root(body)}


def validate_pipeline_model(value: Any) -> dict[str, Any]:
    expected = build_pipeline_model()
    require(value == expected, "PIPPI_PIPELINE_MODEL_INVALID")
    return deepcopy(expected)


def explain_standard_rule(rule_id: str) -> dict[str, Any]:
    atlas = build_constitutional_standards_atlas()
    matches = [row for row in atlas["rules"] if row["rule_id"] == rule_id]
    require(len(matches) == 1, "PIPPI_STANDARD_RULE_UNKNOWN")
    body = {"schema": "mosaic.ucm.pippi-standard-rule-explanation.v0.1",
            "atlas_root": atlas["atlas_root"], "rule": matches[0],
            "projection_is_authority": False, "projection_is_evidence": False, **BOUNDARY}
    return {**body, "explanation_root": root(body)}


def explain_pipeline_transition(transition_id: str) -> dict[str, Any]:
    model = build_pipeline_model()
    matches = [row for row in model["transitions"] if row["transition_id"] == transition_id]
    require(len(matches) == 1, "PIPPI_PIPELINE_TRANSITION_UNKNOWN")
    atlas = build_constitutional_standards_atlas()
    rules = {row["rule_id"]: row for row in atlas["rules"]}
    transition = matches[0]
    body = {"schema": "mosaic.ucm.pippi-pipeline-transition-explanation.v0.1",
            "pipeline_model_root": model["pipeline_model_root"],
            "transition": transition,
            "required_rules": [rules[item] for item in transition["required_rule_ids"]],
            "next_action": ("OBTAIN_CCP_CURRENT_USE_DECISION" if transition["ccp_current_use"] == "REQUIRED"
                            else "APPLY_PURE_TRANSITION_CHECKS"),
            "projection_is_authority": False, **BOUNDARY}
    return {**body, "explanation_root": root(body)}


def explain_context_selection(*, scenario: str, requested_rule_ids: list[str],
                              variables: dict[str, Any]) -> dict[str, Any]:
    library = mediation_library()
    triggers_by_scenario = library["scenario_triggers"]
    require(scenario in triggers_by_scenario, "PIPPI_CONTEXT_SCENARIO_UNKNOWN")
    requested = _strings(requested_rule_ids, "PIPPI_CONTEXT_RULE_INVALID")
    rules = {row["rule_id"]: row for row in library["rules"]}
    require(set(requested) <= set(rules), "PIPPI_CONTEXT_RULE_INVALID")
    triggers = set(triggers_by_scenario[scenario])
    required = sorted(row["rule_id"] for row in library["rules"]
                      if triggers.intersection(row["triggers"]))
    selected = sorted(set(required) | set(requested))
    require(type(variables) is dict and all(type(key) is str and key for key in variables),
            "PIPPI_CONTEXT_VARIABLES_INVALID")
    reason_paths = [{"rule_id": item,
                     "reason": "SCENARIO_REQUIRED" if item in required else "EXPLICIT_REQUEST",
                     "matched_triggers": sorted(triggers.intersection(rules[item]["triggers"]))}
                    for item in selected]
    body = {"schema": "mosaic.ucm.pippi-context-selection-explanation.v0.1",
            "scenario": scenario, "scenario_triggers": sorted(triggers),
            "requested_rule_ids": requested, "required_rule_ids": required,
            "selected_rule_ids": selected, "reason_paths": reason_paths,
            "exact_context": [rules[item]["exact_context"] for item in selected],
            "variables": deepcopy(variables),
            "mediation_library_root": library["mediation_library_root"], **BOUNDARY}
    return {**body, "context_selection_root": root(body)}


def build_credential_reference(*, provider_id: str, account_identity: str,
                               scopes: list[str], secret_handle: str,
                               storage_policy_root: str,
                               expires_at_epoch: int | None) -> dict[str, Any]:
    _ident(provider_id, "PIPPI_CREDENTIAL_PROVIDER_INVALID")
    _ident(account_identity, "PIPPI_CREDENTIAL_ACCOUNT_INVALID")
    scopes = _strings(scopes, "PIPPI_CREDENTIAL_SCOPES_INVALID")
    _ident(secret_handle, "PIPPI_CREDENTIAL_HANDLE_INVALID")
    require(secret_handle.startswith("pippi-credential://")
            and not any(mark in secret_handle.casefold() for mark in
                        ("token=", "password=", "secret=", "private=")),
            "PIPPI_CREDENTIAL_HANDLE_INVALID")
    _sha(storage_policy_root, "PIPPI_CREDENTIAL_STORAGE_POLICY_ROOT_INVALID")
    require(expires_at_epoch is None or type(expires_at_epoch) is int and expires_at_epoch >= 0,
            "PIPPI_CREDENTIAL_EXPIRY_INVALID")
    body = {"schema": "mosaic.ucm.pippi-credential-reference.v0.1",
            "provider_id": provider_id, "account_identity": account_identity,
            "scopes": scopes, "secret_handle": secret_handle,
            "storage_policy_root": storage_policy_root,
            "expires_at_epoch": expires_at_epoch,
            "secret_material_present": False, "portable": False,
            "dispatch_authorized": False, **BOUNDARY}
    return {**body, "credential_reference_root": root(body)}


def credential_broker_policy() -> dict[str, Any]:
    body = {"schema": "mosaic.ucm.pippi-credential-broker-policy.v0.1",
            "providers": ["GITHUB", "MEGA", "SFTP", "WEBDAV", "GENERIC_HTTPS"],
            "storage_modes": ["LOCAL_ENCRYPTED_VAULT", "OS_CREDENTIAL_WRAPPER", "HARDWARE_KEY"],
            "portable_material": ["PUBLIC_KEYS", "MOSAIC_ID_PASSPORTS", "OPAQUE_CREDENTIAL_REFERENCES"],
            "forbidden_portable_material": ["PASSWORDS", "TOKENS", "PRIVATE_KEYS", "IPC_KEYS"],
            "required_cryptography": ["ARGON2ID_OR_SCRYPT", "AEAD", "ED25519"],
            "semantic_encoding_is_not_encryption": True,
            "provider_effects_require_gateway": True, **BOUNDARY}
    return {**body, "credential_broker_policy_root": root(body)}


def build_collaborator_binding(*, passport: dict[str, Any],
                               dkn_namespace: str, dkn_epoch: int,
                               stable_nonce: str = "mosaic.ucm.v0.1") -> dict[str, Any]:
    """Bind a verified MosaicID public identity to a DKN collaboration lane."""
    identity = verify_passport(passport)
    _ident(dkn_namespace, "PIPPI_COLLABORATOR_DKN_NAMESPACE_INVALID")
    require(type(dkn_epoch) is int and dkn_epoch >= 0,
            "PIPPI_COLLABORATOR_DKN_EPOCH_INVALID")
    require(stable_nonce == "mosaic.ucm.v0.1",
            "PIPPI_COLLABORATOR_STABLE_NONCE_INVALID")
    body = {"schema": "mosaic.ucm.pippi-collaborator-binding.v0.1",
            "mosaic_id": identity["mosaic_id"],
            "passport_sha256": identity["passport_sha256"],
            "public_key_hex": identity["public_key_hex"],
            "dkn": {"namespace": dkn_namespace, "epoch": dkn_epoch,
                    "stable_nonce": stable_nonce},
            "possession_proved": False, "authority_granted": False,
            **BOUNDARY}
    return {**body, "collaborator_binding_root": root(body)}


def _verify_ed25519(public_key_hex: str, signature_hex: str, message: bytes, code: str) -> None:
    validate_signing_key(public_key_hex)
    require(type(signature_hex) is str and len(signature_hex) == 128
            and all(ch in "0123456789abcdef" for ch in signature_hex), code)
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex)).verify(
            bytes.fromhex(signature_hex), message)
    except (ValueError, TypeError, ImportError) as error:
        require(False, code, detail=type(error).__name__)
    except Exception as error:
        require(False, code, detail=type(error).__name__)


def change_capsule_signing_body(*, base_root: str, result_root: str,
                                changed_objects: list[dict[str, Any]],
                                acceptance_case_roots: list[str],
                                standard_roots: list[str], policy_pack_roots: list[str],
                                author_identity_root: str, author_public_key_hex: str,
                                dkn_namespace: str, dkn_epoch: int, revision: str,
                                stable_nonce: str = "mosaic.ucm.v0.1") -> dict[str, Any]:
    _sha(base_root, "PIPPI_CHANGE_BASE_ROOT_INVALID")
    _sha(result_root, "PIPPI_CHANGE_RESULT_ROOT_INVALID")
    require(base_root != result_root, "PIPPI_CHANGE_NO_STATE_DELTA")
    require(type(changed_objects) is list and bool(changed_objects), "PIPPI_CHANGE_OBJECTS_INVALID")
    objects = []
    for raw in changed_objects:
        row = exact_keys(raw, {"path", "before_sha256", "after_sha256", "semantic_role"})
        _ident(row["path"], "PIPPI_CHANGE_PATH_INVALID")
        require("\\" not in row["path"] and not row["path"].startswith("/")
                and ".." not in row["path"].split("/"), "PIPPI_CHANGE_PATH_INVALID")
        _sha(row["before_sha256"], "PIPPI_CHANGE_OBJECT_HASH_INVALID")
        _sha(row["after_sha256"], "PIPPI_CHANGE_OBJECT_HASH_INVALID")
        require(row["before_sha256"] != row["after_sha256"], "PIPPI_CHANGE_OBJECT_UNCHANGED")
        _ident(row["semantic_role"], "PIPPI_CHANGE_OBJECT_ROLE_INVALID")
        objects.append(deepcopy(row))
    require(objects == sorted(objects, key=lambda row: row["path"])
            and len({row["path"].casefold() for row in objects}) == len(objects),
            "PIPPI_CHANGE_OBJECTS_INVALID")
    cases = _strings(acceptance_case_roots, "PIPPI_CHANGE_CASE_ROOT_INVALID", roots=True)
    standards = _strings(standard_roots, "PIPPI_CHANGE_STANDARD_ROOT_INVALID", roots=True)
    policies = _strings(policy_pack_roots, "PIPPI_CHANGE_POLICY_ROOT_INVALID", roots=True)
    author_identity_root = _identity_from_key(
        public_key_hex=author_public_key_hex,
        declared_identity_root=author_identity_root,
        code="PIPPI_CHANGE_AUTHOR_IDENTITY_KEY_MISMATCH")
    _ident(dkn_namespace, "PIPPI_CHANGE_DKN_NAMESPACE_INVALID")
    require(type(dkn_epoch) is int and dkn_epoch >= 0, "PIPPI_CHANGE_DKN_EPOCH_INVALID")
    require(type(revision) is str and len(revision) == 4 and revision.startswith("r")
            and revision[1:].isdigit(), "PIPPI_CHANGE_REVISION_INVALID")
    require(stable_nonce == "mosaic.ucm.v0.1", "PIPPI_CHANGE_STABLE_NONCE_INVALID")
    return {"schema": "mosaic.ucm.pippi-constitutional-change-signing-body.v0.1",
            "base_root": base_root, "result_root": result_root,
            "changed_objects": objects, "acceptance_case_roots": cases,
            "standard_roots": standards, "policy_pack_roots": policies,
            "author_identity_root": author_identity_root,
            "author_public_key_hex": author_public_key_hex,
            "dkn": {"namespace": dkn_namespace, "epoch": dkn_epoch,
                    "stable_nonce": stable_nonce, "revision": revision},
            "effect_authorized": False, **BOUNDARY}


def build_signed_change_capsule(*, signature_hex: str, **fields: Any) -> dict[str, Any]:
    signing = change_capsule_signing_body(**fields)
    _verify_ed25519(signing["author_public_key_hex"], signature_hex,
                    canonical_bytes(signing), "PIPPI_CHANGE_SIGNATURE_INVALID")
    body = {"schema": CHANGE_SCHEMA, "signing_body": signing,
            "signature_algorithm": "Ed25519", "signature_hex": signature_hex,
            "signature_status": "PASS", "import_status": "PROPOSAL_ONLY",
            "canonical_replacement_authorized": False, **BOUNDARY}
    return {**body, "change_capsule_root": root(body)}


def validate_signed_change_capsule(value: Any) -> dict[str, Any]:
    require(type(value) is dict and value.get("schema") == CHANGE_SCHEMA,
            "PIPPI_CHANGE_CAPSULE_INVALID")
    signing = value.get("signing_body")
    require(type(signing) is dict, "PIPPI_CHANGE_CAPSULE_INVALID")
    expected_signing = change_capsule_signing_body(
        base_root=signing.get("base_root"), result_root=signing.get("result_root"),
        changed_objects=signing.get("changed_objects"),
        acceptance_case_roots=signing.get("acceptance_case_roots"),
        standard_roots=signing.get("standard_roots"),
        policy_pack_roots=signing.get("policy_pack_roots"),
        author_identity_root=signing.get("author_identity_root"),
        author_public_key_hex=signing.get("author_public_key_hex"),
        dkn_namespace=signing.get("dkn", {}).get("namespace"),
        dkn_epoch=signing.get("dkn", {}).get("epoch"),
        revision=signing.get("dkn", {}).get("revision"),
        stable_nonce=signing.get("dkn", {}).get("stable_nonce"))
    expected = build_signed_change_capsule(signature_hex=value.get("signature_hex"),
        base_root=expected_signing["base_root"], result_root=expected_signing["result_root"],
        changed_objects=expected_signing["changed_objects"],
        acceptance_case_roots=expected_signing["acceptance_case_roots"],
        standard_roots=expected_signing["standard_roots"],
        policy_pack_roots=expected_signing["policy_pack_roots"],
        author_identity_root=expected_signing["author_identity_root"],
        author_public_key_hex=expected_signing["author_public_key_hex"],
        dkn_namespace=expected_signing["dkn"]["namespace"],
        dkn_epoch=expected_signing["dkn"]["epoch"],
        revision=expected_signing["dkn"]["revision"],
        stable_nonce=expected_signing["dkn"]["stable_nonce"])
    require(value == expected, "PIPPI_CHANGE_CAPSULE_INVALID")
    return deepcopy(expected)


def build_storage_locator(*, provider_id: str, locator: str,
                          artifact_sha256: str, provider_account_root: str,
                          credential_reference_root: str) -> dict[str, Any]:
    require(provider_id in {"GITHUB", "MEGA", "SFTP", "WEBDAV", "GENERIC_HTTPS"},
            "PIPPI_STORAGE_PROVIDER_INVALID")
    _ident(locator, "PIPPI_STORAGE_LOCATOR_INVALID", maximum=1024)
    require(not any(mark in locator.casefold() for mark in
                    ("token=", "password=", "secret=", "private=")),
            "PIPPI_STORAGE_LOCATOR_CONTAINS_CREDENTIAL")
    _sha(artifact_sha256, "PIPPI_STORAGE_ARTIFACT_HASH_INVALID")
    _sha(provider_account_root, "PIPPI_STORAGE_ACCOUNT_ROOT_INVALID")
    _sha(credential_reference_root, "PIPPI_STORAGE_CREDENTIAL_ROOT_INVALID")
    body = {"schema": "mosaic.ucm.pippi-storage-locator.v0.1",
            "provider_id": provider_id, "locator": locator,
            "artifact_sha256": artifact_sha256,
            "provider_account_root": provider_account_root,
            "credential_reference_root": credential_reference_root,
            "storage_is_identity_authority": False, "dispatch_authorized": False,
            **BOUNDARY}
    return validate_storage_locator({**body, "storage_locator_root": root(body)})


def validate_storage_locator(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "provider_id", "locator",
        "artifact_sha256", "provider_account_root", "credential_reference_root",
        "storage_is_identity_authority", "dispatch_authorized", *BOUNDARY,
        "storage_locator_root"})
    require(item["schema"] == "mosaic.ucm.pippi-storage-locator.v0.1"
            and item["provider_id"] in {"GITHUB", "MEGA", "SFTP", "WEBDAV",
                                                "GENERIC_HTTPS"}
            and item["storage_is_identity_authority"] is False
            and item["dispatch_authorized"] is False
            and {key: item[key] for key in BOUNDARY} == BOUNDARY,
            "PIPPI_STORAGE_LOCATOR_INVALID")
    _ident(item["locator"], "PIPPI_STORAGE_LOCATOR_INVALID", maximum=1024)
    require(not any(mark in item["locator"].casefold() for mark in
                    ("token=", "password=", "secret=", "private=")),
            "PIPPI_STORAGE_LOCATOR_CONTAINS_CREDENTIAL")
    _sha(item["artifact_sha256"], "PIPPI_STORAGE_ARTIFACT_HASH_INVALID")
    _sha(item["provider_account_root"], "PIPPI_STORAGE_ACCOUNT_ROOT_INVALID")
    _sha(item["credential_reference_root"],
         "PIPPI_STORAGE_CREDENTIAL_ROOT_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items()
            if key != "storage_locator_root"}
    require(item["storage_locator_root"] == root(body),
            "PIPPI_STORAGE_LOCATOR_INVALID")
    return deepcopy(item)


def publication_receipt_signing_body(*, artifact_sha256: str, state_root: str,
                                     semantic_root: str, metadata_root: str,
                                     governance_root: str, dkn_binding_root: str,
                                     storage_locator: dict[str, Any],
                                     publisher_identity_root: str,
                                     publisher_public_key_hex: str,
                                     published_epoch: int) -> dict[str, Any]:
    for value in (artifact_sha256, state_root, semantic_root, metadata_root,
                  governance_root, dkn_binding_root):
        _sha(value, "PIPPI_PUBLICATION_COMMITMENT_ROOT_INVALID")
    storage_locator = validate_storage_locator(storage_locator)
    require(storage_locator["artifact_sha256"] == artifact_sha256,
            "PIPPI_PUBLICATION_LOCATOR_ARTIFACT_MISMATCH")
    publisher_identity_root = _identity_from_key(
        public_key_hex=publisher_public_key_hex,
        declared_identity_root=publisher_identity_root,
        code="PIPPI_PUBLICATION_IDENTITY_KEY_MISMATCH")
    require(type(published_epoch) is int and published_epoch >= 0,
            "PIPPI_PUBLICATION_EPOCH_INVALID")
    return {"schema": "mosaic.ucm.pippi-storage-publication-signing-body.v0.1",
            "artifact_sha256": artifact_sha256,
            "commitments": {"state_root": state_root, "semantic_root": semantic_root,
                            "metadata_root": metadata_root, "governance_root": governance_root},
            "dkn_binding_root": dkn_binding_root,
            "storage_locator_root": storage_locator["storage_locator_root"],
            "publisher_identity_root": publisher_identity_root,
            "publisher_public_key_hex": publisher_public_key_hex,
            "published_epoch": published_epoch,
            "receipt_grants_authority": False, **BOUNDARY}


def build_signed_publication_receipt(*, signature_hex: str, **fields: Any) -> dict[str, Any]:
    signing = publication_receipt_signing_body(**fields)
    _verify_ed25519(signing["publisher_public_key_hex"], signature_hex,
                    canonical_bytes(signing), "PIPPI_PUBLICATION_SIGNATURE_INVALID")
    body = {"schema": PUBLICATION_SCHEMA, "signing_body": signing,
            "signature_algorithm": "Ed25519", "signature_hex": signature_hex,
            "signature_status": "PASS", "provider_receipt_status": "OBSERVED_SIGNED",
            **BOUNDARY}
    return {**body, "publication_receipt_root": root(body)}


def validate_signed_publication_receipt(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "signing_body", "signature_algorithm",
        "signature_hex", "signature_status", "provider_receipt_status", *BOUNDARY,
        "publication_receipt_root"})
    require(item["schema"] == PUBLICATION_SCHEMA
            and item["signature_algorithm"] == "Ed25519"
            and item["signature_status"] == "PASS"
            and item["provider_receipt_status"] == "OBSERVED_SIGNED",
            "PIPPI_PUBLICATION_RECEIPT_INVALID")
    signing = exact_keys(item["signing_body"], {"schema", "artifact_sha256",
        "commitments", "dkn_binding_root", "storage_locator_root",
        "publisher_identity_root", "publisher_public_key_hex", "published_epoch",
        "receipt_grants_authority", *BOUNDARY})
    require(signing["schema"]
            == "mosaic.ucm.pippi-storage-publication-signing-body.v0.1"
            and signing["receipt_grants_authority"] is False
            and {key: signing[key] for key in BOUNDARY} == BOUNDARY
            and type(signing["published_epoch"]) is int
            and signing["published_epoch"] >= 0,
            "PIPPI_PUBLICATION_RECEIPT_INVALID")
    commitments = exact_keys(signing["commitments"], {
        "state_root", "semantic_root", "metadata_root", "governance_root"})
    _identity_from_key(public_key_hex=signing["publisher_public_key_hex"],
                       declared_identity_root=signing["publisher_identity_root"],
                       code="PIPPI_PUBLICATION_IDENTITY_KEY_MISMATCH")
    for value_root in (signing["artifact_sha256"], signing["dkn_binding_root"],
                       signing["storage_locator_root"], *commitments.values()):
        _sha(value_root, "PIPPI_PUBLICATION_RECEIPT_INVALID")
    _verify_ed25519(signing["publisher_public_key_hex"], item["signature_hex"],
                    canonical_bytes(signing), "PIPPI_PUBLICATION_SIGNATURE_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items()
            if key != "publication_receipt_root"}
    require(item["publication_receipt_root"] == root(body),
            "PIPPI_PUBLICATION_RECEIPT_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "PIPPI_PUBLICATION_RECEIPT_INVALID")
    return deepcopy(item)


def retrieval_receipt_signing_body(*, publication_receipt: dict[str, Any],
                                   retrieved_artifact_path: str,
                                   retriever_identity_root: str,
                                   retriever_public_key_hex: str,
                                   retrieved_epoch: int) -> dict[str, Any]:
    publication = validate_signed_publication_receipt(publication_receipt)
    publication_signing = publication["signing_body"]
    observed_sha256 = _file_sha256(retrieved_artifact_path)
    require(observed_sha256 == publication_signing["artifact_sha256"],
            "PIPPI_RETRIEVAL_ARTIFACT_HASH_MISMATCH")
    retriever_identity_root = _identity_from_key(
        public_key_hex=retriever_public_key_hex,
        declared_identity_root=retriever_identity_root,
        code="PIPPI_RETRIEVAL_IDENTITY_KEY_MISMATCH")
    require(type(retrieved_epoch) is int and retrieved_epoch >= 0,
            "PIPPI_RETRIEVAL_EPOCH_INVALID")
    return {"schema": "mosaic.ucm.pippi-storage-retrieval-signing-body.v0.1",
            "publication_receipt_root": publication["publication_receipt_root"],
            "artifact_sha256": observed_sha256,
            "storage_locator_root": publication_signing["storage_locator_root"],
            "retriever_identity_root": retriever_identity_root,
            "retriever_public_key_hex": retriever_public_key_hex,
            "retrieved_epoch": retrieved_epoch,
            "artifact_verified_after_retrieval": True,
            "storage_is_identity_authority": False, **BOUNDARY}


def build_signed_retrieval_receipt(*, signature_hex: str, **fields: Any) -> dict[str, Any]:
    signing = retrieval_receipt_signing_body(**fields)
    _verify_ed25519(signing["retriever_public_key_hex"], signature_hex,
                    canonical_bytes(signing), "PIPPI_RETRIEVAL_SIGNATURE_INVALID")
    body = {"schema": RETRIEVAL_SCHEMA, "signing_body": signing,
            "signature_algorithm": "Ed25519", "signature_hex": signature_hex,
            "signature_status": "PASS", "custody_status": "RETRIEVED_AND_HASH_VERIFIED",
            **BOUNDARY}
    return {**body, "retrieval_receipt_root": root(body)}


def validate_signed_retrieval_receipt(value: Any, *,
                                      publication_receipt: dict[str, Any]) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "signing_body", "signature_algorithm",
        "signature_hex", "signature_status", "custody_status", *BOUNDARY,
        "retrieval_receipt_root"})
    require(item["schema"] == RETRIEVAL_SCHEMA
            and item["signature_algorithm"] == "Ed25519"
            and item["signature_status"] == "PASS"
            and item["custody_status"] == "RETRIEVED_AND_HASH_VERIFIED"
            and {key: item[key] for key in BOUNDARY} == BOUNDARY,
            "PIPPI_RETRIEVAL_RECEIPT_INVALID")
    signing = exact_keys(item["signing_body"], {"schema",
        "publication_receipt_root", "artifact_sha256", "storage_locator_root",
        "retriever_identity_root", "retriever_public_key_hex", "retrieved_epoch",
        "artifact_verified_after_retrieval", "storage_is_identity_authority",
        *BOUNDARY})
    require(signing["schema"]
            == "mosaic.ucm.pippi-storage-retrieval-signing-body.v0.1"
            and signing["artifact_verified_after_retrieval"] is True
            and signing["storage_is_identity_authority"] is False
            and type(signing["retrieved_epoch"]) is int
            and signing["retrieved_epoch"] >= 0
            and {key: signing[key] for key in BOUNDARY} == BOUNDARY,
            "PIPPI_RETRIEVAL_RECEIPT_INVALID")
    publication = validate_signed_publication_receipt(publication_receipt)
    publication_signing = publication["signing_body"]
    require(signing["publication_receipt_root"]
            == publication["publication_receipt_root"],
            "PIPPI_RETRIEVAL_PUBLICATION_MISMATCH")
    require(signing["artifact_sha256"] == publication_signing["artifact_sha256"]
            and signing["storage_locator_root"]
            == publication_signing["storage_locator_root"],
            "PIPPI_RETRIEVAL_PUBLICATION_MISMATCH")
    _identity_from_key(public_key_hex=signing["retriever_public_key_hex"],
                       declared_identity_root=signing["retriever_identity_root"],
                       code="PIPPI_RETRIEVAL_IDENTITY_KEY_MISMATCH")
    for value_root in (signing["publication_receipt_root"],
                       signing["artifact_sha256"], signing["storage_locator_root"]):
        _sha(value_root, "PIPPI_RETRIEVAL_RECEIPT_INVALID")
    _verify_ed25519(signing["retriever_public_key_hex"], item["signature_hex"],
                    canonical_bytes(signing), "PIPPI_RETRIEVAL_SIGNATURE_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items()
            if key != "retrieval_receipt_root"}
    require(item["retrieval_receipt_root"] == root(body),
            "PIPPI_RETRIEVAL_RECEIPT_INVALID")
    return deepcopy(item)


def build_ccp_transition_binding(*, transition_id: str,
                                 ccp_evaluation: dict[str, Any] | None) -> dict[str, Any]:
    model = build_pipeline_model()
    matches = [row for row in model["transitions"] if row["transition_id"] == transition_id]
    require(len(matches) == 1, "PIPPI_PIPELINE_TRANSITION_UNKNOWN")
    transition = matches[0]
    required = transition["ccp_current_use"] == "REQUIRED"
    if not required:
        require(ccp_evaluation is None, "PIPPI_CCP_EVALUATION_UNEXPECTED")
        subject_root = jurisdiction_profile_root = evidence_snapshot_root = None
        current_use_decision_root = None
        current_use_status = "NOT_REQUIRED"
        ready = True
    else:
        evaluation = exact_keys(ccp_evaluation, {"decision", "current_use_snapshot",
            "evidence_snapshot", "jurisdiction_profile", "enforcement_perimeter",
            "correspondence", "expected_anchors"})
        anchors = exact_keys(evaluation["expected_anchors"], {
            "expected_subject_root", "expected_jurisdiction_profile_root",
            "expected_enforcement_perimeter_root", "expected_correspondence_root",
            "expected_policy_root", "expected_schema_registry_root",
            "expected_trust_root", "expected_checkpoint_root"})
        from .ccp_admissibility import (validate_admissibility_decision,
                                        validate_current_use_snapshot)
        checked = validate_admissibility_decision(
            evaluation["decision"],
            current_use_snapshot=evaluation["current_use_snapshot"],
            evidence_snapshot=evaluation["evidence_snapshot"],
            jurisdiction_profile=evaluation["jurisdiction_profile"],
            enforcement_perimeter=evaluation["enforcement_perimeter"],
            correspondence=evaluation["correspondence"], **anchors)
        use = validate_current_use_snapshot(evaluation["current_use_snapshot"])
        require(use["operation"] == transition_id,
                "PIPPI_CCP_TRANSITION_OPERATION_MISMATCH")
        subject_root = use["subject_root"]
        jurisdiction_profile_root = checked["jurisdiction_profile_root"]
        evidence_snapshot_root = checked["evidence_snapshot_root"]
        current_use_decision_root = checked["decision_root"]
        current_use_status = checked["decision"]
        ready = current_use_status == "ADMIT"
    body = {"schema": "mosaic.ucm.pippi-ccp-transition-binding.v0.1",
            "pipeline_model_root": model["pipeline_model_root"],
            "transition_id": transition_id, "subject_root": subject_root,
            "jurisdiction_profile_root": jurisdiction_profile_root,
            "evidence_snapshot_root": evidence_snapshot_root,
            "current_use_decision_root": current_use_decision_root,
            "current_use_status": current_use_status,
            "ccp_required": required, "transition_ready": ready,
            "effect_authorized": False,
            "status": "PASS_READY" if ready else "HELD_BY_CURRENT_USE_ADMISSIBILITY",
            **BOUNDARY}
    return {**body, "ccp_transition_binding_root": root(body)}


__all__ = [
    "build_constitutional_standards_atlas", "validate_constitutional_standards_atlas",
    "build_pipeline_model", "validate_pipeline_model", "explain_standard_rule",
    "explain_pipeline_transition", "explain_context_selection",
    "build_credential_reference", "credential_broker_policy", "build_collaborator_binding",
    "change_capsule_signing_body", "build_signed_change_capsule",
    "validate_signed_change_capsule", "build_storage_locator", "validate_storage_locator",
    "publication_receipt_signing_body", "build_signed_publication_receipt",
    "validate_signed_publication_receipt",
    "retrieval_receipt_signing_body", "build_signed_retrieval_receipt",
    "validate_signed_retrieval_receipt",
    "build_ccp_transition_binding",
]

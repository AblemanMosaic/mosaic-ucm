"""Portable P/PPI project and process governance records.

This module joins UCM's existing planning, standards, identity, journal, and
THR/CAS machinery without becoming an executor.  Every constructor is pure.
The courthouse may consume the resulting records, but only its admitted
executor and native receipts can establish effects.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import canonical_bytes, exact_keys, require, require_root, root

from .development_standards import (
    CLASSES,
    EVALUATION_SCHEMA,
    validate_standards_catalog,
)
from .governance import verify_external_approval
from .identity import mosaic_id, verify_passport
from .system import BOUNDARY
from .thr_cas import build_thr_manifest


LOCALITY_SCHEMA = "mosaic.ucm.process-locality-binding.v0.1"
EXECUTION_CAPSULE_SCHEMA = "mosaic.ucm.exact-execution-capsule.v0.1"
ARTIFACT_PRODUCER_SCHEMA = "mosaic.ucm.artifact-producer-receipt.v0.1"
BASELINE_SCHEMA = "mosaic.ucm.process-baseline.v0.1"
MILESTONE_SCHEMA = "mosaic.ucm.process-milestone.v0.1"
ASSESSMENT_SCHEMA = "mosaic.ucm.process-milestone-assessment.v0.1"
DECISION_SCHEMA = "mosaic.ucm.process-milestone-decision.v0.1"
CHECKPOINT_SCHEMA = "mosaic.ucm.process-checkpoint.v0.1"
REPLAN_SCHEMA = "mosaic.ucm.process-replan.v0.1"
SCHEDULE_SCHEMA = "mosaic.ucm.process-standards-schedule.v0.1"
OBSERVATORY_SCHEMA = "mosaic.ucm.process-observatory.v0.1"
COURTHOUSE_BINDING_SCHEMA = "mosaic.ucm.process-courthouse-binding.v0.1"

LIFECYCLE_STATES = {
    "PROPOSED", "READY", "ACTIVE", "BLOCKED", "AWAITING_ACCEPTANCE",
    "ACCEPTED", "SUPERSEDED",
}
TRANSITIONS = {
    None: {"PROPOSED"},
    "PROPOSED": {"READY", "BLOCKED", "SUPERSEDED"},
    "READY": {"ACTIVE", "BLOCKED", "SUPERSEDED"},
    "ACTIVE": {"BLOCKED", "AWAITING_ACCEPTANCE", "SUPERSEDED"},
    "BLOCKED": {"READY", "ACTIVE", "SUPERSEDED"},
    "AWAITING_ACCEPTANCE": {"ACCEPTED", "BLOCKED", "SUPERSEDED"},
    "ACCEPTED": {"SUPERSEDED"},
    "SUPERSEDED": set(),
}
EVIDENCE_ROLES = {"STATIC", "TARGETED", "COURT", "QUALIFICATION", "WITNESS", "REVIEW"}
MILESTONE_DECISIONS = {"ACCEPTED", "REFUSED"}
REPLAN_DISPOSITIONS = {"RETAINED", "RESOLVED", "DEFERRED"}
METADATA_ROLES = {"SEMANTIC", "GOVERNANCE", "CUSTODY", "PRESENTATION"}
HASH_PROFILE = {
    "H_s": "EXACT_RECORD_BYTES",
    "H_c": "POLICIES_STANDARDS_ACCEPTANCE_AND_CEILING",
    "H_m": "OBJECTIVE_REQUIREMENTS_MILESTONES_AND_DECLARED_INTERPRETATION",
    "H_j": "DKN_LOCALITY_IDENTITIES_AND_SESSION",
    "H_r": "JOURNAL_EVIDENCE_AND_APPROVAL_RECEIPTS",
    "h_body": "COMPLETE_ENVELOPE_INTEGRITY",
    "metadata_roles": {
        "SEMANTIC": ["objective", "requirement_roots", "deliverable_ids"],
        "GOVERNANCE": ["policy_roots", "standards_catalog_root", "responsibilities"],
        "CUSTODY": ["subject_root", "source_manifest_root", "software_generation_root",
                    "execution_capsule_roots"],
        "PRESENTATION": ["project_id"],
    },
}


def _identifier(value: Any, code: str, *, maximum: int = 192) -> str:
    require(type(value) is str and value == value.strip() and 0 < len(value) <= maximum
            and all(ch.isalnum() or ch in "._:-/" for ch in value), code)
    return value


def _text(value: Any, code: str, *, maximum: int = 4096) -> str:
    require(type(value) is str and value == value.strip() and 0 < len(value) <= maximum,
            code)
    return value


def _ids(value: Any, code: str, *, allow_empty: bool = True) -> list[str]:
    require(type(value) is list and value == sorted(set(value))
            and (allow_empty or bool(value)), code)
    return [_identifier(item, code) for item in value]


def _roots(value: Any, code: str, *, allow_empty: bool = True) -> list[str]:
    require(type(value) is list and value == sorted(set(value))
            and (allow_empty or bool(value)), code)
    return [require_root(item) for item in value]


def _optional_root(value: Any) -> str | None:
    return None if value is None else require_root(value)


def _ceiling(value: Any) -> dict[str, Any]:
    require(value == BOUNDARY, "PROCESS_AUTHORITY_CEILING_INVALID")
    return deepcopy(BOUNDARY)


def _relative_path(value: Any, code: str) -> str:
    require(type(value) is str and value == value.strip() and value
            and "\\" not in value and not value.startswith("/")
            and all(part not in {"", ".", ".."} for part in value.split("/")), code)
    return value


def _rooted(value: Any, *, schema: str, root_field: str, code: str) -> dict[str, Any]:
    require(type(value) is dict and value.get("schema") == schema, code)
    body = {key: deepcopy(item) for key, item in value.items() if key != root_field}
    require(value.get(root_field) == root(body), code)
    require({key: value.get(key) for key in BOUNDARY} == BOUNDARY,
            "PROCESS_AUTHORITY_CEILING_INVALID")
    return deepcopy(value)


def build_dkn_locality_binding(*, phase_code: str, authority_public_key_hex: str,
                               semantic_namespace: str, universe_root: str,
                               namespace_policy_root: str, passport: dict[str, Any] | None,
                               possession_receipt_root: str | None,
                               local_admission_root: str | None) -> dict[str, Any]:
    """Build a DKN-compatible locality commitment under an explicit byte profile.

    The source formula is BLAKE3(phase_code || authority_pubkey).  UCM pins the
    concrete encoding used here: UTF-8 phase bytes followed by the raw 32-byte
    public key.  This record is locality and identity context, never permission.
    """
    _identifier(phase_code, "PROCESS_DKN_PHASE_CODE_INVALID")
    _identifier(semantic_namespace, "PROCESS_DKN_NAMESPACE_INVALID", maximum=512)
    require_root(universe_root)
    require_root(namespace_policy_root)
    require(type(authority_public_key_hex) is str and len(authority_public_key_hex) == 64,
            "PROCESS_DKN_PUBLIC_KEY_INVALID")
    try:
        public_key = bytes.fromhex(authority_public_key_hex)
    except ValueError as error:
        raise ValueError("PROCESS_DKN_PUBLIC_KEY_INVALID") from error
    require(len(public_key) == 32, "PROCESS_DKN_PUBLIC_KEY_INVALID")
    try:
        from blake3 import blake3
    except ImportError as error:
        raise ValueError("PROCESS_DKN_BLAKE3_DEPENDENCY_MISSING") from error
    dimension_id = blake3(phase_code.encode("utf-8") + public_key).hexdigest()
    identity_id = mosaic_id(authority_public_key_hex)
    passport_root = None
    passport_status = "NOT_SUPPLIED"
    if passport is not None:
        inspection = verify_passport(passport, expected_mosaic_id=identity_id)
        require(inspection["public_key_hex"] == authority_public_key_hex,
                "PROCESS_DKN_PASSPORT_KEY_MISMATCH")
        passport_root = inspection["passport_sha256"]
        passport_status = "PASS_SELF_CERTIFIED"
    body = {
        "schema": LOCALITY_SCHEMA,
        "profile_id": "DKN.AUTHORITY_KEYED_DIMENSION.UTF8_RAW_ED25519.V1",
        "profile_source_statement": "dimension_id=BLAKE3(UTF8(phase_code)||raw_authority_pubkey)",
        "phase_code": phase_code,
        "authority_public_key_hex": authority_public_key_hex,
        "authority_mosaic_id": identity_id,
        "dimension_id": dimension_id,
        "semantic_namespace": semantic_namespace,
        "universe_root": universe_root,
        "namespace_policy_root": namespace_policy_root,
        "passport_root": passport_root,
        "passport_status": passport_status,
        "possession_receipt_root": _optional_root(possession_receipt_root),
        "local_admission_root": _optional_root(local_admission_root),
        "namespace_authority_verified": False,
        "permission_granted": False,
        "non_claims": [
            "DIMENSION_HASH_DOES_NOT_GRANT_NAMESPACE_AUTHORITY",
            "PASSPORT_DOES_NOT_GRANT_PERMISSION",
            "LOCAL_ADMISSION_REQUIRES_EXTERNAL_VERIFICATION",
        ],
        **BOUNDARY,
    }
    return {**body, "locality_binding_root": root(body)}


def validate_dkn_locality_binding(value: Any) -> dict[str, Any]:
    item = _rooted(value, schema=LOCALITY_SCHEMA,
                   root_field="locality_binding_root", code="PROCESS_DKN_BINDING_INVALID")
    expected = build_dkn_locality_binding(
        phase_code=item["phase_code"],
        authority_public_key_hex=item["authority_public_key_hex"],
        semantic_namespace=item["semantic_namespace"],
        universe_root=item["universe_root"],
        namespace_policy_root=item["namespace_policy_root"],
        passport=None,
        possession_receipt_root=item["possession_receipt_root"],
        local_admission_root=item["local_admission_root"],
    )
    for field in ("profile_id", "profile_source_statement", "phase_code",
                  "authority_public_key_hex", "authority_mosaic_id", "dimension_id",
                  "semantic_namespace", "universe_root", "namespace_policy_root",
                  "possession_receipt_root", "local_admission_root",
                  "namespace_authority_verified", "permission_granted", "non_claims"):
        require(item[field] == expected[field], "PROCESS_DKN_BINDING_INVALID", detail=field)
    require(item["passport_status"] in {"NOT_SUPPLIED", "PASS_SELF_CERTIFIED"},
            "PROCESS_DKN_BINDING_INVALID")
    if item["passport_status"] == "NOT_SUPPLIED":
        require(item["passport_root"] is None, "PROCESS_DKN_BINDING_INVALID")
    else:
        require_root(item["passport_root"])
    return item


def build_exact_execution_capsule(*, capsule_id: str, executable_root: str,
                                  runner_root: str, argv: list[str], normalized_cwd: str,
                                  environment_projection: dict[str, str],
                                  dependencies: list[dict[str, Any]],
                                  missing_dependency_ids: list[str],
                                  exact_input_roots: list[str], policy_root: str,
                                  profile_root: str, authority_root: str,
                                  jurisdiction_root: str, effect_class: str,
                                  expected_write_paths: list[str],
                                  transaction_history_paths: list[str],
                                  adapter_root: str) -> dict[str, Any]:
    capsule_id = _identifier(capsule_id, "PROCESS_EXECUTION_CAPSULE_ID_INVALID")
    for value in (executable_root, runner_root, policy_root, profile_root,
                  authority_root, jurisdiction_root, adapter_root):
        require_root(value)
    require(type(argv) is list and bool(argv)
            and all(type(value) is str and value for value in argv),
            "PROCESS_EXECUTION_ARGV_INVALID")
    cwd = _relative_path(normalized_cwd, "PROCESS_EXECUTION_CWD_INVALID")
    require(type(environment_projection) is dict
            and all(type(key) is str and key and type(value) is str
                    for key, value in environment_projection.items()),
            "PROCESS_EXECUTION_ENVIRONMENT_INVALID")
    environment = {key: environment_projection[key] for key in sorted(environment_projection)}
    require(type(dependencies) is list, "PROCESS_EXECUTION_DEPENDENCIES_INVALID")
    normalized_dependencies = []
    seen_paths: set[str] = set()
    for raw in dependencies:
        item = exact_keys(raw, {"path", "sha256", "role"})
        path = _relative_path(item["path"], "PROCESS_EXECUTION_DEPENDENCY_PATH_INVALID")
        require(path not in seen_paths, "PROCESS_EXECUTION_DEPENDENCY_DUPLICATE")
        seen_paths.add(path)
        normalized_dependencies.append({
            "path": path,
            "sha256": require_root(item["sha256"]),
            "role": _identifier(item["role"], "PROCESS_EXECUTION_DEPENDENCY_ROLE_INVALID"),
        })
    normalized_dependencies.sort(key=lambda row: row["path"])
    missing = _ids(missing_dependency_ids, "PROCESS_EXECUTION_MISSING_DEPENDENCIES_INVALID")
    writes = [_relative_path(path, "PROCESS_EXECUTION_WRITE_PATH_INVALID")
              for path in expected_write_paths]
    require(writes == sorted(set(writes)), "PROCESS_EXECUTION_WRITE_PATHS_INVALID")
    history_paths = [_relative_path(path, "PROCESS_EXECUTION_HISTORY_PATH_INVALID")
                     for path in transaction_history_paths]
    require(history_paths == sorted(set(history_paths))
            and set(history_paths).issubset(writes),
            "PROCESS_EXECUTION_HISTORY_PATHS_INVALID")
    closure_status = "COMPLETE" if not missing else "INCOMPLETE"
    identity_material = {
        "capsule_id": capsule_id,
        "executable_root": executable_root,
        "runner_root": runner_root,
        "argv": deepcopy(argv),
        "normalized_cwd": cwd,
        "environment_projection": environment,
        "dependency_manifest_root": root(normalized_dependencies),
        "missing_dependency_ids": missing,
        "dependency_closure_status": closure_status,
        "exact_input_roots": _roots(exact_input_roots,
                                    "PROCESS_EXECUTION_INPUT_ROOTS_INVALID"),
        "policy_root": policy_root,
        "profile_root": profile_root,
        "authority_root": authority_root,
        "jurisdiction_root": jurisdiction_root,
        "effect_class": _identifier(effect_class, "PROCESS_EXECUTION_EFFECT_CLASS_INVALID"),
        "expected_write_paths": writes,
        "transaction_history_paths": history_paths,
        "adapter_root": adapter_root,
    }
    operation_identity_root = root(identity_material)
    body = {
        "schema": EXECUTION_CAPSULE_SCHEMA,
        **identity_material,
        "dependencies": normalized_dependencies,
        "missing_dependency_ids": missing,
        "dependency_closure_status": closure_status,
        "idempotency_material_root": operation_identity_root,
        "operation_identity_root": operation_identity_root,
        "artifact_producer_binding": {
            "field": "producer_operation_root",
            "expected_value": operation_identity_root,
            "covered_write_paths": writes,
        },
        "terminal_receipt_reusable": closure_status == "COMPLETE",
        "stale_receipt_rule": "ANY_BOUND_INPUT_CHANGE_REQUIRES_NEW_OPERATION_IDENTITY",
        "same_operation_divergence_rule": "SAME_OPERATION_DIFFERENT_BYTES_REFUSE",
        "successor_supersession_rule": "NEW_OPERATION_IDENTITY_AND_PREDECESSOR_HISTORY_REQUIRED",
        "legacy_artifact_migration_required": True,
        "execution_authorized": False,
        **BOUNDARY,
    }
    return {**body, "execution_capsule_root": root(body)}


def validate_exact_execution_capsule(value: Any) -> dict[str, Any]:
    item = _rooted(value, schema=EXECUTION_CAPSULE_SCHEMA,
                   root_field="execution_capsule_root",
                   code="PROCESS_EXECUTION_CAPSULE_INVALID")
    expected = build_exact_execution_capsule(
        capsule_id=item["capsule_id"], executable_root=item["executable_root"],
        runner_root=item["runner_root"], argv=item["argv"],
        normalized_cwd=item["normalized_cwd"],
        environment_projection=item["environment_projection"],
        dependencies=item["dependencies"],
        missing_dependency_ids=item["missing_dependency_ids"],
        exact_input_roots=item["exact_input_roots"], policy_root=item["policy_root"],
        profile_root=item["profile_root"], authority_root=item["authority_root"],
        jurisdiction_root=item["jurisdiction_root"], effect_class=item["effect_class"],
        expected_write_paths=item["expected_write_paths"],
        transaction_history_paths=item["transaction_history_paths"],
        adapter_root=item["adapter_root"],
    )
    require(item == expected, "PROCESS_EXECUTION_CAPSULE_INVALID")
    return item


def build_artifact_producer_receipt(*, artifact_path: str, artifact_sha256: str,
                                    producer_operation_root: str,
                                    predecessor_artifact_sha256: str | None,
                                    predecessor_producer_operation_root: str | None,
                                    transaction_history_path: str | None,
                                    supersession_kind: str) -> dict[str, Any]:
    path = _relative_path(artifact_path, "PROCESS_ARTIFACT_PATH_INVALID")
    require_root(artifact_sha256)
    require_root(producer_operation_root)
    predecessor_sha = _optional_root(predecessor_artifact_sha256)
    predecessor_operation = _optional_root(predecessor_producer_operation_root)
    history_path = (None if transaction_history_path is None else
                    _relative_path(transaction_history_path,
                                   "PROCESS_ARTIFACT_HISTORY_PATH_INVALID"))
    require(supersession_kind in {"INITIAL", "SUCCESSOR", "LEGACY_MIGRATION"},
            "PROCESS_ARTIFACT_SUPERSESSION_KIND_INVALID")
    if supersession_kind == "INITIAL":
        require(predecessor_sha is None and predecessor_operation is None
                and history_path is None, "PROCESS_ARTIFACT_INITIAL_LINEAGE_INVALID")
    elif supersession_kind == "SUCCESSOR":
        require(predecessor_sha is not None and predecessor_operation is not None
                and history_path is not None
                and predecessor_operation != producer_operation_root,
                "PROCESS_ARTIFACT_SUCCESSOR_LINEAGE_INVALID")
    else:
        require(predecessor_sha is not None and history_path is not None,
                "PROCESS_ARTIFACT_LEGACY_MIGRATION_INVALID")
    body = {
        "schema": ARTIFACT_PRODUCER_SCHEMA,
        "artifact_path": path,
        "artifact_sha256": artifact_sha256,
        "producer_operation_root": producer_operation_root,
        "predecessor_artifact_sha256": predecessor_sha,
        "predecessor_producer_operation_root": predecessor_operation,
        "transaction_history_path": history_path,
        "supersession_kind": supersession_kind,
        "same_operation_divergence_refused": True,
        "receipt_grants_authority": False,
        **BOUNDARY,
    }
    return {**body, "artifact_producer_receipt_root": root(body)}


def validate_artifact_producer_receipt(value: Any) -> dict[str, Any]:
    item = _rooted(value, schema=ARTIFACT_PRODUCER_SCHEMA,
                   root_field="artifact_producer_receipt_root",
                   code="PROCESS_ARTIFACT_PRODUCER_RECEIPT_INVALID")
    exact_keys(item, {
        "schema", "artifact_path", "artifact_sha256", "producer_operation_root",
        "predecessor_artifact_sha256", "predecessor_producer_operation_root",
        "transaction_history_path", "supersession_kind",
        "same_operation_divergence_refused", "receipt_grants_authority",
        "standing", "authority_effect", "real_a5", "g0",
        "artifact_producer_receipt_root",
    })
    expected = build_artifact_producer_receipt(
        artifact_path=item["artifact_path"], artifact_sha256=item["artifact_sha256"],
        producer_operation_root=item["producer_operation_root"],
        predecessor_artifact_sha256=item["predecessor_artifact_sha256"],
        predecessor_producer_operation_root=item["predecessor_producer_operation_root"],
        transaction_history_path=item["transaction_history_path"],
        supersession_kind=item["supersession_kind"],
    )
    require(item == expected, "PROCESS_ARTIFACT_PRODUCER_RECEIPT_INVALID")
    return item


def build_process_baseline(*, project_id: str, objective: str, subject_root: str,
                           source_manifest_root: str, architecture_contract_root: str,
                           amcas_contract_root: str, standards_catalog_root: str,
                           policy_roots: list[str], requirement_roots: list[str],
                           software_generation_root: str, initial_journal_head_root: str,
                           user_identity_root: str, session_identity_root: str,
                           locality_binding: dict[str, Any],
                           responsibilities: list[dict[str, Any]],
                           deliverable_ids: list[str],
                           execution_capsule_roots: list[str]) -> dict[str, Any]:
    project_id = _identifier(project_id, "PROCESS_PROJECT_ID_INVALID")
    objective = _text(objective, "PROCESS_OBJECTIVE_INVALID")
    for value in (subject_root, source_manifest_root, architecture_contract_root,
                  amcas_contract_root, standards_catalog_root, software_generation_root,
                  initial_journal_head_root, user_identity_root, session_identity_root):
        require_root(value)
    require(user_identity_root != session_identity_root,
            "PROCESS_USER_SESSION_IDENTITY_COLLISION")
    locality = validate_dkn_locality_binding(locality_binding)
    require(type(responsibilities) is list and bool(responsibilities),
            "PROCESS_RESPONSIBILITIES_INVALID")
    normalized_roles = []
    seen_roles: set[str] = set()
    for raw in responsibilities:
        item = exact_keys(raw, {"role_id", "actor_identity_root", "responsibility_ids",
                                "acceptance_scope_ids"})
        role_id = _identifier(item["role_id"], "PROCESS_ROLE_ID_INVALID")
        require(role_id not in seen_roles, "PROCESS_ROLE_DUPLICATE")
        seen_roles.add(role_id)
        normalized_roles.append({
            "role_id": role_id,
            "actor_identity_root": require_root(item["actor_identity_root"]),
            "responsibility_ids": _ids(item["responsibility_ids"],
                                       "PROCESS_RESPONSIBILITY_IDS_INVALID", allow_empty=False),
            "acceptance_scope_ids": _ids(item["acceptance_scope_ids"],
                                          "PROCESS_ACCEPTANCE_SCOPE_INVALID"),
        })
    normalized_roles.sort(key=lambda row: row["role_id"])
    body = {
        "schema": BASELINE_SCHEMA,
        "project_id": project_id,
        "objective": objective,
        "subject_root": subject_root,
        "source_manifest_root": source_manifest_root,
        "architecture_contract_root": architecture_contract_root,
        "amcas_contract_root": amcas_contract_root,
        "standards_catalog_root": standards_catalog_root,
        "policy_roots": _roots(policy_roots, "PROCESS_POLICY_ROOTS_INVALID", allow_empty=False),
        "requirement_roots": _roots(requirement_roots, "PROCESS_REQUIREMENT_ROOTS_INVALID",
                                    allow_empty=False),
        "software_generation_root": software_generation_root,
        "initial_journal_head_root": initial_journal_head_root,
        "user_identity_root": user_identity_root,
        "session_identity_root": session_identity_root,
        "locality_binding_root": locality["locality_binding_root"],
        "responsibilities": normalized_roles,
        "deliverable_ids": _ids(deliverable_ids, "PROCESS_DELIVERABLE_IDS_INVALID",
                                allow_empty=False),
        "execution_capsule_roots": _roots(
            execution_capsule_roots, "PROCESS_EXECUTION_CAPSULE_ROOTS_INVALID"),
        "hash_profile": deepcopy(HASH_PROFILE),
        "execution_authorized": False,
        **BOUNDARY,
    }
    return {**body, "process_baseline_root": root(body)}


def validate_process_baseline(value: Any) -> dict[str, Any]:
    item = _rooted(value, schema=BASELINE_SCHEMA,
                   root_field="process_baseline_root", code="PROCESS_BASELINE_INVALID")
    expected_keys = {
        "schema", "project_id", "objective", "subject_root", "source_manifest_root",
        "architecture_contract_root", "amcas_contract_root", "standards_catalog_root",
        "policy_roots", "requirement_roots", "software_generation_root",
        "initial_journal_head_root", "user_identity_root", "session_identity_root",
        "locality_binding_root", "responsibilities", "deliverable_ids",
        "execution_capsule_roots", "hash_profile",
        "execution_authorized", "standing", "authority_effect", "real_a5", "g0",
        "process_baseline_root",
    }
    exact_keys(item, expected_keys)
    require(item["execution_authorized"] is False, "PROCESS_BASELINE_AUTHORITY_INVALID")
    for field in ("subject_root", "source_manifest_root", "architecture_contract_root",
                  "amcas_contract_root", "standards_catalog_root", "software_generation_root",
                  "initial_journal_head_root", "user_identity_root", "session_identity_root",
                  "locality_binding_root"):
        require_root(item[field])
    _roots(item["policy_roots"], "PROCESS_POLICY_ROOTS_INVALID", allow_empty=False)
    _roots(item["requirement_roots"], "PROCESS_REQUIREMENT_ROOTS_INVALID", allow_empty=False)
    _ids(item["deliverable_ids"], "PROCESS_DELIVERABLE_IDS_INVALID", allow_empty=False)
    _roots(item["execution_capsule_roots"], "PROCESS_EXECUTION_CAPSULE_ROOTS_INVALID")
    require(item["hash_profile"] == HASH_PROFILE
            and set(item["hash_profile"]["metadata_roles"]) == METADATA_ROLES,
            "PROCESS_HASH_PROFILE_INVALID")
    require(item["project_id"] == _identifier(item["project_id"], "PROCESS_PROJECT_ID_INVALID")
            and item["objective"] == _text(item["objective"], "PROCESS_OBJECTIVE_INVALID"),
            "PROCESS_BASELINE_INVALID")
    require(item["user_identity_root"] != item["session_identity_root"],
            "PROCESS_USER_SESSION_IDENTITY_COLLISION")
    require(type(item["responsibilities"]) is list and bool(item["responsibilities"]),
            "PROCESS_RESPONSIBILITIES_INVALID")
    role_ids = []
    for row in item["responsibilities"]:
        role = exact_keys(row, {"role_id", "actor_identity_root", "responsibility_ids",
                                "acceptance_scope_ids"})
        role_ids.append(_identifier(role["role_id"], "PROCESS_ROLE_ID_INVALID"))
        require_root(role["actor_identity_root"])
        _ids(role["responsibility_ids"], "PROCESS_RESPONSIBILITY_IDS_INVALID",
             allow_empty=False)
        _ids(role["acceptance_scope_ids"], "PROCESS_ACCEPTANCE_SCOPE_INVALID")
    require(role_ids == sorted(set(role_ids)), "PROCESS_ROLE_DUPLICATE")
    return item


def build_process_milestone(*, milestone_id: str, process_baseline_root: str,
                            title: str, objective: str,
                            predecessor_milestone_ids: list[str],
                            entry_criteria: list[dict[str, Any]],
                            deliverables: list[dict[str, Any]],
                            standards_obligation_ids: list[str],
                            acceptance_role_id: str, acceptance_policy_root: str,
                            rollback_required: bool, rollback_plan_root: str | None,
                            authority_ceiling: dict[str, Any]) -> dict[str, Any]:
    milestone_id = _identifier(milestone_id, "PROCESS_MILESTONE_ID_INVALID")
    require_root(process_baseline_root)
    title = _text(title, "PROCESS_MILESTONE_TITLE_INVALID", maximum=512)
    objective = _text(objective, "PROCESS_MILESTONE_OBJECTIVE_INVALID")
    predecessors = _ids(predecessor_milestone_ids, "PROCESS_MILESTONE_PREDECESSORS_INVALID")
    require(milestone_id not in predecessors, "PROCESS_MILESTONE_SELF_PREDECESSOR")
    require(type(entry_criteria) is list and bool(entry_criteria),
            "PROCESS_ENTRY_CRITERIA_INVALID")
    normalized_criteria = []
    seen_criteria: set[str] = set()
    for raw in entry_criteria:
        item = exact_keys(raw, {"criterion_id", "kind", "expected_root"})
        criterion_id = _identifier(item["criterion_id"], "PROCESS_CRITERION_ID_INVALID")
        require(criterion_id not in seen_criteria, "PROCESS_CRITERION_DUPLICATE")
        seen_criteria.add(criterion_id)
        require(item["kind"] in {"ARTIFACT", "MILESTONE", "DECISION", "POLICY", "JOURNAL"},
                "PROCESS_CRITERION_KIND_INVALID")
        normalized_criteria.append({"criterion_id": criterion_id, "kind": item["kind"],
                                    "expected_root": require_root(item["expected_root"])})
    normalized_criteria.sort(key=lambda row: row["criterion_id"])
    require(type(deliverables) is list and bool(deliverables),
            "PROCESS_MILESTONE_DELIVERABLES_INVALID")
    normalized_deliverables = []
    seen_deliverables: set[str] = set()
    for raw in deliverables:
        item = exact_keys(raw, {"deliverable_id", "artifact_role", "subject_root",
                                "required_check_ids"})
        deliverable_id = _identifier(item["deliverable_id"],
                                     "PROCESS_DELIVERABLE_ID_INVALID")
        require(deliverable_id not in seen_deliverables,
                "PROCESS_MILESTONE_DELIVERABLE_DUPLICATE")
        seen_deliverables.add(deliverable_id)
        normalized_deliverables.append({
            "deliverable_id": deliverable_id,
            "artifact_role": _identifier(item["artifact_role"],
                                         "PROCESS_ARTIFACT_ROLE_INVALID"),
            "subject_root": require_root(item["subject_root"]),
            "required_check_ids": _ids(item["required_check_ids"],
                                       "PROCESS_REQUIRED_CHECK_IDS_INVALID", allow_empty=False),
        })
    normalized_deliverables.sort(key=lambda row: row["deliverable_id"])
    require(type(rollback_required) is bool, "PROCESS_ROLLBACK_FLAG_INVALID")
    rollback_root = _optional_root(rollback_plan_root)
    require(rollback_required == (rollback_root is not None),
            "PROCESS_ROLLBACK_PLAN_INCONSISTENT")
    body = {
        "schema": MILESTONE_SCHEMA,
        "milestone_id": milestone_id,
        "process_baseline_root": process_baseline_root,
        "title": title,
        "objective": objective,
        "predecessor_milestone_ids": predecessors,
        "entry_criteria": normalized_criteria,
        "deliverables": normalized_deliverables,
        "standards_obligation_ids": _ids(standards_obligation_ids,
                                         "PROCESS_STANDARDS_OBLIGATIONS_INVALID"),
        "acceptance_role_id": _identifier(acceptance_role_id,
                                          "PROCESS_ACCEPTANCE_ROLE_INVALID"),
        "acceptance_policy_root": require_root(acceptance_policy_root),
        "rollback": {"required": rollback_required, "plan_root": rollback_root},
        "authority_ceiling": _ceiling(authority_ceiling),
        "execution_authorized": False,
        **BOUNDARY,
    }
    return {**body, "milestone_root": root(body)}


def validate_process_milestone(value: Any) -> dict[str, Any]:
    item = _rooted(value, schema=MILESTONE_SCHEMA,
                   root_field="milestone_root", code="PROCESS_MILESTONE_INVALID")
    exact_keys(item, {
        "schema", "milestone_id", "process_baseline_root", "title", "objective",
        "predecessor_milestone_ids", "entry_criteria", "deliverables",
        "standards_obligation_ids", "acceptance_role_id", "acceptance_policy_root",
        "rollback", "authority_ceiling", "execution_authorized", "standing",
        "authority_effect", "real_a5", "g0", "milestone_root",
    })
    expected = build_process_milestone(
        milestone_id=item["milestone_id"], process_baseline_root=item["process_baseline_root"],
        title=item["title"], objective=item["objective"],
        predecessor_milestone_ids=item["predecessor_milestone_ids"],
        entry_criteria=item["entry_criteria"], deliverables=item["deliverables"],
        standards_obligation_ids=item["standards_obligation_ids"],
        acceptance_role_id=item["acceptance_role_id"],
        acceptance_policy_root=item["acceptance_policy_root"],
        rollback_required=item["rollback"]["required"],
        rollback_plan_root=item["rollback"]["plan_root"],
        authority_ceiling=item["authority_ceiling"],
    )
    require(item == expected, "PROCESS_MILESTONE_INVALID")
    return item


def assess_process_milestone(*, milestone: dict[str, Any],
                             accepted_predecessors: list[dict[str, Any]],
                             entry_evidence: list[dict[str, Any]],
                             check_results: list[dict[str, Any]],
                             standards_evaluation: dict[str, Any]) -> dict[str, Any]:
    milestone = validate_process_milestone(milestone)
    require(type(accepted_predecessors) is list, "PROCESS_PREDECESSOR_DECISIONS_INVALID")
    accepted_ids = []
    predecessor_roots = []
    for raw in accepted_predecessors:
        row = validate_process_milestone_decision(raw)
        require(row["decision"] == "ACCEPTED", "PROCESS_PREDECESSOR_NOT_ACCEPTED")
        accepted_ids.append(row["milestone_id"])
        predecessor_roots.append(row["milestone_decision_root"])
    require(sorted(accepted_ids) == milestone["predecessor_milestone_ids"],
            "PROCESS_PREDECESSOR_SET_MISMATCH")
    require(type(entry_evidence) is list, "PROCESS_ENTRY_EVIDENCE_INVALID")
    evidence_by_id = {}
    for raw in entry_evidence:
        item = exact_keys(raw, {"criterion_id", "evidence_root"})
        criterion_id = _identifier(item["criterion_id"], "PROCESS_CRITERION_ID_INVALID")
        require(criterion_id not in evidence_by_id, "PROCESS_ENTRY_EVIDENCE_DUPLICATE")
        evidence_by_id[criterion_id] = require_root(item["evidence_root"])
    criteria = {row["criterion_id"]: row for row in milestone["entry_criteria"]}
    entry_ok = set(evidence_by_id) == set(criteria) and all(
        evidence_by_id[key] == criteria[key]["expected_root"] for key in criteria)
    require(type(check_results) is list, "PROCESS_CHECK_RESULTS_INVALID")
    checks = {}
    for raw in check_results:
        item = exact_keys(raw, {"check_id", "role", "subject_root", "status",
                                "evidence_root", "witness_root", "freshness"})
        check_id = _identifier(item["check_id"], "PROCESS_CHECK_ID_INVALID")
        require(check_id not in checks, "PROCESS_CHECK_DUPLICATE")
        require(item["role"] in EVIDENCE_ROLES and item["status"] in {"PASS", "FAIL"}
                and item["freshness"] in {"CURRENT", "STALE"},
                "PROCESS_CHECK_RESULT_INVALID")
        require_root(item["subject_root"])
        require_root(item["evidence_root"])
        _optional_root(item["witness_root"])
        checks[check_id] = deepcopy(item)
    required_checks = sorted({check_id for deliverable in milestone["deliverables"]
                              for check_id in deliverable["required_check_ids"]})
    checks_ok = set(checks) == set(required_checks) and all(
        checks[key]["status"] == "PASS" and checks[key]["freshness"] == "CURRENT"
        for key in required_checks)
    standards = _rooted(standards_evaluation, schema=EVALUATION_SCHEMA,
                        root_field="evaluation_root", code="PROCESS_STANDARDS_EVALUATION_INVALID")
    standards_ok = (standards["decision"] == "PASS" and set(
        milestone["standards_obligation_ids"]).issubset(
            {row["obligation_id"] for row in standards["obligation_dispositions"]
             if row["status"] in {"PASS", "NOT_APPLICABLE"}}))
    reasons = []
    if not entry_ok:
        reasons.append("ENTRY_CRITERIA_UNSATISFIED")
    if not checks_ok:
        reasons.append("DELIVERABLE_EVIDENCE_UNSATISFIED")
    if not standards_ok:
        reasons.append("STANDARDS_UNSATISFIED")
    body = {
        "schema": ASSESSMENT_SCHEMA,
        "milestone_id": milestone["milestone_id"],
        "milestone_root": milestone["milestone_root"],
        "accepted_predecessor_decision_roots": sorted(predecessor_roots),
        "entry_evidence": [
            {"criterion_id": key, "evidence_root": evidence_by_id[key]}
            for key in sorted(evidence_by_id)
        ],
        "check_results": [checks[key] for key in sorted(checks)],
        "standards_evaluation_root": standards["evaluation_root"],
        "status": "READY_FOR_EXTERNAL_ACCEPTANCE" if not reasons else "HOLD",
        "reason_codes": reasons,
        "acceptance_is_authority": False,
        **BOUNDARY,
    }
    return {**body, "milestone_assessment_root": root(body)}


def validate_process_milestone_assessment(value: Any) -> dict[str, Any]:
    item = _rooted(value, schema=ASSESSMENT_SCHEMA,
                   root_field="milestone_assessment_root",
                   code="PROCESS_MILESTONE_ASSESSMENT_INVALID")
    exact_keys(item, {
        "schema", "milestone_id", "milestone_root",
        "accepted_predecessor_decision_roots", "entry_evidence", "check_results",
        "standards_evaluation_root", "status", "reason_codes",
        "acceptance_is_authority", "standing", "authority_effect", "real_a5", "g0",
        "milestone_assessment_root",
    })
    _identifier(item["milestone_id"], "PROCESS_MILESTONE_ID_INVALID")
    require_root(item["milestone_root"])
    _roots(item["accepted_predecessor_decision_roots"],
           "PROCESS_PREDECESSOR_DECISIONS_INVALID")
    criterion_ids = []
    require(type(item["entry_evidence"]) is list, "PROCESS_ENTRY_EVIDENCE_INVALID")
    for row in item["entry_evidence"]:
        entry = exact_keys(row, {"criterion_id", "evidence_root"})
        criterion_ids.append(_identifier(entry["criterion_id"],
                                         "PROCESS_CRITERION_ID_INVALID"))
        require_root(entry["evidence_root"])
    require(criterion_ids == sorted(set(criterion_ids)),
            "PROCESS_ENTRY_EVIDENCE_DUPLICATE")
    check_ids = []
    require(type(item["check_results"]) is list, "PROCESS_CHECK_RESULTS_INVALID")
    for row in item["check_results"]:
        check = exact_keys(row, {"check_id", "role", "subject_root", "status",
                                 "evidence_root", "witness_root", "freshness"})
        check_ids.append(_identifier(check["check_id"], "PROCESS_CHECK_ID_INVALID"))
        require(check["role"] in EVIDENCE_ROLES
                and check["status"] in {"PASS", "FAIL"}
                and check["freshness"] in {"CURRENT", "STALE"},
                "PROCESS_CHECK_RESULT_INVALID")
        require_root(check["subject_root"])
        require_root(check["evidence_root"])
        _optional_root(check["witness_root"])
    require(check_ids == sorted(set(check_ids)), "PROCESS_CHECK_DUPLICATE")
    require_root(item["standards_evaluation_root"])
    require(item["status"] in {"READY_FOR_EXTERNAL_ACCEPTANCE", "HOLD"}
            and type(item["reason_codes"]) is list
            and item["reason_codes"] == sorted(set(item["reason_codes"])),
            "PROCESS_MILESTONE_ASSESSMENT_INVALID")
    require((item["status"] == "READY_FOR_EXTERNAL_ACCEPTANCE")
            == (not item["reason_codes"]), "PROCESS_MILESTONE_ASSESSMENT_INVALID")
    require(item["acceptance_is_authority"] is False,
            "PROCESS_MILESTONE_ASSESSMENT_INVALID")
    return item


def record_process_milestone_decision(*, assessment: dict[str, Any], decision: str,
                                      reason_codes: list[str],
                                      external_approval: dict[str, Any] | None,
                                      expected_acceptance_policy_root: str,
                                      now: int) -> dict[str, Any]:
    assessment = validate_process_milestone_assessment(assessment)
    require(decision in MILESTONE_DECISIONS, "PROCESS_MILESTONE_DECISION_INVALID")
    reasons = _ids(reason_codes, "PROCESS_MILESTONE_REASON_CODES_INVALID",
                   allow_empty=decision == "ACCEPTED")
    require_root(expected_acceptance_policy_root)
    require(type(now) is int, "PROCESS_MILESTONE_DECISION_TIME_INVALID")
    approval_root = None
    approver_identity_root = None
    if decision == "ACCEPTED":
        require(assessment["status"] == "READY_FOR_EXTERNAL_ACCEPTANCE",
                "PROCESS_MILESTONE_NOT_READY")
        require(external_approval is not None, "PROCESS_MILESTONE_APPROVAL_REQUIRED")
        approval = verify_external_approval(
            external_approval,
            expected_operation_root=assessment["milestone_assessment_root"],
            expected_policy_root=expected_acceptance_policy_root,
            now=now,
        )
        approval_root = approval["approval_root"]
        approver_identity_root = approval["approver_identity_root"]
    else:
        require(external_approval is None, "PROCESS_REFUSAL_APPROVAL_FORBIDDEN")
    body = {
        "schema": DECISION_SCHEMA,
        "milestone_id": assessment["milestone_id"],
        "milestone_root": assessment["milestone_root"],
        "milestone_assessment_root": assessment["milestone_assessment_root"],
        "decision": decision,
        "reason_codes": reasons,
        "acceptance_policy_root": expected_acceptance_policy_root,
        "external_approval": deepcopy(external_approval),
        "external_approval_root": approval_root,
        "approver_identity_root": approver_identity_root,
        "decision_time": now,
        "external_approval_verified": decision == "ACCEPTED",
        "decision_grants_effect_authority": False,
        **BOUNDARY,
    }
    return {**body, "milestone_decision_root": root(body)}


def validate_process_milestone_decision(value: Any) -> dict[str, Any]:
    item = _rooted(value, schema=DECISION_SCHEMA,
                   root_field="milestone_decision_root",
                   code="PROCESS_MILESTONE_DECISION_INVALID")
    exact_keys(item, {
        "schema", "milestone_id", "milestone_root", "milestone_assessment_root",
        "decision", "reason_codes", "acceptance_policy_root", "external_approval",
        "external_approval_root",
        "approver_identity_root", "decision_time", "external_approval_verified",
        "decision_grants_effect_authority", "standing", "authority_effect", "real_a5",
        "g0", "milestone_decision_root",
    })
    _identifier(item["milestone_id"], "PROCESS_MILESTONE_ID_INVALID")
    for field in ("milestone_root", "milestone_assessment_root", "acceptance_policy_root"):
        require_root(item[field])
    require(item["decision"] in MILESTONE_DECISIONS
            and type(item["decision_time"]) is int,
            "PROCESS_MILESTONE_DECISION_INVALID")
    _ids(item["reason_codes"], "PROCESS_MILESTONE_REASON_CODES_INVALID",
         allow_empty=item["decision"] == "ACCEPTED")
    if item["decision"] == "ACCEPTED":
        require(type(item["external_approval"]) is dict,
                "PROCESS_MILESTONE_DECISION_INVALID")
        require_root(item["external_approval_root"])
        require_root(item["approver_identity_root"])
        require(item["external_approval_verified"] is True,
                "PROCESS_MILESTONE_DECISION_INVALID")
        approval = verify_external_approval(
            item["external_approval"],
            expected_operation_root=item["milestone_assessment_root"],
            expected_policy_root=item["acceptance_policy_root"],
            now=item["decision_time"],
        )
        require(approval["approval_root"] == item["external_approval_root"]
                and approval["approver_identity_root"] == item["approver_identity_root"],
                "PROCESS_MILESTONE_DECISION_INVALID")
    else:
        require(item["external_approval"] is None
                and item["external_approval_root"] is None
                and item["approver_identity_root"] is None
                and item["external_approval_verified"] is False,
                "PROCESS_MILESTONE_DECISION_INVALID")
    require(item["decision_grants_effect_authority"] is False,
            "PROCESS_MILESTONE_DECISION_INVALID")
    return item


def build_process_checkpoint(*, baseline: dict[str, Any], sequence: int,
                             predecessor_checkpoint: dict[str, Any] | None,
                             lifecycle_state: str, plan_root: str,
                             milestone_assessments: list[dict[str, Any]],
                             milestone_decisions: list[dict[str, Any]],
                             active_work_ids: list[str], hold_codes: list[str],
                             evidence_roots: list[str], decision_roots: list[str],
                             journal_head_root: str) -> dict[str, Any]:
    baseline = validate_process_baseline(baseline)
    require(type(sequence) is int and sequence >= 1, "PROCESS_CHECKPOINT_SEQUENCE_INVALID")
    require(lifecycle_state in LIFECYCLE_STATES, "PROCESS_LIFECYCLE_STATE_INVALID")
    previous_state = None
    previous_root = None
    if predecessor_checkpoint is not None:
        previous = validate_process_checkpoint(predecessor_checkpoint)
        require(previous["process_baseline_root"] == baseline["process_baseline_root"],
                "PROCESS_CHECKPOINT_BASELINE_MISMATCH")
        require(sequence == previous["sequence"] + 1,
                "PROCESS_CHECKPOINT_SEQUENCE_INVALID")
        previous_state = previous["lifecycle_state"]
        previous_root = previous["process_checkpoint_root"]
    else:
        require(sequence == 1, "PROCESS_CHECKPOINT_SEQUENCE_INVALID")
    require(lifecycle_state in TRANSITIONS[previous_state],
            "PROCESS_LIFECYCLE_TRANSITION_INVALID")
    require_root(plan_root)
    require_root(journal_head_root)
    active = _ids(active_work_ids, "PROCESS_ACTIVE_WORK_INVALID")
    holds = _ids(hold_codes, "PROCESS_HOLD_CODES_INVALID")
    evidence = _roots(evidence_roots, "PROCESS_EVIDENCE_ROOTS_INVALID")
    decisions = _roots(decision_roots, "PROCESS_DECISION_ROOTS_INVALID")
    assessments = []
    assessment_ids: set[str] = set()
    for raw in milestone_assessments:
        item = validate_process_milestone_assessment(raw)
        require(item["milestone_id"] not in assessment_ids,
                "PROCESS_MILESTONE_ASSESSMENT_DUPLICATE")
        assessment_ids.add(item["milestone_id"])
        assessments.append(item)
    assessments.sort(key=lambda row: row["milestone_id"])
    milestone_records = []
    record_ids: set[str] = set()
    for raw in milestone_decisions:
        item = validate_process_milestone_decision(raw)
        require(item["milestone_id"] not in record_ids,
                "PROCESS_MILESTONE_DECISION_DUPLICATE")
        record_ids.add(item["milestone_id"])
        milestone_records.append(item)
    milestone_records.sort(key=lambda row: row["milestone_id"])
    if milestone_records:
        require(set(record_ids).issubset(assessment_ids),
                "PROCESS_MILESTONE_DECISION_ASSESSMENT_MISSING")
        assessment_roots = {row["milestone_id"]: row["milestone_assessment_root"]
                            for row in assessments}
        require(all(row["milestone_assessment_root"] == assessment_roots[row["milestone_id"]]
                    for row in milestone_records),
                "PROCESS_MILESTONE_DECISION_ASSESSMENT_MISMATCH")
    if lifecycle_state == "ACTIVE":
        require(bool(active) and not holds, "PROCESS_ACTIVE_STATE_INVALID")
    if lifecycle_state == "BLOCKED":
        require(bool(holds), "PROCESS_BLOCKED_STATE_REQUIRES_HOLD")
    if lifecycle_state == "AWAITING_ACCEPTANCE":
        require(not active and not holds and bool(assessments)
                and all(row["status"] == "READY_FOR_EXTERNAL_ACCEPTANCE"
                        for row in assessments),
                "PROCESS_AWAITING_ACCEPTANCE_STATE_INVALID")
    if lifecycle_state == "ACCEPTED":
        require(not active and not holds and bool(milestone_records)
                and all(row["decision"] == "ACCEPTED"
                        and row["external_approval_verified"] is True
                        for row in milestone_records),
                "PROCESS_ACCEPTED_STATE_INVALID")
    body = {
        "schema": CHECKPOINT_SCHEMA,
        "process_baseline_root": baseline["process_baseline_root"],
        "sequence": sequence,
        "predecessor_checkpoint_root": previous_root,
        "lifecycle_state": lifecycle_state,
        "plan_root": plan_root,
        "milestone_assessment_roots": [row["milestone_assessment_root"]
                                       for row in assessments],
        "milestone_decision_roots": [row["milestone_decision_root"]
                                     for row in milestone_records],
        "active_work_ids": active,
        "hold_codes": holds,
        "evidence_roots": evidence,
        "decision_roots": decisions,
        "journal_head_root": journal_head_root,
        "execution_authorized": False,
        **BOUNDARY,
    }
    return {**body, "process_checkpoint_root": root(body)}


def validate_process_checkpoint(value: Any) -> dict[str, Any]:
    item = _rooted(value, schema=CHECKPOINT_SCHEMA,
                   root_field="process_checkpoint_root", code="PROCESS_CHECKPOINT_INVALID")
    exact_keys(item, {
        "schema", "process_baseline_root", "sequence", "predecessor_checkpoint_root",
        "lifecycle_state", "plan_root", "milestone_assessment_roots",
        "milestone_decision_roots", "active_work_ids", "hold_codes", "evidence_roots",
        "decision_roots", "journal_head_root", "execution_authorized", "standing",
        "authority_effect", "real_a5", "g0", "process_checkpoint_root",
    })
    require_root(item["process_baseline_root"])
    require(type(item["sequence"]) is int and item["sequence"] >= 1,
            "PROCESS_CHECKPOINT_SEQUENCE_INVALID")
    _optional_root(item["predecessor_checkpoint_root"])
    require(item["lifecycle_state"] in LIFECYCLE_STATES,
            "PROCESS_LIFECYCLE_STATE_INVALID")
    require_root(item["plan_root"])
    _roots(item["milestone_assessment_roots"], "PROCESS_MILESTONE_ASSESSMENTS_INVALID")
    _roots(item["milestone_decision_roots"], "PROCESS_MILESTONE_DECISIONS_INVALID")
    _ids(item["active_work_ids"], "PROCESS_ACTIVE_WORK_INVALID")
    _ids(item["hold_codes"], "PROCESS_HOLD_CODES_INVALID")
    _roots(item["evidence_roots"], "PROCESS_EVIDENCE_ROOTS_INVALID")
    _roots(item["decision_roots"], "PROCESS_DECISION_ROOTS_INVALID")
    require_root(item["journal_head_root"])
    require(item["execution_authorized"] is False, "PROCESS_CHECKPOINT_AUTHORITY_INVALID")
    return item


def build_governed_replan(*, predecessor_checkpoint: dict[str, Any],
                          successor_plan_root: str, reason_code: str,
                          scope_delta: dict[str, list[str]],
                          affected_dependency_ids: list[str],
                          invalidated_evidence_roots: list[str],
                          retained_evidence_roots: list[str],
                          unresolved_work_ids: list[str],
                          unresolved_dispositions: list[dict[str, Any]]) -> dict[str, Any]:
    checkpoint = validate_process_checkpoint(predecessor_checkpoint)
    require_root(successor_plan_root)
    reason_code = _identifier(reason_code, "PROCESS_REPLAN_REASON_INVALID")
    delta = exact_keys(scope_delta, {"added", "removed", "changed"})
    normalized_delta = {
        key: _ids(delta[key], "PROCESS_REPLAN_SCOPE_DELTA_INVALID")
        for key in ("added", "removed", "changed")
    }
    require(not (set(normalized_delta["added"]) & set(normalized_delta["removed"])),
            "PROCESS_REPLAN_SCOPE_DELTA_INVALID")
    invalidated = _roots(invalidated_evidence_roots,
                         "PROCESS_REPLAN_INVALIDATED_EVIDENCE_INVALID")
    retained = _roots(retained_evidence_roots,
                      "PROCESS_REPLAN_RETAINED_EVIDENCE_INVALID")
    require(not set(invalidated).intersection(retained),
            "PROCESS_REPLAN_EVIDENCE_OVERLAP")
    unresolved = _ids(unresolved_work_ids, "PROCESS_REPLAN_UNRESOLVED_INVALID")
    require(type(unresolved_dispositions) is list,
            "PROCESS_REPLAN_DISPOSITIONS_INVALID")
    disposition_by_id = {}
    for raw in unresolved_dispositions:
        item = exact_keys(raw, {"work_id", "disposition", "reason_code",
                                "successor_work_id", "evidence_root"})
        work_id = _identifier(item["work_id"], "PROCESS_REPLAN_WORK_ID_INVALID")
        require(work_id not in disposition_by_id, "PROCESS_REPLAN_DISPOSITION_DUPLICATE")
        require(item["disposition"] in REPLAN_DISPOSITIONS,
                "PROCESS_REPLAN_DISPOSITION_INVALID")
        successor = (None if item["successor_work_id"] is None else
                     _identifier(item["successor_work_id"],
                                 "PROCESS_REPLAN_SUCCESSOR_WORK_ID_INVALID"))
        evidence_root = _optional_root(item["evidence_root"])
        require((item["disposition"] == "RESOLVED") == (evidence_root is not None),
                "PROCESS_REPLAN_RESOLUTION_EVIDENCE_INVALID")
        require((item["disposition"] != "RETAINED") or successor is not None,
                "PROCESS_REPLAN_RETAINED_SUCCESSOR_REQUIRED")
        disposition_by_id[work_id] = {
            "work_id": work_id,
            "disposition": item["disposition"],
            "reason_code": _identifier(item["reason_code"],
                                       "PROCESS_REPLAN_DISPOSITION_REASON_INVALID"),
            "successor_work_id": successor,
            "evidence_root": evidence_root,
        }
    require(set(disposition_by_id) == set(unresolved),
            "PROCESS_REPLAN_UNRESOLVED_DENOMINATOR_MISMATCH")
    body = {
        "schema": REPLAN_SCHEMA,
        "process_baseline_root": checkpoint["process_baseline_root"],
        "predecessor_checkpoint_root": checkpoint["process_checkpoint_root"],
        "predecessor_plan_root": checkpoint["plan_root"],
        "successor_plan_root": successor_plan_root,
        "reason_code": reason_code,
        "scope_delta": normalized_delta,
        "affected_dependency_ids": _ids(affected_dependency_ids,
                                        "PROCESS_REPLAN_DEPENDENCIES_INVALID"),
        "invalidated_evidence_roots": invalidated,
        "retained_evidence_roots": retained,
        "unresolved_dispositions": [disposition_by_id[key]
                                    for key in sorted(disposition_by_id)],
        "execution_authorized": False,
        **BOUNDARY,
    }
    return {**body, "replan_root": root(body)}


def validate_governed_replan(value: Any) -> dict[str, Any]:
    item = _rooted(value, schema=REPLAN_SCHEMA, root_field="replan_root",
                   code="PROCESS_REPLAN_INVALID")
    exact_keys(item, {
        "schema", "process_baseline_root", "predecessor_checkpoint_root",
        "predecessor_plan_root", "successor_plan_root", "reason_code", "scope_delta",
        "affected_dependency_ids", "invalidated_evidence_roots",
        "retained_evidence_roots", "unresolved_dispositions", "execution_authorized",
        "standing", "authority_effect", "real_a5", "g0", "replan_root",
    })
    for field in ("process_baseline_root", "predecessor_checkpoint_root",
                  "predecessor_plan_root", "successor_plan_root"):
        require_root(item[field])
    _identifier(item["reason_code"], "PROCESS_REPLAN_REASON_INVALID")
    delta = exact_keys(item["scope_delta"], {"added", "removed", "changed"})
    normalized_delta = {key: _ids(delta[key], "PROCESS_REPLAN_SCOPE_DELTA_INVALID")
                        for key in ("added", "removed", "changed")}
    require(delta == normalized_delta
            and not (set(delta["added"]) & set(delta["removed"])),
            "PROCESS_REPLAN_SCOPE_DELTA_INVALID")
    _ids(item["affected_dependency_ids"], "PROCESS_REPLAN_DEPENDENCIES_INVALID")
    invalidated = _roots(item["invalidated_evidence_roots"],
                         "PROCESS_REPLAN_INVALIDATED_EVIDENCE_INVALID")
    retained = _roots(item["retained_evidence_roots"],
                      "PROCESS_REPLAN_RETAINED_EVIDENCE_INVALID")
    require(not set(invalidated).intersection(retained),
            "PROCESS_REPLAN_EVIDENCE_OVERLAP")
    require(type(item["unresolved_dispositions"]) is list,
            "PROCESS_REPLAN_DISPOSITIONS_INVALID")
    work_ids = []
    for raw in item["unresolved_dispositions"]:
        row = exact_keys(raw, {"work_id", "disposition", "reason_code",
                               "successor_work_id", "evidence_root"})
        work_ids.append(_identifier(row["work_id"], "PROCESS_REPLAN_WORK_ID_INVALID"))
        require(row["disposition"] in REPLAN_DISPOSITIONS,
                "PROCESS_REPLAN_DISPOSITION_INVALID")
        _identifier(row["reason_code"], "PROCESS_REPLAN_DISPOSITION_REASON_INVALID")
        successor = (None if row["successor_work_id"] is None else
                     _identifier(row["successor_work_id"],
                                 "PROCESS_REPLAN_SUCCESSOR_WORK_ID_INVALID"))
        evidence = _optional_root(row["evidence_root"])
        require((row["disposition"] == "RESOLVED") == (evidence is not None),
                "PROCESS_REPLAN_RESOLUTION_EVIDENCE_INVALID")
        require(row["disposition"] != "RETAINED" or successor is not None,
                "PROCESS_REPLAN_RETAINED_SUCCESSOR_REQUIRED")
    require(work_ids == sorted(set(work_ids)), "PROCESS_REPLAN_DISPOSITION_DUPLICATE")
    require(item["execution_authorized"] is False, "PROCESS_REPLAN_AUTHORITY_INVALID")
    return item


def build_process_standards_schedule(*, catalog: dict[str, Any],
                                     subject_root: str,
                                     event_facts: list[dict[str, Any]],
                                     last_satisfied: list[dict[str, Any]],
                                     invalidations: list[dict[str, Any]]) -> dict[str, Any]:
    catalog = validate_standards_catalog(catalog)
    require_root(subject_root)
    require(type(event_facts) is list and bool(event_facts),
            "PROCESS_STANDARD_EVENTS_INVALID")
    events = []
    seen_events: set[str] = set()
    for raw in event_facts:
        item = exact_keys(raw, {"event_id", "sequence", "trigger", "event_root"})
        event_id = _identifier(item["event_id"], "PROCESS_STANDARD_EVENT_ID_INVALID")
        require(event_id not in seen_events and type(item["sequence"]) is int
                and item["sequence"] >= 1, "PROCESS_STANDARD_EVENT_INVALID")
        seen_events.add(event_id)
        events.append({"event_id": event_id, "sequence": item["sequence"],
                       "trigger": _identifier(item["trigger"],
                                              "PROCESS_STANDARD_TRIGGER_INVALID"),
                       "event_root": require_root(item["event_root"])})
    events.sort(key=lambda row: (row["sequence"], row["event_id"]))
    require([row["sequence"] for row in events] == sorted(row["sequence"] for row in events),
            "PROCESS_STANDARD_EVENT_ORDER_INVALID")
    satisfied = {}
    for raw in last_satisfied:
        item = exact_keys(raw, {"obligation_id", "evaluation_root", "subject_root", "sequence"})
        obligation_id = _identifier(item["obligation_id"],
                                    "PROCESS_STANDARD_OBLIGATION_ID_INVALID")
        require(obligation_id not in satisfied and type(item["sequence"]) is int,
                "PROCESS_STANDARD_LAST_SATISFIED_INVALID")
        require_root(item["evaluation_root"])
        require_root(item["subject_root"])
        satisfied[obligation_id] = deepcopy(item)
    invalidated = {}
    for raw in invalidations:
        item = exact_keys(raw, {"obligation_id", "event_id", "reason_code"})
        obligation_id = _identifier(item["obligation_id"],
                                    "PROCESS_STANDARD_OBLIGATION_ID_INVALID")
        require(obligation_id not in invalidated and item["event_id"] in seen_events,
                "PROCESS_STANDARD_INVALIDATION_INVALID")
        invalidated[obligation_id] = deepcopy(item)
    triggers = {row["trigger"] for row in events}
    latest_sequence = max(row["sequence"] for row in events)
    due = []
    known_obligations = {row["obligation_id"] for row in catalog["obligations"]}
    require(set(satisfied).issubset(known_obligations)
            and set(invalidated).issubset(known_obligations),
            "PROCESS_STANDARD_OBLIGATION_UNKNOWN")
    for obligation in catalog["obligations"]:
        applicable = (obligation["class"] != "CONDITIONAL"
                      or bool(triggers.intersection(obligation["triggers"])))
        if not applicable:
            continue
        last = satisfied.get(obligation["obligation_id"])
        reasons = []
        if last is None:
            reasons.append("NEVER_SATISFIED")
        elif last["subject_root"] != subject_root:
            reasons.append("SUBJECT_CHANGED")
        elif last["sequence"] > latest_sequence:
            reasons.append("SATISFACTION_SEQUENCE_INVALID")
        if obligation["obligation_id"] in invalidated:
            reasons.append(invalidated[obligation["obligation_id"]]["reason_code"])
        if reasons:
            due.append({"obligation_id": obligation["obligation_id"],
                        "class": obligation["class"],
                        "check_ids": obligation["check_ids"],
                        "reason_codes": sorted(set(reasons))})
    body = {
        "schema": SCHEDULE_SCHEMA,
        "catalog_root": catalog["catalog_root"],
        "subject_root": subject_root,
        "event_facts": events,
        "last_satisfied": [satisfied[key] for key in sorted(satisfied)],
        "invalidations": [invalidated[key] for key in sorted(invalidated)],
        "due_reviews": due,
        "reminder_policy": "EVENT_TRIGGERED_CONTEXT_SELECTIVE_NOT_PERIODIC",
        "status": "REVIEW_DUE" if due else "CURRENT",
        "schedule_is_authority": False,
        **BOUNDARY,
    }
    return {**body, "standards_schedule_root": root(body)}


def validate_process_standards_schedule(value: Any) -> dict[str, Any]:
    item = _rooted(value, schema=SCHEDULE_SCHEMA,
                   root_field="standards_schedule_root",
                   code="PROCESS_STANDARDS_SCHEDULE_INVALID")
    exact_keys(item, {
        "schema", "catalog_root", "subject_root", "event_facts", "last_satisfied",
        "invalidations", "due_reviews", "reminder_policy", "status",
        "schedule_is_authority", "standing", "authority_effect", "real_a5", "g0",
        "standards_schedule_root",
    })
    require_root(item["catalog_root"])
    require_root(item["subject_root"])
    require(type(item["event_facts"]) is list and bool(item["event_facts"]),
            "PROCESS_STANDARD_EVENTS_INVALID")
    event_ids = []
    sequences = []
    for raw in item["event_facts"]:
        row = exact_keys(raw, {"event_id", "sequence", "trigger", "event_root"})
        event_ids.append(_identifier(row["event_id"], "PROCESS_STANDARD_EVENT_ID_INVALID"))
        require(type(row["sequence"]) is int and row["sequence"] >= 1,
                "PROCESS_STANDARD_EVENT_INVALID")
        sequences.append(row["sequence"])
        _identifier(row["trigger"], "PROCESS_STANDARD_TRIGGER_INVALID")
        require_root(row["event_root"])
    require(event_ids == [row["event_id"] for row in sorted(
                item["event_facts"], key=lambda row: (row["sequence"], row["event_id"]))]
            and len(event_ids) == len(set(event_ids)) and sequences == sorted(sequences),
            "PROCESS_STANDARD_EVENT_ORDER_INVALID")
    satisfied_ids = []
    for raw in item["last_satisfied"]:
        row = exact_keys(raw, {"obligation_id", "evaluation_root", "subject_root", "sequence"})
        satisfied_ids.append(_identifier(row["obligation_id"],
                                         "PROCESS_STANDARD_OBLIGATION_ID_INVALID"))
        require_root(row["evaluation_root"])
        require_root(row["subject_root"])
        require(type(row["sequence"]) is int and row["sequence"] >= 0,
                "PROCESS_STANDARD_LAST_SATISFIED_INVALID")
    require(satisfied_ids == sorted(set(satisfied_ids)),
            "PROCESS_STANDARD_LAST_SATISFIED_INVALID")
    invalidated_ids = []
    for raw in item["invalidations"]:
        row = exact_keys(raw, {"obligation_id", "event_id", "reason_code"})
        invalidated_ids.append(_identifier(row["obligation_id"],
                                           "PROCESS_STANDARD_OBLIGATION_ID_INVALID"))
        require(row["event_id"] in event_ids, "PROCESS_STANDARD_INVALIDATION_INVALID")
        _identifier(row["reason_code"], "PROCESS_STANDARD_INVALIDATION_INVALID")
    require(invalidated_ids == sorted(set(invalidated_ids)),
            "PROCESS_STANDARD_INVALIDATION_INVALID")
    due_ids = []
    for raw in item["due_reviews"]:
        row = exact_keys(raw, {"obligation_id", "class", "check_ids", "reason_codes"})
        due_ids.append(_identifier(row["obligation_id"],
                                   "PROCESS_STANDARD_OBLIGATION_ID_INVALID"))
        require(row["class"] in CLASSES,
                "PROCESS_STANDARD_DUE_REVIEW_INVALID")
        _ids(row["check_ids"], "PROCESS_STANDARD_DUE_REVIEW_INVALID")
        _ids(row["reason_codes"], "PROCESS_STANDARD_DUE_REVIEW_INVALID", allow_empty=False)
    require(due_ids == sorted(set(due_ids)), "PROCESS_STANDARD_DUE_REVIEW_INVALID")
    require(item["reminder_policy"] == "EVENT_TRIGGERED_CONTEXT_SELECTIVE_NOT_PERIODIC"
            and item["status"] == ("REVIEW_DUE" if item["due_reviews"] else "CURRENT")
            and item["schedule_is_authority"] is False,
            "PROCESS_STANDARDS_SCHEDULE_INVALID")
    return item


def build_process_observatory(*, checkpoint: dict[str, Any],
                              standards_schedule: dict[str, Any],
                              artifact_statuses: list[dict[str, Any]],
                              replan_roots: list[str]) -> dict[str, Any]:
    checkpoint = validate_process_checkpoint(checkpoint)
    schedule = validate_process_standards_schedule(standards_schedule)
    require(type(artifact_statuses) is list and bool(artifact_statuses),
            "PROCESS_ARTIFACT_STATUSES_INVALID")
    normalized = []
    seen: set[str] = set()
    for raw in artifact_statuses:
        item = exact_keys(raw, {"artifact_id", "implementation_root",
                                "test_evidence_roots", "review_root", "acceptance_root"})
        artifact_id = _identifier(item["artifact_id"], "PROCESS_ARTIFACT_ID_INVALID")
        require(artifact_id not in seen, "PROCESS_ARTIFACT_STATUS_DUPLICATE")
        seen.add(artifact_id)
        implementation_root = _optional_root(item["implementation_root"])
        test_roots = _roots(item["test_evidence_roots"],
                            "PROCESS_ARTIFACT_TEST_ROOTS_INVALID")
        review_root = _optional_root(item["review_root"])
        acceptance_root = _optional_root(item["acceptance_root"])
        require(not test_roots or implementation_root is not None,
                "PROCESS_ARTIFACT_TEST_WITHOUT_IMPLEMENTATION")
        require(review_root is None or bool(test_roots),
                "PROCESS_ARTIFACT_REVIEW_WITHOUT_TESTS")
        require(acceptance_root is None or review_root is not None,
                "PROCESS_ARTIFACT_ACCEPTANCE_WITHOUT_REVIEW")
        normalized.append({
            "artifact_id": artifact_id,
            "implementation_root": implementation_root,
            "test_evidence_roots": test_roots,
            "review_root": review_root,
            "acceptance_root": acceptance_root,
            "implemented": implementation_root is not None,
            "tested": bool(test_roots),
            "reviewed": review_root is not None,
            "accepted": acceptance_root is not None,
        })
    normalized.sort(key=lambda row: row["artifact_id"])
    blockers = ([{"kind": "HOLD", "id": code} for code in checkpoint["hold_codes"]]
                + [{"kind": "STANDARD_REVIEW", "id": row["obligation_id"]}
                   for row in schedule["due_reviews"]])
    blockers.sort(key=lambda row: (row["kind"], row["id"]))
    next_actions = []
    if checkpoint["hold_codes"]:
        next_actions.append("RESOLVE_RECORDED_HOLDS")
    if schedule["due_reviews"]:
        next_actions.append("SATISFY_DUE_STANDARDS")
    if checkpoint["active_work_ids"]:
        next_actions.append("COMPLETE_ACTIVE_WORK")
    if checkpoint["lifecycle_state"] == "AWAITING_ACCEPTANCE":
        next_actions.append("REQUEST_EXTERNAL_MILESTONE_ACCEPTANCE")
    if checkpoint["lifecycle_state"] in {"BLOCKED", "SUPERSEDED"}:
        next_actions.append("PREPARE_GOVERNED_REPLAN")
    if not next_actions and checkpoint["lifecycle_state"] == "ACCEPTED":
        next_actions.append("EXPORT_PORTABLE_HANDOFF")
    facts = {
        "implemented": sum(row["implemented"] for row in normalized),
        "tested": sum(row["tested"] for row in normalized),
        "reviewed": sum(row["reviewed"] for row in normalized),
        "accepted": sum(row["accepted"] for row in normalized),
        "artifact_denominator": len(normalized),
    }
    human = {
        "state": checkpoint["lifecycle_state"],
        "blockers": blockers,
        "artifact_facts": facts,
        "next_actions": next_actions,
        "note": "Counts are rooted facts, not a maturity percentage or authority decision.",
    }
    agent = {
        "process_baseline_root": checkpoint["process_baseline_root"],
        "checkpoint_root": checkpoint["process_checkpoint_root"],
        "journal_head_root": checkpoint["journal_head_root"],
        "standards_schedule_root": schedule["standards_schedule_root"],
        "blockers": blockers,
        "artifact_statuses": normalized,
        "next_actions": [{"action": action, "authorized": False}
                         for action in next_actions],
    }
    body = {
        "schema": OBSERVATORY_SCHEMA,
        "process_baseline_root": checkpoint["process_baseline_root"],
        "process_checkpoint_root": checkpoint["process_checkpoint_root"],
        "standards_schedule_root": schedule["standards_schedule_root"],
        "replan_roots": _roots(replan_roots, "PROCESS_REPLAN_ROOTS_INVALID"),
        "human_projection": human,
        "agent_projection": agent,
        "forensic": {
            "checkpoint": checkpoint,
            "standards_schedule": schedule,
            "artifact_statuses": normalized,
        },
        "projection_is_authority": False,
        **BOUNDARY,
    }
    return {**body, "process_observatory_root": root(body)}


def validate_process_observatory(value: Any) -> dict[str, Any]:
    item = _rooted(value, schema=OBSERVATORY_SCHEMA,
                   root_field="process_observatory_root",
                   code="PROCESS_OBSERVATORY_INVALID")
    exact_keys(item, {
        "schema", "process_baseline_root", "process_checkpoint_root",
        "standards_schedule_root", "replan_roots", "human_projection",
        "agent_projection", "forensic", "projection_is_authority", "standing",
        "authority_effect", "real_a5", "g0", "process_observatory_root",
    })
    for field in ("process_baseline_root", "process_checkpoint_root",
                  "standards_schedule_root"):
        require_root(item[field])
    _roots(item["replan_roots"], "PROCESS_REPLAN_ROOTS_INVALID")
    forensic = exact_keys(item["forensic"],
                          {"checkpoint", "standards_schedule", "artifact_statuses"})
    checkpoint = validate_process_checkpoint(forensic["checkpoint"])
    schedule = validate_process_standards_schedule(forensic["standards_schedule"])
    require(checkpoint["process_baseline_root"] == item["process_baseline_root"]
            and checkpoint["process_checkpoint_root"] == item["process_checkpoint_root"]
            and schedule["standards_schedule_root"] == item["standards_schedule_root"],
            "PROCESS_OBSERVATORY_BINDING_INVALID")
    expected = build_process_observatory(
        checkpoint=checkpoint,
        standards_schedule=schedule,
        artifact_statuses=[{
            "artifact_id": row["artifact_id"],
            "implementation_root": row["implementation_root"],
            "test_evidence_roots": row["test_evidence_roots"],
            "review_root": row["review_root"],
            "acceptance_root": row["acceptance_root"],
        } for row in forensic["artifact_statuses"]],
        replan_roots=item["replan_roots"],
    )
    require(item == expected and item["projection_is_authority"] is False,
            "PROCESS_OBSERVATORY_INVALID")
    return item


def build_courthouse_process_binding(*, baseline: dict[str, Any],
                                     checkpoint: dict[str, Any],
                                     execution_capsule: dict[str, Any],
                                     requested_surface: str,
                                     authority_policy_root: str,
                                     native_runner_binding_root: str) -> dict[str, Any]:
    """Bind portable process custody to a future courthouse execution request.

    The record is an input contract only.  It cannot satisfy G1, G2 or G3 and
    cannot authorize the requested effect.
    """
    baseline = validate_process_baseline(baseline)
    checkpoint = validate_process_checkpoint(checkpoint)
    capsule = validate_exact_execution_capsule(execution_capsule)
    require(checkpoint["process_baseline_root"] == baseline["process_baseline_root"],
            "PROCESS_COURTHOUSE_CHECKPOINT_BASELINE_MISMATCH")
    require(capsule["execution_capsule_root"] in baseline["execution_capsule_roots"],
            "PROCESS_COURTHOUSE_EXECUTION_CAPSULE_UNBOUND")
    require_root(authority_policy_root)
    require_root(native_runner_binding_root)
    body = {
        "schema": COURTHOUSE_BINDING_SCHEMA,
        "process_baseline_root": baseline["process_baseline_root"],
        "process_checkpoint_root": checkpoint["process_checkpoint_root"],
        "journal_head_root": checkpoint["journal_head_root"],
        "execution_capsule_root": capsule["execution_capsule_root"],
        "producer_operation_root": capsule["operation_identity_root"],
        "requested_surface": _identifier(requested_surface,
                                          "PROCESS_COURTHOUSE_SURFACE_INVALID"),
        "requested_effect_class": capsule["effect_class"],
        "authority_policy_root": authority_policy_root,
        "jurisdiction_root": capsule["jurisdiction_root"],
        "native_runner_binding_root": native_runner_binding_root,
        "required_gate_receipts": ["G1_SENTINEL", "G2_WITNESS", "G3_DIAGNOSTIC"],
        "required_terminal_bindings": [
            "execution_capsule_root", "producer_operation_root", "process_checkpoint_root",
            "expected_pre_state_root", "observed_post_state_root", "journal_head_root",
        ],
        "dispatch_authorized": False,
        "binding_is_permission": False,
        **BOUNDARY,
    }
    return {**body, "courthouse_process_binding_root": root(body)}


def validate_courthouse_process_binding(value: Any) -> dict[str, Any]:
    item = _rooted(value, schema=COURTHOUSE_BINDING_SCHEMA,
                   root_field="courthouse_process_binding_root",
                   code="PROCESS_COURTHOUSE_BINDING_INVALID")
    exact_keys(item, {
        "schema", "process_baseline_root", "process_checkpoint_root", "journal_head_root",
        "execution_capsule_root", "producer_operation_root", "requested_surface",
        "requested_effect_class", "authority_policy_root", "jurisdiction_root",
        "native_runner_binding_root", "required_gate_receipts",
        "required_terminal_bindings", "dispatch_authorized", "binding_is_permission",
        "standing", "authority_effect", "real_a5", "g0",
        "courthouse_process_binding_root",
    })
    for field in ("process_baseline_root", "process_checkpoint_root", "journal_head_root",
                  "execution_capsule_root", "producer_operation_root",
                  "authority_policy_root", "jurisdiction_root",
                  "native_runner_binding_root"):
        require_root(item[field])
    _identifier(item["requested_surface"], "PROCESS_COURTHOUSE_SURFACE_INVALID")
    _identifier(item["requested_effect_class"],
                "PROCESS_EXECUTION_EFFECT_CLASS_INVALID")
    require(item["required_gate_receipts"] ==
            ["G1_SENTINEL", "G2_WITNESS", "G3_DIAGNOSTIC"]
            and item["required_terminal_bindings"] == [
                "execution_capsule_root", "producer_operation_root",
                "process_checkpoint_root", "expected_pre_state_root",
                "observed_post_state_root", "journal_head_root"]
            and item["dispatch_authorized"] is False
            and item["binding_is_permission"] is False,
            "PROCESS_COURTHOUSE_BINDING_INVALID")
    return item


def build_process_thr_manifest(*, baseline: dict[str, Any],
                               locality_binding: dict[str, Any],
                               checkpoint: dict[str, Any],
                               milestones: list[dict[str, Any]],
                               assessments: list[dict[str, Any]],
                               decisions: list[dict[str, Any]],
                               standards_evaluation_roots: list[str],
                               evidence_receipt_roots: list[str],
                               interpretation_profile_root: str) -> dict[str, Any]:
    """Build the typed THR/CAS projection for a process checkpoint."""
    baseline = validate_process_baseline(baseline)
    locality = validate_dkn_locality_binding(locality_binding)
    checkpoint = validate_process_checkpoint(checkpoint)
    require(checkpoint["process_baseline_root"] == baseline["process_baseline_root"],
            "PROCESS_CHECKPOINT_BASELINE_MISMATCH")
    require(baseline["locality_binding_root"] == locality["locality_binding_root"],
            "PROCESS_LOCALITY_BASELINE_MISMATCH")
    require_root(interpretation_profile_root)
    milestone_rows = [validate_process_milestone(row) for row in milestones]
    require(len({row["milestone_id"] for row in milestone_rows}) == len(milestone_rows),
            "PROCESS_MILESTONE_DUPLICATE")
    assessment_rows = [validate_process_milestone_assessment(row)
                       for row in assessments]
    decision_rows = [validate_process_milestone_decision(row) for row in decisions]
    payload_records = {
        "PROCESS-BASELINE.json": canonical_bytes(baseline),
        "PROCESS-CHECKPOINT.json": canonical_bytes(checkpoint),
        "PROCESS-LOCALITY.json": canonical_bytes(locality),
    }
    for row in sorted(milestone_rows, key=lambda item: item["milestone_id"]):
        payload_records[f"milestones/{row['milestone_id']}.json"] = canonical_bytes(row)
    for row in sorted(assessment_rows, key=lambda item: item["milestone_id"]):
        payload_records[f"assessments/{row['milestone_id']}.json"] = canonical_bytes(row)
    for row in sorted(decision_rows, key=lambda item: item["milestone_id"]):
        payload_records[f"decisions/{row['milestone_id']}.json"] = canonical_bytes(row)
    acceptance_roots = sorted(row["external_approval_root"] for row in decision_rows
                              if row["external_approval_root"] is not None)
    meaning = {
        "profile_id": "PIPPI.PROCESS.GOVERNANCE.V0.1",
        "interpretation_profile_root": interpretation_profile_root,
        "process_baseline_root": baseline["process_baseline_root"],
        "objective": baseline["objective"],
        "requirement_roots": baseline["requirement_roots"],
        "execution_capsule_roots": baseline["execution_capsule_roots"],
        "milestone_roots": sorted(row["milestone_root"] for row in milestone_rows),
        "checkpoint_root": checkpoint["process_checkpoint_root"],
        "metadata_roles": baseline["hash_profile"]["metadata_roles"],
        "semantic_equivalence_claim": "NONE_WITHOUT_DECLARED_LENS_AND_COMPARISON",
    }
    admissibility = {
        "architecture_contract_root": baseline["architecture_contract_root"],
        "amcas_contract_root": baseline["amcas_contract_root"],
        "standards_catalog_root": baseline["standards_catalog_root"],
        "policy_roots": baseline["policy_roots"],
        "standards_evaluation_roots": _roots(
            standards_evaluation_roots, "PROCESS_STANDARDS_EVALUATION_ROOTS_INVALID"),
        "milestone_decision_roots": sorted(row["milestone_decision_root"]
                                           for row in decision_rows),
        "authority_ceiling": deepcopy(BOUNDARY),
        "current_authorization_claim": "NONE",
    }
    locality_section = {
        "locality_binding_root": locality["locality_binding_root"],
        "dimension_id": locality["dimension_id"],
        "semantic_namespace": locality["semantic_namespace"],
        "user_identity_root": baseline["user_identity_root"],
        "session_identity_root": baseline["session_identity_root"],
        "namespace_authority_verified": locality["namespace_authority_verified"],
        "permission_granted": False,
    }
    receipts = {
        "journal_head_root": checkpoint["journal_head_root"],
        "evidence_receipt_roots": _roots(
            evidence_receipt_roots, "PROCESS_EVIDENCE_RECEIPT_ROOTS_INVALID"),
        "assessment_roots": sorted(row["milestone_assessment_root"]
                                   for row in assessment_rows),
        "external_approval_roots": acceptance_roots,
    }
    return build_thr_manifest(
        application_id=baseline["project_id"],
        payloads=payload_records,
        meaning=meaning,
        admissibility=admissibility,
        locality=locality_section,
        receipts=receipts,
    )


__all__ = [
    "build_dkn_locality_binding", "validate_dkn_locality_binding",
    "build_exact_execution_capsule", "validate_exact_execution_capsule",
    "build_artifact_producer_receipt", "validate_artifact_producer_receipt",
    "build_process_baseline", "validate_process_baseline",
    "build_process_milestone", "validate_process_milestone",
    "assess_process_milestone", "validate_process_milestone_assessment",
    "record_process_milestone_decision", "validate_process_milestone_decision",
    "build_process_checkpoint", "validate_process_checkpoint", "build_governed_replan",
    "validate_governed_replan", "build_process_standards_schedule",
    "validate_process_standards_schedule", "build_process_observatory",
    "validate_process_observatory",
    "build_courthouse_process_binding", "validate_courthouse_process_binding",
    "build_process_thr_manifest",
]

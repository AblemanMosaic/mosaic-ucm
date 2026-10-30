from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import exact_keys, require, require_root, root


def make_operational_backup(*, subject_root: str, state_capsule: dict[str, Any], generation: int, predecessor_backup_root: str | None, repository_root: str) -> dict[str, Any]:
    require(type(state_capsule) is dict and state_capsule.get("schema") == "ucl.ucm.operational_runtime_capsule.v1", "OPERATIONAL_BACKUP_CAPSULE_INVALID")
    capsule_body = {key: value for key, value in state_capsule.items() if key != "capsule_root"}
    require(state_capsule.get("capsule_root") == root(capsule_body), "OPERATIONAL_BACKUP_CAPSULE_INVALID")
    require(state_capsule.get("subject_root") == require_root(subject_root), "OPERATIONAL_BACKUP_SUBJECT_MISMATCH")
    require(type(state_capsule.get("sequence")) is int and type(state_capsule.get("sequence")) is not bool and state_capsule["sequence"] >= 0, "OPERATIONAL_BACKUP_CAPSULE_INVALID")
    require_root(state_capsule.get("head"))
    require(state_capsule.get("maximum_effect_class_executed") == "NONE" and state_capsule.get("standing") == "INFORMATION_ONLY" and state_capsule.get("authority_effect") == "NONE", "OPERATIONAL_BACKUP_CAPSULE_INVALID")
    require(type(generation) is int and type(generation) is not bool and generation > 0, "OPERATIONAL_BACKUP_GENERATION_INVALID")
    if generation == 1: require(predecessor_backup_root is None, "OPERATIONAL_BACKUP_PREDECESSOR_INVALID")
    else: require_root(predecessor_backup_root)
    body = {
        "schema": "ucl.ucm.operational_backup.v1", "subject_root": require_root(subject_root),
        "state_capsule_root": state_capsule["capsule_root"], "state_sequence": state_capsule["sequence"],
        "state_head": state_capsule["head"], "generation": generation,
        "predecessor_backup_root": predecessor_backup_root, "repository_root": require_root(repository_root),
        "encrypted_payload_required": True, "contains_private_material": False,
        "status": "UNBOUND_BACKUP_PROPOSAL", "effect_observed": "NONE",
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    }
    return {**body, "backup_root": root(body)}


def verify_operational_backup_chain(backups: Any, *, expected_subject_root: str, expected_capsule_root: str | None = None, expected_head: str | None = None, expected_sequence: int | None = None, expected_repository_root: str | None = None) -> dict[str, Any]:
    require(type(backups) is list and backups, "OPERATIONAL_BACKUP_CHAIN_INVALID")
    predecessor, prior_sequence = None, -1
    prior_state: tuple[str, str] | None = None
    for index, item in enumerate(backups, 1):
        item = exact_keys(item, {"schema", "subject_root", "state_capsule_root", "state_sequence", "state_head", "generation", "predecessor_backup_root", "repository_root", "encrypted_payload_required", "contains_private_material", "status", "effect_observed", "standing", "authority_effect", "backup_root"}, f"$.backups[{index - 1}]")
        body = {key: value for key, value in item.items() if key != "backup_root"}
        require(item["schema"] == "ucl.ucm.operational_backup.v1" and item["backup_root"] == root(body), "OPERATIONAL_BACKUP_ROOT_INVALID")
        require(item["subject_root"] == expected_subject_root and item["generation"] == index and item["predecessor_backup_root"] == predecessor, "OPERATIONAL_BACKUP_CHAIN_INVALID")
        require(type(item["state_sequence"]) is int and type(item["state_sequence"]) is not bool and item["state_sequence"] >= prior_sequence, "OPERATIONAL_BACKUP_ROLLBACK")
        require_root(item["state_capsule_root"]); require_root(item["state_head"]); require_root(item["repository_root"])
        require(item["encrypted_payload_required"] is True and item["contains_private_material"] is False and item["status"] == "UNBOUND_BACKUP_PROPOSAL" and item["effect_observed"] == "NONE" and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "OPERATIONAL_BACKUP_BOUNDARY_INVALID")
        if item["state_sequence"] == prior_sequence:
            require(prior_state == (item["state_capsule_root"], item["state_head"]), "OPERATIONAL_BACKUP_SEQUENCE_FORK")
        predecessor, prior_sequence = item["backup_root"], item["state_sequence"]
        prior_state = (item["state_capsule_root"], item["state_head"])
    latest = backups[-1]
    if expected_capsule_root is not None: require(latest["state_capsule_root"] == require_root(expected_capsule_root), "OPERATIONAL_BACKUP_LATEST_MISMATCH")
    if expected_head is not None: require(latest["state_head"] == require_root(expected_head), "OPERATIONAL_BACKUP_LATEST_MISMATCH")
    if expected_sequence is not None: require(type(expected_sequence) is int and type(expected_sequence) is not bool and latest["state_sequence"] == expected_sequence, "OPERATIONAL_BACKUP_LATEST_MISMATCH")
    if expected_repository_root is not None: require(all(item["repository_root"] == require_root(expected_repository_root) for item in backups), "OPERATIONAL_BACKUP_REPOSITORY_MISMATCH")
    return {"backup_count": len(backups), "latest_backup_root": predecessor, "latest_state_sequence": prior_sequence}


def make_operational_migration(*, subject_root: str, source_capsule_root: str, backup_root: str, target_profile_root: str, rollback_receipt_root: str) -> dict[str, Any]:
    body = {
        "schema": "ucl.ucm.operational_migration.v1", "subject_root": require_root(subject_root),
        "source_capsule_root": require_root(source_capsule_root), "backup_root": require_root(backup_root),
        "target_profile_root": require_root(target_profile_root), "rollback_receipt_root": require_root(rollback_receipt_root),
        "required_steps": ["VERIFY_SOURCE", "VERIFY_BACKUP", "STAGE_TARGET", "RESTORE_CAPSULE", "VERIFY_HEAD", "REHEARSE_ROLLBACK"],
        "status": "UNBOUND_MIGRATION_PROPOSAL", "executed": False, "effect_observed": "NONE",
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    }
    return {**body, "migration_root": root(body)}


def verify_operational_migration(*, plan: dict[str, Any], expected_subject_root: str, observed_source_root: str, observed_restored_root: str, step_evidence: dict[str, str]) -> dict[str, Any]:
    plan = exact_keys(plan, {"schema", "subject_root", "source_capsule_root", "backup_root", "target_profile_root", "rollback_receipt_root", "required_steps", "status", "executed", "effect_observed", "standing", "authority_effect", "migration_root"}, "$.migration")
    require(plan.get("schema") == "ucl.ucm.operational_migration.v1", "OPERATIONAL_MIGRATION_INVALID")
    plan_body = {key: value for key, value in plan.items() if key != "migration_root"}
    require(plan.get("migration_root") == root(plan_body) and plan.get("subject_root") == require_root(expected_subject_root), "OPERATIONAL_MIGRATION_INVALID")
    require(plan.get("status") == "UNBOUND_MIGRATION_PROPOSAL" and plan.get("executed") is False and plan.get("effect_observed") == "NONE" and plan.get("standing") == "INFORMATION_ONLY" and plan.get("authority_effect") == "NONE", "OPERATIONAL_MIGRATION_BOUNDARY_INVALID")
    require(plan.get("required_steps") == ["VERIFY_SOURCE", "VERIFY_BACKUP", "STAGE_TARGET", "RESTORE_CAPSULE", "VERIFY_HEAD", "REHEARSE_ROLLBACK"], "OPERATIONAL_MIGRATION_STEP_SET_INVALID")
    for field in ("source_capsule_root", "backup_root", "target_profile_root", "rollback_receipt_root"): require_root(plan[field])
    require(observed_source_root == plan["source_capsule_root"] == require_root(observed_restored_root), "OPERATIONAL_MIGRATION_STATE_MISMATCH")
    require(type(step_evidence) is dict and set(step_evidence) == set(plan["required_steps"]), "OPERATIONAL_MIGRATION_STEP_SET_INVALID")
    checked = {key: require_root(step_evidence[key]) for key in sorted(step_evidence)}
    body = {
        "schema": "ucl.ucm.operational_migration_rehearsal.v1", "migration_root": plan["migration_root"],
        "restored_capsule_root": observed_restored_root, "step_evidence": checked,
        "status": "PASS_REHEARSAL_ONLY", "migrated": False, "effect_observed": "NONE",
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    }
    return {**body, "rehearsal_root": root(body)}


from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .canonical import exact_keys, require, require_root, root


_VERSION = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


def make_application_package(
    *, subject_root: str, application_id: str, version: str, manifest_root: str,
    implementation_root: str, sdk_root: str, adapter_registry_root: str,
    migration_contract_root: str | None,
) -> dict[str, Any]:
    require(type(application_id) is str and application_id and type(version) is str and bool(_VERSION.fullmatch(version)), "APPLICATION_PACKAGE_IDENTITY_INVALID")
    if migration_contract_root is not None:
        migration_contract_root = require_root(migration_contract_root)
    body = {
        "schema": "ucl.ucm.application_package.v1",
        "subject_root": require_root(subject_root),
        "application_id": application_id,
        "version": version,
        "manifest_root": require_root(manifest_root),
        "implementation_root": require_root(implementation_root),
        "sdk_root": require_root(sdk_root),
        "adapter_registry_root": require_root(adapter_registry_root),
        "migration_contract_root": migration_contract_root,
        "installed": False,
        "released": False,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "package_root": root(body)}


def verify_application_package(value: Any, *, expected_subject_root: str) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "subject_root", "application_id", "version", "manifest_root", "implementation_root",
        "sdk_root", "adapter_registry_root", "migration_contract_root", "installed", "released",
        "standing", "authority_effect", "package_root",
    }, "$.application_package")
    body = {key: item[key] for key in item if key != "package_root"}
    require(item["schema"] == "ucl.ucm.application_package.v1" and item["package_root"] == root(body), "APPLICATION_PACKAGE_ROOT_INVALID")
    rebuilt = make_application_package(
        subject_root=expected_subject_root, application_id=item["application_id"], version=item["version"],
        manifest_root=item["manifest_root"], implementation_root=item["implementation_root"],
        sdk_root=item["sdk_root"], adapter_registry_root=item["adapter_registry_root"],
        migration_contract_root=item["migration_contract_root"],
    )
    require(rebuilt == item, "APPLICATION_PACKAGE_RECOMPUTATION_MISMATCH")
    return deepcopy(body)


def make_backup_receipt(
    *, subject_root: str, application_id: str, generation: int, state_capsule_root: str,
    supervisor_capsule_root: str, custody_capsule_root: str,
) -> dict[str, Any]:
    require(type(generation) is int and type(generation) is not bool and generation > 0, "BACKUP_GENERATION_INVALID")
    body = {
        "schema": "ucl.ucm.application_backup_receipt.v1",
        "subject_root": require_root(subject_root),
        "application_id": application_id,
        "generation": generation,
        "state_capsule_root": require_root(state_capsule_root),
        "supervisor_capsule_root": require_root(supervisor_capsule_root),
        "custody_capsule_root": require_root(custody_capsule_root),
        "status": "PASS_REFERENCE_ONLY",
        "effect_observed": "NONE",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "backup_root": root(body)}


def verify_backup_receipt(value: Any, *, expected_subject_root: str, expected_application_id: str) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "subject_root", "application_id", "generation", "state_capsule_root",
        "supervisor_capsule_root", "custody_capsule_root", "status", "effect_observed",
        "standing", "authority_effect", "backup_root",
    }, "$.backup")
    body = {key: item[key] for key in item if key != "backup_root"}
    require(item["schema"] == "ucl.ucm.application_backup_receipt.v1" and item["backup_root"] == root(body), "BACKUP_ROOT_INVALID")
    require(item["subject_root"] == require_root(expected_subject_root) and item["application_id"] == expected_application_id, "BACKUP_CONTEXT_MISMATCH")
    require(type(item["generation"]) is int and type(item["generation"]) is not bool and item["generation"] > 0, "BACKUP_GENERATION_INVALID")
    for name in ("state_capsule_root", "supervisor_capsule_root", "custody_capsule_root"):
        require_root(item[name])
    require(item["status"] == "PASS_REFERENCE_ONLY" and item["effect_observed"] == "NONE" and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "BACKUP_BOUNDARY_INVALID")
    return deepcopy(body)


def make_upgrade_plan(
    *, subject_root: str, installed_package: dict[str, Any], candidate_package: dict[str, Any],
    backup_receipt: dict[str, Any], compatibility_root: str, rollback_action_roots: list[str],
    migration_step_roots: list[str],
) -> dict[str, Any]:
    verify_application_package(installed_package, expected_subject_root=subject_root)
    verify_application_package(candidate_package, expected_subject_root=subject_root)
    require(installed_package["application_id"] == candidate_package["application_id"], "UPGRADE_APPLICATION_MISMATCH")
    require(installed_package["package_root"] != candidate_package["package_root"], "UPGRADE_PACKAGE_UNCHANGED")
    verify_backup_receipt(backup_receipt, expected_subject_root=subject_root, expected_application_id=installed_package["application_id"])
    require(rollback_action_roots == sorted(set(rollback_action_roots)) and rollback_action_roots, "UPGRADE_ROLLBACK_ACTION_SET_INVALID")
    require(migration_step_roots == sorted(set(migration_step_roots)), "UPGRADE_MIGRATION_STEP_SET_INVALID")
    for value in rollback_action_roots + migration_step_roots:
        require_root(value)
    body = {
        "schema": "ucl.ucm.application_upgrade_plan.v1",
        "subject_root": require_root(subject_root),
        "application_id": installed_package["application_id"],
        "from_package_root": installed_package["package_root"],
        "to_package_root": candidate_package["package_root"],
        "backup_root": backup_receipt["backup_root"],
        "compatibility_root": require_root(compatibility_root),
        "rollback_action_roots": rollback_action_roots,
        "migration_step_roots": migration_step_roots,
        "requires_external_os_sandbox": True,
        "status": "UNBOUND_PROPOSAL",
        "executable": False,
        "installed": False,
        "released": False,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "plan_root": root(body)}


def verify_upgrade_plan(
    value: Any, *, expected_subject_root: str, installed_package: dict[str, Any],
    candidate_package: dict[str, Any], backup_receipt: dict[str, Any],
) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "subject_root", "application_id", "from_package_root", "to_package_root",
        "backup_root", "compatibility_root", "rollback_action_roots", "migration_step_roots",
        "requires_external_os_sandbox", "status", "executable", "installed", "released",
        "standing", "authority_effect", "plan_root",
    }, "$.upgrade_plan")
    body = {key: item[key] for key in item if key != "plan_root"}
    require(item["schema"] == "ucl.ucm.application_upgrade_plan.v1" and item["plan_root"] == root(body), "UPGRADE_PLAN_ROOT_INVALID")
    rebuilt = make_upgrade_plan(
        subject_root=expected_subject_root, installed_package=installed_package, candidate_package=candidate_package,
        backup_receipt=backup_receipt, compatibility_root=item["compatibility_root"],
        rollback_action_roots=item["rollback_action_roots"], migration_step_roots=item["migration_step_roots"],
    )
    require(rebuilt == item, "UPGRADE_PLAN_RECOMPUTATION_MISMATCH")
    return deepcopy(body)


def make_lifecycle_rehearsal_receipt(
    *, upgrade_plan: dict[str, Any], backup_receipt: dict[str, Any],
    before_state_root: str, mutated_state_root: str, restored_state_root: str,
    platform_profile_root: str,
) -> dict[str, Any]:
    require(type(upgrade_plan) is dict and upgrade_plan.get("schema") == "ucl.ucm.application_upgrade_plan.v1", "UPGRADE_PLAN_INVALID")
    plan_body = {key: upgrade_plan[key] for key in upgrade_plan if key != "plan_root"}
    require(upgrade_plan.get("plan_root") == root(plan_body), "UPGRADE_PLAN_ROOT_INVALID")
    require(backup_receipt.get("backup_root") == upgrade_plan["backup_root"], "LIFECYCLE_BACKUP_MISMATCH")
    before = require_root(before_state_root); mutated = require_root(mutated_state_root); restored = require_root(restored_state_root)
    require(before != mutated and restored == before, "LIFECYCLE_ROLLBACK_NOT_BYTE_EXACT")
    body = {
        "schema": "ucl.ucm.application_lifecycle_rehearsal.v1",
        "subject_root": upgrade_plan["subject_root"],
        "application_id": upgrade_plan["application_id"],
        "upgrade_plan_root": upgrade_plan["plan_root"],
        "backup_root": backup_receipt["backup_root"],
        "before_state_root": before,
        "mutated_state_root": mutated,
        "restored_state_root": restored,
        "platform_profile_root": require_root(platform_profile_root),
        "status": "PASS_REFERENCE_ONLY",
        "host_changes": 0,
        "effect_observed": "NONE",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "rehearsal_root": root(body)}

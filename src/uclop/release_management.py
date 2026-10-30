from __future__ import annotations

from copy import deepcopy
import pathlib
import re
import unicodedata
from typing import Any

from .canonical import exact_keys, require, require_root, root
from .ecosystem import verify_application_manifest


_VERSION = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", "CLOCK$", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def _version(value: Any) -> tuple[int, int, int]:
    require(type(value) is str and bool(_VERSION.fullmatch(value)), "PACKAGE_VERSION_INVALID")
    return tuple(int(part) for part in value.split("."))  # type: ignore[return-value]


def _package_path(value: Any) -> tuple[str, str]:
    require(type(value) is str and value and value.isascii() and unicodedata.normalize("NFC", value) == value and "\\" not in value and not value.startswith("/") and "//" not in value, "PACKAGE_PATH_INVALID")
    path = pathlib.PurePosixPath(value)
    require(path.as_posix() == value and 1 <= len(path.parts) <= 16 and len(value.encode("utf-8")) <= 512, "PACKAGE_PATH_INVALID")
    for part in path.parts:
        require(part not in {"", ".", ".."} and not part.endswith((" ", ".")) and ":" not in part and len(part.encode("utf-8")) <= 128, "PACKAGE_PATH_INVALID")
        require(part.split(".", 1)[0].upper() not in _WINDOWS_RESERVED, "PACKAGE_PATH_INVALID")
    return value, value.casefold().rstrip(" .")


def build_application_package(
    *, manifest: dict[str, Any], file_rows: list[dict[str, Any]],
    compatibility: dict[str, Any], migration_roots: list[str], rollback_artifact_root: str,
) -> dict[str, Any]:
    verify_application_manifest(manifest)
    require(type(file_rows) is list and file_rows, "PACKAGE_FILE_SET_INVALID")
    checked: list[dict[str, Any]] = []
    paths: set[str] = set(); aliases: set[str] = set()
    for index, candidate in enumerate(file_rows):
        item = exact_keys(candidate, {"path", "sha256", "bytes"}, f"$.files[{index}]")
        checked_path, alias = _package_path(item["path"])
        require(checked_path not in paths and alias not in aliases, "PACKAGE_PATH_DUPLICATE")
        paths.add(checked_path); aliases.add(alias); require_root(item["sha256"])
        require(type(item["bytes"]) is int and type(item["bytes"]) is not bool and 0 <= item["bytes"] <= 64 * 1024 * 1024, "PACKAGE_FILE_SIZE_INVALID")
        checked.append({"path": item["path"], "sha256": item["sha256"], "bytes": item["bytes"]})
    require(checked == sorted(checked, key=lambda row: row["path"]), "PACKAGE_FILE_ORDER_INVALID")
    compatibility = exact_keys(compatibility, {"minimum_foundation_version", "maximum_foundation_major", "required_capability_roots"}, "$.compatibility")
    minimum = _version(compatibility["minimum_foundation_version"])
    require(type(compatibility["maximum_foundation_major"]) is int and type(compatibility["maximum_foundation_major"]) is not bool and compatibility["maximum_foundation_major"] >= minimum[0], "PACKAGE_COMPATIBILITY_INVALID")
    require(type(compatibility["required_capability_roots"]) is dict, "PACKAGE_COMPATIBILITY_INVALID")
    capability_roots = {key: require_root(value) for key, value in sorted(compatibility["required_capability_roots"].items())}
    require(set(capability_roots) == set(manifest["requested_capabilities"]), "PACKAGE_CAPABILITY_SET_MISMATCH")
    require(type(migration_roots) is list and migration_roots == sorted(migration_roots) and len(migration_roots) == len(set(migration_roots)), "PACKAGE_MIGRATION_SET_INVALID")
    for value in migration_roots:
        require_root(value)
    body = {
        "schema": "ucl.ucm.application_package.v1", "application_id": manifest["application_id"],
        "version": manifest["version"], "manifest_root": manifest["manifest_root"], "files": checked,
        "file_count": len(checked), "payload_root": root(checked),
        "compatibility": {"minimum_foundation_version": compatibility["minimum_foundation_version"], "maximum_foundation_major": compatibility["maximum_foundation_major"], "required_capability_roots": capability_roots},
        "migration_roots": list(migration_roots), "rollback_artifact_root": require_root(rollback_artifact_root),
        "installed": False, "released": False, "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    }
    return {**body, "package_root": root(body)}


def verify_application_package(value: Any, *, expected_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "application_id", "version", "manifest_root", "files", "file_count", "payload_root",
        "compatibility", "migration_roots", "rollback_artifact_root", "installed", "released", "standing",
        "authority_effect", "package_root",
    }, "$.package")
    body = {key: item[key] for key in item if key != "package_root"}
    require(item["schema"] == "ucl.ucm.application_package.v1" and item["package_root"] == root(body), "PACKAGE_ROOT_INVALID")
    require(type(item["files"]) is list and item["files"] and item["file_count"] == len(item["files"]) and item["payload_root"] == root(item["files"]), "PACKAGE_FILE_SET_INVALID")
    seen_paths: set[str] = set(); seen_aliases: set[str] = set()
    for index, row in enumerate(item["files"]):
        row = exact_keys(row, {"path", "sha256", "bytes"}, f"$.package.files[{index}]")
        checked_path, alias = _package_path(row["path"])
        require(checked_path not in seen_paths and alias not in seen_aliases, "PACKAGE_PATH_DUPLICATE"); seen_paths.add(checked_path); seen_aliases.add(alias)
        require_root(row["sha256"])
        require(type(row["bytes"]) is int and type(row["bytes"]) is not bool and 0 <= row["bytes"] <= 64 * 1024 * 1024, "PACKAGE_FILE_SIZE_INVALID")
    require([row["path"] for row in item["files"]] == sorted(seen_paths), "PACKAGE_FILE_ORDER_INVALID")
    _version(item["version"]); require_root(item["manifest_root"]); require_root(item["rollback_artifact_root"])
    compatibility = exact_keys(item["compatibility"], {"minimum_foundation_version", "maximum_foundation_major", "required_capability_roots"}, "$.package.compatibility")
    minimum = _version(compatibility["minimum_foundation_version"])
    require(type(compatibility["maximum_foundation_major"]) is int and type(compatibility["maximum_foundation_major"]) is not bool and compatibility["maximum_foundation_major"] >= minimum[0], "PACKAGE_COMPATIBILITY_INVALID")
    require(type(compatibility["required_capability_roots"]) is dict, "PACKAGE_COMPATIBILITY_INVALID")
    for capability_root in compatibility["required_capability_roots"].values(): require_root(capability_root)
    require(type(item["migration_roots"]) is list and item["migration_roots"] == sorted(item["migration_roots"]) and len(item["migration_roots"]) == len(set(item["migration_roots"])), "PACKAGE_MIGRATION_SET_INVALID")
    for migration_root in item["migration_roots"]: require_root(migration_root)
    require(item["installed"] is False and item["released"] is False and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "PACKAGE_AUTHORITY_INVALID")
    if expected_manifest is not None:
        verify_application_manifest(expected_manifest)
        require(item["application_id"] == expected_manifest["application_id"] and item["version"] == expected_manifest["version"] and item["manifest_root"] == expected_manifest["manifest_root"], "PACKAGE_MANIFEST_MISMATCH")
        require(set(compatibility["required_capability_roots"]) == set(expected_manifest["requested_capabilities"]), "PACKAGE_CAPABILITY_SET_MISMATCH")
    if expected_manifest is not None:
        rebuilt = build_application_package(manifest=expected_manifest, file_rows=item["files"], compatibility=item["compatibility"], migration_roots=item["migration_roots"], rollback_artifact_root=item["rollback_artifact_root"])
        require(rebuilt == item, "PACKAGE_RECOMPUTATION_MISMATCH")
    return deepcopy(body)


def plan_upgrade(
    *, installed_package: dict[str, Any], candidate_package: dict[str, Any],
    installed_manifest: dict[str, Any], candidate_manifest: dict[str, Any], foundation_version: str,
    observed_capability_roots: dict[str, str], state_capsule_root: str, backup_root: str,
) -> dict[str, Any]:
    verify_application_package(installed_package, expected_manifest=installed_manifest)
    verify_application_package(candidate_package, expected_manifest=candidate_manifest)
    require(installed_package["application_id"] == candidate_package["application_id"], "UPGRADE_APPLICATION_MISMATCH")
    old_version, new_version, foundation = _version(installed_package["version"]), _version(candidate_package["version"]), _version(foundation_version)
    require(new_version > old_version, "UPGRADE_VERSION_NOT_FORWARD")
    compatibility = candidate_package["compatibility"]
    require(foundation >= _version(compatibility["minimum_foundation_version"]) and foundation[0] <= compatibility["maximum_foundation_major"], "UPGRADE_FOUNDATION_INCOMPATIBLE")
    require(type(observed_capability_roots) is dict and set(observed_capability_roots) == set(compatibility["required_capability_roots"]), "UPGRADE_CAPABILITY_ROOTS_INVALID")
    for capability_id, required_root in compatibility["required_capability_roots"].items():
        require(observed_capability_roots.get(capability_id) == required_root, "UPGRADE_CAPABILITY_MISMATCH", detail=capability_id)
    body = {
        "schema": "ucl.ucm.application_upgrade_plan.v1", "application_id": installed_package["application_id"],
        "from_package_root": installed_package["package_root"], "to_package_root": candidate_package["package_root"],
        "installed_manifest_root": installed_manifest["manifest_root"], "candidate_manifest_root": candidate_manifest["manifest_root"],
        "foundation_version": foundation_version, "observed_capability_roots": {key: require_root(value) for key, value in sorted(observed_capability_roots.items())},
        "state_capsule_root": require_root(state_capsule_root), "backup_root": require_root(backup_root),
        "migration_roots": candidate_package["migration_roots"], "rollback_artifact_root": candidate_package["rollback_artifact_root"],
        "compatibility_verified": True, "status": "UNBOUND_UPGRADE_PROPOSAL", "executed": False,
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    }
    return {**body, "upgrade_plan_root": root(body)}


def verify_upgrade_plan(
    value: Any, *, installed_package: dict[str, Any], candidate_package: dict[str, Any],
    installed_manifest: dict[str, Any], candidate_manifest: dict[str, Any],
) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "application_id", "from_package_root", "to_package_root", "installed_manifest_root",
        "candidate_manifest_root", "foundation_version", "observed_capability_roots", "state_capsule_root",
        "backup_root", "migration_roots", "rollback_artifact_root", "compatibility_verified", "status",
        "executed", "standing", "authority_effect", "upgrade_plan_root",
    }, "$.upgrade_plan")
    body = {key: item[key] for key in item if key != "upgrade_plan_root"}
    require(item["schema"] == "ucl.ucm.application_upgrade_plan.v1" and item["upgrade_plan_root"] == root(body), "UPGRADE_PLAN_INVALID")
    rebuilt = plan_upgrade(
        installed_package=installed_package, candidate_package=candidate_package,
        installed_manifest=installed_manifest, candidate_manifest=candidate_manifest,
        foundation_version=item["foundation_version"], observed_capability_roots=item["observed_capability_roots"],
        state_capsule_root=item["state_capsule_root"], backup_root=item["backup_root"],
    )
    require(rebuilt == item, "UPGRADE_PLAN_RECOMPUTATION_MISMATCH")
    return deepcopy(body)


def make_rollback_receipt(
    *, upgrade_plan: dict[str, Any], installed_package: dict[str, Any], candidate_package: dict[str, Any],
    installed_manifest: dict[str, Any], candidate_manifest: dict[str, Any],
    observed_restored_package_root: str, observed_restored_state_root: str, evidence_roots: list[str],
) -> dict[str, Any]:
    verify_upgrade_plan(upgrade_plan, installed_package=installed_package, candidate_package=candidate_package, installed_manifest=installed_manifest, candidate_manifest=candidate_manifest)
    require(observed_restored_package_root == upgrade_plan["from_package_root"], "ROLLBACK_PACKAGE_MISMATCH")
    require(observed_restored_state_root == upgrade_plan["state_capsule_root"], "ROLLBACK_STATE_MISMATCH")
    require(type(evidence_roots) is list and evidence_roots == sorted(evidence_roots) and evidence_roots, "ROLLBACK_EVIDENCE_INVALID")
    for value in evidence_roots: require_root(value)
    body = {
        "schema": "ucl.ucm.application_rollback_receipt.v1", "upgrade_plan_root": upgrade_plan["upgrade_plan_root"],
        "restored_package_root": observed_restored_package_root, "restored_state_root": observed_restored_state_root,
        "evidence_roots": list(evidence_roots), "status": "REHEARSED", "executed_on_host": False,
        "effect_observed": "NONE", "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    }
    return {**body, "rollback_receipt_root": root(body)}


def verify_rollback_receipt(value: Any, *, expected_upgrade_plan_root: str) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "upgrade_plan_root", "restored_package_root", "restored_state_root", "evidence_roots",
        "status", "executed_on_host", "effect_observed", "standing", "authority_effect", "rollback_receipt_root",
    }, "$.rollback_receipt")
    body = {key: item[key] for key in item if key != "rollback_receipt_root"}
    require(item["schema"] == "ucl.ucm.application_rollback_receipt.v1" and item["rollback_receipt_root"] == root(body), "ROLLBACK_RECEIPT_INVALID")
    require(item["upgrade_plan_root"] == require_root(expected_upgrade_plan_root), "ROLLBACK_RECEIPT_PLAN_MISMATCH")
    for field in ("upgrade_plan_root", "restored_package_root", "restored_state_root"):
        require_root(item[field])
    require(type(item["evidence_roots"]) is list and item["evidence_roots"] == sorted(item["evidence_roots"]) and item["evidence_roots"], "ROLLBACK_EVIDENCE_INVALID")
    for value_root in item["evidence_roots"]: require_root(value_root)
    require(item["status"] == "REHEARSED" and item["executed_on_host"] is False and item["effect_observed"] == "NONE" and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "ROLLBACK_RECEIPT_BOUNDARY_INVALID")
    return deepcopy(body)


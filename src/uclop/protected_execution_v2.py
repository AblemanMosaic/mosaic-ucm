from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import exact_keys, require, require_root, root
from .platform_profiles import verify_platform_profile


REQUIRED_FEATURES = {
    "POSIX": {"external.os_sandbox", "filesystem.allowlist", "network.deny", "process.limit", "resource.limit"},
    "WINDOWS": {"external.os_sandbox", "filesystem.acl", "network.deny", "process.restricted_token", "resource.job_object"},
}


def make_protected_execution_contract(
    *, subject_root: str, profile: dict[str, Any], candidate_root: str,
    candidate_manifest_root: str, entrypoint_root: str, allowed_read_roots: list[str],
    allowed_write_roots: list[str], memory_bytes: int, cpu_seconds: int, process_limit: int,
) -> dict[str, Any]:
    verify_platform_profile(profile)
    platform = profile["platform"]
    require(REQUIRED_FEATURES[platform].issubset(set(profile["isolation_features"])), "PROTECTED_PROFILE_FEATURES_INCOMPLETE")
    require(profile["network_default"] == "DENY" and profile["persistent_changes_allowed"] is False, "PROTECTED_PROFILE_BOUNDARY_INVALID")
    require(allowed_read_roots == sorted(set(allowed_read_roots)) and allowed_write_roots == sorted(set(allowed_write_roots)), "PROTECTED_ROOT_SET_INVALID")
    require(set(allowed_write_roots).issubset(allowed_read_roots), "PROTECTED_WRITE_ROOT_NOT_READABLE")
    for value in allowed_read_roots + allowed_write_roots:
        require_root(value)
    for value, code in ((memory_bytes, "MEMORY"), (cpu_seconds, "CPU"), (process_limit, "PROCESS")):
        require(type(value) is int and type(value) is not bool and value > 0, f"PROTECTED_{code}_LIMIT_INVALID")
    require(memory_bytes <= 8 * 1024 * 1024 * 1024 and cpu_seconds <= 86_400 and process_limit <= 64, "PROTECTED_RESOURCE_LIMIT_EXCESSIVE")
    body = {
        "schema": "ucl.ucm.protected_execution_contract.v2",
        "subject_root": require_root(subject_root),
        "profile_root": profile["profile_root"],
        "platform": platform,
        "candidate_root": require_root(candidate_root),
        "candidate_manifest_root": require_root(candidate_manifest_root),
        "entrypoint_root": require_root(entrypoint_root),
        "allowed_read_roots": allowed_read_roots,
        "allowed_write_roots": allowed_write_roots,
        "network_policy": "DENY",
        "memory_bytes": memory_bytes,
        "cpu_seconds": cpu_seconds,
        "process_limit": process_limit,
        "single_invocation": True,
        "external_os_sandbox_required": True,
        "persistent_host_changes_allowed": False,
        "status": "UNBOUND_CONTRACT",
        "executable": False,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "contract_root": root(body)}


def verify_protected_execution_contract(
    value: Any, *, expected_subject_root: str, expected_profile: dict[str, Any],
) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "subject_root", "profile_root", "platform", "candidate_root",
        "candidate_manifest_root", "entrypoint_root", "allowed_read_roots", "allowed_write_roots",
        "network_policy", "memory_bytes", "cpu_seconds", "process_limit", "single_invocation",
        "external_os_sandbox_required", "persistent_host_changes_allowed", "status", "executable",
        "standing", "authority_effect", "contract_root",
    }, "$.protected_execution_contract")
    body = {key: item[key] for key in item if key != "contract_root"}
    require(item["schema"] == "ucl.ucm.protected_execution_contract.v2" and item["contract_root"] == root(body), "PROTECTED_CONTRACT_ROOT_INVALID")
    rebuilt = make_protected_execution_contract(
        subject_root=expected_subject_root, profile=expected_profile, candidate_root=item["candidate_root"],
        candidate_manifest_root=item["candidate_manifest_root"], entrypoint_root=item["entrypoint_root"],
        allowed_read_roots=item["allowed_read_roots"], allowed_write_roots=item["allowed_write_roots"],
        memory_bytes=item["memory_bytes"], cpu_seconds=item["cpu_seconds"], process_limit=item["process_limit"],
    )
    require(rebuilt == item, "PROTECTED_CONTRACT_RECOMPUTATION_MISMATCH")
    return deepcopy(body)


def verify_external_execution_receipt(
    value: Any, *, contract: dict[str, Any], expected_executor_root: str,
    expected_executor_attestation_root: str, expected_subject_root: str,
    expected_profile: dict[str, Any],
) -> dict[str, Any]:
    verify_protected_execution_contract(
        contract, expected_subject_root=expected_subject_root,
        expected_profile=expected_profile,
    )
    item = exact_keys(value, {
        "schema", "contract_root", "candidate_root", "executor_root", "executor_attestation_root", "invocations", "exit_code",
        "network_attempts", "outside_write_attempts", "candidate_unchanged", "result_root", "status",
        "real_a5", "g0", "standing", "authority_effect", "receipt_root",
    }, "$.protected_execution_receipt")
    body = {key: item[key] for key in item if key != "receipt_root"}
    require(item["schema"] == "ucl.ucm.external_protected_execution_receipt.v2" and item["receipt_root"] == root(body), "PROTECTED_RECEIPT_ROOT_INVALID")
    require(item["contract_root"] == contract["contract_root"] and item["candidate_root"] == contract["candidate_root"], "PROTECTED_RECEIPT_CONTRACT_MISMATCH")
    require(item["executor_root"] == require_root(expected_executor_root), "PROTECTED_RECEIPT_EXECUTOR_MISMATCH")
    require(item["executor_attestation_root"] == require_root(expected_executor_attestation_root), "PROTECTED_RECEIPT_ATTESTATION_MISMATCH")
    require(item["invocations"] == 1 and item["exit_code"] == 0, "PROTECTED_RECEIPT_EXECUTION_INVALID")
    require(item["network_attempts"] == 0 and item["outside_write_attempts"] == 0 and item["candidate_unchanged"] is True, "PROTECTED_RECEIPT_BOUNDARY_VIOLATION")
    require_root(item["result_root"])
    require(item["status"] == "PASS" and item["real_a5"] is False and item["g0"] == "CLOSED" and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "PROTECTED_RECEIPT_AUTHORITY_INVALID")
    return deepcopy(body)

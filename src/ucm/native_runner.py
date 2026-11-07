"""Pinned adapter contract for the native AOK courthouse HeadlessRunner.

UCM never becomes the effect executor.  It validates an exact installed binding,
derives a preflight decision, and verifies a terminal receipt emitted by the
native owner.  An absent lattice or adapter is a typed refusal, not permission
to fall back to an ungoverned subprocess.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY


BINDING_SCHEMA = "mosaic.ucm.native-headless-runner-binding.v0.1"
PREFLIGHT_SCHEMA = "mosaic.ucm.native-headless-runner-preflight.v0.1"
RECEIPT_SCHEMA = "mosaic.ucm.native-headless-runner-terminal-receipt.v0.1"
NATIVE_OWNER = "AOK_COURTHOUSE_HEADLESS_RUNNER"
PROVIDERS = {
    "CODEX_HEADLESS_LOCAL",
    "GIE_LOCAL_MODEL_SHADOW",
    "TRUSTED_BROWSER_RUNTIME_SHADOW",
}
TRANSPORTS = {
    "FIXED_ARGV_LOCAL_PROCESS",
    "GIE_PROVIDER_PROCESS",
    "EXACT_ORIGIN_GOVERNED_BROWSER",
}


def _identifier(value: Any, code: str) -> str:
    require(type(value) is str and value == value.strip() and 0 < len(value) <= 192
            and all(ch.isalnum() or ch in "._:-" for ch in value), code)
    return value


def validate_binding(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "native_owner", "runner_id", "provider", "transport",
        "source_sha256", "source_manifest_root", "runner_contract_sha256",
        "console_contract_sha256", "installed_lattice_root", "adapter_root",
        "binding_status", "reason_code", "effect_executor", "standing",
        "authority_effect", "real_a5", "g0", "binding_root",
    })
    require(item["schema"] == BINDING_SCHEMA and item["native_owner"] == NATIVE_OWNER,
            "NATIVE_RUNNER_BINDING_SCHEMA_INVALID")
    _identifier(item["runner_id"], "NATIVE_RUNNER_ID_INVALID")
    require(item["provider"] in PROVIDERS and item["transport"] in TRANSPORTS,
            "NATIVE_RUNNER_ROUTE_INVALID")
    for key in ("source_sha256", "source_manifest_root", "runner_contract_sha256",
                "console_contract_sha256"):
        require_root(item[key])
    require(item["binding_status"] in {"BOUND", "UNAVAILABLE"},
            "NATIVE_RUNNER_BINDING_STATUS_INVALID")
    if item["binding_status"] == "BOUND":
        require_root(item["installed_lattice_root"])
        require_root(item["adapter_root"])
        require(item["reason_code"] == "NATIVE_RUNNER_BOUND",
                "NATIVE_RUNNER_BINDING_REASON_INVALID")
    else:
        require(item["installed_lattice_root"] is None and item["adapter_root"] is None
                and item["reason_code"] in {"CAPABILITY_LATTICE_ABSENT",
                                            "NATIVE_RUNNER_BINDING_UNAVAILABLE"},
                "NATIVE_RUNNER_BINDING_REASON_INVALID")
    require(item["effect_executor"] == NATIVE_OWNER,
            "NATIVE_RUNNER_EFFECT_OWNER_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "NATIVE_RUNNER_AUTHORITY_CEILING_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "binding_root"}
    require(item["binding_root"] == root(body), "NATIVE_RUNNER_BINDING_ROOT_INVALID")
    return deepcopy(item)


def build_unavailable_binding(*, runner_id: str, provider: str, transport: str,
                              source_sha256: str, source_manifest_root: str,
                              runner_contract_sha256: str,
                              console_contract_sha256: str,
                              reason_code: str = "CAPABILITY_LATTICE_ABSENT") -> dict[str, Any]:
    body = {
        "schema": BINDING_SCHEMA,
        "native_owner": NATIVE_OWNER,
        "runner_id": runner_id,
        "provider": provider,
        "transport": transport,
        "source_sha256": source_sha256,
        "source_manifest_root": source_manifest_root,
        "runner_contract_sha256": runner_contract_sha256,
        "console_contract_sha256": console_contract_sha256,
        "installed_lattice_root": None,
        "adapter_root": None,
        "binding_status": "UNAVAILABLE",
        "reason_code": reason_code,
        "effect_executor": NATIVE_OWNER,
        **BOUNDARY,
    }
    return validate_binding({**body, "binding_root": root(body)})


def build_preflight(*, run_contract_root: str, execution_context_root: str,
                    binding: Any, requested_effect_classes: list[str],
                    execution_authorized: bool) -> dict[str, Any]:
    checked = validate_binding(binding)
    require_root(run_contract_root)
    require_root(execution_context_root)
    require(type(requested_effect_classes) is list
            and requested_effect_classes == sorted(set(requested_effect_classes))
            and all(type(row) is str and row for row in requested_effect_classes),
            "NATIVE_RUNNER_EFFECT_INVENTORY_INVALID")
    require(type(execution_authorized) is bool,
            "NATIVE_RUNNER_AUTHORIZATION_FLAG_INVALID")
    allowed = checked["binding_status"] == "BOUND" and execution_authorized
    reason = "PREFLIGHT_READY" if allowed else (
        checked["reason_code"] if checked["binding_status"] != "BOUND"
        else "EXECUTION_AUTHORITY_NOT_GRANTED")
    body = {
        "schema": PREFLIGHT_SCHEMA,
        "run_contract_root": run_contract_root,
        "execution_context_root": execution_context_root,
        "binding_root": checked["binding_root"],
        "native_owner": NATIVE_OWNER,
        "provider": checked["provider"],
        "requested_effect_classes": requested_effect_classes,
        "decision": "ALLOW" if allowed else "REFUSE",
        "reason_code": reason,
        "fallback_execution_allowed": False,
        **BOUNDARY,
    }
    return {**body, "preflight_root": root(body)}


def validate_terminal_receipt(value: Any, *, expected_preflight: Any) -> dict[str, Any]:
    preflight = exact_keys(expected_preflight, {
        "schema", "run_contract_root", "execution_context_root", "binding_root",
        "native_owner", "provider", "requested_effect_classes", "decision",
        "reason_code", "fallback_execution_allowed", "standing",
        "authority_effect", "real_a5", "g0", "preflight_root",
    })
    require(preflight["schema"] == PREFLIGHT_SCHEMA
            and preflight["preflight_root"] == root({
                key: deepcopy(raw) for key, raw in preflight.items()
                if key != "preflight_root"
            }), "NATIVE_RUNNER_PREFLIGHT_INVALID")
    require(preflight["decision"] == "ALLOW", "NATIVE_RUNNER_PREFLIGHT_REFUSED")
    item = exact_keys(value, {
        "schema", "preflight_root", "native_owner", "provider", "lease_ref",
        "terminal_event_ref", "terminal_state", "result_root", "observed_effect_classes",
        "completion_status", "recovery_status", "standing", "authority_effect",
        "real_a5", "g0", "receipt_root",
    })
    require(item["schema"] == RECEIPT_SCHEMA
            and item["preflight_root"] == preflight["preflight_root"]
            and item["native_owner"] == NATIVE_OWNER
            and item["provider"] == preflight["provider"],
            "NATIVE_RUNNER_RECEIPT_BINDING_INVALID")
    for key in ("lease_ref", "terminal_event_ref", "result_root"):
        require_root(item[key])
    require(item["terminal_state"] in {"COMPLETED", "CANCELLED", "FAILED"}
            and item["completion_status"] in {"COMPLETE", "REFUSED", "INCOMPLETE"}
            and item["recovery_status"] in {"NOT_REQUIRED", "COMPLETE", "REQUIRED"},
            "NATIVE_RUNNER_TERMINAL_STATUS_INVALID")
    require(type(item["observed_effect_classes"]) is list
            and item["observed_effect_classes"] == sorted(set(item["observed_effect_classes"]))
            and set(item["observed_effect_classes"]).issubset(
                set(preflight["requested_effect_classes"])),
            "NATIVE_RUNNER_EFFECT_OBSERVATION_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "NATIVE_RUNNER_AUTHORITY_CEILING_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "receipt_root"}
    require(item["receipt_root"] == root(body), "NATIVE_RUNNER_RECEIPT_ROOT_INVALID")
    return deepcopy(item)

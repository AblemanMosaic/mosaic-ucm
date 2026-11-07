from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .canonical import exact_keys, require, require_root, root, validate_value


ADAPTER_KINDS = {"FILESYSTEM", "DATABASE", "NETWORK", "MODEL", "UI", "IN_PROCESS"}
EFFECT_CLASSES = {"NONE", "READ_LOCAL", "WRITE_LOCAL", "READ_EXTERNAL", "NETWORK"}
_ID = re.compile(r"^[a-z][a-z0-9_.-]{2,95}$")


def _identifier(value: Any, code: str, path: str) -> str:
    require(type(value) is str and bool(_ID.fullmatch(value)), code, path)
    return value


def make_adapter_contract(
    *, subject_root: str, adapter_id: str, adapter_kind: str, capability_id: str,
    implementation_root: str, input_contract_root: str, output_contract_root: str,
    effect_class: str, deterministic: bool, idempotent: bool,
    required_platform_features: list[str],
) -> dict[str, Any]:
    subject_root = require_root(subject_root)
    _identifier(adapter_id, "ADAPTER_ID_INVALID", "$.adapter_id")
    _identifier(capability_id, "ADAPTER_CAPABILITY_ID_INVALID", "$.capability_id")
    require(adapter_kind in ADAPTER_KINDS and effect_class in EFFECT_CLASSES, "ADAPTER_CLASS_INVALID")
    require(type(deterministic) is bool and type(idempotent) is bool, "ADAPTER_BOOLEAN_INVALID")
    require(type(required_platform_features) is list and required_platform_features == sorted(set(required_platform_features)), "ADAPTER_FEATURE_SET_INVALID")
    require(all(type(item) is str and bool(_ID.fullmatch(item)) for item in required_platform_features), "ADAPTER_FEATURE_INVALID")
    if effect_class != "NONE":
        require(required_platform_features and "external.os_sandbox" in required_platform_features, "ADAPTER_EXTERNAL_SANDBOX_REQUIRED")
    body = {
        "schema": "ucl.ucm.adapter_contract.v1",
        "subject_root": subject_root,
        "adapter_id": adapter_id,
        "adapter_kind": adapter_kind,
        "capability_id": capability_id,
        "implementation_root": require_root(implementation_root),
        "input_contract_root": require_root(input_contract_root),
        "output_contract_root": require_root(output_contract_root),
        "effect_class": effect_class,
        "deterministic": deterministic,
        "idempotent": idempotent,
        "required_platform_features": required_platform_features,
        "fixture_execution_only": True,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "adapter_root": root(body)}


def verify_adapter_contract(value: Any, *, expected_subject_root: str | None = None) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "subject_root", "adapter_id", "adapter_kind", "capability_id",
        "implementation_root", "input_contract_root", "output_contract_root", "effect_class",
        "deterministic", "idempotent", "required_platform_features", "fixture_execution_only",
        "standing", "authority_effect", "adapter_root",
    }, "$.adapter")
    body = {key: item[key] for key in item if key != "adapter_root"}
    require(item["schema"] == "ucl.ucm.adapter_contract.v1" and item["adapter_root"] == root(body), "ADAPTER_ROOT_INVALID")
    if expected_subject_root is not None:
        require(item["subject_root"] == require_root(expected_subject_root), "ADAPTER_SUBJECT_MISMATCH")
    rebuilt = make_adapter_contract(
        subject_root=item["subject_root"], adapter_id=item["adapter_id"], adapter_kind=item["adapter_kind"],
        capability_id=item["capability_id"], implementation_root=item["implementation_root"],
        input_contract_root=item["input_contract_root"], output_contract_root=item["output_contract_root"],
        effect_class=item["effect_class"], deterministic=item["deterministic"], idempotent=item["idempotent"],
        required_platform_features=item["required_platform_features"],
    )
    require(rebuilt == item, "ADAPTER_CANONICAL_FORM_INVALID")
    return deepcopy(body)


def compile_adapter_registry(*, subject_root: str, contracts: list[dict[str, Any]]) -> dict[str, Any]:
    subject_root = require_root(subject_root)
    checked: dict[str, dict[str, Any]] = {}
    capabilities: set[str] = set()
    for contract in contracts:
        verify_adapter_contract(contract, expected_subject_root=subject_root)
        require(contract["adapter_id"] not in checked, "ADAPTER_DUPLICATE_ID")
        require(contract["capability_id"] not in capabilities, "ADAPTER_CAPABILITY_DUPLICATE")
        checked[contract["adapter_id"]] = deepcopy(contract)
        capabilities.add(contract["capability_id"])
    require(checked, "ADAPTER_REGISTRY_EMPTY")
    ordered = [checked[key] for key in sorted(checked)]
    body = {
        "schema": "ucl.ucm.adapter_registry.v1",
        "subject_root": subject_root,
        "contracts": ordered,
        "adapter_roots": {item["adapter_id"]: item["adapter_root"] for item in ordered},
        "capability_routes": {item["capability_id"]: item["adapter_id"] for item in ordered},
        "effect_ceiling": "NETWORK",
        "all_effectful_routes_are_proposals": True,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "registry_root": root(body)}


def verify_adapter_registry(value: Any, *, expected_subject_root: str) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "subject_root", "contracts", "adapter_roots", "capability_routes", "effect_ceiling",
        "all_effectful_routes_are_proposals", "standing", "authority_effect", "registry_root",
    }, "$.adapter_registry")
    body = {key: item[key] for key in item if key != "registry_root"}
    require(item["schema"] == "ucl.ucm.adapter_registry.v1" and item["registry_root"] == root(body), "ADAPTER_REGISTRY_ROOT_INVALID")
    rebuilt = compile_adapter_registry(subject_root=expected_subject_root, contracts=item["contracts"])
    require(rebuilt == item, "ADAPTER_REGISTRY_RECOMPUTATION_MISMATCH")
    return deepcopy(body)


def make_adapter_invocation(
    *, subject_root: str, registry: dict[str, Any], adapter_id: str, application_root: str,
    tenant_id: str, caller_principal_root: str, input_value: Any, idempotency_key: str,
) -> dict[str, Any]:
    verify_adapter_registry(registry, expected_subject_root=subject_root)
    require(adapter_id in registry["adapter_roots"], "ADAPTER_NOT_REGISTERED")
    contract = next(item for item in registry["contracts"] if item["adapter_id"] == adapter_id)
    _identifier(tenant_id, "ADAPTER_TENANT_ID_INVALID", "$.tenant_id")
    require(type(idempotency_key) is str and 8 <= len(idempotency_key) <= 128, "ADAPTER_IDEMPOTENCY_KEY_INVALID")
    validate_value(input_value)
    effectful = contract["effect_class"] != "NONE"
    body = {
        "schema": "ucl.ucm.adapter_invocation.v1",
        "subject_root": require_root(subject_root),
        "registry_root": registry["registry_root"],
        "adapter_id": adapter_id,
        "adapter_root": contract["adapter_root"],
        "application_root": require_root(application_root),
        "tenant_id": tenant_id,
        "caller_principal_root": require_root(caller_principal_root),
        "input_root": root(input_value),
        "idempotency_key": idempotency_key,
        "effect_class": contract["effect_class"],
        "disposition": "UNBOUND_EFFECT_PROPOSAL" if effectful else "FIXTURE_EXECUTION_ELIGIBLE",
        "executable": not effectful,
        "effect_observed": "NONE",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "invocation_root": root(body)}


def make_fixture_adapter_receipt(
    *, invocation: dict[str, Any], output_value: Any, adapter_contract: dict[str, Any],
) -> dict[str, Any]:
    verify_adapter_contract(adapter_contract, expected_subject_root=invocation.get("subject_root"))
    item = exact_keys(invocation, {
        "schema", "subject_root", "registry_root", "adapter_id", "adapter_root", "application_root",
        "tenant_id", "caller_principal_root", "input_root", "idempotency_key", "effect_class",
        "disposition", "executable", "effect_observed", "standing", "authority_effect", "invocation_root",
    }, "$.invocation")
    body = {key: item[key] for key in item if key != "invocation_root"}
    require(item["schema"] == "ucl.ucm.adapter_invocation.v1" and item["invocation_root"] == root(body), "ADAPTER_INVOCATION_ROOT_INVALID")
    require(item["adapter_root"] == adapter_contract["adapter_root"] and item["adapter_id"] == adapter_contract["adapter_id"], "ADAPTER_INVOCATION_CONTRACT_MISMATCH")
    require(item["effect_class"] == "NONE" and item["executable"] is True and item["disposition"] == "FIXTURE_EXECUTION_ELIGIBLE", "ADAPTER_FIXTURE_EFFECT_REFUSED")
    validate_value(output_value)
    receipt_body = {
        "schema": "ucl.ucm.fixture_adapter_receipt.v1",
        "subject_root": item["subject_root"],
        "invocation_root": item["invocation_root"],
        "adapter_root": adapter_contract["adapter_root"],
        "output_root": root(output_value),
        "status": "PASS_FIXTURE_ONLY",
        "effect_observed": "NONE",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**receipt_body, "receipt_root": root(receipt_body)}

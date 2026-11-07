from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .canonical import exact_keys, require, require_root, root, validate_value
from .composition import verify_composition
from .ecosystem import (
    EFFECT_CLASSES,
    effect_rank,
    verify_application_manifest,
    verify_capability_registry,
    verify_policy_bundle,
)


_ID = re.compile(r"^[a-z][a-z0-9_.-]{2,63}$")
_VERSION = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
FIELD_TYPES = {"NULL", "BOOLEAN", "INTEGER", "STRING", "ROOT", "LIST", "MAP"}


def _identifier(value: Any, code: str, path: str) -> str:
    require(type(value) is str and bool(_ID.fullmatch(value)), code, path)
    return value


def _version(value: Any, path: str) -> str:
    require(type(value) is str and bool(_VERSION.fullmatch(value)), "SEMANTIC_VERSION_INVALID", path)
    return value


def make_data_contract(*, contract_id: str, version: str, fields: list[dict[str, Any]], allow_unknown: bool = False) -> dict[str, Any]:
    _identifier(contract_id, "CONTRACT_ID_INVALID", "$.contract_id")
    _version(version, "$.version")
    require(type(allow_unknown) is bool and allow_unknown is False, "CONTRACT_UNKNOWN_FIELDS_MUST_REFUSE")
    require(type(fields) is list and fields, "CONTRACT_FIELDS_INVALID")
    checked: list[dict[str, Any]] = []
    names: list[str] = []
    for index, raw in enumerate(fields):
        item = exact_keys(raw, {"name", "type", "required"}, f"$.fields[{index}]")
        name = _identifier(item["name"], "CONTRACT_FIELD_NAME_INVALID", f"$.fields[{index}].name")
        require(item["type"] in FIELD_TYPES and type(item["required"]) is bool, "CONTRACT_FIELD_INVALID", f"$.fields[{index}]")
        names.append(name)
        checked.append({"name": name, "type": item["type"], "required": item["required"]})
    require(names == sorted(names) and len(names) == len(set(names)), "CONTRACT_FIELD_ORDER_INVALID")
    body = {
        "schema": "ucl.ucm.data_contract.v1",
        "contract_id": contract_id,
        "version": version,
        "fields": checked,
        "allow_unknown": False,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "contract_root": root(body)}


def verify_data_contract(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "contract_id", "version", "fields", "allow_unknown", "standing", "authority_effect", "contract_root"}, "$.contract")
    body = {key: item[key] for key in item if key != "contract_root"}
    require(item["schema"] == "ucl.ucm.data_contract.v1" and item["contract_root"] == root(body), "CONTRACT_ROOT_INVALID")
    rebuilt = make_data_contract(contract_id=item["contract_id"], version=item["version"], fields=item["fields"], allow_unknown=item["allow_unknown"])
    require(rebuilt == item, "CONTRACT_CANONICAL_FORM_INVALID")
    require(item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "CONTRACT_AUTHORITY_INVALID")
    return deepcopy(body)


def validate_contract_value(contract: dict[str, Any], value: Any) -> dict[str, Any]:
    verify_data_contract(contract)
    require(type(value) is dict, "CONTRACT_VALUE_OBJECT_REQUIRED")
    field_map = {item["name"]: item for item in contract["fields"]}
    require(set(value).issubset(field_map), "CONTRACT_VALUE_UNKNOWN_FIELD")
    required = {name for name, item in field_map.items() if item["required"]}
    require(required.issubset(value), "CONTRACT_VALUE_REQUIRED_FIELD_MISSING")
    for name, candidate in value.items():
        expected = field_map[name]["type"]
        ok = {
            "NULL": candidate is None,
            "BOOLEAN": type(candidate) is bool,
            "INTEGER": type(candidate) is int and type(candidate) is not bool,
            "STRING": type(candidate) is str,
            "ROOT": type(candidate) is str and len(candidate) == 64 and all(ch in "0123456789abcdef" for ch in candidate),
            "LIST": type(candidate) is list,
            "MAP": type(candidate) is dict,
        }[expected]
        require(ok, "CONTRACT_VALUE_TYPE_MISMATCH", f"$.value.{name}", expected)
    validate_value(value)
    body = {
        "schema": "ucl.ucm.contract_validation.v1",
        "contract_root": contract["contract_root"],
        "value_root": root(value),
        "status": "PASS",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "validation_root": root(body)}


def make_capability_request(
    *, application: dict[str, Any], capability_id: str, input_contract: dict[str, Any],
    input_value: dict[str, Any], idempotency_key: str,
) -> dict[str, Any]:
    verify_application_manifest(application)
    _identifier(capability_id, "CAPABILITY_ID_INVALID", "$.capability_id")
    require(capability_id in application["requested_capabilities"], "CAPABILITY_NOT_REQUESTED")
    require(type(idempotency_key) is str and 8 <= len(idempotency_key) <= 128, "IDEMPOTENCY_KEY_INVALID")
    validation = validate_contract_value(input_contract, input_value)
    body = {
        "schema": "ucl.ucm.sdk_capability_request.v1",
        "application_id": application["application_id"],
        "application_root": application["manifest_root"],
        "capability_id": capability_id,
        "input_contract_root": input_contract["contract_root"],
        "input_root": root(input_value),
        "validation_root": validation["validation_root"],
        "idempotency_key": idempotency_key,
        "effect_ceiling": "NONE",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "request_root": root(body)}


def compile_sdk_bundle(
    *, subject_root: str, sdk_version: str, registry: dict[str, Any], policy: dict[str, Any],
    contracts: list[dict[str, Any]], compositions: list[dict[str, Any]],
) -> dict[str, Any]:
    subject_root = require_root(subject_root)
    _version(sdk_version, "$.sdk_version")
    verify_capability_registry(registry, expected_subject_root=subject_root)
    verify_policy_bundle(policy, registry=registry, expected_subject_root=subject_root)
    contract_map: dict[str, dict[str, Any]] = {}
    for contract in contracts:
        verify_data_contract(contract)
        require(contract["contract_id"] not in contract_map, "CONTRACT_DUPLICATE_ID")
        contract_map[contract["contract_id"]] = deepcopy(contract)
    require(contract_map, "SDK_CONTRACT_SET_EMPTY")
    checked_compositions: list[dict[str, Any]] = []
    composition_ids: set[str] = set()
    for composition in compositions:
        verify_composition(composition, registry=registry, policy=policy, expected_subject_root=subject_root)
        require(composition["composition_id"] not in composition_ids, "COMPOSITION_DUPLICATE_ID")
        composition_ids.add(composition["composition_id"])
        checked_compositions.append(deepcopy(composition))
    checked_compositions.sort(key=lambda item: item["composition_id"])
    ordered_contracts = [contract_map[key] for key in sorted(contract_map)]
    body = {
        "schema": "ucl.ucm.application_sdk_bundle.v1",
        "subject_root": subject_root,
        "sdk_version": sdk_version,
        "registry_root": registry["registry_root"],
        "policy_root": policy["policy_root"],
        "contracts": ordered_contracts,
        "contract_roots": {item["contract_id"]: item["contract_root"] for item in ordered_contracts},
        "compositions": checked_compositions,
        "composition_roots": {item["composition_id"]: item["composition_root"] for item in checked_compositions},
        "supported_effect_ceiling": "NONE",
        "later_effects_are_proposals": True,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "sdk_root": root(body)}


def verify_sdk_bundle(
    value: Any, *, expected_subject_root: str, registry: dict[str, Any], policy: dict[str, Any],
) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "subject_root", "sdk_version", "registry_root", "policy_root", "contracts",
        "contract_roots", "compositions", "composition_roots", "supported_effect_ceiling",
        "later_effects_are_proposals", "standing", "authority_effect", "sdk_root",
    }, "$.sdk")
    body = {key: item[key] for key in item if key != "sdk_root"}
    require(item["schema"] == "ucl.ucm.application_sdk_bundle.v1" and item["sdk_root"] == root(body), "SDK_ROOT_INVALID")
    require(item["subject_root"] == require_root(expected_subject_root), "SDK_SUBJECT_MISMATCH")
    rebuilt = compile_sdk_bundle(
        subject_root=expected_subject_root, sdk_version=item["sdk_version"], registry=registry,
        policy=policy, contracts=item["contracts"], compositions=item["compositions"],
    )
    require(rebuilt == item, "SDK_RECOMPUTATION_MISMATCH")
    require(item["supported_effect_ceiling"] == "NONE" and item["later_effects_are_proposals"] is True, "SDK_EFFECT_CEILING_INVALID")
    return deepcopy(body)


def assess_sdk_compatibility(*, installed: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    for item in (installed, candidate):
        require(type(item) is dict and item.get("schema") == "ucl.ucm.application_sdk_bundle.v1", "SDK_INVALID")
        require(item.get("sdk_root") == root({key: value for key, value in item.items() if key != "sdk_root"}), "SDK_ROOT_INVALID")
    require(installed["subject_root"] == candidate["subject_root"], "SDK_SUBJECT_MISMATCH")
    installed_major = int(installed["sdk_version"].split(".")[0])
    candidate_major = int(candidate["sdk_version"].split(".")[0])
    removed_contracts = sorted(set(installed["contract_roots"]) - set(candidate["contract_roots"]))
    changed_contracts = sorted(key for key in set(installed["contract_roots"]) & set(candidate["contract_roots"]) if installed["contract_roots"][key] != candidate["contract_roots"][key])
    removed_compositions = sorted(set(installed["composition_roots"]) - set(candidate["composition_roots"]))
    compatible = candidate_major == installed_major and not removed_contracts and not changed_contracts and not removed_compositions
    body = {
        "schema": "ucl.ucm.sdk_compatibility.v1",
        "installed_sdk_root": installed["sdk_root"],
        "candidate_sdk_root": candidate["sdk_root"],
        "compatible": compatible,
        "removed_contracts": removed_contracts,
        "changed_contracts": changed_contracts,
        "removed_compositions": removed_compositions,
        "required_action": "NONE" if compatible else "REQUALIFY_AND_MIGRATE",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "compatibility_root": root(body)}

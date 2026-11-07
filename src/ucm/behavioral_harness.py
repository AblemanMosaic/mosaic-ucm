"""Controlled state-transition behavioral harness contracts and receipts.

UCM validates the boundary and an external executor's receipt.  Application
effects remain owned by the native executor named by the harness contract.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY


CONTRACT_SCHEMA = "mosaic.ucm.behavioral-harness-contract.v0.1"
RECEIPT_SCHEMA = "mosaic.ucm.behavioral-transition-receipt.v0.1"
CONTROLS = {"TIME", "RNG", "FILESYSTEM", "NETWORK", "PROCESS", "ENVIRONMENT"}


def _identifier(value: Any, code: str) -> str:
    require(type(value) is str and value == value.strip() and 0 < len(value) <= 192
            and all(ch.isalnum() or ch in "._:-" for ch in value), code)
    return value


def build_harness_contract(*, harness_id: str, subject_root: str,
                           state_adapter_root: str, action_generator_root: str,
                           executor_binding_root: str, required_controls: list[str],
                           allowed_write_paths: list[str], scenario_ids: list[str]) -> dict[str, Any]:
    _identifier(harness_id, "HARNESS_ID_INVALID")
    for value in (subject_root, state_adapter_root, action_generator_root,
                  executor_binding_root):
        require_root(value)
    require(type(required_controls) is list
            and required_controls == sorted(set(required_controls))
            and set(required_controls) <= CONTROLS,
            "HARNESS_CONTROLS_INVALID")
    require(type(allowed_write_paths) is list
            and allowed_write_paths == sorted(set(allowed_write_paths)),
            "HARNESS_WRITE_PATHS_INVALID")
    for path in allowed_write_paths:
        require(type(path) is str and path == path.strip() and bool(path)
                and "\\" not in path and not path.startswith("/") and ".." not in path.split("/"),
                "HARNESS_WRITE_PATH_INVALID")
    require(type(scenario_ids) is list and scenario_ids == sorted(set(scenario_ids))
            and bool(scenario_ids), "HARNESS_SCENARIOS_INVALID")
    for scenario_id in scenario_ids:
        _identifier(scenario_id, "HARNESS_SCENARIO_ID_INVALID")
    body = {"schema": CONTRACT_SCHEMA, "harness_id": harness_id,
            "subject_root": subject_root, "state_adapter_root": state_adapter_root,
            "action_generator_root": action_generator_root,
            "executor_binding_root": executor_binding_root,
            "required_controls": required_controls,
            "allowed_write_paths": allowed_write_paths,
            "scenario_ids": scenario_ids, "fixed_denominator": len(scenario_ids),
            "external_executor_required": True, "effect_claim": "NONE", **BOUNDARY}
    return {**body, "harness_contract_root": root(body)}


def validate_harness_contract(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "harness_id", "subject_root",
                              "state_adapter_root", "action_generator_root",
                              "executor_binding_root", "required_controls",
                              "allowed_write_paths", "scenario_ids", "fixed_denominator",
                              "external_executor_required", "effect_claim", "standing",
                              "authority_effect", "real_a5", "g0", "harness_contract_root"})
    expected = build_harness_contract(harness_id=item["harness_id"],
        subject_root=item["subject_root"], state_adapter_root=item["state_adapter_root"],
        action_generator_root=item["action_generator_root"],
        executor_binding_root=item["executor_binding_root"],
        required_controls=item["required_controls"],
        allowed_write_paths=item["allowed_write_paths"], scenario_ids=item["scenario_ids"])
    require(item == expected, "HARNESS_CONTRACT_INVALID")
    return deepcopy(item)


def build_transition_receipt(*, contract: dict[str, Any], scenario_id: str,
                             pre_state_root: str, action_root: str, post_state_root: str,
                             observed_controls: list[str], observed_write_paths: list[str],
                             executor_receipt_root: str, status: str,
                             reason_codes: list[str]) -> dict[str, Any]:
    contract = validate_harness_contract(contract)
    require(scenario_id in contract["scenario_ids"], "HARNESS_SCENARIO_UNKNOWN")
    for value in (pre_state_root, action_root, post_state_root, executor_receipt_root):
        require_root(value)
    require(type(observed_controls) is list
            and observed_controls == sorted(set(observed_controls))
            and set(observed_controls) <= CONTROLS, "HARNESS_OBSERVED_CONTROLS_INVALID")
    require(type(observed_write_paths) is list
            and observed_write_paths == sorted(set(observed_write_paths)),
            "HARNESS_OBSERVED_WRITES_INVALID")
    require(status in {"PASS", "REFUSED", "INCOMPLETE"}, "HARNESS_STATUS_INVALID")
    require(type(reason_codes) is list and reason_codes == sorted(set(reason_codes)),
            "HARNESS_REASON_CODES_INVALID")
    controls_complete = set(contract["required_controls"]) <= set(observed_controls)
    writes_allowed = set(observed_write_paths) <= set(contract["allowed_write_paths"])
    require((status == "PASS") == (controls_complete and writes_allowed),
            "HARNESS_PASS_CLAIM_INVALID")
    body = {"schema": RECEIPT_SCHEMA,
            "harness_contract_root": contract["harness_contract_root"],
            "scenario_id": scenario_id, "pre_state_root": pre_state_root,
            "action_root": action_root, "post_state_root": post_state_root,
            "observed_controls": observed_controls,
            "observed_write_paths": observed_write_paths,
            "controls_complete": controls_complete, "writes_allowed": writes_allowed,
            "executor_receipt_root": executor_receipt_root,
            "status": status, "reason_codes": reason_codes,
            "effect_claim": "OBSERVED_EXTERNAL_EXECUTOR_ONLY", **BOUNDARY}
    return {**body, "transition_receipt_root": root(body)}

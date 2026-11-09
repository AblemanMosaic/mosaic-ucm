"""Shared CM1 launcher contracts with application-specific CM2 presentation.

The module validates contracts and externally observed lifecycle receipts.  It
does not create a process; the effect executor remains external to UCM.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY


CONTRACT_SCHEMA = "mosaic.ucm.constitutional-launch-contract.v0.1"
OBSERVATION_SCHEMA = "mosaic.ucm.constitutional-launch-observation.v0.1"
STATE_SCHEMA = "mosaic.ucm.constitutional-launch-state.v0.1"
STATES = {"PREPARED", "STARTING", "READY", "FAILED", "CANCELLED", "TERMINATED", "UNCERTAIN"}
TERMINAL = {"FAILED", "CANCELLED", "TERMINATED"}


def _identifier(value: Any, code: str) -> str:
    require(type(value) is str and value == value.strip() and 0 < len(value) <= 192
            and all(ch.isalnum() or ch in "._:-" for ch in value), code)
    return value


def build_launch_contract(*, launch_id: str, application_id: str, subject_root: str,
                          executable_root: str, argument_root: str,
                          environment_policy_root: str, readiness_probe_id: str,
                          readiness_contract_root: str, timeout_ms: int,
                          executor_binding_root: str, branding: dict[str, Any]) -> dict[str, Any]:
    _identifier(launch_id, "LAUNCH_ID_INVALID")
    _identifier(application_id, "LAUNCH_APPLICATION_ID_INVALID")
    _identifier(readiness_probe_id, "LAUNCH_READINESS_PROBE_INVALID")
    for value in (subject_root, executable_root, argument_root, environment_policy_root,
                  readiness_contract_root, executor_binding_root):
        require_root(value)
    require(type(timeout_ms) is int and 1 <= timeout_ms <= 86_400_000,
            "LAUNCH_TIMEOUT_INVALID")
    branding = exact_keys(branding, {"display_name", "splash_asset_root", "phase_labels"})
    require(type(branding["display_name"]) is str and bool(branding["display_name"].strip()),
            "LAUNCH_DISPLAY_NAME_INVALID")
    require(branding["splash_asset_root"] is None or require_root(branding["splash_asset_root"]),
            "LAUNCH_SPLASH_ROOT_INVALID")
    require(type(branding["phase_labels"]) is dict and bool(branding["phase_labels"]),
            "LAUNCH_PHASE_LABELS_INVALID")
    for key, value in branding["phase_labels"].items():
        _identifier(key, "LAUNCH_PHASE_ID_INVALID")
        require(type(value) is str and bool(value.strip()), "LAUNCH_PHASE_LABEL_INVALID")
    body = {"schema": CONTRACT_SCHEMA, "launch_id": launch_id,
            "application_id": application_id, "subject_root": subject_root,
            "executable_root": executable_root, "argument_root": argument_root,
            "environment_policy_root": environment_policy_root,
            "readiness_probe_id": readiness_probe_id,
            "readiness_contract_root": readiness_contract_root,
            "timeout_ms": timeout_ms, "executor_binding_root": executor_binding_root,
            "cm1": {"exact_bindings_required": True,
                    "external_executor_required": True,
                    "three_gate_receipts_required": True,
                    "headless_console_policy": "NO_PERSISTENT_CONSOLE_WITHOUT_REQUEST",
                    "progress_semantics": "NONE",
                    "uncertain_policy": "RECONCILE_WITHOUT_RELAUNCH"},
            "cm2": deepcopy(branding), **BOUNDARY}
    return {**body, "launch_contract_root": root(body)}


def validate_launch_contract(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "launch_id", "application_id", "subject_root",
                              "executable_root", "argument_root", "environment_policy_root",
                              "readiness_probe_id", "readiness_contract_root", "timeout_ms",
                              "executor_binding_root", "cm1", "cm2", "standing",
                              "authority_effect", "real_a5", "g0", "launch_contract_root"})
    expected = build_launch_contract(launch_id=item["launch_id"],
        application_id=item["application_id"], subject_root=item["subject_root"],
        executable_root=item["executable_root"], argument_root=item["argument_root"],
        environment_policy_root=item["environment_policy_root"],
        readiness_probe_id=item["readiness_probe_id"],
        readiness_contract_root=item["readiness_contract_root"],
        timeout_ms=item["timeout_ms"], executor_binding_root=item["executor_binding_root"],
        branding=item["cm2"])
    require(item == expected, "LAUNCH_CONTRACT_INVALID")
    return deepcopy(item)


def build_launch_observation(*, contract: dict[str, Any], sequence: int, state: str,
                             previous_observation_root: str | None,
                             executor_receipt_root: str,
                             g1_root: str, g2_root: str | None, g3_root: str | None,
                             readiness_evidence_root: str | None,
                             reason_codes: list[str]) -> dict[str, Any]:
    contract = validate_launch_contract(contract)
    require(type(sequence) is int and sequence >= 1 and state in STATES,
            "LAUNCH_OBSERVATION_STATE_INVALID")
    require((sequence == 1) == (previous_observation_root is None),
            "LAUNCH_OBSERVATION_PREDECESSOR_INVALID")
    for value in (previous_observation_root, executor_receipt_root, g1_root, g2_root,
                  g3_root, readiness_evidence_root):
        require(value is None or require_root(value), "LAUNCH_OBSERVATION_ROOT_INVALID")
    require(state == "PREPARED" or previous_observation_root is not None,
            "LAUNCH_OBSERVATION_INITIAL_STATE_INVALID")
    require((state == "READY") is (readiness_evidence_root is not None),
            "LAUNCH_READINESS_EVIDENCE_INVALID")
    require((state in TERMINAL) is (g2_root is not None and g3_root is not None),
            "LAUNCH_TERMINAL_RECEIPTS_INVALID")
    require(type(reason_codes) is list and reason_codes == sorted(set(reason_codes)),
            "LAUNCH_REASON_CODES_INVALID")
    for code in reason_codes:
        _identifier(code, "LAUNCH_REASON_CODE_INVALID")
    body = {"schema": OBSERVATION_SCHEMA,
            "launch_contract_root": contract["launch_contract_root"],
            "sequence": sequence, "state": state,
            "previous_observation_root": previous_observation_root,
            "executor_receipt_root": executor_receipt_root, "g1_root": g1_root,
            "g2_root": g2_root, "g3_root": g3_root,
            "readiness_evidence_root": readiness_evidence_root,
            "reason_codes": reason_codes, **BOUNDARY}
    return {**body, "observation_root": root(body)}


def derive_launch_state(*, contract: dict[str, Any],
                        observations: list[dict[str, Any]]) -> dict[str, Any]:
    contract = validate_launch_contract(contract)
    require(type(observations) is list and bool(observations),
            "LAUNCH_OBSERVATIONS_INVALID")
    previous = None
    normalized = []
    transitions = {
        None: {"PREPARED"}, "PREPARED": {"STARTING", "CANCELLED"},
        "STARTING": {"READY", "FAILED", "CANCELLED", "UNCERTAIN"},
        "READY": {"TERMINATED", "FAILED", "UNCERTAIN"},
        "UNCERTAIN": {"READY", "FAILED", "TERMINATED"},
    }
    for index, item in enumerate(observations, 1):
        require(type(item) is dict and item.get("schema") == OBSERVATION_SCHEMA,
                "LAUNCH_OBSERVATION_SCHEMA_INVALID")
        expected = build_launch_observation(contract=contract,
            sequence=item.get("sequence"), state=item.get("state"),
            previous_observation_root=item.get("previous_observation_root"),
            executor_receipt_root=item.get("executor_receipt_root"),
            g1_root=item.get("g1_root"), g2_root=item.get("g2_root"),
            g3_root=item.get("g3_root"),
            readiness_evidence_root=item.get("readiness_evidence_root"),
            reason_codes=item.get("reason_codes"))
        require(item == expected and item["sequence"] == index
                and item["previous_observation_root"] ==
                    (previous["observation_root"] if previous else None),
                "LAUNCH_OBSERVATION_CHAIN_INVALID")
        require(item["state"] in transitions.get(previous["state"] if previous else None, set()),
                "LAUNCH_TRANSITION_INVALID")
        normalized.append(deepcopy(item)); previous = item
    body = {"schema": STATE_SCHEMA,
            "launch_contract_root": contract["launch_contract_root"],
            "last_observation_root": previous["observation_root"],
            "sequence": len(normalized), "state": previous["state"],
            "terminal": previous["state"] in TERMINAL,
            "ready": previous["state"] == "READY",
            "requires_reconciliation": previous["state"] == "UNCERTAIN",
            "relaunch_allowed": False, **BOUNDARY}
    return {**body, "launch_state_root": root(body)}

"""Receipt-consuming durable operation state for Stage I4 c4."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY


SCHEMA = "mosaic.ucm.stage-i4-operation-state.v0.2"
TERMINAL = {"REFUSED", "COMPLETED", "DIVERGED", "CANCELLED", "UNCERTAIN"}


def _receipt(raw: Any, *, run_contract_root: str, transition: str,
             prior_receipt_root: str | None) -> dict[str, Any]:
    if transition in {"G1_ALLOWED", "G1_REFUSED"}:
        keys = {"schema", "gate", "run_contract_root", "context_root",
                "trust_anchors_root", "preflight_root", "decision", "reason_codes"}
    elif transition == "NATIVE_DISPATCHED":
        keys = {"schema", "run_contract_root", "g1_root", "native_owner",
                "lease_ref", "status"}
    elif transition == "G2_RECORDED":
        keys = {"schema", "gate", "run_contract_root", "g1_root",
                "dispatch_root", "native_receipt_root", "completion_status",
                "recovery_status", "case_results", "observed_effect_classes"}
    elif transition in {"G3_PASS", "G3_DIVERGED"}:
        keys = {"schema", "gate", "run_contract_root", "g2_root",
                "classification", "finding_codes", "next_action"}
    else:
        keys = {"schema", "run_contract_root", "prior_receipt_root",
                "terminal_state", "reason_codes"}
    item = exact_keys(raw, keys | set(BOUNDARY) | {"receipt_root"})
    require(item["receipt_root"] == root({
        key: deepcopy(value) for key, value in item.items()
        if key != "receipt_root"
    }), "STAGE_I4_OPERATION_RECEIPT_ROOT_INVALID")
    require(item["run_contract_root"] == run_contract_root,
            "STAGE_I4_OPERATION_RECEIPT_BINDING_INVALID")
    schema = item["schema"]
    if transition in {"G1_ALLOWED", "G1_REFUSED"}:
        require(schema == "mosaic.ucm.integration-g1-receipt.v0.1"
                and item["gate"] == "G1_SENTINEL"
                and item["decision"] == ("ALLOW" if transition == "G1_ALLOWED" else "REFUSE"),
                "STAGE_I4_OPERATION_G1_RECEIPT_INVALID")
    elif transition == "NATIVE_DISPATCHED":
        require(schema == "mosaic.ucm.native-dispatch-receipt.v0.1"
                and item["status"] == "DISPATCHED"
                and item["g1_root"] == prior_receipt_root,
                "STAGE_I4_OPERATION_DISPATCH_RECEIPT_INVALID")
    elif transition == "G2_RECORDED":
        require(schema == "mosaic.ucm.integration-g2-receipt.v0.1"
                and item["gate"] == "G2_WITNESS"
                and item["dispatch_root"] == prior_receipt_root,
                "STAGE_I4_OPERATION_G2_RECEIPT_INVALID")
    elif transition in {"G3_PASS", "G3_DIVERGED"}:
        require(schema == "mosaic.ucm.integration-g3-receipt.v0.1"
                and item["gate"] == "G3_DIAGNOSTIC"
                and item["g2_root"] == prior_receipt_root
                and item["classification"] == ("PASS" if transition == "G3_PASS" else "DIVERGED"),
                "STAGE_I4_OPERATION_G3_RECEIPT_INVALID")
    else:
        require(schema == "mosaic.ucm.stage-i4-terminal-state-receipt.v0.1"
                and item["prior_receipt_root"] == prior_receipt_root
                and item["terminal_state"] == ("CANCELLED" if transition == "CANCELLED" else "UNCERTAIN"),
                "STAGE_I4_OPERATION_TERMINAL_RECEIPT_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "STAGE_I4_AUTHORITY_CEILING_INVALID")
    return deepcopy(item)


def derive_operation_state(*, operation_id: str, run_contract_root: str,
                           events: Any) -> dict[str, Any]:
    require(type(operation_id) is str and bool(operation_id.strip()),
            "STAGE_I4_OPERATION_ID_INVALID")
    require_root(run_contract_root)
    require(type(events) is list, "STAGE_I4_OPERATION_EVENTS_INVALID")
    state = "PLANNED"
    roots: dict[str, str | None] = {"g1_root": None, "dispatch_root": None,
                                    "g2_root": None, "g3_root": None,
                                    "terminal_root": None}
    seen: set[str] = set()
    ordered = []
    transitions = {
        "G1_ALLOWED": ("PLANNED", "SENTINEL_ALLOWED", "g1_root"),
        "G1_REFUSED": ("PLANNED", "REFUSED", "g1_root"),
        "NATIVE_DISPATCHED": ("SENTINEL_ALLOWED", "DISPATCHED", "dispatch_root"),
        "G2_RECORDED": ("DISPATCHED", "WITNESSED", "g2_root"),
        "G3_PASS": ("WITNESSED", "COMPLETED", "g3_root"),
        "G3_DIVERGED": ("WITNESSED", "DIVERGED", "g3_root"),
        "CANCELLED": (None, "CANCELLED", "terminal_root"),
        "OUTCOME_UNCERTAIN": ("DISPATCHED", "UNCERTAIN", "terminal_root"),
    }
    prior: str | None = None
    for raw in events:
        row = exact_keys(raw, {"event_id", "transition", "run_contract_root", "receipt"})
        require(type(row["event_id"]) is str and bool(row["event_id"])
                and row["event_id"] not in seen,
                "STAGE_I4_OPERATION_EVENT_DUPLICATE")
        seen.add(row["event_id"])
        require(row["run_contract_root"] == run_contract_root
                and row["transition"] in transitions,
                "STAGE_I4_OPERATION_EVENT_BINDING_INVALID")
        required, following, field = transitions[row["transition"]]
        if row["transition"] == "CANCELLED":
            require(state in {"PLANNED", "SENTINEL_ALLOWED"},
                    "STAGE_I4_OPERATION_CANCEL_TOO_LATE")
        else:
            require(state == required, "STAGE_I4_OPERATION_ORDER_INVALID")
        receipt = _receipt(row["receipt"], run_contract_root=run_contract_root,
                           transition=row["transition"],
                           prior_receipt_root=prior)
        prior = receipt["receipt_root"]
        roots[field] = prior
        state = following
        if state in TERMINAL:
            roots["terminal_root"] = prior
        ordered.append({**deepcopy(row), "receipt": receipt})
    body = {
        "schema": SCHEMA, "operation_id": operation_id,
        "run_contract_root": run_contract_root, "state": state,
        "events": ordered, **roots,
        "resume_allowed": state in {"PLANNED", "SENTINEL_ALLOWED"},
        "native_redispatch_allowed": False,
        "requires_operator_resolution": state == "UNCERTAIN", **BOUNDARY,
    }
    return {**body, "state_root": root(body)}


def validate_operation_state(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "operation_id", "run_contract_root", "state", "events",
        "g1_root", "dispatch_root", "g2_root", "g3_root", "terminal_root",
        "resume_allowed", "native_redispatch_allowed",
        "requires_operator_resolution", "standing", "authority_effect",
        "real_a5", "g0", "state_root",
    })
    expected = derive_operation_state(
        operation_id=item["operation_id"],
        run_contract_root=item["run_contract_root"], events=item["events"])
    require(item == expected, "STAGE_I4_OPERATION_STATE_INVALID")
    return deepcopy(item)


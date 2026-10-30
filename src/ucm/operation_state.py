"""Durable operation-state projection for mediated Stage I4 work.

The journal remains the source of truth.  This module derives a compact state
machine from journaled gate and terminal events, so retries and interruption do
not invent a second operation or silently repeat a native effect.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root
from .amcas import BOUNDARY


SCHEMA = "mosaic.ucm.stage-i4-operation-state.v0.1"
TERMINAL = {"REFUSED", "COMPLETED", "DIVERGED", "CANCELLED", "UNCERTAIN"}


def derive_operation_state(*, operation_id: str, run_contract_root: str,
                           events: Any) -> dict[str, Any]:
    require(type(operation_id) is str and bool(operation_id.strip()),
            "STAGE_I4_OPERATION_ID_INVALID")
    require_root(run_contract_root)
    require(type(events) is list, "STAGE_I4_OPERATION_EVENTS_INVALID")
    state = "PLANNED"
    roots: dict[str, str | None] = {"g1_root": None, "g2_root": None,
                                    "g3_root": None, "terminal_root": None}
    seen: set[str] = set()
    ordered = []
    transitions = {
        "G1_ALLOWED": ("PLANNED", "SENTINEL_ALLOWED", "g1_root"),
        "G1_REFUSED": ("PLANNED", "REFUSED", "g1_root"),
        "NATIVE_DISPATCHED": ("SENTINEL_ALLOWED", "DISPATCHED", None),
        "G2_RECORDED": ("DISPATCHED", "WITNESSED", "g2_root"),
        "G3_PASS": ("WITNESSED", "COMPLETED", "g3_root"),
        "G3_DIVERGED": ("WITNESSED", "DIVERGED", "g3_root"),
        "CANCELLED": (None, "CANCELLED", None),
        "OUTCOME_UNCERTAIN": ("DISPATCHED", "UNCERTAIN", None),
    }
    for raw in events:
        row = exact_keys(raw, {"event_id", "transition", "run_contract_root",
                               "receipt_root"})
        require(type(row["event_id"]) is str and row["event_id"] not in seen,
                "STAGE_I4_OPERATION_EVENT_DUPLICATE")
        seen.add(row["event_id"])
        require(row["run_contract_root"] == run_contract_root,
                "STAGE_I4_OPERATION_EVENT_BINDING_INVALID")
        require_root(row["receipt_root"])
        require(row["transition"] in transitions,
                "STAGE_I4_OPERATION_TRANSITION_INVALID")
        required, following, receipt_field = transitions[row["transition"]]
        if row["transition"] == "CANCELLED":
            require(state in {"PLANNED", "SENTINEL_ALLOWED"},
                    "STAGE_I4_OPERATION_CANCEL_TOO_LATE")
        else:
            require(state == required, "STAGE_I4_OPERATION_ORDER_INVALID")
        state = following
        if receipt_field is not None:
            roots[receipt_field] = row["receipt_root"]
        if state in TERMINAL:
            roots["terminal_root"] = row["receipt_root"]
        ordered.append(deepcopy(row))
    body = {"schema": SCHEMA, "operation_id": operation_id,
            "run_contract_root": run_contract_root, "state": state,
            "events": ordered, **roots,
            "resume_allowed": state in {"PLANNED", "SENTINEL_ALLOWED"},
            "native_redispatch_allowed": False,
            "requires_operator_resolution": state == "UNCERTAIN", **BOUNDARY}
    return {**body, "state_root": root(body)}


def validate_operation_state(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "operation_id", "run_contract_root",
        "state", "events", "g1_root", "g2_root", "g3_root", "terminal_root",
        "resume_allowed", "native_redispatch_allowed", "requires_operator_resolution",
        "standing", "authority_effect", "real_a5", "g0", "state_root"})
    expected = derive_operation_state(operation_id=item["operation_id"],
        run_contract_root=item["run_contract_root"], events=item["events"])
    require(item == expected, "STAGE_I4_OPERATION_STATE_INVALID")
    return deepcopy(item)

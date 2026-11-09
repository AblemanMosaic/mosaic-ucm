"""Read-only ecosystem integration observatory."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY
from .application_capsule import validate_application_capsule
from .operation_gateway import STATE_SCHEMA, TERMINAL_STATES


SCHEMA = "mosaic.ucm.integration-observatory.v0.1"


def _validate_state(value: Any) -> dict[str, Any]:
    require(type(value) is dict and value.get("schema") == STATE_SCHEMA,
            "OBSERVATORY_OPERATION_STATE_SCHEMA_INVALID")
    body = {key: deepcopy(item) for key, item in value.items() if key != "state_root"}
    require(value.get("state_root") == root(body), "OBSERVATORY_OPERATION_STATE_ROOT_INVALID")
    require(type(body.get("operation_id")) is str and body["operation_id"],
            "OBSERVATORY_OPERATION_ID_INVALID")
    require({key: body.get(key) for key in BOUNDARY} == BOUNDARY,
            "OBSERVATORY_OPERATION_AUTHORITY_INVALID")
    require(body.get("redispatch_allowed") is False,
            "OBSERVATORY_REDISPATCH_POLICY_INVALID")
    require(body.get("requires_reconciliation") is (body.get("state") == "UNCERTAIN")
            and body.get("terminal") is (body.get("state") in TERMINAL_STATES),
            "OBSERVATORY_OPERATION_FLAGS_INVALID")
    return deepcopy(value)


def build_observatory(*, capsules: list[dict[str, Any]],
                      operation_states: list[dict[str, Any]],
                      journal_heads: list[dict[str, Any]]) -> dict[str, Any]:
    require(type(capsules) is list, "OBSERVATORY_CAPSULES_INVALID")
    normalized = sorted((validate_application_capsule(row) for row in capsules),
                        key=lambda row: row["application_id"])
    require(len(normalized) == len({row["application_id"] for row in normalized}),
            "OBSERVATORY_APPLICATION_DUPLICATE")
    require(type(operation_states) is list and type(journal_heads) is list,
            "OBSERVATORY_INPUT_INVALID")
    states = sorted((_validate_state(row) for row in operation_states),
                    key=lambda row: row["operation_id"])
    require(len(states) == len({row["operation_id"] for row in states}),
            "OBSERVATORY_OPERATION_DUPLICATE")
    uncertain = sorted(row["operation_id"] for row in states
                       if row["requires_reconciliation"] is True)
    terminal = sum(row["terminal"] is True for row in states)
    heads = []
    for row in journal_heads:
        item = exact_keys(row, {"schema", "sequence", "head", "events_sha256",
            "standing", "authority_effect", "real_a5", "g0", "root"})
        require(item["schema"] == "mosaic.ucm.integration-journal-head.v0.1"
                and type(item["sequence"]) is int and item["sequence"] >= 0
                and {key: item[key] for key in BOUNDARY} == BOUNDARY,
                "OBSERVATORY_JOURNAL_HEAD_INVALID")
        require_root(item["head"])
        require_root(item["events_sha256"])
        body = {key: deepcopy(value) for key, value in item.items() if key != "root"}
        require(item["root"] == root(body), "OBSERVATORY_JOURNAL_HEAD_ROOT_INVALID")
        heads.append(item["root"])
    body = {"schema": SCHEMA,
            "application_count": len(normalized),
            "application_roots": [{"application_id": row["application_id"],
                                    "capsule_root": row["capsule_root"]}
                                   for row in normalized],
            "active_surface_count": len({surface for row in normalized
                                         for surface in row["active_surfaces"]}),
            "operation_count": len(states),
            "terminal_operation_count": terminal,
            "uncertain_operation_ids": uncertain,
            "journal_head_roots": sorted(set(heads)),
            "policy_drift_status": "NOT_EVALUATED_NO_EXPECTED_ROOTS",
            "read_only": True, "status": "PASS", **BOUNDARY}
    return {**body, "observatory_root": root(body)}

"""Read-only projections over Pippi and development-control records."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY
from .constitutional_launcher import STATE_SCHEMA as LAUNCH_STATE_SCHEMA
from .development_standards import EVALUATION_SCHEMA
from .pippi import DECISION_SCHEMA, EXCEPTION_SCHEMA


STATE_SCHEMA = "mosaic.ucm.development-observatory-state.v0.1"
PROJECTION_SCHEMA = "mosaic.ucm.development-observatory-projection.v0.1"


def _rooted(value: Any, *, schema: str, root_field: str, code: str) -> dict[str, Any]:
    require(type(value) is dict and value.get("schema") == schema, code)
    body = {key: deepcopy(item) for key, item in value.items() if key != root_field}
    require(value.get(root_field) == root(body), code)
    return deepcopy(value)


def build_development_observatory(*, subject_root: str,
                                  standards_evaluations: list[dict[str, Any]],
                                  pippi_decisions: list[dict[str, Any]],
                                  launch_states: list[dict[str, Any]],
                                  constitutional_exceptions: list[dict[str, Any]],
                                  journal_head_roots: list[str]) -> dict[str, Any]:
    require_root(subject_root)
    require(type(standards_evaluations) is list and type(pippi_decisions) is list
            and type(launch_states) is list and type(constitutional_exceptions) is list,
            "DEVELOPMENT_OBSERVATORY_INPUT_INVALID")
    standards = [_rooted(row, schema=EVALUATION_SCHEMA, root_field="evaluation_root",
                         code="DEVELOPMENT_OBSERVATORY_STANDARDS_INVALID")
                 for row in standards_evaluations]
    decisions = [_rooted(row, schema=DECISION_SCHEMA, root_field="decision_root",
                         code="DEVELOPMENT_OBSERVATORY_DECISION_INVALID")
                 for row in pippi_decisions]
    launches = [_rooted(row, schema=LAUNCH_STATE_SCHEMA, root_field="launch_state_root",
                        code="DEVELOPMENT_OBSERVATORY_LAUNCH_INVALID")
                for row in launch_states]
    exceptions = [_rooted(row, schema=EXCEPTION_SCHEMA, root_field="exception_root",
                          code="DEVELOPMENT_OBSERVATORY_EXCEPTION_INVALID")
                  for row in constitutional_exceptions]
    require(type(journal_head_roots) is list
            and journal_head_roots == sorted(set(journal_head_roots)),
            "DEVELOPMENT_OBSERVATORY_JOURNAL_HEADS_INVALID")
    for value in journal_head_roots:
        require_root(value)
    attention = []
    for row in standards:
        if row["decision"] != "PASS":
            attention.append({"kind": "STANDARDS", "record_root": row["evaluation_root"],
                              "status": row["decision"]})
    for row in decisions:
        if row["status"] != "VALIDATED":
            attention.append({"kind": "PIPPI_DECISION", "record_root": row["decision_root"],
                              "status": row["status"]})
    for row in launches:
        if row["requires_reconciliation"]:
            attention.append({"kind": "LAUNCH_RECONCILIATION",
                              "record_root": row["launch_state_root"], "status": "UNCERTAIN"})
    for row in exceptions:
        if row["status"] == "OPEN":
            attention.append({"kind": "CONSTITUTIONAL_EXCEPTION",
                              "record_root": row["exception_root"], "status": "OPEN"})
    attention.sort(key=lambda row: (row["kind"], row["record_root"]))
    available = sorted({
        "RESOLVE_STANDARDS" if row["kind"] == "STANDARDS" else
        "RESOLVE_CONSTITUTIONAL_EXCEPTION" if row["kind"] == "CONSTITUTIONAL_EXCEPTION" else
        "RECONCILE_LAUNCH" if row["kind"] == "LAUNCH_RECONCILIATION" else
        "RESOLVE_PIPPI_DECISION"
        for row in attention
    })
    body = {"schema": STATE_SCHEMA, "subject_root": subject_root,
            "standards_evaluation_roots": sorted(row["evaluation_root"] for row in standards),
            "pippi_decision_roots": sorted(row["decision_root"] for row in decisions),
            "launch_state_roots": sorted(row["launch_state_root"] for row in launches),
            "constitutional_exception_roots": sorted(row["exception_root"] for row in exceptions),
            "journal_head_roots": journal_head_roots,
            "attention": attention,
            "available_actions": [{"action": action, "authorized": False}
                                  for action in available],
            "status": "ATTENTION_REQUIRED" if attention else "CURRENT",
            "read_only": True, **BOUNDARY}
    return {**body, "observatory_state_root": root(body)}


def project_development_observatory(*, state: dict[str, Any], view: str) -> dict[str, Any]:
    item = exact_keys(state, {"schema", "subject_root", "standards_evaluation_roots",
                              "pippi_decision_roots", "launch_state_roots",
                              "constitutional_exception_roots", "journal_head_roots",
                              "attention", "available_actions", "status", "read_only",
                              "standing", "authority_effect", "real_a5", "g0",
                              "observatory_state_root"})
    body = {key: deepcopy(value) for key, value in item.items()
            if key != "observatory_state_root"}
    require(item["schema"] == STATE_SCHEMA
            and item["observatory_state_root"] == root(body)
            and item["read_only"] is True, "DEVELOPMENT_OBSERVATORY_STATE_INVALID")
    require(view in {"HUMAN", "AGENT", "FORENSIC"}, "DEVELOPMENT_OBSERVATORY_VIEW_INVALID")
    if view == "HUMAN":
        content = {"status": item["status"], "attention": item["attention"],
                   "next": item["available_actions"]}
    elif view == "AGENT":
        content = {"status": item["status"], "subject_root": item["subject_root"],
                   "attention": item["attention"], "available_actions": item["available_actions"],
                   "journal_head_roots": item["journal_head_roots"]}
    else:
        content = {key: deepcopy(value) for key, value in item.items()
                   if key != "observatory_state_root"}
    projection = {"schema": PROJECTION_SCHEMA,
                  "observatory_state_root": item["observatory_state_root"],
                  "view": view, "content": content,
                  "projection_is_authority": False, **BOUNDARY}
    return {**projection, "projection_root": root(projection)}

"""Pure query, comparison, and inclusion tools for integration journals."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .journal import BOUNDARY, GENESIS, verify_event


def verify_event_chain(events: Any, *, predecessor: str = GENESIS,
                       start_sequence: int = 1) -> list[dict[str, Any]]:
    require(type(events) is list and type(start_sequence) is int and start_sequence >= 1,
            "JOURNAL_CHAIN_INPUT_INVALID")
    require_root(predecessor)
    verified = []
    current = predecessor
    for sequence, raw in enumerate(events, start_sequence):
        event = verify_event(raw, sequence=sequence, predecessor=current)
        verified.append(event); current = event["event_root"]
    return verified


def summarize_events(events: Any) -> dict[str, Any]:
    verified = verify_event_chain(events)
    counts = Counter(event["event_type"] for event in verified)
    operations: dict[str, str] = {}
    for event in verified:
        operation_id = event["payload"].get("operation_id")
        if type(operation_id) is str:
            operations[operation_id] = event["event_type"]
    body = {"schema": "mosaic.ucm.journal-summary.v0.1",
            "sequence": len(verified),
            "head": verified[-1]["event_root"] if verified else GENESIS,
            "event_type_counts": dict(sorted(counts.items())),
            "operation_states": [{"operation_id": key, "last_event_type": operations[key]}
                                 for key in sorted(operations)],
            **BOUNDARY}
    return {**body, "summary_root": root(body)}


def query_events(events: Any, *, event_type: str | None = None,
                 operation_id: str | None = None, limit: int | None = None) -> dict[str, Any]:
    verified = verify_event_chain(events)
    require(event_type is None or type(event_type) is str, "JOURNAL_QUERY_INVALID")
    require(operation_id is None or type(operation_id) is str, "JOURNAL_QUERY_INVALID")
    require(limit is None or (type(limit) is int and limit > 0), "JOURNAL_QUERY_INVALID")
    selected = [event for event in verified
                if (event_type is None or event["event_type"] == event_type)
                and (operation_id is None or event["payload"].get("operation_id") == operation_id)]
    if limit is not None:
        selected = selected[-limit:]
    body = {"schema": "mosaic.ucm.journal-query.v0.1",
            "journal_head": verified[-1]["event_root"] if verified else GENESIS,
            "criteria": {"event_type": event_type, "operation_id": operation_id,
                         "limit": limit},
            "events": deepcopy(selected), "match_count": len(selected), **BOUNDARY}
    return {**body, "query_root": root(body)}


def diff_event_chains(before: Any, after: Any) -> dict[str, Any]:
    left, right = verify_event_chain(before), verify_event_chain(after)
    shared = 0
    for first, second in zip(left, right):
        if first["event_root"] != second["event_root"]:
            break
        shared += 1
    relation = "IDENTICAL" if len(left) == len(right) == shared else (
        "FAST_FORWARD" if shared == len(left) else "DIVERGED")
    body = {"schema": "mosaic.ucm.journal-diff.v0.1",
            "before_head": left[-1]["event_root"] if left else GENESIS,
            "after_head": right[-1]["event_root"] if right else GENESIS,
            "shared_prefix_events": shared, "relation": relation,
            "added_events": deepcopy(right[shared:]) if relation == "FAST_FORWARD" else [],
            "before_only_roots": [row["event_root"] for row in left[shared:]],
            "after_only_roots": [row["event_root"] for row in right[shared:]], **BOUNDARY}
    return {**body, "diff_root": root(body)}


def build_inclusion_proof(events: Any, *, event_root: str) -> dict[str, Any]:
    verified = verify_event_chain(events); require_root(event_root)
    matches = [index for index, event in enumerate(verified) if event["event_root"] == event_root]
    require(len(matches) == 1, "JOURNAL_EVENT_NOT_FOUND")
    index = matches[0]
    body = {"schema": "mosaic.ucm.journal-inclusion-proof.v0.1",
            "start_sequence": index + 1,
            "predecessor": verified[index]["predecessor"],
            "included_event_root": event_root,
            "events_to_head": deepcopy(verified[index:]),
            "journal_head": verified[-1]["event_root"], **BOUNDARY}
    return {**body, "proof_root": root(body)}


def verify_inclusion_proof(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "start_sequence", "predecessor",
        "included_event_root", "events_to_head", "journal_head", "standing",
        "authority_effect", "real_a5", "g0", "proof_root"})
    require(item["schema"] == "mosaic.ucm.journal-inclusion-proof.v0.1",
            "JOURNAL_PROOF_SCHEMA_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "proof_root"}
    require(item["proof_root"] == root(body), "JOURNAL_PROOF_ROOT_INVALID")
    verified = verify_event_chain(item["events_to_head"], predecessor=item["predecessor"],
                                  start_sequence=item["start_sequence"])
    require(bool(verified) and verified[0]["event_root"] == item["included_event_root"]
            and verified[-1]["event_root"] == item["journal_head"],
            "JOURNAL_PROOF_INVALID")
    return deepcopy(item)

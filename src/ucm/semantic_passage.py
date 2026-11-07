"""Immutable prose with separately rooted, provider-qualified sense bindings."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY


PASSAGE_SCHEMA = "mosaic.ucm.semantic-passage.v0.1"
CLARIFICATION_SCHEMA = "mosaic.ucm.semantic-clarification-request.v0.1"
RESOLUTION_SCHEMA = "mosaic.ucm.semantic-passage-resolution.v0.1"
PROVIDER_MODES = {"REFERENCE_UNBOUND", "PINNED_EXTERNAL_PROVIDER"}
SPAN_REQUIREMENTS = {"REQUIRED", "OPTIONAL"}


def _identifier(value: Any, code: str) -> str:
    require(type(value) is str and value == value.strip() and 0 < len(value) <= 192
            and all(ch.isalnum() or ch in "._:-" for ch in value), code)
    return value


def _candidate(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"vocabulary_root", "term_id", "sense_id", "bound_term"})
    require_root(item["vocabulary_root"])
    require(type(item["term_id"]) is int and item["term_id"] >= 0
            and type(item["sense_id"]) is int and item["sense_id"] >= 0,
            "SEMANTIC_INTEGER_ID_INVALID")
    require(type(item["bound_term"]) is str and item["bound_term"] == item["bound_term"].strip()
            and bool(item["bound_term"]), "SEMANTIC_BOUND_TERM_INVALID")
    return deepcopy(item)


def build_semantic_passage(*, passage_id: str, text: str, context_root: str,
                           provider_mode: str, provider_root: str | None,
                           spans: list[dict[str, Any]]) -> dict[str, Any]:
    _identifier(passage_id, "SEMANTIC_PASSAGE_ID_INVALID")
    require(type(text) is str and bool(text), "SEMANTIC_TEXT_INVALID")
    require_root(context_root)
    require(provider_mode in PROVIDER_MODES, "SEMANTIC_PROVIDER_MODE_INVALID")
    require((provider_mode == "REFERENCE_UNBOUND" and provider_root is None) or
            (provider_mode == "PINNED_EXTERNAL_PROVIDER" and provider_root is not None
             and require_root(provider_root)), "SEMANTIC_PROVIDER_ROOT_INVALID")
    raw = text.encode("utf-8")
    normalized = []
    seen: set[str] = set()
    require(type(spans) is list, "SEMANTIC_SPANS_INVALID")
    for span in spans:
        item = exact_keys(span, {"span_id", "byte_start", "byte_end", "exact_text",
                                 "requirement", "candidates", "citation_roots"})
        span_id = _identifier(item["span_id"], "SEMANTIC_SPAN_ID_INVALID")
        require(span_id not in seen, "SEMANTIC_SPAN_DUPLICATE")
        seen.add(span_id)
        require(type(item["byte_start"]) is int and type(item["byte_end"]) is int
                and 0 <= item["byte_start"] < item["byte_end"] <= len(raw),
                "SEMANTIC_SPAN_RANGE_INVALID")
        try:
            exact = raw[item["byte_start"]:item["byte_end"]].decode("utf-8", errors="strict")
        except UnicodeError as error:
            require(False, "SEMANTIC_SPAN_UTF8_BOUNDARY_INVALID", detail=type(error).__name__)
        require(item["exact_text"] == exact, "SEMANTIC_SPAN_TEXT_MISMATCH")
        require(item["requirement"] in SPAN_REQUIREMENTS, "SEMANTIC_SPAN_REQUIREMENT_INVALID")
        require(type(item["candidates"]) is list and bool(item["candidates"]),
                "SEMANTIC_CANDIDATES_INVALID")
        candidates = [_candidate(row) for row in item["candidates"]]
        keys = [(row["vocabulary_root"], row["term_id"], row["sense_id"]) for row in candidates]
        require(keys == sorted(set(keys)), "SEMANTIC_CANDIDATES_ORDER_INVALID")
        require(type(item["citation_roots"]) is list
                and item["citation_roots"] == sorted(set(item["citation_roots"])),
                "SEMANTIC_CITATIONS_INVALID")
        for citation_root in item["citation_roots"]:
            require_root(citation_root)
        normalized.append({**{key: deepcopy(value) for key, value in item.items()
                              if key not in {"candidates"}}, "candidates": candidates})
    normalized.sort(key=lambda row: (row["byte_start"], row["byte_end"], row["span_id"]))
    body = {"schema": PASSAGE_SCHEMA, "passage_id": passage_id, "text": text,
            "text_sha256": hashlib.sha256(raw).hexdigest(), "context_root": context_root,
            "provider_mode": provider_mode, "provider_root": provider_root,
            "spans": normalized, **BOUNDARY}
    return {**body, "passage_root": root(body)}


def validate_semantic_passage(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "passage_id", "text", "text_sha256",
                              "context_root", "provider_mode", "provider_root", "spans",
                              "standing", "authority_effect", "real_a5", "g0", "passage_root"})
    expected = build_semantic_passage(passage_id=item["passage_id"], text=item["text"],
        context_root=item["context_root"], provider_mode=item["provider_mode"],
        provider_root=item["provider_root"], spans=item["spans"])
    require(item == expected, "SEMANTIC_PASSAGE_INVALID")
    return deepcopy(item)


def build_clarification_request(*, passage: dict[str, Any], turn: int,
                                unresolved_span_ids: list[str],
                                remaining_turns: int) -> dict[str, Any]:
    passage = validate_semantic_passage(passage)
    require(type(turn) is int and turn >= 1 and type(remaining_turns) is int
            and remaining_turns >= 0, "SEMANTIC_CLARIFICATION_BUDGET_INVALID")
    known = {row["span_id"] for row in passage["spans"]}
    require(type(unresolved_span_ids) is list and unresolved_span_ids == sorted(set(unresolved_span_ids))
            and bool(unresolved_span_ids) and set(unresolved_span_ids) <= known,
            "SEMANTIC_UNRESOLVED_SPANS_INVALID")
    body = {"schema": CLARIFICATION_SCHEMA, "passage_root": passage["passage_root"],
            "turn": turn, "remaining_turns": remaining_turns,
            "unresolved_spans": [deepcopy(next(row for row in passage["spans"]
                                                if row["span_id"] == span_id))
                                 for span_id in unresolved_span_ids], **BOUNDARY}
    return {**body, "clarification_root": root(body)}


def resolve_semantic_passage(*, passage: dict[str, Any], selections: list[dict[str, Any]],
                             clarification_roots: list[str],
                             budget_exhausted: bool = False) -> dict[str, Any]:
    passage = validate_semantic_passage(passage)
    require(type(selections) is list and type(budget_exhausted) is bool,
            "SEMANTIC_SELECTIONS_INVALID")
    by_span = {row["span_id"]: row for row in passage["spans"]}
    chosen: dict[str, dict[str, Any]] = {}
    for raw in selections:
        item = exact_keys(raw, {"span_id", "vocabulary_root", "term_id", "sense_id"})
        span_id = _identifier(item["span_id"], "SEMANTIC_SELECTION_SPAN_INVALID")
        require(span_id in by_span and span_id not in chosen,
                "SEMANTIC_SELECTION_UNKNOWN_OR_DUPLICATE")
        key = (item["vocabulary_root"], item["term_id"], item["sense_id"])
        require(key in {(candidate["vocabulary_root"], candidate["term_id"], candidate["sense_id"])
                        for candidate in by_span[span_id]["candidates"]},
                "SEMANTIC_SELECTION_NOT_CANDIDATE")
        chosen[span_id] = deepcopy(item)
    require(type(clarification_roots) is list
            and clarification_roots == sorted(set(clarification_roots)),
            "SEMANTIC_CLARIFICATION_ROOTS_INVALID")
    for clarification_root in clarification_roots:
        require_root(clarification_root)
    required = {row["span_id"] for row in passage["spans"] if row["requirement"] == "REQUIRED"}
    unresolved = sorted(required - set(chosen))
    status = "PASS_RESOLVED" if not unresolved else (
        "REFUSED_BUDGET_EXHAUSTED" if budget_exhausted else "HELD_CLARIFICATION_REQUIRED")
    body = {"schema": RESOLUTION_SCHEMA, "passage_root": passage["passage_root"],
            "text_sha256": passage["text_sha256"],
            "selections": [chosen[key] for key in sorted(chosen)],
            "unresolved_required_span_ids": unresolved,
            "clarification_roots": clarification_roots,
            "budget_exhausted": budget_exhausted, "status": status,
            "original_text_preserved": True, **BOUNDARY}
    return {**body, "resolution_root": root(body)}

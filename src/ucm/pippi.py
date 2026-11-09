"""Pippi: a rooted proposal, evaluation, and human-projection protocol.

This module models a mediation boundary.  It does not claim that a host has
enforced that boundary; each context capsule declares its actually mediated
channels.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY


CONTEXT_SCHEMA = "mosaic.ucm.pippi-context.v0.1"
ATTESTED_CONTEXT_SCHEMA = "mosaic.ucm.pippi-context.v0.2"
DRAFT_SCHEMA = "mosaic.ucm.pippi-model-draft.v0.1"
DECISION_SCHEMA = "mosaic.ucm.pippi-decision.v0.1"
PROJECTION_SCHEMA = "mosaic.ucm.pippi-human-projection.v0.1"
EXCEPTION_SCHEMA = "mosaic.ucm.pippi-constitutional-exception.v0.1"
TURN_SCHEMA = "mosaic.ucm.pippi-turn-envelope.v0.1"
CHANNELS = {"MODEL_INPUT", "MODEL_DRAFT", "VISIBLE_OUTPUT", "TOOL_PROPOSAL",
            "TOOL_DISPATCH", "TOOL_RESULT", "JOURNAL_WRITE"}
PROPOSAL_DECISIONS = {"PASS", "ADVISORY", "HELD", "REFUSED"}


def _identifier(value: Any, code: str) -> str:
    require(type(value) is str and value == value.strip() and 0 < len(value) <= 192
            and all(ch.isalnum() or ch in "._:-" for ch in value), code)
    return value


def build_pippi_context(*, session_root: str, subject_root: str,
                        policy_roots: list[str], capability_registry_root: str,
                        profile_root: str, jurisdiction_root: str,
                        retained_context_roots: list[str],
                        mediated_channels: list[str]) -> dict[str, Any]:
    for value in (session_root, subject_root, capability_registry_root, profile_root,
                  jurisdiction_root):
        require_root(value)
    for values, code in ((policy_roots, "PIPPI_POLICY_ROOTS_INVALID"),
                         (retained_context_roots, "PIPPI_CONTEXT_ROOTS_INVALID")):
        require(type(values) is list and values == sorted(set(values)), code)
        for value in values:
            require_root(value)
    require(type(mediated_channels) is list
            and mediated_channels == sorted(set(mediated_channels))
            and set(mediated_channels) <= CHANNELS,
            "PIPPI_MEDIATED_CHANNELS_INVALID")
    # Channel enumeration is a declaration, not proof that the host actually
    # mediated those channels.  Only the v0.2 attested builder may emit an
    # ENFORCED_HOST context.
    enforcement = "SIDECAR_PARTIAL"
    body = {"schema": CONTEXT_SCHEMA, "session_root": session_root,
            "subject_root": subject_root, "policy_roots": policy_roots,
            "capability_registry_root": capability_registry_root,
            "profile_root": profile_root, "jurisdiction_root": jurisdiction_root,
            "retained_context_roots": retained_context_roots,
            "mediated_channels": mediated_channels, "integration_mode": enforcement,
            **BOUNDARY}
    return {**body, "context_root": root(body)}


def build_attested_pippi_context(*, session_root: str, subject_root: str,
                                 policy_roots: list[str],
                                 capability_registry_root: str, profile_root: str,
                                 jurisdiction_root: str,
                                 retained_context_roots: list[str],
                                 expected_host_policy_root: str,
                                 host_policy: dict[str, Any],
                                 host_attestation: dict[str, Any],
                                 now_ns: int) -> dict[str, Any]:
    from .pippi_host import (validate_host_adapter_policy,
                             validate_host_mediation_attestation)
    for value in (session_root, subject_root, capability_registry_root, profile_root,
                  jurisdiction_root):
        require_root(value)
    for values, code in ((policy_roots, "PIPPI_POLICY_ROOTS_INVALID"),
                         (retained_context_roots, "PIPPI_CONTEXT_ROOTS_INVALID")):
        require(type(values) is list and values == sorted(set(values)), code)
        for value in values: require_root(value)
    require_root(expected_host_policy_root)
    policy = validate_host_adapter_policy(host_policy)
    require(policy["host_policy_root"] == expected_host_policy_root,
            "PIPPI_HOST_POLICY_ANCHOR_MISMATCH")
    require(policy["host_policy_root"] in policy_roots,
            "PIPPI_HOST_POLICY_NOT_PINNED")
    attestation = validate_host_mediation_attestation(host_attestation,
        policy=policy, expected_session_root=session_root,
        expected_subject_root=subject_root, now_ns=now_ns)
    body = {"schema": ATTESTED_CONTEXT_SCHEMA, "session_root": session_root,
            "subject_root": subject_root, "policy_roots": policy_roots,
            "capability_registry_root": capability_registry_root,
            "profile_root": profile_root, "jurisdiction_root": jurisdiction_root,
            "retained_context_roots": retained_context_roots,
            "mediated_channels": sorted(CHANNELS),
            "integration_mode": "ENFORCED_HOST", "host_policy": policy,
            "expected_host_policy_root": expected_host_policy_root,
            "host_attestation": attestation,
            "host_attestation_root": attestation["host_attestation_root"],
            "attestation_checked_at_ns": now_ns, **BOUNDARY}
    return {**body, "context_root": root(body)}


def validate_pippi_context(value: Any) -> dict[str, Any]:
    require(type(value) is dict, "PIPPI_CONTEXT_INVALID")
    if value.get("schema") == ATTESTED_CONTEXT_SCHEMA:
        item = exact_keys(value, {"schema", "session_root", "subject_root", "policy_roots",
            "capability_registry_root", "profile_root", "jurisdiction_root",
            "retained_context_roots", "mediated_channels", "integration_mode",
            "host_policy", "expected_host_policy_root", "host_attestation",
            "host_attestation_root",
            "attestation_checked_at_ns", "standing", "authority_effect", "real_a5", "g0",
            "context_root"})
        expected = build_attested_pippi_context(session_root=item["session_root"],
            subject_root=item["subject_root"], policy_roots=item["policy_roots"],
            capability_registry_root=item["capability_registry_root"],
            profile_root=item["profile_root"], jurisdiction_root=item["jurisdiction_root"],
            retained_context_roots=item["retained_context_roots"],
            expected_host_policy_root=item["expected_host_policy_root"],
            host_policy=item["host_policy"], host_attestation=item["host_attestation"],
            now_ns=item["attestation_checked_at_ns"])
        require(item == expected, "PIPPI_CONTEXT_INVALID")
        return deepcopy(item)
    item = exact_keys(value, {"schema", "session_root", "subject_root", "policy_roots",
        "capability_registry_root", "profile_root", "jurisdiction_root",
        "retained_context_roots", "mediated_channels", "integration_mode",
        "standing", "authority_effect", "real_a5", "g0", "context_root"})
    require(item["schema"] == CONTEXT_SCHEMA, "PIPPI_CONTEXT_INVALID")
    # Historical v0.1 contexts that declared all seven channels may retain the
    # old label for byte-level compatibility.  They are never treated as
    # effectively enforced by current code.
    require(item["integration_mode"] in {"SIDECAR_PARTIAL", "ENFORCED_HOST"},
            "PIPPI_CONTEXT_INVALID")
    for name in ("session_root", "subject_root", "capability_registry_root",
                 "profile_root", "jurisdiction_root"):
        require_root(item[name])
    require(item["policy_roots"] == sorted(set(item["policy_roots"]))
            and item["retained_context_roots"] == sorted(set(item["retained_context_roots"]))
            and item["mediated_channels"] == sorted(set(item["mediated_channels"]))
            and set(item["mediated_channels"]) <= CHANNELS,
            "PIPPI_CONTEXT_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "context_root"}
    require(item["context_root"] == root(body), "PIPPI_CONTEXT_INVALID")
    return deepcopy(item)


def effective_integration_mode(context: dict[str, Any], *,
                               expected_host_policy_root: str | None = None) -> str:
    checked = validate_pippi_context(context)
    if (checked["schema"] == ATTESTED_CONTEXT_SCHEMA
            and expected_host_policy_root is not None
            and checked["expected_host_policy_root"] == require_root(
                expected_host_policy_root)):
        return "ENFORCED_HOST"
    return "SIDECAR_PARTIAL"


def build_model_draft(*, turn_id: str, context: dict[str, Any], text: str,
                      proposals: list[dict[str, Any]]) -> dict[str, Any]:
    _identifier(turn_id, "PIPPI_TURN_ID_INVALID")
    context = validate_pippi_context(context)
    require(type(text) is str, "PIPPI_DRAFT_TEXT_INVALID")
    normalized = []
    seen: set[str] = set()
    require(type(proposals) is list, "PIPPI_PROPOSALS_INVALID")
    for raw in proposals:
        item = exact_keys(raw, {"proposal_id", "kind", "payload_root", "effect_class"})
        proposal_id = _identifier(item["proposal_id"], "PIPPI_PROPOSAL_ID_INVALID")
        require(proposal_id not in seen, "PIPPI_PROPOSAL_DUPLICATE")
        seen.add(proposal_id)
        require(item["kind"] in {"TEXT", "TOOL_CALL", "CAPABILITY_GRANT", "POLICY_CHANGE"},
                "PIPPI_PROPOSAL_KIND_INVALID")
        require_root(item["payload_root"])
        require(item["effect_class"] in {"NONE", "PURE_COMPUTATION", "READ_ONLY",
            "LOCAL_ARTIFACT_PREPARATION", "WRITE_WORKSPACE", "DELETE_WORKSPACE",
            "NETWORK", "INSTALL", "PERSISTENT_HOST_STATE", "AUTHORITY_CHANGE"},
            "PIPPI_EFFECT_CLASS_INVALID")
        normalized.append(deepcopy(item))
    normalized.sort(key=lambda row: row["proposal_id"])
    raw = text.encode("utf-8")
    body = {"schema": DRAFT_SCHEMA, "turn_id": turn_id,
            "context_root": context["context_root"], "text": text,
            "text_sha256": hashlib.sha256(raw).hexdigest(),
            "proposals": normalized, **BOUNDARY}
    return {**body, "draft_root": root(body)}


def validate_model_draft(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "turn_id", "context_root", "text",
                              "text_sha256", "proposals", "standing",
                              "authority_effect", "real_a5", "g0", "draft_root"})
    require(item["schema"] == DRAFT_SCHEMA, "PIPPI_DRAFT_SCHEMA_INVALID")
    _identifier(item["turn_id"], "PIPPI_TURN_ID_INVALID")
    require_root(item["context_root"])
    require(type(item["text"]) is str, "PIPPI_DRAFT_TEXT_INVALID")
    require(item["text_sha256"] == hashlib.sha256(item["text"].encode("utf-8")).hexdigest(),
            "PIPPI_DRAFT_TEXT_HASH_INVALID")
    require(type(item["proposals"]) is list, "PIPPI_PROPOSALS_INVALID")
    seen: set[str] = set()
    for proposal in item["proposals"]:
        row = exact_keys(proposal, {"proposal_id", "kind", "payload_root", "effect_class"})
        proposal_id = _identifier(row["proposal_id"], "PIPPI_PROPOSAL_ID_INVALID")
        require(proposal_id not in seen, "PIPPI_PROPOSAL_DUPLICATE")
        seen.add(proposal_id)
        require(row["kind"] in {"TEXT", "TOOL_CALL", "CAPABILITY_GRANT", "POLICY_CHANGE"},
                "PIPPI_PROPOSAL_KIND_INVALID")
        require_root(row["payload_root"])
        require(row["effect_class"] in {"NONE", "PURE_COMPUTATION", "READ_ONLY",
            "LOCAL_ARTIFACT_PREPARATION", "WRITE_WORKSPACE", "DELETE_WORKSPACE",
            "NETWORK", "INSTALL", "PERSISTENT_HOST_STATE", "AUTHORITY_CHANGE"},
            "PIPPI_EFFECT_CLASS_INVALID")
    require(item["proposals"] == sorted(item["proposals"], key=lambda row: row["proposal_id"]),
            "PIPPI_PROPOSAL_ORDER_INVALID")
    body = {key: deepcopy(row) for key, row in item.items() if key != "draft_root"}
    require(item["draft_root"] == root(body)
            and all(item[key] == value for key, value in BOUNDARY.items()),
            "PIPPI_DRAFT_INVALID")
    return deepcopy(item)


def build_pippi_decision(*, draft: dict[str, Any], policy_evaluation_roots: list[str],
                         proposal_dispositions: list[dict[str, Any]],
                         semantic_resolution_root: str | None,
                         semantic_status: str) -> dict[str, Any]:
    draft = validate_model_draft(draft)
    require(type(policy_evaluation_roots) is list
            and policy_evaluation_roots == sorted(set(policy_evaluation_roots)),
            "PIPPI_POLICY_EVALUATIONS_INVALID")
    for value in policy_evaluation_roots:
        require_root(value)
    require(semantic_status in {"PASS", "ADVISORY", "HELD", "REFUSED", "NOT_REQUIRED"},
            "PIPPI_SEMANTIC_STATUS_INVALID")
    require((semantic_resolution_root is None) == (semantic_status == "NOT_REQUIRED"),
            "PIPPI_SEMANTIC_ROOT_INVALID")
    if semantic_resolution_root is not None:
        require_root(semantic_resolution_root)
    proposal_ids = {row["proposal_id"] for row in draft["proposals"]}
    dispositions = []
    seen: set[str] = set()
    for raw in proposal_dispositions:
        item = exact_keys(raw, {"proposal_id", "declared", "effectful", "decision",
                                "reason_codes", "contract_root"})
        proposal_id = _identifier(item["proposal_id"], "PIPPI_DISPOSITION_ID_INVALID")
        require(proposal_id in proposal_ids and proposal_id not in seen,
                "PIPPI_DISPOSITION_UNKNOWN_OR_DUPLICATE")
        seen.add(proposal_id)
        require(type(item["declared"]) is bool and type(item["effectful"]) is bool
                and item["decision"] in PROPOSAL_DECISIONS,
                "PIPPI_DISPOSITION_INVALID")
        require(type(item["reason_codes"]) is list
                and item["reason_codes"] == sorted(set(item["reason_codes"])),
                "PIPPI_REASON_CODES_INVALID")
        for code in item["reason_codes"]:
            _identifier(code, "PIPPI_REASON_CODE_INVALID")
        require(item["contract_root"] is None or require_root(item["contract_root"]),
                "PIPPI_CONTRACT_ROOT_INVALID")
        require(item["declared"] is (item["contract_root"] is not None),
                "PIPPI_DECLARATION_BINDING_INVALID")
        require(not (item["effectful"] and not item["declared"]
                     and item["decision"] in {"PASS", "ADVISORY"}),
                "PIPPI_UNDECLARED_EFFECT_NOT_HELD")
        dispositions.append(deepcopy(item))
    require(seen == proposal_ids, "PIPPI_DISPOSITION_DENOMINATOR_MISMATCH")
    dispositions.sort(key=lambda row: row["proposal_id"])
    statuses = {row["decision"] for row in dispositions}
    if "REFUSED" in statuses or semantic_status == "REFUSED":
        status = "REFUSED"
    elif "HELD" in statuses or semantic_status == "HELD":
        status = "HELD"
    elif "ADVISORY" in statuses or semantic_status == "ADVISORY":
        status = "ADVISORY"
    else:
        status = "VALIDATED"
    body = {"schema": DECISION_SCHEMA, "draft_root": draft["draft_root"],
            "context_root": draft["context_root"],
            "policy_evaluation_roots": policy_evaluation_roots,
            "proposal_dispositions": dispositions,
            "semantic_resolution_root": semantic_resolution_root,
            "semantic_status": semantic_status, "status": status, **BOUNDARY}
    return {**body, "decision_root": root(body)}


def validate_pippi_decision(value: Any, *, draft: dict[str, Any] | None = None) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "draft_root", "context_root",
        "policy_evaluation_roots", "proposal_dispositions", "semantic_resolution_root",
        "semantic_status", "status", "standing", "authority_effect", "real_a5", "g0",
        "decision_root"})
    require(item["schema"] == DECISION_SCHEMA, "PIPPI_DECISION_SCHEMA_INVALID")
    require_root(item["draft_root"]); require_root(item["context_root"])
    require(item["policy_evaluation_roots"] == sorted(set(item["policy_evaluation_roots"])),
            "PIPPI_POLICY_EVALUATIONS_INVALID")
    for value_root in item["policy_evaluation_roots"]:
        require_root(value_root)
    require(item["semantic_status"] in {"PASS", "ADVISORY", "HELD", "REFUSED", "NOT_REQUIRED"},
            "PIPPI_SEMANTIC_STATUS_INVALID")
    require((item["semantic_resolution_root"] is None) ==
            (item["semantic_status"] == "NOT_REQUIRED"), "PIPPI_SEMANTIC_ROOT_INVALID")
    if item["semantic_resolution_root"] is not None:
        require_root(item["semantic_resolution_root"])
    dispositions = item["proposal_dispositions"]
    require(type(dispositions) is list
            and dispositions == sorted(dispositions, key=lambda row: row["proposal_id"]),
            "PIPPI_DISPOSITION_ORDER_INVALID")
    seen: set[str] = set()
    for raw in dispositions:
        row = exact_keys(raw, {"proposal_id", "declared", "effectful", "decision",
                               "reason_codes", "contract_root"})
        proposal_id = _identifier(row["proposal_id"], "PIPPI_DISPOSITION_ID_INVALID")
        require(proposal_id not in seen, "PIPPI_DISPOSITION_DUPLICATE")
        seen.add(proposal_id)
        require(type(row["declared"]) is bool and type(row["effectful"]) is bool
                and row["decision"] in PROPOSAL_DECISIONS,
                "PIPPI_DISPOSITION_INVALID")
        require(row["reason_codes"] == sorted(set(row["reason_codes"])),
                "PIPPI_REASON_CODES_INVALID")
        for code in row["reason_codes"]:
            _identifier(code, "PIPPI_REASON_CODE_INVALID")
        require(row["contract_root"] is None or require_root(row["contract_root"]),
                "PIPPI_CONTRACT_ROOT_INVALID")
        require(row["declared"] is (row["contract_root"] is not None),
                "PIPPI_DECLARATION_BINDING_INVALID")
        require(not (row["effectful"] and not row["declared"]
                     and row["decision"] in {"PASS", "ADVISORY"}),
                "PIPPI_UNDECLARED_EFFECT_NOT_HELD")
    if draft is not None:
        draft = validate_model_draft(draft)
        require(item["draft_root"] == draft["draft_root"]
                and item["context_root"] == draft["context_root"]
                and seen == {row["proposal_id"] for row in draft["proposals"]},
                "PIPPI_DECISION_DRAFT_BINDING_INVALID")
    statuses = {row["decision"] for row in dispositions}
    expected_status = ("REFUSED" if "REFUSED" in statuses or item["semantic_status"] == "REFUSED"
        else "HELD" if "HELD" in statuses or item["semantic_status"] == "HELD"
        else "ADVISORY" if "ADVISORY" in statuses or item["semantic_status"] == "ADVISORY"
        else "VALIDATED")
    body = {key: deepcopy(row) for key, row in item.items() if key != "decision_root"}
    require(item["status"] == expected_status and item["decision_root"] == root(body)
            and all(item[key] == value for key, value in BOUNDARY.items()),
            "PIPPI_DECISION_INVALID")
    return deepcopy(item)


def build_human_projection(*, draft: dict[str, Any], decision: dict[str, Any],
                           view: str, annotation_root: str | None = None) -> dict[str, Any]:
    draft = validate_model_draft(draft)
    decision = validate_pippi_decision(decision, draft=draft)
    require(view in {"READING", "INTEGER", "SPLIT", "AUDIT"},
            "PIPPI_VIEW_INVALID")
    require(annotation_root is None or require_root(annotation_root),
            "PIPPI_ANNOTATION_ROOT_INVALID")
    require((view == "READING") or annotation_root is not None,
            "PIPPI_ANNOTATION_REQUIRED")
    body = {"schema": PROJECTION_SCHEMA, "draft_root": draft["draft_root"],
            "decision_root": decision["decision_root"], "view": view,
            "display_text": draft["text"], "text_sha256": draft["text_sha256"],
            "annotation_root": annotation_root, "status": decision["status"],
            "host_rendering_required": True, **BOUNDARY}
    return {**body, "projection_root": root(body)}


def validate_human_projection(value: Any, *, draft: dict[str, Any],
                              decision: dict[str, Any]) -> dict[str, Any]:
    draft = validate_model_draft(draft)
    decision = validate_pippi_decision(decision, draft=draft)
    item = exact_keys(value, {"schema", "draft_root", "decision_root", "view",
        "display_text", "text_sha256", "annotation_root", "status",
        "host_rendering_required", "standing", "authority_effect", "real_a5", "g0",
        "projection_root"})
    expected = build_human_projection(draft=draft, decision=decision, view=item["view"],
                                      annotation_root=item["annotation_root"])
    require(item == expected, "PIPPI_PROJECTION_INVALID")
    return deepcopy(item)


def build_constitutional_exception(*, draft_root: str, proposal_id: str,
                                   missing_rule_id: str, requested_decision: str,
                                   affected_obligation_ids: list[str],
                                   external_decision_root: str | None = None,
                                   successor_policy_root: str | None = None) -> dict[str, Any]:
    require_root(draft_root)
    _identifier(proposal_id, "PIPPI_EXCEPTION_PROPOSAL_INVALID")
    _identifier(missing_rule_id, "PIPPI_EXCEPTION_RULE_INVALID")
    _identifier(requested_decision, "PIPPI_EXCEPTION_DECISION_INVALID")
    require(type(affected_obligation_ids) is list
            and affected_obligation_ids == sorted(set(affected_obligation_ids))
            and bool(affected_obligation_ids), "PIPPI_EXCEPTION_OBLIGATIONS_INVALID")
    for value in affected_obligation_ids:
        _identifier(value, "PIPPI_EXCEPTION_OBLIGATION_INVALID")
    for value in (external_decision_root, successor_policy_root):
        require(value is None or require_root(value), "PIPPI_EXCEPTION_ROOT_INVALID")
    require((external_decision_root is None) == (successor_policy_root is None),
            "PIPPI_EXCEPTION_RESOLUTION_INCOMPLETE")
    body = {"schema": EXCEPTION_SCHEMA, "draft_root": draft_root,
            "proposal_id": proposal_id, "missing_rule_id": missing_rule_id,
            "requested_decision": requested_decision,
            "affected_obligation_ids": affected_obligation_ids,
            "external_decision_root": external_decision_root,
            "successor_policy_root": successor_policy_root,
            "status": "RESOLVED" if external_decision_root else "OPEN",
            "exception_grants_authority": False, **BOUNDARY}
    return {**body, "exception_root": root(body)}


def build_turn_envelope(*, sequence: int, previous_turn_root: str | None,
                        context: dict[str, Any], draft: dict[str, Any],
                        decision: dict[str, Any], projection: dict[str, Any],
                        tool_proposal_roots: list[str], dispatch_receipt_roots: list[str],
                        tool_result_roots: list[str]) -> dict[str, Any]:
    """Bind a complete observable turn without claiming hidden model reasoning."""
    require(type(sequence) is int and sequence >= 1
            and ((sequence == 1) == (previous_turn_root is None)),
            "PIPPI_TURN_SEQUENCE_INVALID")
    if previous_turn_root is not None:
        require_root(previous_turn_root)
    context = validate_pippi_context(context)
    draft = validate_model_draft(draft)
    require(draft["context_root"] == context["context_root"],
            "PIPPI_TURN_DRAFT_BINDING_INVALID")
    decision = validate_pippi_decision(decision, draft=draft)
    projection = validate_human_projection(projection, draft=draft, decision=decision)
    roots = []
    for values, code in ((tool_proposal_roots, "PIPPI_TOOL_PROPOSALS_INVALID"),
                         (dispatch_receipt_roots, "PIPPI_DISPATCH_RECEIPTS_INVALID"),
                         (tool_result_roots, "PIPPI_TOOL_RESULTS_INVALID")):
        require(type(values) is list and values == sorted(set(values)), code)
        for value in values:
            require_root(value)
        roots.append(list(values))
    body = {"schema": TURN_SCHEMA, "sequence": sequence,
            "previous_turn_root": previous_turn_root,
            "context_root": context["context_root"], "draft_root": draft["draft_root"],
            "decision_root": decision["decision_root"],
            "projection_root": projection["projection_root"],
            "tool_proposal_roots": roots[0], "dispatch_receipt_roots": roots[1],
            "tool_result_roots": roots[2],
            "observable_model_draft_only": True,
            "status": decision["status"], **BOUNDARY}
    return {**body, "turn_root": root(body)}


def validate_turn_envelope(value: Any, *, context: dict[str, Any], draft: dict[str, Any],
                           decision: dict[str, Any], projection: dict[str, Any]) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "sequence", "previous_turn_root", "context_root",
        "draft_root", "decision_root", "projection_root", "tool_proposal_roots",
        "dispatch_receipt_roots", "tool_result_roots", "observable_model_draft_only",
        "status", "standing", "authority_effect", "real_a5", "g0", "turn_root"})
    context = validate_pippi_context(context)
    draft = validate_model_draft(draft)
    decision = validate_pippi_decision(decision, draft=draft)
    projection = validate_human_projection(projection, draft=draft, decision=decision)
    expected = build_turn_envelope(sequence=item["sequence"],
        previous_turn_root=item["previous_turn_root"], context=context, draft=draft,
        decision=decision, projection=projection,
        tool_proposal_roots=item["tool_proposal_roots"],
        dispatch_receipt_roots=item["dispatch_receipt_roots"],
        tool_result_roots=item["tool_result_roots"])
    require(item == expected, "PIPPI_TURN_INVALID")
    return deepcopy(item)

"""Strict, registry-pinned adapter for coding agents and MCP-style tool hosts."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from uclop.canonical import exact_keys, require, require_root, root

from .profiles import profile_allows_surface, profile_registry
from .system import BOUNDARY, capability_registry


AGENT_LOOP = (
    "ORIENT",
    "BIND_SUBJECT",
    "VALIDATE_OR_COMPILE",
    "PLAN",
    "GATE_EFFECTS_EXTERNALLY",
    "EXPORT_JOURNAL",
)


class AgentToolAdapter:
    """Expose only a pinned product profile through a strict request envelope."""

    def __init__(self, *, profile_id: str, capability_registry_root: str,
                 profile_registry_root: str,
                 dispatcher: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
        current_capabilities = capability_registry()
        current_profiles = profile_registry()
        require(capability_registry_root == current_capabilities["root"],
                "UCM_AGENT_CAPABILITY_REGISTRY_MISMATCH")
        require(profile_registry_root == current_profiles["profile_registry_root"],
                "UCM_AGENT_PROFILE_REGISTRY_MISMATCH")
        require(any(row["profile_id"] == profile_id for row in current_profiles["profiles"]),
                "UCM_PROFILE_UNKNOWN")
        self.profile_id = profile_id
        self.capability_registry_root = capability_registry_root
        self.profile_registry_root = profile_registry_root
        self.dispatcher = dispatcher

    def call(self, *, surface: str, payload: dict[str, Any],
             request_id: str) -> dict[str, Any]:
        require(profile_allows_surface(self.profile_id, surface)["status"] == "PASS_ALLOWED",
                "UCM_AGENT_SURFACE_REFUSED", detail=f"{self.profile_id}:{surface}")
        require(type(payload) is dict and type(request_id) is str and request_id,
                "UCM_AGENT_REQUEST_INVALID")
        request = {
            "schema": "mosaic.ucm.request.v0.2",
            "surface": surface, "payload": deepcopy(payload),
            "request_id": request_id,
            "profile_selection": {
                "schema": "mosaic.ucm.product-profile-selection.v0.1",
                "profile_id": self.profile_id,
                "capability_registry_root": self.capability_registry_root,
            },
        }
        result = self.dispatcher(request)
        require(type(result) is dict and result.get("surface") == surface,
                "UCM_AGENT_RESULT_INVALID")
        return result


def agent_loop_contract() -> dict[str, Any]:
    capabilities = capability_registry()
    profiles = profile_registry()
    body = {
        "schema": "mosaic.ucm.agent-loop-contract.v0.1",
        "steps": list(AGENT_LOOP),
        "capability_registry_root": capabilities["root"],
        "profile_registry_root": profiles["profile_registry_root"],
        "tool_result_policy": [
            "RETURN_EXACT_RESULT_ROOTS_AND_TYPED_STATUS",
            "RETURN_JOURNAL_HEAD_AFTER_STATE_CHANGE",
            "DO_NOT_TREAT_PROGRESS_JSONL_AS_EVIDENCE",
        ],
        "chat_memory_policy": [
            "CARRY_ROOTS_AND_HUMAN_SUMMARIES_ONLY",
            "RELOAD_CANONICAL_JOURNAL_BEFORE_CONTINUATION",
            "NEVER_INFER_AUTHORITY_FROM_CHAT_HISTORY",
        ],
        "effect_policy": "NO_EFFECT_WITHOUT_OPERATIONAL_GATEWAY",
        **BOUNDARY,
    }
    return {**body, "contract_root": root(body)}


def validate_agent_sidecar(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "capability_registry_root",
                              "profile_registry_root", "profile_id",
                              "agent_loop_contract_root"})
    require(item["schema"] == "mosaic.ucm.agent-sidecar-binding.v0.1",
            "UCM_AGENT_SIDECAR_SCHEMA_INVALID")
    require_root(item["capability_registry_root"])
    require_root(item["profile_registry_root"])
    require_root(item["agent_loop_contract_root"])
    require(item["capability_registry_root"] == capability_registry()["root"],
            "UCM_AGENT_CAPABILITY_REGISTRY_MISMATCH")
    require(item["profile_registry_root"] == profile_registry()["profile_registry_root"],
            "UCM_AGENT_PROFILE_REGISTRY_MISMATCH")
    require(item["agent_loop_contract_root"] == agent_loop_contract()["contract_root"],
            "UCM_AGENT_LOOP_CONTRACT_MISMATCH")
    require(profile_allows_surface(item["profile_id"], "ORIENT")["status"] == "PASS_ALLOWED",
            "UCM_PROFILE_UNKNOWN")
    return deepcopy(item)

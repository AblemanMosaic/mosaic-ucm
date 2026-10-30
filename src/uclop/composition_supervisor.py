from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .canonical import exact_keys, require, require_root, root
from .composition import verify_composition


_ID = re.compile(r"^[a-z][a-z0-9_.-]{2,95}$")


class DurableCompositionSupervisor:
    """Append-only, fixture-only orchestration for an exact compiled composition."""

    def __init__(
        self, *, subject_root: str, registry: dict[str, Any], policy: dict[str, Any],
        composition: dict[str, Any], initial_capsule: dict[str, Any] | None = None,
        expected_pin: str | None = None,
    ) -> None:
        self.subject_root = require_root(subject_root)
        verify_composition(composition, registry=registry, policy=policy, expected_subject_root=self.subject_root)
        self.composition = deepcopy(composition)
        self._nodes = {item["node_id"]: item for item in composition["nodes"]}
        self._predecessors: dict[str, list[str]] = {key: [] for key in self._nodes}
        for edge in composition["edges"]:
            self._predecessors[edge["target"]].append(edge["source"])
        self._sequence = 0
        self._head = root({"composition_supervisor_genesis": True, "subject_root": self.subject_root, "composition_root": composition["composition_root"]})
        self._runs: dict[str, dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []
        self._idempotency: dict[str, str] = {}
        if initial_capsule is not None:
            self.restore(initial_capsule, expected_pin=require_root(expected_pin))
        else:
            require(expected_pin is None, "COMPOSITION_CAPSULE_REQUIRED")

    def _append(self, event_type: str, run_id: str, payload: dict[str, Any], key: str) -> dict[str, Any]:
        require(type(key) is str and 8 <= len(key) <= 128, "COMPOSITION_IDEMPOTENCY_KEY_INVALID")
        proposed = root({"event_type": event_type, "run_id": run_id, "payload": payload})
        if key in self._idempotency:
            require(self._idempotency[key] == proposed, "COMPOSITION_IDEMPOTENCY_CONFLICT")
            return deepcopy(next(item for item in self._events if item["idempotency_key"] == key))
        body = {
            "schema": "ucl.ucm.composition_supervisor_event.v1", "subject_root": self.subject_root,
            "composition_root": self.composition["composition_root"], "event_type": event_type, "run_id": run_id,
            "payload": deepcopy(payload), "payload_root": root(payload), "idempotency_key": key,
            "sequence": self._sequence + 1, "previous_head": self._head, "effect_observed": "NONE",
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        }
        event = {**body, "event_root": root(body)}
        self._events.append(event); self._sequence += 1; self._head = event["event_root"]; self._idempotency[key] = proposed
        return deepcopy(event)

    def start(self, *, run_id: str, tenant_id: str, tenant_principal_root: str, input_root: str, idempotency_key: str) -> dict[str, Any]:
        require(type(run_id) is str and bool(_ID.fullmatch(run_id)) and run_id not in self._runs, "COMPOSITION_RUN_ID_INVALID")
        require(type(tenant_id) is str and bool(_ID.fullmatch(tenant_id)), "COMPOSITION_TENANT_ID_INVALID")
        state = {
            "tenant_id": tenant_id, "tenant_principal_root": require_root(tenant_principal_root),
            "input_root": require_root(input_root), "completed_nodes": [], "node_outputs": {},
            "unbound_effect_nodes": [], "status": "ACTIVE",
        }
        event = self._append("START", run_id, state, idempotency_key); self._runs[run_id] = state; return event

    def record_node(
        self, *, run_id: str, tenant_principal_root: str, node_id: str, input_root: str,
        output_root: str, disposition: str, idempotency_key: str,
    ) -> dict[str, Any]:
        require(run_id in self._runs, "COMPOSITION_RUN_UNKNOWN")
        state = self._runs[run_id]
        require(state["tenant_principal_root"] == require_root(tenant_principal_root), "COMPOSITION_CALLER_MISMATCH")
        require(state["status"] == "ACTIVE", "COMPOSITION_RUN_NOT_ACTIVE")
        expected_node = self.composition["topological_order"][len(state["completed_nodes"])]
        require(node_id == expected_node, "COMPOSITION_NODE_ORDER_INVALID")
        predecessors = sorted(self._predecessors[node_id])
        expected_input = state["input_root"] if not predecessors else root({"predecessor_outputs": [{"node_id": item, "output_root": state["node_outputs"][item]} for item in predecessors]})
        require(require_root(input_root) == expected_input, "COMPOSITION_NODE_INPUT_MISMATCH")
        node = self._nodes[node_id]
        expected_disposition = "PASS_FIXTURE_ONLY" if node["effect_class"] == "NONE" else "UNBOUND_EFFECT_PROPOSAL"
        require(disposition == expected_disposition, "COMPOSITION_NODE_DISPOSITION_INVALID")
        payload = {"node_id": node_id, "input_root": input_root, "output_root": require_root(output_root), "effect_class": node["effect_class"], "disposition": disposition}
        event = self._append("NODE", run_id, payload, idempotency_key)
        state["completed_nodes"].append(node_id); state["node_outputs"][node_id] = payload["output_root"]
        if node["effect_class"] != "NONE":
            state["unbound_effect_nodes"].append(node_id)
        if len(state["completed_nodes"]) == len(self.composition["topological_order"]):
            state["status"] = "REFERENCE_PLAN_COMPLETE" if not state["unbound_effect_nodes"] else "REFERENCE_PLAN_COMPLETE_WITH_UNBOUND_EFFECTS"
        return event

    def export_capsule(self) -> dict[str, Any]:
        body = {
            "schema": "ucl.ucm.composition_supervisor_capsule.v1", "subject_root": self.subject_root,
            "composition_root": self.composition["composition_root"], "sequence": self._sequence, "head": self._head,
            "runs": {key: deepcopy(self._runs[key]) for key in sorted(self._runs)}, "events": deepcopy(self._events),
            "idempotency": {key: self._idempotency[key] for key in sorted(self._idempotency)},
            "host_actions": 0, "effect_observed": "NONE", "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        }
        return {**body, "capsule_root": root(body)}

    def restore(self, capsule: Any, *, expected_pin: str) -> None:
        item = exact_keys(capsule, {"schema", "subject_root", "composition_root", "sequence", "head", "runs", "events", "idempotency", "host_actions", "effect_observed", "standing", "authority_effect", "capsule_root"}, "$.composition_capsule")
        body = {key: value for key, value in item.items() if key != "capsule_root"}
        require(item["schema"] == "ucl.ucm.composition_supervisor_capsule.v1" and item["capsule_root"] == root(body) == expected_pin, "COMPOSITION_CAPSULE_PIN_MISMATCH")
        require(item["subject_root"] == self.subject_root and item["composition_root"] == self.composition["composition_root"], "COMPOSITION_CAPSULE_CONTEXT_MISMATCH")
        require(item["host_actions"] == 0 and item["effect_observed"] == "NONE" and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "COMPOSITION_CAPSULE_AUTHORITY_INVALID")
        # Replay without recursive construction: apply only exact events through the public rules.
        saved_events = deepcopy(item["events"]); expected_runs = deepcopy(item["runs"]); expected_idempotency = deepcopy(item["idempotency"])
        self._sequence = 0; self._head = root({"composition_supervisor_genesis": True, "subject_root": self.subject_root, "composition_root": self.composition["composition_root"]}); self._runs = {}; self._events = []; self._idempotency = {}
        for sequence, event in enumerate(saved_events, 1):
            exact_keys(event, {"schema", "subject_root", "composition_root", "event_type", "run_id", "payload", "payload_root", "idempotency_key", "sequence", "previous_head", "effect_observed", "standing", "authority_effect", "event_root"}, f"$.events[{sequence - 1}]")
            event_body = {key: value for key, value in event.items() if key != "event_root"}
            require(event["event_root"] == root(event_body) and event["payload_root"] == root(event["payload"]) and event["sequence"] == sequence and event["previous_head"] == self._head, "COMPOSITION_EVENT_CHAIN_INVALID")
            payload = event["payload"]
            if event["event_type"] == "START":
                self.start(run_id=event["run_id"], tenant_id=payload["tenant_id"], tenant_principal_root=payload["tenant_principal_root"], input_root=payload["input_root"], idempotency_key=event["idempotency_key"])
            elif event["event_type"] == "NODE":
                self.record_node(run_id=event["run_id"], tenant_principal_root=self._runs[event["run_id"]]["tenant_principal_root"], node_id=payload["node_id"], input_root=payload["input_root"], output_root=payload["output_root"], disposition=payload["disposition"], idempotency_key=event["idempotency_key"])
            else:
                require(False, "COMPOSITION_EVENT_TYPE_INVALID")
            require(self._events[-1] == event, "COMPOSITION_EVENT_REPLAY_MISMATCH")
        require(self._sequence == item["sequence"] and self._head == item["head"] and self._runs == expected_runs and self._idempotency == expected_idempotency, "COMPOSITION_CAPSULE_STATE_MISMATCH")

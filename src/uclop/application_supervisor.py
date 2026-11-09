from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .canonical import exact_keys, require, require_root, root


_ID = re.compile(r"^[a-z][a-z0-9_.-]{2,95}$")
STATES = {"REGISTERED", "READY", "RUNNING", "PAUSED", "FAILED", "RECOVERY_PENDING", "RETIRED"}
TRANSITIONS = {
    "REGISTERED": {"READY", "RETIRED"},
    "READY": {"RUNNING", "PAUSED", "RETIRED"},
    "RUNNING": {"PAUSED", "FAILED"},
    "PAUSED": {"READY", "RECOVERY_PENDING", "RETIRED"},
    "FAILED": {"RECOVERY_PENDING", "RETIRED"},
    "RECOVERY_PENDING": {"READY", "RETIRED"},
    "RETIRED": set(),
}


def _identifier(value: Any, code: str) -> str:
    require(type(value) is str and bool(_ID.fullmatch(value)), code)
    return value


class DurableApplicationSupervisor:
    """Append-only reference supervisor; it never starts or stops a host process."""

    def __init__(
        self, *, subject_root: str, policy_root: str,
        initial_capsule: dict[str, Any] | None = None, expected_pin: str | None = None,
    ) -> None:
        self.subject_root = require_root(subject_root)
        self.policy_root = require_root(policy_root)
        self._sequence = 0
        self._head = root({"supervisor_genesis": True, "subject_root": self.subject_root, "policy_root": self.policy_root})
        self._applications: dict[str, dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []
        self._idempotency: dict[str, str] = {}
        if initial_capsule is not None:
            self.restore(initial_capsule, expected_pin=require_root(expected_pin))
        else:
            require(expected_pin is None, "SUPERVISOR_CAPSULE_REQUIRED")

    def _append(self, *, event_type: str, application_id: str, payload: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        require(type(idempotency_key) is str and 8 <= len(idempotency_key) <= 128, "SUPERVISOR_IDEMPOTENCY_KEY_INVALID")
        proposed = root({"event_type": event_type, "application_id": application_id, "payload": payload})
        if idempotency_key in self._idempotency:
            require(self._idempotency[idempotency_key] == proposed, "SUPERVISOR_IDEMPOTENCY_CONFLICT")
            return deepcopy(next(event for event in self._events if event["idempotency_key"] == idempotency_key))
        event_body = {
            "schema": "ucl.ucm.supervisor_event.v1",
            "subject_root": self.subject_root,
            "policy_root": self.policy_root,
            "event_type": event_type,
            "application_id": application_id,
            "payload": deepcopy(payload),
            "payload_root": root(payload),
            "idempotency_key": idempotency_key,
            "sequence": self._sequence + 1,
            "previous_head": self._head,
            "effect_observed": "NONE",
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        event = {**event_body, "event_root": root(event_body)}
        self._events.append(event)
        self._sequence += 1
        self._head = event["event_root"]
        self._idempotency[idempotency_key] = proposed
        return deepcopy(event)

    def register(
        self, *, application_id: str, application_root: str, tenant_id: str,
        tenant_principal_root: str, idempotency_key: str,
    ) -> dict[str, Any]:
        _identifier(application_id, "SUPERVISOR_APPLICATION_ID_INVALID")
        _identifier(tenant_id, "SUPERVISOR_TENANT_ID_INVALID")
        require(application_id not in self._applications, "SUPERVISOR_APPLICATION_DUPLICATE")
        state = {
            "application_root": require_root(application_root),
            "tenant_id": tenant_id,
            "tenant_principal_root": require_root(tenant_principal_root),
            "state": "REGISTERED",
            "health_root": None,
            "open_incident_root": None,
            "generation": 1,
        }
        event = self._append(event_type="REGISTER", application_id=application_id, payload=state, idempotency_key=idempotency_key)
        self._applications[application_id] = state
        return event

    def transition(
        self, *, application_id: str, caller_principal_root: str, target_state: str,
        evidence_root: str, idempotency_key: str,
    ) -> dict[str, Any]:
        require(application_id in self._applications, "SUPERVISOR_APPLICATION_UNKNOWN")
        require(target_state in STATES, "SUPERVISOR_TARGET_STATE_INVALID")
        current = self._applications[application_id]
        require(current["tenant_principal_root"] == require_root(caller_principal_root), "SUPERVISOR_CALLER_MISMATCH")
        require(target_state in TRANSITIONS[current["state"]], "SUPERVISOR_TRANSITION_INVALID")
        if target_state in {"READY", "RUNNING"}:
            require(current["open_incident_root"] is None, "SUPERVISOR_OPEN_INCIDENT_BLOCKS_PROGRESS")
        payload = {
            "from_state": current["state"],
            "to_state": target_state,
            "evidence_root": require_root(evidence_root),
            "generation": current["generation"],
        }
        event = self._append(event_type="TRANSITION", application_id=application_id, payload=payload, idempotency_key=idempotency_key)
        current["state"] = target_state
        return event

    def record_health(
        self, *, application_id: str, caller_principal_root: str, health_root: str,
        status: str, idempotency_key: str,
    ) -> dict[str, Any]:
        require(application_id in self._applications, "SUPERVISOR_APPLICATION_UNKNOWN")
        current = self._applications[application_id]
        require(current["tenant_principal_root"] == require_root(caller_principal_root), "SUPERVISOR_CALLER_MISMATCH")
        require(status in {"HEALTHY", "DEGRADED", "UNHEALTHY"}, "SUPERVISOR_HEALTH_STATUS_INVALID")
        payload = {"health_root": require_root(health_root), "status": status, "generation": current["generation"]}
        event = self._append(event_type="HEALTH", application_id=application_id, payload=payload, idempotency_key=idempotency_key)
        current["health_root"] = payload["health_root"]
        if status == "UNHEALTHY" and current["state"] == "RUNNING":
            current["state"] = "FAILED"
        return event

    def open_incident(
        self, *, application_id: str, caller_principal_root: str, incident_root: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        require(application_id in self._applications, "SUPERVISOR_APPLICATION_UNKNOWN")
        current = self._applications[application_id]
        require(current["tenant_principal_root"] == require_root(caller_principal_root), "SUPERVISOR_CALLER_MISMATCH")
        require(current["open_incident_root"] is None, "SUPERVISOR_INCIDENT_ALREADY_OPEN")
        payload = {"incident_root": require_root(incident_root), "generation": current["generation"]}
        event = self._append(event_type="INCIDENT_OPEN", application_id=application_id, payload=payload, idempotency_key=idempotency_key)
        current["open_incident_root"] = payload["incident_root"]
        if current["state"] == "RUNNING":
            current["state"] = "PAUSED"
        return event

    def close_incident(
        self, *, application_id: str, caller_principal_root: str, resolution_root: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        require(application_id in self._applications, "SUPERVISOR_APPLICATION_UNKNOWN")
        current = self._applications[application_id]
        require(current["tenant_principal_root"] == require_root(caller_principal_root), "SUPERVISOR_CALLER_MISMATCH")
        require(current["open_incident_root"] is not None, "SUPERVISOR_INCIDENT_NOT_OPEN")
        payload = {
            "incident_root": current["open_incident_root"],
            "resolution_root": require_root(resolution_root),
            "generation": current["generation"],
        }
        event = self._append(event_type="INCIDENT_CLOSE", application_id=application_id, payload=payload, idempotency_key=idempotency_key)
        current["open_incident_root"] = None
        return event

    def state(self, application_id: str) -> dict[str, Any]:
        require(application_id in self._applications, "SUPERVISOR_APPLICATION_UNKNOWN")
        return deepcopy(self._applications[application_id])

    def export_capsule(self) -> dict[str, Any]:
        body = {
            "schema": "ucl.ucm.application_supervisor_capsule.v1",
            "subject_root": self.subject_root,
            "policy_root": self.policy_root,
            "sequence": self._sequence,
            "head": self._head,
            "applications": {key: deepcopy(self._applications[key]) for key in sorted(self._applications)},
            "events": deepcopy(self._events),
            "idempotency": {key: self._idempotency[key] for key in sorted(self._idempotency)},
            "host_processes_started": 0,
            "effect_observed": "NONE",
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        return {**body, "capsule_root": root(body)}

    def restore(self, capsule: Any, *, expected_pin: str) -> None:
        item = exact_keys(capsule, {
            "schema", "subject_root", "policy_root", "sequence", "head", "applications", "events",
            "idempotency", "host_processes_started", "effect_observed", "standing", "authority_effect", "capsule_root",
        }, "$.supervisor_capsule")
        body = {key: item[key] for key in item if key != "capsule_root"}
        require(item["schema"] == "ucl.ucm.application_supervisor_capsule.v1" and item["capsule_root"] == root(body) == require_root(expected_pin), "SUPERVISOR_CAPSULE_PIN_MISMATCH")
        require(item["subject_root"] == self.subject_root and item["policy_root"] == self.policy_root, "SUPERVISOR_CAPSULE_CONTEXT_MISMATCH")
        require(item["host_processes_started"] == 0 and item["effect_observed"] == "NONE" and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "SUPERVISOR_CAPSULE_AUTHORITY_INVALID")
        applications: dict[str, dict[str, Any]] = {}
        idempotency: dict[str, str] = {}
        head = root({"supervisor_genesis": True, "subject_root": self.subject_root, "policy_root": self.policy_root})
        for sequence, event in enumerate(item["events"], 1):
            exact_keys(event, {
                "schema", "subject_root", "policy_root", "event_type", "application_id", "payload", "payload_root",
                "idempotency_key", "sequence", "previous_head", "effect_observed", "standing", "authority_effect", "event_root",
            }, f"$.events[{sequence - 1}]")
            event_body = {key: event[key] for key in event if key != "event_root"}
            require(event["event_root"] == root(event_body) and event["sequence"] == sequence and event["previous_head"] == head, "SUPERVISOR_EVENT_CHAIN_INVALID")
            require(event["subject_root"] == self.subject_root and event["policy_root"] == self.policy_root and event["payload_root"] == root(event["payload"]), "SUPERVISOR_EVENT_CONTEXT_INVALID")
            require(event["effect_observed"] == "NONE" and event["standing"] == "INFORMATION_ONLY" and event["authority_effect"] == "NONE", "SUPERVISOR_EVENT_AUTHORITY_INVALID")
            key = event["idempotency_key"]
            proposal = root({"event_type": event["event_type"], "application_id": event["application_id"], "payload": event["payload"]})
            require(key not in idempotency, "SUPERVISOR_EVENT_IDEMPOTENCY_DUPLICATE")
            idempotency[key] = proposal
            app_id = event["application_id"]
            payload = event["payload"]
            if event["event_type"] == "REGISTER":
                require(app_id not in applications and payload["state"] == "REGISTERED", "SUPERVISOR_REPLAY_REGISTER_INVALID")
                applications[app_id] = deepcopy(payload)
            else:
                require(app_id in applications, "SUPERVISOR_REPLAY_APPLICATION_UNKNOWN")
                current = applications[app_id]
                if event["event_type"] == "TRANSITION":
                    require(payload["from_state"] == current["state"] and payload["to_state"] in TRANSITIONS[current["state"]], "SUPERVISOR_REPLAY_TRANSITION_INVALID")
                    if payload["to_state"] in {"READY", "RUNNING"}:
                        require(current["open_incident_root"] is None, "SUPERVISOR_REPLAY_INCIDENT_BLOCK_INVALID")
                    current["state"] = payload["to_state"]
                elif event["event_type"] == "HEALTH":
                    require(payload["status"] in {"HEALTHY", "DEGRADED", "UNHEALTHY"}, "SUPERVISOR_REPLAY_HEALTH_INVALID")
                    current["health_root"] = require_root(payload["health_root"])
                    if payload["status"] == "UNHEALTHY" and current["state"] == "RUNNING": current["state"] = "FAILED"
                elif event["event_type"] == "INCIDENT_OPEN":
                    require(current["open_incident_root"] is None, "SUPERVISOR_REPLAY_INCIDENT_INVALID")
                    current["open_incident_root"] = require_root(payload["incident_root"])
                    if current["state"] == "RUNNING": current["state"] = "PAUSED"
                elif event["event_type"] == "INCIDENT_CLOSE":
                    require(current["open_incident_root"] == payload["incident_root"], "SUPERVISOR_REPLAY_INCIDENT_INVALID")
                    require_root(payload["resolution_root"]); current["open_incident_root"] = None
                else:
                    require(False, "SUPERVISOR_REPLAY_EVENT_TYPE_INVALID")
            head = event["event_root"]
        require(item["sequence"] == len(item["events"]) and item["head"] == head, "SUPERVISOR_CAPSULE_HEAD_MISMATCH")
        require(item["applications"] == applications and item["idempotency"] == {key: idempotency[key] for key in sorted(idempotency)}, "SUPERVISOR_CAPSULE_STATE_MISMATCH")
        self._sequence, self._head = item["sequence"], item["head"]
        self._applications, self._events, self._idempotency = applications, deepcopy(item["events"]), idempotency

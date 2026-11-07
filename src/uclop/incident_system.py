from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .canonical import exact_keys, require, require_root, root


SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
TRANSITIONS = {
    "OPEN": {"CONTAINED", "CLOSED"},
    "CONTAINED": {"RECOVERING", "CLOSED"},
    "RECOVERING": {"REQUALIFICATION_REQUIRED", "CLOSED"},
    "REQUALIFICATION_REQUIRED": {"CLOSED"},
    "CLOSED": set(),
}
_ID = re.compile(r"^[a-z][a-z0-9_.-]{2,95}$")


class IncidentLedger:
    """Append-only incident and requalification ledger with a NONE effect ceiling."""

    def __init__(self, *, subject_root: str, initial_capsule: dict[str, Any] | None = None, expected_pin: str | None = None) -> None:
        self.subject_root = require_root(subject_root)
        self._events: list[dict[str, Any]] = []
        self._current: dict[str, dict[str, Any]] = {}
        self._idempotency: dict[str, tuple[str, str]] = {}
        self._sequence = 0
        self._head = root({"subject_root": self.subject_root, "incident_genesis": True})
        if initial_capsule is not None:
            require(expected_pin is not None, "INCIDENT_CAPSULE_PIN_REQUIRED")
            self.restore(initial_capsule, expected_pin=expected_pin)
        else:
            require(expected_pin is None, "INCIDENT_CAPSULE_REQUIRED")

    def _append(self, body: dict[str, Any], *, idempotency_key: str) -> dict[str, Any]:
        require(type(idempotency_key) is str and 8 <= len(idempotency_key) <= 128, "IDEMPOTENCY_KEY_INVALID")
        request_root = root(body)
        if idempotency_key in self._idempotency:
            prior_request, event_root = self._idempotency[idempotency_key]
            require(prior_request == request_root, "IDEMPOTENCY_CONFLICT")
            return deepcopy(next(event for event in self._events if event["event_root"] == event_root))
        self._sequence += 1
        bound = {**body, "idempotency_key": idempotency_key, "sequence": self._sequence, "previous_head": self._head}
        event = {**bound, "event_root": root(bound)}
        self._events.append(event)
        self._head = event["event_root"]
        self._idempotency[idempotency_key] = (request_root, event["event_root"])
        self._current[event["incident_id"]] = deepcopy(event)
        return deepcopy(event)

    def open(self, *, incident_id: str, severity: str, affected_roots: list[str], evidence_roots: list[str], summary_root: str, idempotency_key: str) -> dict[str, Any]:
        require(type(incident_id) is str and bool(_ID.fullmatch(incident_id)), "INCIDENT_ID_INVALID")
        require(incident_id not in self._current, "INCIDENT_DUPLICATE")
        require(severity in SEVERITIES, "INCIDENT_SEVERITY_INVALID")
        for name, values in (("affected", affected_roots), ("evidence", evidence_roots)):
            require(type(values) is list and values == sorted(values) and len(values) == len(set(values)) and values, "INCIDENT_ROOT_SET_INVALID", detail=name)
            for value in values: require_root(value)
        body = {
            "schema": "ucl.ucm.incident_event.v1",
            "incident_id": incident_id,
            "subject_root": self.subject_root,
            "severity": severity,
            "status": "OPEN",
            "prior_event_root": None,
            "affected_roots": affected_roots,
            "evidence_roots": evidence_roots,
            "summary_root": require_root(summary_root),
            "required_actions": ["CONTAIN", "DIAGNOSE", "REPAIR", "REQUALIFY"] if severity in {"HIGH", "CRITICAL"} else ["DIAGNOSE", "REPAIR"],
            "effect_observed": "NONE",
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        return self._append(body, idempotency_key=idempotency_key)

    def transition(self, *, incident_id: str, target_status: str, evidence_roots: list[str], resolution_root: str, idempotency_key: str) -> dict[str, Any]:
        require(incident_id in self._current, "INCIDENT_UNKNOWN")
        prior = self._current[incident_id]
        require(target_status in TRANSITIONS[prior["status"]], "INCIDENT_TRANSITION_INVALID")
        require(type(evidence_roots) is list and evidence_roots == sorted(evidence_roots) and len(evidence_roots) == len(set(evidence_roots)) and evidence_roots, "INCIDENT_EVIDENCE_SET_INVALID")
        for value in evidence_roots: require_root(value)
        require(target_status != "CLOSED" or prior["status"] in {"OPEN", "CONTAINED", "RECOVERING", "REQUALIFICATION_REQUIRED"}, "INCIDENT_CLOSE_INVALID")
        body = {
            "schema": "ucl.ucm.incident_event.v1",
            "incident_id": incident_id,
            "subject_root": self.subject_root,
            "severity": prior["severity"],
            "status": target_status,
            "prior_event_root": prior["event_root"],
            "affected_roots": prior["affected_roots"],
            "evidence_roots": evidence_roots,
            "summary_root": require_root(resolution_root),
            "required_actions": [] if target_status == "CLOSED" else prior["required_actions"],
            "effect_observed": "NONE",
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        return self._append(body, idempotency_key=idempotency_key)

    def gate(self, *, affected_roots: list[str]) -> dict[str, Any]:
        require(type(affected_roots) is list and affected_roots == sorted(affected_roots) and len(affected_roots) == len(set(affected_roots)), "INCIDENT_ROOT_SET_INVALID")
        for value in affected_roots: require_root(value)
        blocking = sorted(
            event["event_root"] for event in self._current.values()
            if event["status"] != "CLOSED" and event["severity"] in {"HIGH", "CRITICAL"} and set(event["affected_roots"]) & set(affected_roots)
        )
        body = {
            "schema": "ucl.ucm.incident_gate.v1",
            "subject_root": self.subject_root,
            "affected_roots": affected_roots,
            "blocking_incident_roots": blocking,
            "status": "BLOCKED" if blocking else "PASS",
            "requires_requalification": bool(blocking),
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        return {**body, "gate_root": root(body)}

    def export_capsule(self) -> dict[str, Any]:
        body = {
            "schema": "ucl.ucm.incident_capsule.v1",
            "subject_root": self.subject_root,
            "sequence": self._sequence,
            "head": self._head,
            "events": deepcopy(self._events),
            "idempotency": {key: list(value) for key, value in sorted(self._idempotency.items())},
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        return {**body, "capsule_root": root(body)}

    def restore(self, capsule: Any, *, expected_pin: str) -> None:
        item = exact_keys(capsule, {"schema", "subject_root", "sequence", "head", "events", "idempotency", "standing", "authority_effect", "capsule_root"}, "$.incident_capsule")
        body = {key: item[key] for key in item if key != "capsule_root"}
        require(item["schema"] == "ucl.ucm.incident_capsule.v1" and item["capsule_root"] == root(body) == require_root(expected_pin), "INCIDENT_CAPSULE_PIN_MISMATCH")
        require(item["subject_root"] == self.subject_root, "INCIDENT_CAPSULE_SUBJECT_MISMATCH")
        require(type(item["events"]) is list and type(item["sequence"]) is int and type(item["sequence"]) is not bool, "INCIDENT_CAPSULE_INVALID")
        expected_head = root({"subject_root": self.subject_root, "incident_genesis": True})
        current: dict[str, dict[str, Any]] = {}
        for sequence, event in enumerate(item["events"], 1):
            required = {"schema", "incident_id", "subject_root", "severity", "status", "prior_event_root", "affected_roots", "evidence_roots", "summary_root", "required_actions", "effect_observed", "standing", "authority_effect", "idempotency_key", "sequence", "previous_head", "event_root"}
            exact_keys(event, required, f"$.incident_capsule.events[{sequence - 1}]")
            event_body = {key: event[key] for key in event if key != "event_root"}
            require(event["sequence"] == sequence and event["previous_head"] == expected_head and event["event_root"] == root(event_body), "INCIDENT_CHAIN_INVALID")
            require(event["subject_root"] == self.subject_root and event["severity"] in SEVERITIES and event["status"] in TRANSITIONS, "INCIDENT_EVENT_INVALID")
            prior = current.get(event["incident_id"])
            if prior is None:
                require(event["status"] == "OPEN" and event["prior_event_root"] is None, "INCIDENT_CHAIN_INVALID")
            else:
                require(event["prior_event_root"] == prior["event_root"] and event["status"] in TRANSITIONS[prior["status"]], "INCIDENT_CHAIN_INVALID")
            current[event["incident_id"]] = deepcopy(event)
            expected_head = event["event_root"]
        require(item["sequence"] == len(item["events"]) and item["head"] == expected_head, "INCIDENT_CAPSULE_HEAD_MISMATCH")
        require(type(item["idempotency"]) is dict, "INCIDENT_IDEMPOTENCY_INVALID")
        rebuilt_idempotency: dict[str, tuple[str, str]] = {}
        for event in item["events"]:
            key = event["idempotency_key"]
            require(type(key) is str and 8 <= len(key) <= 128 and key not in rebuilt_idempotency, "INCIDENT_IDEMPOTENCY_INVALID")
            request_body = {field: event[field] for field in event if field not in {"idempotency_key", "sequence", "previous_head", "event_root"}}
            rebuilt_idempotency[key] = (root(request_body), event["event_root"])
        expected_idempotency = {key: list(value) for key, value in sorted(rebuilt_idempotency.items())}
        require(item["idempotency"] == expected_idempotency, "INCIDENT_IDEMPOTENCY_INVALID")
        self._events, self._current = deepcopy(item["events"]), current
        self._sequence, self._head, self._idempotency = item["sequence"], item["head"], rebuilt_idempotency

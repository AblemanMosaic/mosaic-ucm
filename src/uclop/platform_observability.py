from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import exact_keys, require, require_root, root


KINDS = {"HEALTH", "COURT", "DEPLOYMENT", "FEDERATION", "INCIDENT", "REQUALIFICATION"}
STATUSES = {"PASS", "DEGRADED", "REFUSED", "FAIL", "UNKNOWN"}


class ObservationLedger:
    """Append-only, restart-safe observations with an INFORMATION_ONLY ceiling."""

    def __init__(self, *, subject_root: str, initial_capsule: dict[str, Any] | None = None, expected_pin: str | None = None) -> None:
        self.subject_root = require_root(subject_root)
        self._rows: list[dict[str, Any]] = []
        self._keys: dict[str, tuple[str, str]] = {}
        self._head = root({"subject_root": self.subject_root, "genesis": True})
        if initial_capsule is not None:
            self._restore(initial_capsule, expected_pin=expected_pin)
        else:
            require(expected_pin is None, "OBSERVATION_CAPSULE_REQUIRED")

    def append(self, *, observation_id: str, kind: str, status: str, observed_subject_root: str, evidence_roots: list[str], detail_root: str, idempotency_key: str) -> dict[str, Any]:
        require(type(observation_id) is str and observation_id and kind in KINDS and status in STATUSES, "OBSERVATION_INPUT_INVALID")
        require(type(idempotency_key) is str and 8 <= len(idempotency_key) <= 128, "IDEMPOTENCY_KEY_INVALID")
        require(type(evidence_roots) is list and evidence_roots == sorted(evidence_roots) and evidence_roots, "OBSERVATION_EVIDENCE_INVALID")
        for value in evidence_roots: require_root(value)
        body = {
            "schema": "ucl.ucm.platform_observation.v1", "observation_id": observation_id,
            "kind": kind, "status": status, "subject_root": require_root(observed_subject_root),
            "evidence_roots": list(evidence_roots), "detail_root": require_root(detail_root),
            "idempotency_key": idempotency_key, "sequence": len(self._rows) + 1,
            "previous_head": self._head, "effect_observed": "NONE",
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        }
        request_root = root({key: value for key, value in body.items() if key not in {"sequence", "previous_head"}})
        prior = self._keys.get(idempotency_key)
        if prior is not None:
            require(prior[0] == request_root, "IDEMPOTENCY_CONFLICT")
            return deepcopy(next(row for row in self._rows if row["observation_root"] == prior[1]))
        row = {**body, "observation_root": root(body)}
        self._rows.append(row); self._head = row["observation_root"]; self._keys[idempotency_key] = (request_root, self._head)
        return deepcopy(row)

    def health(self) -> dict[str, Any]:
        active = [row for row in self._rows if row["status"] in {"DEGRADED", "FAIL", "UNKNOWN"}]
        body = {
            "schema": "ucl.ucm.platform_health_projection.v1", "subject_root": self.subject_root,
            "observation_head": self._head, "observation_count": len(self._rows),
            "active_problem_roots": [row["observation_root"] for row in active],
            "status": "PASS" if not active else "ATTENTION_REQUIRED",
            "effect_observed": "NONE", "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        }
        return {**body, "health_root": root(body)}

    def export_capsule(self) -> dict[str, Any]:
        body = {
            "schema": "ucl.ucm.platform_observation_capsule.v1", "subject_root": self.subject_root,
            "rows": deepcopy(self._rows), "sequence": len(self._rows), "head": self._head,
            "idempotency": {key: list(value) for key, value in sorted(self._keys.items())},
            "effect_observed": "NONE", "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        }
        return {**body, "capsule_root": root(body)}

    def _restore(self, capsule: Any, *, expected_pin: str | None) -> None:
        require(expected_pin is not None, "OBSERVATION_CAPSULE_PIN_REQUIRED")
        item = exact_keys(capsule, {"schema", "subject_root", "rows", "sequence", "head", "idempotency", "effect_observed", "standing", "authority_effect", "capsule_root"}, "$.observation_capsule")
        body = {key: item[key] for key in item if key != "capsule_root"}
        require(item["schema"] == "ucl.ucm.platform_observation_capsule.v1" and item["capsule_root"] == root(body) == require_root(expected_pin), "OBSERVATION_CAPSULE_PIN_MISMATCH")
        require(item["subject_root"] == self.subject_root and item["effect_observed"] == "NONE" and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "OBSERVATION_CAPSULE_CONTEXT_INVALID")
        require(type(item["rows"]) is list and type(item["sequence"]) is int and type(item["sequence"]) is not bool and item["sequence"] == len(item["rows"]), "OBSERVATION_CHAIN_INVALID")
        head = root({"subject_root": self.subject_root, "genesis": True}); keys: dict[str, tuple[str, str]] = {}
        for sequence, row in enumerate(item["rows"], 1):
            checked = exact_keys(row, {"schema", "observation_id", "kind", "status", "subject_root", "evidence_roots", "detail_root", "idempotency_key", "sequence", "previous_head", "effect_observed", "standing", "authority_effect", "observation_root"}, f"$.rows[{sequence - 1}]")
            row_body = {key: checked[key] for key in checked if key != "observation_root"}
            require(checked["sequence"] == sequence and checked["previous_head"] == head and checked["observation_root"] == root(row_body), "OBSERVATION_CHAIN_INVALID")
            require(checked["subject_root"] == self.subject_root and checked["kind"] in KINDS and checked["status"] in STATUSES and checked["effect_observed"] == "NONE" and checked["standing"] == "INFORMATION_ONLY" and checked["authority_effect"] == "NONE", "OBSERVATION_ROW_INVALID")
            for value in checked["evidence_roots"]: require_root(value)
            request_root = root({key: value for key, value in row_body.items() if key not in {"sequence", "previous_head"}})
            require(checked["idempotency_key"] not in keys, "OBSERVATION_IDEMPOTENCY_INVALID")
            keys[checked["idempotency_key"]] = (request_root, checked["observation_root"]); head = checked["observation_root"]
        require(item["head"] == head and item["idempotency"] == {key: list(value) for key, value in sorted(keys.items())}, "OBSERVATION_MATERIALIZED_STATE_INVALID")
        self._rows, self._head, self._keys = deepcopy(item["rows"]), head, keys


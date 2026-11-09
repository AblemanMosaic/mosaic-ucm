from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import exact_keys, require, require_root, root
from .ecosystem import STAGES, stage_rank


OBSERVATION_KINDS = {"HEALTH", "AUDIT", "PERFORMANCE", "SECURITY", "CUSTODY", "POLICY"}
INCIDENT_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
DEPLOYMENT_STATUSES = {"PLANNED", "PREFLIGHT_PASS", "REHEARSED", "REVIEW_READY", "BLOCKED", "ROLLED_BACK"}


def _record_root(record: dict[str, Any], field: str) -> str:
    body = {key: value for key, value in record.items() if key != field}
    require(record.get(field) == root(body), "RECORD_ROOT_INVALID", detail=field)
    return record[field]


class FoundationRuntime:
    """Pure, restartable D2 operations kernel.

    It stores no external resources and cannot cross the D2 ceiling. State
    capsules bind every append-only record and every idempotency decision.
    """

    def __init__(self, *, subject_root: str, policy_root: str, initial_capsule: dict[str, Any] | None = None, expected_pin: str | None = None) -> None:
        self.subject_root = require_root(subject_root)
        self.policy_root = require_root(policy_root)
        self._observations: list[dict[str, Any]] = []
        self._incidents: list[dict[str, Any]] = []
        self._deployments: dict[str, dict[str, Any]] = {}
        self._idempotency: dict[str, str] = {}
        self._sequence = 0
        self._head = root({"subject_root": self.subject_root, "policy_root": self.policy_root, "genesis": True})
        if initial_capsule is not None:
            require(expected_pin is not None, "RUNTIME_EXPECTED_PIN_REQUIRED")
            self.restore(initial_capsule, expected_pin=expected_pin)
        else:
            require(expected_pin is None, "RUNTIME_CAPSULE_REQUIRED")

    def _append(self, collection: list[dict[str, Any]], body: dict[str, Any], root_field: str) -> dict[str, Any]:
        self._sequence += 1
        bound = {**body, "sequence": self._sequence, "previous_head": self._head}
        record = {**bound, root_field: root(bound)}
        self._head = record[root_field]
        collection.append(record)
        return deepcopy(record)

    def append_observation(self, *, kind: str, subject_root: str, evidence_roots: list[str], status: str, details: dict[str, Any]) -> dict[str, Any]:
        require(kind in OBSERVATION_KINDS, "OBSERVATION_KIND_INVALID")
        require(type(evidence_roots) is list and evidence_roots == sorted(evidence_roots) and len(evidence_roots) == len(set(evidence_roots)), "OBSERVATION_EVIDENCE_SET_INVALID")
        for value in evidence_roots:
            require_root(value)
        require(status in {"PASS", "FAIL", "DEGRADED", "INFORMATION_ONLY"}, "OBSERVATION_STATUS_INVALID")
        require(type(details) is dict, "OBSERVATION_DETAILS_INVALID")
        return self._append(self._observations, {
            "schema": "ucl.ucm.foundation_observation.v1", "kind": kind,
            "subject_root": require_root(subject_root), "evidence_roots": evidence_roots,
            "status": status, "details": deepcopy(details), "effect_observed": "NONE",
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        }, "observation_root")

    def open_incident(self, *, incident_id: str, severity: str, subject_root: str, evidence_roots: list[str], summary: str) -> dict[str, Any]:
        require(type(incident_id) is str and 6 <= len(incident_id) <= 96, "INCIDENT_ID_INVALID")
        require(all(item["incident_id"] != incident_id for item in self._incidents), "INCIDENT_ID_DUPLICATE")
        require(severity in INCIDENT_SEVERITIES, "INCIDENT_SEVERITY_INVALID")
        require(type(summary) is str and 1 <= len(summary) <= 2048, "INCIDENT_SUMMARY_INVALID")
        require(type(evidence_roots) is list and evidence_roots == sorted(evidence_roots) and evidence_roots, "INCIDENT_EVIDENCE_INVALID")
        for value in evidence_roots:
            require_root(value)
        return self._append(self._incidents, {
            "schema": "ucl.ucm.foundation_incident.v1", "incident_id": incident_id,
            "severity": severity, "subject_root": require_root(subject_root),
            "evidence_roots": evidence_roots, "summary": summary, "status": "OPEN",
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        }, "incident_root")

    def close_incident(self, *, incident_id: str, resolution_root: str) -> dict[str, Any]:
        matches = [item for item in self._incidents if item["incident_id"] == incident_id]
        require(matches and matches[-1]["status"] == "OPEN", "INCIDENT_NOT_OPEN")
        return self._append(self._incidents, {
            "schema": "ucl.ucm.foundation_incident.v1", "incident_id": incident_id,
            "severity": matches[-1]["severity"], "subject_root": matches[-1]["subject_root"],
            "evidence_roots": [matches[-1]["incident_root"], require_root(resolution_root)],
            "summary": "resolved by bound evidence", "status": "CLOSED",
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        }, "incident_root")

    def plan_deployment(
        self, *, deployment_id: str, application_root: str, artifact_root: str,
        target_profile_root: str, rollback_root: str, requested_stage: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        require(type(deployment_id) is str and 6 <= len(deployment_id) <= 96, "DEPLOYMENT_ID_INVALID")
        require(type(idempotency_key) is str and 8 <= len(idempotency_key) <= 128, "IDEMPOTENCY_KEY_INVALID")
        require(requested_stage in STAGES and stage_rank(requested_stage) >= stage_rank("D3_REAL_IDENTITY_SEATING"), "DEPLOYMENT_STAGE_INVALID")
        body = {
            "schema": "ucl.ucm.deployment_plan.v1", "deployment_id": deployment_id,
            "application_root": require_root(application_root), "artifact_root": require_root(artifact_root),
            "target_profile_root": require_root(target_profile_root), "rollback_root": require_root(rollback_root),
            "requested_stage": requested_stage, "status": "PLANNED", "executable": False,
            "required_external_receipts": ["ENTRY_DECISION", "IDENTITY_SEATING", "PROTECTED_EXECUTION", "ACCEPTANCE"],
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        }
        plan = {**body, "deployment_root": root(body)}
        prior_root = self._idempotency.get(idempotency_key)
        if prior_root is not None:
            require(prior_root == plan["deployment_root"], "IDEMPOTENCY_CONFLICT")
            return deepcopy(self._deployments[deployment_id])
        require(deployment_id not in self._deployments, "DEPLOYMENT_ID_DUPLICATE")
        self._idempotency[idempotency_key] = plan["deployment_root"]
        self._deployments[deployment_id] = plan
        return deepcopy(plan)

    def preflight_deployment(self, *, deployment_id: str, checks: list[dict[str, Any]]) -> dict[str, Any]:
        require(deployment_id in self._deployments, "DEPLOYMENT_UNKNOWN")
        prior = self._deployments[deployment_id]
        require(prior["status"] == "PLANNED", "DEPLOYMENT_TRANSITION_INVALID")
        require(type(checks) is list and checks and all(type(item) is dict and set(item) == {"check_id", "status", "evidence_root"} for item in checks), "DEPLOYMENT_CHECK_SET_INVALID")
        require([item["check_id"] for item in checks] == sorted(item["check_id"] for item in checks) and len({item["check_id"] for item in checks}) == len(checks), "DEPLOYMENT_CHECK_SET_INVALID")
        for item in checks:
            require(item["status"] == "PASS", "DEPLOYMENT_PREFLIGHT_FAILED", detail=item["check_id"])
            require_root(item["evidence_root"])
        body = {**{key: value for key, value in prior.items() if key not in {"deployment_root", "status"}}, "status": "PREFLIGHT_PASS", "preflight_root": root(checks)}
        updated = {**body, "deployment_root": root(body)}
        self._deployments[deployment_id] = updated
        return deepcopy(updated)

    def rehearse_deployment(self, *, deployment_id: str, rehearsal_root: str, rollback_rehearsal_root: str) -> dict[str, Any]:
        require(deployment_id in self._deployments, "DEPLOYMENT_UNKNOWN")
        prior = self._deployments[deployment_id]
        require(prior["status"] == "PREFLIGHT_PASS", "DEPLOYMENT_TRANSITION_INVALID")
        body = {**{key: value for key, value in prior.items() if key not in {"deployment_root", "status"}}, "status": "REHEARSED", "rehearsal_root": require_root(rehearsal_root), "rollback_rehearsal_root": require_root(rollback_rehearsal_root)}
        updated = {**body, "deployment_root": root(body)}
        self._deployments[deployment_id] = updated
        return deepcopy(updated)

    def readiness(self, deployment_id: str) -> dict[str, Any]:
        require(deployment_id in self._deployments, "DEPLOYMENT_UNKNOWN")
        plan = self._deployments[deployment_id]
        open_high = [item["incident_root"] for item in self._incidents if item["status"] == "OPEN" and item["severity"] in {"HIGH", "CRITICAL"}]
        missing = list(plan["required_external_receipts"])
        ready_for_external_review = plan["status"] == "REHEARSED" and not open_high
        body = {
            "schema": "ucl.ucm.deployment_readiness.v1", "deployment_root": plan["deployment_root"],
            "requested_stage": plan["requested_stage"], "ready_for_external_review": ready_for_external_review,
            "ready_for_execution": False, "open_blocking_incident_roots": open_high,
            "missing_external_receipts": missing, "maximum_current_stage": "D2_INDEPENDENT_REVIEW",
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        }
        return {**body, "readiness_root": root(body)}

    def export_capsule(self) -> dict[str, Any]:
        body = {
            "schema": "ucl.ucm.foundation_runtime_capsule.v1", "subject_root": self.subject_root,
            "policy_root": self.policy_root, "sequence": self._sequence, "head": self._head,
            "observations": deepcopy(self._observations), "incidents": deepcopy(self._incidents),
            "deployments": [deepcopy(self._deployments[key]) for key in sorted(self._deployments)],
            "idempotency": dict(sorted(self._idempotency.items())), "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        return {**body, "capsule_root": root(body)}

    def restore(self, capsule: Any, *, expected_pin: str) -> None:
        item = exact_keys(capsule, {"schema", "subject_root", "policy_root", "sequence", "head", "observations", "incidents", "deployments", "idempotency", "standing", "authority_effect", "capsule_root"}, "$.capsule")
        body = {key: item[key] for key in item if key != "capsule_root"}
        require(item["schema"] == "ucl.ucm.foundation_runtime_capsule.v1" and item["capsule_root"] == root(body) == require_root(expected_pin), "RUNTIME_CAPSULE_PIN_MISMATCH")
        require(item["subject_root"] == self.subject_root and item["policy_root"] == self.policy_root, "RUNTIME_CAPSULE_CONTEXT_MISMATCH")
        require(type(item["sequence"]) is int and type(item["sequence"]) is not bool and item["sequence"] >= 0, "RUNTIME_SEQUENCE_INVALID")
        require(item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "RUNTIME_CAPSULE_AUTHORITY_INVALID")
        require(type(item["observations"]) is list and type(item["incidents"]) is list, "RUNTIME_RECORD_SET_INVALID")
        ordered_records = (
            [(record, "observation_root") for record in item["observations"]]
            + [(record, "incident_root") for record in item["incidents"]]
        )
        require(all(type(record) is dict and type(record.get("sequence")) is int and type(record.get("sequence")) is not bool for record, _ in ordered_records), "RUNTIME_RECORD_CHAIN_INVALID")
        ordered_records.sort(key=lambda pair: pair[0]["sequence"])
        expected_sequence = 0
        expected_head = root({"subject_root": self.subject_root, "policy_root": self.policy_root, "genesis": True})
        for record, field in ordered_records:
            expected_sequence += 1
            require(record.get("sequence") == expected_sequence and record.get("previous_head") == expected_head, "RUNTIME_RECORD_CHAIN_INVALID")
            expected_head = _record_root(record, field)
        require(item["sequence"] == expected_sequence and item["head"] == expected_head, "RUNTIME_HEAD_MISMATCH")
        require(type(item["deployments"]) is list and type(item["idempotency"]) is dict, "RUNTIME_STATE_INVALID")
        deployments: dict[str, dict[str, Any]] = {}
        for deployment in item["deployments"]:
            require(type(deployment) is dict and deployment.get("status") in DEPLOYMENT_STATUSES, "DEPLOYMENT_STATE_INVALID")
            _record_root(deployment, "deployment_root")
            require(deployment["deployment_id"] not in deployments, "DEPLOYMENT_ID_DUPLICATE")
            deployments[deployment["deployment_id"]] = deepcopy(deployment)
        require(all(type(key) is str and type(value) is str for key, value in item["idempotency"].items()), "IDEMPOTENCY_STATE_INVALID")
        self._sequence, self._head = item["sequence"], item["head"]
        self._observations, self._incidents = deepcopy(item["observations"]), deepcopy(item["incidents"])
        self._deployments, self._idempotency = deployments, deepcopy(item["idempotency"])


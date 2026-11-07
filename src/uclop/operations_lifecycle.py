from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import exact_keys, require, require_root, root
from .custody import CustodyProvider, verify_asymmetric
from .identity_boundary import verify_operational_identity_binding


LIFECYCLE_DOMAIN = "UCL_UCM_PROTECTED_OPERATIONS_LIFECYCLE_V2"
ACCEPTANCE_DOMAIN = "UCL_UCM_PROTECTED_OPERATIONS_ACCEPTANCE_V2"
INCIDENT_DOMAIN = "UCL_UCM_PROTECTED_OPERATIONS_INCIDENT_V2"
IDENTITY_STATUS_DOMAIN = "UCL_UCM_OPERATIONAL_IDENTITY_STATUS_V1"

STAGE_ORDER = {
    "S0_NATIVE_REPLAY": 0,
    "S1_PROTECTED_SHADOW_INSTALLATION": 1,
    "S2_INFORMATION_ONLY_FEDERATION": 2,
}
STAGE_ENTRY_CRITERIA = {
    "S0_NATIVE_REPLAY": ("CACHE_FREE_COURT_PLAN", "IDENTITY_BINDING", "PINNED_PREDECESSOR", "PINNED_SOURCE"),
    "S1_PROTECTED_SHADOW_INSTALLATION": ("CONTENT_COMPLETE_BACKUP", "ROLLBACK_PLAN", "S0_ACCEPTANCE"),
    "S2_INFORMATION_ONLY_FEDERATION": ("RETIREMENT_AWARE_PEER", "S1_ACCEPTANCE", "SIGNED_REGISTRY_LINEAGE"),
}
STAGE_ACCEPTANCE_CHECKS = {
    "S0_NATIVE_REPLAY": ("ALL_SELECTED_COURTS_PASS", "TYPED_ATTACK_REFUSALS", "ZERO_REQUIRED_SKIPS"),
    "S1_PROTECTED_SHADOW_INSTALLATION": ("ANCHOR_ADVANCED_ONCE", "DISPOSABLE_RESTORE_SUCCEEDED", "INCIDENT_CONTAINMENT_RECORDED"),
    "S2_INFORMATION_ONLY_FEDERATION": ("IDENTITY_RETIREMENT_ENFORCED", "NODE_CONSTRUCTION_VERIFIED", "REPLAY_AND_ROLLBACK_REFUSED"),
}
MAX_IDENTITY_STATUS_EVENT_WINDOW = 4096
STAGE_CONTRACT_BODY = {
    "schema": "ucl.ucm.protected_operations_stage_contract.v2",
    "maximum_stage": "S2_INFORMATION_ONLY_FEDERATION",
    "stage_order": list(STAGE_ORDER),
    "entry_criteria": {key: list(value) for key, value in STAGE_ENTRY_CRITERIA.items()},
    "acceptance_checks": {key: list(value) for key, value in STAGE_ACCEPTANCE_CHECKS.items()},
    "acceptance_signer_roles": ["REVIEWER", "WITNESS"],
    "progress_requires_prior_acceptance": True,
    "open_incidents_block_progress": True,
    "rollback_plan_required": True,
    "maximum_identity_status_event_window": MAX_IDENTITY_STATUS_EVENT_WINDOW,
    "standing": "INFORMATION_ONLY",
    "authority_effect": "NONE",
}
PINNED_STAGE_CONTRACT_ROOT = root(STAGE_CONTRACT_BODY)

TRANSITIONS = {
    ("INITIAL", "PLAN"): "PLANNED",
    ("PLANNED", "STAGE"): "STAGED",
    ("STAGED", "ACTIVATE_SHADOW"): "SHADOW_ACTIVE",
    ("SHADOW_ACTIVE", "ENTER_FEDERATION"): "FEDERATION_ACTIVE",
    ("PLANNED", "SUSPEND"): "SUSPENDED",
    ("STAGED", "SUSPEND"): "SUSPENDED",
    ("SHADOW_ACTIVE", "SUSPEND"): "SUSPENDED",
    ("FEDERATION_ACTIVE", "SUSPEND"): "SUSPENDED",
    ("SUSPENDED", "BEGIN_RECOVERY"): "RECOVERY_PENDING",
    ("RECOVERY_PENDING", "COMPLETE_RECOVERY"): "SHADOW_ACTIVE",
    **{(state, "ROLLBACK"): "ROLLED_BACK" for state in ("PLANNED", "STAGED", "SHADOW_ACTIVE", "FEDERATION_ACTIVE", "SUSPENDED", "RECOVERY_PENDING")},
    **{(state, "REVOKE"): "REVOKED" for state in ("INITIAL", "PLANNED", "STAGED", "SHADOW_ACTIVE", "FEDERATION_ACTIVE", "SUSPENDED", "RECOVERY_PENDING", "ROLLED_BACK")},
}
ACTION_STAGE = {
    "PLAN": "S0_NATIVE_REPLAY",
    "STAGE": "S0_NATIVE_REPLAY",
    "ACTIVATE_SHADOW": "S1_PROTECTED_SHADOW_INSTALLATION",
    "ENTER_FEDERATION": "S2_INFORMATION_ONLY_FEDERATION",
}
PROGRESS_ACTIONS = set(ACTION_STAGE)


def _signed(value: dict[str, Any]) -> dict[str, Any]:
    return {key: value[key] for key in ("body", "body_root", "signature", "key_root", "signature_algorithm")}


def stage_contract() -> dict[str, Any]:
    return {**deepcopy(STAGE_CONTRACT_BODY), "contract_root": PINNED_STAGE_CONTRACT_ROOT}


def make_identity_status(
    provider: CustodyProvider,
    witness_handle: str,
    *,
    identity_binding_root: str,
    allowed_stages: list[str],
    sequence: int,
    predecessor_status_root: str,
    valid_through_event_sequence: int,
) -> dict[str, Any]:
    identity = provider.identity(witness_handle)
    require(identity["role"] == "REVIEWER", "IDENTITY_STATUS_SIGNER_ROLE_INVALID")
    require(type(sequence) is int and type(sequence) is not bool and sequence > 0, "IDENTITY_STATUS_SEQUENCE_INVALID")
    require((sequence == 1 and predecessor_status_root == "GENESIS") or (sequence > 1 and require_root(predecessor_status_root)), "IDENTITY_STATUS_PREDECESSOR_INVALID")
    require(type(valid_through_event_sequence) is int and type(valid_through_event_sequence) is not bool and valid_through_event_sequence >= sequence and valid_through_event_sequence - sequence <= MAX_IDENTITY_STATUS_EVENT_WINDOW, "IDENTITY_STATUS_VALIDITY_INVALID")
    require(type(allowed_stages) is list and allowed_stages == sorted(set(allowed_stages)) and set(allowed_stages).issubset(STAGE_ORDER), "IDENTITY_STATUS_STAGE_SET_INVALID")
    body = {
        "schema": "ucl.ucm.operational_identity_status.v1",
        "identity_binding_root": require_root(identity_binding_root),
        "sequence": sequence,
        "predecessor_status_root": predecessor_status_root,
        "status": "CURRENT",
        "allowed_stages": allowed_stages,
        "valid_through_event_sequence": valid_through_event_sequence,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    signed = provider.sign(witness_handle, IDENTITY_STATUS_DOMAIN, body)
    return {**signed, "identity_status_root": root(signed)}


def verify_identity_status(value: Any, *, expected_status_root: str, expected_binding_root: str, expected_witness_identity: dict[str, Any]) -> dict[str, Any]:
    item = exact_keys(value, {"body", "body_root", "signature", "key_root", "signature_algorithm", "identity_status_root"}, "$.identity_status")
    signed = _signed(item)
    body = verify_asymmetric(signed, IDENTITY_STATUS_DOMAIN, expected_key_root=expected_witness_identity["key_root"], public_key_hex=expected_witness_identity["public_key_hex"])
    exact_keys(body, {"schema", "identity_binding_root", "sequence", "predecessor_status_root", "status", "allowed_stages", "valid_through_event_sequence", "standing", "authority_effect"}, "$.identity_status.body")
    require(item["identity_status_root"] == root(signed) == require_root(expected_status_root), "IDENTITY_STATUS_ROOT_MISMATCH")
    require(body["schema"] == "ucl.ucm.operational_identity_status.v1" and body["identity_binding_root"] == require_root(expected_binding_root), "IDENTITY_STATUS_BINDING_MISMATCH")
    require(type(body["sequence"]) is int and type(body["sequence"]) is not bool and body["sequence"] > 0, "IDENTITY_STATUS_SEQUENCE_INVALID")
    require((body["sequence"] == 1 and body["predecessor_status_root"] == "GENESIS") or (body["sequence"] > 1 and require_root(body["predecessor_status_root"])), "IDENTITY_STATUS_PREDECESSOR_INVALID")
    require(body["status"] == "CURRENT", "IDENTITY_BINDING_NOT_CURRENT")
    require(type(body["allowed_stages"]) is list and body["allowed_stages"] == sorted(set(body["allowed_stages"])) and set(body["allowed_stages"]).issubset(STAGE_ORDER), "IDENTITY_STATUS_STAGE_SET_INVALID")
    require(type(body["valid_through_event_sequence"]) is int and type(body["valid_through_event_sequence"]) is not bool and body["valid_through_event_sequence"] >= body["sequence"] and body["valid_through_event_sequence"] - body["sequence"] <= MAX_IDENTITY_STATUS_EVENT_WINDOW, "IDENTITY_STATUS_VALIDITY_INVALID")
    require(body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE", "IDENTITY_STATUS_EFFECT_FORBIDDEN")
    return deepcopy(body)


class ProtectedOperationsLifecycle:
    """Contract-enforcing fixture lifecycle retained for predecessor compatibility."""

    def __init__(
        self,
        provider: CustodyProvider,
        transition_handle: str,
        *,
        acceptance_handle: str,
        identity_status_handle: str,
        identity_binding: dict[str, Any],
        expected_provider_root: str,
        expected_principal_id: str,
        expected_role_address: str,
        expected_host_root: str,
        expected_identity_nonce: str,
        expected_allowed_stages: list[str],
        expected_allowed_effects: list[str],
        identity_status: dict[str, Any],
        expected_identity_status_root: str,
        deployment_contract_root: str = PINNED_STAGE_CONTRACT_ROOT,
        maximum_stage: str = "S2_INFORMATION_ONLY_FEDERATION",
    ) -> None:
        require(deployment_contract_root == PINNED_STAGE_CONTRACT_ROOT, "OPERATIONS_STAGE_CONTRACT_NOT_PINNED")
        require(maximum_stage == "S2_INFORMATION_ONLY_FEDERATION", "OPERATIONS_STAGE_CEILING_INVALID")
        self.provider = provider
        self.transition_handle = transition_handle
        self.acceptance_handle = acceptance_handle
        self.identity_status_handle = identity_status_handle
        self.identity = provider.identity(transition_handle)
        self.acceptance_identity = provider.identity(acceptance_handle)
        self.identity_status_identity = provider.identity(identity_status_handle)
        require(self.identity["role"] == "GOVERNOR", "OPERATIONS_GOVERNOR_ROLE_REQUIRED")
        require(self.acceptance_identity["role"] in {"REVIEWER", "WITNESS"}, "OPERATIONS_ACCEPTANCE_ROLE_INVALID")
        require(self.identity_status_identity["role"] == "REVIEWER", "IDENTITY_STATUS_SIGNER_ROLE_INVALID")
        require(self.identity["key_root"] != self.acceptance_identity["key_root"], "OPERATIONS_ACCEPTANCE_NOT_INDEPENDENT")
        require(len({self.identity["key_root"], self.acceptance_identity["key_root"], self.identity_status_identity["key_root"]}) == 3, "OPERATIONS_IDENTITY_STATUS_NOT_INDEPENDENT")
        binding_body = verify_operational_identity_binding(
            identity_binding,
            expected_provider_root=expected_provider_root,
            expected_key_root=self.identity["key_root"],
            expected_principal_id=expected_principal_id,
            expected_role_address=expected_role_address,
            expected_host_root=expected_host_root,
            expected_nonce=expected_identity_nonce,
            expected_allowed_stages=expected_allowed_stages,
            expected_allowed_effects=expected_allowed_effects,
        )
        require(binding_body["role"] == "GOVERNOR", "OPERATIONS_BINDING_ROLE_INVALID")
        require(set(binding_body["allowed_stages"]).issubset(STAGE_ORDER), "OPERATIONS_BINDING_STAGE_INVALID")
        self.identity_binding = deepcopy(identity_binding)
        self.identity_binding_root = identity_binding["binding_root"]
        self.identity_status = deepcopy(identity_status)
        self.identity_status_root = require_root(expected_identity_status_root)
        self.identity_status_body = verify_identity_status(identity_status, expected_status_root=self.identity_status_root, expected_binding_root=self.identity_binding_root, expected_witness_identity=self.identity_status_identity)
        require(set(self.identity_status_body["allowed_stages"]).issubset(set(binding_body["allowed_stages"])), "IDENTITY_STATUS_STAGE_ESCALATION")
        self.deployment_contract_root = deployment_contract_root
        self.maximum_stage = maximum_stage
        self.state = "INITIAL"
        self.stage = "S0_NATIVE_REPLAY"
        self.events: list[dict[str, Any]] = []
        self.acceptance: dict[str, dict[str, Any]] = {}
        self.incidents: list[dict[str, Any]] = []

    def _open_incidents(self) -> list[dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        for record in self.incidents:
            latest[record["body"]["incident_id"]] = record
        return [record for record in latest.values() if record["body"]["status"] == "OPEN"]

    def _expected_stage(self, action: str, requested_stage: str) -> str:
        require(requested_stage in STAGE_ORDER, "OPERATIONS_STAGE_UNKNOWN")
        if action in ACTION_STAGE:
            require(requested_stage == ACTION_STAGE[action], "OPERATIONS_ACTION_STAGE_MISMATCH")
        else:
            require(requested_stage == self.stage, "OPERATIONS_STAGE_REVERSAL")
        return requested_stage

    @staticmethod
    def _criteria(action: str, stage: str, *, current_event_accepted: bool = True) -> tuple[str, ...]:
        if action == "PLAN": return STAGE_ENTRY_CRITERIA[stage]
        if action == "STAGE": return ("PREDECESSOR_ACCEPTANCE", "ROLLBACK_PLAN", "STAGING_PLAN")
        if action in {"ACTIVATE_SHADOW", "ENTER_FEDERATION"}: return STAGE_ENTRY_CRITERIA[stage]
        if action == "SUSPEND": return (("CURRENT_ACCEPTANCE", "INCIDENT_OR_SUSPENSION_EVIDENCE") if current_event_accepted else ("CURRENT_EVENT", "INCIDENT_OR_SUSPENSION_EVIDENCE"))
        if action == "BEGIN_RECOVERY": return ("CONTAINMENT_RECEIPT", "CURRENT_ACCEPTANCE", "RECOVERY_PLAN")
        if action == "COMPLETE_RECOVERY": return ("RECOVERY_COURT", "RECOVERY_PLAN", "RESTORE_RECEIPT")
        if action == "ROLLBACK": return (("PRESERVED_EVIDENCE", "ROLLBACK_PLAN", "ROLLBACK_RECEIPT") if current_event_accepted else ("CURRENT_EVENT", "PRESERVED_EVIDENCE", "ROLLBACK_PLAN", "ROLLBACK_RECEIPT"))
        if action == "REVOKE": return ("PRESERVED_EVIDENCE", "REVOCATION_EVIDENCE", "ROLLBACK_PLAN")
        require(False, "OPERATIONS_ACTION_UNKNOWN")
        raise AssertionError

    def _verify_previous_acceptance(self) -> str:
        require(self.events, "OPERATIONS_PREDECESSOR_EVENT_REQUIRED")
        event_root = self.events[-1]["event_root"]
        require(event_root in self.acceptance, "OPERATIONS_PREDECESSOR_NOT_ACCEPTED")
        self.verify_acceptance_receipt(self.acceptance[event_root], expected_event_root=event_root)
        return self.acceptance[event_root]["acceptance_root"]

    def transition(self, action: str, *, stage: str, entry_evidence_roots: dict[str, str], rollback_plan_root: str, reason_code: str) -> dict[str, Any]:
        require((self.state, action) in TRANSITIONS, "OPERATIONS_TRANSITION_INVALID", detail=f"{self.state}:{action}")
        if action == "ACTIVATE_SHADOW":
            require(self.stage == "S0_NATIVE_REPLAY", "OPERATIONS_COMPATIBILITY_PATH_FORBIDDEN")
        if action == "ENTER_FEDERATION":
            require(self.stage == "S1_PROTECTED_SHADOW_INSTALLATION", "OPERATIONS_COMPATIBILITY_PATH_FORBIDDEN")
        stage = self._expected_stage(action, stage)
        require(STAGE_ORDER[stage] <= STAGE_ORDER[self.maximum_stage], "OPERATIONS_STAGE_ABOVE_CEILING")
        require(stage in self.identity_status_body["allowed_stages"], "OPERATIONS_STAGE_NOT_AUTHORIZED_BY_IDENTITY")
        next_sequence = len(self.events) + 1
        require(next_sequence <= self.identity_status_body["valid_through_event_sequence"], "IDENTITY_STATUS_EXPIRED")
        if action in PROGRESS_ACTIONS:
            require(not self._open_incidents(), "OPERATIONS_OPEN_INCIDENT_BLOCKS_PROGRESS")
        current_event_accepted = bool(self.events and self.events[-1]["event_root"] in self.acceptance)
        emergency_without_acceptance = action in {"SUSPEND", "ROLLBACK", "REVOKE"}
        previous_acceptance = self._verify_previous_acceptance() if self.events and action != "REVOKE" and not (emergency_without_acceptance and not current_event_accepted) else None
        criteria = self._criteria(action, stage, current_event_accepted=current_event_accepted)
        require(type(entry_evidence_roots) is dict and set(entry_evidence_roots) == set(criteria), "OPERATIONS_ENTRY_EVIDENCE_SET_INVALID")
        checked = {key: require_root(entry_evidence_roots[key], f"$.entry_evidence.{key}") for key in sorted(criteria)}
        rollback_plan_root = require_root(rollback_plan_root)
        if "ROLLBACK_PLAN" in checked: require(checked["ROLLBACK_PLAN"] == rollback_plan_root, "OPERATIONS_ROLLBACK_PLAN_MISMATCH")
        if previous_acceptance is not None and "PREDECESSOR_ACCEPTANCE" in checked: require(checked["PREDECESSOR_ACCEPTANCE"] == previous_acceptance, "OPERATIONS_PREDECESSOR_ACCEPTANCE_MISMATCH")
        if previous_acceptance is not None and "CURRENT_ACCEPTANCE" in checked: require(checked["CURRENT_ACCEPTANCE"] == previous_acceptance, "OPERATIONS_PREDECESSOR_ACCEPTANCE_MISMATCH")
        if "CURRENT_EVENT" in checked: require(self.events and checked["CURRENT_EVENT"] == self.events[-1]["event_root"], "OPERATIONS_CURRENT_EVENT_MISMATCH")
        if action == "ACTIVATE_SHADOW": require(checked["S0_ACCEPTANCE"] == previous_acceptance, "OPERATIONS_PREDECESSOR_ACCEPTANCE_MISMATCH")
        if action == "ENTER_FEDERATION": require(checked["S1_ACCEPTANCE"] == previous_acceptance, "OPERATIONS_PREDECESSOR_ACCEPTANCE_MISMATCH")
        require(type(reason_code) is str and bool(reason_code.strip()), "OPERATIONS_REASON_INVALID")
        predecessor = self.events[-1]["event_root"] if self.events else "GENESIS"
        next_state = TRANSITIONS[(self.state, action)]
        body = {
            "schema": "ucl.ucm.protected_operations_lifecycle_event.v2",
            "sequence": next_sequence,
            "predecessor_event_root": predecessor,
            "predecessor_acceptance_root": previous_acceptance,
            "stage_contract_root": self.deployment_contract_root,
            "identity_binding_root": self.identity_binding_root,
            "identity_status_root": self.identity_status_root,
            "stage": stage,
            "maximum_stage": self.maximum_stage,
            "action": action,
            "prior_state": self.state,
            "next_state": next_state,
            "entry_evidence_roots": checked,
            "rollback_plan_root": rollback_plan_root,
            "reason_code": reason_code,
            "real_a5": False,
            "g0": "CLOSED",
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        signed = self.provider.sign(self.transition_handle, LIFECYCLE_DOMAIN, body)
        event = {**signed, "event_root": root(signed)}
        self.events.append(event)
        self.state, self.stage = next_state, stage
        return deepcopy(event)

    def accept(self, event_root: str, *, checks: dict[str, str], terminal_evidence_root: str) -> dict[str, Any]:
        require(self.events and self.events[-1]["event_root"] == require_root(event_root), "OPERATIONS_ACCEPTANCE_EVENT_MISMATCH")
        require(event_root not in self.acceptance, "OPERATIONS_ACCEPTANCE_ALREADY_RECORDED")
        event = self.events[-1]["body"]
        expected = STAGE_ACCEPTANCE_CHECKS[event["stage"]]
        require(type(checks) is dict and set(checks) == set(expected), "OPERATIONS_ACCEPTANCE_CHECK_SET_INVALID")
        checked = {key: require_root(checks[key], f"$.acceptance.checks.{key}") for key in sorted(expected)}
        body = {
            "schema": "ucl.ucm.protected_operations_acceptance.v2",
            "event_root": event_root,
            "event_sequence": event["sequence"],
            "stage_contract_root": self.deployment_contract_root,
            "identity_binding_root": self.identity_binding_root,
            "identity_status_root": self.identity_status_root,
            "transition_key_root": self.identity["key_root"],
            "acceptance_key_root": self.acceptance_identity["key_root"],
            "stage": event["stage"],
            "state": event["next_state"],
            "checks": checked,
            "terminal_evidence_root": require_root(terminal_evidence_root),
            "automatic_promotion": False,
            "maximum_stage": self.maximum_stage,
            "real_a5": False,
            "g0": "CLOSED",
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        signed = self.provider.sign(self.acceptance_handle, ACCEPTANCE_DOMAIN, body)
        receipt = {**signed, "acceptance_root": root(signed)}
        self.acceptance[event_root] = receipt
        return deepcopy(receipt)

    def verify_acceptance_receipt(self, value: Any, *, expected_event_root: str) -> dict[str, Any]:
        item = exact_keys(value, {"body", "body_root", "signature", "key_root", "signature_algorithm", "acceptance_root"}, "$.acceptance")
        signed = _signed(item)
        body = verify_asymmetric(signed, ACCEPTANCE_DOMAIN, expected_key_root=self.acceptance_identity["key_root"], public_key_hex=self.acceptance_identity["public_key_hex"])
        exact_keys(body, {"schema", "event_root", "event_sequence", "stage_contract_root", "identity_binding_root", "identity_status_root", "transition_key_root", "acceptance_key_root", "stage", "state", "checks", "terminal_evidence_root", "automatic_promotion", "maximum_stage", "real_a5", "g0", "standing", "authority_effect"}, "$.acceptance.body")
        require(item["acceptance_root"] == root(signed), "OPERATIONS_ACCEPTANCE_ROOT_INVALID")
        require(body["event_root"] == require_root(expected_event_root), "OPERATIONS_ACCEPTANCE_EVENT_MISMATCH")
        matching = next((event["body"] for event in self.events if event["event_root"] == expected_event_root), None)
        require(matching is not None, "OPERATIONS_ACCEPTANCE_EVENT_UNKNOWN")
        require(body["event_sequence"] == matching["sequence"] and body["stage"] == matching["stage"] and body["state"] == matching["next_state"], "OPERATIONS_ACCEPTANCE_EVENT_BINDING_INVALID")
        require(body["stage_contract_root"] == self.deployment_contract_root and body["identity_binding_root"] == self.identity_binding_root and body["identity_status_root"] == self.identity_status_root, "OPERATIONS_ACCEPTANCE_CONTEXT_MISMATCH")
        require(body["transition_key_root"] == self.identity["key_root"] and body["acceptance_key_root"] == self.acceptance_identity["key_root"] and body["transition_key_root"] != body["acceptance_key_root"], "OPERATIONS_ACCEPTANCE_NOT_INDEPENDENT")
        expected = STAGE_ACCEPTANCE_CHECKS[body["stage"]]
        require(type(body["checks"]) is dict and set(body["checks"]) == set(expected) and all(require_root(value) for value in body["checks"].values()), "OPERATIONS_ACCEPTANCE_CHECK_SET_INVALID")
        require(body["automatic_promotion"] is False and body["maximum_stage"] == self.maximum_stage and body["real_a5"] is False and body["g0"] == "CLOSED" and body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE", "OPERATIONS_ACCEPTANCE_EFFECT_FORBIDDEN")
        require_root(body["terminal_evidence_root"])
        return deepcopy(body)

    def open_incident(self, *, code: str, severity: str, evidence_roots: list[str]) -> dict[str, Any]:
        require(type(code) is str and bool(code.strip()), "INCIDENT_CODE_INVALID")
        require(severity in {"LOW", "MED", "HIGH", "CRITICAL"}, "INCIDENT_SEVERITY_INVALID")
        require(type(evidence_roots) is list and evidence_roots and all(require_root(value) for value in evidence_roots), "INCIDENT_EVIDENCE_INVALID")
        sequence = len(self.incidents) + 1
        incident_id = root({"code": code, "sequence": sequence, "evidence_roots": sorted(evidence_roots)})
        body = {
            "schema": "ucl.ucm.protected_operations_incident.v2",
            "sequence": sequence,
            "predecessor_incident_root": self.incidents[-1]["incident_root"] if self.incidents else "GENESIS",
            "incident_id": incident_id,
            "code": code,
            "severity": severity,
            "status": "OPEN",
            "lifecycle_event_root": self.events[-1]["event_root"] if self.events else "GENESIS",
            "evidence_roots": sorted(evidence_roots),
            "resolution_root": None,
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        signed = self.provider.sign(self.transition_handle, INCIDENT_DOMAIN, body)
        record = {**signed, "incident_root": root(signed)}
        self.incidents.append(record)
        return deepcopy(record)

    def resolve_incident(self, incident_root: str, *, resolution_root: str) -> dict[str, Any]:
        incident_root = require_root(incident_root)
        prior_record = next((record for record in reversed(self.incidents) if record["incident_root"] == incident_root), None)
        require(prior_record is not None and prior_record["body"]["status"] == "OPEN", "INCIDENT_NOT_CURRENT")
        require(self.state in {"SUSPENDED", "ROLLED_BACK", "RECOVERY_PENDING", "REVOKED"}, "INCIDENT_CONTAINMENT_REQUIRED")
        prior = prior_record["body"]
        body = {
            **prior,
            "sequence": len(self.incidents) + 1,
            "predecessor_incident_root": self.incidents[-1]["incident_root"],
            "status": "RESOLVED",
            "resolution_root": require_root(resolution_root),
            "lifecycle_event_root": self.events[-1]["event_root"] if self.events else "GENESIS",
        }
        signed = self.provider.sign(self.transition_handle, INCIDENT_DOMAIN, body)
        record = {**signed, "incident_root": root(signed)}
        self.incidents.append(record)
        return deepcopy(record)

    def verify_history(self) -> dict[str, Any]:
        verify_identity_status(self.identity_status, expected_status_root=self.identity_status_root, expected_binding_root=self.identity_binding_root, expected_witness_identity=self.identity_status_identity)
        predecessor, prior_state, prior_stage = "GENESIS", "INITIAL", "S0_NATIVE_REPLAY"
        for sequence, event in enumerate(self.events, 1):
            signed = _signed(event)
            body = verify_asymmetric(signed, LIFECYCLE_DOMAIN, expected_key_root=self.identity["key_root"], public_key_hex=self.identity["public_key_hex"])
            require(event["event_root"] == root(signed), "OPERATIONS_EVENT_ROOT_INVALID")
            require(body["sequence"] == sequence and body["predecessor_event_root"] == predecessor, "OPERATIONS_EVENT_CHAIN_INVALID")
            require(body["prior_state"] == prior_state and TRANSITIONS.get((prior_state, body["action"])) == body["next_state"], "OPERATIONS_EVENT_TRANSITION_INVALID")
            require(body["stage_contract_root"] == self.deployment_contract_root and body["identity_binding_root"] == self.identity_binding_root and body["identity_status_root"] == self.identity_status_root, "OPERATIONS_EVENT_CONTEXT_MISMATCH")
            require(body["stage"] == ACTION_STAGE.get(body["action"], prior_stage) and body["stage"] in self.identity_status_body["allowed_stages"], "OPERATIONS_EVENT_STAGE_INVALID")
            predecessor_accepted = predecessor in self.acceptance
            expected_criteria = self._criteria(body["action"], body["stage"], current_event_accepted=predecessor_accepted)
            require(type(body["entry_evidence_roots"]) is dict and set(body["entry_evidence_roots"]) == set(expected_criteria) and all(require_root(value) for value in body["entry_evidence_roots"].values()), "OPERATIONS_ENTRY_EVIDENCE_SET_INVALID")
            emergency_without_acceptance = body["action"] in {"SUSPEND", "ROLLBACK", "REVOKE"} and not predecessor_accepted
            if sequence > 1 and body["action"] != "REVOKE" and not emergency_without_acceptance:
                receipt = self.acceptance.get(predecessor)
                require(receipt is not None and receipt["acceptance_root"] == body["predecessor_acceptance_root"], "OPERATIONS_PREDECESSOR_ACCEPTANCE_MISMATCH")
                self.verify_acceptance_receipt(receipt, expected_event_root=predecessor)
            if sequence > 1 and emergency_without_acceptance and body["action"] in {"SUSPEND", "ROLLBACK"}:
                require(body["predecessor_acceptance_root"] is None and body["entry_evidence_roots"]["CURRENT_EVENT"] == predecessor, "OPERATIONS_CURRENT_EVENT_MISMATCH")
            require(body["maximum_stage"] == self.maximum_stage and body["real_a5"] is False and body["g0"] == "CLOSED" and body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE", "OPERATIONS_EVENT_EFFECT_FORBIDDEN")
            predecessor, prior_state, prior_stage = event["event_root"], body["next_state"], body["stage"]
        require(prior_state == self.state and prior_stage == self.stage, "OPERATIONS_HISTORY_STATE_MISMATCH")
        for event_root, receipt in self.acceptance.items(): self.verify_acceptance_receipt(receipt, expected_event_root=event_root)
        incident_predecessor = "GENESIS"
        for sequence, record in enumerate(self.incidents, 1):
            signed = _signed(record)
            body = verify_asymmetric(signed, INCIDENT_DOMAIN, expected_key_root=self.identity["key_root"], public_key_hex=self.identity["public_key_hex"])
            require(record["incident_root"] == root(signed), "INCIDENT_ROOT_INVALID")
            require(body["sequence"] == sequence and body["predecessor_incident_root"] == incident_predecessor, "INCIDENT_CHAIN_INVALID")
            incident_predecessor = record["incident_root"]
        return {"status": "PASS", "event_count": len(self.events), "accepted_event_count": len(self.acceptance), "incident_record_count": len(self.incidents), "open_incident_count": len(self._open_incidents()), "head": predecessor, "state": self.state, "stage": self.stage, "maximum_stage": self.maximum_stage, "stage_contract_root": self.deployment_contract_root, "identity_status_root": self.identity_status_root, "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}

    def snapshot(self) -> dict[str, Any]:
        body = {"schema": "ucl.ucm.protected_operations_snapshot.v2", "stage_contract_root": self.deployment_contract_root, "identity_binding_root": self.identity_binding_root, "identity_status_root": self.identity_status_root, "maximum_stage": self.maximum_stage, "state": self.state, "stage": self.stage, "events": deepcopy(self.events), "acceptance": deepcopy(self.acceptance), "incidents": deepcopy(self.incidents), "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
        return {**body, "snapshot_root": root(body)}

    @classmethod
    def restore_snapshot(cls, *, snapshot: Any, expected_snapshot_root: str, expected_minimum_event_sequence: int, **constructor: Any) -> "ProtectedOperationsLifecycle":
        item = exact_keys(snapshot, {"schema", "stage_contract_root", "identity_binding_root", "identity_status_root", "maximum_stage", "state", "stage", "events", "acceptance", "incidents", "standing", "authority_effect", "snapshot_root"}, "$.snapshot")
        body = {key: item[key] for key in item if key != "snapshot_root"}
        require(item["schema"] == "ucl.ucm.protected_operations_snapshot.v2" and item["snapshot_root"] == root(body) == require_root(expected_snapshot_root), "OPERATIONS_SNAPSHOT_ROOT_MISMATCH")
        require(type(expected_minimum_event_sequence) is int and type(expected_minimum_event_sequence) is not bool and len(item["events"]) >= expected_minimum_event_sequence >= 0, "OPERATIONS_SNAPSHOT_ROLLBACK")
        restored = cls(**constructor)
        require(item["stage_contract_root"] == restored.deployment_contract_root and item["identity_binding_root"] == restored.identity_binding_root and item["identity_status_root"] == restored.identity_status_root, "OPERATIONS_SNAPSHOT_CONTEXT_MISMATCH")
        restored.state, restored.stage = item["state"], item["stage"]
        restored.events, restored.acceptance, restored.incidents = deepcopy(item["events"]), deepcopy(item["acceptance"]), deepcopy(item["incidents"])
        restored.verify_history()
        require(restored.snapshot() == item, "OPERATIONS_SNAPSHOT_REPLAY_MISMATCH")
        return restored


class ProtectedOperationsAgent:
    SURFACES = {"INSPECT_LIFECYCLE", "PROPOSE_TRANSITION", "VALIDATE_ACCEPTANCE_RECEIPT", "INSPECT_INCIDENTS", "PLAN_BACKUP", "PLAN_RESTORE", "DESCRIBE_AUTHORITY_CEILING"}

    def __init__(self, lifecycle: ProtectedOperationsLifecycle) -> None:
        self.lifecycle = lifecycle
        self.results: dict[str, dict[str, Any]] = {}

    def dispatch(self, request: Any) -> dict[str, Any]:
        item = exact_keys(request, {"schema", "surface", "idempotency_key", "payload"}, "$.agent_request")
        require(item["schema"] == "ucl.ucm.protected_operations_agent_request.v2", "OPERATIONS_AGENT_SCHEMA_INVALID")
        require(item["surface"] in self.SURFACES, "OPERATIONS_AGENT_SURFACE_UNKNOWN")
        require(type(item["idempotency_key"]) is str and bool(item["idempotency_key"]), "OPERATIONS_AGENT_IDEMPOTENCY_INVALID")
        require(type(item["payload"]) is dict, "OPERATIONS_AGENT_PAYLOAD_INVALID")
        request_root = root(item)
        if item["idempotency_key"] in self.results:
            prior = self.results[item["idempotency_key"]]
            require(prior["request_root"] == request_root, "OPERATIONS_AGENT_IDEMPOTENCY_CONFLICT")
            return deepcopy(prior)
        output = self._run(item["surface"], item["payload"])
        result = {"schema": "ucl.ucm.protected_operations_agent_result.v2", "request_root": request_root, "surface": item["surface"], "output": output, "effect_observed": "NONE", "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
        result["result_root"] = root(result)
        self.results[item["idempotency_key"]] = result
        return deepcopy(result)

    def _run(self, surface: str, payload: dict[str, Any]) -> dict[str, Any]:
        if surface == "INSPECT_LIFECYCLE":
            require(not payload, "OPERATIONS_AGENT_PAYLOAD_FIELDS_INVALID"); return self.lifecycle.verify_history()
        if surface == "INSPECT_INCIDENTS":
            require(not payload, "OPERATIONS_AGENT_PAYLOAD_FIELDS_INVALID"); return {"incident_count": len(self.lifecycle.incidents), "open_incident_count": len(self.lifecycle._open_incidents()), "incident_roots": [row["incident_root"] for row in self.lifecycle.incidents]}
        if surface == "DESCRIBE_AUTHORITY_CEILING":
            require(not payload, "OPERATIONS_AGENT_PAYLOAD_FIELDS_INVALID"); return {"maximum_stage": self.lifecycle.maximum_stage, "stage_contract_root": self.lifecycle.deployment_contract_root, "real_a5": False, "g0": "CLOSED", "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
        if surface == "PROPOSE_TRANSITION":
            item = exact_keys(payload, {"action", "stage", "reason_code"}, "$.agent_request.payload")
            require((self.lifecycle.state, item["action"]) in TRANSITIONS, "OPERATIONS_TRANSITION_INVALID")
            self.lifecycle._expected_stage(item["action"], item["stage"])
            require(item["stage"] in self.lifecycle.identity_status_body["allowed_stages"], "OPERATIONS_STAGE_NOT_AUTHORIZED_BY_IDENTITY")
            return {"proposal": item, "required_entry_criteria": list(self.lifecycle._criteria(item["action"], item["stage"])), "would_transition_to": TRANSITIONS[(self.lifecycle.state, item["action"])], "applied": False}
        if surface == "VALIDATE_ACCEPTANCE_RECEIPT":
            item = exact_keys(payload, {"event_root", "acceptance_root"}, "$.agent_request.payload")
            event_root, acceptance_root = require_root(item["event_root"]), require_root(item["acceptance_root"])
            require(event_root in self.lifecycle.acceptance and self.lifecycle.acceptance[event_root]["acceptance_root"] == acceptance_root, "OPERATIONS_ACCEPTANCE_NOT_FOUND")
            self.lifecycle.verify_acceptance_receipt(self.lifecycle.acceptance[event_root], expected_event_root=event_root)
            return {"event_root": event_root, "acceptance_root": acceptance_root, "status": "VALID"}
        if surface in {"PLAN_BACKUP", "PLAN_RESTORE"}:
            item = exact_keys(payload, {"state_root", "backup_root", "retirement_snapshot_root"}, "$.agent_request.payload")
            return {"operation": surface, "state_root": require_root(item["state_root"]), "backup_root": require_root(item["backup_root"]), "retirement_snapshot_root": require_root(item["retirement_snapshot_root"]), "applied": False, "effect_ceiling": "DISPOSABLE_FIXTURE_ONLY"}
        require(False, "OPERATIONS_AGENT_SURFACE_UNKNOWN")
        raise AssertionError

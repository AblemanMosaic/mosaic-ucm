from __future__ import annotations

from copy import deepcopy
from typing import Any

from .acceptance import STAGES, build_rollback_contract, make_stage_entry_packet, stage_rank
from .application_sdk import make_capability_request, validate_contract_value, verify_sdk_bundle
from .canonical import Refusal, exact_keys, require, require_root, root
from .custody_maturity import CustodyLineage, verify_custody_profile
from .ecosystem import verify_capability_registry, verify_policy_bundle
from .foundation_agent import _scan_no_secrets
from .incident_system import IncidentLedger
from .platform_observability import ObservationLedger
from .platform_operations import make_deployment_proposal, verify_acceptance_receipt, verify_protected_execution_receipt


SURFACES = (
    "ORIENT_PLATFORM",
    "LIST_APPLICATIONS",
    "LIST_CAPABILITIES",
    "DESCRIBE_SDK",
    "VALIDATE_CONTRACT_VALUE",
    "PREPARE_CAPABILITY_REQUEST",
    "DESCRIBE_ACCEPTANCE_STAGE",
    "PREPARE_STAGE_ENTRY",
    "PREPARE_ROLLBACK",
    "OPEN_INCIDENT",
    "TRANSITION_INCIDENT",
    "CHECK_INCIDENT_GATE",
    "INSPECT_CUSTODY",
    "CHECK_CUSTODY_ADMISSION",
    "PREPARE_CUSTODY_MIGRATION",
    "PREPARE_DEPLOYMENT_PROPOSAL",
    "VALIDATE_PROTECTED_EXECUTION",
    "VALIDATE_ACCEPTANCE_RECEIPT",
    "APPEND_OBSERVATION",
    "GET_HEALTH",
    "DECIDE_COURT_LANE",
    "PREPARE_REVIEW_HANDOFF",
)


class PlatformWorkbench:
    """Typed agent/operator surface for the experimental application platform."""

    def __init__(
        self, *, subject_root: str, registry: dict[str, Any], policy: dict[str, Any], sdk: dict[str, Any],
        expected_registry_root: str, expected_policy_root: str,
        acceptance_constitution: dict[str, Any], custody_profile: dict[str, Any], custody: CustodyLineage,
        incidents: IncidentLedger, observations: ObservationLedger,
    ) -> None:
        self.subject_root = require_root(subject_root)
        require(registry.get("registry_root") == require_root(expected_registry_root), "WORKBENCH_REGISTRY_EXTERNAL_PIN_MISMATCH")
        require(policy.get("policy_root") == require_root(expected_policy_root), "WORKBENCH_POLICY_EXTERNAL_PIN_MISMATCH")
        verify_capability_registry(registry, expected_subject_root=self.subject_root)
        verify_policy_bundle(policy, registry=registry, expected_subject_root=self.subject_root)
        verify_sdk_bundle(sdk, expected_subject_root=self.subject_root, registry=registry, policy=policy)
        require(acceptance_constitution.get("subject_root") == self.subject_root, "WORKBENCH_ACCEPTANCE_CONTEXT_MISMATCH")
        verify_custody_profile(custody_profile, expected_subject_root=self.subject_root)
        require(custody.subject_root == self.subject_root and incidents.subject_root == self.subject_root and observations.subject_root == self.subject_root, "WORKBENCH_RUNTIME_CONTEXT_MISMATCH")
        self.registry, self.policy, self.sdk = deepcopy(registry), deepcopy(policy), deepcopy(sdk)
        self.acceptance_constitution = deepcopy(acceptance_constitution)
        self.custody_profile, self.custody, self.incidents, self.observations = deepcopy(custody_profile), custody, incidents, observations
        self._results: dict[str, tuple[str, dict[str, Any]]] = {}

    def dispatch(self, value: Any) -> dict[str, Any]:
        request = exact_keys(value, {"schema", "surface", "idempotency_key", "effect_ceiling", "payload"}, "$.request")
        require(request["schema"] == "ucl.ucm.platform_workbench_request.v1" and request["surface"] in SURFACES, "WORKBENCH_SURFACE_INVALID")
        require(type(request["idempotency_key"]) is str and 8 <= len(request["idempotency_key"]) <= 128, "IDEMPOTENCY_KEY_INVALID")
        require(request["effect_ceiling"] == "NONE" and type(request["payload"]) is dict, "WORKBENCH_EFFECT_CEILING_INVALID")
        request_root = root(request)
        prior = self._results.get(request["idempotency_key"])
        try:
            _scan_no_secrets(request["payload"], "$.request.payload")
            if prior is not None:
                require(prior[0] == request_root, "IDEMPOTENCY_CONFLICT")
                return deepcopy(prior[1])
            output = self._execute(request["surface"], request["payload"], request["idempotency_key"])
            outcome, diagnostic = "COMPLETED", "PASS"
        except Refusal as error:
            output = {"path": error.path, "detail": error.detail}
            outcome, diagnostic = "REFUSED", error.code
        except (KeyError, TypeError, IndexError) as error:
            output = {"path": "$.request.payload", "detail": type(error).__name__}
            outcome, diagnostic = "REFUSED", "WORKBENCH_PAYLOAD_INVALID"
        body = {
            "schema": "ucl.ucm.platform_workbench_result.v1",
            "surface": request["surface"],
            "request_root": request_root,
            "outcome": outcome,
            "diagnostic": diagnostic,
            "output": output,
            "effect_observed": "NONE",
            "maximum_stage": "S2_INFORMATION_ONLY_FEDERATION",
            "standing": "INFORMATION_ONLY",
            "real_a5": False,
            "g0": "CLOSED",
            "authority_effect": "NONE",
        }
        result = {**body, "result_root": root(body)}
        if prior is None:
            self._results[request["idempotency_key"]] = (request_root, deepcopy(result))
        return result

    def _execute(self, surface: str, payload: dict[str, Any], key: str) -> dict[str, Any]:
        if surface == "ORIENT_PLATFORM":
            exact_keys(payload, set(), "$.payload")
            return {
                "program": "UCL-UCM-APPLICATION-ECOSYSTEM-PLATFORM-c1",
                "subject_root": self.subject_root,
                "sdk_root": self.sdk["sdk_root"],
                "surfaces": list(SURFACES),
                "maximum_stage": "S2_INFORMATION_ONLY_FEDERATION",
                "standing": "INFORMATION_ONLY",
            }
        if surface == "LIST_APPLICATIONS":
            exact_keys(payload, set(), "$.payload")
            return {"applications": [{"application_id": item["application_id"], "manifest_root": item["manifest_root"], "maximum_effect_class": item["maximum_effect_class"]} for item in self.policy["applications"]]}
        if surface == "LIST_CAPABILITIES":
            exact_keys(payload, set(), "$.payload")
            return {"capabilities": [{"capability_id": item["capability_id"], "descriptor_root": item["descriptor_root"], "effect_class": item["effect_class"]} for item in self.registry["capabilities"]]}
        if surface == "DESCRIBE_SDK":
            exact_keys(payload, set(), "$.payload")
            return {"sdk_root": self.sdk["sdk_root"], "sdk_version": self.sdk["sdk_version"], "contract_roots": self.sdk["contract_roots"], "composition_roots": self.sdk["composition_roots"]}
        if surface == "VALIDATE_CONTRACT_VALUE":
            exact_keys(payload, {"contract_id", "value"}, "$.payload")
            contracts = {item["contract_id"]: item for item in self.sdk["contracts"]}
            require(payload["contract_id"] in contracts, "CONTRACT_UNKNOWN")
            return validate_contract_value(contracts[payload["contract_id"]], payload["value"])
        if surface == "PREPARE_CAPABILITY_REQUEST":
            exact_keys(payload, {"application_id", "capability_id", "contract_id", "input"}, "$.payload")
            apps = {item["application_id"]: item for item in self.policy["applications"]}
            contracts = {item["contract_id"]: item for item in self.sdk["contracts"]}
            require(payload["application_id"] in apps and payload["contract_id"] in contracts, "SDK_CONTEXT_UNKNOWN")
            return make_capability_request(application=apps[payload["application_id"]], capability_id=payload["capability_id"], input_contract=contracts[payload["contract_id"]], input_value=payload["input"], idempotency_key="sdk:" + key)
        if surface == "DESCRIBE_ACCEPTANCE_STAGE":
            exact_keys(payload, {"stage"}, "$.payload")
            ordinal = stage_rank(payload["stage"])
            return deepcopy(self.acceptance_constitution["stages"][ordinal])
        if surface == "PREPARE_STAGE_ENTRY":
            exact_keys(payload, {"stage", "prior_acceptance", "evidence_roots", "decision_root"}, "$.payload")
            return make_stage_entry_packet(constitution=self.acceptance_constitution, stage=payload["stage"], subject_root=self.subject_root, prior_acceptance=payload["prior_acceptance"], evidence_roots=payload["evidence_roots"], decision_root=payload["decision_root"])
        if surface == "PREPARE_ROLLBACK":
            exact_keys(payload, {"stage", "preimage_root", "dependent_roots"}, "$.payload")
            return build_rollback_contract(constitution=self.acceptance_constitution, stage=payload["stage"], subject_root=self.subject_root, preimage_root=payload["preimage_root"], dependent_roots=payload["dependent_roots"])
        if surface == "OPEN_INCIDENT":
            exact_keys(payload, {"incident_id", "severity", "affected_roots", "evidence_roots", "summary_root"}, "$.payload")
            return self.incidents.open(**payload, idempotency_key="incident:" + key)
        if surface == "TRANSITION_INCIDENT":
            exact_keys(payload, {"incident_id", "target_status", "evidence_roots", "resolution_root"}, "$.payload")
            return self.incidents.transition(**payload, idempotency_key="incident:" + key)
        if surface == "CHECK_INCIDENT_GATE":
            exact_keys(payload, {"affected_roots"}, "$.payload")
            return self.incidents.gate(affected_roots=payload["affected_roots"])
        if surface == "INSPECT_CUSTODY":
            exact_keys(payload, set(), "$.payload")
            return self.custody.export_capsule()
        if surface == "CHECK_CUSTODY_ADMISSION":
            exact_keys(payload, {"role", "proposed_public_root"}, "$.payload")
            return self.custody.admission_check(**payload)
        if surface == "PREPARE_CUSTODY_MIGRATION":
            exact_keys(payload, {"target_profile_root", "backup_root", "rollback_root"}, "$.payload")
            return self.custody.migration_plan(**payload)
        if surface == "PREPARE_DEPLOYMENT_PROPOSAL":
            exact_keys(payload, {"application_root", "artifact_root", "target_profile_root", "rollback_plan_root", "requested_stage", "source_root", "qualification_root"}, "$.payload")
            return make_deployment_proposal(subject_root=self.subject_root, **payload)
        if surface == "VALIDATE_PROTECTED_EXECUTION":
            exact_keys(payload, {"proposal", "receipt", "expected_result_root"}, "$.payload")
            return verify_protected_execution_receipt(payload["receipt"], proposal=payload["proposal"], expected_result_root=payload["expected_result_root"])
        if surface == "VALIDATE_ACCEPTANCE_RECEIPT":
            exact_keys(payload, {"receipt", "expected_proposal_root", "expected_execution_receipt_root", "expected_rollback_receipt_root", "expected_reviewer_verdict_root", "expected_decision_root"}, "$.payload")
            return verify_acceptance_receipt(payload["receipt"], expected_proposal_root=payload["expected_proposal_root"], expected_execution_receipt_root=payload["expected_execution_receipt_root"], expected_rollback_receipt_root=payload["expected_rollback_receipt_root"], expected_reviewer_verdict_root=payload["expected_reviewer_verdict_root"], expected_decision_root=payload["expected_decision_root"])
        if surface == "APPEND_OBSERVATION":
            exact_keys(payload, {"observation_id", "kind", "status", "observed_subject_root", "evidence_roots", "detail_root"}, "$.payload")
            return self.observations.append(**payload, idempotency_key="observation:" + key)
        if surface == "GET_HEALTH":
            exact_keys(payload, set(), "$.payload")
            return self.observations.health()
        if surface == "DECIDE_COURT_LANE":
            exact_keys(payload, {"changed_paths", "circumstances", "frozen_candidate"}, "$.payload")
            paths, circumstances = payload["changed_paths"], payload["circumstances"]
            require(type(paths) is list and all(type(item) is str for item in paths) and type(circumstances) is list and all(type(item) is str for item in circumstances) and type(payload["frozen_candidate"]) is bool, "COURT_LANE_INPUT_INVALID")
            normalized = [item.replace("\\", "/").casefold() for item in paths]
            malformed = any(
                not path or path.startswith("/") or ":" in path or any(part in {"", ".", ".."} for part in path.split("/"))
                or any(ord(ch) > 127 for ch in path)
                for path in normalized
            )
            sensitive = ("src/", "tools/", "tests/", "spec/", "planning/", "verifier", "freeze", "release", "authority", "custody", "deploy", "scheduler", "cache")
            forced = malformed or bool(circumstances) or any(any(token in path for token in sensitive) for path in normalized) or not paths
            if payload["frozen_candidate"]:
                lane, reason = "REVIEW", "EXACT_FROZEN_BYTES"
            elif forced:
                lane, reason = "QUALIFICATION", "SENSITIVE_OR_UNKNOWN_IMPACT"
            elif all(path.startswith("docs/") and path.endswith(".md") for path in normalized):
                lane, reason = "FAST", "ALLOWLISTED_DOCUMENTATION"
            else:
                lane, reason = "INCREMENTAL", "CONTENT_GRAPH_REQUIRED"
            return {"lane": lane, "reason": reason, "cache_allowed": lane in {"FAST", "INCREMENTAL"}, "downgrade_allowed": False}
        if surface == "PREPARE_REVIEW_HANDOFF":
            exact_keys(payload, {"evidence_roots", "work_order_root"}, "$.payload")
            require(type(payload["evidence_roots"]) is list and payload["evidence_roots"] == sorted(payload["evidence_roots"]) and payload["evidence_roots"], "REVIEW_EVIDENCE_SET_INVALID")
            for value in payload["evidence_roots"]: require_root(value)
            body = {
                "schema": "ucl.ucm.platform_review_handoff.v1",
                "subject_root": self.subject_root,
                "sdk_root": self.sdk["sdk_root"],
                "evidence_roots": payload["evidence_roots"],
                "work_order_root": require_root(payload["work_order_root"]),
                "status": "UNBOUND_REVIEW_HANDOFF",
                "standing": "INFORMATION_ONLY",
                "authority_effect": "NONE",
            }
            return {**body, "handoff_root": root(body)}
        raise Refusal("WORKBENCH_SURFACE_INVALID")

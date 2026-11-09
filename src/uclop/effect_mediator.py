from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import exact_keys, require, require_root, root
from .ecosystem import (
    application_from_policy,
    capability_from_registry,
    effect_rank,
    verify_capability_registry,
    verify_policy_bundle,
)


REQUEST_KEYS = {
    "schema", "application_id", "capability_id", "policy_root", "registry_root",
    "input_root", "idempotency_key", "requested_effect_class", "requested_stage",
    "standing", "authority_effect", "request_root",
}


def make_capability_request(
    *, application_id: str, capability_id: str, policy: dict[str, Any],
    registry: dict[str, Any], input_value: Any, idempotency_key: str,
) -> dict[str, Any]:
    verify_policy_bundle(policy, registry=registry, expected_subject_root=policy["subject_root"])
    application = application_from_policy(policy, application_id)
    capability = capability_from_registry(registry, capability_id)
    require(capability_id in policy["grants"][application_id], "CAPABILITY_NOT_GRANTED")
    require(type(idempotency_key) is str and 8 <= len(idempotency_key) <= 128, "IDEMPOTENCY_KEY_INVALID")
    body = {
        "schema": "ucl.ucm.capability_request.v1",
        "application_id": application_id,
        "capability_id": capability_id,
        "policy_root": policy["policy_root"],
        "registry_root": registry["registry_root"],
        "input_root": root(input_value),
        "idempotency_key": idempotency_key,
        "requested_effect_class": capability["effect_class"],
        "requested_stage": capability["minimum_stage"],
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    require(effect_rank(body["requested_effect_class"]) <= effect_rank(application["maximum_effect_class"]), "APPLICATION_EFFECT_CEILING_EXCEEDED")
    return {**body, "request_root": root(body)}


def verify_capability_request(
    value: Any, *, policy: dict[str, Any], registry: dict[str, Any],
    input_value: Any, expected_application_id: str | None = None,
    expected_capability_id: str | None = None,
) -> dict[str, Any]:
    item = exact_keys(value, REQUEST_KEYS, "$.request")
    body = {key: item[key] for key in item if key != "request_root"}
    require(item["schema"] == "ucl.ucm.capability_request.v1" and item["request_root"] == root(body), "CAPABILITY_REQUEST_ROOT_INVALID")
    verify_policy_bundle(policy, registry=registry, expected_subject_root=policy["subject_root"])
    require(item["policy_root"] == policy["policy_root"] and item["registry_root"] == registry["registry_root"], "CAPABILITY_REQUEST_CONTEXT_MISMATCH")
    application = application_from_policy(policy, item["application_id"])
    capability = capability_from_registry(registry, item["capability_id"])
    require(item["capability_id"] in policy["grants"][item["application_id"]], "CAPABILITY_NOT_GRANTED")
    require(item["input_root"] == root(input_value), "CAPABILITY_INPUT_MISMATCH")
    require(type(item["idempotency_key"]) is str and 8 <= len(item["idempotency_key"]) <= 128, "IDEMPOTENCY_KEY_INVALID")
    require(item["requested_effect_class"] == capability["effect_class"] and item["requested_stage"] == capability["minimum_stage"], "CAPABILITY_REQUEST_EFFECT_MISMATCH")
    require(effect_rank(capability["effect_class"]) <= effect_rank(application["maximum_effect_class"]), "APPLICATION_EFFECT_CEILING_EXCEEDED")
    if expected_application_id is not None:
        require(item["application_id"] == expected_application_id, "CAPABILITY_REQUEST_APPLICATION_MISMATCH")
    if expected_capability_id is not None:
        require(item["capability_id"] == expected_capability_id, "CAPABILITY_REQUEST_CAPABILITY_MISMATCH")
    require(item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "CAPABILITY_REQUEST_AUTHORITY_INVALID")
    return deepcopy(body)


def evaluate_capability_request(
    request: dict[str, Any], *, policy: dict[str, Any], registry: dict[str, Any], input_value: Any,
) -> dict[str, Any]:
    verify_capability_request(request, policy=policy, registry=registry, input_value=input_value)
    capability = capability_from_registry(registry, request["capability_id"])
    executable = capability["effect_class"] == "NONE" and capability["minimum_stage"] == "D2_INDEPENDENT_REVIEW"
    disposition = "EXECUTABLE_NO_EFFECT" if executable else "EXTERNAL_DECISION_REQUIRED"
    body = {
        "schema": "ucl.ucm.capability_evaluation.v1",
        "request_root": request["request_root"],
        "policy_root": policy["policy_root"],
        "capability_root": capability["descriptor_root"],
        "effect_class": capability["effect_class"],
        "minimum_stage": capability["minimum_stage"],
        "disposition": disposition,
        "executable": executable,
        "effect_observed": "NONE",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "evaluation_root": root(body)}


def prepare_effect_proposal(evaluation: dict[str, Any]) -> dict[str, Any]:
    require(type(evaluation) is dict and evaluation.get("schema") == "ucl.ucm.capability_evaluation.v1", "CAPABILITY_EVALUATION_INVALID")
    evaluation_body = {key: value for key, value in evaluation.items() if key != "evaluation_root"}
    require(evaluation.get("evaluation_root") == root(evaluation_body), "CAPABILITY_EVALUATION_ROOT_INVALID")
    require(evaluation.get("disposition") == "EXTERNAL_DECISION_REQUIRED" and evaluation.get("executable") is False, "EFFECT_PROPOSAL_NOT_REQUIRED")
    body = {
        "schema": "ucl.ucm.effect_proposal.v1",
        "request_root": require_root(evaluation["request_root"]),
        "evaluation_root": evaluation["evaluation_root"],
        "policy_root": require_root(evaluation["policy_root"]),
        "effect_class": evaluation["effect_class"],
        "required_stage": evaluation["minimum_stage"],
        "status": "UNBOUND_PROPOSAL",
        "executable": False,
        "effect_observed": "NONE",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "proposal_root": root(body)}


class EffectMediator:
    """Idempotent D2 mediator. It can evaluate and simulate, never apply effects."""

    def __init__(self, *, subject_root: str, registry: dict[str, Any], policy: dict[str, Any], expected_registry_root: str, expected_policy_root: str) -> None:
        self.subject_root = require_root(subject_root)
        verify_capability_registry(registry, expected_subject_root=self.subject_root)
        verify_policy_bundle(policy, registry=registry, expected_subject_root=self.subject_root)
        require(registry["registry_root"] == require_root(expected_registry_root), "CAPABILITY_REGISTRY_EXTERNAL_PIN_MISMATCH")
        require(policy["policy_root"] == require_root(expected_policy_root), "POLICY_EXTERNAL_PIN_MISMATCH")
        self.registry = deepcopy(registry)
        self.policy = deepcopy(policy)
        self._results: dict[str, tuple[str, dict[str, Any]]] = {}

    def evaluate(self, request: dict[str, Any], *, input_value: Any) -> dict[str, Any]:
        result = evaluate_capability_request(request, policy=self.policy, registry=self.registry, input_value=input_value)
        prior = self._results.get(request["idempotency_key"])
        if prior is not None:
            require(prior[0] == request["request_root"], "IDEMPOTENCY_CONFLICT")
            return deepcopy(prior[1])
        self._results[request["idempotency_key"]] = (request["request_root"], deepcopy(result))
        return result

    def simulate_no_effect(self, request: dict[str, Any], *, input_value: Any, output_value: Any) -> dict[str, Any]:
        evaluation = self.evaluate(request, input_value=input_value)
        require(evaluation["disposition"] == "EXECUTABLE_NO_EFFECT", "EFFECT_EXECUTION_FORBIDDEN")
        body = {
            "schema": "ucl.ucm.no_effect_execution_receipt.v1",
            "subject_root": self.subject_root,
            "request_root": request["request_root"],
            "evaluation_root": evaluation["evaluation_root"],
            "input_root": root(input_value),
            "output_root": root(output_value),
            "status": "PASS",
            "effect_observed": "NONE",
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        return {**body, "receipt_root": root(body)}


"""Exact, non-authorizing correspondence with the UCM Governed Execution Layer.

UGEL remains an external executor realization.  This module discovers the
known Batch E contract, binds an exact external installation, compiles UCM
and Pippi records into the Batch E guest-call vocabulary, and supplies a
small pure ``sim.add`` reference evaluator.  It never selects an executor,
loads the supplied UGEL archive, mints a grant, signs a receipt, or dispatches
an effect.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any

from uclop.canonical import canonical_bytes, exact_keys, require, require_root, root

from .amcas import BOUNDARY
from .operation_gateway import (CONTRACT_SCHEMA, DISPATCH_SCHEMA,
                                TERMINAL_SCHEMA)
from .pippi import validate_pippi_decision


UGEL_DOMAIN = b"MOSAIC-UGEL-E1\x00"
UGEL_SOURCE_ARCHIVE_SHA256 = (
    "70e09459418a6672cc0e1924a7f6338fd1e0a929f8dc6f5630e61d0f866307cc"
)
UGEL_SOURCE_ROOT = (
    "8bdcd1532f914f4c471d8311597e61e59d6cfdf15347e3f55d63f6556476d851"
)
UGEL_WIT_SHA256 = (
    "cd0babc8e6221f5df82ac766615ef1c185dc9cbdbbea6ab1b417af548211abf9"
)
UGEL_BOUNDARY_SHA256 = (
    "fae15cdd1a2ae19d2842ed657faf5531f51cfa8aa8ae617306e45407f8cb11fd"
)
UGEL_HOST_SHA256 = (
    "f738561cc20cc1cc25415ff8af2f592528fa1f7128e3a861dcddc490856f78a3"
)
UGEL_EFFECTS = ("fs.create", "fs.read", "sim.add", "sim.echo")
UGEL_PILOT_EFFECTS = ("sim.add",)
UGEL_ACTIONS = ("ADMIT", "OBSERVE", "PREVIEW", "RUN")


def _sha(value: Any, code: str) -> str:
    require(type(value) is str and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value), code)
    return value


def _identifier(value: Any, code: str) -> str:
    require(type(value) is str and value == value.strip() and 0 < len(value) <= 192
            and all(ch.isalnum() or ch in "._:-" for ch in value), code)
    return value


def ugel_canonical_bytes(value: Any) -> bytes:
    """Reproduce Batch E canonical JSON, including its ASCII-only policy."""
    try:
        text = json.dumps(value, sort_keys=True, ensure_ascii=True,
                          separators=(",", ":"), allow_nan=False)
        return text.encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ValueError("UGEL_CANONICAL_VALUE_INVALID") from error


def ugel_root(value: Any) -> str:
    return hashlib.sha256(UGEL_DOMAIN + ugel_canonical_bytes(value)).hexdigest()


def executor_pack_registry() -> dict[str, Any]:
    body = {
        "schema": "mosaic.ucm.ugel-executor-pack-registry.v0.1",
        "pack_id": "UGEL_EXECUTOR",
        "implementation_id": "UGEL_BATCH_E_R001",
        "source_archive_sha256": UGEL_SOURCE_ARCHIVE_SHA256,
        "source_root": UGEL_SOURCE_ROOT,
        "wit_contract_sha256": UGEL_WIT_SHA256,
        "boundary_source_sha256": UGEL_BOUNDARY_SHA256,
        "host_source_sha256": UGEL_HOST_SHA256,
        "declared_effect_ids": list(UGEL_EFFECTS),
        "r022_pilot_effect_ids": list(UGEL_PILOT_EFFECTS),
        "unsupported_effect_ids": sorted(set(UGEL_EFFECTS) - set(UGEL_PILOT_EFFECTS)),
        "native_wasi_runtime_status": "NOT_BOUND",
        "rust_client_execution_status": "NOT_RUN",
        "external_binding_required": True,
        "executor_selected_by_ucm": False,
        "guest_can_mint_grants": False,
        "structural_verification_is_semantic_proof": False,
        **BOUNDARY,
    }
    return {**body, "registry_root": root(body)}


def build_executor_binding(*, executor_public_key_hex: str,
                           source_archive_sha256: str,
                           source_root: str,
                           evidence_roots: list[str]) -> dict[str, Any]:
    registry = executor_pack_registry()
    require(source_archive_sha256 == UGEL_SOURCE_ARCHIVE_SHA256,
            "UGEL_SOURCE_ARCHIVE_PIN_MISMATCH")
    require(source_root == UGEL_SOURCE_ROOT, "UGEL_SOURCE_ROOT_MISMATCH")
    _sha(executor_public_key_hex, "UGEL_EXECUTOR_PUBLIC_KEY_INVALID")
    require(type(evidence_roots) is list
            and evidence_roots == sorted(set(evidence_roots))
            and bool(evidence_roots), "UGEL_BINDING_EVIDENCE_INVALID")
    for value in evidence_roots:
        require_root(value)
    body = {
        "schema": "mosaic.ucm.ugel-executor-binding.v0.1",
        "pack_id": registry["pack_id"],
        "implementation_id": registry["implementation_id"],
        "registry_root": registry["registry_root"],
        "source_archive_sha256": source_archive_sha256,
        "source_root": source_root,
        "executor_public_key_hex": executor_public_key_hex,
        "effect_ids": list(UGEL_PILOT_EFFECTS),
        "evidence_roots": list(evidence_roots),
        "binding_status": "BOUND_EXTERNAL",
        "binding_grants_authority": False,
        "executor_selected_by_ucm": False,
        **BOUNDARY,
    }
    return {**body, "binding_root": root(body)}


def validate_executor_binding(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "pack_id", "implementation_id", "registry_root",
        "source_archive_sha256", "source_root", "executor_public_key_hex",
        "effect_ids", "evidence_roots", "binding_status",
        "binding_grants_authority", "executor_selected_by_ucm", "standing",
        "authority_effect", "real_a5", "g0", "binding_root",
    })
    expected = build_executor_binding(
        executor_public_key_hex=item["executor_public_key_hex"],
        source_archive_sha256=item["source_archive_sha256"],
        source_root=item["source_root"], evidence_roots=item["evidence_roots"])
    require(item == expected, "UGEL_EXECUTOR_BINDING_INVALID")
    return deepcopy(item)


def build_component_policy(*, component_sha256: str, contract_root: str,
                           allowed_effects: list[str], resource_ids: list[str],
                           allowed_actions: list[str],
                           max_text_bytes: int) -> dict[str, Any]:
    _sha(component_sha256, "UGEL_COMPONENT_SHA256_INVALID")
    require_root(contract_root)
    require(type(allowed_effects) is list
            and allowed_effects == sorted(set(allowed_effects))
            and bool(allowed_effects)
            and set(allowed_effects) <= set(UGEL_PILOT_EFFECTS),
            "UGEL_POLICY_EFFECTS_INVALID")
    require(type(resource_ids) is list and resource_ids == sorted(set(resource_ids))
            and bool(resource_ids)
            and all(type(item) is str and item for item in resource_ids),
            "UGEL_POLICY_RESOURCES_INVALID")
    require(type(allowed_actions) is list
            and allowed_actions == sorted(set(allowed_actions))
            and bool(allowed_actions) and set(allowed_actions) <= set(UGEL_ACTIONS),
            "UGEL_POLICY_ACTIONS_INVALID")
    require(type(max_text_bytes) is int and not isinstance(max_text_bytes, bool)
            and 0 <= max_text_bytes <= 65536,
            "UGEL_POLICY_SIZE_INVALID")
    body = {
        "schema": "mosaic.ugel.batch-e.component-policy.v1",
        "component_sha256": component_sha256,
        "contract_root": contract_root,
        "allowed_effects": list(allowed_effects),
        "allowed_actions": list(allowed_actions),
        "resource_ids": list(resource_ids),
        "max_text_bytes": max_text_bytes,
        **BOUNDARY,
    }
    return {**body, "root": ugel_root(body)}


def validate_component_policy(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "component_sha256", "contract_root", "allowed_effects",
        "allowed_actions", "resource_ids", "max_text_bytes", "standing",
        "authority_effect", "real_a5", "g0", "root",
    })
    expected = build_component_policy(
        component_sha256=item["component_sha256"],
        contract_root=item["contract_root"],
        allowed_effects=item["allowed_effects"], resource_ids=item["resource_ids"],
        allowed_actions=item["allowed_actions"],
        max_text_bytes=item["max_text_bytes"])
    require(item == expected, "UGEL_COMPONENT_POLICY_INVALID")
    return deepcopy(item)


def build_guest_call(*, policy: dict[str, Any], action: str,
                     operation_id: str, effect_id: str, resource_id: str,
                     parameters: dict[str, Any],
                     evidence_roots: list[str]) -> dict[str, Any]:
    policy = validate_component_policy(policy)
    _identifier(operation_id, "UGEL_OPERATION_ID_INVALID")
    require(action in policy["allowed_actions"], "UGEL_ACTION_NOT_ALLOWED")
    require(effect_id in policy["allowed_effects"], "UGEL_EFFECT_NOT_ALLOWED")
    require(resource_id in policy["resource_ids"], "UGEL_RESOURCE_NOT_ALLOWED")
    require(type(parameters) is dict, "UGEL_PARAMETERS_INVALID")
    if "text" in parameters:
        require(type(parameters["text"]) is str
                and len(parameters["text"].encode("utf-8"))
                <= policy["max_text_bytes"],
                "UGEL_CALL_TEXT_LIMIT")
    require(type(evidence_roots) is list
            and evidence_roots == sorted(set(evidence_roots)),
            "UGEL_EVIDENCE_ROOTS_INVALID")
    for value in evidence_roots:
        require_root(value)
    request = {
        "operation_id": operation_id, "effect": effect_id,
        "effect_id": effect_id, "resource_id": resource_id,
        "parameters": deepcopy(parameters),
        "evidence_roots": list(evidence_roots),
    }
    body = {"schema": "mosaic.ugel.batch-e.guest-call.v1",
            "policy_root": policy["root"], "action": action,
            "request": request}
    return {**body, "request_root": ugel_root(body)}


def validate_guest_call(value: Any, *, policy: dict[str, Any]) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "policy_root", "action", "request",
                              "request_root"})
    request = exact_keys(item["request"], {"operation_id", "effect", "effect_id",
                                           "resource_id", "parameters",
                                           "evidence_roots"})
    expected = build_guest_call(
        policy=policy, action=item["action"], operation_id=request["operation_id"],
        effect_id=request["effect_id"], resource_id=request["resource_id"],
        parameters=request["parameters"], evidence_roots=request["evidence_roots"])
    require(request["effect"] == request["effect_id"] and item == expected,
            "UGEL_GUEST_CALL_INVALID")
    return deepcopy(item)


def evaluate_reference_sim_add(*, guest_call: dict[str, Any],
                               policy: dict[str, Any]) -> dict[str, Any]:
    call = validate_guest_call(guest_call, policy=policy)
    require(call["action"] == "RUN"
            and call["request"]["effect_id"] == "sim.add",
            "UGEL_REFERENCE_EFFECT_UNSUPPORTED")
    parameters = exact_keys(call["request"]["parameters"], {"left", "right"})
    left, right = parameters["left"], parameters["right"]
    require(type(left) is int and not isinstance(left, bool)
            and type(right) is int and not isinstance(right, bool),
            "UGEL_SIM_ADD_OPERAND_INVALID")
    result = {
        "schema": "mosaic.ucm.ugel-reference-result.v0.1",
        "request_root": call["request_root"], "effect_id": "sim.add",
        "resource_id": call["request"]["resource_id"],
        "output": {"sum": left + right},
        "executor_kind": "PURE_REFERENCE_SIMULATOR",
        "native_ugel_runtime_claimed": False,
        **BOUNDARY,
    }
    return {**result, "ugel_result_root": ugel_root(result),
            "result_root": root(result)}


def validate_reference_result(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "request_root", "effect_id", "resource_id", "output",
        "executor_kind", "native_ugel_runtime_claimed", "standing",
        "authority_effect", "real_a5", "g0", "ugel_result_root",
        "result_root",
    })
    exact_keys(item["output"], {"sum"}, "$.output")
    require(item["schema"] == "mosaic.ucm.ugel-reference-result.v0.1"
            and item["effect_id"] == "sim.add"
            and item["executor_kind"] == "PURE_REFERENCE_SIMULATOR"
            and item["native_ugel_runtime_claimed"] is False
            and type(item["output"]["sum"]) is int
            and not isinstance(item["output"]["sum"], bool),
            "UGEL_REFERENCE_RESULT_INVALID")
    body = {key: deepcopy(value) for key, value in item.items()
            if key not in {"ugel_result_root", "result_root"}}
    require(item["ugel_result_root"] == ugel_root(body)
            and item["result_root"] == root(body),
            "UGEL_REFERENCE_RESULT_ROOT_INVALID")
    return deepcopy(item)


def validate_correspondence(value: Any) -> dict[str, Any]:
    require(type(value) is dict
            and value.get("schema") == "mosaic.ucm.ugel-correspondence.v0.1"
            and value.get("correspondence_root") == root({
                key: deepcopy(item) for key, item in value.items()
                if key != "correspondence_root"
            }), "UGEL_CORRESPONDENCE_INVALID")
    return deepcopy(value)


def compile_correspondence(*, pippi_decision: dict[str, Any],
                           proposal_id: str, operational_contract: dict[str, Any],
                           executor_binding: dict[str, Any],
                           component_policy: dict[str, Any],
                           guest_call: dict[str, Any]) -> dict[str, Any]:
    decision = validate_pippi_decision(pippi_decision)
    binding = validate_executor_binding(executor_binding)
    policy = validate_component_policy(component_policy)
    call = validate_guest_call(guest_call, policy=policy)
    _identifier(proposal_id, "UGEL_PROPOSAL_ID_INVALID")
    contract = exact_keys(operational_contract, {
        "schema", "operation_id", "application_id", "action_id", "request_root",
        "subject_identity_root", "session_root", "jurisdiction_root",
        "executor_public_key_hex", "requested_effect_classes", "budget",
        "rollback_root", "generation", "idempotency_key", "expected_result_root",
        "authorization_time", "permit", "revocation_registry",
        "standing", "authority_effect", "real_a5", "g0", "contract_root",
    })
    require(contract["schema"] == CONTRACT_SCHEMA
            and contract["contract_root"] == root({
                key: deepcopy(value) for key, value in contract.items()
                if key != "contract_root"
            }), "UGEL_OPERATIONAL_CONTRACT_INVALID")
    matches = [row for row in decision["proposal_dispositions"]
               if row["proposal_id"] == proposal_id]
    require(decision["status"] == "VALIDATED" and len(matches) == 1
            and matches[0]["decision"] == "PASS"
            and matches[0]["declared"] and matches[0]["effectful"]
            and matches[0]["contract_root"] == contract["contract_root"],
            "UGEL_PIPPI_DECISION_NOT_DISPATCHABLE")
    expected = evaluate_reference_sim_add(guest_call=call, policy=policy)
    require(contract["operation_id"] == call["request"]["operation_id"]
            and contract["request_root"] == call["request_root"]
            and contract["executor_public_key_hex"] == binding["executor_public_key_hex"]
            and contract["expected_result_root"] == expected["result_root"]
            and "PROCESS" in contract["requested_effect_classes"],
            "UGEL_OPERATIONAL_BINDING_INVALID")
    wit_request = {
        "operation-id": call["request"]["operation_id"],
        "effect-id": call["request"]["effect_id"],
        "resource-id": call["request"]["resource_id"],
        "parameters-canonical-json": ugel_canonical_bytes(
            call["request"]["parameters"]).decode("ascii"),
        "evidence-roots-canonical-json": ugel_canonical_bytes(
            call["request"]["evidence_roots"]).decode("ascii"),
    }
    body = {
        "schema": "mosaic.ucm.ugel-correspondence.v0.1",
        "registry_root": executor_pack_registry()["registry_root"],
        "executor_binding_root": binding["binding_root"],
        "pippi_decision_root": decision["decision_root"],
        "proposal_id": proposal_id,
        "operational_contract_root": contract["contract_root"],
        "component_policy_root": policy["root"],
        "guest_call_root": call["request_root"],
        "expected_result_root": expected["result_root"],
        "wit_request": wit_request,
        "wit_request_sha256": hashlib.sha256(
            ugel_canonical_bytes(wit_request)).hexdigest(),
        "ugel_domain_root": ugel_root(wit_request),
        "ucm_semantic_root": root(wit_request),
        "root_relation": "CORRESPONDENCE_NOT_HASH_IDENTITY",
        "executor_selected_by_ucm": False,
        "dispatch_performed": False,
        **BOUNDARY,
    }
    return {**body, "correspondence_root": root(body)}


def build_dispatch_receipt_body(*, correspondence: dict[str, Any],
                                operational_contract: dict[str, Any],
                                dispatch_authorization: dict[str, Any],
                                started_at: int) -> dict[str, Any]:
    correspondence = validate_correspondence(correspondence)
    contract_root = require_root(operational_contract.get("contract_root"))
    require(contract_root == correspondence["operational_contract_root"],
            "UGEL_CORRESPONDENCE_CONTRACT_MISMATCH")
    require(type(started_at) is int and not isinstance(started_at, bool)
            and started_at >= 0, "UGEL_TIME_INVALID")
    return {
        "schema": DISPATCH_SCHEMA,
        "operation_id": operational_contract["operation_id"],
        "contract_root": contract_root,
        "g1_root": require_root(dispatch_authorization["g1_root"]),
        "dispatch_authorization_root": require_root(
            dispatch_authorization["receipt_root"]),
        "idempotency_key": operational_contract["idempotency_key"],
        "dispatch_nonce": dispatch_authorization["dispatch_nonce"],
        "started_at": started_at, "status": "DISPATCHED", **BOUNDARY,
    }


def build_terminal_receipt_body(*, correspondence: dict[str, Any],
                                operational_contract: dict[str, Any],
                                dispatch_receipt_root: str,
                                result: dict[str, Any],
                                ended_at: int) -> dict[str, Any]:
    correspondence = validate_correspondence(correspondence)
    result = validate_reference_result(result)
    require(correspondence.get("operational_contract_root")
            == operational_contract.get("contract_root"),
            "UGEL_CORRESPONDENCE_CONTRACT_MISMATCH")
    expected = correspondence.get("expected_result_root")
    require(result.get("result_root") == expected
            and expected == operational_contract.get("expected_result_root"),
            "UGEL_RESULT_BINDING_INVALID")
    require(type(ended_at) is int and not isinstance(ended_at, bool)
            and ended_at >= 0, "UGEL_TIME_INVALID")
    return {
        "schema": TERMINAL_SCHEMA,
        "operation_id": operational_contract["operation_id"],
        "contract_root": operational_contract["contract_root"],
        "dispatch_root": require_root(dispatch_receipt_root),
        "terminal_status": "COMPLETED", "result_root": expected,
        "output_bytes": len(canonical_bytes(result)), "completed_cases": 1,
        "observed_effect_classes": ["PROCESS"], "ended_at": ended_at,
        "receipt_nonce": root({
            "correspondence_root": correspondence["correspondence_root"],
            "result_root": expected, "ended_at": ended_at,
        }),
        **BOUNDARY,
    }

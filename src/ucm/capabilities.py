"""Versioned invocation route for the stable UCM capability registry."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import base64
import binascii

from uclop.canonical import exact_keys, require, root
from uclop.workbench_contracts import reject_raw_secrets

from .realization import (
    project_to_ucl_tessera,
    select_configuration,
    trace_preservation,
    validate_configuration,
    validate_contract,
)
from .system import (BOUNDARY, CAPABILITIES, CAPABILITY_PAYLOAD_FIELDS,
                     capability_registry, orientation)


def _seal(body: dict[str, Any]) -> dict[str, Any]:
    return {**body, "root": root(body)}


def _archive(value: Any) -> bytes:
    require(type(value) is str and bool(value), "UCM_ARCHIVE_BASE64_INVALID")
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as error:
        require(False, "UCM_ARCHIVE_BASE64_INVALID", detail=type(error).__name__)
    raise AssertionError("unreachable")


def invoke(request: Any) -> dict[str, Any]:
    """Dispatch a stable public request or refuse a separately staged effect."""
    item = exact_keys(request, {"schema", "surface", "payload", "request_id"})
    require(
        item["schema"] == "mosaic.ucm.request.v0.1"
        and type(item["request_id"]) is str and bool(item["request_id"])
        and item["surface"] in CAPABILITIES and type(item["payload"]) is dict,
        "UCM_REQUEST_INVALID",
    )
    surface, payload = item["surface"], item["payload"]
    semantic_seed_surfaces = {
        "VALIDATE_REALIZATION_CONTRACT", "CHECK_REALIZATION", "SELECT_REALIZATION",
        "PROJECT_TO_UCL_TESSERA", "TRACE_PRESERVATION",
    }
    if surface in semantic_seed_surfaces:
        allowed_paths = frozenset({("contract", "selection", "seed")})
    elif surface in {"VALIDATE_AMCAS", "COMPILE_AMCAS"}:
        allowed_paths = frozenset({("contract", "realization_contract", "selection", "seed")})
    elif surface in {"DERIVE_STAGE_I4_ELIGIBILITY",
                     "VALIDATE_STAGE_I4_RUN_CONTRACT",
                     "VALIDATE_STAGE_I4_OBSERVATION",
                     "DERIVE_TRUSTED_STAGE_I4_ELIGIBILITY",
                     "BUILD_STAGE_I4_EXACT_RUN_CONTRACT",
                     "BUILD_STAGE_I4_ANCHORED_RUN_CONTRACT"}:
        allowed_paths = frozenset({("review_archive_base64",)})
    elif surface == "VERIFY_OPERATIONAL_ARCHIVE":
        allowed_paths = frozenset({("archive_base64",)})
    else:
        allowed_paths = frozenset()
    reject_raw_secrets(payload, allowed_paths=allowed_paths)
    if surface == "ORIENT":
        exact_keys(payload, set()); result = orientation()
    elif surface == "DISCOVER_CAPABILITIES":
        exact_keys(payload, set()); result = capability_registry()
    elif surface == "VALIDATE_REALIZATION_CONTRACT":
        exact_keys(payload, {"contract"}); result = validate_contract(payload["contract"])
    elif surface == "CHECK_REALIZATION":
        exact_keys(payload, {"contract", "configuration"})
        result = validate_configuration(payload["contract"], payload["configuration"])
    elif surface == "SELECT_REALIZATION":
        exact_keys(payload, {"contract", "candidates"})
        result = select_configuration(payload["contract"], payload["candidates"])
    elif surface == "PROJECT_TO_UCL_TESSERA":
        exact_keys(payload, {"contract"}); result = project_to_ucl_tessera(payload["contract"])
    elif surface == "TRACE_PRESERVATION":
        exact_keys(payload, {"contract", "before", "after"})
        result = trace_preservation(payload["contract"], payload["before"], payload["after"])
    elif surface == "VALIDATE_AMCAS":
        from .amcas import validate_contract as validate_amcas
        exact_keys(payload, {"contract"}); result = validate_amcas(payload["contract"])
    elif surface == "COMPILE_AMCAS":
        from .amcas import compile_contract
        exact_keys(payload, {"contract"}); result = compile_contract(payload["contract"])
    elif surface == "INSPECT_MOSAIC_ID":
        from .identity import verify_passport
        exact_keys(payload, {"passport", "expected_mosaic_id"})
        result = verify_passport(payload["passport"], expected_mosaic_id=payload["expected_mosaic_id"])
    elif surface == "VERIFY_NATIVE_PROOF":
        from uclop.deductive_proofs import verify_proof
        exact_keys(payload, {"contract", "proof_bundle"})
        result = verify_proof(payload["contract"], payload["proof_bundle"])
    elif surface == "PROJECT_DASHBOARD":
        from uclop import project_intelligence as pi
        exact_keys(payload, {"project", "workspace"})
        require(type(payload["workspace"]) is str and bool(payload["workspace"]), "UCM_WORKSPACE_INVALID")
        result = pi.project_dashboard(payload["project"], Path(payload["workspace"]))
    elif surface == "PREPARE_AUTONOMOUS_PLAN":
        from uclop import autonomous_project_manager as apm
        exact_keys(payload, {"project", "changed_ids", "changed_paths", "objective"})
        result = apm.make_plan(payload["project"], payload["changed_ids"], payload["changed_paths"], objective=payload["objective"])
    elif surface == "EXPLAIN_CLAIM":
        from uclop.operational_explanation import make_explanation_graph
        exact_keys(payload, {"subject_root", "assertions", "edges", "proof_roots", "evidence_contracts", "accepted_contract_roots"})
        result = make_explanation_graph(**payload)
    elif surface == "VALIDATE_STAGE_I3_PLAN":
        from .stage3 import validate_plan
        exact_keys(payload, {"instruction", "plan"})
        result = validate_plan(payload["plan"], expected_instruction=payload["instruction"])
    elif surface == "DERIVE_STAGE_I4_ELIGIBILITY":
        from .stage4 import derive_eligibility
        exact_keys(payload, {"instruction", "plan", "review_archive_base64"})
        result = derive_eligibility(instruction=payload["instruction"],
            plan=payload["plan"], review_archive=_archive(payload["review_archive_base64"]))
    elif surface == "VALIDATE_STAGE_I4_RUN_CONTRACT":
        from .stage4 import validate_run_contract
        exact_keys(payload, {"eligibility", "instruction", "plan",
                             "review_archive_base64", "run_contract"})
        result = validate_run_contract(payload["run_contract"],
            expected_eligibility=payload["eligibility"],
            expected_plan=payload["plan"], expected_instruction=payload["instruction"],
            expected_review_archive=_archive(payload["review_archive_base64"]))
    elif surface == "VALIDATE_STAGE_I4_OBSERVATION":
        from .stage4 import validate_observation
        exact_keys(payload, {"eligibility", "instruction", "observation", "plan",
                             "review_archive_base64", "run_contract"})
        result = validate_observation(payload["observation"],
            expected_run_contract=payload["run_contract"],
            expected_eligibility=payload["eligibility"],
            expected_plan=payload["plan"], expected_instruction=payload["instruction"],
            expected_review_archive=_archive(payload["review_archive_base64"]))
    elif surface == "VALIDATE_NATIVE_HEADLESS_RUNNER_BINDING":
        from .native_runner import validate_binding
        exact_keys(payload, {"binding"})
        result = validate_binding(payload["binding"])
    elif surface == "DERIVE_TRUSTED_STAGE_I4_ELIGIBILITY":
        from .stage4_c3 import derive_eligibility
        exact_keys(payload, {"instruction", "plan", "review_archive_base64",
                             "review_policy"})
        result = derive_eligibility(instruction=payload["instruction"],
            plan=payload["plan"], review_archive=_archive(payload["review_archive_base64"]),
            review_policy=payload["review_policy"])
    elif surface == "BUILD_STAGE_I4_EXACT_RUN_CONTRACT":
        from .stage4_c3 import build_run_contract
        exact_keys(payload, {"eligibility", "instruction", "native_runner_binding",
                             "plan", "relation_case_map", "review_archive_base64",
                             "review_policy", "selection", "execution_context"})
        result = build_run_contract(eligibility=payload["eligibility"],
            instruction=payload["instruction"], plan=payload["plan"],
            review_archive=_archive(payload["review_archive_base64"]),
            review_policy=payload["review_policy"],
            relation_case_map=payload["relation_case_map"],
            execution_context=payload["execution_context"],
            native_runner_binding=payload["native_runner_binding"],
            selection=payload["selection"])
    elif surface == "BUILD_STAGE_I4_TERMINAL_REFUSAL":
        from .stage4_c3 import build_terminal_refusal
        exact_keys(payload, {"run_contract"})
        result = build_terminal_refusal(run_contract=payload["run_contract"])
    elif surface == "BUILD_NATIVE_HEADLESS_RUNNER_PREFLIGHT":
        from .native_runner import build_preflight
        exact_keys(payload, {"binding", "execution_authorized", "execution_context_root",
                             "requested_effect_classes", "run_contract_root"})
        result = build_preflight(run_contract_root=payload["run_contract_root"],
            execution_context_root=payload["execution_context_root"],
            binding=payload["binding"],
            requested_effect_classes=payload["requested_effect_classes"],
            execution_authorized=payload["execution_authorized"])
    elif surface == "VALIDATE_NATIVE_HEADLESS_RUNNER_RECEIPT":
        from .native_runner import validate_terminal_receipt
        exact_keys(payload, {"preflight", "receipt"})
        result = validate_terminal_receipt(payload["receipt"],
                                           expected_preflight=payload["preflight"])
    elif surface == "DERIVE_STAGE_I4_OPERATION_STATE":
        from .operation_state import derive_operation_state
        exact_keys(payload, {"events", "operation_id", "run_contract_root"})
        result = derive_operation_state(operation_id=payload["operation_id"],
            run_contract_root=payload["run_contract_root"], events=payload["events"])
    elif surface == "VALIDATE_STAGE_I4_OPERATION_STATE":
        from .operation_state import validate_operation_state
        exact_keys(payload, {"state"})
        result = validate_operation_state(payload["state"])
    elif surface == "BUILD_STAGE_I4_ANCHORED_RUN_CONTRACT":
        from .stage4_c4 import build_run_contract
        exact_keys(payload, {"eligibility", "instruction", "native_runner_binding",
            "plan", "relation_case_map", "review_archive_base64", "review_policy",
            "selection", "execution_context", "trust_anchors",
            "expected_trust_anchors_root", "execution_authority_policy"})
        result = build_run_contract(eligibility=payload["eligibility"],
            instruction=payload["instruction"], plan=payload["plan"],
            review_archive=_archive(payload["review_archive_base64"]),
            review_policy=payload["review_policy"],
            relation_case_map=payload["relation_case_map"],
            execution_context=payload["execution_context"],
            native_runner_binding=payload["native_runner_binding"],
            selection=payload["selection"], trust_anchors=payload["trust_anchors"],
            expected_trust_anchors_root=payload["expected_trust_anchors_root"],
            execution_authority_policy=payload["execution_authority_policy"])
    elif surface == "BUILD_STAGE_I4_AUTHORITY_SAFE_PREFLIGHT":
        from .native_runner_c4 import build_preflight
        exact_keys(payload, {"run_contract", "trust_anchors",
            "expected_trust_anchors_root", "execution_authority_policy"})
        result = build_preflight(run_contract=payload["run_contract"],
            trust_anchors=payload["trust_anchors"],
            expected_trust_anchors_root=payload["expected_trust_anchors_root"],
            execution_authority_policy=payload["execution_authority_policy"])
    elif surface == "BUILD_STAGE_I4_RECEIPTED_REFUSAL":
        from .stage4_c4 import build_terminal_refusal
        exact_keys(payload, {"run_contract", "expected_trust_anchors_root"})
        result = build_terminal_refusal(run_contract=payload["run_contract"],
            expected_trust_anchors_root=payload["expected_trust_anchors_root"])
    elif surface == "DERIVE_STAGE_I4_RECEIPT_STATE":
        from .operation_state_c4 import derive_operation_state
        exact_keys(payload, {"events", "operation_id", "run_contract_root"})
        result = derive_operation_state(operation_id=payload["operation_id"],
            run_contract_root=payload["run_contract_root"], events=payload["events"])
    elif surface == "VALIDATE_STAGE_I4_RECEIPT_STATE":
        from .operation_state_c4 import validate_operation_state
        exact_keys(payload, {"state"})
        result = validate_operation_state(payload["state"])
    elif surface == "BUILD_OPERATIONAL_CONTRACT":
        from .operation_gateway import build_operation_contract
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_operation_contract(**payload)
    elif surface == "PREPARE_OPERATIONAL_GATEWAY":
        from .operation_gateway import gateway_from_workspace
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        gateway = gateway_from_workspace(payload["workspace"], payload["progress_path"])
        result = gateway.prepare(payload["contract"],
            expected_issuer_public_key_hex=payload["expected_issuer_public_key_hex"],
            expected_jurisdiction_root=payload["expected_jurisdiction_root"],
            expected_revocation_registry_root=payload["expected_revocation_registry_root"])
    elif surface == "RECORD_OPERATIONAL_DISPATCH":
        from .operation_gateway import gateway_from_workspace
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = gateway_from_workspace(payload["workspace"], payload["progress_path"]).record_dispatch(
            payload["operation_id"], payload["receipt"])
    elif surface == "RECORD_OPERATIONAL_TERMINAL":
        from .operation_gateway import gateway_from_workspace
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = gateway_from_workspace(payload["workspace"], payload["progress_path"]).record_terminal(
            payload["operation_id"], payload["receipt"])
    elif surface == "MARK_OPERATIONAL_UNCERTAIN":
        from .operation_gateway import gateway_from_workspace
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = gateway_from_workspace(payload["workspace"], payload["progress_path"]).mark_uncertain(
            payload["operation_id"], reason_code=payload["reason_code"])
    elif surface == "RECONCILE_OPERATIONAL_OUTCOME":
        from .operation_gateway import gateway_from_workspace
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = gateway_from_workspace(payload["workspace"], payload["progress_path"]).reconcile(
            payload["operation_id"], payload["receipt"])
    elif surface == "CANCEL_OPERATIONAL_GATEWAY":
        from .operation_gateway import gateway_from_workspace
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = gateway_from_workspace(payload["workspace"], payload["progress_path"]).cancel(
            payload["operation_id"], reason_code=payload["reason_code"])
    elif surface == "INSPECT_OPERATIONAL_STATE":
        from .operation_gateway import gateway_from_workspace
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = gateway_from_workspace(payload["workspace"]).state(payload["operation_id"])
    elif surface == "BUILD_OPERATIONAL_PROOF":
        from .operation_gateway import gateway_from_workspace
        from .operation_proofs import build_operation_proof_bundle
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        gateway = gateway_from_workspace(payload["workspace"])
        result = build_operation_proof_bundle(operation_id=payload["operation_id"],
            events=gateway.journal.verify(),
            expected_issuer_public_key_hex=payload["expected_issuer_public_key_hex"],
            expected_jurisdiction_root=payload["expected_jurisdiction_root"],
            expected_revocation_registry_root=payload["expected_revocation_registry_root"])
    elif surface == "EXPORT_OPERATIONAL_ARCHIVE":
        from .operation_archive import build_operation_archive
        from .operation_gateway import gateway_from_workspace
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        raw = build_operation_archive(gateway_from_workspace(payload["workspace"]),
            operation_id=payload["operation_id"],
            expected_issuer_public_key_hex=payload["expected_issuer_public_key_hex"],
            expected_jurisdiction_root=payload["expected_jurisdiction_root"],
            expected_revocation_registry_root=payload["expected_revocation_registry_root"])
        result = {"schema": "mosaic.ucm.operational-archive-base64.v0.1",
                  "archive_base64": base64.b64encode(raw).decode("ascii"),
                  "archive_sha256": __import__("hashlib").sha256(raw).hexdigest(),
                  **BOUNDARY}
    elif surface == "VERIFY_OPERATIONAL_ARCHIVE":
        from .operation_archive import verify_operation_archive
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = verify_operation_archive(_archive(payload["archive_base64"]),
            expected_issuer_public_key_hex=payload["expected_issuer_public_key_hex"],
            expected_jurisdiction_root=payload["expected_jurisdiction_root"],
            expected_revocation_registry_root=payload["expected_revocation_registry_root"])
    elif surface == "RECOVER_OPERATIONAL_JOURNAL":
        from .operation_gateway import gateway_from_workspace
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = gateway_from_workspace(payload["workspace"], payload["progress_path"]).recover_stale_lock(
            expected_head=payload["expected_head"])
    else:
        require(False, "UCM_SEPARATE_STAGE_REQUIRED", detail=surface)
    return _seal({
        "schema": "mosaic.ucm.response.v0.1",
        "request_root": root(item),
        "surface": surface,
        "result": result,
        "effect_scope": next(row["effect_scope"] for row in capability_registry()["surfaces"] if row["name"] == surface),
        **BOUNDARY,
    })

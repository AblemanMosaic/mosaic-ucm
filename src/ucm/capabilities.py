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
from .system import (BOUNDARY, CAPABILITIES, CAPABILITY_DEFINITIONS,
                     CAPABILITY_PAYLOAD_FIELDS, LEGACY_SURFACE_REPLACEMENTS,
                     capability_registry, legacy_capability_registry, orientation)


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
    require(type(request) is dict, "UCM_REQUEST_INVALID")
    schema = request.get("schema")
    if schema == "mosaic.ucm.request.v0.1":
        # The legacy envelope is retained as an explicitly AUTHORING-bound
        # compatibility route.  It no longer implies access to every surface.
        item = exact_keys(request, {"schema", "surface", "payload", "request_id"})
        from .profiles import validate_profile_selection
        selection = validate_profile_selection({
            "schema": "mosaic.ucm.product-profile-selection.v0.1",
            "profile_id": "AUTHORING",
            "capability_registry_root": capability_registry()["root"],
        })
    elif schema == "mosaic.ucm.request.v0.2":
        item = exact_keys(request, {"schema", "surface", "payload", "request_id",
                                    "profile_selection"})
        from .profiles import validate_profile_selection
        selection = validate_profile_selection(item["profile_selection"])
    else:
        require(False, "UCM_REQUEST_SCHEMA_INVALID")
    require(
        type(item["request_id"]) is str and bool(item["request_id"])
        and item["surface"] in CAPABILITIES and type(item["payload"]) is dict,
        "UCM_REQUEST_INVALID",
    )
    surface, payload = item["surface"], item["payload"]
    if surface in LEGACY_SURFACE_REPLACEMENTS:
        require(selection["profile_id"] == "COMPATIBILITY",
                "UCM_LEGACY_SURFACE_REQUIRES_COMPATIBILITY_PROFILE",
                detail=f"{surface}->{LEGACY_SURFACE_REPLACEMENTS[surface]}")
    from .profiles import profile_allows_surface
    profile_check = profile_allows_surface(selection["profile_id"], surface)
    require(profile_check["status"] == "PASS_ALLOWED",
            "UCM_PROFILE_SURFACE_REFUSED",
            detail=f"{selection['profile_id']}:{surface}")
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
    elif surface == "PREPARE_MOSAICOS_M1":
        allowed_paths = frozenset({("m0_archive_base64",)})
    else:
        allowed_paths = frozenset()
    reject_raw_secrets(payload, allowed_paths=allowed_paths)
    if surface == "ORIENT":
        exact_keys(payload, set()); result = orientation()
    elif surface == "DISCOVER_CAPABILITIES":
        exact_keys(payload, set()); result = capability_registry()
    elif surface == "DISCOVER_LEGACY_CAPABILITIES":
        exact_keys(payload, set()); result = legacy_capability_registry()
    elif surface == "DISCOVER_PRODUCT_PROFILES":
        from .profiles import profile_registry
        exact_keys(payload, set()); result = profile_registry()
    elif surface == "PLAN_INCREMENTAL_HOTFIX":
        from .incremental_hotfix import build_bound_hotfix_plan
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_bound_hotfix_plan(**payload)
    elif surface == "VALIDATE_INCREMENTAL_HOTFIX":
        from .incremental_hotfix import validate_hotfix_result
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = validate_hotfix_result(**payload)
    elif surface == "COMPILE_DEPENDENCY_GRAPH":
        from .dependency_graph import build_graph
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_graph(**payload)
    elif surface == "VERIFY_DEPENDENCY_GRAPH":
        from .dependency_graph import verify_graph
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = verify_graph(**payload)
    elif surface == "BUILD_DEPENDENCY_SNAPSHOT":
        from .dependency_graph import build_snapshot
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_snapshot(**payload)
    elif surface == "APPLY_DEPENDENCY_SNAPSHOT_DELTA":
        from .dependency_graph import apply_snapshot_delta
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = apply_snapshot_delta(**payload)
    elif surface == "BUILD_DEPENDENCY_PRODUCER_RECEIPT":
        from .dependency_graph import build_producer_receipt
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_producer_receipt(**payload)
    elif surface == "BUILD_DEPENDENCY_REUSE_ADMISSION":
        from .dependency_graph import build_reuse_admission
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_reuse_admission(**payload)
    elif surface == "EVALUATE_DEPENDENCY_GRAPH":
        from .dependency_graph import evaluate_graph
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = evaluate_graph(**payload)
    elif surface == "DIFF_DEPENDENCY_EVALUATIONS":
        from .dependency_graph import compare_evaluations
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = compare_evaluations(**payload)
    elif surface == "EXPLAIN_DEPENDENCY_NODE":
        from .dependency_graph import explain_node
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = explain_node(**payload)
    elif surface == "BUILD_DEPENDENCY_PORTABLE_CLOSURE":
        from .dependency_graph import build_portable_closure
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_portable_closure(**payload)
    elif surface == "VERIFY_DEPENDENCY_PORTABLE_CLOSURE":
        from .dependency_graph import verify_portable_closure
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = verify_portable_closure(**payload)
    elif surface in {
        "DISCOVER_DEPENDENCY_ADAPTERS", "COMPILE_PROJECT_DEPENDENCY_GRAPH",
        "BUILD_CONTENT_REFERENCE_SNAPSHOT", "BUILD_GOVERNED_REPLAN_SET",
        "FOLD_DEPENDENCY_JOURNAL_UPDATES", "BUILD_POLICY_PACK_DEPENDENCY_PLAN",
        "PREPARE_PIPPI_DEPENDENCY_TURN",
        "RECONCILE_PIPPI_DEPENDENCY_TURN", "PROJECT_DEPENDENCY_OBSERVATORY",
        "BUILD_AMCAS_DEPENDENCY_PROFILE", "PREPARE_COURTHOUSE_DEPENDENCY_BINDING",
        "PROJECT_DEPENDENCY_EFFECT_HISTORY", "BUILD_DEPENDENCY_STORAGE_INDEXES",
        "BUILD_DEPENDENCY_CHECK_PLAN", "BUILD_DEPENDENCY_COMPILER_PROOF_BINDING",
        "BUILD_C_DEPENDENCY_ENVELOPE", "BUILD_DEPENDENCY_ARCHITECTURE_TRACE",
        "CAPTURE_DEPENDENCY_OBSERVATION", "BUILD_DEPENDENCY_BENCHMARK_REPORT",
        "ASSESS_DEPENDENCY_REUSE_GRADUATION",
    }:
        from . import dependency_adapters as adapters
        routes = {
            "DISCOVER_DEPENDENCY_ADAPTERS": adapters.dependency_adapter_registry,
            "COMPILE_PROJECT_DEPENDENCY_GRAPH": adapters.compile_project_dependency_graph,
            "BUILD_CONTENT_REFERENCE_SNAPSHOT": adapters.build_content_reference_snapshot,
            "BUILD_GOVERNED_REPLAN_SET": adapters.build_governed_replan_set,
            "FOLD_DEPENDENCY_JOURNAL_UPDATES": adapters.fold_dependency_journal_updates,
            "BUILD_POLICY_PACK_DEPENDENCY_PLAN": adapters.build_policy_pack_dependency_plan,
            "PREPARE_PIPPI_DEPENDENCY_TURN": adapters.build_dependency_aware_turn,
            "RECONCILE_PIPPI_DEPENDENCY_TURN": adapters.reconcile_dependency_turn,
            "PROJECT_DEPENDENCY_OBSERVATORY": adapters.project_dependency_observatory,
            "BUILD_AMCAS_DEPENDENCY_PROFILE": adapters.build_amcas_dependency_profile,
            "PREPARE_COURTHOUSE_DEPENDENCY_BINDING": adapters.prepare_courthouse_dependency_binding,
            "PROJECT_DEPENDENCY_EFFECT_HISTORY": adapters.project_effect_history,
            "BUILD_DEPENDENCY_STORAGE_INDEXES": adapters.build_storage_admission_indexes,
            "BUILD_DEPENDENCY_CHECK_PLAN": adapters.build_development_check_plan,
            "BUILD_DEPENDENCY_COMPILER_PROOF_BINDING": adapters.build_compiler_proof_binding,
            "BUILD_C_DEPENDENCY_ENVELOPE": adapters.build_c_dependency_envelope,
            "BUILD_DEPENDENCY_ARCHITECTURE_TRACE": adapters.build_architecture_trace,
            "CAPTURE_DEPENDENCY_OBSERVATION": adapters.capture_observation,
            "BUILD_DEPENDENCY_BENCHMARK_REPORT": adapters.build_benchmark_report,
            "ASSESS_DEPENDENCY_REUSE_GRADUATION": adapters.assess_reuse_graduation,
        }
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = routes[surface](**payload)
    elif surface == "BUILD_DEVELOPMENT_STANDARDS_CATALOG":
        from .development_standards import build_standards_catalog
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_standards_catalog(**payload)
    elif surface == "EVALUATE_DEVELOPMENT_STANDARDS":
        from .development_standards import evaluate_standards
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = evaluate_standards(**payload)
    elif surface == "DISCOVER_C_CODING_STANDARD":
        from .c_preflight import c_coding_standard
        exact_keys(payload, set())
        result = c_coding_standard()
    elif surface == "PREFLIGHT_C_CHANGE":
        from .c_preflight import build_c_change_preflight
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_c_change_preflight(**payload)
    elif surface == "EVALUATE_C_CHANGE_RESULTS":
        from .c_preflight import evaluate_c_check_results
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = evaluate_c_check_results(**payload)
    elif surface == "DISCOVER_NATIVE_CORE_PROFILE":
        from .native_core import native_core_profile
        exact_keys(payload, set())
        result = native_core_profile()
    elif surface == "COMPILE_NATIVE_CORE_PROGRAM":
        from .native_core import lower_native_program, validate_native_program
        exact_keys(payload, {"program"})
        program = validate_native_program(payload["program"])
        projection = lower_native_program(program)
        result = {
            "schema": "mosaic.ucm.native-core-projection.v0.1",
            "program_root": program["program_root"],
            "projection_base64": base64.b64encode(projection).decode("ascii"),
            "projection_sha256": __import__("hashlib").sha256(projection).hexdigest(),
            **BOUNDARY,
        }
    elif surface == "EXECUTE_NATIVE_CORE_REFERENCE":
        from .native_core import execute_native_reference
        exact_keys(payload, {"program"})
        result = {"schema": "mosaic.ucm.native-core-reference-result.v0.1",
                  "execution": execute_native_reference(payload["program"]),
                  **BOUNDARY}
    elif surface == "BUILD_PIPPI_CONTEXT":
        from .pippi import build_pippi_context
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_pippi_context(**payload)
    elif surface == "BUILD_PIPPI_HOST_ADAPTER_POLICY":
        from .pippi_host import build_host_adapter_policy
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_host_adapter_policy(**payload)
    elif surface == "BUILD_ATTESTED_PIPPI_CONTEXT":
        from .pippi import build_attested_pippi_context
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_attested_pippi_context(**payload)
    elif surface == "BUILD_PIPPI_HOST_LAUNCH_PROPOSAL":
        from .pippi_host import build_host_launch_proposal
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_host_launch_proposal(**payload)
    elif surface == "VALIDATE_PIPPI_HOST_LAUNCH_RESULT":
        from .pippi_host import validate_host_launch_result
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = validate_host_launch_result(**payload)
    elif surface == "BUILD_PIPPI_INTEGRATION_REGISTRY":
        from .pippi_integrations import build_integration_availability_registry
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_integration_availability_registry(**payload)
    elif surface == "BIND_PIPPI_EXTERNAL_INTEGRATION":
        from .pippi_integrations import bind_external_integration
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = bind_external_integration(**payload)
    elif surface == "BUILD_PIPPI_MODEL_DRAFT":
        from .pippi import build_model_draft
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_model_draft(**payload)
    elif surface == "EVALUATE_PIPPI_DRAFT":
        from .pippi import build_pippi_decision
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_pippi_decision(**payload)
    elif surface == "BUILD_PIPPI_HUMAN_PROJECTION":
        from .pippi import build_human_projection
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_human_projection(**payload)
    elif surface == "BUILD_PIPPI_CONSTITUTIONAL_EXCEPTION":
        from .pippi import build_constitutional_exception
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_constitutional_exception(**payload)
    elif surface == "BUILD_PIPPI_TURN_ENVELOPE":
        from .pippi import build_turn_envelope
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_turn_envelope(**payload)
    elif surface == "DISCOVER_PIPPI_MEDIATION_LIBRARY":
        from .pippi_adaptive import mediation_library
        exact_keys(payload, set())
        result = mediation_library()
    elif surface in {
        "DISCOVER_CONSTITUTIONAL_STANDARDS_ATLAS", "DISCOVER_PIPPI_PIPELINE_MODEL",
        "EXPLAIN_PIPPI_STANDARD_RULE", "EXPLAIN_PIPPI_PIPELINE_TRANSITION",
        "EXPLAIN_PIPPI_CONTEXT_SELECTION", "BUILD_PIPPI_COLLABORATOR_BINDING",
        "DISCOVER_PIPPI_CREDENTIAL_BROKER_POLICY", "BUILD_PIPPI_CREDENTIAL_REFERENCE",
        "BUILD_SIGNED_CONSTITUTIONAL_CHANGE_CAPSULE",
        "VERIFY_SIGNED_CONSTITUTIONAL_CHANGE_CAPSULE", "BUILD_PIPPI_STORAGE_LOCATOR",
        "BUILD_SIGNED_STORAGE_PUBLICATION_RECEIPT",
        "VERIFY_SIGNED_STORAGE_PUBLICATION_RECEIPT",
        "BUILD_SIGNED_STORAGE_RETRIEVAL_RECEIPT",
        "VERIFY_SIGNED_STORAGE_RETRIEVAL_RECEIPT", "BUILD_PIPPI_CCP_TRANSITION_BINDING",
    }:
        from . import pippi_constitution as constitution
        routes = {
            "DISCOVER_CONSTITUTIONAL_STANDARDS_ATLAS": constitution.build_constitutional_standards_atlas,
            "DISCOVER_PIPPI_PIPELINE_MODEL": constitution.build_pipeline_model,
            "EXPLAIN_PIPPI_STANDARD_RULE": constitution.explain_standard_rule,
            "EXPLAIN_PIPPI_PIPELINE_TRANSITION": constitution.explain_pipeline_transition,
            "EXPLAIN_PIPPI_CONTEXT_SELECTION": constitution.explain_context_selection,
            "BUILD_PIPPI_COLLABORATOR_BINDING": constitution.build_collaborator_binding,
            "DISCOVER_PIPPI_CREDENTIAL_BROKER_POLICY": constitution.credential_broker_policy,
            "BUILD_PIPPI_CREDENTIAL_REFERENCE": constitution.build_credential_reference,
            "BUILD_SIGNED_CONSTITUTIONAL_CHANGE_CAPSULE": constitution.build_signed_change_capsule,
            "VERIFY_SIGNED_CONSTITUTIONAL_CHANGE_CAPSULE": constitution.validate_signed_change_capsule,
            "BUILD_PIPPI_STORAGE_LOCATOR": constitution.build_storage_locator,
            "BUILD_SIGNED_STORAGE_PUBLICATION_RECEIPT": constitution.build_signed_publication_receipt,
            "VERIFY_SIGNED_STORAGE_PUBLICATION_RECEIPT": constitution.validate_signed_publication_receipt,
            "BUILD_SIGNED_STORAGE_RETRIEVAL_RECEIPT": constitution.build_signed_retrieval_receipt,
            "VERIFY_SIGNED_STORAGE_RETRIEVAL_RECEIPT": constitution.validate_signed_retrieval_receipt,
            "BUILD_PIPPI_CCP_TRANSITION_BINDING": constitution.build_ccp_transition_binding,
        }
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        if surface.startswith("DISCOVER_"):
            result = routes[surface]()
        elif surface == "VERIFY_SIGNED_CONSTITUTIONAL_CHANGE_CAPSULE":
            result = routes[surface](payload["value"])
        elif surface == "VERIFY_SIGNED_STORAGE_RETRIEVAL_RECEIPT":
            result = routes[surface](payload["value"],
                                     publication_receipt=payload["publication_receipt"])
        else:
            result = routes[surface](**payload)
    elif surface == "NEGOTIATE_PIPPI_HOST_MODE":
        from .pippi_adaptive import negotiate_host_mode
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = negotiate_host_mode(**payload)
    elif surface == "PREPARE_PIPPI_TURN":
        from .pippi_adaptive import prepare_turn
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = prepare_turn(**payload)
    elif surface in {"DISCOVER_PIPPI_TURN_REQUIREMENTS", "BUILD_PIPPI_TURN_RECORD", "PROJECT_PIPPI_TURN_RECORD"}:
        from .pippi_turn_record import reporting_requirements, build_turn_record, project_turn_record
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        routes = {"DISCOVER_PIPPI_TURN_REQUIREMENTS": reporting_requirements,
                  "BUILD_PIPPI_TURN_RECORD": build_turn_record,
                  "PROJECT_PIPPI_TURN_RECORD": project_turn_record}
        result = routes[surface](**payload)
    elif surface == "RECONCILE_PIPPI_TURN_RECORD":
        from .pippi_turn_workflow import reconcile_common_turn
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = reconcile_common_turn(**payload)
    elif surface in {"DISCOVER_PIPPI_CMBA_BINDING", "ASSESS_PIPPI_CMBA_TURN", "VERIFY_PIPPI_CMBA_TURN"}:
        from .pippi_cmba import discover_cmba_binding, build_cmba_turn_assessment, validate_cmba_turn_assessment
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        routes = {"DISCOVER_PIPPI_CMBA_BINDING": discover_cmba_binding,
                  "ASSESS_PIPPI_CMBA_TURN": build_cmba_turn_assessment,
                  "VERIFY_PIPPI_CMBA_TURN": validate_cmba_turn_assessment}
        result = routes[surface](**payload)
    elif surface in {"DISCOVER_PIPPI_CMBA_COMPOSITE_PROFILE",
                     "BUILD_PIPPI_CMBA_COMPOSITE_ASSESSMENT",
                     "VERIFY_PIPPI_CMBA_COMPOSITE_ASSESSMENT"}:
        from .pippi_cmba_composite import (composite_profile,
            build_composite_assessment, validate_composite_assessment)
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        routes = {"DISCOVER_PIPPI_CMBA_COMPOSITE_PROFILE": composite_profile,
                  "BUILD_PIPPI_CMBA_COMPOSITE_ASSESSMENT": build_composite_assessment,
                  "VERIFY_PIPPI_CMBA_COMPOSITE_ASSESSMENT": validate_composite_assessment}
        result = routes[surface]() if surface.startswith("DISCOVER_") else routes[surface](**payload)
    elif surface == "BUILD_PIPPI_TURN_REPORT":
        from .pippi_adaptive import build_turn_report
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_turn_report(**payload)
    elif surface == "RECONCILE_PIPPI_TURN":
        from .pippi_adaptive import reconcile_turn
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = reconcile_turn(**payload)
    elif surface == "BUILD_PIPPI_PROJECT_CAPSULE":
        from .pippi_adaptive import build_project_capsule
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_project_capsule(**payload)
    elif surface == "VERIFY_PIPPI_PROJECT_CAPSULE":
        from .pippi_adaptive import verify_project_capsule
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = verify_project_capsule(**payload)
    elif surface == "INSPECT_PIPPI_INTERFACE_CONFORMANCE":
        from .pippi_adaptive import interface_conformance
        exact_keys(payload, set())
        result = interface_conformance()
    elif surface == "DISCOVER_PIPPI_PACK_REGISTRY":
        from .pippi_packs import pack_registry
        exact_keys(payload, set())
        result = pack_registry()
    elif surface == "BUILD_PIPPI_INSTALL_PLAN":
        from .pippi_packs import build_install_plan
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_install_plan(**payload)
    elif surface == "EXPLAIN_PIPPI_PROJECT_PORTABILITY":
        from .pippi_packs import explain_project_portability
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = explain_project_portability(**payload)
    elif surface == "BUILD_PIPPI_EXECUTION_CONTEXT":
        from .pippi_portability import build_execution_context
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_execution_context(**payload)
    elif surface == "DISCOVER_PIPPI_PORTABILITY_POLICY":
        from .pippi_portability import portability_policy
        exact_keys(payload, set())
        result = portability_policy()
    elif surface == "BUILD_PIPPI_PORTABILITY_WITNESS":
        from .pippi_portability import build_portability_witness
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_portability_witness(**payload)
    elif surface == "EVALUATE_PIPPI_PORTABILITY_GATE":
        from .pippi_portability import evaluate_portability_gate
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = evaluate_portability_gate(**payload)
    elif surface == "INSPECT_PIPPI_PORTABLE_SOURCE":
        from .pippi_portability import inspect_portable_python_sources
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = inspect_portable_python_sources(**payload)
    elif surface == "VERIFY_TRANSTEMPORAL_REVISION":
        from pathlib import Path
        from .transtemporal_archive import verify_revision
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = verify_revision(repository=Path(payload["repository"]), revision=payload["revision"])
    elif surface == "DIFF_TRANSTEMPORAL_REVISIONS":
        from pathlib import Path
        from .transtemporal_archive import diff_revisions
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = diff_revisions(repository=Path(payload["repository"]), before=payload["before"], after=payload["after"])
    elif surface == "INSPECT_TRANSTEMPORAL_STORAGE":
        from pathlib import Path
        from .transtemporal_archive import storage_report
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = storage_report(repository=Path(payload["repository"]))
    elif surface == "BUILD_SEMCRYS_TRANSTEMPORAL_PLAN":
        from pathlib import Path
        from .transtemporal_archive import build_semcrys_plan
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_semcrys_plan(repository=Path(payload["repository"]),
            revision=payload["revision"], semcrys_manifest_root=payload["semcrys_manifest_root"],
            memory_vault_binding_root=payload["memory_vault_binding_root"])
    elif surface == "BUILD_PIPPI_OPERATOR_KIT_CONTRACT":
        from .pippi_reviews import build_operator_kit_contract
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_operator_kit_contract(**payload)
    elif surface == "VERIFY_PIPPI_OPERATOR_KIT_CONTRACT":
        from .pippi_reviews import validate_operator_kit_contract
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        value = validate_operator_kit_contract(payload["value"])
        result = {"schema": "mosaic.ucm.pippi-operator-kit-verification.v0.1",
                  "status": "PASS", "operator_kit_root": value["operator_kit_root"],
                  **BOUNDARY}
    elif surface == "BUILD_DEVELOPMENT_OBSERVATORY":
        from .development_observatory import build_development_observatory
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_development_observatory(**payload)
    elif surface == "PROJECT_DEVELOPMENT_OBSERVATORY":
        from .development_observatory import project_development_observatory
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = project_development_observatory(**payload)
    elif surface == "BUILD_DKN_LOCALITY_BINDING":
        from .process_governance import build_dkn_locality_binding
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_dkn_locality_binding(**payload)
    elif surface == "BUILD_EXACT_EXECUTION_CAPSULE":
        from .process_governance import build_exact_execution_capsule
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_exact_execution_capsule(**payload)
    elif surface == "BUILD_ARTIFACT_PRODUCER_RECEIPT":
        from .process_governance import build_artifact_producer_receipt
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_artifact_producer_receipt(**payload)
    elif surface == "BUILD_PROCESS_BASELINE":
        from .process_governance import build_process_baseline
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_process_baseline(**payload)
    elif surface == "BUILD_PROCESS_MILESTONE":
        from .process_governance import build_process_milestone
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_process_milestone(**payload)
    elif surface == "ASSESS_PROCESS_MILESTONE":
        from .process_governance import assess_process_milestone
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = assess_process_milestone(**payload)
    elif surface == "RECORD_PROCESS_MILESTONE_DECISION":
        from .process_governance import record_process_milestone_decision
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = record_process_milestone_decision(**payload)
    elif surface == "BUILD_PROCESS_CHECKPOINT":
        from .process_governance import build_process_checkpoint
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_process_checkpoint(**payload)
    elif surface == "BUILD_PROCESS_REPLAN":
        from .process_governance import build_governed_replan
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_governed_replan(**payload)
    elif surface == "BUILD_PROCESS_STANDARDS_SCHEDULE":
        from .process_governance import build_process_standards_schedule
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_process_standards_schedule(**payload)
    elif surface == "BUILD_PROCESS_OBSERVATORY":
        from .process_governance import build_process_observatory
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_process_observatory(**payload)
    elif surface == "BUILD_COURTHOUSE_PROCESS_BINDING":
        from .process_governance import build_courthouse_process_binding
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_courthouse_process_binding(**payload)
    elif surface == "BUILD_PROCESS_THR_MANIFEST":
        from .process_governance import build_process_thr_manifest
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_process_thr_manifest(**payload)
    elif surface == "BUILD_SEMANTIC_PASSAGE":
        from .semantic_passage import build_semantic_passage
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_semantic_passage(**payload)
    elif surface == "BUILD_SEMANTIC_CLARIFICATION":
        from .semantic_passage import build_clarification_request
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_clarification_request(**payload)
    elif surface == "RESOLVE_SEMANTIC_PASSAGE":
        from .semantic_passage import resolve_semantic_passage
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = resolve_semantic_passage(**payload)
    elif surface == "BUILD_CONSTITUTIONAL_LAUNCH_CONTRACT":
        from .constitutional_launcher import build_launch_contract
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_launch_contract(**payload)
    elif surface == "BUILD_CONSTITUTIONAL_LAUNCH_OBSERVATION":
        from .constitutional_launcher import build_launch_observation
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_launch_observation(**payload)
    elif surface == "DERIVE_CONSTITUTIONAL_LAUNCH_STATE":
        from .constitutional_launcher import derive_launch_state
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = derive_launch_state(**payload)
    elif surface == "BUILD_BEHAVIORAL_HARNESS_CONTRACT":
        from .behavioral_harness import build_harness_contract
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_harness_contract(**payload)
    elif surface == "BUILD_BEHAVIORAL_TRANSITION_RECEIPT":
        from .behavioral_harness import build_transition_receipt
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_transition_receipt(**payload)
    elif surface == "NEGOTIATE_FEATURE_LEVEL":
        from .evolution import negotiate_feature_level
        exact_keys(payload, {"descriptor"})
        result = negotiate_feature_level(payload["descriptor"])
    elif surface == "BUILD_CONTRACT_LIFECYCLE_RECEIPT":
        from .lifecycle import build_lifecycle_receipt
        exact_keys(payload, {"contract_root", "from_state", "to_state",
                             "predecessor_receipt_root", "evidence_roots"})
        result = build_lifecycle_receipt(**payload)
    elif surface == "LINT_REALIZATION_CONTRACT":
        from .authoring import lint_realization_contract
        exact_keys(payload, {"contract"})
        result = lint_realization_contract(payload["contract"])
    elif surface == "LINT_AMCAS_CONTRACT":
        from .authoring import lint_amcas_contract
        exact_keys(payload, {"contract"})
        result = lint_amcas_contract(payload["contract"])
    elif surface == "DIFF_SEMANTIC_CONTRACTS":
        from .authoring import semantic_contract_diff
        exact_keys(payload, {"before", "after"})
        result = semantic_contract_diff(payload["before"], payload["after"])
    elif surface == "DIFF_CONTRACT_DOMAINS":
        from .contract_workbench import domain_contract_diff
        exact_keys(payload, {"before", "after"})
        result = domain_contract_diff(payload["before"], payload["after"])
    elif surface == "INITIALIZE_REALIZATION_CONTRACT":
        from .contract_workbench import initialize_realization_contract
        exact_keys(payload, {"contract_id", "subject_id", "subject_root", "description"})
        result = initialize_realization_contract(**payload)
    elif surface == "COMPILE_CONTRACT_AUTHORING_PROFILE":
        from .contract_workbench import compile_authoring_profile
        exact_keys(payload, {"source"})
        result = compile_authoring_profile(payload["source"])
    elif surface == "INITIALIZE_AMCAS_CONTRACT":
        from .contract_workbench import initialize_amcas_contract
        exact_keys(payload, {"integration_id", "application_id", "application_name",
                             "subject_root", "manifest_root", "realization_contract"})
        result = initialize_amcas_contract(**payload)
    elif surface == "DOCTOR_CONTRACT":
        from .contract_workbench import doctor_contract
        exact_keys(payload, {"kind", "contract"})
        result = doctor_contract(payload["kind"], payload["contract"])
    elif surface == "CLASSIFY_CONTRACT_COMPATIBILITY":
        from .contract_workbench import classify_contract_compatibility
        exact_keys(payload, {"predecessor", "successor", "known_roots"})
        result = classify_contract_compatibility(**payload)
    elif surface == "EXPLAIN_REALIZATION_SELECTION":
        from .contract_workbench import explain_selection
        exact_keys(payload, {"contract", "candidates"})
        result = explain_selection(payload["contract"], payload["candidates"])
    elif surface == "DIFF_REALIZATION_CONFIGURATIONS":
        from .contract_workbench import compare_configurations
        exact_keys(payload, {"contract", "left", "right"})
        result = compare_configurations(payload["contract"], payload["left"], payload["right"])
    elif surface == "INSPECT_ABI_STABILITY":
        from .governance import abi_stability_table
        exact_keys(payload, set()); result = abi_stability_table()
    elif surface == "INSPECT_ENVIRONMENT_POLICY":
        from .governance import inspect_environment
        exact_keys(payload, {"environment", "strict"})
        result = inspect_environment(payload["environment"], strict=payload["strict"])
    elif surface == "GENERATE_SHELL_COMPLETION":
        from .governance import shell_completion
        exact_keys(payload, {"shell"}); result = shell_completion(payload["shell"])
    elif surface == "PRETTY_PRINT_RECORD":
        from .presentation import pretty_record
        exact_keys(payload, {"record", "title"})
        result = pretty_record(payload["record"], title=payload["title"])
    elif surface == "BUILD_EXTERNAL_TOOL_EVIDENCE":
        from .evidence_adapters import build_tool_evidence_subject
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_tool_evidence_subject(**payload)
    elif surface == "VERIFY_EXTERNAL_TOOL_EVIDENCE":
        from .evidence_adapters import validate_tool_evidence_subject
        exact_keys(payload, {"evidence_subject"})
        result = validate_tool_evidence_subject(payload["evidence_subject"])
    elif surface == "VERIFY_EXTERNAL_APPROVAL":
        from .governance import verify_external_approval
        exact_keys(payload, {"approval", "expected_operation_root",
                             "expected_policy_root", "now"})
        result = verify_external_approval(payload["approval"],
            expected_operation_root=payload["expected_operation_root"],
            expected_policy_root=payload["expected_policy_root"], now=payload["now"])
    elif surface == "VALIDATE_EXTERNAL_EVIDENCE":
        from .evidence import validate_evidence_envelope
        exact_keys(payload, {"evidence", "expected_subject_root", "expected_policy_root", "now"})
        result = validate_evidence_envelope(payload["evidence"],
            expected_subject_root=payload["expected_subject_root"],
            expected_policy_root=payload["expected_policy_root"], now=payload["now"])
    elif surface == "SUMMARIZE_JOURNAL":
        from .journal_tools import summarize_events
        exact_keys(payload, {"events"}); result = summarize_events(payload["events"])
    elif surface == "DIFF_JOURNALS":
        from .journal_tools import diff_event_chains
        exact_keys(payload, {"before", "after"})
        result = diff_event_chains(payload["before"], payload["after"])
    elif surface == "BUILD_JOURNAL_INCLUSION_PROOF":
        from .journal_tools import build_inclusion_proof
        exact_keys(payload, {"events", "event_root"})
        result = build_inclusion_proof(payload["events"], event_root=payload["event_root"])
    elif surface == "VERIFY_JOURNAL_INCLUSION_PROOF":
        from .journal_tools import verify_inclusion_proof
        exact_keys(payload, {"proof"}); result = verify_inclusion_proof(payload["proof"])
    elif surface == "RUN_FIELD_SMOKE":
        from .diagnostics import smoke
        exact_keys(payload, set()); result = smoke()
    elif surface == "BUILD_ARCHITECTURE_STUDY_ROSTER":
        from .evaluation import build_run_roster
        exact_keys(payload, {"protocol"}); result = build_run_roster(payload["protocol"])
    elif surface == "VALIDATE_ARCHITECTURE_STUDY_RESULT":
        from .evaluation import validate_run_result
        exact_keys(payload, {"protocol", "result", "context_registration"})
        result = validate_run_result(payload["protocol"], payload["result"],
                                     payload["context_registration"])
    elif surface == "AGGREGATE_ARCHITECTURE_STUDY":
        from .evaluation import aggregate_study_results
        exact_keys(payload, {"protocol", "results", "context_registration"})
        result = aggregate_study_results(payload["protocol"], payload["results"],
                                         payload["context_registration"])
    elif surface == "VALIDATE_ARCHITECTURE_CONTRACT":
        from .architecture import validate_architecture_contract
        exact_keys(payload, {"contract"}); result = validate_architecture_contract(payload["contract"])
    elif surface == "CHECK_ARCHITECTURE_CHANGE":
        from .architecture import check_architecture_change
        exact_keys(payload, {"contract", "candidate"})
        result = check_architecture_change(payload["contract"], payload["candidate"])
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
    elif surface == "DISCOVER_AMCAS_BASELINE":
        from .amcas_parity import build_amcas_registry
        exact_keys(payload, set()); result = build_amcas_registry()
    elif surface == "INSPECT_AMCAS_UCM_COVERAGE":
        from .amcas_parity import build_ucm_coverage_registry
        exact_keys(payload, set()); result = build_ucm_coverage_registry()
    elif surface == "COMPILE_AMCAS_BASELINE":
        from .amcas_parity import compile_amcas_baseline
        exact_keys(payload, {"contract"}); result = compile_amcas_baseline(payload["contract"])
    elif surface == "DIFF_AMCAS_BASELINES":
        from .amcas_parity import semantic_diff_amcas
        exact_keys(payload, {"old_contract", "new_contract"})
        result = semantic_diff_amcas(payload["old_contract"], payload["new_contract"])
    elif surface == "CHECK_AMCAS_UCM_PARITY":
        from .amcas_parity import run_amcas_ucm_parity
        exact_keys(payload, set()); result = run_amcas_ucm_parity()
    elif surface == "INSPECT_AMCAS_PORTFOLIO":
        from .amcas_parity import build_portfolio_observatory
        exact_keys(payload, {"profile_sets", "parity_result", "consolidation_roots"})
        result = build_portfolio_observatory(**payload)
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
    elif surface == "PREPARE_GOVERNED_WORK_PACKAGE":
        from .work_package import prepare_work_package
        exact_keys(payload, {"project", "changed_ids", "changed_paths", "objective",
                             "workspace", "architecture_contract", "architecture_candidate"})
        result = prepare_work_package(**payload)
    elif surface == "PREPARE_MOSAICOS_M1":
        from uclop.maturity_mosaicos import prepare_m1_from_m0_archive
        exact_keys(payload, {"m0_archive_base64", "expected_archive_sha256"})
        result = prepare_m1_from_m0_archive(
            _archive(payload["m0_archive_base64"]),
            expected_archive_sha256=payload["expected_archive_sha256"])
    elif surface == "VERIFY_MOSAICOS_M1_PREPARATION":
        from uclop.maturity_mosaicos import verify_m1_preparation
        exact_keys(payload, {"preparation", "expected_root"})
        result = verify_m1_preparation(payload["preparation"],
                                       expected_root=payload["expected_root"])
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
    elif surface == "VALIDATE_NATIVE_CONTROL_PLANE_RESULT":
        from .constitutional_runtime import validate_adapter_result
        exact_keys(payload, {"adapter_result"})
        result = validate_adapter_result(payload["adapter_result"])
    elif surface == "VALIDATE_APPLICATION_CAPSULE":
        from .application_capsule import validate_application_capsule
        exact_keys(payload, {"capsule"})
        result = validate_application_capsule(payload["capsule"])
    elif surface == "VALIDATE_INTEGRATION_CONTROL_PLAN":
        from .integration_control import validate_control_plan
        exact_keys(payload, {"plan"})
        result = validate_control_plan(payload["plan"])
    elif surface == "INSPECT_INTEGRATION_OBSERVATORY":
        from .integration_observatory import build_observatory
        exact_keys(payload, {"capsules", "operation_states", "journal_heads"})
        result = build_observatory(**payload)
    elif surface == "BUILD_ADMISSIBILITY_JURISDICTION":
        from .ccp_admissibility import build_jurisdiction_profile
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_jurisdiction_profile(**payload)
    elif surface == "BUILD_ADMISSIBILITY_ENFORCEMENT_PERIMETER":
        from .ccp_admissibility import build_enforcement_perimeter
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_enforcement_perimeter(**payload)
    elif surface == "BUILD_CHC_THR_CORRESPONDENCE":
        from .ccp_admissibility import build_chc_thr_correspondence
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_chc_thr_correspondence(**payload)
    elif surface == "BUILD_ADMISSIBILITY_EVIDENCE_SNAPSHOT":
        from .ccp_admissibility import build_evidence_snapshot
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_evidence_snapshot(**payload)
    elif surface == "BUILD_CURRENT_USE_SNAPSHOT":
        from .ccp_admissibility import build_current_use_snapshot
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_current_use_snapshot(**payload)
    elif surface == "EVALUATE_CURRENT_ADMISSIBILITY":
        from .ccp_admissibility import evaluate_current_admissibility
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = evaluate_current_admissibility(**payload)
    elif surface == "EXPLAIN_CURRENT_ADMISSIBILITY":
        from .ccp_admissibility import build_admissibility_projection
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_admissibility_projection(**payload)
    elif surface == "BUILD_COURTHOUSE_ADMISSION_ENVELOPE":
        from .ccp_courthouse import build_courthouse_admission_envelope
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_courthouse_admission_envelope(**payload)
    elif surface == "COMPILE_ADMISSIBLE_COURTHOUSE_WORKFLOW":
        from .ccp_courthouse import compile_admissible_workflow_submission
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = compile_admissible_workflow_submission(**payload)
    elif surface == "PROJECT_COURTHOUSE_ADMISSION_STATUS":
        from .ccp_courthouse import build_pippi_admission_status
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = build_pippi_admission_status(**payload)
    elif surface == "VERIFY_ADMISSIBLE_COURTHOUSE_RESULT":
        from .ccp_courthouse import validate_admissible_workflow_result
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = validate_admissible_workflow_result(**payload)
    elif surface in {
            "DISCOVER_UGEL_EXECUTOR_PACK", "BUILD_UGEL_EXECUTOR_BINDING",
            "BUILD_UGEL_COMPONENT_POLICY", "BUILD_UGEL_GUEST_CALL",
            "EVALUATE_UGEL_REFERENCE_SIMULATION", "COMPILE_UGEL_CORRESPONDENCE",
            }:
        from . import ugel
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        functions = {
            "DISCOVER_UGEL_EXECUTOR_PACK": ugel.executor_pack_registry,
            "BUILD_UGEL_EXECUTOR_BINDING": ugel.build_executor_binding,
            "BUILD_UGEL_COMPONENT_POLICY": ugel.build_component_policy,
            "BUILD_UGEL_GUEST_CALL": ugel.build_guest_call,
            "EVALUATE_UGEL_REFERENCE_SIMULATION": ugel.evaluate_reference_sim_add,
            "COMPILE_UGEL_CORRESPONDENCE": ugel.compile_correspondence,
        }
        result = functions[surface](**payload)
    elif surface == "PREPARE_ADMISSIBILITY_BOUND_GATEWAY":
        from .operation_gateway import gateway_from_workspace
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        gateway = gateway_from_workspace(payload["workspace"], payload["progress_path"])
        result = gateway.prepare_with_admissibility(
            payload["contract"], payload["decision"],
            current_use_snapshot=payload["current_use_snapshot"],
            evidence_snapshot=payload["evidence_snapshot"],
            jurisdiction_profile=payload["jurisdiction_profile"],
            enforcement_perimeter=payload["enforcement_perimeter"],
            correspondence=payload["correspondence"],
            expected_subject_root=payload["expected_subject_root"],
            expected_jurisdiction_profile_root=
                payload["expected_jurisdiction_profile_root"],
            expected_enforcement_perimeter_root=
                payload["expected_enforcement_perimeter_root"],
            expected_correspondence_root=
                payload["expected_correspondence_root"],
            expected_policy_root=payload["expected_policy_root"],
            expected_schema_registry_root=
                payload["expected_schema_registry_root"],
            expected_trust_root=payload["expected_trust_root"],
            expected_checkpoint_root=payload["expected_checkpoint_root"],
            expected_admissibility_decision_root=payload["expected_admissibility_decision_root"],
            expected_current_use_snapshot_root=payload["expected_current_use_snapshot_root"],
            expected_issuer_public_key_hex=payload["expected_issuer_public_key_hex"],
            expected_jurisdiction_root=payload["expected_jurisdiction_root"],
            expected_revocation_registry_root=payload["expected_revocation_registry_root"])
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
    elif surface == "FINALIZE_OPERATIONAL_TERMINAL":
        from .operation_gateway import gateway_from_workspace
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = gateway_from_workspace(payload["workspace"], payload["progress_path"]).finalize_terminal(
            payload["operation_id"])
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
        from .operation_gateway import inspect_operation_state
        exact_keys(payload, set(CAPABILITY_PAYLOAD_FIELDS[surface]))
        result = inspect_operation_state(payload["workspace"], payload["operation_id"])
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
        "profile_id": selection["profile_id"],
        "profile_selection_root": selection["profile_selection_root"],
        "result": result,
        "effect_scope": next(row[2] for row in CAPABILITY_DEFINITIONS if row[0] == surface),
        **BOUNDARY,
    })

"""Stable public identity and capability registry for UCM v0.1.

Build-generation labels are deliberately absent from this surface. The compatible
implementation remains in ``uclop`` and ``uclsh``; this module names roles rather
than the batches in which they were introduced.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import root

VERSION = "v0.1"
BOUNDARY = {
    "standing": "INFORMATION_ONLY",
    "authority_effect": "NONE",
    "real_a5": False,
    "g0": "CLOSED",
}

SYSTEMS = (
    ("CONSTITUTIONAL_CORE", "Constitutional Core", "Typed identity, authority ceilings, obligations, and receipts."),
    ("UCL_LANGUAGE", "UCL Language System", "Deterministic constitutional programs and self-hosted evaluation."),
    ("TESSERA_COMPILATION", "Tessera Compilation System", "Obligation-preserving compilation and evidence subjects."),
    ("NATIVE_PROOF", "Native Proof Kernel", "Bounded proof certificates rechecked by a small trusted kernel."),
    ("REALIZATION_SPACE", "Realization Space Engine", "Admissible configuration, selection, lowering, and evidence."),
    ("COURT_EXECUTION", "Court Execution Engine", "Exact test selection, protected execution, and typed outcomes."),
    ("QUALIFICATION_CONTROL", "Qualification Control Plane", "Impact planning, qualification, freeze, replay, and handoff."),
    ("CUSTODY_FEDERATION", "Custody and Federation System", "Identity continuity, retirement, replay protection, and custody."),
    ("AGENT_WORKBENCH", "Agent Workbench", "Capability discovery, bounded tasks, recovery, and agent-facing context."),
    ("PROJECT_INTELLIGENCE", "Project Intelligence System", "Content-addressed project graphs and impact analysis."),
    ("AUTONOMOUS_PROJECT_MANAGER", "Autonomous Project Manager", "Plan preparation and durable simulation without authority."),
    ("PORTABLE_BOOTSTRAP", "Portable Bootstrap System", "Content-addressed profiles, deterministic staging, and rollback."),
    ("APPLICATION_GATEWAY", "Application Integration Gateway", "Exact request, response, and correspondence kits."),
    ("AMCAS_INTEGRATION", "AMCAS Integration Compiler", "Compiles application contracts into CM1 obligations, CM2 preferences, and governed work."),
    ("IDENTITY_SESSION", "MosaicID Session System", "Public identity import, possession challenges, session continuity, and non-granting bindings."),
    ("INTEGRATION_JOURNAL", "Integration Journal System", "Durable campaign events, checkpoints, reports, and portable journal archives."),
    ("INTEGRATION_PORTFOLIO", "Integration Portfolio System", "Fixed-denominator Stage I1 custody, THR/CAS separation, Stage I2 preflight, and Stage I3 shadow planning."),
    ("OPERATIONAL_GATEWAY", "Operational Gateway", "Receipt-mediated authorization, durable dispatch custody, reconciliation, proof, and portable operation archives."),
)

CAPABILITY_DEFINITIONS = (
    ("ORIENT", "AGENT_WORKBENCH", "PURE_COMPUTATION", "ACTIVE", "ucm.orientation", "mosaic.ucm.empty.v0.1", "mosaic.ucm.orientation.v0.1"),
    ("DISCOVER_CAPABILITIES", "AGENT_WORKBENCH", "PURE_COMPUTATION", "ACTIVE", "ucm.capability_registry", "mosaic.ucm.empty.v0.1", "mosaic.ucm.capability-registry.v0.1"),
    ("VALIDATE_REALIZATION_CONTRACT", "REALIZATION_SPACE", "PURE_COMPUTATION", "ACTIVE", "ucm.validate_contract", "mosaic.realization-contract-request.v0.1", "mosaic.realization-space-contract.v0.1"),
    ("CHECK_REALIZATION", "REALIZATION_SPACE", "PURE_COMPUTATION", "ACTIVE", "ucm.validate_configuration", "mosaic.realization-check-request.v0.1", "mosaic.realization-configuration.v0.1"),
    ("SELECT_REALIZATION", "REALIZATION_SPACE", "PURE_COMPUTATION", "ACTIVE", "ucm.select_configuration", "mosaic.realization-selection-request.v0.1", "mosaic.realization-selection.v0.1"),
    ("PROJECT_TO_UCL_TESSERA", "TESSERA_COMPILATION", "PURE_COMPUTATION", "ACTIVE", "ucm.project_to_ucl_tessera", "mosaic.realization-projection-request.v0.1", "mosaic.ucl-tessera.realization-projection.v0.1"),
    ("VERIFY_NATIVE_PROOF", "NATIVE_PROOF", "PURE_COMPUTATION", "ACTIVE", "ucm.invoke", "mosaic.native-proof-request.v0.1", "ucl.proof.check.v1"),
    ("PROJECT_DASHBOARD", "PROJECT_INTELLIGENCE", "READ_ONLY", "ACTIVE_WITH_PREPARED_PROJECT", "ucm.invoke", "mosaic.project-dashboard-request.v0.1", "ucl.ucm.project_intelligence.dashboard.v1"),
    ("PREPARE_AUTONOMOUS_PLAN", "AUTONOMOUS_PROJECT_MANAGER", "PURE_COMPUTATION", "ACTIVE_WITH_PREPARED_PROJECT", "ucm.invoke", "mosaic.autonomous-plan-request.v0.1", "ucl.ucm.autonomous_project_manager.plan.v1"),
    ("EXPLAIN_CLAIM", "CONSTITUTIONAL_CORE", "PURE_COMPUTATION", "ACTIVE_WITH_EVIDENCE_CONTEXT", "ucm.invoke", "mosaic.claim-explanation-request.v0.1", "ucl.ucm.explanation_graph.v1"),
    ("TRACE_PRESERVATION", "REALIZATION_SPACE", "PURE_COMPUTATION", "ACTIVE", "ucm.trace_preservation", "mosaic.realization-preservation-request.v0.1", "mosaic.realization-preservation.v0.1"),
    ("BUILD_PORTABLE_PROFILE", "PORTABLE_BOOTSTRAP", "LOCAL_ARTIFACT_PREPARATION", "SEPARATE_STAGE_REQUIRED", "tools/build_release.py", "mosaic.portable-profile-stage-contract.v0.1", "mosaic.ucm.artifact-manifest.v0.1"),
    ("VALIDATE_AMCAS", "AMCAS_INTEGRATION", "PURE_COMPUTATION", "ACTIVE", "ucm.invoke", "mosaic.amcas-validation-request.v0.1", "mosaic.amcas.integration-contract.v0.2"),
    ("COMPILE_AMCAS", "AMCAS_INTEGRATION", "PURE_COMPUTATION", "ACTIVE", "ucm.invoke", "mosaic.amcas-compilation-request.v0.1", "mosaic.amcas.integration-ir.v0.2"),
    ("INSPECT_MOSAIC_ID", "IDENTITY_SESSION", "PURE_COMPUTATION", "ACTIVE", "ucm.invoke", "mosaic.identity-inspection-request.v0.1", "mosaic.identity.inspection.v0.1"),
    ("MANAGE_INTEGRATION_CAMPAIGN", "INTEGRATION_JOURNAL", "LOCAL_ARTIFACT_PREPARATION", "SEPARATE_STAGE_REQUIRED", "ucm campaign-*", "mosaic.integration-campaign-stage.v0.1", "mosaic.ucm.integration-status.v0.1"),
    ("BIND_INTEGRATION_SUBJECT", "AMCAS_INTEGRATION", "READ_ONLY", "SEPARATE_STAGE_REQUIRED", "ucm integration-bind-subject", "mosaic.ucm.subject-binding-policy.v0.1", "mosaic.ucm.subject-binding.v0.1"),
    ("CHECK_CONTROL_PLANES", "AMCAS_INTEGRATION", "PURE_COMPUTATION", "SEPARATE_STAGE_REQUIRED", "ucm integration-check-control-planes", "mosaic.ucm.control-plane-disposition.v0.1", "mosaic.ucm.control-plane-disposition.v0.1"),
    ("RUN_CORRESPONDENCE_COURT", "COURT_EXECUTION", "PURE_COMPUTATION", "SEPARATE_STAGE_REQUIRED", "ucm integration-correspondence-court", "mosaic.ucm.native-correspondence-cases.v0.1", "mosaic.ucm.native-correspondence-court.v0.1"),
    ("VERIFY_STAGE_I1", "AMCAS_INTEGRATION", "READ_ONLY", "SEPARATE_STAGE_REQUIRED", "ucm integration-verify-stage1", "mosaic.ucm.stage-i1-bundle.v0.2", "mosaic.ucm.stage-i1-verification.v0.2"),
    ("GOVERN_INTEGRATION_PORTFOLIO", "INTEGRATION_PORTFOLIO", "LOCAL_ARTIFACT_PREPARATION", "SEPARATE_STAGE_REQUIRED", "ucm portfolio-*", "mosaic.ucm.integration-portfolio.v0.1", "mosaic.ucm.integration-portfolio-status.v0.2"),
    ("PREFLIGHT_PORTFOLIO_COMPOSITION", "INTEGRATION_PORTFOLIO", "PURE_COMPUTATION", "SEPARATE_STAGE_REQUIRED", "ucm portfolio-composition-*", "mosaic.ucm.stage-i2-declaration.v0.1", "mosaic.ucm.stage-i2-composition-preflight.v0.1"),
    ("PLAN_STAGE_I3_SHADOW", "INTEGRATION_PORTFOLIO", "LOCAL_ARTIFACT_PREPARATION", "SEPARATE_STAGE_REQUIRED", "ucm portfolio-issue-stage3-instructions", "mosaic.ucm.stage-i3-shadow-instruction.v0.1", "mosaic.ucm.stage-i3-shadow-plan.v0.1"),
    ("VALIDATE_STAGE_I3_PLAN", "INTEGRATION_PORTFOLIO", "PURE_COMPUTATION", "ACTIVE", "ucm stage3-validate-plan", "mosaic.ucm.stage-i3-plan-validation-request.v0.1", "mosaic.ucm.stage-i3-shadow-plan.v0.1"),
    ("DERIVE_STAGE_I4_ELIGIBILITY", "INTEGRATION_PORTFOLIO", "PURE_COMPUTATION", "LEGACY_COMPATIBILITY_ONLY", "ucm stage4-derive-eligibility", "mosaic.ucm.stage-i4-eligibility-request.v0.2", "mosaic.ucm.stage-i4-eligibility.v0.2"),
    ("VALIDATE_STAGE_I4_RUN_CONTRACT", "INTEGRATION_PORTFOLIO", "PURE_COMPUTATION", "LEGACY_COMPATIBILITY_ONLY", "ucm stage4-validate-run-contract", "mosaic.ucm.stage-i4-run-contract-request.v0.2", "mosaic.ucm.stage-i4-shadow-run-contract.v0.2"),
    ("VALIDATE_STAGE_I4_OBSERVATION", "INTEGRATION_PORTFOLIO", "PURE_COMPUTATION", "LEGACY_COMPATIBILITY_ONLY", "ucm stage4-validate-observation", "mosaic.ucm.stage-i4-observation-request.v0.2", "mosaic.ucm.stage-i4-shadow-observation.v0.2"),
    ("VALIDATE_NATIVE_HEADLESS_RUNNER_BINDING", "COURT_EXECUTION", "PURE_COMPUTATION", "LEGACY_COMPATIBILITY_ONLY", "ucm.invoke", "mosaic.ucm.native-headless-runner-binding-request.v0.1", "mosaic.ucm.native-headless-runner-binding.v0.1"),
    ("DERIVE_TRUSTED_STAGE_I4_ELIGIBILITY", "INTEGRATION_PORTFOLIO", "PURE_COMPUTATION", "LEGACY_COMPATIBILITY_ONLY", "ucm stage4-c3-derive-eligibility", "mosaic.ucm.stage-i4-trusted-eligibility-request.v0.1", "mosaic.ucm.stage-i4-eligibility.v0.3"),
    ("BUILD_STAGE_I4_EXACT_RUN_CONTRACT", "INTEGRATION_PORTFOLIO", "PURE_COMPUTATION", "LEGACY_COMPATIBILITY_ONLY", "ucm stage4-c3-build-run-contract", "mosaic.ucm.stage-i4-exact-run-contract-request.v0.1", "mosaic.ucm.stage-i4-run-contract.v0.3"),
    ("BUILD_STAGE_I4_TERMINAL_REFUSAL", "INTEGRATION_PORTFOLIO", "PURE_COMPUTATION", "LEGACY_COMPATIBILITY_ONLY", "ucm stage4-c3-build-terminal-refusal", "mosaic.ucm.stage-i4-terminal-refusal-request.v0.1", "mosaic.ucm.stage-i4-terminal-operation.v0.1"),
    ("BUILD_NATIVE_HEADLESS_RUNNER_PREFLIGHT", "COURT_EXECUTION", "PURE_COMPUTATION", "LEGACY_COMPATIBILITY_ONLY", "ucm native-runner-preflight", "mosaic.ucm.native-headless-runner-preflight-request.v0.1", "mosaic.ucm.native-headless-runner-preflight.v0.1"),
    ("VALIDATE_NATIVE_HEADLESS_RUNNER_RECEIPT", "COURT_EXECUTION", "PURE_COMPUTATION", "LEGACY_COMPATIBILITY_ONLY", "ucm native-runner-validate-receipt", "mosaic.ucm.native-headless-runner-receipt-request.v0.1", "mosaic.ucm.native-headless-runner-terminal-receipt.v0.1"),
    ("DERIVE_STAGE_I4_OPERATION_STATE", "INTEGRATION_PORTFOLIO", "PURE_COMPUTATION", "LEGACY_COMPATIBILITY_ONLY", "ucm stage4-c3-derive-operation-state", "mosaic.ucm.stage-i4-operation-state-request.v0.1", "mosaic.ucm.stage-i4-operation-state.v0.1"),
    ("VALIDATE_STAGE_I4_OPERATION_STATE", "INTEGRATION_PORTFOLIO", "PURE_COMPUTATION", "LEGACY_COMPATIBILITY_ONLY", "ucm stage4-c3-validate-operation-state", "mosaic.ucm.stage-i4-operation-state-validation-request.v0.1", "mosaic.ucm.stage-i4-operation-state.v0.1"),
    ("BUILD_STAGE_I4_ANCHORED_RUN_CONTRACT", "INTEGRATION_PORTFOLIO", "PURE_COMPUTATION", "LEGACY_COMPATIBILITY_ONLY", "ucm.invoke", "mosaic.ucm.stage-i4-anchored-run-contract-request.v0.1", "mosaic.ucm.stage-i4-run-contract.v0.4"),
    ("BUILD_STAGE_I4_AUTHORITY_SAFE_PREFLIGHT", "COURT_EXECUTION", "PURE_COMPUTATION", "LEGACY_COMPATIBILITY_ONLY", "ucm.invoke", "mosaic.ucm.stage-i4-authority-safe-preflight-request.v0.1", "mosaic.ucm.native-headless-runner-preflight.v0.2"),
    ("BUILD_STAGE_I4_RECEIPTED_REFUSAL", "INTEGRATION_PORTFOLIO", "PURE_COMPUTATION", "LEGACY_COMPATIBILITY_ONLY", "ucm.invoke", "mosaic.ucm.stage-i4-receipted-refusal-request.v0.1", "mosaic.ucm.stage-i4-terminal-operation.v0.2"),
    ("DERIVE_STAGE_I4_RECEIPT_STATE", "INTEGRATION_PORTFOLIO", "PURE_COMPUTATION", "LEGACY_COMPATIBILITY_ONLY", "ucm.invoke", "mosaic.ucm.stage-i4-receipt-state-request.v0.1", "mosaic.ucm.stage-i4-operation-state.v0.2"),
    ("VALIDATE_STAGE_I4_RECEIPT_STATE", "INTEGRATION_PORTFOLIO", "PURE_COMPUTATION", "LEGACY_COMPATIBILITY_ONLY", "ucm.invoke", "mosaic.ucm.stage-i4-receipt-state-validation-request.v0.1", "mosaic.ucm.stage-i4-operation-state.v0.2"),
    ("BUILD_OPERATIONAL_CONTRACT", "OPERATIONAL_GATEWAY", "PURE_COMPUTATION", "ACTIVE", "ucm operational-invoke", "mosaic.ucm.operational-contract-request.v0.1", "mosaic.ucm.operational-contract.v0.1"),
    ("PREPARE_OPERATIONAL_GATEWAY", "OPERATIONAL_GATEWAY", "LOCAL_ARTIFACT_PREPARATION", "ACTIVE", "ucm operational-invoke", "mosaic.ucm.operational-prepare-request.v0.1", "mosaic.ucm.operational-preparation.v0.1"),
    ("RECORD_OPERATIONAL_DISPATCH", "OPERATIONAL_GATEWAY", "LOCAL_ARTIFACT_PREPARATION", "ACTIVE", "ucm operational-invoke", "mosaic.ucm.operational-dispatch-request.v0.1", "mosaic.ucm.operational-dispatch-result.v0.1"),
    ("RECORD_OPERATIONAL_TERMINAL", "OPERATIONAL_GATEWAY", "LOCAL_ARTIFACT_PREPARATION", "ACTIVE", "ucm operational-invoke", "mosaic.ucm.operational-terminal-request.v0.1", "mosaic.ucm.operational-terminal-result.v0.1"),
    ("MARK_OPERATIONAL_UNCERTAIN", "OPERATIONAL_GATEWAY", "LOCAL_ARTIFACT_PREPARATION", "ACTIVE", "ucm operational-invoke", "mosaic.ucm.operational-uncertain-request.v0.1", "mosaic.ucm.operational-state.v0.1"),
    ("RECONCILE_OPERATIONAL_OUTCOME", "OPERATIONAL_GATEWAY", "LOCAL_ARTIFACT_PREPARATION", "ACTIVE", "ucm operational-invoke", "mosaic.ucm.operational-reconcile-request.v0.1", "mosaic.ucm.operational-terminal-result.v0.1"),
    ("CANCEL_OPERATIONAL_GATEWAY", "OPERATIONAL_GATEWAY", "LOCAL_ARTIFACT_PREPARATION", "ACTIVE", "ucm operational-invoke", "mosaic.ucm.operational-cancel-request.v0.1", "mosaic.ucm.operational-state.v0.1"),
    ("INSPECT_OPERATIONAL_STATE", "OPERATIONAL_GATEWAY", "READ_ONLY", "ACTIVE", "ucm operational-invoke", "mosaic.ucm.operational-state-request.v0.1", "mosaic.ucm.operational-state.v0.1"),
    ("BUILD_OPERATIONAL_PROOF", "OPERATIONAL_GATEWAY", "READ_ONLY", "ACTIVE", "ucm operational-invoke", "mosaic.ucm.operational-proof-request.v0.1", "mosaic.ucm.operational-proof-bundle.v0.1"),
    ("EXPORT_OPERATIONAL_ARCHIVE", "OPERATIONAL_GATEWAY", "READ_ONLY", "ACTIVE", "ucm operational-invoke", "mosaic.ucm.operational-archive-request.v0.1", "mosaic.ucm.operational-archive-base64.v0.1"),
    ("VERIFY_OPERATIONAL_ARCHIVE", "OPERATIONAL_GATEWAY", "PURE_COMPUTATION", "ACTIVE", "ucm operational-invoke", "mosaic.ucm.operational-archive-verification-request.v0.1", "mosaic.ucm.operational-archive-verification.v0.1"),
    ("RECOVER_OPERATIONAL_JOURNAL", "OPERATIONAL_GATEWAY", "LOCAL_ARTIFACT_PREPARATION", "ACTIVE", "ucm operational-invoke", "mosaic.ucm.operational-journal-recovery-request.v0.1", "mosaic.ucm.integration-journal-head.v0.1"),
)
CAPABILITIES = tuple(row[0] for row in CAPABILITY_DEFINITIONS)
CAPABILITY_PAYLOAD_FIELDS = {
    "ORIENT": (),
    "DISCOVER_CAPABILITIES": (),
    "VALIDATE_REALIZATION_CONTRACT": ("contract",),
    "CHECK_REALIZATION": ("contract", "configuration"),
    "SELECT_REALIZATION": ("contract", "candidates"),
    "PROJECT_TO_UCL_TESSERA": ("contract",),
    "VERIFY_NATIVE_PROOF": ("contract", "proof_bundle"),
    "PROJECT_DASHBOARD": ("project", "workspace"),
    "PREPARE_AUTONOMOUS_PLAN": ("changed_ids", "changed_paths", "objective", "project"),
    "EXPLAIN_CLAIM": ("accepted_contract_roots", "assertions", "edges", "evidence_contracts", "proof_roots", "subject_root"),
    "TRACE_PRESERVATION": ("after", "before", "contract"),
    "BUILD_PORTABLE_PROFILE": ("stage_contract",),
    "VALIDATE_AMCAS": ("contract",),
    "COMPILE_AMCAS": ("contract",),
    "INSPECT_MOSAIC_ID": ("passport", "expected_mosaic_id"),
    "MANAGE_INTEGRATION_CAMPAIGN": ("stage_contract",),
    "BIND_INTEGRATION_SUBJECT": ("stage_contract",),
    "CHECK_CONTROL_PLANES": ("stage_contract",),
    "RUN_CORRESPONDENCE_COURT": ("stage_contract",),
    "VERIFY_STAGE_I1": ("stage_contract",),
    "GOVERN_INTEGRATION_PORTFOLIO": ("stage_contract",),
    "PREFLIGHT_PORTFOLIO_COMPOSITION": ("stage_contract",),
    "PLAN_STAGE_I3_SHADOW": ("stage_contract",),
    "VALIDATE_STAGE_I3_PLAN": ("instruction", "plan"),
    "DERIVE_STAGE_I4_ELIGIBILITY": ("instruction", "plan", "review_archive_base64"),
    "VALIDATE_STAGE_I4_RUN_CONTRACT": ("eligibility", "instruction", "plan", "review_archive_base64", "run_contract"),
    "VALIDATE_STAGE_I4_OBSERVATION": ("eligibility", "instruction", "observation", "plan", "review_archive_base64", "run_contract"),
    "VALIDATE_NATIVE_HEADLESS_RUNNER_BINDING": ("binding",),
    "DERIVE_TRUSTED_STAGE_I4_ELIGIBILITY": ("instruction", "plan", "review_archive_base64", "review_policy"),
    "BUILD_STAGE_I4_EXACT_RUN_CONTRACT": ("eligibility", "instruction", "native_runner_binding", "plan", "relation_case_map", "review_archive_base64", "review_policy", "selection", "execution_context"),
    "BUILD_STAGE_I4_TERMINAL_REFUSAL": ("run_contract",),
    "BUILD_NATIVE_HEADLESS_RUNNER_PREFLIGHT": ("binding", "execution_authorized", "execution_context_root", "requested_effect_classes", "run_contract_root"),
    "VALIDATE_NATIVE_HEADLESS_RUNNER_RECEIPT": ("preflight", "receipt"),
    "DERIVE_STAGE_I4_OPERATION_STATE": ("events", "operation_id", "run_contract_root"),
    "VALIDATE_STAGE_I4_OPERATION_STATE": ("state",),
    "BUILD_STAGE_I4_ANCHORED_RUN_CONTRACT": ("eligibility", "instruction", "native_runner_binding", "plan", "relation_case_map", "review_archive_base64", "review_policy", "selection", "execution_context", "trust_anchors", "expected_trust_anchors_root", "execution_authority_policy"),
    "BUILD_STAGE_I4_AUTHORITY_SAFE_PREFLIGHT": ("run_contract", "trust_anchors", "expected_trust_anchors_root", "execution_authority_policy"),
    "BUILD_STAGE_I4_RECEIPTED_REFUSAL": ("run_contract", "expected_trust_anchors_root"),
    "DERIVE_STAGE_I4_RECEIPT_STATE": ("events", "operation_id", "run_contract_root"),
    "VALIDATE_STAGE_I4_RECEIPT_STATE": ("state",),
    "BUILD_OPERATIONAL_CONTRACT": ("expected_issuer_public_key_hex", "expected_jurisdiction_root", "expected_result_root", "expected_revocation_registry_root", "idempotency_key", "now", "operation_id", "permit", "requested_effect_classes", "revocation_registry"),
    "PREPARE_OPERATIONAL_GATEWAY": ("contract", "expected_issuer_public_key_hex", "expected_jurisdiction_root", "expected_revocation_registry_root", "progress_path", "workspace"),
    "RECORD_OPERATIONAL_DISPATCH": ("operation_id", "progress_path", "receipt", "workspace"),
    "RECORD_OPERATIONAL_TERMINAL": ("operation_id", "progress_path", "receipt", "workspace"),
    "MARK_OPERATIONAL_UNCERTAIN": ("operation_id", "progress_path", "reason_code", "workspace"),
    "RECONCILE_OPERATIONAL_OUTCOME": ("operation_id", "progress_path", "receipt", "workspace"),
    "CANCEL_OPERATIONAL_GATEWAY": ("operation_id", "progress_path", "reason_code", "workspace"),
    "INSPECT_OPERATIONAL_STATE": ("operation_id", "workspace"),
    "BUILD_OPERATIONAL_PROOF": ("expected_issuer_public_key_hex", "expected_jurisdiction_root", "expected_revocation_registry_root", "operation_id", "workspace"),
    "EXPORT_OPERATIONAL_ARCHIVE": ("expected_issuer_public_key_hex", "expected_jurisdiction_root", "expected_revocation_registry_root", "operation_id", "workspace"),
    "VERIFY_OPERATIONAL_ARCHIVE": ("archive_base64", "expected_issuer_public_key_hex", "expected_jurisdiction_root", "expected_revocation_registry_root"),
    "RECOVER_OPERATIONAL_JOURNAL": ("expected_head", "progress_path", "workspace"),
}


def _seal(body: dict[str, Any]) -> dict[str, Any]:
    return {**deepcopy(body), "root": root(body)}


def orientation() -> dict[str, Any]:
    return _seal({
        "schema": "mosaic.ucm.orientation.v0.1",
        "product": "Universal Constitutional Machine",
        "short_name": "UCM",
        "version": VERSION,
        "publisher": "Ableman Mosaic",
        "license": "Apache-2.0",
        "start_here": {
            "human": "README.md",
            "agent": "docs/AGENT-START.md",
            "architecture": "docs/ARCHITECTURE.md",
            "capabilities": "docs/CAPABILITY-SURFACES.md",
            "realization": "docs/REALIZATION-SPACE.md",
            "integration": "docs/APPLICATION-INTEGRATION.md",
        },
        "conceptual_interface": [
            "DESCRIBE", "CONSTRAIN", "CHECK", "COMPARE", "SELECT", "PROJECT",
            "TRACE", "PROVE", "EXPLAIN", "PREPARE",
        ],
        "systems": [{"id": i, "name": n, "role": r} for i, n, r in SYSTEMS],
        "compatibility_implementation": ["uclop", "uclsh"],
        **BOUNDARY,
    })


def capability_registry() -> dict[str, Any]:
    return _seal({
        "schema": "mosaic.ucm.capability-registry.v0.1",
        "version": VERSION,
        "surfaces": [
            {
                "name": name, "system": system, "effect_scope": effect,
                "availability": availability, "route": route,
                "request_schema": request_schema, "result_schema": result_schema,
                "payload_required": list(CAPABILITY_PAYLOAD_FIELDS[name]),
                "readiness_required": availability != "ACTIVE",
            }
            for name, system, effect, availability, route, request_schema, result_schema in CAPABILITY_DEFINITIONS
        ],
        "effectful_execution": "REQUIRES_SEPARATE_GOVERNED_STAGE",
        **BOUNDARY,
    })


from __future__ import annotations

import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from uclop.canonical import canonical_bytes, root
from ucm.development_standards import build_standards_catalog, evaluate_standards
from ucm.governance import build_external_approval, external_approval_signing_body
from ucm.process_governance import (
    assess_process_milestone,
    build_artifact_producer_receipt,
    build_courthouse_process_binding,
    build_dkn_locality_binding,
    build_exact_execution_capsule,
    build_governed_replan,
    build_process_baseline,
    build_process_checkpoint,
    build_process_milestone,
    build_process_observatory,
    build_process_standards_schedule,
    build_process_thr_manifest,
    record_process_milestone_decision,
    validate_dkn_locality_binding,
    validate_artifact_producer_receipt,
    validate_courthouse_process_binding,
    validate_exact_execution_capsule,
    validate_process_baseline,
    validate_process_checkpoint,
    validate_process_milestone,
    validate_process_milestone_assessment,
    validate_process_milestone_decision,
    validate_process_observatory,
    validate_process_standards_schedule,
)
from ucm.system import BOUNDARY
from ucm.thr_cas import verify_thr_manifest


def h(label: str) -> str:
    return root({"label": label})


class ProcessGovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.private_key = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
        cls.public_key_hex = cls.private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        ).hex()

    def locality(self) -> dict:
        return build_dkn_locality_binding(
            phase_code="UCM.V0.1.PROCESS",
            authority_public_key_hex=self.public_key_hex,
            semantic_namespace="mosaic.ucm.process.fixture",
            universe_root=h("fixture-universe"),
            namespace_policy_root=h("namespace-policy"),
            passport=None,
            possession_receipt_root=None,
            local_admission_root=None,
        )

    def catalog(self) -> dict:
        return build_standards_catalog(
            catalog_id="PIPPI.PROCESS.C1",
            policy_root=h("standards-policy"),
            obligations=[{
                "obligation_id": "PROCESS.EXACT.SUBJECT",
                "statement": "Bind work to the exact subject.",
                "class": "MANDATORY",
                "triggers": [],
                "check_ids": ["CHECK.EXACT.SUBJECT"],
                "evidence_required": True,
            }, {
                "obligation_id": "PROCESS.ARCHITECTURE.REVIEW",
                "statement": "Review architecture changes.",
                "class": "CONDITIONAL",
                "triggers": ["ARCHITECTURE_CHANGE"],
                "check_ids": ["CHECK.ARCHITECTURE"],
                "evidence_required": True,
            }],
        )

    def baseline(self, catalog: dict, locality: dict,
                 execution_capsule_roots: list[str] | None = None) -> dict:
        return build_process_baseline(
            project_id="UCM.PIPPI.PROCESS.C1",
            objective="Build a portable process-governance successor.",
            subject_root=h("subject"),
            source_manifest_root=h("source-manifest"),
            architecture_contract_root=h("architecture"),
            amcas_contract_root=h("amcas"),
            standards_catalog_root=catalog["catalog_root"],
            policy_roots=sorted([h("process-policy"), h("standards-policy")]),
            requirement_roots=sorted([h("requirement-1"), h("requirement-2")]),
            software_generation_root=h("software-generation"),
            initial_journal_head_root=h("journal-initial"),
            user_identity_root=h("user-identity"),
            session_identity_root=h("session-identity"),
            locality_binding=locality,
            responsibilities=[{
                "role_id": "BUILDER",
                "actor_identity_root": h("session-identity"),
                "responsibility_ids": ["IMPLEMENT", "TEST"],
                "acceptance_scope_ids": [],
            }, {
                "role_id": "GOVERNOR",
                "actor_identity_root": h("user-identity"),
                "responsibility_ids": ["ACCEPT"],
                "acceptance_scope_ids": ["MILESTONE.C1"],
            }],
            deliverable_ids=["PROCESS.CODE", "PROCESS.DOCS", "PROCESS.REVIEW.KIT"],
            execution_capsule_roots=execution_capsule_roots or [],
        )

    def execution_capsule(self) -> dict:
        return build_exact_execution_capsule(
            capsule_id="QUALIFY.PROCESS.C1", executable_root=h("python-runtime"),
            runner_root=h("qualification-runner"),
            argv=["python", "tools/run_process_qualification.py"],
            normalized_cwd="workspace",
            environment_projection={"PYTHONDONTWRITEBYTECODE": "1"},
            dependencies=[
                {"path": "src/ucm/process_governance.py", "sha256": h("process-source"),
                 "role": "IMPLEMENTATION"},
                {"path": "tools/run_process_qualification.py", "sha256": h("runner-source"),
                 "role": "RUNNER"},
            ], missing_dependency_ids=[],
            exact_input_roots=sorted([h("source-manifest"), h("standards-policy")]),
            policy_root=h("process-policy"), profile_root=h("profile"),
            authority_root=h("authority"), jurisdiction_root=h("jurisdiction"),
            effect_class="LOCAL_TEST_EXECUTION",
            expected_write_paths=["artifacts/.history/qualification.json",
                                  "out/qualification.json"],
            transaction_history_paths=["artifacts/.history/qualification.json"],
            adapter_root=h("adapter"),
        )

    def evaluation(self, catalog: dict) -> dict:
        return evaluate_standards(
            catalog=catalog,
            subject_root=h("deliverable-subject"),
            active_triggers=[],
            check_results=[{
                "check_id": "CHECK.EXACT.SUBJECT",
                "role": "STATIC",
                "subject_root": h("deliverable-subject"),
                "status": "PASS",
                "evidence_root": h("standards-evidence"),
                "witness_root": None,
            }],
        )

    def milestone(self, baseline: dict) -> dict:
        return build_process_milestone(
            milestone_id="MILESTONE.C1",
            process_baseline_root=baseline["process_baseline_root"],
            title="Portable process-governance subsystem",
            objective="Deliver typed records, projections, and review material.",
            predecessor_milestone_ids=[],
            entry_criteria=[{
                "criterion_id": "ENTRY.BASELINE",
                "kind": "ARTIFACT",
                "expected_root": baseline["process_baseline_root"],
            }],
            deliverables=[{
                "deliverable_id": "PROCESS.CODE",
                "artifact_role": "IMPLEMENTATION",
                "subject_root": h("deliverable-subject"),
                "required_check_ids": ["CHECK.PROCESS.TARGETED"],
            }],
            standards_obligation_ids=["PROCESS.EXACT.SUBJECT"],
            acceptance_role_id="GOVERNOR",
            acceptance_policy_root=h("acceptance-policy"),
            rollback_required=True,
            rollback_plan_root=h("rollback-plan"),
            authority_ceiling=BOUNDARY,
        )

    def assessment(self, milestone: dict, evaluation: dict) -> dict:
        return assess_process_milestone(
            milestone=milestone,
            accepted_predecessors=[],
            entry_evidence=[{
                "criterion_id": "ENTRY.BASELINE",
                "evidence_root": milestone["process_baseline_root"],
            }],
            check_results=[{
                "check_id": "CHECK.PROCESS.TARGETED",
                "role": "TARGETED",
                "subject_root": h("deliverable-subject"),
                "status": "PASS",
                "evidence_root": h("targeted-evidence"),
                "witness_root": None,
                "freshness": "CURRENT",
            }],
            standards_evaluation=evaluation,
        )

    def approval(self, assessment: dict) -> dict:
        policy_root = h("acceptance-policy")
        signing_body = external_approval_signing_body(
            approval_id="APPROVAL.MILESTONE.C1",
            operation_root=assessment["milestone_assessment_root"],
            approver_identity_root=h("user-identity"),
            approver_public_key_hex=self.public_key_hex,
            policy_root=policy_root,
            decision="APPROVE",
            issued_at=100,
            not_after=200,
        )
        signature = self.private_key.sign(canonical_bytes(signing_body)).hex()
        return build_external_approval(
            approval_id="APPROVAL.MILESTONE.C1",
            operation_root=assessment["milestone_assessment_root"],
            approver_identity_root=h("user-identity"),
            approver_public_key_hex=self.public_key_hex,
            policy_root=policy_root,
            decision="APPROVE",
            issued_at=100,
            not_after=200,
            signature_hex=signature,
        )

    def test_locality_baseline_and_milestone_are_exact_and_non_authorizing(self) -> None:
        locality = self.locality()
        catalog = self.catalog()
        capsule = self.execution_capsule()
        baseline = self.baseline(catalog, locality, [capsule["execution_capsule_root"]])
        milestone = self.milestone(baseline)
        self.assertEqual(validate_dkn_locality_binding(locality), locality)
        self.assertEqual(validate_process_baseline(baseline), baseline)
        self.assertEqual(validate_process_milestone(milestone), milestone)
        self.assertFalse(locality["permission_granted"])
        self.assertFalse(baseline["execution_authorized"])
        self.assertFalse(milestone["execution_authorized"])

    def test_locality_surface_is_available_through_authoring_abi(self) -> None:
        from ucm.capabilities import invoke
        from ucm.system import capability_registry
        registry = capability_registry()
        response = invoke({
            "schema": "mosaic.ucm.request.v0.2",
            "surface": "BUILD_DKN_LOCALITY_BINDING",
            "payload": {
                "phase_code": "UCM.V0.1.PROCESS",
                "authority_public_key_hex": self.public_key_hex,
                "semantic_namespace": "mosaic.ucm.process.fixture",
                "universe_root": h("fixture-universe"),
                "namespace_policy_root": h("namespace-policy"),
                "passport": None,
                "possession_receipt_root": None,
                "local_admission_root": None,
            },
            "profile_selection": {
                "schema": "mosaic.ucm.product-profile-selection.v0.1",
                "profile_id": "AUTHORING",
                "capability_registry_root": registry["root"],
            },
            "request_id": "TEST.PROCESS.LOCALITY",
        })
        self.assertEqual(response["result"]["schema"],
                         "mosaic.ucm.process-locality-binding.v0.1")

    def test_execution_capsule_binds_complete_dependency_closure(self) -> None:
        capsule = self.execution_capsule()
        self.assertEqual(validate_exact_execution_capsule(capsule), capsule)
        self.assertEqual(capsule["dependency_closure_status"], "COMPLETE")
        self.assertTrue(capsule["terminal_receipt_reusable"])
        self.assertEqual(capsule["artifact_producer_binding"]["expected_value"],
                         capsule["operation_identity_root"])
        self.assertEqual(capsule["transaction_history_paths"],
                         ["artifacts/.history/qualification.json"])
        receipt = build_artifact_producer_receipt(
            artifact_path="out/qualification.json",
            artifact_sha256=h("qualification-bytes"),
            producer_operation_root=capsule["operation_identity_root"],
            predecessor_artifact_sha256=None,
            predecessor_producer_operation_root=None,
            transaction_history_path=None,
            supersession_kind="INITIAL",
        )
        self.assertEqual(validate_artifact_producer_receipt(receipt), receipt)
        self.assertFalse(capsule["execution_authorized"])

    def test_milestone_acceptance_and_lifecycle_remain_external_and_receipted(self) -> None:
        locality = self.locality()
        catalog = self.catalog()
        baseline = self.baseline(catalog, locality)
        assessment = self.assessment(self.milestone(baseline), self.evaluation(catalog))
        decision = record_process_milestone_decision(
            assessment=assessment,
            decision="ACCEPTED",
            reason_codes=[],
            external_approval=self.approval(assessment),
            expected_acceptance_policy_root=h("acceptance-policy"),
            now=150,
        )
        self.assertEqual(validate_process_milestone_assessment(assessment), assessment)
        self.assertEqual(validate_process_milestone_decision(decision), decision)
        proposed = build_process_checkpoint(
            baseline=baseline, sequence=1, predecessor_checkpoint=None,
            lifecycle_state="PROPOSED", plan_root=h("plan"),
            milestone_assessments=[], milestone_decisions=[], active_work_ids=[],
            hold_codes=[], evidence_roots=[], decision_roots=[],
            journal_head_root=h("journal-1"),
        )
        ready = build_process_checkpoint(
            baseline=baseline, sequence=2, predecessor_checkpoint=proposed,
            lifecycle_state="READY", plan_root=h("plan"),
            milestone_assessments=[], milestone_decisions=[], active_work_ids=[],
            hold_codes=[], evidence_roots=[], decision_roots=[],
            journal_head_root=h("journal-2"),
        )
        active = build_process_checkpoint(
            baseline=baseline, sequence=3, predecessor_checkpoint=ready,
            lifecycle_state="ACTIVE", plan_root=h("plan"),
            milestone_assessments=[], milestone_decisions=[],
            active_work_ids=["WORK.PROCESS.CODE"], hold_codes=[],
            evidence_roots=[], decision_roots=[], journal_head_root=h("journal-3"),
        )
        awaiting = build_process_checkpoint(
            baseline=baseline, sequence=4, predecessor_checkpoint=active,
            lifecycle_state="AWAITING_ACCEPTANCE", plan_root=h("plan"),
            milestone_assessments=[assessment], milestone_decisions=[],
            active_work_ids=[], hold_codes=[], evidence_roots=[h("targeted-evidence")],
            decision_roots=[], journal_head_root=h("journal-4"),
        )
        accepted = build_process_checkpoint(
            baseline=baseline, sequence=5, predecessor_checkpoint=awaiting,
            lifecycle_state="ACCEPTED", plan_root=h("plan"),
            milestone_assessments=[assessment], milestone_decisions=[decision],
            active_work_ids=[], hold_codes=[], evidence_roots=[h("targeted-evidence")],
            decision_roots=[decision["milestone_decision_root"]],
            journal_head_root=h("journal-5"),
        )
        self.assertEqual(validate_process_checkpoint(accepted), accepted)
        self.assertFalse(accepted["execution_authorized"])
        self.assertFalse(decision["decision_grants_effect_authority"])

    def test_replan_schedule_observatory_and_thr_projection(self) -> None:
        locality = self.locality()
        catalog = self.catalog()
        capsule = self.execution_capsule()
        baseline = self.baseline(catalog, locality, [capsule["execution_capsule_root"]])
        milestone = self.milestone(baseline)
        assessment = self.assessment(milestone, self.evaluation(catalog))
        proposed = build_process_checkpoint(
            baseline=baseline, sequence=1, predecessor_checkpoint=None,
            lifecycle_state="PROPOSED", plan_root=h("plan-1"),
            milestone_assessments=[], milestone_decisions=[], active_work_ids=[],
            hold_codes=[], evidence_roots=[], decision_roots=[],
            journal_head_root=h("journal-1"),
        )
        ready = build_process_checkpoint(
            baseline=baseline, sequence=2, predecessor_checkpoint=proposed,
            lifecycle_state="READY", plan_root=h("plan-1"),
            milestone_assessments=[], milestone_decisions=[], active_work_ids=[],
            hold_codes=[], evidence_roots=[], decision_roots=[],
            journal_head_root=h("journal-2"),
        )
        active = build_process_checkpoint(
            baseline=baseline, sequence=3, predecessor_checkpoint=ready,
            lifecycle_state="ACTIVE", plan_root=h("plan-1"),
            milestone_assessments=[], milestone_decisions=[],
            active_work_ids=["WORK.PROCESS.CODE"], hold_codes=[], evidence_roots=[],
            decision_roots=[], journal_head_root=h("journal-3"),
        )
        blocked = build_process_checkpoint(
            baseline=baseline, sequence=4, predecessor_checkpoint=active,
            lifecycle_state="BLOCKED", plan_root=h("plan-1"),
            milestone_assessments=[assessment], milestone_decisions=[],
            active_work_ids=[], hold_codes=["EXTERNAL_REVIEW_PENDING"],
            evidence_roots=[h("targeted-evidence")], decision_roots=[],
            journal_head_root=h("journal-4"),
        )
        replan = build_governed_replan(
            predecessor_checkpoint=blocked,
            successor_plan_root=h("plan-2"),
            reason_code="REVIEW_FEEDBACK_BATCH",
            scope_delta={"added": ["WORK.DOCS"], "removed": [],
                         "changed": ["WORK.PROCESS.CODE"]},
            affected_dependency_ids=["MILESTONE.C1"],
            invalidated_evidence_roots=[h("targeted-evidence")],
            retained_evidence_roots=[h("static-evidence")],
            unresolved_work_ids=["WORK.PROCESS.CODE"],
            unresolved_dispositions=[{
                "work_id": "WORK.PROCESS.CODE", "disposition": "RETAINED",
                "reason_code": "REPAIR_REQUIRED", "successor_work_id": "WORK.PROCESS.CODE.V2",
                "evidence_root": None,
            }],
        )
        schedule = build_process_standards_schedule(
            catalog=catalog,
            subject_root=h("deliverable-subject"),
            event_facts=[{
                "event_id": "EVENT.ARCHITECTURE.1", "sequence": 1,
                "trigger": "ARCHITECTURE_CHANGE", "event_root": h("event-1"),
            }],
            last_satisfied=[],
            invalidations=[],
        )
        observatory = build_process_observatory(
            checkpoint=blocked,
            standards_schedule=schedule,
            artifact_statuses=[{
                "artifact_id": "PROCESS.CODE",
                "implementation_root": h("implementation"),
                "test_evidence_roots": [h("targeted-evidence")],
                "review_root": None,
                "acceptance_root": None,
            }],
            replan_roots=[replan["replan_root"]],
        )
        self.assertEqual(validate_process_standards_schedule(schedule), schedule)
        self.assertEqual(validate_process_observatory(observatory), observatory)
        courthouse_binding = build_courthouse_process_binding(
            baseline=baseline, checkpoint=blocked, execution_capsule=capsule,
            requested_surface="COURTHOUSE.VNEXT.EXECUTE",
            authority_policy_root=h("courthouse-authority-policy"),
            native_runner_binding_root=h("courthouse-runner"),
        )
        self.assertEqual(validate_courthouse_process_binding(courthouse_binding),
                         courthouse_binding)
        self.assertFalse(courthouse_binding["dispatch_authorized"])
        manifest = build_process_thr_manifest(
            baseline=baseline,
            locality_binding=locality,
            checkpoint=blocked,
            milestones=[milestone],
            assessments=[assessment],
            decisions=[],
            standards_evaluation_roots=[self.evaluation(catalog)["evaluation_root"]],
            evidence_receipt_roots=[h("targeted-evidence")],
            interpretation_profile_root=h("interpretation-profile"),
        )
        payloads = {
            "PROCESS-BASELINE.json": canonical_bytes(baseline),
            "PROCESS-CHECKPOINT.json": canonical_bytes(blocked),
            "PROCESS-LOCALITY.json": canonical_bytes(locality),
            "milestones/MILESTONE.C1.json": canonical_bytes(milestone),
            "assessments/MILESTONE.C1.json": canonical_bytes(assessment),
        }
        self.assertEqual(verify_thr_manifest(manifest, payloads=payloads), manifest)
        self.assertEqual(schedule["status"], "REVIEW_DUE")
        self.assertEqual(observatory["human_projection"]["state"], "BLOCKED")
        self.assertFalse(observatory["projection_is_authority"])
        self.assertEqual(manifest["locality"]["permission_granted"], False)


if __name__ == "__main__":
    unittest.main()

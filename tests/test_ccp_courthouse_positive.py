from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from uclop.canonical import root
from ucm.ccp_admissibility import (
    build_chc_thr_correspondence,
    build_current_use_snapshot,
    build_enforcement_perimeter,
    build_evidence_snapshot,
    build_jurisdiction_profile,
    evaluate_current_admissibility,
)
from ucm.ccp_courthouse import (
    build_courthouse_admission_envelope,
    build_pippi_admission_status,
    compile_admissible_workflow_submission,
    validate_admissible_workflow_result,
    validate_admissible_workflow_submission,
)
from ucm.capabilities import invoke
from ucm.system import capability_registry

from tests.test_courthouse_workflow import BOUNDARY, gate, request


ROOT = Path(__file__).resolve().parents[1]


def h(label: str) -> str:
    return root({"ccp-courthouse": label})


def fixture() -> tuple[dict, dict, dict]:
    workflow_request = request()
    subject = workflow_request["subject_root"]
    policy = workflow_request["policy_pack_roots"][0]
    schema_registry = h("schema-registry")
    trust = h("trust")
    checkpoint = h("checkpoint")
    operation = workflow_request["operation_id"]
    jurisdiction = build_jurisdiction_profile(
        profile_id="CCP.COURTHOUSE.V0_1",
        application_id=workflow_request["application_id"],
        subject_root=subject,
        state_boundary_id="EXACT_ARCHIVE",
        state_root=subject,
        manifest_root=h("manifest"),
        path_policy="EXACT_ARCHIVE_MEMBERS_V1",
        governance_jurisdiction_root=workflow_request["identity_binding"][
            "jurisdiction_root"],
        bound_policy_root=policy,
        bound_schema_registry_root=schema_registry,
        bound_trust_root=trust,
        transition_rule_root=h("transition"),
        allowed_operations=[operation],
        evidence_modes=["LOCAL"])
    perimeter = build_enforcement_perimeter(
        perimeter_id="CCP.COURTHOUSE.LOCAL",
        jurisdiction_profile_root=jurisdiction["jurisdiction_profile_root"],
        adapter_root=h("adapter"),
        intercepted_operations=[operation],
        excluded_bypass_classes=[],
        continuing_use_policy="LAUNCH_ONLY_RECHECK_REQUIRED",
        qualification_status="QUALIFIED_SCOPED")
    correspondence = build_chc_thr_correspondence(
        correspondence_id="CCP.COURTHOUSE.CHC.THR",
        correspondence_version="v0.1",
        chc_source_root=h("chc-source"),
        chc_profile_root=h("chc-profile"),
        thr_contract_root=h("thr-contract"))
    status_ids = {domain: f"STATUS.{domain.upper()}" for domain in (
        "checkpoint", "policy", "revocation", "schema", "semantic", "state")}
    observations = {
        "checkpoint": "CURRENT", "policy": "CURRENT",
        "revocation": "CURRENT_CLEAR", "schema": "CURRENT",
        "semantic": "CURRENT", "state": "CURRENT",
    }
    rows = [{
        "evidence_id": evidence_id,
        "evidence_kind": f"STATUS_{domain.upper()}",
        "subject_root": subject,
        "evidence_root": h(f"status-{domain}"),
        "source_mode": "LOCAL",
        "verification_status": "PASS",
        "observed_epoch": 100,
        "valid_until_epoch": 110,
        "admissibility_status_claim": {
            "domain": domain, "observed_status": observations[domain]},
    } for domain, evidence_id in status_ids.items()]
    evidence = build_evidence_snapshot(
        snapshot_id="CCP.COURTHOUSE.EVIDENCE.1",
        subject_root=subject,
        state_identity_root=subject,
        semantic_identity_root=h("semantic"),
        jurisdiction_profile_root=jurisdiction["jurisdiction_profile_root"],
        enforcement_perimeter_root=perimeter["enforcement_perimeter_root"],
        active_policy_root=policy,
        active_schema_registry_root=schema_registry,
        active_trust_root=trust,
        checkpoint_root=checkpoint,
        checkpoint_sequence=1,
        persistent_maximum_sequence=1,
        authenticated_epoch=100,
        evidence=rows,
        status_evidence_ids=status_ids,
        unresolved_requirements=[])
    requested_effects = sorted({row["effect_class"]
                                for row in workflow_request["requested_capabilities"]})
    current_use = build_current_use_snapshot(
        request_id="CCP.COURTHOUSE.REQUEST.1",
        operation=operation,
        subject_root=subject,
        target_root=workflow_request["request_root"],
        handler_root=h("handler"), runtime_root=h("runtime"),
        dependency_closure_root=h("dependencies"),
        state_identity_root=subject,
        semantic_identity_root=h("semantic"),
        jurisdiction_profile_root=jurisdiction["jurisdiction_profile_root"],
        enforcement_perimeter_root=perimeter["enforcement_perimeter_root"],
        correspondence_root=correspondence["correspondence_root"],
        evidence_snapshot_root=evidence["evidence_snapshot_root"],
        active_policy_root=policy,
        active_schema_registry_root=schema_registry,
        active_trust_root=trust,
        checkpoint_root=checkpoint,
        authenticated_epoch=100,
        requested_effect_classes=requested_effects,
        max_steps=100,
        max_evidence_rows=8)
    anchors = {
        "expected_subject_root": subject,
        "expected_jurisdiction_profile_root":
            jurisdiction["jurisdiction_profile_root"],
        "expected_enforcement_perimeter_root":
            perimeter["enforcement_perimeter_root"],
        "expected_correspondence_root": correspondence["correspondence_root"],
        "expected_policy_root": policy,
        "expected_schema_registry_root": schema_registry,
        "expected_trust_root": trust,
        "expected_checkpoint_root": checkpoint,
    }
    decision = evaluate_current_admissibility(
        current_use_snapshot=current_use,
        evidence_snapshot=evidence,
        jurisdiction_profile=jurisdiction,
        enforcement_perimeter=perimeter,
        correspondence=correspondence,
        **anchors)
    envelope = build_courthouse_admission_envelope(
        workflow_request=workflow_request,
        acceptance_case_root=h("acceptance-case"),
        work_unit_root=h("work-unit"),
        jurisdiction_profile=jurisdiction,
        enforcement_perimeter=perimeter,
        correspondence=correspondence,
        evidence_snapshot=evidence,
        current_use_snapshot=current_use,
        decision=decision,
        **anchors)
    submission = compile_admissible_workflow_submission(
        workflow_request=workflow_request, admission_envelope=envelope)
    return workflow_request, envelope, submission


class CcpCourthousePositiveTests(unittest.TestCase):
    def test_pippi_builds_exact_non_authorizing_submission(self) -> None:
        workflow_request, envelope, submission = fixture()
        self.assertEqual("ADMISSIBLE_FOR_COURTHOUSE_PREFLIGHT",
                         envelope["admission_status"])
        self.assertFalse(envelope["effect_authorized"])
        self.assertEqual(submission,
                         validate_admissible_workflow_submission(submission))
        self.assertEqual("NOT_DISPATCHED", submission["dispatch_status"])
        self.assertEqual("EXTERNAL_RESOLUTION_REQUIRED",
                         submission["courthouse_lattice_status"])
        self.assertEqual(workflow_request["request_root"],
                         submission["workflow_request"]["request_root"])

    def test_pippi_status_is_human_visible_and_non_authorizing(self) -> None:
        _, _, submission = fixture()
        status = build_pippi_admission_status(submission=submission)
        self.assertEqual("CURRENT_ADMIT", status["admissibility"])
        self.assertEqual("EXTERNAL_NOT_ESTABLISHED", status["authority"])
        self.assertEqual("NOT_DISPATCHED", status["execution"])
        self.assertFalse(status["projection_is_evidence"])
        self.assertFalse(status["projection_is_authority"])

    def test_bound_g1_result_imports_without_creating_authority(self) -> None:
        workflow_request, _, submission = fixture()
        workflow = submission["compiled_workflow"]
        g1 = gate("G1_SENTINEL", workflow["workflow_root"], "GENESIS", [],
                  submission["required_g1_evidence_roots"])
        g2 = gate("G2_WITNESS", workflow["workflow_root"], g1["receipt_root"],
                  ["PROCESS", "WRITE_WORKSPACE"], [h("effect")])
        g3 = gate("G3_DIAGNOSTIC", workflow["workflow_root"], g2["receipt_root"],
                  ["PROCESS", "WRITE_WORKSPACE"], [h("diagnostic")])
        body = {
            "schema": "mosaic.ucm.aok-vnext-workflow-result.v0.1",
            "workflow_root": workflow["workflow_root"],
            "request_root": workflow_request["request_root"],
            "courthouse_identity_root": "4" * 64,
            "selected_realization_root": "5" * 64,
            "selected_executor_root": "6" * 64,
            "g1": g1, "g2": g2, "g3": g3,
            "obligation_dispositions": [
                {"obligation_id": "ARCHITECTURE_FIDELITY", "status": "PASS",
                 "evidence_roots": ["7" * 64]},
                {"obligation_id": "CROSS_PLATFORM_TESTS", "status": "PASS",
                 "evidence_roots": ["8" * 64]},
            ],
            "cm2_evaluated": True,
            "expected_journal_head": {"sequence": 0, "head": "GENESIS"},
            "successor_journal_head": {"sequence": 1, "head": "9" * 64},
            "terminal_status": "PASS",
            **BOUNDARY,
        }
        result = {**body, "result_root": root(body)}
        imported = validate_admissible_workflow_result(
            submission=submission, result=result)
        self.assertEqual("PASS_BOUND_CORRESPONDENCE", imported["status"])
        self.assertFalse(imported["effect_authorized_by_ucm"])

    def test_public_abi_exposes_the_same_submission_and_status(self) -> None:
        workflow_request, envelope, submission = fixture()
        compiled = invoke({
            "schema": "mosaic.ucm.request.v0.1",
            "surface": "COMPILE_ADMISSIBLE_COURTHOUSE_WORKFLOW",
            "payload": {"workflow_request": workflow_request,
                        "admission_envelope": envelope},
            "request_id": "compile-admissible-workflow",
        })["result"]
        self.assertEqual(submission, compiled)
        projected = invoke({
            "schema": "mosaic.ucm.request.v0.1",
            "surface": "PROJECT_COURTHOUSE_ADMISSION_STATUS",
            "payload": {"submission": submission},
            "request_id": "project-admission-status",
        })["result"]
        self.assertEqual(build_pippi_admission_status(submission=submission),
                         projected)
        surfaces = {row["name"]: row for row in capability_registry()["surfaces"]}
        self.assertEqual("PURE_COMPUTATION",
                         surfaces["COMPILE_ADMISSIBLE_COURTHOUSE_WORKFLOW"][
                             "effect_scope"])
        self.assertEqual("PURE_COMPUTATION",
                         surfaces["PROJECT_COURTHOUSE_ADMISSION_STATUS"][
                             "effect_scope"])

    def test_role_named_cli_projects_same_submission_and_status(self) -> None:
        workflow_request, envelope, submission = fixture()
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            request_path = base / "request.json"
            envelope_path = base / "admission.json"
            submission_path = base / "submission.json"
            status_path = base / "status.json"
            request_path.write_text(json.dumps(workflow_request), encoding="utf-8")
            envelope_path.write_text(json.dumps(envelope), encoding="utf-8")
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            subprocess.run([
                sys.executable, "-m", "ucm.cli",
                "courthouse-compile-admissible", str(request_path),
                str(envelope_path), str(submission_path),
            ], cwd=ROOT, env=env, check=True, capture_output=True, text=True)
            subprocess.run([
                sys.executable, "-m", "ucm.cli",
                "courthouse-admission-status", str(submission_path),
                str(status_path),
            ], cwd=ROOT, env=env, check=True, capture_output=True, text=True)
            self.assertEqual(submission,
                             json.loads(submission_path.read_text(encoding="utf-8")))
            self.assertEqual(build_pippi_admission_status(submission=submission),
                             json.loads(status_path.read_text(encoding="utf-8")))

    def test_governed_program_records_rebuild_exactly(self) -> None:
        completed = subprocess.run([
            sys.executable, "tools/build_ccp_courthouse_program.py", "--check",
        ], cwd=ROOT, check=True, capture_output=True, text=True)
        result = json.loads(completed.stdout)
        self.assertEqual("PASS", result["status"])
        self.assertEqual(7, result["records"])


if __name__ == "__main__":
    unittest.main()

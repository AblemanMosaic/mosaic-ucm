"""Positive Stage I4 c3 construction and interface-parity tests."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uclop.canonical import canonical_bytes, root
from ucm.amcas import BOUNDARY
from ucm.artifacts import deterministic_zip
from ucm.capabilities import invoke
from ucm.journal import CampaignJournal
from ucm.native_runner import (BINDING_SCHEMA, NATIVE_OWNER, RECEIPT_SCHEMA,
    build_preflight, build_unavailable_binding, validate_terminal_receipt)
from ucm.operation_state import derive_operation_state, validate_operation_state
from ucm.stage3 import instruction, plan_template
from ucm.stage4 import REVIEW_POLICY_ID, REVIEW_SCHEMA
from ucm.stage4_c3 import (
    CONTEXT_SCHEMA,
    RELATION_MAP_SCHEMA,
    REVIEW_ARCHIVE_ROLE,
    REVIEW_ARCHIVE_SCHEMA,
    REVIEW_POLICY_SCHEMA,
    build_run_contract,
    build_terminal_refusal,
    derive_eligibility,
)
from ucm.stage4_semantics import validate_run_contract_shape, validate_terminal_operation


class StageI4C3PositiveTests(unittest.TestCase):
    def setUp(self):
        relation = {
            "provider_application_id": "APP.PROVIDER",
            "consumer_application_id": "APP.ONE",
            "interface_id": "READ_EVIDENCE.V1",
            "schema_root": "9" * 64,
            "required": True,
            "status": "MATCHED",
        }
        self.instruction = instruction(
            application={"id": "APP.ONE", "thread_id": "thread-one"},
            pipeline_release_sha256="1" * 64,
            predecessor_portfolio_sha256="2" * 64,
            portfolio_status_root="3" * 64,
            preflight_root="4" * 64,
            court_root="5" * 64,
            court_evidence_sha256="6" * 64,
            stage_i1_artifact_sha256="7" * 64,
            stage_i2_artifact_sha256="8" * 64,
            stage_i1_status="READY_FOR_REVIEW",
            matched_relations=[relation],
        )
        self.plan = plan_template(self.instruction)
        self.plan["relation_dispositions"][0].update(
            {"disposition": "PLAN", "reason": "EXACT_CASE_COVERAGE"})
        self.plan["capability_projections"] = [{
            "capability_id": "CAP.ONE", "native_route": "native.one",
            "ucm_projection": "shadow.one", "effect_class": "READ_ONLY",
            "input_schema_root": "a" * 64, "output_schema_root": "b" * 64,
            "control_plane_disposition": "RETAIN", "case_ids": ["CASE.ONE"],
        }]
        self.plan["correspondence_cases"] = [{
            "id": "CASE.ONE", "capability_id": "CAP.ONE", "input_root": "c" * 64,
            "expected_native_decision": "PASS", "expected_ucm_decision": "PASS",
            "expected_native_result_root": "d" * 64,
            "expected_ucm_result_root": "d" * 64, "expected_equivalence": True,
            "evidence_requirements": ["NATIVE_RESULT", "UCM_RESULT"],
        }]
        self.plan["plan_root"] = root({key: value for key, value in self.plan.items()
                                       if key != "plan_root"})
        disposition_body = {
            "schema": REVIEW_SCHEMA, "review_class": "INDEPENDENT_REVIEW",
            "reviewer_policy_id": REVIEW_POLICY_ID,
            "reviewer_identity_root": "e" * 64,
            "reviewed_subject_root": "f" * 64,
            "reviewed_qualification_root": "1" * 64,
            "reviewed_source_root": "2" * 64,
            "applications": [{"application_id": "APP.ONE",
                "instruction_root": self.instruction["instruction_root"],
                "plan_root": self.plan["plan_root"]}],
            "verdict": "QUALIFIED_RECOMMENDATION_ONLY", "findings": [],
            "limitations": [], **BOUNDARY,
        }
        disposition = {**disposition_body,
                       "disposition_root": root(disposition_body)}
        findings_body = {"schema": "mosaic.ucm.stage-i4-review-findings.v0.1",
            "verdict": disposition["verdict"], "findings": [], **BOUNDARY}
        findings = {**findings_body, "findings_root": root(findings_body)}
        recompute_body = {"schema": "mosaic.ucm.stage-i4-review-recompute.v0.1",
            "reviewed_subject_root": disposition["reviewed_subject_root"],
            "reviewed_source_root": disposition["reviewed_source_root"],
            "reviewed_qualification_root": disposition["reviewed_qualification_root"],
            "status": "PASS", **BOUNDARY}
        recompute = {**recompute_body, "recompute_root": root(recompute_body)}
        payloads = {
            "REPORT.md": b"# Independent review\n\nVerdict: `QUALIFIED_RECOMMENDATION_ONLY`\n",
            "FINDINGS.json": canonical_bytes(findings),
            "RECOMPUTE.json": canonical_bytes(recompute),
            "REVIEW-DISPOSITION.json": canonical_bytes(disposition),
        }
        self.review = deterministic_zip(payloads, schema=REVIEW_ARCHIVE_SCHEMA,
                                        artifact_role=REVIEW_ARCHIVE_ROLE)
        policy_body = {
            "schema": REVIEW_POLICY_SCHEMA,
            "policy_id": "UCM.AMCAS.STAGE_I4.C3.REVIEW.v1",
            "reviewer_identity_root": "e" * 64,
            "accepted_review_classes": ["INDEPENDENT_REVIEW"],
            "expected_archive_sha256": hashlib.sha256(self.review).hexdigest(),
            "expected_subject_root": "f" * 64,
            "expected_source_root": "2" * 64,
            "expected_qualification_root": "1" * 64,
            "expected_disposition_root": disposition["disposition_root"],
            "expected_file_sha256": {
                path: hashlib.sha256(raw).hexdigest() for path, raw in payloads.items()
            },
            **BOUNDARY,
        }
        self.policy = {**policy_body, "policy_root": root(policy_body)}
        self.relation_id = root({
            "provider_application_id": "APP.PROVIDER",
            "consumer_application_id": "APP.ONE",
            "interface_id": "READ_EVIDENCE.V1",
            "schema_root": "9" * 64,
        })
        relation_body = {
            "schema": RELATION_MAP_SCHEMA, "application_id": "APP.ONE",
            "plan_root": self.plan["plan_root"],
            "relations": [{"relation_id": self.relation_id,
                "provider_application_id": "APP.PROVIDER",
                "consumer_application_id": "APP.ONE",
                "interface_id": "READ_EVIDENCE.V1", "schema_root": "9" * 64,
                "disposition": "PLAN"}],
            "case_dependencies": [{"case_id": "CASE.ONE",
                                    "relation_ids": [self.relation_id]}],
            **BOUNDARY,
        }
        self.relation_map = {**relation_body, "map_root": root(relation_body)}
        context_body = {
            "schema": CONTEXT_SCHEMA, "identity_root": "3" * 64,
            "session_root": "4" * 64, "jurisdiction_root": "5" * 64,
            "generation": 1, "policy_root": "6" * 64,
            "budget_root": "7" * 64, "rollback_root": "8" * 64, **BOUNDARY,
        }
        self.context = {**context_body, "context_root": root(context_body)}
        self.binding = build_unavailable_binding(
            runner_id="AOK.COURTHOUSE.HEADLESS.RUNNER",
            provider="CODEX_HEADLESS_LOCAL",
            transport="FIXED_ARGV_LOCAL_PROCESS",
            source_sha256="388ff1d59f77d4143c426a7833e5a63ccca7e9ead5c81bc35fbdc6b37922aa99",
            source_manifest_root="30834ac032528a7c3350d8db0c791cf910979fa88eb1d0d144aa4ad217b7d3aa",
            runner_contract_sha256="ff240ae1dc05680dbdae1f1016a47fabf5f525c28d116993cee1079467c952a3",
            console_contract_sha256="0c8c46415e3b6973b6633291704e2ce586794dd5acf072c8077a6a1a956cc8f1",
        )
        self.selection = {
            "mode": "FULL", "selected_case_ids": ["CASE.ONE"],
            "omitted_case_ids": [], "covered_relation_ids": [self.relation_id],
            "selection_basis_roots": [], "rationale": "FULL_CASE_SET",
        }

    def _build(self):
        eligibility = derive_eligibility(
            instruction=self.instruction, plan=self.plan,
            review_archive=self.review, review_policy=self.policy)
        contract = build_run_contract(
            eligibility=eligibility, instruction=self.instruction, plan=self.plan,
            review_archive=self.review, review_policy=self.policy,
            relation_case_map=self.relation_map, execution_context=self.context,
            native_runner_binding=self.binding, selection=self.selection)
        return eligibility, contract

    def test_exact_review_relation_and_native_runner_binding(self):
        eligibility, contract = self._build()
        self.assertTrue(eligibility["eligible_for_shadow_execution"])
        self.assertEqual(contract["case_schedule"][0]["relation_ids"],
                         [self.relation_id])
        self.assertEqual(contract["native_runner_binding"]["binding_status"],
                         "UNAVAILABLE")
        self.assertFalse(contract["execution_authorized"])

    def test_terminal_refusal_is_one_bound_operation(self):
        _, contract = self._build()
        terminal = build_terminal_refusal(run_contract=contract)
        self.assertEqual(validate_run_contract_shape(contract), contract)
        self.assertEqual(validate_terminal_operation(terminal,
                                                     expected_run_contract=contract), terminal)
        self.assertEqual(terminal["terminal_status"], "REFUSED")
        self.assertEqual(terminal["g1_sentinel"]["decision"], "REFUSE")
        self.assertEqual(terminal["g2_witness"]["case_results"], [])
        self.assertEqual(terminal["g3_diagnostic"]["classification"], "REFUSED")

    def test_agent_surfaces_equal_direct_results(self):
        eligibility, contract = self._build()
        encoded = base64.b64encode(self.review).decode("ascii")
        derived = invoke({"schema": "mosaic.ucm.request.v0.1",
            "surface": "DERIVE_TRUSTED_STAGE_I4_ELIGIBILITY",
            "payload": {"instruction": self.instruction, "plan": self.plan,
                        "review_archive_base64": encoded,
                        "review_policy": self.policy}, "request_id": "c3-eligibility"})
        built = invoke({"schema": "mosaic.ucm.request.v0.1",
            "surface": "BUILD_STAGE_I4_EXACT_RUN_CONTRACT",
            "payload": {"eligibility": eligibility, "instruction": self.instruction,
                "plan": self.plan, "review_archive_base64": encoded,
                "review_policy": self.policy, "relation_case_map": self.relation_map,
                "execution_context": self.context,
                "native_runner_binding": self.binding, "selection": self.selection},
            "request_id": "c3-contract"})
        terminal = invoke({"schema": "mosaic.ucm.request.v0.1",
            "surface": "BUILD_STAGE_I4_TERMINAL_REFUSAL",
            "payload": {"run_contract": contract}, "request_id": "c3-terminal"})
        preflight_direct = build_preflight(
            run_contract_root=contract["run_contract_root"],
            execution_context_root=self.context["context_root"],
            binding=self.binding, requested_effect_classes=["READ_ONLY"],
            execution_authorized=False)
        preflight = invoke({"schema": "mosaic.ucm.request.v0.1",
            "surface": "BUILD_NATIVE_HEADLESS_RUNNER_PREFLIGHT",
            "payload": {"binding": self.binding, "execution_authorized": False,
                "execution_context_root": self.context["context_root"],
                "requested_effect_classes": ["READ_ONLY"],
                "run_contract_root": contract["run_contract_root"]},
            "request_id": "c3-native-preflight"})
        events = [{"event_id": "event-g1", "transition": "G1_REFUSED",
            "run_contract_root": contract["run_contract_root"],
            "receipt_root": terminal["result"]["g1_sentinel"]["receipt_root"]}]
        state_direct = derive_operation_state(operation_id="operation-one",
            run_contract_root=contract["run_contract_root"], events=events)
        state = invoke({"schema": "mosaic.ucm.request.v0.1",
            "surface": "DERIVE_STAGE_I4_OPERATION_STATE",
            "payload": {"operation_id": "operation-one",
                "run_contract_root": contract["run_contract_root"], "events": events},
            "request_id": "c3-operation-state"})
        validated = invoke({"schema": "mosaic.ucm.request.v0.1",
            "surface": "VALIDATE_STAGE_I4_OPERATION_STATE",
            "payload": {"state": state_direct}, "request_id": "c3-state-validate"})
        bound_body = {"schema": BINDING_SCHEMA, "native_owner": NATIVE_OWNER,
            "runner_id": "AOK.COURTHOUSE.HEADLESS.RUNNER",
            "provider": "CODEX_HEADLESS_LOCAL",
            "transport": "FIXED_ARGV_LOCAL_PROCESS",
            "source_sha256": "1" * 64, "source_manifest_root": "2" * 64,
            "runner_contract_sha256": "3" * 64,
            "console_contract_sha256": "4" * 64,
            "installed_lattice_root": "5" * 64, "adapter_root": "6" * 64,
            "binding_status": "BOUND", "reason_code": "NATIVE_RUNNER_BOUND",
            "effect_executor": NATIVE_OWNER, **BOUNDARY}
        bound = {**bound_body, "binding_root": root(bound_body)}
        allowed = build_preflight(run_contract_root=contract["run_contract_root"],
            execution_context_root=self.context["context_root"], binding=bound,
            requested_effect_classes=["READ_ONLY"], execution_authorized=True)
        receipt_body = {"schema": RECEIPT_SCHEMA,
            "preflight_root": allowed["preflight_root"],
            "native_owner": NATIVE_OWNER, "provider": "CODEX_HEADLESS_LOCAL",
            "lease_ref": "7" * 64, "terminal_event_ref": "8" * 64,
            "terminal_state": "COMPLETED", "result_root": "9" * 64,
            "observed_effect_classes": ["READ_ONLY"],
            "completion_status": "COMPLETE", "recovery_status": "NOT_REQUIRED",
            **BOUNDARY}
        receipt = {**receipt_body, "receipt_root": root(receipt_body)}
        receipt_validated = invoke({"schema": "mosaic.ucm.request.v0.1",
            "surface": "VALIDATE_NATIVE_HEADLESS_RUNNER_RECEIPT",
            "payload": {"preflight": allowed, "receipt": receipt},
            "request_id": "c3-native-receipt"})
        self.assertEqual(derived["result"], eligibility)
        self.assertEqual(built["result"], contract)
        self.assertEqual(terminal["result"], build_terminal_refusal(run_contract=contract))
        self.assertEqual(preflight["result"], preflight_direct)
        self.assertEqual(state["result"], state_direct)
        self.assertEqual(validated["result"], validate_operation_state(state_direct))
        self.assertEqual(receipt_validated["result"],
                         validate_terminal_receipt(receipt,
                                                   expected_preflight=allowed))

    def test_journal_identical_retry_returns_existing_event(self):
        with tempfile.TemporaryDirectory() as folder:
            journal = CampaignJournal(Path(folder) / "journal")
            journal.initialize()
            request = {"event_id": "same", "event_type": "CAMPAIGN_CREATED",
                       "actor": {"kind": "SYSTEM", "mosaic_id": None,
                                 "session_id": None},
                       "payload": {"campaign": "C3"}}
            first = journal.append(**request)
            second = journal.append(**request)
            self.assertEqual(first, second)
            self.assertEqual(len(journal.verify()), 1)

    def test_cli_exposes_native_preflight_and_operation_state(self):
        _, contract = self._build()
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            contract_path = workspace / "contract.json"
            binding_path = workspace / "binding.json"
            preflight_path = workspace / "preflight.json"
            events_path = workspace / "events.json"
            state_path = workspace / "state.json"
            contract_path.write_bytes(canonical_bytes(contract))
            binding_path.write_bytes(canonical_bytes(self.binding))
            events = [{"event_id": "event-g1", "transition": "G1_REFUSED",
                "run_contract_root": contract["run_contract_root"],
                "receipt_root": build_terminal_refusal(
                    run_contract=contract)["g1_sentinel"]["receipt_root"]}]
            events_path.write_bytes(canonical_bytes(events))
            environment = {**os.environ,
                "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
            preflight_run = subprocess.run([sys.executable, "-m", "ucm.cli",
                "native-runner-preflight", str(contract_path), str(binding_path),
                str(preflight_path)], cwd=workspace, env=environment,
                capture_output=True, text=True)
            self.assertEqual(preflight_run.returncode, 0,
                             preflight_run.stdout + preflight_run.stderr)
            self.assertEqual(json.loads(preflight_path.read_text(encoding="utf-8")),
                build_preflight(run_contract_root=contract["run_contract_root"],
                    execution_context_root=self.context["context_root"],
                    binding=self.binding, requested_effect_classes=["READ_ONLY"],
                    execution_authorized=False))
            state_run = subprocess.run([sys.executable, "-m", "ucm.cli",
                "stage4-c3-derive-operation-state", "operation-cli",
                contract["run_contract_root"], str(events_path), str(state_path)],
                cwd=workspace, env=environment, capture_output=True, text=True)
            self.assertEqual(state_run.returncode, 0,
                             state_run.stdout + state_run.stderr)
            self.assertEqual(json.loads(state_path.read_text(encoding="utf-8")),
                derive_operation_state(operation_id="operation-cli",
                    run_contract_root=contract["run_contract_root"], events=events))


if __name__ == "__main__":
    unittest.main()

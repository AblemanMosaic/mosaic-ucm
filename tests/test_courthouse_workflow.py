from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from uclop.canonical import root
from ucm.courthouse_workflow import (compile_workflow_ir,
                                     validate_workflow_request,
                                     validate_workflow_result,
                                     verify_compiled_workflow)


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def rooted(body, field):
    return {**body, field: root(body)}


def request():
    body = {
        "schema": "mosaic.ucm.courthouse-workflow-request.v0.1",
        "request_id": "TERMINAL_UI_BUILD_001",
        "campaign_root": "1" * 64,
        "operation_id": "BUILD_WINDOWS_AND_LINUX",
        "application_id": "MOSAIC_TERMINAL_UI",
        "subject_root": "2" * 64,
        "expected_journal_head": {"sequence": 0, "head": "GENESIS"},
        "architecture_contract_root": "3" * 64,
        "architecture_candidate_root": "4" * 64,
        "work_package_root": "5" * 64,
        "objective": "Build deterministic Windows and Linux artifacts.",
        "cm1_obligations": [
            {"obligation_id": "ARCHITECTURE_FIDELITY",
             "obligation_root": "6" * 64,
             "evidence_kind": "STATIC_CHECK", "required": True},
            {"obligation_id": "CROSS_PLATFORM_TESTS",
             "obligation_root": "7" * 64,
             "evidence_kind": "TEST_RECEIPT", "required": True},
        ],
        "cm2_preferences": [
            {"preference_id": "MINIMIZE_ARTIFACT_SIZE",
             "objective_root": "8" * 64, "priority": 0},
        ],
        "requested_capabilities": [
            {"capability_id": "FILESYSTEM_BUILD",
             "effect_class": "WRITE_WORKSPACE", "budget_root": "9" * 64},
            {"capability_id": "PROCESS_TEST",
             "effect_class": "PROCESS", "budget_root": "a" * 64},
        ],
        "policy_pack_roots": ["b" * 64],
        "identity_binding": {
            "requester_mosaic_id_root": "c" * 64,
            "session_mosaic_id_root": "d" * 64,
            "jurisdiction_root": "e" * 64,
            "courthouse_identity_root": "4" * 64,
            "courthouse_protocol_root": "f" * 64,
        },
        "authority_ceiling": {**BOUNDARY,
                              "execution_authority_owner": "COURTHOUSE_VNEXT_EXTERNAL"},
    }
    return {**body, "request_root": root(body)}


def gate(gate_id, workflow_root, predecessor, effects, evidence):
    body = {
        "schema": "mosaic.ucm.aok-vnext-gate-receipt.v0.1",
        "gate": gate_id,
        "workflow_root": workflow_root,
        "decision": "PASS",
        "predecessor_receipt_root": predecessor,
        "observed_effect_classes": effects,
        "evidence_roots": evidence,
    }
    return {**body, "receipt_root": root(body)}


class CourthouseWorkflowTests(unittest.TestCase):
    def test_checked_in_protocol_contract_is_self_bound(self):
        contract = json.loads((ROOT / "spec/UCM-AOK-VNEXT-WORKFLOW-IR-CONTRACT.json")
                              .read_text(encoding="utf-8"))
        body = {key: value for key, value in contract.items()
                if key != "contract_root"}
        self.assertEqual(contract["contract_root"], root(body))
        self.assertEqual(contract["protocol_id"],
                         "UCM_AOK_VNEXT_WORKFLOW_IR_V0_1")
        self.assertFalse(contract["progress_is_evidence"])

    def test_compile_and_verify_are_deterministic_and_vnext_neutral(self):
        source = request()
        self.assertEqual(validate_workflow_request(source), source)
        first = compile_workflow_ir(source)
        second = compile_workflow_ir(source)
        self.assertEqual(first, second)
        self.assertEqual(verify_compiled_workflow(source, first), first)
        self.assertEqual(first["ccba_lattice_binding"]["binding_owner"],
                         "COURTHOUSE_VNEXT")
        self.assertEqual(first["realization_route"]["status"], "UNRESOLVED")
        self.assertIn("NOT_EXECUTOR_SELECTION", first["non_claims"])

    def test_positive_three_gate_result_import(self):
        source = request()
        workflow = compile_workflow_ir(source)
        g1 = gate("G1_SENTINEL", workflow["workflow_root"], "GENESIS", [],
                  ["1" * 64])
        g2 = gate("G2_WITNESS", workflow["workflow_root"], g1["receipt_root"],
                  ["PROCESS", "WRITE_WORKSPACE"], ["2" * 64])
        g3 = gate("G3_DIAGNOSTIC", workflow["workflow_root"], g2["receipt_root"],
                  ["PROCESS", "WRITE_WORKSPACE"], ["3" * 64])
        body = {
            "schema": "mosaic.ucm.aok-vnext-workflow-result.v0.1",
            "workflow_root": workflow["workflow_root"],
            "request_root": source["request_root"],
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
        imported = validate_workflow_result(source, workflow, result)
        self.assertEqual(imported["status"], "PASS_CORRESPONDENCE")
        self.assertEqual(imported["cm1_status"], "PASS")
        self.assertEqual(imported["cm2_status"], "EVALUATED")
        self.assertEqual(imported["authority_effect"], "NONE")

    def test_cli_compiles_the_same_workflow(self):
        source = request()
        with tempfile.TemporaryDirectory() as folder:
            request_path = Path(folder) / "request.json"
            output_path = Path(folder) / "workflow.json"
            request_path.write_text(json.dumps(source), encoding="utf-8")
            environment = {**__import__("os").environ,
                           "PYTHONPATH": str(ROOT / "src")}
            completed = subprocess.run(
                [sys.executable, "-m", "ucm.cli", "courthouse-compile-workflow",
                 str(request_path), str(output_path)],
                cwd=ROOT, env=environment, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0,
                             completed.stderr + completed.stdout)
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")),
                             compile_workflow_ir(source))


if __name__ == "__main__":
    unittest.main()

"""Positive end-to-end tests for the anchored Stage I4 c4 surface."""
from __future__ import annotations

from pathlib import Path
import base64
import json
import os
import subprocess
import tempfile
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root
from ucm.amcas import BOUNDARY
from ucm.capabilities import invoke
from ucm.native_runner_c4 import build_preflight, validate_preflight
from ucm.operation_state_c4 import derive_operation_state, validate_operation_state
from ucm.stage4_c4 import (
    AUTHORITY_POLICY_SCHEMA,
    TRUST_ANCHORS_SCHEMA,
    build_run_contract,
    build_terminal_refusal,
    validate_run_contract,
)
from ucm.stage4_semantics_c4 import (
    POSITIVE_CONTROL_SCHEMA,
    QUALIFICATION_SCHEMA,
    RUNTIME_RESULT_SCHEMA,
    validate_qualification,
    validate_terminal_operation,
)
from tests.test_stage4_c3_positive import StageI4C3PositiveTests


class StageI4C4PositiveTests(unittest.TestCase):
    def setUp(self):
        legacy = StageI4C3PositiveTests(
            "test_exact_review_relation_and_native_runner_binding")
        legacy.setUp()
        self.legacy = legacy
        self.eligibility, _ = legacy._build()
        authority_body = {
            "schema": AUTHORITY_POLICY_SCHEMA,
            "policy_id": "UCM.AMCAS.STAGE_I4.C4.AUTHORITY.NONE",
            "jurisdiction_root": legacy.context["jurisdiction_root"],
            "generation": 1, "execution_authorized": False,
            "allowed_effect_classes": [],
            "reason_code": "EXECUTION_AUTHORITY_NOT_GRANTED", **BOUNDARY,
        }
        self.authority = {
            **authority_body, "authority_policy_root": root(authority_body)}
        anchors_body = {
            "schema": TRUST_ANCHORS_SCHEMA,
            "anchor_id": "UCM.AMCAS.STAGE_I4.C4.TRUST.v1",
            "review_policy_root": legacy.policy["policy_root"],
            "execution_context_root": legacy.context["context_root"],
            "native_runner_binding_root": legacy.binding["binding_root"],
            "native_runner_source_sha256": legacy.binding["source_sha256"],
            "native_runner_source_manifest_root": legacy.binding["source_manifest_root"],
            "authority_policy_root": self.authority["authority_policy_root"],
            "jurisdiction_root": legacy.context["jurisdiction_root"], **BOUNDARY,
        }
        self.anchors = {
            **anchors_body, "trust_anchors_root": root(anchors_body)}
        self.contract = build_run_contract(
            eligibility=self.eligibility, instruction=legacy.instruction,
            plan=legacy.plan, review_archive=legacy.review,
            review_policy=legacy.policy, relation_case_map=legacy.relation_map,
            execution_context=legacy.context,
            native_runner_binding=legacy.binding, selection=legacy.selection,
            trust_anchors=self.anchors,
            expected_trust_anchors_root=self.anchors["trust_anchors_root"],
            execution_authority_policy=self.authority,
        )

    def test_anchored_contract_rederives_and_keeps_authority_none(self):
        checked = validate_run_contract(
            self.contract,
            expected_trust_anchors_root=self.anchors["trust_anchors_root"])
        self.assertEqual(checked, self.contract)
        self.assertFalse(checked["execution_authority_policy"]["execution_authorized"])
        self.assertEqual(checked["trust_anchors"], self.anchors)

    def test_preflight_derives_inputs_and_refuses_without_authority(self):
        preflight = build_preflight(
            run_contract=self.contract, trust_anchors=self.anchors,
            expected_trust_anchors_root=self.anchors["trust_anchors_root"],
            execution_authority_policy=self.authority)
        self.assertEqual(preflight["decision"], "REFUSE")
        self.assertEqual(preflight["requested_effect_classes"], ["READ_ONLY"])
        self.assertEqual(validate_preflight(preflight,
            expected_run_contract=self.contract,
            expected_trust_anchors_root=self.anchors["trust_anchors_root"]), preflight)

    def test_terminal_refusal_validates_full_gate_chain(self):
        terminal = build_terminal_refusal(
            run_contract=self.contract,
            expected_trust_anchors_root=self.anchors["trust_anchors_root"])
        self.assertEqual(validate_terminal_operation(
            terminal, expected_run_contract=self.contract,
            expected_trust_anchors_root=self.anchors["trust_anchors_root"]), terminal)
        self.assertEqual(terminal["g1_sentinel"]["decision"], "REFUSE")
        self.assertEqual(terminal["g2_witness"]["observed_effect_classes"], [])
        self.assertEqual(terminal["g3_diagnostic"]["classification"], "REFUSED")

    def test_agent_surfaces_match_direct_c4_results(self):
        legacy = self.legacy
        encoded = base64.b64encode(legacy.review).decode("ascii")
        contract_response = invoke({"schema": "mosaic.ucm.request.v0.1",
            "surface": "BUILD_STAGE_I4_ANCHORED_RUN_CONTRACT",
            "payload": {"eligibility": self.eligibility,
                "instruction": legacy.instruction, "plan": legacy.plan,
                "review_archive_base64": encoded, "review_policy": legacy.policy,
                "relation_case_map": legacy.relation_map,
                "execution_context": legacy.context,
                "native_runner_binding": legacy.binding,
                "selection": legacy.selection, "trust_anchors": self.anchors,
                "expected_trust_anchors_root": self.anchors["trust_anchors_root"],
                "execution_authority_policy": self.authority},
            "request_id": "c4-contract"})
        self.assertEqual(contract_response["result"], self.contract)
        preflight = invoke({"schema": "mosaic.ucm.request.v0.1",
            "surface": "BUILD_STAGE_I4_AUTHORITY_SAFE_PREFLIGHT",
            "payload": {"run_contract": self.contract,
                "trust_anchors": self.anchors,
                "expected_trust_anchors_root": self.anchors["trust_anchors_root"],
                "execution_authority_policy": self.authority},
            "request_id": "c4-preflight"})
        terminal = invoke({"schema": "mosaic.ucm.request.v0.1",
            "surface": "BUILD_STAGE_I4_RECEIPTED_REFUSAL",
            "payload": {"run_contract": self.contract,
                "expected_trust_anchors_root": self.anchors["trust_anchors_root"]},
            "request_id": "c4-terminal"})
        self.assertEqual(preflight["result"], build_preflight(
            run_contract=self.contract, trust_anchors=self.anchors,
            expected_trust_anchors_root=self.anchors["trust_anchors_root"],
            execution_authority_policy=self.authority))
        self.assertEqual(terminal["result"], build_terminal_refusal(
            run_contract=self.contract,
            expected_trust_anchors_root=self.anchors["trust_anchors_root"]))

    def test_operation_state_consumes_full_receipt(self):
        terminal = build_terminal_refusal(
            run_contract=self.contract,
            expected_trust_anchors_root=self.anchors["trust_anchors_root"])
        events = [{"event_id": "g1-refusal", "transition": "G1_REFUSED",
            "run_contract_root": self.contract["run_contract_root"],
            "receipt": terminal["g1_sentinel"]}]
        state = derive_operation_state(operation_id="op.c4",
            run_contract_root=self.contract["run_contract_root"], events=events)
        self.assertEqual(state["state"], "REFUSED")
        self.assertEqual(validate_operation_state(state), state)

    def test_role_named_cli_builds_preflight_and_receipt_state(self):
        terminal = build_terminal_refusal(run_contract=self.contract,
            expected_trust_anchors_root=self.anchors["trust_anchors_root"])
        events = [{"event_id": "g1-refusal", "transition": "G1_REFUSED",
            "run_contract_root": self.contract["run_contract_root"],
            "receipt": terminal["g1_sentinel"]}]
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            for name, value in (("contract.json", self.contract),
                    ("anchors.json", self.anchors), ("authority.json", self.authority),
                    ("events.json", events)):
                (work / name).write_bytes(canonical_bytes(value))
            environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
            preflight_path = work / "preflight.json"
            state_path = work / "state.json"
            preflight_run = subprocess.run([sys.executable, "-m", "ucm.cli",
                "stage4-build-authority-safe-preflight", str(work / "contract.json"),
                str(work / "anchors.json"), str(work / "authority.json"),
                self.anchors["trust_anchors_root"], str(preflight_path)],
                cwd=work, env=environment, capture_output=True, text=True)
            self.assertEqual(preflight_run.returncode, 0,
                             preflight_run.stdout + preflight_run.stderr)
            state_run = subprocess.run([sys.executable, "-m", "ucm.cli",
                "stage4-derive-receipt-state", "op.cli",
                self.contract["run_contract_root"], str(work / "events.json"),
                str(state_path)], cwd=work, env=environment,
                capture_output=True, text=True)
            self.assertEqual(state_run.returncode, 0,
                             state_run.stdout + state_run.stderr)
            self.assertEqual(json.loads(preflight_path.read_text(encoding="utf-8")),
                build_preflight(run_contract=self.contract,
                    trust_anchors=self.anchors,
                    expected_trust_anchors_root=self.anchors["trust_anchors_root"],
                    execution_authority_policy=self.authority))
            self.assertEqual(json.loads(state_path.read_text(encoding="utf-8")),
                derive_operation_state(operation_id="op.cli",
                    run_contract_root=self.contract["run_contract_root"], events=events))

    def test_positive_qualification_validates_every_runtime_field(self):
        source_root = "a" * 64
        tests = ["tests.test_stage4_c4_positive.StageI4C4PositiveTests"]
        runtime_body = {"schema": RUNTIME_RESULT_SCHEMA, "runtime": "CPython 3.12",
            "source_graph_root": source_root, "source_file_count": 1,
            "source_verified_before_and_after": True, "test_ids": tests,
            "test_count": 1, "test_set_root": root(tests), "failures": 0,
            "errors": 0, "skips": 0, "cache_policy": "CACHE_DISABLED",
            "status": "PASS", **BOUNDARY}
        runtime = {**runtime_body, "runtime_result_root": root(runtime_body)}
        control_body = {"schema": POSITIVE_CONTROL_SCHEMA,
            "control_class": "BUILDER_POSITIVE_ONLY", "source_root": source_root,
            "test_set_root": root(tests),
            "checks": [{"check": "POSITIVE_CONSTRUCTION", "status": "PASS"}],
            "status": "PASS", **BOUNDARY}
        control = {**control_body, "control_root": root(control_body)}
        state = derive_operation_state(operation_id="qualification",
            run_contract_root="b" * 64, events=[])
        body = {"schema": QUALIFICATION_SCHEMA,
            "qualification_class": "BUILDER_POSITIVE_QUALIFICATION",
            "source_root": source_root, "source_file_count": 1,
            "test_ids": tests, "test_count": 1, "test_set_root": root(tests),
            "semantic_contract_root": "c" * 64,
            "trust_anchors_root": self.anchors["trust_anchors_root"],
            "positive_control": control, "runtime_results": [runtime],
            "operation_state": state, "failures": 0, "errors": 0, "skips": 0,
            "status": "PASS", **BOUNDARY}
        qualification = {**body, "qualification_root": root(body)}
        self.assertEqual(validate_qualification(qualification,
            expected_source_root=source_root, expected_source_file_count=1,
            expected_test_ids=tests, expected_semantic_contract_root="c" * 64,
            expected_trust_anchors_root=self.anchors["trust_anchors_root"]),
            qualification)


if __name__ == "__main__":
    unittest.main()

"""Positive exact-wheel exercises; adversarial cases belong to the operator kit."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

from ucm.pippi_adaptive import build_turn_report, negotiate_host_mode, prepare_turn
from ucm.pippi_cmba import (CMBA_WHEEL_RELATIVE_PATH, CMBA_WHEEL_SHA256,
    build_cmba_turn_assessment, discover_cmba_binding, validate_cmba_turn_assessment)
from ucm.pippi_global import build_project
from ucm.pippi_portability import build_execution_context
from ucm.pippi_turn_record import build_turn_record


ROOT = Path(__file__).resolve().parents[1]
R1, R2, R3, R4 = (str(n) * 64 for n in range(1, 5))


def common_turn_fixture(*, complete: bool = True):
    project = build_project(project_id="pippi", title="P/PPI", workspace=str(ROOT),
        github_url=None, application_command=["pippi", "dashboard"],
        verification_command=["pippi", "interface-doctor"], revision="r034")
    host = negotiate_host_mode(host_id="codex-local", requested_mode="EXECUTABLE_LOCAL",
        capability_ids=["ARTIFACT_EXCHANGE", "FILESYSTEM_READ", "PROCESS_EXECUTION"],
        adapter_root=None)
    context = build_execution_context(host_family="WINDOWS", shell_family="POWERSHELL",
        path_flavour="WINDOWS", filesystem_class="WINDOWS_NATIVE", case_sensitive=False,
        python_implementation="CPython", python_version="3.12.3",
        source="DECLARED_EXTERNAL_HOST", wsl_distribution=None)
    opening = prepare_turn(project=project, host_profile=host, sequence=1,
        previous_turn_root=None, scenario="CODING", requested_rule_ids=[],
        acceptance_case_roots=[R1], journal_head=R2, execution_context=context)
    report = build_turn_report(opening=opening, summary="Bound the common turn through CMBA.",
        changed_paths=["src/ucm/pippi_cmba.py"], artifact_roots=[R3], evidence_roots=[R4],
        unresolved_items=[], next_action="Preserve the exact assessment with the project report.",
        claim_class="IMPLEMENTATION")
    evidence = [{"evidence_id": "check-output", "subject_root": R4,
        "source_root": R3, "producer_id": "declared-local-checker", "receipt_root": None,
        "declared_basis": "HOST_CAPTURED", "description": "Caller references its local check output."}]
    claims = [{"claim_id": "change", "activity_kind": "CHANGE",
        "statement": "Added a source-bound assessment adapter.",
        "declared_basis": "AGENT_REPORTED", "evidence_ids": []},
        {"claim_id": "check", "activity_kind": "CHECK",
         "statement": "Caller reports a positive structural check.",
         "declared_basis": "VERIFIER_DERIVED", "evidence_ids": ["check-output"]}]
    coverage = [{"channel": channel, "status": "PARTIAL", "evidence_ids": [],
        "limitations": ["Declared turn-level coverage; no tool interposition attested."]}
        for channel in ("JOURNAL_WRITE", "VISIBLE_OUTPUT")] if complete else []
    record = build_turn_record(opening=opening, report=report, claims=claims, evidence=evidence,
        coverage=coverage,
        objectives=[{"objective_id": "bind-common-turn", "statement": "Preserve declared provenance.",
                     "acceptance_case_roots": [R1]}] if complete else [],
        acceptance_dispositions=[{"acceptance_case_root": R1, "disposition": "REPORTED_MET",
            "claim_ids": ["change", "check"], "evidence_ids": ["check-output"]}]
            if complete else [], native_turn_roots=[])
    return opening, report, record


class PippiCmbaPositiveTests(unittest.TestCase):
    def assessment(self, *, complete=True):
        opening, report, record = common_turn_fixture(complete=complete)
        assessment = build_cmba_turn_assessment(opening=opening, report=report,
            turn_record=record, expected_wheel_sha256=CMBA_WHEEL_SHA256)
        return opening, report, record, assessment

    def test_exact_optional_wheel_discovery_does_not_import_cmba(self):
        before = {name for name in sys.modules if name.startswith("cmba_")}
        descriptor = discover_cmba_binding()
        after = {name for name in sys.modules if name.startswith("cmba_")}
        self.assertEqual(before, after)
        self.assertEqual(descriptor["status"], "AVAILABLE")
        self.assertEqual(descriptor["artifact_observation"], "EXACT_WHEEL_VERIFIED")
        self.assertEqual(descriptor["expected_wheel_sha256"], CMBA_WHEEL_SHA256)
        self.assertFalse(descriptor["core_turn_records_require_cmba"])

    def test_actual_cmba_evaluator_binds_exact_common_record(self):
        opening, report, record, assessment = self.assessment()
        self.assertEqual(assessment["outcome"], "STRUCTURAL_BINDING_VALID")
        self.assertEqual(assessment["cmba_values"]["ucm.common-turn"], record)
        self.assertEqual(assessment["cmba_values"]["ucm.opening"], opening)
        self.assertEqual(assessment["cmba_values"]["ucm.report"], report)
        self.assertEqual(assessment["cmba_receipt"]["body"]["result"]["checks"],
                         {"binding.structure": "MATCH"})
        self.assertEqual(assessment["cmba_replay"]["status"], "MATCH_EXACT_EVALUATION_REPLAY")
        self.assertNotEqual(assessment["cmba_binding"]["binding_root"], record["turn_record_root"])
        self.assertEqual(assessment["native_roots"]["turn_record_root"], record["turn_record_root"])

    def test_assessment_rebuild_and_import_are_exact_and_non_granting(self):
        opening, report, record, assessment = self.assessment()
        validated = validate_cmba_turn_assessment(assessment, opening=opening, report=report,
            turn_record=record, expected_wheel_sha256=CMBA_WHEEL_SHA256)
        self.assertEqual(validated, assessment)
        self.assertEqual(assessment["assurance"], "DECLARED_NOT_VERIFIED")
        self.assertTrue(all(row["assurance"] == "DECLARED_NOT_VERIFIED"
                            for row in assessment["cmba_values"]["ucm.common-turn"]["claims"]))
        self.assertEqual(assessment["reported_activity"], "NOT_INDEPENDENTLY_OBSERVED")
        self.assertEqual(assessment["current_use_admissibility"], "NOT_EVALUATED")
        self.assertEqual(assessment["authority_effect"], "NONE")
        self.assertFalse(assessment["effect_authorized"])

    def test_selected_module_origins_stay_in_exact_wheel_without_installation(self):
        before = list(sys.path)
        _, _, _, assessment = self.assessment()
        self.assertEqual(sys.path, before)
        identity = assessment["cmba_identity"]
        self.assertEqual(identity["wheel_sha256"], CMBA_WHEEL_SHA256)
        self.assertEqual(identity["artifact"], CMBA_WHEEL_RELATIVE_PATH)
        self.assertGreater(identity["wheel_member_count"], 50)
        for row in identity["loaded_origins"]:
            self.assertTrue(row["member"].startswith("cmba_core/"))
            self.assertEqual(len(row["sha256"]), 64)
            self.assertIn(".whl", sys.modules[row["module"]].__file__)
        native = discover_cmba_binding()["native_adapter_inventory"][0]
        self.assertEqual(native["scope"], "PINNED_UCM_R033_NO_NATIVE_TOOLS")
        self.assertEqual(native["r034_compatibility"], "NOT_CLAIMED")

    def test_incomplete_reporting_stays_visible_in_structural_assessment(self):
        _, _, record, assessment = self.assessment(complete=False)
        self.assertEqual(record["status"], "NEEDS_INFORMATION")
        self.assertEqual(assessment["outcome"], "STRUCTURAL_BINDING_VALID")
        self.assertEqual(assessment["cmba_values"]["ucm.common-turn"]["missing_information"],
                         record["missing_information"])
        self.assertFalse(assessment["cmba_values"]["ucm.common-turn"]["acceptance_case_closed"])


if __name__ == "__main__":
    unittest.main()

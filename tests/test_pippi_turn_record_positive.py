"""Positive construction checks for common P/PPI reporting; no attack cases."""
from copy import deepcopy
from pathlib import Path
import unittest

from uclop.canonical import canonical_bytes
from ucm.pippi_adaptive import build_turn_report, negotiate_host_mode, prepare_turn
from ucm.pippi_global import build_project
from ucm.pippi_portability import build_execution_context
from ucm.pippi_turn_record import (CHANNELS, PROVENANCE_BASES, build_turn_record,
    project_turn_record, reporting_requirements, validate_turn_record)


ROOT = Path(__file__).resolve().parents[1]
R1, R2, R3, R4, R5, R6 = (str(index) * 64 for index in range(1, 7))


def common_turn_fixture(scenario="CODING"):
    """Return exact legacy inputs and new writer inputs for positive examples."""
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
        previous_turn_root=None, scenario=scenario, requested_rule_ids=[],
        acceptance_case_roots=[R1, R2], journal_head=R3, execution_context=context)
    report = build_turn_report(opening=opening, summary="Built the common turn record.",
        changed_paths=["src/ucm/pippi_turn_record.py"], artifact_roots=[R4],
        evidence_roots=[R5], unresolved_items=[], next_action="Attach verified external evidence.",
        claim_class="IMPLEMENTATION")
    details = {
        "claims": [
            {"claim_id": "change", "activity_kind": "CHANGE", "statement": "Added a turn record.",
             "declared_basis": "AGENT_REPORTED", "evidence_ids": ["suite"]},
            {"claim_id": "check", "activity_kind": "CHECK", "statement": "Recorded a reported check.",
             "declared_basis": "VERIFIER_DERIVED", "evidence_ids": ["suite"]}],
        "evidence": [{"evidence_id": "suite", "subject_root": R5, "source_root": R4,
            "producer_id": "positive-example", "receipt_root": R6,
            "declared_basis": "EXTERNALLY_ATTESTED", "description": "Referenced check receipt."}],
        "coverage": [{"channel": "JOURNAL_WRITE", "status": "PARTIAL", "evidence_ids": [],
            "limitations": ["Closing report only."]},
            {"channel": "VISIBLE_OUTPUT", "status": "PARTIAL", "evidence_ids": [],
             "limitations": ["Agent-reported visible summary."]}],
        "objectives": [{"objective_id": "turn-record", "statement": "Preserve structured turn facts.",
            "acceptance_case_roots": [R1, R2]}],
        "acceptance_dispositions": [
            {"acceptance_case_root": R1, "disposition": "REPORTED_MET",
             "claim_ids": ["change", "check"], "evidence_ids": ["suite"]},
            {"acceptance_case_root": R2, "disposition": "OPEN", "claim_ids": [], "evidence_ids": []}],
        "native_turn_roots": [R6],
    }
    return opening, report, details


class PippiTurnRecordPositiveTests(unittest.TestCase):
    def test_exact_roundtrip_preserves_legacy_inputs(self):
        opening, report, details = common_turn_fixture()
        before = canonical_bytes({"opening": opening, "report": report, "details": details})
        result = build_turn_record(opening=opening, report=report, **details)
        self.assertEqual(validate_turn_record(result, opening=opening, report=report), result)
        self.assertEqual(before, canonical_bytes({"opening": opening, "report": report, "details": details}))
        self.assertEqual(result["turn_opening_root"], opening["turn_opening_root"])
        self.assertEqual(result["turn_report_root"], report["turn_report_root"])
        self.assertEqual(result["status"], "INFORMATION_COMPLETE")
        self.assertTrue(result["reporting_completeness_is_not_verification"])

    def test_all_basis_labels_remain_declared(self):
        opening, report, details = common_turn_fixture()
        details["claims"] = [{"claim_id": str(index), "activity_kind": "CHECK",
            "statement": basis, "declared_basis": basis, "evidence_ids": ["suite"]}
            for index, basis in enumerate(PROVENANCE_BASES)]
        details["acceptance_dispositions"] = []
        result = build_turn_record(opening=opening, report=report, **details)
        self.assertEqual({row["declared_basis"] for row in result["claims"]}, set(PROVENANCE_BASES))
        self.assertEqual({row["assurance"] for row in result["claims"] + result["evidence"]},
                         {"DECLARED_NOT_VERIFIED"})
        self.assertEqual(result["verified_channel_ids"], [])
        self.assertFalse(result["enforced_host_verified"])

    def test_missing_information_and_full_denominator_are_preserved(self):
        opening, report, _ = common_turn_fixture()
        result = build_turn_record(opening=opening, report=report, claims=[], evidence=[],
            coverage=[], objectives=[], acceptance_dispositions=[], native_turn_roots=[])
        self.assertEqual({row["channel"] for row in result["coverage"]}, set(CHANNELS))
        self.assertEqual({row["status"] for row in result["coverage"]}, {"UNKNOWN"})
        self.assertEqual([row["acceptance_case_root"] for row in result["acceptance_dispositions"]],
                         opening["acceptance_case_roots"])
        self.assertEqual({row["disposition"] for row in result["acceptance_dispositions"]}, {"UNKNOWN"})
        self.assertEqual(result["status"], "NEEDS_INFORMATION")
        self.assertFalse(result["acceptance_case_closed"])
        self.assertFalse(result["effect_authorized"])

    def test_requirements_follow_scenario_at_turn_granularity(self):
        coding = reporting_requirements("CODING")
        packaging = reporting_requirements("PACKAGING")
        remote = reporting_requirements("REMOTE_WORK")
        self.assertEqual(coding["required_activity_kinds"], ["CHANGE", "CHECK"])
        self.assertTrue(packaging["evidence_references_required"])
        self.assertEqual(remote["required_activity_kinds"], ["EXTERNAL_RECEIPT"])
        self.assertFalse(remote["per_tool_interception_required"])

    def test_native_turn_and_source_roots_are_reference_links(self):
        opening, report, details = common_turn_fixture()
        result = build_turn_record(opening=opening, report=report, **details)
        self.assertEqual(result["native_turn_roots"], [R6])
        self.assertTrue(result["native_turn_roots_are_references"])
        self.assertEqual(result["source_roots"], [R4])
        self.assertTrue(result["source_roots_are_references"])
        self.assertEqual(result["context"], opening["context"])
        self.assertEqual(result["journal_head"], opening["journal_head"])

    def test_views_are_deterministic_projections(self):
        opening, report, details = common_turn_fixture()
        result = build_turn_record(opening=opening, report=report, **details)
        human = project_turn_record(result, opening=opening, report=report)
        again = project_turn_record(result, opening=opening, report=report)
        machine = project_turn_record(result, opening=opening, report=report, view="MACHINE")
        self.assertEqual(canonical_bytes(human), canonical_bytes(again))
        self.assertEqual(human["turn_record_root"], result["turn_record_root"])
        self.assertFalse(human["projection_is_evidence"])
        self.assertEqual(machine["facts"], human["facts"])
        self.assertEqual(machine["lines"], [])

    def test_input_order_has_one_canonical_record(self):
        opening, report, details = common_turn_fixture()
        reordered = deepcopy(details)
        for field in ("claims", "coverage", "acceptance_dispositions"):
            reordered[field].reverse()
        self.assertEqual(build_turn_record(opening=opening, report=report, **details),
                         build_turn_record(opening=opening, report=report, **reordered))


if __name__ == "__main__":
    unittest.main()

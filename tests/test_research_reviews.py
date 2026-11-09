from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from uclop.canonical import root
from ucm.research_reviews import (
    build_finding_adjudication,
    build_review_finding,
    build_review_lens_pack,
    build_saturation_assessment,
    build_successor_ledger,
    validate_finding_adjudication,
    validate_review_finding,
    validate_review_lens_pack,
    validate_saturation_assessment,
    validate_successor_ledger,
)


def lens_pack():
    return build_review_lens_pack(
        lens_pack_id="research-lenses-v0.1",
        subject_class="RESEARCH_PAPER",
        lenses=[{
            "lens_id": "L01",
            "title": "Claim and authority boundary",
            "objective": "Find claims that outrun their declared evidence or standing.",
            "review_class": "SEMANTIC",
            "required_context_roles": ["CORPUS_CONTEXT"],
            "deterministic_check_ids": ["SUBJECT_SHA256_MATCH"],
            "review_questions": ["What does the evidence actually support?"],
            "exclusions": ["No publication authorization."],
        }],
        limitations=["Internal calibration only."],
    )


class ResearchReviewRecordTests(unittest.TestCase):
    def test_records_round_trip_and_no_successor_is_explicit(self):
        lenses = lens_pack()
        self.assertEqual(validate_review_lens_pack(lenses), lenses)
        finding = build_review_finding(
            finding_id="F001", review_id="review-001", lens_pack_root=lenses["lens_pack_root"],
            lens_id="L01", subject_root="a" * 64,
            source_anchor={"path": "subject/paper.md", "section": "Scope", "location_start": 1,
                           "location_end": 1, "excerpt_sha256": "b" * 64},
            severity="INFO", change_class="PROCESS", summary="Independent review remains outstanding.",
            rationale="A deterministic runner can verify structure but cannot supply scholarly judgment.",
            evidence_roots=["c" * 64], counterevidence_roots=[], affected_concept_ids=[],
            affected_artifact_ids=["AC-0081"], proposed_action="Run a declared independent review pass.",
            reviewer_identity_root="d" * 64, limitations=["Calibration finding only."],
        )
        self.assertEqual(validate_review_finding(finding), finding)
        adjudication = build_finding_adjudication(
            finding_root=finding["finding_root"], disposition="DEFERRED",
            reason_codes=["INDEPENDENT_REVIEW_NOT_IN_SCOPE"], author_decision_root=None,
            applied_change_root=None, superseded_by_finding_root=None,
            remaining_obligation_ids=["RUN_INDEPENDENT_REVIEW"],
            regression_review_required=False, notes="No paper mutation in calibration.",
        )
        self.assertEqual(validate_finding_adjudication(adjudication), adjudication)
        ledger = build_successor_ledger(
            ledger_id="AC-0081-calibration", logical_work_id="AC-0081", source_root="a" * 64,
            successor_status="NOT_CREATED", successor_root=None, lens_pack_root=lenses["lens_pack_root"],
            accepted_finding_roots=[], adjudication_roots=[adjudication["adjudication_root"]],
            accepted_change_roots=[], semantic_change_roots=[], editorial_change_roots=[],
            added_claim_roots=[], removed_claim_roots=[], cross_reference_delta_roots=[],
            regression_evidence_roots=[], unresolved_finding_roots=[finding["finding_root"]],
            predecessor_ledger_root=None, producer_operation_root="e" * 64, status="REVIEW_ONLY",
        )
        self.assertEqual(validate_successor_ledger(ledger), ledger)

    def test_saturation_requires_multiple_passes(self):
        assessment = build_saturation_assessment(
            assessment_id="A001", subject_root="a" * 64, lens_pack_root="b" * 64,
            pass_roots=["c" * 64], new_substantive_findings_by_pass=[1],
            accepted_substantive_changes_by_pass=[0], severity_weighted_yield_by_pass=[0],
            repeated_finding_count_by_pass=[0], regression_count_by_pass=[0],
            coverage_delta_basis_points={"corpus_linkage": 0, "counterevidence": 0,
                                         "evidence": 0, "pedagogical_accessibility": 0},
            unresolved_high_severity_roots=[], thresholds={"minimum_passes": 3, "window_size": 2,
                "maximum_new_findings": 0, "maximum_accepted_changes": 0,
                "maximum_weighted_yield": 0, "maximum_regressions": 0},
            nonclaims=["This result does not establish publication readiness."],
        )
        self.assertEqual(assessment["result"], "INSUFFICIENT_PASSES")
        self.assertEqual(validate_saturation_assessment(assessment), assessment)

    def test_structural_runner_is_deterministic_and_noninterpretive(self):
        with tempfile.TemporaryDirectory() as td:
            root_path = Path(td)
            (root_path / "subject").mkdir(); (root_path / "policy").mkdir(); (root_path / "context").mkdir()
            paper = b"# Example\n\n## References\n\nhttps://example.invalid\n"
            (root_path / "subject" / "paper.md").write_bytes(paper)
            lenses = lens_pack()
            (root_path / "policy" / "LENS-PACK.json").write_text(json.dumps(lenses), encoding="utf-8")
            context = {"review_id": "review-001", "expected_subject_sha256": __import__("hashlib").sha256(paper).hexdigest()}
            (root_path / "context" / "CALIBRATION-CONTEXT.json").write_text(json.dumps(context), encoding="utf-8")
            runner = Path(__file__).parents[1] / "tools" / "run_research_review.py"
            outputs = []
            for name in ("out-a", "out-b"):
                subprocess.run([sys.executable, str(runner), "--output-dir", name], cwd=root_path,
                               check=True, capture_output=True)
                outputs.append((root_path / name / "DETERMINISTIC-CHECKS.json").read_bytes())
            self.assertEqual(outputs[0], outputs[1])
            review_pass = json.loads((root_path / "out-a" / "REVIEW-PASS.json").read_text())
            self.assertEqual(review_pass["domain_verdict"], "NOT_PERFORMED_BY_DETERMINISTIC_RUNNER")
            self.assertFalse(review_pass["paper_mutated"])


if __name__ == "__main__":
    unittest.main()

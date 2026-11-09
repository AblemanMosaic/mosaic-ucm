from __future__ import annotations

from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root
from ucm.amcas import BOUNDARY
from ucm.artifacts import deterministic_zip, verify_deterministic_zip
from ucm.maturity_operator_evidence import (
    ADDENDUM_ROLE, ADDENDUM_SCHEMA, EVIDENCE_ROLE, EVIDENCE_SCHEMA,
    KIT_REPAIR_SCHEMA, KIT_ROLE, KIT_SCHEMA, build_maturity_operator_evidence_addendum,
    verify_maturity_operator_evidence,
)
from tools.maturity_release_common import collect_payloads


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class MaturityOperatorEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.source = b"exact qualification source"
        self.runner = b"# exact builder-authored court\n"
        qualification = {
            "status": "PASS", "failures": 0, "errors": 0, "skips": 0,
            "operator_adversarial_status": "SEPARATE_USER_RUN_REQUIRED",
            "qualification_root": "1" * 64,
            "qualification_source_anchor": {"archive_sha256": sha(self.source)},
        }
        self.kit = deterministic_zip({
            "QUALIFICATION-SOURCE.zip": self.source,
            "QUALIFICATION.json": canonical_bytes(qualification),
            "RUN-MATURITY-TIER1.py": self.runner,
        }, schema=KIT_SCHEMA, artifact_role=KIT_ROLE)
        body = {
            "schema": "mosaic.ucm.maturity-tier1-result.v0.1",
            "subject_sha256": sha(self.source),
            "case_count": 1,
            "cases": [{"id": "CONTROL", "status": "PASS",
                       "diagnostic": "EXPECTED_RESULT"}],
            "failed": 0, "status": "PASS", **BOUNDARY,
        }
        result = {**body, "court_root": root(body)}
        self.evidence = deterministic_zip({
            "TIER1-RESULT.json": canonical_bytes(result),
            "REPORT.md": b"operator evidence\n",
            "RUN-MATURITY-TIER1.py": self.runner,
        }, schema=EVIDENCE_SCHEMA, artifact_role=EVIDENCE_ROLE)
        freeze_body = {"schema": "freeze", "qualification_root": "1" * 64,
                       **BOUNDARY}
        self.freeze = canonical_bytes({**freeze_body, "freeze_root": root(freeze_body)})
        self.handoff = b"exact review handoff"

    def test_exact_operator_evidence_binds_deterministically(self):
        acceptance = verify_maturity_operator_evidence(
            kit_raw=self.kit, evidence_raw=self.evidence,
            expected_kit_sha256=sha(self.kit))
        self.assertEqual(acceptance["operator_case_count"], 1)
        self.assertEqual(acceptance["operator_status"], "PASS")
        self.assertEqual(acceptance["independent_review_status"], "PENDING")
        first, accepted = build_maturity_operator_evidence_addendum(
            kit_raw=self.kit, evidence_raw=self.evidence,
            review_handoff_raw=self.handoff, freeze_receipt_raw=self.freeze,
            expected_kit_sha256=sha(self.kit),
            expected_review_handoff_sha256=sha(self.handoff))
        second, _ = build_maturity_operator_evidence_addendum(
            kit_raw=self.kit, evidence_raw=self.evidence,
            review_handoff_raw=self.handoff, freeze_receipt_raw=self.freeze,
            expected_kit_sha256=sha(self.kit),
            expected_review_handoff_sha256=sha(self.handoff))
        self.assertEqual(first, second)
        self.assertEqual(accepted, acceptance)
        verify_deterministic_zip(first, expected_schema=ADDENDUM_SCHEMA,
                                 expected_role=ADDENDUM_ROLE)

    def test_predecessor_evidence_is_refused_by_subject_pin(self):
        with zipfile.ZipFile(io.BytesIO(self.evidence)) as archive:
            result = json.loads(archive.read("TIER1-RESULT.json"))
        body = {key: deepcopy(value) for key, value in result.items()
                if key != "court_root"}
        body["subject_sha256"] = "2" * 64
        changed = {**body, "court_root": root(body)}
        stale = deterministic_zip({
            "TIER1-RESULT.json": canonical_bytes(changed),
            "REPORT.md": b"operator evidence\n",
            "RUN-MATURITY-TIER1.py": self.runner,
        }, schema=EVIDENCE_SCHEMA, artifact_role=EVIDENCE_ROLE)
        with self.assertRaisesRegex(ValueError, "MATURITY_OPERATOR_SUBJECT_MISMATCH"):
            verify_maturity_operator_evidence(
                kit_raw=self.kit, evidence_raw=stale,
                expected_kit_sha256=sha(self.kit))

    def test_importer_ships_in_canonical_runtime(self):
        payloads = collect_payloads(review=False)
        self.assertIn("tools/build_maturity_operator_evidence_addendum.py", payloads)
        self.assertIn("src/ucm/maturity_operator_evidence.py", payloads)

    def test_operator_architecture_cases_track_the_v02_contract(self):
        runner = (ROOT / "review/operator/RUN-MATURITY-TIER1.py").read_text(
            encoding="utf-8")
        self.assertIn('"test_evidence_receipts"', runner)
        self.assertIn('"proof_evidence_receipts"', runner)
        self.assertIn("reroot_architecture_candidate", runner)
        self.assertNotIn('"test_evidence_roots"', runner)
        self.assertNotIn('"verified_proof_roots"', runner)

    def test_operator_repair_carries_the_exact_predecessor_hold(self):
        evidence = (ROOT / "review/operator/predecessor-c2/TIER1-HOLD-EVIDENCE.zip").read_bytes()
        disposition = json.loads((
            ROOT / "review/operator/predecessor-c2/DISPOSITION.json").read_text(
                encoding="utf-8"))
        self.assertEqual(sha(evidence), disposition["evidence_sha256"])
        self.assertEqual(disposition["status"],
                         "BUILDER_REPAIRED_PENDING_OPERATOR_RERUN")
        self.assertEqual(len(disposition["affected_cases"]), 4)

    def test_repair_kit_schema_binds_predecessor_hold(self):
        predecessor = (ROOT / "review/operator/predecessor-c2/TIER1-HOLD-EVIDENCE.zip").read_bytes()
        disposition = json.loads((
            ROOT / "review/operator/predecessor-c2/DISPOSITION.json").read_text(
                encoding="utf-8"))
        with zipfile.ZipFile(io.BytesIO(self.kit)) as archive:
            payloads = {name: archive.read(name) for name in archive.namelist()
                        if name != "MANIFEST.json"}
        repaired = deterministic_zip({
            **payloads,
            "PREDECESSOR-TIER1-EVIDENCE.zip": predecessor,
            "PREDECESSOR-TIER1-DISPOSITION.json": canonical_bytes(disposition),
        }, schema=KIT_REPAIR_SCHEMA, artifact_role=KIT_ROLE)
        acceptance = verify_maturity_operator_evidence(
            kit_raw=repaired, evidence_raw=self.evidence,
            expected_kit_sha256=sha(repaired))
        self.assertEqual(acceptance["operator_status"], "PASS")

    def test_accepted_operator_addendum_is_pinned(self):
        addendum = (ROOT / "review/operator/accepted-c2/OPERATOR-EVIDENCE-ADDENDUM.zip").read_bytes()
        disposition = json.loads((
            ROOT / "review/operator/accepted-c2/DISPOSITION.json").read_text(
                encoding="utf-8"))
        self.assertEqual(sha(addendum), disposition["addendum_sha256"])
        self.assertEqual(disposition["operator_case_count"], 39)
        self.assertEqual(disposition["status"],
                         "PASS_OPERATOR_TIER1_EVIDENCE_BOUND")
        self.assertEqual(disposition["independent_review_status"], "PENDING")


if __name__ == "__main__":
    unittest.main()

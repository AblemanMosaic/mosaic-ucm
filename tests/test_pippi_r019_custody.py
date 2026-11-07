from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


class PippiR019CustodyTests(unittest.TestCase):
    def test_review_and_operator_return_are_exact_and_provenanced(self):
        review = ROOT / "review/pippi-r019-review-return"
        evidence = ROOT / "review/pippi-r019-operator-return/PIPPI-r019-TIER1-EVIDENCE.zip"
        disposition = json.loads((review / "DISPOSITION.json").read_text(encoding="utf-8"))
        body = {key: value for key, value in disposition.items() if key != "disposition_root"}
        self.assertEqual(disposition["disposition_root"],
                         hashlib.sha256(canonical(body)).hexdigest())
        for field, name in (
            ("review_report_sha256", "REPORT.md"),
            ("review_findings_sha256", "FINDINGS.json"),
            ("review_recompute_sha256", "RECOMPUTE.json"),
            ("reviewer_evidence_sha256", "REVIEWER-EVIDENCE.zip"),
        ):
            self.assertEqual(disposition[field], hashlib.sha256((review / name).read_bytes()).hexdigest())
        self.assertEqual(disposition["operator_evidence_sha256"],
                         hashlib.sha256(evidence.read_bytes()).hexdigest())
        self.assertEqual(disposition["operator_evidence_provenance"],
                         "USER_RUN_BUILDER_AUTHORED_COURT")
        self.assertFalse(disposition["independent_tier1"])
        with zipfile.ZipFile(evidence) as archive:
            result = json.loads(archive.read("TIER1-RESULT.json"))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["case_count"], 31)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["court_root"], disposition["operator_tier1_court_root"])


if __name__ == "__main__":
    unittest.main()

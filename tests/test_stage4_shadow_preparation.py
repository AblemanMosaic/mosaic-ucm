"""Compatibility-facing positive checks for the Stage I4 v0.2 contracts.

Negative and mutation coverage is intentionally in the operator-run Tier 1 kit.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tests import test_stage4_c2_positive as positive
from ucm.stage4 import verify_review_archive


class StageI4PreparationCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = positive.StageI4C2PositiveTests(); self.fixture.setUp()

    def test_exact_review_archive_is_the_eligibility_subject(self):
        checked = verify_review_archive(self.fixture.review)
        self.assertEqual(checked["disposition"]["verdict"],
                         "QUALIFIED_RECOMMENDATION_ONLY")

    def test_run_contract_preserves_effect_class_and_expected_result(self):
        _, contract = self.fixture._contracts()
        case = contract["case_schedule"][0]
        self.assertEqual(case["effect_class"], "READ_ONLY")
        self.assertEqual(case["expected_native_result_root"], "d" * 64)
        self.assertEqual(case["expected_ucm_result_root"], "d" * 64)

    def test_run_contract_is_non_granting(self):
        _, contract = self.fixture._contracts()
        self.assertFalse(contract["application_contact_authorized"])
        self.assertFalse(contract["execution_authorized"])
        self.assertFalse(contract["composition_authorized"])


if __name__ == "__main__":
    unittest.main()

from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uclop.canonical import Refusal, root
from ucm.correspondence import run_correspondence_court, verify_correspondence_court


class CorrespondenceTests(unittest.TestCase):
    def cases(self):
        result = root({"decision": "PASS"})
        return {"schema": "mosaic.ucm.native-correspondence-cases.v0.1",
                "application_id": "APP.ONE", "subject_root": "1" * 64,
                "native_validator_id": "NATIVE", "ucm_validator_id": "UCM.SHADOW",
                "cases": [{"case_id": "C001", "input_root": "2" * 64,
                           "native": {"decision": "PASS", "result_root": result},
                           "ucm": {"decision": "PASS", "result_root": result}}]}

    def test_equivalent_and_divergent_cases_are_explicit(self):
        passed = run_correspondence_court(self.cases())
        self.assertEqual(verify_correspondence_court(passed)["status"], "PASS_EQUIVALENT")
        changed = self.cases()
        changed["cases"][0]["ucm"]["decision"] = "REFUSED"
        self.assertEqual(run_correspondence_court(changed)["status"], "HOLD_DIVERGENCE")

    def test_row_tampering_refuses(self):
        value = run_correspondence_court(self.cases())
        value["rows"][0]["diagnostic"] = "EQUIVALENT"
        value["rows"][0]["equivalent"] = False
        with self.assertRaises(Refusal):
            verify_correspondence_court(value)


if __name__ == "__main__":
    unittest.main()

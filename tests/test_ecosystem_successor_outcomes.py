from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes
from ucm.ecosystem_successor_outcomes import build_successor_outcome_register


class EcosystemSuccessorOutcomeTests(unittest.TestCase):
    def setUp(self):
        returns_dir = ROOT / "integration" / "successor-returns"
        self.packages = {path.name: path.read_bytes()
                         for path in sorted(returns_dir.glob("*.zip"))}

    def test_current_successor_returns_reconcile_without_authority(self):
        result = build_successor_outcome_register(self.packages)
        self.assertEqual(result["fixed_denominator"], 7)
        self.assertEqual(result["received_count"], len(self.packages))
        self.assertEqual(result["pending_count"], 7 - len(self.packages))
        self.assertFalse(result["application_execution_authorized"])
        self.assertFalse(result["all_holds_cleared"])
        self.assertEqual(result["authority_effect"], "NONE")
        reconciled = [row for row in result["applications"]
                      if row["return_status"] == "STATIC_RECONCILED_UNVERIFIED"]
        self.assertEqual(len(reconciled), len(self.packages))
        self.assertTrue(all(not row["execution_eligible"] for row in reconciled))
        self.assertTrue(all(row["hold_clearance"] == "NONE" for row in reconciled))
        self.assertTrue(all(row["holds"] for row in reconciled))

    def test_frozen_successor_outcome_register_matches_current_packages(self):
        result = build_successor_outcome_register(self.packages)
        frozen = (ROOT / "integration" /
                  "ECOSYSTEM-SUCCESSOR-OUTCOME-REGISTER.json").read_bytes()
        self.assertEqual(canonical_bytes(result), frozen)


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, strict_loads
from ucm.ecosystem_outcomes import build_outcome_register


class EcosystemOutcomeTests(unittest.TestCase):
    def test_all_seven_returns_reconcile_without_execution_eligibility(self):
        directory = ROOT / "integration" / "session-returns"
        packages = {path.name: path.read_bytes() for path in directory.glob("*.zip")}
        result = build_outcome_register(packages)
        frozen = strict_loads((ROOT / "integration" /
            "ECOSYSTEM-INTEGRATION-OUTCOME-REGISTER.json").read_bytes())
        self.assertEqual(canonical_bytes(result), canonical_bytes(frozen))
        self.assertEqual(len(result["applications"]), 7)
        self.assertTrue(result["all_returns_received"])
        self.assertFalse(result["all_content_independently_reviewed"])
        self.assertTrue(all(not row["execution_eligible"]
                            and row["hold_clearance"] == "NONE"
                            for row in result["applications"]))
        dispositions = {row["application_id"]: row["coordinator_disposition"]
                        for row in result["applications"]}
        self.assertEqual(dispositions["MOSAIC.2D_3D"], "REBIND_REQUIRED")
        self.assertEqual(dispositions["MOSAIC.MESSENGER_CRYSTAL"],
                         "RETURN_REPAIR_REQUIRED")
        self.assertEqual(dispositions["MOSAIC.MEMORY_VAULT"],
                         "STATIC_READINESS_ONLY")


if __name__ == "__main__":
    unittest.main()

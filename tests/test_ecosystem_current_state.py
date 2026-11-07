from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, strict_loads
from ucm.ecosystem_current_state import build_ecosystem_current_state


class EcosystemCurrentStateTests(unittest.TestCase):
    def test_append_only_current_state_reproduces(self):
        integration = ROOT / "integration"
        successors = strict_loads(
            (integration / "ECOSYSTEM-SUCCESSOR-OUTCOME-REGISTER.json").read_bytes())
        audits = strict_loads(
            (integration / "ECOSYSTEM-AUDIT-RETURN-REGISTER.json").read_bytes())
        repairs = strict_loads(
            (integration / "ECOSYSTEM-REPAIR-RETURN-REGISTER.json").read_bytes())
        result = build_ecosystem_current_state(successors, audits, repairs)
        frozen = (integration / "ECOSYSTEM-INTEGRATION-CURRENT-STATE.json").read_bytes()
        self.assertEqual(canonical_bytes(result), frozen)
        self.assertEqual(result["application_count"], 7)
        self.assertEqual(result["audit_overlay_count"], 1)
        self.assertEqual(result["repair_overlay_count"], 1)
        self.assertFalse(result["application_execution_authorized"])
        self.assertFalse(result["all_holds_cleared"])
        spatial = next(row for row in result["applications"]
                       if row["application_id"] == "MOSAIC.2D_3D")
        self.assertTrue(spatial["audit_overlay_present"])
        self.assertTrue(spatial["repair_overlay_present"])
        self.assertEqual(spatial["status"], "HOLD_FOR_REPAIR")
        self.assertEqual(spatial["open_findings"], 0)
        self.assertEqual(spatial["open_high_priority_holds"], 0)
        self.assertEqual(spatial["repaired_findings"], 17)
        self.assertEqual(spatial["remaining_external_holds"], 7)
        self.assertFalse(spatial["execution_eligible"])


if __name__ == "__main__":
    unittest.main()

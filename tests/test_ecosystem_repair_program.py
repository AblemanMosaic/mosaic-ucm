from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, strict_loads
from ucm.ecosystem_repair_program import build_ecosystem_repair_program


class EcosystemRepairProgramTests(unittest.TestCase):
    def test_frozen_program_batches_all_audit_holds(self):
        integration = ROOT / "integration"
        values = [strict_loads((integration / name).read_bytes()) for name in (
            "ECOSYSTEM-SUCCESSOR-OUTCOME-REGISTER.json",
            "ECOSYSTEM-AUDIT-RETURN-REGISTER.json",
            "ECOSYSTEM-REPAIR-RETURN-REGISTER.json",
            "ECOSYSTEM-INTEGRATION-CURRENT-STATE.json",
        )]
        result = build_ecosystem_repair_program(*values)
        frozen = (integration / "ECOSYSTEM-AUDIT-REPAIR-PROGRAM.json").read_bytes()
        self.assertEqual(canonical_bytes(result), frozen)
        self.assertEqual(result["repair_batch_count"], 1)
        repair = result["repair_batches"][0]
        self.assertEqual(repair["application_id"], "MOSAIC.2D_3D")
        self.assertEqual(len(repair["high_priority_hold_ids"]), 8)
        self.assertEqual(len(repair["other_open_hold_ids"]), 9)
        self.assertEqual(repair["status"],
                         "BATCH_REPAIR_RETURNED_PENDING_INDEPENDENT_REVIEW")
        self.assertTrue(repair["repair_return_present"])
        self.assertEqual(repair["repairs_claimed"], 17)
        self.assertFalse(repair["application_execution_authorized"])
        self.assertFalse(repair["independent_review_claimed"])


if __name__ == "__main__":
    unittest.main()

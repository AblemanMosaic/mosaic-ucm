from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, strict_loads
from ucm.ecosystem_work import build_next_dispatch, build_next_work_program


class EcosystemWorkTests(unittest.TestCase):
    def test_next_work_is_fixed_denominator_and_non_authorizing(self):
        outcomes = strict_loads((ROOT / "integration" /
            "ECOSYSTEM-INTEGRATION-OUTCOME-REGISTER.json").read_bytes())
        result = build_next_work_program(outcomes)
        frozen = (ROOT / "integration" /
                  "ECOSYSTEM-NEXT-WORK-PROGRAM.json").read_bytes()
        self.assertEqual(canonical_bytes(result), frozen)
        self.assertEqual(len(result["applications"]), 7)
        self.assertTrue(all(not row["execution_authorized"]
                            and not row["hold_clearance_authorized"]
                            for row in result["applications"]))
        lanes = {row["application_id"]: row["work_lane"]
                 for row in result["applications"]}
        self.assertEqual(lanes["MOSAIC.MESSENGER_CRYSTAL"],
                         "RETURN_RECOVERY_LANE")
        self.assertEqual(lanes["MOSAIC.2D_3D"],
                         "SOURCE_ROUTE_REBIND_LANE")
        self.assertEqual(lanes["MOSAIC.MEDIA_CENTER"],
                         "READINESS_REVIEW_LANE")

    def test_next_dispatch_preserves_roster_and_is_non_authorizing(self):
        program = strict_loads((ROOT / "integration" /
            "ECOSYSTEM-NEXT-WORK-PROGRAM.json").read_bytes())
        prior = strict_loads((ROOT / "integration" /
            "ECOSYSTEM-SESSION-DISPATCH.json").read_bytes())
        result = build_next_dispatch(program, prior)
        frozen = (ROOT / "integration" /
                  "ECOSYSTEM-NEXT-WORK-DISPATCH.json").read_bytes()
        self.assertEqual(canonical_bytes(result), frozen)
        self.assertEqual(len(result["applications"]), 7)
        self.assertTrue(result["transport_acceptance_is_not_work_completion"])
        self.assertTrue(all(not row["application_execution_authorized"]
                            and not row["hold_clearance_authorized"]
                            for row in result["applications"]))


if __name__ == "__main__":
    unittest.main()

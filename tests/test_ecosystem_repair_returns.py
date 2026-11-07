from pathlib import Path
import hashlib
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, strict_loads
from ucm.ecosystem_repair_returns import build_repair_return_register


class EcosystemRepairReturnTests(unittest.TestCase):
    def test_exact_repair_return_register_reproduces(self):
        integration = ROOT / "integration"
        audits = strict_loads(
            (integration / "ECOSYSTEM-AUDIT-RETURN-REGISTER.json").read_bytes())
        folder = integration / "repair-returns"
        packages = {path.name: path.read_bytes() for path in sorted(folder.glob("*.zip"))}
        result = build_repair_return_register(audits, packages)
        self.assertEqual(canonical_bytes(result),
            (integration / "ECOSYSTEM-REPAIR-RETURN-REGISTER.json").read_bytes())
        self.assertEqual(result["repair_return_count"], 1)
        repair = result["repairs"][0]
        self.assertEqual(repair["application_id"], "MOSAIC.2D_3D")
        self.assertEqual(repair["repairs_claimed"], 17)
        self.assertEqual(len(repair["preserved_external_hold_ids"]), 7)
        self.assertEqual(repair["artifact_sha256"],
                         "193621e123b8a38770e721b85181286af47a53d0fc97d26cfa8cc9c1ef11b50c")
        self.assertEqual(repair["qualification_root"],
                         "33d53b78bf66f5fd49b77605ae498a4eb4ee84bee710c5cbac196f4e6b6b51f5")
        self.assertFalse(repair["independent_review_claimed"])
        self.assertFalse(repair["execution_eligible"])
        self.assertTrue(all(hashlib.sha256(raw).hexdigest() for raw in packages.values()))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ucm.ecosystem_audit_returns import (
    build_audit_return_register, verify_audit_return,
)

RETURNS = ROOT / "integration" / "audit-returns"
REGISTER = ROOT / "integration" / "ECOSYSTEM-AUDIT-RETURN-REGISTER.json"


class EcosystemAuditReturnTests(unittest.TestCase):
    def test_exact_audit_return_and_register_reproduce(self):
        packages = {path.name: path.read_bytes()
                    for path in sorted(RETURNS.glob("*.zip"))}
        self.assertEqual(len(packages), 1)
        row = verify_audit_return(next(iter(packages.values())))
        self.assertEqual(row["application_id"], "MOSAIC.2D_3D")
        self.assertEqual(row["status"], "HOLD_FOR_REPAIR")
        self.assertEqual(row["focused_tests_passed"], 89)
        self.assertEqual(row["open_findings"], 17)
        self.assertEqual(row["open_high_priority_holds"], 8)
        self.assertEqual(row["high_priority_hold_ids"],
                         [f"DRAWING_PIPELINE_R{i:02d}" for i in range(1, 9)])
        self.assertEqual(len(row["open_hold_ids"]), 17)
        self.assertFalse(row["execution_eligible"])
        built = build_audit_return_register(packages)
        frozen = json.loads(REGISTER.read_text(encoding="utf-8"))
        self.assertEqual(built, frozen)
        self.assertFalse(built["application_execution_authorized"])
        self.assertFalse(built["all_holds_cleared"])


if __name__ == "__main__":
    unittest.main()

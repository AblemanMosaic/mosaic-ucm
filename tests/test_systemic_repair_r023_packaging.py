from __future__ import annotations

import ast
import json
from pathlib import Path
import unittest


ROOT=Path(__file__).resolve().parents[1]


class SystemicRepairR023PackagingTests(unittest.TestCase):
    def test_operator_kit_is_builder_authored_and_unexecuted(self):
        declaration=json.loads((ROOT/"operator/systemic-repair-r023/KIT-DECLARATION.json").read_text())
        self.assertTrue(declaration["builder_authored"])
        self.assertFalse(declaration["operator_executed"])
        self.assertFalse(declaration["tier1_executed"])
        runner=(ROOT/"operator/systemic-repair-r023/RUN-TIER1.py").read_text()
        ast.parse(runner)
        self.assertNotIn("TemporaryDirectory(dir=kit)",runner)
        self.assertIn("FROZEN_PROGRAM_CUSTODY_MISMATCH",runner)

    def test_packagers_bind_exact_qualified_release_and_do_not_execute_court(self):
        builder=(ROOT/"tools/build_systemic_repair_r023_operator_kit.py").read_text()
        transport=(ROOT/"tools/build_r023_review_transport.py").read_text()
        self.assertIn("UCM-v0.1-QUALIFICATION.json",builder)
        self.assertIn("UGEL-BATCH-E-r001.zip",builder)
        self.assertIn("PROGRAM-HISTORY.zip",builder)
        self.assertNotIn("subprocess",builder)
        self.assertIn("UCM-v0.1-r023-FOCUSED-SUCCESSOR-REVIEW-TRANSPORT.zip",transport)
        self.assertIn("SEPARATE_USER_RUN_REQUIRED",transport)


if __name__=="__main__":unittest.main()

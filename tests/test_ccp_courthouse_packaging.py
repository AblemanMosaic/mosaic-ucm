from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]


class CcpCourthousePackagingTests(unittest.TestCase):
    def test_operator_kit_is_builder_authored_and_unexecuted(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "operator-kit"
            completed = subprocess.run([
                sys.executable,
                str(ROOT / "tools/build_ccp_courthouse_r015_operator_kit.py"),
                "--out", str(out),
            ], cwd=ROOT, check=True, capture_output=True, text=True)
            result = json.loads(completed.stdout)
            self.assertEqual("PASS", result["status"])
            self.assertFalse(result["tier1_executed"])
            with zipfile.ZipFile(out / "KIT.zip") as archive:
                manifest = json.loads(archive.read("KIT-MANIFEST.json"))
                self.assertTrue(manifest["builder_authored"])
                self.assertFalse(manifest["operator_executed"])
                self.assertFalse(manifest["tier1_executed"])
                self.assertIn("RUN-TIER1.py", archive.namelist())

    def test_runner_is_syntax_checked_but_not_imported(self) -> None:
        source = (ROOT / "operator-kits/ccp-courthouse-r015/RUN-TIER1.py").read_text(
            encoding="utf-8")
        compile(source, "RUN-TIER1.py", "exec")
        self.assertIn("The double-click launcher is the execution boundary", source)


if __name__ == "__main__":
    unittest.main()

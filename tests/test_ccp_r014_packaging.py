from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]


class CcpR014PackagingTests(unittest.TestCase):
    def test_operator_kit_is_builder_authored_and_unexecuted(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / "operator"
            run = subprocess.run([
                sys.executable, "-B",
                str(ROOT / "tools/build_ccp_admissibility_r014_operator_kit.py"),
                "--out", str(output),
            ], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(0, run.returncode, run.stderr + run.stdout)
            with zipfile.ZipFile(output / "KIT.zip") as archive:
                manifest = json.loads(archive.read("KIT-MANIFEST.json"))
            self.assertTrue(manifest["builder_authored"])
            self.assertFalse(manifest["operator_executed"])
            self.assertFalse(manifest["tier1_executed"])
            self.assertNotIn("operator_authored", manifest)

    def test_shareable_fault_schema_hashes_exception_text(self) -> None:
        source = (ROOT / "operator-kits/ccp-admissibility-r014/RUN-TIER1.py").read_text(
            encoding="utf-8")
        self.assertIn('"exception_message_sha256"', source)
        self.assertNotIn('"exception_message": str(error)', source)
        self.assertIn("def guarded_main()", source)


if __name__ == "__main__":
    unittest.main()

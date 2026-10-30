from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from release_common import public_source_body


class PublicSourceScopeTests(unittest.TestCase):
    def test_generated_evidence_and_local_environment_are_excluded(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            (root / "src").mkdir(); (root / "src/code.py").write_text("pass\n")
            (root / "evidence").mkdir(); (root / "evidence/run.json").write_text("{}")
            (root / ".venv").mkdir(); (root / ".venv/host.py").write_text("host")
            paths = [row["path"] for row in public_source_body(root)["members"]]
            self.assertEqual(paths, ["src/code.py"])


if __name__ == "__main__":
    unittest.main()

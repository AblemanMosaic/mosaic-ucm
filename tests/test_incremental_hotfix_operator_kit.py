from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "build_incremental_hotfix_operator_kit.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("incremental_hotfix_operator_builder", BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError("BUILDER_IMPORT_SPEC_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IncrementalHotfixOperatorKitTests(unittest.TestCase):
    def test_fresh_extraction_contains_and_imports_complete_runtime(self) -> None:
        builder = load_builder()
        members = builder._collect_members()
        self.assertIn("src/ucm/system.py", members)
        self.assertIn("src/ucm/correction_transaction.py", members)
        self.assertIn("src/ucm/incremental_hotfix.py", members)
        with tempfile.TemporaryDirectory() as raw:
            kit = Path(raw) / "KIT.zip"
            builder._write_zip(kit, members)
            builder._verify_fresh_extraction(kit, members)


if __name__ == "__main__":
    unittest.main()


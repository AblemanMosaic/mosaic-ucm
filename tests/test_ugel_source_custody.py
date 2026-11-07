from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/verify_ugel_source_archive.py"
SPEC = importlib.util.spec_from_file_location("verify_ugel_source_archive", TOOL)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class UgelSourceCustodyTests(unittest.TestCase):
    def test_exact_batch_e_source_archive_is_closed_and_pinned(self):
        result = MODULE.verify_archive(MODULE.DEFAULT_ARCHIVE)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["source_root"], MODULE.SOURCE_ROOT)
        self.assertFalse(result["subject_code_loaded"])

    def test_resealed_member_mutation_is_refused(self):
        source = MODULE.DEFAULT_ARCHIVE
        with tempfile.TemporaryDirectory(dir=ROOT / ".build") as folder:
            target = Path(folder) / "mutated.zip"
            with zipfile.ZipFile(source) as existing, zipfile.ZipFile(target, "w") as out:
                for info in existing.infolist():
                    data = existing.read(info.filename)
                    if info.filename == "spec/ugel-effects.wit":
                        data += b"\n"
                    out.writestr(info, data)
            with self.assertRaisesRegex(ValueError, "UGEL_SOURCE_ARCHIVE_SHA256_MISMATCH"):
                MODULE.verify_archive(target)


if __name__ == "__main__":
    unittest.main()

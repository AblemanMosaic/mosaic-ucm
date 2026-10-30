from pathlib import Path
import io
import json
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

from amcas_release_common import build_qualification_source_archive
from release_common import public_source_body


class QualificationSourceClosureTests(unittest.TestCase):
    def test_direct_test_dependencies_are_packaged(self):
        raw, anchor = build_qualification_source_archive()
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = set(archive.namelist())
        required = {
            "fixtures/ucl_selfhost_compiler.ucl.json",
            "release/SOURCE-MANIFEST.json",
            "sidecar/UCM-AMCAS-ADAPT.py",
            "tools/build_release.py",
            "tools/prepare_release_contracts.py",
            "tools/release_common.py",
            "tools/verify_release.py",
        }
        self.assertTrue(required.issubset(names), sorted(required - names))
        self.assertEqual(anchor["source_file_count"], len(names) - 1)
        with tempfile.TemporaryDirectory() as temporary:
            staged = Path(temporary)
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                archive.extractall(staged)
            stored = json.loads((staged / "release/SOURCE-MANIFEST.json").read_text(
                encoding="utf-8"))
            self.assertEqual(public_source_body(staged),
                             {key: value for key, value in stored.items() if key != "root"})


if __name__ == "__main__":
    unittest.main()

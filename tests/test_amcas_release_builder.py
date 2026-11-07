from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root
from ucm.artifacts import verify_deterministic_zip

sys.path.insert(0, str(ROOT / "tools"))
from amcas_release_common import build_software_archive  # noqa: E402
from build_amcas_release import build  # noqa: E402


class ReleaseBuilderTests(unittest.TestCase):
    def test_release_separates_software_journal_and_review(self):
        software, anchor = build_software_archive()
        manifest = verify_deterministic_zip(software,
            expected_schema="mosaic.ucm.amcas.canonical-software-archive.v0.1",
            expected_role="CANONICAL_SOFTWARE")
        paths = {row["path"] for row in manifest["files"]}
        self.assertFalse(any(path.startswith(("review/", "historical/", "evidence/",
                                              "vendor/amcas-standard/evidence/"))
                             for path in paths))
        self.assertFalse(any(path.lower().endswith(("evidence.zip", ".tar.gz"))
                             for path in paths))
        body = {"schema": "mosaic.ucm.amcas.qualification.v0.1",
                "source_graph_root": "1" * 64, "source_file_count": 1,
                "test_ids": ["TEST"], "test_count": 1, "test_set_root": root(["TEST"]),
                "failures": 0, "errors": 0, "skips": 0,
                "skill_validation": "PASS", "software_anchor": anchor,
                "source_verified_before_and_after": True, "cache_policy": "DISABLED",
                "status": "PASS", "standing": "INFORMATION_ONLY",
                "authority_effect": "NONE", "real_a5": False, "g0": "CLOSED"}
        qualification = {**body, "qualification_root": root(body)}
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            q = directory / "qualification.json"; q.write_bytes(canonical_bytes(qualification))
            output = directory / "out"
            result = build(q, output)
            self.assertEqual(result["status"], "PASS")
            software_path = output / "MOSAIC-UCM-AMCAS-CANONICAL-SOFTWARE-v0.1.zip"
            journal_path = output / "MOSAIC-UCM-AMCAS-CANONICAL-JOURNAL-v0.1.zip"
            self.assertEqual(software_path.read_bytes(), software)
            verify_deterministic_zip(journal_path.read_bytes(),
                expected_schema="mosaic.ucm.integration-journal-archive.v0.1",
                expected_role="CANONICAL_INTEGRATION_JOURNAL")
            self.assertNotEqual(software_path.read_bytes(), journal_path.read_bytes())
            self.assertEqual(len(list(output.glob("MOSAIC-UCM-AMCAS-*-KIT-v0.1.zip"))), 5)


if __name__ == "__main__":
    unittest.main()

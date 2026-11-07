from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from uclop.canonical import Refusal
from ucm.program_history import (build_frozen_program_registry,
                                 verify_frozen_program_registry)


ROOT = Path(__file__).resolve().parents[1]


class ProgramHistoryTests(unittest.TestCase):
    def test_r023_registry_freezes_predecessor_programs_and_preimages(self):
        registry = json.loads(
            (ROOT / "spec/FROZEN-PROGRAM-REGISTRY.json").read_text(encoding="utf-8"))
        verified = verify_frozen_program_registry(source_root=ROOT,
                                                  registry=registry)
        directories = {row["directory"] for row in verified["directories"]}
        self.assertIn("program/ccp-admissibility-r014", directories)
        self.assertIn("program/pippi-adaptive-r020", directories)
        self.assertIn("program/public-vocabulary-r013", directories)
        self.assertIn("program/ugel-executor-r022", directories)
        self.assertIn(
            "historical/program-preimages/r020/ccp-admissibility-r014",
            directories)
        self.assertIn(
            "historical/program-preimages/r021/public-vocabulary-r013",
            directories)
        self.assertEqual(verified["mutation_policy"],
                         "REFUSE_IN_PLACE_REQUIRE_NEW_SUCCESSOR_DIRECTORY")

    def test_mutated_frozen_member_refuses(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".build") as raw:
            root = Path(raw); directory = root / "program" / "example"
            directory.mkdir(parents=True)
            (directory / "RECORD.json").write_text("{}\n", encoding="utf-8")
            registry = build_frozen_program_registry(
                source_root=root, successor_revision="r023",
                rows=[{"directory": "program/example",
                       "frozen_revision": "r022",
                       "provenance": "TEST_PREDECESSOR"}])
            verify_frozen_program_registry(source_root=root, registry=registry)
            (directory / "RECORD.json").write_text("{\"changed\":true}\n",
                                                     encoding="utf-8")
            with self.assertRaisesRegex(Refusal,
                                        "FROZEN_PROGRAM_CUSTODY_MISMATCH"):
                verify_frozen_program_registry(source_root=root,
                                               registry=registry)

    def test_historical_builders_check_custody_instead_of_rewriting(self):
        commands = [
            ["tools/build_ccp_native_program.py", "--check"],
            ["tools/build_pippi_adaptive_program.py", "--check"],
            ["tools/build_ugel_r022_program.py", "--check"],
            ["tools/build_public_vocabulary.py", "--check"],
        ]
        for script, mode in commands:
            result = subprocess.run(
                [sys.executable, "-I", str(ROOT / script), mode], cwd=ROOT,
                text=True, capture_output=True)
            self.assertEqual(result.returncode, 0,
                             script + "\n" + result.stdout + result.stderr)
        refused = subprocess.run(
            [sys.executable, "-I", str(ROOT / "tools/build_ugel_r022_program.py"),
             "--write"], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(refused.returncode, 3)
        self.assertIn("FROZEN_PROGRAM_MUTATION_REFUSED", refused.stdout)


if __name__ == "__main__":
    unittest.main()

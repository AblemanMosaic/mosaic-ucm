from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

from uclop.canonical import canonical_bytes
from ucm.pippi_constitution import build_constitutional_standards_atlas, build_pipeline_model


ROOT = Path(__file__).resolve().parents[1]


class PippiConstitutionalContractTests(unittest.TestCase):
    def test_generated_contracts_match_live_builders(self) -> None:
        self.assertEqual((ROOT / "spec/PIPPI-CONSTITUTIONAL-STANDARDS-ATLAS.json").read_bytes(),
                         canonical_bytes(build_constitutional_standards_atlas()) + b"\n")
        self.assertEqual((ROOT / "spec/PIPPI-PIPELINE-MODEL.json").read_bytes(),
                         canonical_bytes(build_pipeline_model()) + b"\n")

    def test_generator_check_is_clean(self) -> None:
        run = subprocess.run([sys.executable, "-I", str(ROOT / "tools/build_pippi_constitutional_contracts.py"),
                              "--check"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()

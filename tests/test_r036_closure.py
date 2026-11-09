from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

from ucm.pippi_cmba_composite import THR_CONTRACT_ROOT, composite_profile


ROOT = Path(__file__).resolve().parents[1]


class R036ClosureTests(unittest.TestCase):
    def test_profile_names_every_co_projection_and_distinct_thr_domains(self):
        profile = composite_profile()
        self.assertEqual(profile["required_co_projections"], ["CHC_THR", "CMBA", "CCP", "DKN", "THR"])
        self.assertEqual(profile["conditional_co_projections"], ["G1_SENTINEL", "G2_WITNESS", "G3_DIAGNOSTIC"])
        self.assertEqual(profile["thr_contract_root"], THR_CONTRACT_ROOT)
        self.assertEqual(len({profile["thr_contract"][name] for name in
            ("state", "admissibility", "meaning", "locality", "receipt_identity")}), 5)
        self.assertFalse(profile["effect_authorized"])

    def test_documentation_and_skill_name_claim_ceiling(self):
        docs = (ROOT / "docs/PIPPI-CMBA-COMPOSITE.md").read_text(encoding="utf-8")
        skill = (ROOT / "skill/ucm-pippi-mediated-agent/SKILL.md").read_text(encoding="utf-8")
        for token in ("OBSERVATIONAL", "EFFECT_BOUND", "G1", "G2", "G3", "CCP", "THR"):
            self.assertIn(token, docs)
        self.assertIn("r036\ncomposite profile", skill)
        self.assertIn("does not grant authority", docs)

    def test_generated_contracts_are_current(self):
        process = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8",
            str(ROOT / "tools/check_active_generated_contracts.py")],
            cwd=ROOT.parent, capture_output=True, check=False)
        self.assertEqual(process.returncode, 0, process.stderr.decode(errors="replace"))

    def test_program_rebuilds_and_keeps_cases_open(self):
        process = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8",
            str(ROOT / "tools/build_cmba_composite_r036_program.py"), "--check"],
            cwd=ROOT.parent, capture_output=True, check=False)
        self.assertEqual(process.returncode, 0, process.stderr.decode(errors="replace"))
        program = json.loads((ROOT / "program/cmba-composite-r036/PROGRAM.json").read_bytes())
        self.assertEqual(program["case_count"], 8)
        self.assertFalse(program["acceptance_case_closed"])
        self.assertFalse(program["effect_authorized"])

    def test_predecessor_reconstructs_exact_r035_manifest(self):
        manifest = json.loads((ROOT / "review/r035-predecessor/SOURCE-MANIFEST.json").read_bytes())
        delta = json.loads((ROOT / "review/r035-predecessor/DELTA.json").read_bytes())
        changed = {row["path"]: row["preimage_path"] for row in delta["changed_members"]}
        import hashlib
        for row in manifest["members"]:
            path = ROOT / changed.get(row["path"], row["path"])
            raw = path.read_bytes()
            self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()),
                             (row["bytes"], row["sha256"]), row["path"])


if __name__ == "__main__":
    unittest.main()

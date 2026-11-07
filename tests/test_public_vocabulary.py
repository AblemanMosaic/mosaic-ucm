from __future__ import annotations

import json
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TEST_ID = (
    "test_public_vocabulary.PublicVocabularyTests."
    "test_deterministic_regeneration_and_semantic_lint"
)


class PublicVocabularyTests(unittest.TestCase):
    def test_deterministic_regeneration_and_semantic_lint(self):
        with tempfile.TemporaryDirectory() as raw:
            run = subprocess.run(
                [sys.executable, "-I", "-B",
                 str(ROOT / "tools/build_public_vocabulary.py"), "--check"],
                cwd=raw, text=True, capture_output=True,
            )
        self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
        result = json.loads(run.stdout.strip().splitlines()[-1])
        self.assertEqual(result["status"], "PASS")

        selection = json.loads((ROOT / "program/public-vocabulary-r013/WORK-SELECTION.json")
                               .read_text(encoding="utf-8"))
        state = json.loads((ROOT / "program/public-vocabulary-r013/WORK-UNIT-STATE.json")
                           .read_text(encoding="utf-8"))
        self.assertEqual(selection["direct_closure_check_id"], TEST_ID)
        self.assertEqual(state["direct_closure_check_id"], TEST_ID)

        preimage = ROOT / "historical/public-vocabulary-r013-closure-preimage"
        normalization = json.loads(
            (ROOT / "program/public-vocabulary-r020-normalization/NORMALIZATION.json")
            .read_text(encoding="utf-8"))
        normalization_body = {key: value for key, value in normalization.items()
                              if key != "normalization_root"}
        self.assertEqual(normalization["normalization_root"],
                         hashlib.sha256(json.dumps(
                             normalization_body, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest())
        self.assertEqual(normalization["preimage_direct_closure_check_id"],
                         "public_vocabulary_deterministic_regeneration_and_semantic_lint")
        self.assertEqual(normalization["active_direct_closure_check_id"], TEST_ID)
        for row in normalization["preimage_members"]:
            path = preimage / row["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row["sha256"])
            self.assertEqual(path.stat().st_size, row["bytes"])

        registry = json.loads((ROOT / "spec/PUBLIC-VOCABULARY-REGISTRY.json")
                              .read_text(encoding="utf-8"))
        tokens = [row["token"] for row in registry["entries"]]
        self.assertEqual(len(tokens), len(set(tokens)))
        self.assertTrue(registry["registry_root"])


if __name__ == "__main__":
    unittest.main()

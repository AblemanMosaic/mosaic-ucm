from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from ucm import invoke
from ucm.pippi_global import HubRefusal
from ucm.pippi_reviews import build_operator_kit_contract, validate_operator_kit_contract


ROOT = Path(__file__).resolve().parents[1]
H = [f"{n:x}" * 64 for n in range(1, 5)]


def request():
    return {
        "subject_id": "DEMO_SUBJECT", "revision": "r001",
        "members": [{"path": "RUN.py", "sha256": H[0], "bytes": 12,
                     "role": "SUBJECT_SPECIFIC_RUNNER"}],
        "runtime_sha256": H[1], "qualification_sha256": H[2],
        "cold_boot_sha256": H[3], "runner_path": "RUN.py",
        "evidence_glob": "DEMO-EVIDENCE-*.zip",
    }


class PippiOperatorKitContractTests(unittest.TestCase):
    def test_contract_is_exact_nonexecuting_and_abi_visible(self):
        direct = build_operator_kit_contract(**request())
        self.assertEqual(validate_operator_kit_contract(direct), direct)
        self.assertFalse(direct["operator_executed"])
        self.assertFalse(direct["tier1_executed"])
        self.assertTrue(direct["launcher_contract"]["live_progress_required"])
        via_abi = invoke({"schema": "mosaic.ucm.request.v0.1",
                          "surface": "BUILD_PIPPI_OPERATOR_KIT_CONTRACT",
                          "payload": request(), "request_id": "operator-kit-contract"})
        self.assertEqual(via_abi["result"], direct)

    def test_mutation_and_missing_runner_refuse(self):
        value = build_operator_kit_contract(**request())
        value["operator_executed"] = True
        with self.assertRaises(HubRefusal):
            validate_operator_kit_contract(value)
        changed = request(); changed["runner_path"] = "MISSING.py"
        with self.assertRaises(HubRefusal):
            build_operator_kit_contract(**changed)

    def test_pippi_cli_builds_and_verifies_same_contract(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            base = Path(folder); source = base / "request.json"
            source.write_text(json.dumps(request()), encoding="utf-8")
            env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
            built = subprocess.run([sys.executable, "-B", "-m", "ucm.pippi_cli",
                                    "--data-root", str(base / "data"),
                                    "operator-kit-contract", str(source)],
                                   cwd=base, env=env, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr + built.stdout)
            contract = base / "contract.json"; contract.write_text(built.stdout, encoding="utf-8")
            verified = subprocess.run([sys.executable, "-B", "-m", "ucm.pippi_cli",
                                       "--data-root", str(base / "data"),
                                       "operator-kit-verify", str(contract)],
                                      cwd=base, env=env, capture_output=True, text=True)
            self.assertEqual(verified.returncode, 0, verified.stderr + verified.stdout)
            self.assertEqual(json.loads(verified.stdout)["operator_kit_root"],
                             json.loads(built.stdout)["operator_kit_root"])


if __name__ == "__main__":
    unittest.main()

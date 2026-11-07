from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


class SystemicRepairR023Tests(unittest.TestCase):
    def test_fixed_denominator_program_rebuilds_and_names_live_checks(self):
        run = subprocess.run(
            [sys.executable, "-I", str(ROOT / "tools/build_systemic_repair_r023_program.py"),
             "--check"], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
        folder = ROOT / "program/systemic-repair-r023"
        program = json.loads((folder / "PROGRAM.json").read_text())
        cases = [json.loads(path.read_text()) for path in sorted(folder.glob("*-ACCEPTANCE-CASE.json"))]
        self.assertEqual(program["engineering_revision"], "r023")
        predecessor=json.loads(
            (ROOT/"release/PREDECESSOR-r022-QUALIFICATION.json").read_text())
        self.assertEqual(program["predecessor_qualification_root"],predecessor["root"])
        self.assertEqual(len(cases), 5)
        loader = unittest.TestLoader()
        suite = loader.discover(str(ROOT / "tests"))
        def flatten(value):
            for item in value:
                if isinstance(item, unittest.TestSuite):
                    yield from flatten(item)
                else:
                    yield item
        ids = {case.id() for case in flatten(suite)}
        self.assertTrue({row["verification_surface"] for row in cases} <= ids)

    def test_return_provenance_and_frozen_registry_are_self_rooted(self):
        for path, field in (
            (ROOT / "review/ugel-r022-operator-return/PROVENANCE.json", "provenance_root"),
            (ROOT / "spec/FROZEN-PROGRAM-REGISTRY.json", "registry_root"),
        ):
            value = json.loads(path.read_text())
            body = {key: item for key, item in value.items() if key != field}
            self.assertEqual(value[field], hashlib.sha256(canonical(body)).hexdigest())
        provenance = json.loads((ROOT / "review/ugel-r022-operator-return/PROVENANCE.json").read_text())
        self.assertEqual([row["status"] for row in provenance["operator_runs"]],
                         ["HOLD_FOR_REPAIR", "PASS"])
        self.assertTrue(all(row["operator_executed"] for row in provenance["operator_runs"]))
        self.assertTrue(all(not row["independent_review"] for row in provenance["operator_runs"]))


if __name__ == "__main__":
    unittest.main()

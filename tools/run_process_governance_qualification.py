from __future__ import annotations

import argparse
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "tools")]

from uclop.canonical import canonical_bytes, root
from process_governance_common import source_manifest


def test_ids(suite: unittest.TestSuite) -> list[str]:
    result = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            result.extend(test_ids(item))
        else:
            result.append(item.id())
    return result


class ProgressResult(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        print(json.dumps({"kind": "TEST_START", "test_id": test.id()},
                         sort_keys=True, separators=(",", ":")), flush=True)

    def addSuccess(self, test):
        super().addSuccess(test)
        print(json.dumps({"kind": "TEST_COMPLETE", "status": "PASS",
                          "test_id": test.id()}, sort_keys=True,
                         separators=(",", ":")), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    manifest = source_manifest()
    suite = unittest.defaultTestLoader.loadTestsFromName("tests.test_process_governance")
    identities = sorted(test_ids(suite))
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=0,
                                     resultclass=ProgressResult).run(suite)
    body = {
        "schema": "mosaic.ucm.process-governance-qualification.v0.1",
        "source_manifest_root": manifest["source_manifest_root"],
        "source_file_count": manifest["file_count"],
        "test_ids": identities,
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skips": len(result.skipped),
        "status": "PASS" if result.wasSuccessful() and result.testsRun == len(identities)
                  and not result.skipped else "FAIL",
        "progress_is_evidence": False,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
        "real_a5": False,
        "g0": "CLOSED",
    }
    record = {**body, "qualification_root": root(body)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("xb") as stream:
        stream.write(canonical_bytes(record) + b"\n")
    print(json.dumps({"status": record["status"],
                      "qualification_root": record["qualification_root"],
                      "tests": record["tests_run"]},
                     sort_keys=True, separators=(",", ":")), flush=True)
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

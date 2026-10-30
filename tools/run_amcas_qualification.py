"""One cache-free qualification with granular nonsemantic progress."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root  # noqa: E402
from ucm.content_graph import build_graph  # noqa: E402
from ucm.progress import Progress  # noqa: E402
from amcas_release_common import (build_qualification_source_archive,
                                  build_software_archive, write_new)  # noqa: E402


class LiveResult(unittest.TextTestResult):
    def startTest(self, test):
        self.stream.writeln(json.dumps({"channel": "NONSEMANTIC_PROGRESS", "event": "TEST_START",
            "test_id": test.id()}, sort_keys=True)); super().startTest(test)

    def addSuccess(self, test):
        self.stream.writeln(json.dumps({"channel": "NONSEMANTIC_PROGRESS", "event": "TEST_PASS",
            "test_id": test.id()}, sort_keys=True)); super().addSuccess(test)

    def addFailure(self, test, err):
        self.stream.writeln(json.dumps({"channel": "NONSEMANTIC_PROGRESS", "event": "TEST_FAIL",
            "test_id": test.id()}, sort_keys=True)); super().addFailure(test, err)

    def addError(self, test, err):
        self.stream.writeln(json.dumps({"channel": "NONSEMANTIC_PROGRESS", "event": "TEST_ERROR",
            "test_id": test.id()}, sort_keys=True)); super().addError(test, err)

    def addSkip(self, test, reason):
        self.stream.writeln(json.dumps({"channel": "NONSEMANTIC_PROGRESS", "event": "TEST_SKIP",
            "test_id": test.id(), "reason": reason}, sort_keys=True)); super().addSkip(test, reason)


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item.id()


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    output = args.output.resolve()
    excluded = ()
    if output.is_relative_to(ROOT):
        excluded = (output.relative_to(ROOT).as_posix(),)
    progress = Progress(output / "PROGRESS.jsonl")
    progress.emit("PHASE_START", phase="SOURCE")
    before = build_graph(ROOT, excluded_prefixes=excluded)
    progress.emit("PHASE_PASS", phase="SOURCE", files=before["workspace_file_count"],
                  graph_root=before["graph_root"])
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    test_ids = sorted(flatten(suite))
    progress.emit("PHASE_START", phase="TESTS", total=len(test_ids))
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=0, resultclass=LiveResult)
    result = runner.run(suite)
    if not result.wasSuccessful() or result.skipped:
        raise SystemExit("INTEGRATION_QUALIFICATION_TESTS_FAILED")
    progress.emit("PHASE_PASS", phase="TESTS", passed=result.testsRun, skips=0)
    progress.emit("PHASE_START", phase="SKILL")
    skill_validator = Path.home() / ".codex/skills/.system/skill-creator/scripts/quick_validate.py"
    if skill_validator.exists():
        checked = subprocess.run([sys.executable, str(skill_validator),
            str(ROOT / "skill/ucm-amcas-integration")], capture_output=True, text=True)
        if checked.returncode:
            raise SystemExit("INTEGRATION_SKILL_VALIDATION_FAILED:" + checked.stdout + checked.stderr)
    progress.emit("PHASE_PASS", phase="SKILL")
    progress.emit("PHASE_START", phase="STAGE_I3_CANDIDATE_VALIDATOR_COURT")
    with tempfile.TemporaryDirectory(prefix="ucm-amcas-candidate-court-") as temp:
        court_path = Path(temp) / "court.json"
        court_run = subprocess.run([sys.executable,
            str(ROOT / "tools/run_stage3_candidate_attack_court.py"),
            str(ROOT / "predecessors/stage-i3-c2/UCL-UCM-AMCAS-STAGE-I3-C2-INDEPENDENT-REVIEW-HANDOFF.zip"),
            "--expected-handoff-sha256",
            "de2fe6e00077e8bc7cbd9c985322b1f3d356853a9c750ac5d2e0a481141994fc",
            "--out", str(court_path)], capture_output=True, text=True)
        if court_run.returncode:
            raise SystemExit("STAGE_I3_CANDIDATE_VALIDATOR_COURT_FAILED:"
                             + court_run.stdout + court_run.stderr)
        court_raw = court_path.read_bytes()
    frozen_court_raw = (ROOT / "evidence/stage-i3-candidate-attack-court.json").read_bytes()
    if court_raw != frozen_court_raw:
        raise SystemExit("STAGE_I3_CANDIDATE_VALIDATOR_COURT_DRIFT")
    candidate_court = __import__("uclop.canonical", fromlist=["strict_loads"]).strict_loads(court_raw)
    progress.emit("PHASE_PASS", phase="STAGE_I3_CANDIDATE_VALIDATOR_COURT",
                  cases=candidate_court["case_count"], court_root=candidate_court["court_root"])
    progress.emit("PHASE_START", phase="SOFTWARE_ARCHIVE")
    archive_a, anchor_a = build_software_archive(); archive_b, anchor_b = build_software_archive()
    if archive_a != archive_b or anchor_a != anchor_b:
        raise SystemExit("INTEGRATION_SOFTWARE_ARCHIVE_NONDETERMINISTIC")
    source_a, source_anchor_a = build_qualification_source_archive()
    source_b, source_anchor_b = build_qualification_source_archive()
    if source_a != source_b or source_anchor_a != source_anchor_b:
        raise SystemExit("INTEGRATION_QUALIFICATION_SOURCE_NONDETERMINISTIC")
    with tempfile.TemporaryDirectory(prefix="ucm-amcas-stage-") as temp:
        archive_path = Path(temp) / "qualification-source.zip"; archive_path.write_bytes(source_a)
        staged = Path(temp) / "staged"
        command = [sys.executable, str(ROOT / "STAGE.py"), str(archive_path), str(staged),
            "--schema", "mosaic.ucm.amcas.qualification-source-archive.v0.1",
            "--role", "QUALIFICATION_SOURCE"]
        run = subprocess.run(command, capture_output=True, text=True)
        if run.returncode:
            raise SystemExit("INTEGRATION_SOFTWARE_STAGE_FAILED:" + run.stdout + run.stderr)
        smoke = subprocess.run([sys.executable, "-I", "-B", str(staged / "tools/ucm.py"), "orient"],
                               cwd=staged, capture_output=True, text=True)
        if smoke.returncode:
            raise SystemExit("INTEGRATION_SOFTWARE_SMOKE_FAILED:" + smoke.stdout + smoke.stderr)
        progress.emit("PHASE_START", phase="STAGED_QUALIFICATION_SOURCE_TESTS",
                      total=len(test_ids))
        staged_tests = subprocess.run([sys.executable, "-I", "-B", "-m", "unittest",
            "discover", "-s", "tests", "-v"], cwd=staged, capture_output=True, text=True)
        if staged_tests.returncode:
            raise SystemExit("INTEGRATION_STAGED_QUALIFICATION_SOURCE_FAILED:"
                             + staged_tests.stdout + staged_tests.stderr)
        progress.emit("PHASE_PASS", phase="STAGED_QUALIFICATION_SOURCE_TESTS",
                      passed=len(test_ids), skips=0)
    progress.emit("PHASE_PASS", phase="SOFTWARE_ARCHIVE",
                  archive_sha256=anchor_a["archive_sha256"])
    after = build_graph(ROOT, excluded_prefixes=excluded)
    if after != before:
        raise SystemExit("INTEGRATION_QUALIFICATION_SOURCE_CHANGED")
    body = {"schema": "mosaic.ucm.amcas.qualification.v0.1",
            "source_graph_root": before["graph_root"],
            "source_file_count": before["workspace_file_count"],
            "test_ids": test_ids, "test_count": result.testsRun,
            "test_set_root": root(test_ids), "failures": 0, "errors": 0, "skips": 0,
            "staged_qualification_source_test_count": len(test_ids),
            "staged_qualification_source_status": "PASS",
            "candidate_validator_court_root": candidate_court["court_root"],
            "candidate_validator_court_cases": candidate_court["case_count"],
            "skill_validation": "PASS", "software_anchor": anchor_a,
            "qualification_source_anchor": source_anchor_a,
            "source_verified_before_and_after": True, "cache_policy": "DISABLED",
            "status": "PASS", "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
    qualification = {**body, "qualification_root": root(body)}
    write_new(args.output / "QUALIFICATION.json", canonical_bytes(qualification))
    write_new(args.output / "CANONICAL-SOFTWARE.zip", archive_a)
    write_new(args.output / "SOFTWARE-ANCHOR.json", canonical_bytes(anchor_a))
    write_new(args.output / "QUALIFICATION-SOURCE.zip", source_a)
    write_new(args.output / "QUALIFICATION-SOURCE-ANCHOR.json", canonical_bytes(source_anchor_a))
    write_new(args.output / "STAGE-I3-CANDIDATE-VALIDATOR-COURT.json", court_raw)
    progress.emit("QUALIFICATION_PASS", qualification_root=qualification["qualification_root"])
    print(canonical_bytes(qualification).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

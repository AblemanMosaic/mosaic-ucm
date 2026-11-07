"""One cache-free positive/static qualification for the UCM maturity successor.

The operator-owned adversarial court is deliberately excluded.  This runner
qualifies construction, public APIs, semantic contracts, packaging, and exact
staged reproduction, while emitting a nonsemantic progress stream.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "tools"))

from uclop.canonical import canonical_bytes, root  # noqa: E402
from maturity_release_common import (BOUNDARY, build_profile_overlay,
    build_review_source_archive, build_runtime_archive, collect_payloads,
    source_record, write_new)  # noqa: E402


SAFE_MODULES = [
    "tests.test_maturity_evolution",
    "tests.test_agentic_adaptation_sidecar_c3",
    "tests.test_maturity_foundations",
    "tests.test_public_surface",
    "tests.test_realization",
    "tests.test_integration_cli",
    "tests.test_amcas_integration",
    "tests.test_compatibility_scope",
    "tests.test_ecosystem_stage3_reconciliation",
    "tests.test_ecosystem_session_returns",
    "tests.test_ecosystem_outcomes",
    "tests.test_ecosystem_work",
    "tests.test_ecosystem_successor_returns",
    "tests.test_ecosystem_successor_outcomes",
    "tests.test_ecosystem_audit_returns",
    "tests.test_ecosystem_current_state",
    "tests.test_ecosystem_repair_returns",
    "tests.test_ecosystem_repair_program",
    "tests.test_stage4_c2_positive",
    "tests.test_stage4_c3_operation_state",
    "tests.test_stage4_c3_positive",
    "tests.test_stage4_c4_positive",
    "tests.test_stage4_c5_operational_positive",
    "tests.test_stage4_shadow_preparation",
    "tests.test_amcas_parity",
    "tests.test_constitutional_integration",
    "tests.test_correction_transaction",
    "tests.test_incremental_hotfix",
    "tests.test_incremental_hotfix_abi",
    "tests.test_incremental_hotfix_operator_kit",
    "tests.test_semantic_consolidation",
    "tests.test_courthouse_workflow",
    "tests.test_pippi_foundations",
    "tests.test_pippi_global",
    "tests.test_pippi_integrations",
    "tests.test_pippi_host_boundary",
    "tests.test_pippi_portfolio",
    "tests.test_pippi_release_packaging",
    "tests.test_pippi_reviews",
    "tests.test_pippi_work_units",
    "tests.test_research_reviews",
]


class LiveResult(unittest.TextTestResult):
    def startTest(self, test):
        print(json.dumps({"channel": "NONSEMANTIC_PROGRESS", "event": "TEST_START",
                          "test_id": test.id()}, sort_keys=True), flush=True)
        super().startTest(test)

    def addSuccess(self, test):
        print(json.dumps({"channel": "NONSEMANTIC_PROGRESS", "event": "TEST_PASS",
                          "test_id": test.id()}, sort_keys=True), flush=True)
        super().addSuccess(test)

    def addFailure(self, test, err):
        print(json.dumps({"channel": "NONSEMANTIC_PROGRESS", "event": "TEST_FAIL",
                          "test_id": test.id()}, sort_keys=True), flush=True)
        super().addFailure(test, err)

    def addError(self, test, err):
        print(json.dumps({"channel": "NONSEMANTIC_PROGRESS", "event": "TEST_ERROR",
                          "test_id": test.id()}, sort_keys=True), flush=True)
        super().addError(test, err)

    def addSkip(self, test, reason):
        print(json.dumps({"channel": "NONSEMANTIC_PROGRESS", "event": "TEST_SKIP",
                          "test_id": test.id(), "reason": reason}, sort_keys=True), flush=True)
        super().addSkip(test, reason)


def _flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten(item)
        else:
            yield item.id()


def _deduplicate(suite):
    seen = set(); selected = []
    for test in _tests(suite):
        if test.id() not in seen:
            selected.append(test); seen.add(test.id())
    return unittest.TestSuite(selected)


def _tests(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _tests(item)
        else:
            yield item


def inner(output: Path) -> int:
    staged = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(staged)); sys.path.insert(0, str(staged / "src"))
    sys.path.insert(0, str(staged / "tests"))
    suite = _deduplicate(unittest.defaultTestLoader.loadTestsFromNames(SAFE_MODULES))
    test_ids = sorted(_flatten(suite))
    runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=0, resultclass=LiveResult)
    result = runner.run(suite)
    body = {"schema": "mosaic.ucm.maturity-positive-static-result.v0.1",
            "test_ids": test_ids, "test_count": result.testsRun,
            "failures": len(result.failures), "errors": len(result.errors),
            "skips": len(result.skipped),
            "status": "PASS" if result.wasSuccessful() and not result.skipped else "FAIL",
            **BOUNDARY}
    output.write_bytes(canonical_bytes({**body, "result_root": root(body)}))
    return 0 if body["status"] == "PASS" else 2


def _extract(raw: bytes, destination: Path) -> None:
    archive_path = destination.parent / "qualification-source.zip"
    archive_path.write_bytes(raw)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(destination)


def outer(output: Path) -> int:
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    output = output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit("MATURITY_QUALIFICATION_OUTPUT_NOT_EMPTY")
    output.mkdir(parents=True, exist_ok=True)
    progress = output / "PROGRESS.jsonl"

    def emit(event: str, **fields) -> None:
        record = {"channel": "NONSEMANTIC_PROGRESS", "event": event, **fields}
        with progress.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        print(json.dumps(record, sort_keys=True), flush=True)

    before = source_record(collect_payloads(review=True), role="QUALIFICATION_SOURCE")
    emit("PHASE_PASS", phase="SOURCE_BOUND", files=before["file_count"],
         source_root=before["source_root"])
    source_a, source_anchor_a = build_review_source_archive()
    source_b, source_anchor_b = build_review_source_archive()
    if source_a != source_b or source_anchor_a != source_anchor_b:
        raise SystemExit("MATURITY_QUALIFICATION_SOURCE_NONDETERMINISTIC")
    emit("PHASE_PASS", phase="SOURCE_ARCHIVE", archive_sha256=source_anchor_a["archive_sha256"])

    temporary = Path(tempfile.mkdtemp(prefix="ucm-maturity-qualification-"))
    try:
        staged = temporary / "staged"
        staged.mkdir()
        _extract(source_a, staged)
        inner_result = temporary / "INNER-RESULT.json"
        emit("PHASE_START", phase="POSITIVE_STATIC_TESTS")
        process = subprocess.Popen([sys.executable, "-I", "-B",
                                    str(staged / "tools/run_maturity_qualification.py"),
                                    "--inner", "--output", str(inner_result)], cwd=staged,
                                   stdout=subprocess.PIPE, stderr=None, text=True,
                                   encoding="utf-8", bufsize=1)
        completed = failed = 0
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            with progress.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
            # Tests may exercise their own nonsemantic progress emitters.  Only
            # runner events with an exact test identity contribute to the live
            # qualification summary.
            if (event.get("event") in {"TEST_PASS", "TEST_FAIL", "TEST_ERROR", "TEST_SKIP"}
                    and isinstance(event.get("test_id"), str)):
                completed += 1
                failed += event.get("event") in {"TEST_FAIL", "TEST_ERROR", "TEST_SKIP"}
                if completed % 10 == 0:
                    print(f"[summary] completed={completed} failed={failed}", flush=True)
        return_code = process.wait()
        print(f"[summary] completed={completed} failed={failed}", flush=True)
        if return_code:
            raise SystemExit("MATURITY_POSITIVE_STATIC_TESTS_FAILED")
        result = json.loads(inner_result.read_text(encoding="utf-8"))
        if result["status"] != "PASS" or result["skips"]:
            raise SystemExit("MATURITY_POSITIVE_STATIC_RESULT_INVALID")
        emit("PHASE_PASS", phase="POSITIVE_STATIC_TESTS", tests=result["test_count"])
    finally:
        shutil.rmtree(temporary, ignore_errors=True)

    runtime_a, runtime_anchor_a = build_runtime_archive()
    runtime_b, runtime_anchor_b = build_runtime_archive()
    if runtime_a != runtime_b or runtime_anchor_a != runtime_anchor_b:
        raise SystemExit("MATURITY_RUNTIME_NONDETERMINISTIC")
    overlays = {}
    overlay_anchors = {}
    for profile_id in ("AUTHORING", "COMPATIBILITY", "OPERATIONAL", "VERIFY_ONLY"):
        first, first_anchor = build_profile_overlay(profile_id)
        second, second_anchor = build_profile_overlay(profile_id)
        if first != second or first_anchor != second_anchor:
            raise SystemExit("MATURITY_PROFILE_NONDETERMINISTIC:" + profile_id)
        overlays[profile_id] = first; overlay_anchors[profile_id] = first_anchor
    after = source_record(collect_payloads(review=True), role="QUALIFICATION_SOURCE")
    if after != before:
        raise SystemExit("MATURITY_QUALIFICATION_SOURCE_CHANGED")
    body = {"schema": "mosaic.ucm.maturity-qualification.v0.1",
            "qualification_class": "BUILDER_POSITIVE_STATIC_CACHE_FREE",
            "source": before, "qualification_source_anchor": source_anchor_a,
            "runtime_anchor": runtime_anchor_a, "profile_anchors": overlay_anchors,
            "test_ids": result["test_ids"], "test_count": result["test_count"],
            "test_set_root": root(result["test_ids"]), "failures": 0,
            "errors": 0, "skips": 0, "cache_policy": "DISABLED",
            "operator_adversarial_status": "SEPARATE_USER_RUN_REQUIRED",
            "status": "PASS", **BOUNDARY}
    qualification = {**body, "qualification_root": root(body)}
    write_new(output / "QUALIFICATION.json", canonical_bytes(qualification))
    write_new(output / "CANONICAL-SOFTWARE.zip", runtime_a)
    write_new(output / "QUALIFICATION-SOURCE.zip", source_a)
    for profile_id, raw in overlays.items():
        write_new(output / f"{profile_id}-PROFILE-OVERLAY.zip", raw)
    emit("QUALIFICATION_PASS", qualification_root=qualification["qualification_root"])
    print(canonical_bytes(qualification).decode(), flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inner", action="store_true")
    args = parser.parse_args()
    return inner(args.output) if args.inner else outer(args.output)


if __name__ == "__main__":
    raise SystemExit(main())

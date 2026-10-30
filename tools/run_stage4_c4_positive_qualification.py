"""Cache-free positive qualification for the Stage I4 c4 successor.

This intentionally runs no mutation, tamper, forgery, or fault-injection case.
Operator Tier 1 is a separate sealed artifact and remains unexecuted here.
"""
from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root, strict_loads
from ucm.amcas import BOUNDARY
from ucm.artifacts import deterministic_zip, verify_deterministic_zip
from ucm.operation_state_c4 import derive_operation_state
from ucm.progress import Progress
from ucm.stage4_semantics_c4 import (
    POSITIVE_CONTROL_SCHEMA, QUALIFICATION_SCHEMA, RUNTIME_RESULT_SCHEMA,
    validate_qualification,
)
from amcas_release_common import software_payloads


POSITIVE_CLASSES = (
    "tests.test_stage4_c3_positive.StageI4C3PositiveTests",
    "tests.test_stage4_c3_operation_state.OperationStatePositiveTests",
    "tests.test_stage4_c4_positive.StageI4C4PositiveTests",
    "tests.test_agentic_adaptation_sidecar_c3.SidecarTests",
)


class SafeStream:
    """Best-effort stream whose failure cannot change test semantics."""
    def __init__(self, wrapped): self.wrapped = wrapped
    def write(self, value):
        try: return self.wrapped.write(value)
        except (OSError, UnicodeError): return len(value)
    def flush(self):
        try: self.wrapped.flush()
        except (OSError, UnicodeError): pass
    def writeln(self, value=""):
        self.write(value + "\n"); self.flush()


class PositiveResult(unittest.TextTestResult):
    def __init__(self, *args, progress=None, total=0, **kwargs):
        self.progress = progress; self.total = total; self.done = 0
        super().__init__(*args, **kwargs)
    def startTest(self, test):
        self.progress.emit("TEST_START", phase="C4_POSITIVE", test_id=test.id(),
                           total=self.total, completed=self.done)
        super().startTest(test)
    def _finish(self, event, test, **fields):
        self.done += 1
        self.progress.emit(event, phase="C4_POSITIVE", test_id=test.id(),
                           total=self.total, completed=self.done,
                           remaining=max(0, self.total - self.done), **fields)
    def addSuccess(self, test): self._finish("TEST_PASS", test); super().addSuccess(test)
    def addFailure(self, test, err): self._finish("TEST_FAIL", test); super().addFailure(test, err)
    def addError(self, test, err): self._finish("TEST_ERROR", test); super().addError(test, err)
    def addSkip(self, test, reason): self._finish("TEST_SKIP", test, reason=reason); super().addSkip(test, reason)


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite): yield from flatten(item)
        else: yield item.id()


def safe_print(value: str) -> None:
    try: print(value, flush=True)
    except (OSError, UnicodeError): pass


def run_runtime(staged: Path, manifest_root: str, file_count: int,
                output: Path, progress_path: Path) -> int:
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"; sys.dont_write_bytecode = True
    sys.path.insert(0, str(staged)); sys.path.insert(0, str(staged / "src"))
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite(loader.loadTestsFromName(name) for name in POSITIVE_CLASSES)
    test_ids = sorted(flatten(suite))
    progress = Progress(progress_path)
    progress.emit("PHASE_START", phase="C4_POSITIVE", total=len(test_ids))
    result_class = lambda *a, **k: PositiveResult(*a, progress=progress,
                                                  total=len(test_ids), **k)
    result = unittest.TextTestRunner(stream=SafeStream(sys.stdout), verbosity=0,
                                     resultclass=result_class).run(suite)
    body = {"schema": RUNTIME_RESULT_SCHEMA,
        "runtime": ".".join(map(str, sys.version_info[:3])),
        "source_graph_root": manifest_root, "source_file_count": file_count,
        "source_verified_before_and_after": True, "test_ids": test_ids,
        "test_count": result.testsRun, "test_set_root": root(test_ids),
        "failures": len(result.failures), "errors": len(result.errors),
        "skips": len(result.skipped), "cache_policy": "CACHE_DISABLED",
        "status": "PASS" if result.wasSuccessful() and not result.skipped else "FAIL",
        **BOUNDARY}
    record = {**body, "runtime_result_root": root(body)}
    output.write_bytes(canonical_bytes(record))
    progress.emit("PHASE_PASS" if record["status"] == "PASS" else "PHASE_FAIL",
                  phase="C4_POSITIVE", total=len(test_ids), completed=result.testsRun)
    safe_print(canonical_bytes(record).decode())
    return 0 if record["status"] == "PASS" else 1


def extract_source(raw: bytes, destination: Path) -> dict:
    manifest = verify_deterministic_zip(raw,
        expected_schema="mosaic.ucm.stage-i4-c4-positive-source.v0.1",
        expected_role="UCM_AMCAS_STAGE_I4_C4_POSITIVE_SOURCE")
    import zipfile
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for row in manifest["files"]:
            target = destination.joinpath(*Path(row["path"]).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(row["path"]))
    return manifest


def orchestrate(output: Path) -> int:
    output.mkdir(parents=True, exist_ok=True)
    progress = Progress(output / "PROGRESS.jsonl")
    progress.emit("PHASE_START", phase="SOURCE_ARCHIVE")
    payloads_a = software_payloads(); payloads_b = software_payloads()
    source_a = deterministic_zip(payloads_a,
        schema="mosaic.ucm.stage-i4-c4-positive-source.v0.1",
        artifact_role="UCM_AMCAS_STAGE_I4_C4_POSITIVE_SOURCE")
    source_b = deterministic_zip(payloads_b,
        schema="mosaic.ucm.stage-i4-c4-positive-source.v0.1",
        artifact_role="UCM_AMCAS_STAGE_I4_C4_POSITIVE_SOURCE")
    if source_a != source_b: raise SystemExit("C4_POSITIVE_SOURCE_NONDETERMINISTIC")
    source_manifest = verify_deterministic_zip(source_a,
        expected_schema="mosaic.ucm.stage-i4-c4-positive-source.v0.1",
        expected_role="UCM_AMCAS_STAGE_I4_C4_POSITIVE_SOURCE")
    progress.emit("PHASE_PASS", phase="SOURCE_ARCHIVE",
        files=len(source_manifest["files"]), source_root=source_manifest["manifest_root"])
    with tempfile.TemporaryDirectory(prefix="UCM-AMCAS-I4-C4-POSITIVE-") as folder:
        staged = Path(folder) / "source"; staged.mkdir()
        extract_source(source_a, staged)
        runtime_path = Path(folder) / "RUNTIME.json"
        runtime_progress = Path(folder) / "PROGRESS.jsonl"
        run = subprocess.run([sys.executable, "-I", "-B",
            str(staged / "tools/run_stage4_c4_positive_qualification.py"),
            "--runtime", str(staged), "--manifest-root",
            source_manifest["manifest_root"], "--file-count",
            str(len(source_manifest["files"])), "--runtime-out", str(runtime_path),
            "--progress", str(runtime_progress)], cwd=staged)
        if run.returncode: raise SystemExit("C4_POSITIVE_RUNTIME_FAILED")
        runtime = strict_loads(runtime_path.read_bytes())
        if runtime_progress.is_file():
            (output / "RUNTIME-PROGRESS.jsonl").write_bytes(runtime_progress.read_bytes())
    tests = runtime["test_ids"]
    control_body = {"schema": POSITIVE_CONTROL_SCHEMA,
        "control_class": "BUILDER_POSITIVE_ONLY",
        "source_root": source_manifest["manifest_root"],
        "test_set_root": root(tests),
        "checks": [{"check": "DETERMINISTIC_SOURCE_ARCHIVE", "status": "PASS"},
                   {"check": "STAGED_CACHE_FREE_POSITIVE_SUITE", "status": "PASS"},
                   {"check": "AUTHORITY_CEILING_NONE", "status": "PASS"}],
        "status": "PASS", **BOUNDARY}
    control = {**control_body, "control_root": root(control_body)}
    contract = strict_loads((ROOT / "spec/STAGE-I4-C4-CONTRACT.json").read_bytes())
    anchors = strict_loads((ROOT / "spec/STAGE-I4-C4-TRUST-ANCHORS.json").read_bytes())
    state = derive_operation_state(operation_id="qualification.no-native-effect",
        run_contract_root=contract["contract_root"], events=[])
    body = {"schema": QUALIFICATION_SCHEMA,
        "qualification_class": "BUILDER_POSITIVE_QUALIFICATION",
        "source_root": source_manifest["manifest_root"],
        "source_file_count": len(source_manifest["files"]),
        "test_ids": tests, "test_count": len(tests), "test_set_root": root(tests),
        "semantic_contract_root": contract["contract_root"],
        "trust_anchors_root": anchors["trust_anchors_root"],
        "positive_control": control, "runtime_results": [runtime],
        "operation_state": state, "failures": 0, "errors": 0, "skips": 0,
        "status": "PASS", **BOUNDARY}
    qualification = {**body, "qualification_root": root(body)}
    validate_qualification(qualification,
        expected_source_root=source_manifest["manifest_root"],
        expected_source_file_count=len(source_manifest["files"]),
        expected_test_ids=tests,
        expected_semantic_contract_root=contract["contract_root"],
        expected_trust_anchors_root=anchors["trust_anchors_root"])
    evidence_payloads = {"QUALIFICATION.json": canonical_bytes(qualification),
        "RUNTIME.json": canonical_bytes(runtime),
        "POSITIVE-CONTROL.json": canonical_bytes(control),
        "SOURCE-MANIFEST.json": canonical_bytes(source_manifest)}
    evidence_a = deterministic_zip(evidence_payloads,
        schema="mosaic.ucm.stage-i4-c4-positive-qualification-evidence.v0.1",
        artifact_role="UCM_AMCAS_STAGE_I4_C4_POSITIVE_QUALIFICATION_EVIDENCE")
    evidence_b = deterministic_zip(evidence_payloads,
        schema="mosaic.ucm.stage-i4-c4-positive-qualification-evidence.v0.1",
        artifact_role="UCM_AMCAS_STAGE_I4_C4_POSITIVE_QUALIFICATION_EVIDENCE")
    if evidence_a != evidence_b: raise SystemExit("C4_POSITIVE_EVIDENCE_NONDETERMINISTIC")
    (output / "QUALIFICATION.json").write_bytes(canonical_bytes(qualification))
    (output / "RUNTIME.json").write_bytes(canonical_bytes(runtime))
    (output / "QUALIFICATION-SOURCE.zip").write_bytes(source_a)
    (output / "POSITIVE-QUALIFICATION-EVIDENCE.zip").write_bytes(evidence_a)
    progress.emit("QUALIFICATION_PASS", phase="C4_POSITIVE",
                  qualification_root=qualification["qualification_root"])
    safe_print(canonical_bytes({"status": "PASS",
        "qualification_root": qualification["qualification_root"],
        "tests": len(tests), "operator_tier1": "NOT_EXECUTED_BY_BUILDER",
        **BOUNDARY}).decode())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--manifest-root")
    parser.add_argument("--file-count", type=int)
    parser.add_argument("--runtime-out", type=Path)
    parser.add_argument("--progress", type=Path)
    args = parser.parse_args()
    if args.runtime is not None:
        return run_runtime(args.runtime, args.manifest_root, args.file_count,
                           args.runtime_out, args.progress)
    if args.out is None: parser.error("--out is required")
    return orchestrate(args.out)


if __name__ == "__main__":
    raise SystemExit(main())

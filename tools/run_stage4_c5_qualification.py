"""Cache-free inherited positive qualification for Stage I4 c5.

No mutation, tamper, forgery, or fault-injection case is executed here.
"""
from __future__ import annotations

import argparse
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT / "src"))

from amcas_release_common import software_payloads
from uclop.canonical import canonical_bytes, root, strict_loads
from ucm.amcas import BOUNDARY
from ucm.artifacts import deterministic_zip, verify_deterministic_zip
from ucm.progress import Progress
from ucm.stage4_semantics_c5 import (QUALIFICATION_SCHEMA, RUNTIME_SCHEMA,
                                     validate_qualification)


INHERITED_CLASSES = (
    "tests.test_stage4_c3_positive.StageI4C3PositiveTests",
    "tests.test_stage4_c3_operation_state.OperationStatePositiveTests",
    "tests.test_stage4_c4_positive.StageI4C4PositiveTests",
    "tests.test_agentic_adaptation_sidecar_c3.SidecarTests",
)
CLASSES = (*INHERITED_CLASSES,
           "tests.test_stage4_c5_operational_positive.OperationalGatewayPositiveTests")
SOURCE_SCHEMA = "mosaic.ucm.stage-i4-c5-qualification-source.v0.1"
SOURCE_ROLE = "UCM_AMCAS_STAGE_I4_C5_QUALIFICATION_SOURCE"


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item.id()


def ids_for(classes: tuple[str, ...]) -> list[str]:
    loader = unittest.defaultTestLoader
    return sorted(flatten(unittest.TestSuite(loader.loadTestsFromName(name)
                                             for name in classes)))


class Result(unittest.TextTestResult):
    def __init__(self, *args, progress=None, total=0, **kwargs):
        self.progress = progress; self.total = total; self.done = 0
        super().__init__(*args, **kwargs)
    def startTest(self, test):
        self.progress.emit("TEST_START", phase="C5_QUALIFICATION",
                           test_id=test.id(), completed=self.done, total=self.total)
        super().startTest(test)
    def _finish(self, event, test, **fields):
        self.done += 1
        self.progress.emit(event, phase="C5_QUALIFICATION", test_id=test.id(),
            completed=self.done, total=self.total,
            remaining=max(0, self.total - self.done), **fields)
    def addSuccess(self, test): self._finish("TEST_PASS", test); super().addSuccess(test)
    def addFailure(self, test, err): self._finish("TEST_FAIL", test); super().addFailure(test, err)
    def addError(self, test, err): self._finish("TEST_ERROR", test); super().addError(test, err)
    def addSkip(self, test, reason): self._finish("TEST_SKIP", test, reason=reason); super().addSkip(test, reason)


class SafeStream:
    def write(self, value):
        try: return sys.stdout.write(value)
        except (OSError, UnicodeError): return len(value)
    def flush(self):
        try: sys.stdout.flush()
        except (OSError, UnicodeError): pass


def extract(raw: bytes, destination: Path) -> dict:
    manifest = verify_deterministic_zip(raw, expected_schema=SOURCE_SCHEMA,
                                        expected_role=SOURCE_ROLE)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for row in manifest["files"]:
            target = destination.joinpath(*Path(row["path"]).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(row["path"]))
    return manifest


def runtime(staged: Path, manifest_root: str, file_count: int,
            output: Path, progress_path: Path) -> int:
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"; sys.dont_write_bytecode = True
    sys.path.insert(0, str(staged)); sys.path.insert(0, str(staged / "src"))
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite(loader.loadTestsFromName(name) for name in CLASSES)
    test_ids = sorted(flatten(suite)); progress = Progress(progress_path)
    progress.emit("PHASE_START", phase="C5_QUALIFICATION", total=len(test_ids))
    result_class = lambda *a, **k: Result(*a, progress=progress,
                                         total=len(test_ids), **k)
    result = unittest.TextTestRunner(stream=SafeStream(), verbosity=0,
                                     resultclass=result_class).run(suite)
    body = {"schema": RUNTIME_SCHEMA,
        "runtime": ".".join(map(str, sys.version_info[:3])),
        "source_root": manifest_root, "source_file_count": file_count,
        "source_stable": True, "test_ids": test_ids,
        "test_count": result.testsRun, "test_set_root": root(test_ids),
        "failures": len(result.failures), "errors": len(result.errors),
        "skips": len(result.skipped), "cache_policy": "CACHE_DISABLED",
        "status": "PASS" if result.wasSuccessful() and not result.skipped else "FAIL",
        **BOUNDARY}
    record = {**body, "runtime_result_root": root(body)}
    output.write_bytes(canonical_bytes(record))
    progress.emit("PHASE_PASS" if record["status"] == "PASS" else "PHASE_FAIL",
                  phase="C5_QUALIFICATION", completed=result.testsRun,
                  total=len(test_ids))
    print(canonical_bytes(record).decode(), flush=True)
    return 0 if record["status"] == "PASS" else 1


def orchestrate(output: Path) -> int:
    output.mkdir(parents=True, exist_ok=True)
    progress = Progress(output / "PROGRESS.jsonl")
    progress.emit("PHASE_START", phase="SOURCE_ARCHIVE")
    payloads_a = software_payloads(); payloads_b = software_payloads()
    source_a = deterministic_zip(payloads_a, schema=SOURCE_SCHEMA,
                                 artifact_role=SOURCE_ROLE)
    source_b = deterministic_zip(payloads_b, schema=SOURCE_SCHEMA,
                                 artifact_role=SOURCE_ROLE)
    if source_a != source_b: raise SystemExit("C5_SOURCE_NONDETERMINISTIC")
    manifest = verify_deterministic_zip(source_a, expected_schema=SOURCE_SCHEMA,
                                        expected_role=SOURCE_ROLE)
    progress.emit("PHASE_PASS", phase="SOURCE_ARCHIVE", files=len(manifest["files"]),
                  source_root=manifest["manifest_root"])
    with tempfile.TemporaryDirectory(prefix="UCM-AMCAS-I4-C5-") as raw:
        staged = Path(raw) / "source"; staged.mkdir()
        extract(source_a, staged)
        runtime_path = Path(raw) / "RUNTIME.json"
        runtime_progress = Path(raw) / "PROGRESS.jsonl"
        run = subprocess.run([sys.executable, "-I", "-B",
            str(staged / "tools/run_stage4_c5_qualification.py"),
            "--runtime", str(staged), "--manifest-root", manifest["manifest_root"],
            "--file-count", str(len(manifest["files"])),
            "--runtime-out", str(runtime_path), "--progress", str(runtime_progress)],
            cwd=staged)
        if run.returncode: raise SystemExit("C5_RUNTIME_FAILED")
        runtime_record = strict_loads(runtime_path.read_bytes())
        if runtime_progress.exists():
            (output / "RUNTIME-PROGRESS.jsonl").write_bytes(runtime_progress.read_bytes())
    test_ids = runtime_record["test_ids"]
    inherited = sorted(test_id for test_id in test_ids
        if not test_id.startswith(
            "tests.test_stage4_c5_operational_positive.OperationalGatewayPositiveTests."))
    if len(inherited) != 16:
        raise SystemExit("C5_INHERITED_TEST_IDENTITY_MISMATCH")
    contract = strict_loads((ROOT / "spec/STAGE-I4-C5-CONTRACT.json").read_bytes())
    body = {"schema": QUALIFICATION_SCHEMA,
        "qualification_class": "CACHE_FREE_INHERITED_POSITIVE",
        "source_root": manifest["manifest_root"],
        "source_file_count": len(manifest["files"]),
        "test_ids": test_ids, "test_count": len(test_ids),
        "test_set_root": root(test_ids), "inherited_c4_test_ids": inherited,
        "inherited_c4_test_set_root": root(inherited),
        "operational_contract_root": contract["contract_root"],
        "runtime_results": [runtime_record], "failures": 0, "errors": 0,
        "skips": 0, "cache_policy": "CACHE_DISABLED", "status": "PASS",
        "operator_tier1": "PREPARED_NOT_EXECUTED_BY_BUILDER", **BOUNDARY}
    qualification = {**body, "qualification_root": root(body)}
    validate_qualification(qualification, source_root=manifest["manifest_root"],
        source_file_count=len(manifest["files"]), test_ids=test_ids,
        inherited_c4_test_ids=inherited, contract_root=contract["contract_root"])
    evidence_payloads = {"QUALIFICATION.json": canonical_bytes(qualification),
                         "RUNTIME.json": canonical_bytes(runtime_record),
                         "SOURCE-MANIFEST.json": canonical_bytes(manifest)}
    evidence_a = deterministic_zip(evidence_payloads,
        schema="mosaic.ucm.stage-i4-c5-qualification-evidence.v0.1",
        artifact_role="UCM_AMCAS_STAGE_I4_C5_QUALIFICATION_EVIDENCE")
    evidence_b = deterministic_zip(evidence_payloads,
        schema="mosaic.ucm.stage-i4-c5-qualification-evidence.v0.1",
        artifact_role="UCM_AMCAS_STAGE_I4_C5_QUALIFICATION_EVIDENCE")
    if evidence_a != evidence_b: raise SystemExit("C5_EVIDENCE_NONDETERMINISTIC")
    (output / "QUALIFICATION.json").write_bytes(canonical_bytes(qualification))
    (output / "RUNTIME.json").write_bytes(canonical_bytes(runtime_record))
    (output / "QUALIFICATION-SOURCE.zip").write_bytes(source_a)
    (output / "QUALIFICATION-EVIDENCE.zip").write_bytes(evidence_a)
    progress.emit("QUALIFICATION_PASS", phase="C5_QUALIFICATION",
                  qualification_root=qualification["qualification_root"])
    print(canonical_bytes({"status": "PASS", "tests": len(test_ids),
        "inherited_tests": len(inherited),
        "qualification_root": qualification["qualification_root"],
        "operator_tier1": "NOT_EXECUTED_BY_BUILDER", **BOUNDARY}).decode())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--out", type=Path)
    parser.add_argument("--runtime", type=Path); parser.add_argument("--manifest-root")
    parser.add_argument("--file-count", type=int); parser.add_argument("--runtime-out", type=Path)
    parser.add_argument("--progress", type=Path); args = parser.parse_args()
    if args.runtime is not None:
        return runtime(args.runtime, args.manifest_root, args.file_count,
                       args.runtime_out, args.progress)
    if args.out is None: parser.error("--out is required")
    return orchestrate(args.out)


if __name__ == "__main__":
    raise SystemExit(main())

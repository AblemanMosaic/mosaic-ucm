#!/usr/bin/env python3
"""Qualify the exact public UCM source and bind its rebuilt release."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(1, str(ROOT / "tools"))
sys.path.insert(2, str(ROOT))

from release_common import (ENGINEERING_REVISION, PUBLIC_VERSION, canonical,
                            sha, verify_public_source)  # noqa: E402
from ucm.pippi_portability_evidence import recompute_canonical_outputs  # noqa: E402


STALE_MATURITY_FIELDS = {
    "canonical_software_sha256",
    "independent_review_handoff_sha256",
    "maturity_freeze_root",
    "maturity_qualification_root",
    "maturity_source_root",
    "qualification_source_sha256",
}


def sealed(body: dict) -> dict:
    return {**body, "root": sha(canonical(body))}


def flatten(suite: unittest.TestSuite) -> list[unittest.TestCase]:
    cases: list[unittest.TestCase] = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            cases.extend(flatten(item))
        else:
            cases.append(item)
    return cases


class ProgressResult(unittest.TextTestResult):
    completed = 0

    def _event(self, test: unittest.TestCase, status: str) -> None:
        self.completed += 1
        print(json.dumps({"event": "test", "completed": self.completed,
                          "test_id": test.id(), "status": status}, sort_keys=True),
              file=sys.__stdout__, flush=True)

    def addSuccess(self, test):
        super().addSuccess(test); self._event(test, "PASS")

    def addFailure(self, test, err):
        super().addFailure(test, err); self._event(test, "FAIL")

    def addError(self, test, err):
        super().addError(test, err); self._event(test, "ERROR")

    def addSkip(self, test, reason):
        super().addSkip(test, reason); self._event(test, "SKIP")


class ProgressRunner(unittest.TextTestRunner):
    resultclass = ProgressResult


def final_identity(identity: dict, source_root: str) -> dict:
    body = {key: value for key, value in identity.items()
            if key != "root" and key not in STALE_MATURITY_FIELDS}
    body.update({
        "engineering_revision": ENGINEERING_REVISION,
        "source_manifest_root": source_root,
        "qualification_scope": "EXACT_PUBLIC_SOURCE_AND_RELEASE",
        "qualification_receipt_path": "UCM-v0.1-QUALIFICATION.json",
        "release_status": "CANDIDATE_BUILDER_QUALIFIED_OPERATOR_TIER1_PENDING",
        "operator_tier1_case_count": 0,
        "operator_tier1_status": "SEPARATE_USER_RUN_REQUIRED",
    })
    return sealed(body)


def write_canonical(path: pathlib.Path, value: dict) -> None:
    path.write_bytes(canonical(value) + b"\n")


def verify_staged_adaptive_contracts(runtime_path: pathlib.Path,
                                     cold_boot_path: pathlib.Path) -> None:
    pairs = [
        ("spec/PIPPI-ADAPTIVE-COLD-BOOT-CONTRACT.json",
         "PIPPI/PIPPI-ADAPTIVE-COLD-BOOT-CONTRACT.json"),
        ("spec/PIPPI-CAPABILITY-SURFACE-REGISTRY.json",
         "PIPPI/PIPPI-CAPABILITY-SURFACE-REGISTRY.json"),
        ("spec/PIPPI-MEDIATION-LIBRARY.json",
         "PIPPI/PIPPI-MEDIATION-LIBRARY.json"),
        ("spec/PIPPI-CONSTITUTIONAL-STANDARDS-ATLAS.json",
         "PIPPI/PIPPI-CONSTITUTIONAL-STANDARDS-ATLAS.json"),
        ("spec/PIPPI-PIPELINE-MODEL.json",
         "PIPPI/PIPPI-PIPELINE-MODEL.json"),
    ]
    for suffix in ("bash", "zsh", "fish", "ps1"):
        pairs.extend((
            (f"completions/pippi.{suffix}",
             f"PIPPI/completions/pippi.{suffix}"),
            (f"completions/pippi.{suffix}.json",
             f"PIPPI/completions/pippi.{suffix}.json"),
        ))
    with zipfile.ZipFile(runtime_path) as runtime, zipfile.ZipFile(cold_boot_path) as cold:
        for runtime_name, cold_name in pairs:
            source = (ROOT / runtime_name).read_bytes()
            if runtime.read(runtime_name) != source or cold.read(cold_name) != source:
                raise SystemExit("STAGED_ADAPTIVE_CONTRACT_PARITY_FAILED:" + runtime_name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--portability-gate", type=pathlib.Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out == ROOT or out.is_relative_to(ROOT):
        raise SystemExit("QUALIFICATION_OUTPUT_INSIDE_SOURCE_REFUSED")
    if out.exists() and any(out.iterdir()):
        raise SystemExit("QUALIFICATION_OUTPUT_NOT_EMPTY")
    out.mkdir(parents=True, exist_ok=True)
    temp_root = out / "temp"
    temp_root.mkdir(parents=True, exist_ok=False)
    tempfile.tempdir = str(temp_root)
    os.environ["TEMP"] = str(temp_root)
    os.environ["TMP"] = str(temp_root)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONNOUSERSITE"] = "1"
    os.environ["PYTHONPATH"] = str(ROOT / "src")
    os.environ.pop("PYTHONHOME", None)
    # Qualification is location-independent for the caller while tests that
    # deliberately inspect repository resources receive one explicit root.
    # Test scratch space remains bound to this run's output/temp directory.
    os.chdir(ROOT)

    custody = verify_public_source(ROOT)
    source_probe = subprocess.run([
        sys.executable, "-I", "-B", "-c",
        "import pathlib,sys;"
        f"sys.path.insert(0,{str(ROOT / 'src')!r});"
        "import ucm;print(pathlib.Path(ucm.__file__).resolve())"],
        cwd=temp_root, text=True, capture_output=True)
    if source_probe.returncode:
        sys.stderr.write(source_probe.stdout); sys.stderr.write(source_probe.stderr)
        raise SystemExit("QUALIFICATION_SOURCE_IMPORT_FAILED")
    resolved_ucm = pathlib.Path(source_probe.stdout.strip()).resolve()
    expected_ucm = (ROOT / "src" / "ucm" / "__init__.py").resolve()
    if resolved_ucm != expected_ucm:
        raise SystemExit("QUALIFICATION_SOURCE_SHADOWED:" + str(resolved_ucm))
    source_import_sha256 = sha(resolved_ucm.read_bytes())
    contract_check = subprocess.run(
        [sys.executable, "-B", str(ROOT / "tools/build_pippi_adaptive_contracts.py"),
         "--check"], cwd=ROOT, text=True, capture_output=True)
    if contract_check.returncode:
        sys.stderr.write(contract_check.stdout); sys.stderr.write(contract_check.stderr)
        raise SystemExit("PIPPI_ADAPTIVE_CONTRACT_PARITY_FAILED")
    for tool in ("build_native_core_r032_assets.py",
                 "build_native_core_r033_assets.py",
                 "build_native_closure_r033_program.py"):
        check = subprocess.run(
            [sys.executable, "-B", str(ROOT / "tools" / tool), "--check"],
            cwd=ROOT, text=True, capture_output=True)
        if check.returncode:
            sys.stderr.write(check.stdout); sys.stderr.write(check.stderr)
            raise SystemExit("R033_GENERATED_CONTRACT_PARITY_FAILED:" + tool)
    native_witnesses = [json.loads(
        (ROOT / "evidence/native-core-r033" / name).read_text(encoding="utf-8"))
        for name in ("WINDOWS-NATIVE-CORE-WITNESS.json",
                     "WSL-NATIVE-CORE-WITNESS.json")]
    for witness in native_witnesses:
        witness_body = {key: value for key, value in witness.items()
                        if key != "witness_root"}
        if (witness.get("witness_root") != sha(canonical(witness_body))
                or witness.get("status") != "PASS_CORRESPONDENCE"):
            raise SystemExit("R033_NATIVE_WITNESS_INVALID")
    if ([row.get("leg_id") for row in native_witnesses]
            != ["WINDOWS_NATIVE_C17", "WSL_NATIVE_C17"]
            or native_witnesses[0].get("result_set_root")
            != native_witnesses[1].get("result_set_root")
            or native_witnesses[0].get("results")
            != native_witnesses[1].get("results")):
        raise SystemExit("R033_NATIVE_PLATFORM_CORRESPONDENCE_MISMATCH")
    portability_gate = json.loads(
        args.portability_gate.resolve().read_text(encoding="utf-8"))
    gate_body = {key: value for key, value in portability_gate.items()
                 if key != "portability_gate_root"}
    if (portability_gate.get("portability_gate_root") != sha(canonical(gate_body))
            or portability_gate.get("status") != "PASS_PORTABLE"
            or portability_gate.get("portable_claim_allowed") is not True
            or portability_gate.get("required_leg_ids")
            != ["WINDOWS_NATIVE", "WSL_NATIVE"]):
        raise SystemExit("PORTABILITY_GATE_INVALID")
    witnesses = [json.loads((args.portability_gate.parent / name).read_text(encoding="utf-8"))
                 for name in ("WINDOWS-NATIVE-WITNESS.json", "WSL-NATIVE-WITNESS.json")]
    expected_outputs = recompute_canonical_outputs(ROOT)
    if ([row["witness_root"] for row in witnesses]
            != portability_gate.get("witness_roots")
            or any(row.get("source_root") != custody["source_manifest"]["root"]
                   for row in witnesses)
            or any(row.get("canonical_outputs") != expected_outputs
                   for row in witnesses)):
        raise SystemExit("PORTABILITY_GATE_SOURCE_BINDING_MISMATCH")
    loader = unittest.TestLoader()
    suite = loader.discover(str(ROOT / "tests"))
    cases = flatten(suite)
    test_ids = sorted(case.id() for case in cases)
    if len(test_ids) != len(set(test_ids)):
        raise SystemExit("QUALIFICATION_TEST_ID_DUPLICATE")
    selections = [json.loads(path.read_text(encoding="utf-8")) for path in
                  sorted((ROOT / "program/native-closure-r033").glob(
                      "*-WORK-SELECTION.json"), key=lambda item: item.as_posix())]
    closure_checks = [row.get("direct_closure_check_id") for row in selections]
    if (len(closure_checks) != 7 or len(set(closure_checks)) != 7
            or any(check not in test_ids for check in closure_checks)):
        raise SystemExit("R033_ACCEPTANCE_CLOSURE_CHECK_NOT_IN_QUALIFICATION")
    print(json.dumps({"event": "qualification_start", "tests": len(test_ids),
                      "source_manifest_root": custody["source_manifest"]["root"]},
                     sort_keys=True), flush=True)
    result = ProgressRunner(verbosity=0, buffer=True).run(suite)
    failures = len(result.failures); errors = len(result.errors); skips = len(result.skipped)
    if not result.wasSuccessful() or skips:
        failure = sealed({
            "schema": "mosaic.ucm.public-release-qualification.v0.1",
            "status": "FAIL",
            "source_manifest_root": custody["source_manifest"]["root"],
            "test_count": result.testsRun, "failures": failures,
            "errors": errors, "skips": skips, "test_ids": test_ids,
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED",
        })
        write_canonical(out / "UCM-v0.1-QUALIFICATION-FAILED.json", failure)
        raise SystemExit("PUBLIC_RELEASE_QUALIFICATION_FAILED")

    temp_root.rmdir()

    identity_path = ROOT / "release" / "RELEASE-IDENTITY.json"
    identity = final_identity(json.loads(identity_path.read_text(encoding="utf-8")),
                              custody["source_manifest"]["root"])
    write_canonical(identity_path, identity)

    command = [sys.executable, "-B", str(ROOT / "tools" / "build_release.py"),
               "--output", str(out)]
    built = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if built.returncode:
        sys.stderr.write(built.stdout); sys.stderr.write(built.stderr)
        raise SystemExit("PUBLIC_RELEASE_BUILD_FAILED")
    release = json.loads(built.stdout.strip().splitlines()[-1])
    artifacts = {row["role"]: row for row in release["artifacts"]}
    cold_boot_path = out / "PIPPI-v0.1-adaptive-cold-boot.zip"
    cold_build = subprocess.run([sys.executable, "-B", str(ROOT / "tools" / "build_pippi_cold_boot.py"),
        "--runtime", str(out / "UCM-v0.1-runtime.zip"), "--output", str(cold_boot_path)],
        cwd=ROOT, text=True, capture_output=True)
    if cold_build.returncode:
        sys.stderr.write(cold_build.stdout); sys.stderr.write(cold_build.stderr)
        raise SystemExit("PIPPI_COLD_BOOT_BUILD_FAILED")
    cold_record = json.loads(cold_build.stdout.strip().splitlines()[-1])
    cold_verify = subprocess.run([sys.executable, "-B", str(ROOT / "tools" / "verify_pippi_cold_boot.py"),
        str(cold_boot_path)], cwd=ROOT, text=True, capture_output=True)
    if cold_verify.returncode:
        sys.stderr.write(cold_verify.stdout); sys.stderr.write(cold_verify.stderr)
        raise SystemExit("PIPPI_COLD_BOOT_VERIFY_FAILED")
    cold_verification = json.loads(cold_verify.stdout.strip().splitlines()[-1])
    verify_staged_adaptive_contracts(
        out / "UCM-v0.1-runtime.zip", cold_boot_path)
    receipt = sealed({
        "schema": "mosaic.ucm.public-release-qualification.v0.1",
        "product": "Universal Constitutional Machine",
        "version": PUBLIC_VERSION, "engineering_revision": ENGINEERING_REVISION,
        "status": "PASS",
        "source_manifest_root": custody["source_manifest"]["root"],
        "release_identity_root": identity["root"],
        "release_root": release["root"],
        "runtime_sha256": artifacts["UCM_RUNTIME"]["sha256"],
        "runtime_manifest_root": artifacts["UCM_RUNTIME"]["manifest_root"],
        "sdk_sha256": artifacts["UCM_SDK"]["sha256"],
        "review_sha256": artifacts["UCM_REVIEW"]["sha256"],
        "lineage_sha256": artifacts["UCM_LINEAGE_METADATA"]["sha256"],
        "pippi_cold_boot_sha256": cold_record["sha256"],
        "pippi_cold_boot_manifest_root": cold_verification["manifest_root"],
        "pippi_cold_boot_state_root": cold_verification["state_root"],
        "pippi_cold_boot_thr_body_root": cold_verification["thr_body_root"],
        "pippi_cold_boot_dkn_binding_root": cold_verification["dkn_binding_root"],
        "pippi_cold_boot_certificate_root": cold_verification["certificate_root"],
        "portability_gate_root": portability_gate["portability_gate_root"],
        "portability_witness_roots": portability_gate["witness_roots"],
        "portability_required_leg_ids": portability_gate["required_leg_ids"],
        "native_core_profile_root": native_witnesses[0]["profile_root"],
        "native_core_witness_roots": [row["witness_root"] for row in native_witnesses],
        "native_core_result_set_root": native_witnesses[0]["result_set_root"],
        "native_core_required_leg_ids": [row["leg_id"] for row in native_witnesses],
        "r033_acceptance_closure_check_ids": closure_checks,
        "source_import_path": resolved_ucm.relative_to(ROOT).as_posix(),
        "source_import_sha256": source_import_sha256,
        "test_count": result.testsRun, "failures": 0, "errors": 0, "skips": 0,
        "test_ids": test_ids,
        "test_set_root": sha(canonical(test_ids)),
        "python": ".".join(str(value) for value in sys.version_info[:3]),
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        "real_a5": False, "g0": "CLOSED",
    })
    write_canonical(ROOT / "release" / "UCM-v0.1-QUALIFICATION.json", receipt)
    write_canonical(out / "UCM-v0.1-QUALIFICATION.json", receipt)
    print(json.dumps({"status": "PASS", "qualification_root": receipt["root"],
                      "release_root": release["root"], "test_count": result.testsRun,
                      "runtime_manifest_root": receipt["runtime_manifest_root"]},
                     sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


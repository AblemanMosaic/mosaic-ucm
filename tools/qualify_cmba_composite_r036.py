#!/usr/bin/env python3
"""One cache-free r036 positive/static qualification; never run its court."""
from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests"), str(ROOT / "tools")]
from release_common import canonical, sha, verify_public_source

POSITIVE_MODULES = ("test_pippi_cmba_composite_positive", "test_r036_closure",
                    "test_pippi_turn_workflow_positive", "test_pippi_cli_common_positive")
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def event(phase, **facts):
    print(json.dumps({"phase": phase, **facts}, sort_keys=True), flush=True)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value) + b"\n")


def cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from cases(item)
        else:
            yield item


def run(command, *, cwd, stdout, stderr, code):
    result = subprocess.run(command, cwd=cwd, capture_output=True, check=False)
    stdout.write_bytes(result.stdout)
    stderr.write_bytes(result.stderr)
    if result.returncode:
        raise SystemExit(code)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.is_relative_to(ROOT) or (out.exists() and any(out.iterdir())):
        raise SystemExit("QUALIFICATION_REQUIRES_FRESH_OUTPUT_OUTSIDE_SOURCE")
    out.mkdir(parents=True, exist_ok=True)
    custody = verify_public_source(ROOT)
    manifest = custody["source_manifest"]
    event("SOURCE_VERIFIED", root=manifest["root"], members=manifest["member_count"])
    parsed = 0
    for row in manifest["members"]:
        if row["path"].endswith(".py"):
            ast.parse((ROOT / row["path"]).read_bytes(), filename=row["path"])
            parsed += 1
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name)
                               for name in POSITIVE_MODULES)
    ids = [case.id() for case in cases(suite)]
    class Progress(unittest.TextTestResult):
        def addSuccess(self, test):
            super().addSuccess(test); event("POSITIVE_CHECK_PASS", test_id=test.id())
    with (out / "positive-tests.log").open("w", encoding="utf-8", newline="\n") as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=Progress).run(suite)
    if not result.wasSuccessful() or result.skipped:
        raise SystemExit("POSITIVE_QUALIFICATION_FAILED_SEE_LOG")
    members = {row["path"]: row for row in manifest["members"]}
    origins = []
    for name, module in sorted(sys.modules.items()):
        path = getattr(module, "__file__", None)
        if not path or not (name == "ucm" or name.startswith("ucm.")
                            or name == "uclop" or name.startswith("uclop.")):
            continue
        file = Path(path).resolve()
        if not file.is_relative_to(ROOT / "src"):
            raise SystemExit("QUALIFICATION_FOREIGN_SUBJECT_IMPORT:" + name)
        relative = file.relative_to(ROOT).as_posix()
        if relative not in members or sha(file.read_bytes()) != members[relative]["sha256"]:
            raise SystemExit("QUALIFICATION_IMPORT_BYTES_MISMATCH:" + name)
        origins.append({"module": name, "path": relative,
                        "sha256": members[relative]["sha256"]})
    previous = json.loads((ROOT / "review/r035-predecessor/SOURCE-MANIFEST.json").read_bytes())
    delta = json.loads((ROOT / "review/r035-predecessor/DELTA.json").read_bytes())
    changed = {row["path"]: row["preimage_path"] for row in delta["changed_members"]}
    for row in previous["members"]:
        file = ROOT / changed.get(row["path"], row["path"])
        if not file.is_file() or len(file.read_bytes()) != row["bytes"] or sha(file.read_bytes()) != row["sha256"]:
            raise SystemExit("PREDECESSOR_RECONSTRUCTION_MISMATCH:" + row["path"])
    portability = json.loads((ROOT / "conformance/cmba-composite-r036/PORTABILITY.json").read_bytes())
    if sha(canonical({k: v for k, v in portability.items() if k != "root"})) != portability["root"]:
        raise SystemExit("PORTABILITY_RECORD_ROOT_MISMATCH")
    if portability["status"] != "PASS" or {row["platform"] for row in portability["witnesses"]} != {"WINDOWS_NATIVE", "WSL_NATIVE"}:
        raise SystemExit("PORTABILITY_LEGS_INCOMPLETE")
    for tool, name in (("build_cmba_composite_r036_program.py", "PROGRAM"),
                       ("build_cmba_composite_r036_portability.py", "PORTABILITY"),
                       ("check_active_generated_contracts.py", "GENERATED")):
        command = [sys.executable, "-I", "-B", "-X", "utf8", str(ROOT / "tools" / tool)]
        if tool != "check_active_generated_contracts.py":
            command.append("--check")
        run(command, cwd=ROOT.parent, stdout=out / f"{name}.stdout.json",
            stderr=out / f"{name}.stderr.log", code=name + "_CHECK_FAILED")
    builds = []
    for index in (1, 2):
        folder = out / f"release-{index}"
        run([sys.executable, "-I", "-B", "-X", "utf8", str(ROOT / "tools/build_release.py"),
             "--output", str(folder)], cwd=ROOT.parent,
            stdout=out / f"release-{index}.stdout.json", stderr=out / f"release-{index}.stderr.log",
            code="DETERMINISTIC_RELEASE_BUILD_FAILED")
        files = {p.name: sha(p.read_bytes()) for p in sorted(folder.iterdir()) if p.is_file()}
        builds.append(files)
        event("RELEASE_BUILD_PASS", build=index, artifacts=len(files))
    if builds[0] != builds[1]:
        raise SystemExit("RELEASE_BUILDS_DIVERGED")
    release = json.loads((out / "release-1/UCM-v0.1-release.json").read_bytes())
    run([sys.executable, "-I", "-B", "-X", "utf8", str(ROOT / "tools/verify_release.py"),
         str(out / "release-1/UCM-v0.1-release.json"), "--expected-release-root", release["root"]],
        cwd=ROOT.parent, stdout=out / "release-verification.json",
        stderr=out / "release-verification.stderr.log", code="RELEASE_VERIFICATION_FAILED")
    from verify_pippi_cold_boot import verify as verify_cold_boot
    cold_hashes = []
    cold_proof = None
    for index in (1, 2):
        target = out / f"cold-boot-{index}.zip"
        run([sys.executable, "-I", "-B", "-X", "utf8", str(ROOT / "tools/build_pippi_cold_boot.py"),
             "--runtime", str(out / f"release-{index}/UCM-v0.1-runtime.zip"),
             "--output", str(target)], cwd=ROOT.parent,
            stdout=out / f"cold-boot-{index}.stdout.json", stderr=out / f"cold-boot-{index}.stderr.log",
            code="COLD_BOOT_BUILD_FAILED")
        cold_proof = verify_cold_boot(target.read_bytes())
        if cold_proof["engineering_revision"] != "r036":
            raise SystemExit("COLD_BOOT_REVISION_MISMATCH")
        cold_hashes.append(sha(target.read_bytes()))
    if len(set(cold_hashes)) != 1:
        raise SystemExit("COLD_BOOT_BUILDS_DIVERGED")
    mapping = {
        "R036.PROFILE_CONTRACT": "test_r036_closure.R036ClosureTests.test_profile_names_every_co_projection_and_distinct_thr_domains",
        "R036.OBSERVATIONAL": "test_pippi_cmba_composite_positive.PippiCmbaCompositePositiveTests.test_observational_composite_keeps_roots_distinct",
        "R036.EFFECT_BOUND": "test_pippi_cmba_composite_positive.PippiCmbaCompositePositiveTests.test_effect_history_binds_ccp_and_complete_gates",
        "R036.THR_SEPARATION": "test_r036_closure.R036ClosureTests.test_profile_names_every_co_projection_and_distinct_thr_domains",
        "R036.CLI_ABI": "test_pippi_cmba_composite_positive.PippiCmbaCompositePositiveTests.test_public_cli_exposes_profile_without_writing",
        "R036.DOCUMENTATION": "test_r036_closure.R036ClosureTests.test_documentation_and_skill_name_claim_ceiling",
        "R036.GENERATED_PARITY": "test_r036_closure.R036ClosureTests.test_generated_contracts_are_current",
        "R036.PREDECESSOR_HISTORY": "test_r036_closure.R036ClosureTests.test_predecessor_reconstructs_exact_r035_manifest",
    }
    if any(test_id not in ids for test_id in mapping.values()):
        raise SystemExit("PROGRAM_CLOSURE_TEST_MISSING")
    checks = {key: {"status": "PASS", "test_id": value} for key, value in mapping.items()}
    body = {"schema": "mosaic.ucm.cmba-composite-positive-qualification.v0.1",
        "version": "v0.1", "engineering_revision": "r036",
        "qualification_scope": "POSITIVE_CONSTRUCTION_AND_STATIC_SOURCE", "status": "PASS",
        "source_manifest_root": manifest["root"],
        "release_identity_root": custody["release_identity"]["root"],
        "release_root": release["root"], "artifacts": release["artifacts"],
        "release_files": builds[0], "cold_boot_sha256": cold_hashes[0],
        "cold_boot_verification": cold_proof, "test_count": len(ids),
        "test_ids": sorted(ids), "failures": 0, "errors": 0, "skips": 0,
        "source_python_files_parsed": parsed, "source_imports": origins,
        "program_checks": checks, "predecessor_source_root": previous["root"],
        "predecessor_member_count": len(previous["members"]), "portability": portability,
        "full_legacy_suite_executed": False, "adversarial_cases_executed": 0,
        "operator_court_executed": False, "independent_review": "NOT_PERFORMED",
        "platform": "WINDOWS_NATIVE" if os.name == "nt" else "POSIX_NATIVE",
        "python": sys.version.split()[0], **BOUNDARY}
    receipt = {**body, "root": sha(canonical(body))}
    write(out / "QUALIFICATION.json", receipt)
    event("QUALIFICATION_PASS", root=receipt["root"], source_manifest_root=manifest["root"],
          tests=len(ids), adversarial_cases_executed=0)


if __name__ == "__main__":
    main()

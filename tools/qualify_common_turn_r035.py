"""One cache-free positive/static qualification; never discover adversarial tests."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"tests"),str(ROOT/"tools")]
from release_common import canonical, sha, verify_public_source

POSITIVE_MODULES=("test_pippi_turn_record_positive","test_pippi_cmba_positive",
                  "test_pippi_turn_workflow_positive","test_pippi_cli_common_positive",
                  "test_r035_closure")
BOUNDARY={"standing":"INFORMATION_ONLY","authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}


def event(phase, **facts):
    print(json.dumps({"phase":phase,**facts},sort_keys=True),flush=True)


def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(value)+b"\n")


def test_cases(suite):
    for case in suite:
        if isinstance(case, unittest.TestSuite):yield from test_cases(case)
        else:yield case


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();out=args.output.resolve()
    if out.is_relative_to(ROOT) or (out.exists() and any(out.iterdir())):
        raise SystemExit("QUALIFICATION_REQUIRES_FRESH_OUTPUT_OUTSIDE_SOURCE")
    out.mkdir(parents=True,exist_ok=True)
    custody=verify_public_source(ROOT);manifest=custody["source_manifest"]
    event("SOURCE_VERIFIED",root=manifest["root"],members=manifest["member_count"])
    parsed=0
    for row in manifest["members"]:
        if row["path"].endswith(".py"):
            ast.parse((ROOT/row["path"]).read_bytes(),filename=row["path"]);parsed+=1
    event("STATIC_SYNTAX_PASS",python_sources=parsed)
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in POSITIVE_MODULES)
    ids=[case.id() for case in test_cases(suite)]
    class Progress(unittest.TextTestResult):
        def addSuccess(self,test):
            super().addSuccess(test);event("POSITIVE_CHECK_PASS",test_id=test.id())
        def addFailure(self,test,err):
            super().addFailure(test,err);event("POSITIVE_CHECK_FAIL",test_id=test.id())
        def addError(self,test,err):
            super().addError(test,err);event("POSITIVE_CHECK_ERROR",test_id=test.id())
    with (out/"positive-tests.log").open("w",encoding="utf-8",newline="\n") as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=Progress).run(suite)
    if not result.wasSuccessful() or result.skipped:
        raise SystemExit("POSITIVE_QUALIFICATION_FAILED_SEE_LOG")
    members={row["path"]:row for row in manifest["members"]}
    origins=[]
    for name,module in sorted(sys.modules.items()):
        path=getattr(module,"__file__",None)
        if not path or not (name=="ucm" or name.startswith("ucm.") or name=="uclop" or name.startswith("uclop.")):
            continue
        file=Path(path).resolve()
        if not file.is_relative_to(ROOT/"src"):
            raise SystemExit("QUALIFICATION_FOREIGN_SUBJECT_IMPORT:"+name)
        relative=file.relative_to(ROOT).as_posix()
        if relative not in members or sha(file.read_bytes())!=members[relative]["sha256"]:
            raise SystemExit("QUALIFICATION_IMPORT_BYTES_MISMATCH:"+name)
        origins.append({"module":name,"path":relative,"sha256":members[relative]["sha256"]})
    previous=json.loads((ROOT/"review/r034-predecessor/SOURCE-MANIFEST.json").read_bytes())
    delta=json.loads((ROOT/"review/r034-predecessor/DELTA.json").read_bytes())
    changed={row["path"]:row["preimage_path"] for row in delta["changed_members"]}
    for row in previous["members"]:
        file=ROOT/changed.get(row["path"],row["path"])
        if not file.is_file() or len(file.read_bytes())!=row["bytes"] or sha(file.read_bytes())!=row["sha256"]:
            raise SystemExit("PREDECESSOR_RECONSTRUCTION_MISMATCH:"+row["path"])
    portability=json.loads((ROOT/"conformance/common-turn-r035/PORTABILITY.json").read_bytes())
    expected_output=(ROOT/"conformance/common-turn-r035/EXPECTED-CANONICAL.json").read_bytes()
    if sha(canonical({key:value for key,value in portability.items() if key!="root"}))!=portability["root"]:
        raise SystemExit("PORTABILITY_RECORD_ROOT_MISMATCH")
    if sha(canonical(portability["implementation_members"]))!=portability["implementation_root"]:
        raise SystemExit("PORTABILITY_IMPLEMENTATION_ROOT_MISMATCH")
    for row in portability["implementation_members"]:
        raw=(ROOT/row["path"]).read_bytes()
        if len(raw)!=row["bytes"] or sha(raw)!=row["sha256"]:
            raise SystemExit("PORTABILITY_IMPLEMENTATION_BYTES_MISMATCH:"+row["path"])
    if portability["status"]!="PASS" or {row["platform"] for row in portability["witnesses"]}!={"WINDOWS_NATIVE","WSL_NATIVE"}:
        raise SystemExit("PORTABILITY_LEGS_INCOMPLETE")
    if any(row["canonical_sha256"]!=sha(expected_output) for row in portability["witnesses"]):
        raise SystemExit("PORTABILITY_OUTPUT_MISMATCH")
    for witness in portability["witnesses"]:
        label="WINDOWS" if witness["platform"]=="WINDOWS_NATIVE" else "WSL"
        receipt_path=ROOT/f"review/common-turn-r035-positive/{label}-DEMO-RECEIPT.json"
        evidence_path=ROOT/f"review/common-turn-r035-positive/{label}-PILOT-EVIDENCE.zip"
        if sha(receipt_path.read_bytes())!=witness["demo_receipt_sha256"] or sha(evidence_path.read_bytes())!=witness["evidence_zip_sha256"]:
            raise SystemExit("PORTABILITY_CARRIED_EVIDENCE_PIN_MISMATCH")
        with zipfile.ZipFile(evidence_path) as archive:
            proof=json.loads(archive.read("MANIFEST.json"))
            body={key:value for key,value in proof.items() if key!="manifest_root"}
            if sha(canonical(body))!=proof["manifest_root"] or set(archive.namelist())!={"MANIFEST.json",*(row["path"] for row in proof["files"])}:
                raise SystemExit("PORTABILITY_DEMO_ARCHIVE_MANIFEST_MISMATCH")
            for row in proof["files"]:
                data=archive.read(row["path"])
                if len(data)!=row["bytes"] or sha(data)!=row["sha256"]:
                    raise SystemExit("PORTABILITY_DEMO_ARCHIVE_MEMBER_MISMATCH")
            if archive.read("canonical.json")!=expected_output:
                raise SystemExit("PORTABILITY_DEMO_BYTES_DIVERGED")
    # Recompute the frozen input once on this exact source; progress is separate.
    demo_out=out/"positive-demo"
    demo=subprocess.run([sys.executable,"-I","-B","-X","utf8",str(ROOT/"tools/run_common_turn_r035_demo.py"),
        "--request",str(ROOT/"examples/common-turn-r035/REQUEST.json"),"--output",str(demo_out)],
        capture_output=True,check=False)
    (out/"demo.stdout.jsonl").write_bytes(demo.stdout);(out/"demo.stderr.log").write_bytes(demo.stderr)
    if demo.returncode or (demo_out/"canonical.json").read_bytes()!=expected_output:
        raise SystemExit("EXACT_FROZEN_DEMO_REPLAY_DIVERGED")
    program=subprocess.run([sys.executable,"-I","-B","-X","utf8",str(ROOT/"tools/build_common_turn_r035_program.py"),"--check"],capture_output=True,check=False)
    if program.returncode:raise SystemExit("COMMON_TURN_PROGRAM_CHECK_FAILED")
    event("POSITIVE_AND_HISTORY_PASS",tests=len(ids),predecessor_members=len(previous["members"]))
    builds=[]
    for index in (1,2):
        folder=out/f"release-{index}"
        command=subprocess.run([sys.executable,"-I","-B","-X","utf8",str(ROOT/"tools/build_release.py"),"--output",str(folder)],capture_output=True,check=False)
        (out/f"release-{index}.stdout.json").write_bytes(command.stdout)
        (out/f"release-{index}.stderr.log").write_bytes(command.stderr)
        if command.returncode:raise SystemExit("DETERMINISTIC_RELEASE_BUILD_FAILED")
        files={p.name:sha(p.read_bytes()) for p in sorted(folder.iterdir()) if p.is_file()}
        builds.append(files);event("RELEASE_BUILD_PASS",build=index,artifacts=len(files))
    if builds[0]!=builds[1]:raise SystemExit("RELEASE_BUILDS_DIVERGED")
    release=json.loads((out/"release-1/UCM-v0.1-release.json").read_bytes())
    verified=subprocess.run([sys.executable,"-I","-B","-X","utf8",str(ROOT/"tools/verify_release.py"),
        str(out/"release-1/UCM-v0.1-release.json"),"--expected-release-root",release["root"]],capture_output=True,check=False)
    (out/"release-verification.json").write_bytes(verified.stdout)
    (out/"release-verification.stderr.log").write_bytes(verified.stderr)
    if verified.returncode:raise SystemExit("RELEASE_VERIFICATION_FAILED")
    event("RELEASE_VERIFICATION_PASS",release_root=release["root"])
    cold_boot_hashes=[]
    from verify_pippi_cold_boot import verify as verify_cold_boot
    for index in (1,2):
        cold_boot=out/f"cold-boot-{index}.zip"
        command=subprocess.run([sys.executable,"-I","-B","-X","utf8",str(ROOT/"tools/build_pippi_cold_boot.py"),
            "--runtime",str(out/f"release-{index}/UCM-v0.1-runtime.zip"),"--output",str(cold_boot)],capture_output=True,check=False)
        (out/f"cold-boot-{index}.stdout.json").write_bytes(command.stdout)
        (out/f"cold-boot-{index}.stderr.log").write_bytes(command.stderr)
        if command.returncode:raise SystemExit("COLD_BOOT_BUILD_FAILED")
        cold_boot_proof=verify_cold_boot(cold_boot.read_bytes())
        if cold_boot_proof["engineering_revision"]!="r035":raise SystemExit("COLD_BOOT_REVISION_MISMATCH")
        cold_boot_hashes.append(sha(cold_boot.read_bytes()))
        event("COLD_BOOT_BUILD_AND_VERIFY_PASS",build=index,sha256=cold_boot_hashes[-1])
    if cold_boot_hashes[0]!=cold_boot_hashes[1]:raise SystemExit("COLD_BOOT_BUILDS_DIVERGED")
    verify_public_source(ROOT)
    release=json.loads((out/"release-1/UCM-v0.1-release.json").read_bytes())
    mapping={
        "R035.RUNTIME_IDENTITY":"test_r035_closure.R035ClosureTests.test_runtime_tree_and_installer_revision_binding",
        "R035.REPORT_SUPERSESSION":"test_r035_closure.R035ClosureTests.test_report_amendment_retires_superseded_information_request",
        "R035.ATOMIC_OPENING":"test_r035_closure.R035ClosureTests.test_atomic_opening_commit_exact_retry_is_idempotent",
        "R035.OPERATOR_DURABILITY":"test_r035_closure.R035ClosureTests.test_launcher_contract_names_durable_preservation_and_terminal_receipt",
        "R035.GENERATED_PARITY":"test_r035_closure.R035ClosureTests.test_active_generated_contracts_match_live_generators",
        "R035.CMBA_DENOMINATOR":"test_r035_closure.R035ClosureTests.test_optional_pack_positive_denominator_includes_cmba",
        "R035.HISTORY_PROJECTION":"test_r035_closure.R035ClosureTests.test_report_amendment_retires_superseded_information_request",
    }
    checks={key:{"status":"PASS","test_id":value} for key,value in mapping.items()}
    for row in checks.values():
        if row["test_id"] not in ids:raise SystemExit("PROGRAM_CLOSURE_TEST_MISSING")
    checks["R035.PREDECESSOR_HISTORY"]={"status":"PASS","member_count":len(previous["members"]),"source_root":previous["root"]}
    body={"schema":"mosaic.ucm.common-turn-positive-qualification.v0.1","version":"v0.1","engineering_revision":"r035",
        "qualification_scope":"POSITIVE_CONSTRUCTION_AND_STATIC_SOURCE","status":"PASS",
        "source_manifest_root":manifest["root"],"release_identity_root":custody["release_identity"]["root"],
        "release_root":release["root"],"artifacts":release["artifacts"],"release_files":builds[0],
        "cold_boot_sha256":cold_boot_hashes[0],"cold_boot_verification":cold_boot_proof,
        "test_count":len(ids),"test_ids":sorted(ids),"failures":0,"errors":0,"skips":0,
        "source_python_files_parsed":parsed,"source_imports":origins,"program_checks":checks,
        "full_legacy_suite_executed":False,"adversarial_cases_executed":0,"operator_court_executed":False,
        "independent_review":"NOT_PERFORMED","platform":"WINDOWS_NATIVE" if os.name=="nt" else "POSIX_NATIVE","python":sys.version.split()[0],
        "portability":portability,**BOUNDARY}
    receipt={**body,"root":sha(canonical(body))}
    write(out/"QUALIFICATION.json",receipt)
    event("QUALIFICATION_PASS",root=receipt["root"],source_manifest_root=manifest["root"],tests=len(ids))


if __name__=="__main__":main()

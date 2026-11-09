"""Prepare six isolated Track C executor dispatches without running a model."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def rooted(body: dict, field: str) -> dict:
    return {**body, field: sha(canonical(body))}


def verify(verifier: Path, archive: Path, schema: str, role: str) -> None:
    completed = subprocess.run(
        [sys.executable, str(verifier), str(archive), "--schema", schema,
         "--role", role], capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise SystemExit("STUDY_DISPATCH_ARCHIVE_VERIFY_FAILED:" + completed.stderr.strip())


def prepare(package: Path, expected_package_sha256: str,
            verifier: Path, output: Path, instructions: Path, sealer: Path) -> dict:
    raw = package.read_bytes()
    if sha(raw) != expected_package_sha256:
        raise SystemExit("STUDY_DISPATCH_PACKAGE_PIN_MISMATCH")
    verify(verifier, package, "mosaic.ucm.architecture-study-package.v0.1",
           "ARCHITECTURE_STUDY_PACKAGE")
    if output.exists() and any(output.iterdir()):
        raise SystemExit("STUDY_DISPATCH_OUTPUT_NOT_EMPTY")
    output.mkdir(parents=True, exist_ok=True)
    instruction_raw = instructions.read_bytes()
    verifier_raw = verifier.read_bytes()
    sealer_raw = sealer.read_bytes()
    with zipfile.ZipFile(package) as archive:
        inventory = json.loads(archive.read("STUDY-KIT-INVENTORY.json"))
        if (inventory.get("status") != "READY_NOT_EXECUTED"
                or inventory.get("denominator") != 6
                or len(inventory.get("runs", [])) != 6):
            raise SystemExit("STUDY_DISPATCH_INVENTORY_INVALID")
        rows = []
        for number, item in enumerate(sorted(inventory["runs"], key=lambda row: row["run_id"]), 1):
            member = "runs/" + item["archive"]
            nested = archive.read(member)
            if sha(nested) != item["sha256"] or len(nested) != item["bytes"]:
                raise SystemExit("STUDY_DISPATCH_RUN_KIT_PIN_MISMATCH")
            folder = output / f"DISPATCH-{number:03d}"
            folder.mkdir()
            kit = folder / "RUN-KIT.zip"
            kit.write_bytes(nested)
            verify(verifier, kit, "mosaic.ucm.architecture-study-run-kit.v0.1",
                   "ARCHITECTURE_STUDY_RUN_KIT")
            with zipfile.ZipFile(kit) as run_archive:
                assignment = json.loads(run_archive.read("ASSIGNMENT.json"))
                template = run_archive.read("RUN-OUTPUT.template.json")
                if assignment.get("run_id") != item["run_id"]:
                    raise SystemExit("STUDY_DISPATCH_RUN_BINDING_MISMATCH")
                condition = json.loads(run_archive.read("CONDITION-CONTEXT.json"))
                if "arm_id" in condition or "enforcement_profile" in condition:
                    raise SystemExit("STUDY_DISPATCH_ARM_DISCLOSURE")
            (folder / "RUN-OUTPUT.template.json").write_bytes(template)
            (folder / "SESSION-INSTRUCTIONS.md").write_bytes(instruction_raw)
            (folder / "VERIFY.py").write_bytes(verifier_raw)
            (folder / "SEAL-STUDY-RUN-RETURN.py").write_bytes(sealer_raw)
            seal_command = rf'''@echo off
setlocal EnableExtensions
title UCM Track C execution return sealer
set "PYEXE="
py -3.12 -c "import sys;assert sys.version_info[:2]==(3,12)" >nul 2>nul && set "PYEXE=py -3.12"
if not defined PYEXE py -3.13 -c "import sys;assert sys.version_info[:2]==(3,13)" >nul 2>nul && set "PYEXE=py -3.13"
if not defined PYEXE python -c "import sys;assert (3,12)<=sys.version_info[:2]<(3,14)" >nul 2>nul && set "PYEXE=python"
if not defined PYEXE goto :FAIL
%PYEXE% "%~dp0VERIFY.py" "%~dp0RUN-KIT.zip" --schema "mosaic.ucm.architecture-study-run-kit.v0.1" --role "ARCHITECTURE_STUDY_RUN_KIT" || goto :FAIL
%PYEXE% "%~dp0SEAL-STUDY-RUN-RETURN.py" --run-kit "%~dp0RUN-KIT.zip" --expected-run-kit-sha256 "{item['sha256']}" --capture "%~dp0RETURN-CAPTURE" --output "%~dp0EXECUTION-RETURN.zip" || goto :FAIL
%PYEXE% "%~dp0VERIFY.py" "%~dp0EXECUTION-RETURN.zip" --schema "mosaic.ucm.architecture-study-execution-return.v0.1" --role "ARCHITECTURE_STUDY_EXECUTION_RETURN" || goto :FAIL
echo PASS - EXECUTION-RETURN.zip is ready for coordinator intake and blinded scoring.
pause
exit /b 0
:FAIL
echo ERROR - inspect the diagnostic above.
pause
exit /b 1
'''.replace("\n", "\r\n").encode("ascii")
            (folder / "RUN-SEAL-EXECUTION-RETURN.cmd").write_bytes(seal_command)
            checklist_body = {
                "schema": "mosaic.ucm.architecture-study-return-checklist.v0.1",
                "run_id": item["run_id"],
                "run_kit_sha256": item["sha256"],
                "required_capture": ["ACTIONS", "DIFF", "TESTS", "OUTPUT",
                                     "REVIEW", "REPAIRS", "JOURNAL", "RECEIPTS"],
                "return_status": "NOT_EXECUTED",
                "non_claims": ["NOT_A_RUN_RESULT", "NOT_SCORED", "NOT_A_STUDY_CONCLUSION"],
                **BOUNDARY,
            }
            checklist = rooted(checklist_body, "checklist_root")
            (folder / "RETURN-CHECKLIST.json").write_bytes(canonical(checklist))
            rows.append({"dispatch": folder.name, "run_id": item["run_id"],
                         "run_kit_sha256": item["sha256"],
                         "assignment_root": assignment["assignment_root"]})
    index_body = {
        "schema": "mosaic.ucm.architecture-study-dispatch-index.v0.1",
        "study_root": inventory["study_root"],
        "roster_root": inventory["roster_root"],
        "denominator": 6,
        "dispatches": rows,
        "status": "READY_NOT_EXECUTED",
        "arm_labels_disclosed_to_executors": False,
        "non_claims": ["NO_MODEL_EXECUTION", "NO_RUN_RESULT", "NO_BENEFIT_CLAIM"],
        **BOUNDARY,
    }
    index = rooted(index_body, "dispatch_index_root")
    (output / "COORDINATOR-DISPATCH-INDEX.json").write_bytes(canonical(index))
    return index


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--expected-package-sha256", required=True)
    parser.add_argument("--verifier", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--instructions", type=Path, required=True)
    parser.add_argument("--sealer", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.package.resolve(), args.expected_package_sha256,
                     args.verifier.resolve(), args.output.resolve(),
                     args.instructions.resolve(), args.sealer.resolve())
    print(json.dumps({"status": "PASS", "dispatches": result["denominator"],
                      "dispatch_index_root": result["dispatch_index_root"],
                      "output": str(args.output.resolve()), **BOUNDARY},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

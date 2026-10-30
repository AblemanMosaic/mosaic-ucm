#!/usr/bin/env python3
"""Build, but never execute, the sealed Stage I4 c5 operator court."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from uclop.canonical import canonical_bytes
from ucm.amcas import BOUNDARY
from ucm.artifacts import deterministic_zip, verify_deterministic_zip
SCHEMA="mosaic.ucm.amcas-stage-i4-c5-operator-kit.v0.1"; ROLE="UCM_AMCAS_STAGE_I4_C5_OPERATOR_KIT"
def sha(raw): return hashlib.sha256(raw).hexdigest()
def main():
    p=argparse.ArgumentParser(); p.add_argument("--cold-boot",type=Path,required=True); p.add_argument("--out-dir",type=Path,required=True); a=p.parse_args()
    if a.out_dir.exists(): raise SystemExit("C5_OPERATOR_OUTPUT_EXISTS")
    cold=a.cold_boot.read_bytes(); verify_deterministic_zip(cold,expected_schema="mosaic.ucm.amcas-stage-i4-c5-cold-boot.v0.1",expected_role="UCM_AMCAS_STAGE_I4_C5_COLD_BOOT")
    court=(ROOT/"review/stage4-c5/RUN-STAGE-I4-C5-TIER1.py").read_bytes(); bootstrap=(ROOT/"review/stage4-c5/BOOTSTRAP-STAGE-I4-C5.py").read_bytes(); verifier=(ROOT/"VERIFY.py").read_bytes(); stager=(ROOT/"STAGE.py").read_bytes()
    kit=deterministic_zip({"COLD-BOOT.zip":cold,"RUN-STAGE-I4-C5-TIER1.py":court,"VERIFY.py":verifier,"STAGE.py":stager,"STAGE-I4-C5-CONTRACT.json":(ROOT/"spec/STAGE-I4-C5-CONTRACT.json").read_bytes()},schema=SCHEMA,artifact_role=ROLE)
    verify_deterministic_zip(kit,expected_schema=SCHEMA,expected_role=ROLE)
    a.out_dir.mkdir(parents=True); kit_name="UCL-UCM-AMCAS-STAGE-I4-C5-OPERATOR-KIT.zip"; (a.out_dir/kit_name).write_bytes(kit); (a.out_dir/"BOOTSTRAP-STAGE-I4-C5.py").write_bytes(bootstrap)
    command=(f'''@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\nset "PYEXE="\r\nif exist "%LocalAppData%\\Programs\\Python\\Python312\\python.exe" set "PYEXE=%LocalAppData%\\Programs\\Python\\Python312\\python.exe"\r\nif not defined PYEXE if exist "%LocalAppData%\\Programs\\Python\\Python313\\python.exe" set "PYEXE=%LocalAppData%\\Programs\\Python\\Python313\\python.exe"\r\nif not defined PYEXE where py >nul 2>nul && py -3.12 -c "import sys" >nul 2>nul && set "PYEXE=py -3.12"\r\nif not defined PYEXE where py >nul 2>nul && py -3.13 -c "import sys" >nul 2>nul && set "PYEXE=py -3.13"\r\nif not defined PYEXE where python >nul 2>nul && python -c "import sys;sys.exit(0 if (3,12) <= sys.version_info[:2] < (3,14) else 1)" >nul 2>nul && set "PYEXE=python"\r\nif not defined PYEXE (echo NOTICE: Python 3.12 or 3.13 is required&goto :fail)\r\n%PYEXE% -c "import cryptography; from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey" >nul 2>nul\r\nif errorlevel 1 (echo NOTICE: cryptography 46-50 is required for the Ed25519 receipt court&goto :fail)\r\necho UCM-AMCAS Stage I4 c5 operator Tier 1 review\r\n%PYEXE% BOOTSTRAP-STAGE-I4-C5.py {kit_name} --expected-sha256 {sha(kit)} --output "%CD%"\r\nif errorlevel 1 goto :fail\r\necho.\r\necho PASS - sealed Tier 1 evidence was written beside this command.\r\npause\r\nexit /b 0\r\n:fail\r\necho.\r\necho HOLD_FOR_REPAIR - evidence was preserved when available.\r\npause\r\nexit /b 1\r\n''').encode("ascii")
    (a.out_dir/"RUN-STAGE-I4-C5-TIER1.cmd").write_bytes(command)
    (a.out_dir/"START-HERE.md").write_text("# Stage I4 c5 operator Tier 1\n\nDouble-click `RUN-STAGE-I4-C5-TIER1.cmd` on Windows. It verifies this exact kit, extracts to a disposable directory, streams per-case progress, preserves one sealed evidence ZIP beside the command, removes temporary files, and pauses. The builder authored but did not execute the court. The result is operator-reproduced evidence, not independent reviewer-authored evidence.\n",encoding="utf-8",newline="\n")
    files=[]
    for path in sorted(a.out_dir.iterdir()):
        if path.is_file(): files.append({"path":path.name,"bytes":path.stat().st_size,"sha256":sha(path.read_bytes())})
    boundary={"schema":"codex.exact-artifact-boundary.v1","runner_required_paths":[row["path"] for row in files],"files":files,"allow_extra_artifacts":False,"policy":{"maximum_invocations":1,"maximum_retries":0,"preserve_prior_custody":True,"terminal_capture":["stdout","stderr","exit_code","terminal_receipt"]},**BOUNDARY}
    (a.out_dir/"EXACT-ARTIFACT-BOUNDARY.json").write_bytes(canonical_bytes(boundary))
    print(json.dumps({"status":"PASS","kit_sha256":sha(kit),"directory":str(a.out_dir),"execution":"NOT_PERFORMED_BY_BUILDER",**BOUNDARY},sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from uclop.canonical import canonical_bytes
from ucm.amcas import BOUNDARY
from ucm.artifacts import deterministic_zip, verify_deterministic_zip
def sha(raw): return hashlib.sha256(raw).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--source",type=Path,required=True); ap.add_argument("--out-dir",type=Path,required=True); a=ap.parse_args()
    source=a.source.read_bytes(); contract=(ROOT/"spec/STAGE-I4-C3-CONTRACT.json").read_bytes()
    tier1=(ROOT/"review/stage4-c3/RUN-STAGE-I4-C3-TIER1.py").read_bytes(); qual=(ROOT/"review/stage4-c3/RUN-STAGE-I4-C3-QUALIFICATION.py").read_bytes(); bootstrap=(ROOT/"review/stage4-c3/BOOTSTRAP-STAGE-I4-C3.py").read_bytes()
    subject=deterministic_zip({"QUALIFICATION-SOURCE.zip":source,"STAGE-I4-C3-CONTRACT.json":contract},schema="mosaic.ucm.amcas-stage-i4-c3-operator-subject.v0.1",artifact_role="UCM_AMCAS_STAGE_I4_C3_OPERATOR_SUBJECT")
    kit=deterministic_zip({"QUALIFICATION-SOURCE.zip":source,"STAGE-I4-C3-CONTRACT.json":contract,"OPERATOR-SUBJECT.zip":subject,"RUN-STAGE-I4-C3-TIER1.py":tier1,"RUN-STAGE-I4-C3-QUALIFICATION.py":qual},schema="mosaic.ucm.amcas-stage-i4-c3-operator-kit.v0.1",artifact_role="UCM_AMCAS_STAGE_I4_C3_OPERATOR_KIT")
    verify_deterministic_zip(kit,expected_schema="mosaic.ucm.amcas-stage-i4-c3-operator-kit.v0.1",expected_role="UCM_AMCAS_STAGE_I4_C3_OPERATOR_KIT")
    a.out_dir.mkdir(parents=True,exist_ok=False); kit_path=a.out_dir/"UCL-UCM-AMCAS-STAGE-I4-C3-OPERATOR-KIT.zip"; kit_path.write_bytes(kit); (a.out_dir/"BOOTSTRAP-STAGE-I4-C3.py").write_bytes(bootstrap)
    command=(f'''@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\nset "PYEXE="\r\nwhere py >nul 2>nul && py -3.12 -c "import sys" >nul 2>nul && set "PYEXE=py -3.12"\r\nif not defined PYEXE where py >nul 2>nul && py -3.13 -c "import sys" >nul 2>nul && set "PYEXE=py -3.13"\r\nif not defined PYEXE where python >nul 2>nul && python -c "import sys;sys.exit(0 if (3,12) <= sys.version_info[:2] < (3,14) else 1)" >nul 2>nul && set "PYEXE=python"\r\nif not defined PYEXE (echo NOTICE: Python 3.12 or 3.13 is required&goto :fail)\r\necho UCM-AMCAS Stage I4 c3 consolidated operator review\r\n%PYEXE% BOOTSTRAP-STAGE-I4-C3.py UCL-UCM-AMCAS-STAGE-I4-C3-OPERATOR-KIT.zip --expected-sha256 {sha(kit)} --output "%CD%"\r\nif errorlevel 1 goto :fail\r\necho.\r\necho PASS - sealed evidence was written beside this command.\r\npause\r\nexit /b 0\r\n:fail\r\necho.\r\necho HOLD_FOR_REPAIR - inspect the diagnostic above.\r\npause\r\nexit /b 1\r\n''').encode()
    (a.out_dir/"RUN-STAGE-I4-C3-OPERATOR-REVIEW.cmd").write_bytes(command)
    start=b"# Stage I4 c3 operator review\n\nDouble-click RUN-STAGE-I4-C3-OPERATOR-REVIEW.cmd on Windows with Python 3.12 or 3.13. The sealed 24-case Tier 1 court and one cache-free 88-test qualification run in disposable directories with per-case, per-test, and compact summary progress. Evidence is preserved beside the command and temporary files are removed. This is operator-reproduced builder-authored evidence, not independent review.\n"; (a.out_dir/"START-HERE.md").write_bytes(start)
    files=[]
    for p in sorted(a.out_dir.iterdir()):
        if p.is_file(): files.append({"path":p.name,"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())})
    boundary={"schema":"codex.exact-artifact-boundary.v1","runner_required_paths":[r["path"] for r in files],"files":files,**BOUNDARY}; (a.out_dir/"EXACT-ARTIFACT-BOUNDARY.json").write_bytes(canonical_bytes(boundary))
    print(json.dumps({"status":"PASS","kit_sha256":sha(kit),"subject_sha256":sha(subject),"directory":str(a.out_dir),**BOUNDARY},sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())

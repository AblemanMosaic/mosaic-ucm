#!/usr/bin/env python3
"""Build, but never execute, the r032 native-completion operator kit."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from ucm.pippi_reviews import build_operator_kit_contract  # noqa:E402

FIXED=(1980,1,1,0,0,0)

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()

def sha(raw): return hashlib.sha256(raw).hexdigest()

def write_zip(path,payload):
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,raw in sorted(payload.items()):
            info=zipfile.ZipInfo(name,FIXED);info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16;info.create_system=3;archive.writestr(info,raw)

def build(runtime,qualification,cold_boot,witness_dir,output):
    output.mkdir(parents=True,exist_ok=True)
    source=ROOT/"operator/native-completion-r032"
    payload={
        "RUN-TIER1.py":(source/"RUN-TIER1.py").read_bytes(),
        "KIT-DECLARATION.json":(source/"KIT-DECLARATION.json").read_bytes(),
        "UCM-v0.1-runtime.zip":runtime.read_bytes(),
        "UCM-v0.1-QUALIFICATION.json":qualification.read_bytes(),
        "PIPPI-v0.1-adaptive-cold-boot.zip":cold_boot.read_bytes(),
        "WINDOWS-NATIVE-CORE-WITNESS.json":(witness_dir/"WINDOWS-NATIVE-CORE-WITNESS.json").read_bytes(),
        "WSL-NATIVE-CORE-WITNESS.json":(witness_dir/"WSL-NATIVE-CORE-WITNESS.json").read_bytes(),
        "R031-COURT-REPAIR.json":(ROOT/"operator/transtemporal-native-r031-repaired/COURT-REPAIR.json").read_bytes(),
        "R031-USER-TIER1-PASS-EVIDENCE.zip":(ROOT/"review/r031/USER-TIER1-PASS-EVIDENCE.zip").read_bytes(),
    }
    for path in sorted((ROOT/"program/native-completion-r032").glob("*.json")):
        payload["PROGRAM/"+path.name]=path.read_bytes()
    roles={}
    for name in payload:
        if name=="RUN-TIER1.py": role="SUBJECT_SPECIFIC_RUNNER"
        elif name=="KIT-DECLARATION.json": role="SUBJECT_DECLARATION"
        elif name=="UCM-v0.1-runtime.zip": role="EXACT_RUNTIME"
        elif name=="UCM-v0.1-QUALIFICATION.json": role="QUALIFICATION_RECEIPT"
        elif name=="PIPPI-v0.1-adaptive-cold-boot.zip": role="EXACT_COLD_BOOT"
        elif name.endswith("WITNESS.json"): role="POSITIVE_NATIVE_CORRESPONDENCE_EVIDENCE"
        elif name.startswith("PROGRAM/"): role="GOVERNED_PROGRAM_RECORD"
        else: role="PREDECESSOR_REPAIR_EVIDENCE"
        roles[name]=role
    members=[{"path":name,"sha256":sha(raw),"bytes":len(raw),"role":roles[name]}
             for name,raw in sorted(payload.items())]
    manifest=build_operator_kit_contract(
        subject_id="UCM_R032_NATIVE_COMPLETION",revision="r032",members=members,
        runtime_sha256=sha(payload["UCM-v0.1-runtime.zip"]),
        qualification_sha256=sha(payload["UCM-v0.1-QUALIFICATION.json"]),
        cold_boot_sha256=sha(payload["PIPPI-v0.1-adaptive-cold-boot.zip"]),
        runner_path="RUN-TIER1.py",
        evidence_glob="UCM-r032-NATIVE-COMPLETION-TIER1-*.zip")
    payload["KIT-MANIFEST.json"]=canonical(manifest)+b"\n"
    kit=output/"UCM-r032-NATIVE-COMPLETION-OPERATOR-KIT.zip"
    write_zip(kit,payload);digest=sha(kit.read_bytes())
    ps1=fr'''$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$kit = Join-Path $here "{kit.name}"
$expected = "{digest}"
$temp = Join-Path $env:TEMP ("UCM-r032-NATIVE-COMPLETION-" + [guid]::NewGuid().ToString("N"))
try {{
  Write-Host "UCM r032 Native Completion operator Tier 1 court"
  Write-Host "[1/6] Verifying the sealed operator kit..."
  if ((Get-FileHash -Algorithm SHA256 -LiteralPath $kit).Hash.ToLowerInvariant() -ne $expected) {{ throw "OPERATOR_KIT_HASH_MISMATCH" }}
  New-Item -ItemType Directory -Path $temp | Out-Null
  Write-Host "[2/6] Extracting exact review material into a disposable workspace..."
  Expand-Archive -LiteralPath $kit -DestinationPath $temp
  $candidates = @("$env:LOCALAPPDATA\Programs\Python\Python312\python.exe", "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe")
  $exe = $candidates | Where-Object {{ Test-Path -LiteralPath $_ }} | Select-Object -First 1
  if(-not $exe) {{ $cmd=Get-Command python -ErrorAction SilentlyContinue; if(-not $cmd){{throw "PYTHON_RUNTIME_MISSING"}}; $exe=$cmd.Source }}
  Write-Host "[3/6] Running custody checks and adversarial cases with live progress..."
  & $exe (Join-Path $temp "RUN-TIER1.py") --kit-root $temp --out-dir (Join-Path $temp "evidence")
  $code=$LASTEXITCODE
  $evidence=Get-ChildItem -LiteralPath (Join-Path $temp "evidence") -Filter "*.zip" | Select-Object -First 1
  if(-not $evidence){{throw "TIER1_EVIDENCE_MISSING"}}
  Copy-Item -LiteralPath $evidence.FullName -Destination (Join-Path $here $evidence.Name) -Force
  Write-Host "[4/6] Evidence preserved beside this command: $($evidence.Name)"
  if($code -ne 0){{throw "TIER1_HOLD_FOR_REPAIR"}}
  Write-Host "[5/6] Court status PASS."
  Write-Host "PASS - sealed operator evidence was written beside this command."
}} catch {{ Write-Host "HOLD_FOR_REPAIR - $($_.Exception.Message)"; exit 3 }} finally {{
  Write-Host "[6/6] Removing disposable review files..."
  if(Test-Path -LiteralPath $temp){{Remove-Item -LiteralPath $temp -Recurse -Force}}
}}
'''
    (output/"RUN.ps1").write_text(ps1,encoding="utf-8",newline="\r\n")
    (output/"RUN.cmd").write_text('@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN.ps1"\r\necho.\r\npause\r\n',encoding="utf-8",newline="")
    return {"status":"PASS","kit":str(kit),"kit_sha256":digest,
            "operator_kit_root":manifest["operator_kit_root"],
            "launcher":str(output/"RUN.cmd"),"operator_executed":False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--runtime",type=Path,required=True)
    parser.add_argument("--qualification",type=Path,required=True)
    parser.add_argument("--cold-boot",type=Path,required=True)
    parser.add_argument("--witness-dir",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    print(json.dumps(build(args.runtime.resolve(),args.qualification.resolve(),
        args.cold_boot.resolve(),args.witness_dir.resolve(),args.output.resolve()),sort_keys=True))
    return 0

if __name__=="__main__": raise SystemExit(main())

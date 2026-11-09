#!/usr/bin/env python3
"""Build, but never execute, the r029 collaboration-integrity operator court."""
from __future__ import annotations
import argparse, hashlib, json, zipfile
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];FIXED=(1980,1,1,0,0,0)
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(1,str(ROOT/"tests"))
from ucm.pippi_reviews import build_operator_kit_contract  # noqa: E402
from test_ccp_admissibility_positive import fixture as ccp_fixture  # noqa: E402
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def zip_write(path,payload):
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for name,raw in sorted(payload.items()):
            info=zipfile.ZipInfo(name,FIXED);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;info.create_system=3;zf.writestr(info,raw)
def build(runtime,qualification,cold_boot,out):
    out.mkdir(parents=True,exist_ok=True);source=ROOT/"operator/collaboration-integrity-r029"
    records=ccp_fixture(operation="PROPOSE_PUBLICATION")
    evaluation={"decision":records["decision"],"current_use_snapshot":records["use"],
        "evidence_snapshot":records["evidence"],"jurisdiction_profile":records["profile"],
        "enforcement_perimeter":records["perimeter"],"correspondence":records["correspondence"],
        "expected_anchors":records["anchors"]}
    payload={"RUN-TIER1.py":(source/"RUN-TIER1.py").read_bytes(),"KIT-DECLARATION.json":(source/"KIT-DECLARATION.json").read_bytes(),"CCP-CONTROL-EVALUATION.json":canonical(evaluation)+b"\n","UCM-v0.1-runtime.zip":runtime.read_bytes(),"UCM-v0.1-QUALIFICATION.json":qualification.read_bytes(),"PIPPI-v0.1-adaptive-cold-boot.zip":cold_boot.read_bytes(),"PORTABILITY-GATE.json":(ROOT/"evidence/r029-portability/PORTABILITY-GATE.json").read_bytes(),"WINDOWS-NATIVE-WITNESS.json":(ROOT/"evidence/r029-portability/WINDOWS-NATIVE-WITNESS.json").read_bytes(),"WSL-NATIVE-WITNESS.json":(ROOT/"evidence/r029-portability/WSL-NATIVE-WITNESS.json").read_bytes()}
    for path in sorted((ROOT/"program/collaboration-integrity-r029").glob("*.json")):
        payload[f"PROGRAM/{path.name}"]=path.read_bytes()
    roles={name:("SUBJECT_SPECIFIC_RUNNER" if name=="RUN-TIER1.py" else "SUBJECT_DECLARATION" if name=="KIT-DECLARATION.json" else "EXACT_RUNTIME" if name=="UCM-v0.1-runtime.zip" else "QUALIFICATION_RECEIPT" if name=="UCM-v0.1-QUALIFICATION.json" else "EXACT_COLD_BOOT" if name=="PIPPI-v0.1-adaptive-cold-boot.zip" else "POSITIVE_PORTABILITY_EVIDENCE" if name.endswith("WITNESS.json") or name=="PORTABILITY-GATE.json" else "GOVERNED_PROGRAM_RECORD") for name in payload}
    members=[{"path":n,"sha256":sha(r),"bytes":len(r),"role":roles[n]} for n,r in sorted(payload.items())]
    manifest=build_operator_kit_contract(subject_id="UCM_R029_COLLABORATION_INTEGRITY",revision="r029",members=members,runtime_sha256=sha(payload["UCM-v0.1-runtime.zip"]),qualification_sha256=sha(payload["UCM-v0.1-QUALIFICATION.json"]),cold_boot_sha256=sha(payload["PIPPI-v0.1-adaptive-cold-boot.zip"]),runner_path="RUN-TIER1.py",evidence_glob="UCM-r029-COLLABORATION-INTEGRITY-TIER1-EVIDENCE-*.zip")
    payload["KIT-MANIFEST.json"]=canonical(manifest)+b"\n";kit=out/"UCM-r029-COLLABORATION-INTEGRITY-OPERATOR-KIT.zip";zip_write(kit,payload);digest=sha(kit.read_bytes())
    ps1=f'''$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$kit = Join-Path $here "UCM-r029-COLLABORATION-INTEGRITY-OPERATOR-KIT.zip"
$expected = "{digest}"
$temp = Join-Path $env:TEMP ("UCM-r029-COLLABORATION-INTEGRITY-" + [guid]::NewGuid().ToString("N"))
try {{
  Write-Host "UCM r029 collaboration integrity operator Tier 1 court"
  Write-Host "[1/6] Verifying the sealed operator kit..."
  if ((Get-FileHash -Algorithm SHA256 -LiteralPath $kit).Hash.ToLowerInvariant() -ne $expected) {{ throw "OPERATOR_KIT_HASH_MISMATCH" }}
  New-Item -ItemType Directory -Path $temp | Out-Null
  Write-Host "[2/6] Extracting exact review material into a disposable workspace..."
  Expand-Archive -LiteralPath $kit -DestinationPath $temp
  $candidates = @("$env:LOCALAPPDATA\\Programs\\Python\\Python312\\python.exe", "$env:LOCALAPPDATA\\Programs\\Python\\Python313\\python.exe")
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
    (out/"RUN.ps1").write_text(ps1,encoding="utf-8",newline="\r\n");(out/"RUN.cmd").write_text('@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN.ps1"\r\necho.\r\npause\r\n',encoding="utf-8",newline="")
    return {"status":"PASS","kit":str(kit),"kit_sha256":digest,"launcher":str(out/"RUN.cmd"),"operator_executed":False,"case_scope_count":17}
def main():
    p=argparse.ArgumentParser();p.add_argument("--runtime",type=Path,required=True);p.add_argument("--qualification",type=Path,required=True);p.add_argument("--cold-boot",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.runtime.resolve(),a.qualification.resolve(),a.cold_boot.resolve(),a.output.resolve()),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())

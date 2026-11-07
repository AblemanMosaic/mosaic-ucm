#!/usr/bin/env python3
"""Build, but never execute, the P/PPI r020 operator Tier 1 kit."""
from __future__ import annotations
import argparse,hashlib,json,pathlib,zipfile

ROOT=pathlib.Path(__file__).resolve().parents[1];FIXED=(1980,1,1,0,0,0)
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()

def build(runtime:pathlib.Path,cold:pathlib.Path,out:pathlib.Path):
    payload={"RUN-TIER1.py":(ROOT/"operator/pippi-adaptive-r020/RUN-TIER1.py").read_bytes(),
             "UCM-v0.1-runtime.zip":runtime.read_bytes(),
             "PIPPI-v0.1-adaptive-cold-boot.zip":cold.read_bytes()}
    members=[{"path":n,"sha256":sha(d),"bytes":len(d)} for n,d in sorted(payload.items())]
    body={"schema":"mosaic.ucm.pippi-adaptive-operator-kit.v0.1","revision":"r020",
          "runtime_sha256":sha(payload["UCM-v0.1-runtime.zip"]),
          "cold_boot_sha256":sha(payload["PIPPI-v0.1-adaptive-cold-boot.zip"]),
          "members":members,"member_count":len(members),"builder_authored":True,
          "operator_executed":False,"tier1_executed":False,"standing":"INFORMATION_ONLY",
          "authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}
    manifest={**body,"manifest_root":sha(canonical(body))};payload["KIT-MANIFEST.json"]=canonical(manifest)+b"\n"
    out.mkdir(parents=True,exist_ok=True);kit=out/"PIPPI-r020-OPERATOR-KIT.zip"
    with zipfile.ZipFile(kit,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for name,data in sorted(payload.items()):
            info=zipfile.ZipInfo(name,FIXED);info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16;info.create_system=3;zf.writestr(info,data)
    kit_sha=sha(kit.read_bytes())
    ps1=f'''$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$kit = Join-Path $here "PIPPI-r020-OPERATOR-KIT.zip"
$expected = "{kit_sha}"
$temp = Join-Path $env:TEMP ("PIPPI-r020-" + [guid]::NewGuid().ToString("N"))
try {{
  Write-Host "P/PPI r020 adaptive operator Tier 1 court"
  Write-Host "[1/6] Verifying the sealed operator kit..."
  $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $kit).Hash.ToLowerInvariant()
  if ($actual -ne $expected) {{ throw "OPERATOR_KIT_HASH_MISMATCH" }}
  New-Item -ItemType Directory -Path $temp | Out-Null
  Write-Host "[2/6] Extracting exact review material into a disposable workspace..."
  Expand-Archive -LiteralPath $kit -DestinationPath $temp
  $python = (Get-Command python -ErrorAction SilentlyContinue).Source
  if (-not $python) {{ throw "PYTHON_RUNTIME_MISSING" }}
  Write-Host "[3/6] Running custody checks and adversarial cases with live progress..."
  & $python (Join-Path $temp "RUN-TIER1.py") --kit-root $temp --out-dir (Join-Path $temp "evidence")
  $code = $LASTEXITCODE
  $evidence = Get-ChildItem -LiteralPath (Join-Path $temp "evidence") -Filter "*.zip" | Select-Object -First 1
  if (-not $evidence) {{ throw "TIER1_EVIDENCE_MISSING" }}
  Copy-Item -LiteralPath $evidence.FullName -Destination (Join-Path $here $evidence.Name) -Force
  Write-Host "[4/6] Evidence preserved beside this command: $($evidence.Name)"
  if ($code -ne 0) {{ throw "TIER1_HOLD_FOR_REPAIR" }}
  Write-Host "[5/6] Court status PASS."
  Write-Host "PASS - sealed operator evidence was written beside this command."
}} catch {{
  Write-Host "HOLD_FOR_REPAIR - $($_.Exception.Message)"
  exit 3
}} finally {{
  Write-Host "[6/6] Removing disposable review files..."
  if (Test-Path -LiteralPath $temp) {{ Remove-Item -LiteralPath $temp -Recurse -Force }}
}}
'''
    (out/"RUN.ps1").write_text(ps1,encoding="utf-8",newline="\r\n")
    (out/"RUN.cmd").write_text('@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN.ps1"\r\necho.\r\npause\r\n',encoding="utf-8",newline="")
    return {"status":"PASS","kit":str(kit),"kit_sha256":kit_sha,"launcher":str(out/"RUN.cmd")}

def main():
    p=argparse.ArgumentParser();p.add_argument("--runtime",type=pathlib.Path,required=True);p.add_argument("--cold-boot",type=pathlib.Path,required=True);p.add_argument("--output",type=pathlib.Path,required=True);a=p.parse_args()
    print(json.dumps(build(a.runtime.resolve(),a.cold_boot.resolve(),a.output.resolve()),sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())

#!/usr/bin/env python3
"""Build, but never execute, the r022 UGEL operator court kit."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FIXED = (1980, 1, 1, 0, 0, 0)
sys.path.insert(0, str(ROOT / "src"))
from ucm.pippi_reviews import build_operator_kit_contract


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build(runtime: Path, qualification: Path, cold_boot: Path, out: Path):
    payload = {
        "RUN-TIER1.py": (ROOT / "operator/ugel-executor-r022/RUN-TIER1.py").read_bytes(),
        "KIT-DECLARATION.json": (ROOT / "operator/ugel-executor-r022/KIT-DECLARATION.json").read_bytes(),
        "UCM-v0.1-runtime.zip": runtime.read_bytes(),
        "UCM-v0.1-QUALIFICATION.json": qualification.read_bytes(),
    }
    roles = {"RUN-TIER1.py": "SUBJECT_SPECIFIC_RUNNER",
             "KIT-DECLARATION.json": "SUBJECT_DECLARATION",
             "UCM-v0.1-runtime.zip": "EXACT_RUNTIME",
             "UCM-v0.1-QUALIFICATION.json": "QUALIFICATION_RECEIPT"}
    members = [{"path": name, "sha256": sha(raw), "bytes": len(raw),
                "role": roles[name]} for name, raw in sorted(payload.items())]
    manifest = build_operator_kit_contract(
        subject_id="UCM_UGEL_EXECUTOR_INTEGRATION", revision="r022",
        members=members, runtime_sha256=sha(payload["UCM-v0.1-runtime.zip"]),
        qualification_sha256=sha(payload["UCM-v0.1-QUALIFICATION.json"]),
        cold_boot_sha256=sha(cold_boot.read_bytes()), runner_path="RUN-TIER1.py",
        evidence_glob="UCM-UGEL-r022-TIER1-EVIDENCE-*.zip")
    payload["KIT-MANIFEST.json"] = canonical(manifest) + b"\n"
    out.mkdir(parents=True, exist_ok=True)
    kit = out / "UCM-UGEL-r022-OPERATOR-KIT.zip"
    with zipfile.ZipFile(kit, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for name, raw in sorted(payload.items()):
            info = zipfile.ZipInfo(name, FIXED); info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16; info.create_system = 3
            archive.writestr(info, raw)
    digest = sha(kit.read_bytes())
    ps1 = f'''$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$kit = Join-Path $here "UCM-UGEL-r022-OPERATOR-KIT.zip"
$expected = "{digest}"
$temp = Join-Path $env:TEMP ("UCM-UGEL-r022-" + [guid]::NewGuid().ToString("N"))
try {{
  Write-Host "UCM UGEL r022 operator Tier 1 court"
  Write-Host "[1/6] Verifying the sealed operator kit..."
  if ((Get-FileHash -Algorithm SHA256 -LiteralPath $kit).Hash.ToLowerInvariant() -ne $expected) {{ throw "OPERATOR_KIT_HASH_MISMATCH" }}
  New-Item -ItemType Directory -Path $temp | Out-Null
  Write-Host "[2/6] Extracting exact review material into a disposable workspace..."
  Expand-Archive -LiteralPath $kit -DestinationPath $temp
  $python = Get-Command py -ErrorAction SilentlyContinue
  if ($python) {{ $exe=$python.Source; $pyArgs=@("-3.12") }} else {{ $cmd=Get-Command python -ErrorAction SilentlyContinue; if(-not $cmd){{throw "PYTHON_RUNTIME_MISSING"}}; $exe=$cmd.Source; $pyArgs=@() }}
  Write-Host "[3/6] Running custody checks and adversarial cases with live progress..."
  & $exe @pyArgs (Join-Path $temp "RUN-TIER1.py") --kit-root $temp --out-dir (Join-Path $temp "evidence")
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
    (out / "RUN.ps1").write_text(ps1, encoding="utf-8", newline="\r\n")
    (out / "RUN.cmd").write_text(
        '@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN.ps1"\r\necho.\r\npause\r\n',
        encoding="utf-8", newline="")
    return {"status": "PASS", "kit": str(kit), "kit_sha256": digest,
            "launcher": str(out / "RUN.cmd"), "operator_executed": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--cold-boot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.runtime.resolve(), args.qualification.resolve(),
                           args.cold_boot.resolve(), args.output.resolve()),
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build, but never execute, the r023 systemic repair operator court."""
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
from ucm.pippi_reviews import build_operator_kit_contract  # noqa: E402


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def deterministic_zip(path: Path, payload: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for name, raw in sorted(payload.items()):
            info = zipfile.ZipInfo(name, FIXED); info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16; info.create_system = 3
            archive.writestr(info, raw)


def history_archive(out: Path) -> Path:
    registry_path = ROOT / "spec/FROZEN-PROGRAM-REGISTRY.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    payload = {"spec/FROZEN-PROGRAM-REGISTRY.json": registry_path.read_bytes()}
    for directory in registry["directories"]:
        for member in directory["members"]:
            relative = f"{directory['directory']}/{member['path']}"
            payload[relative] = (ROOT / relative).read_bytes()
    path = out / "PROGRAM-HISTORY.zip"
    deterministic_zip(path, payload)
    return path


def build(runtime: Path, qualification: Path, cold_boot: Path, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    history = history_archive(out)
    payload = {
        "RUN-TIER1.py": (ROOT / "operator/systemic-repair-r023/RUN-TIER1.py").read_bytes(),
        "KIT-DECLARATION.json": (ROOT / "operator/systemic-repair-r023/KIT-DECLARATION.json").read_bytes(),
        "UCM-v0.1-runtime.zip": runtime.read_bytes(),
        "UCM-v0.1-QUALIFICATION.json": qualification.read_bytes(),
        "UGEL-BATCH-E-r001.zip": (ROOT / "qualification/inputs/ugel/UGEL-BATCH-E-r001.zip").read_bytes(),
        "verify_ugel_source_archive.py": (ROOT / "tools/verify_ugel_source_archive.py").read_bytes(),
        "PROGRAM-HISTORY.zip": history.read_bytes(),
        "R022-OPERATOR-PROVENANCE.json": (ROOT / "review/ugel-r022-operator-return/PROVENANCE.json").read_bytes(),
        "R022-UGEL-TIER1-PASS-EVIDENCE.zip": (ROOT / "review/ugel-r022-operator-return/UCM-UGEL-r022-TIER1-PASS-EVIDENCE.zip").read_bytes(),
    }
    roles = {
        "RUN-TIER1.py":"SUBJECT_SPECIFIC_RUNNER",
        "KIT-DECLARATION.json":"SUBJECT_DECLARATION",
        "UCM-v0.1-runtime.zip":"EXACT_RUNTIME",
        "UCM-v0.1-QUALIFICATION.json":"QUALIFICATION_RECEIPT",
        "UGEL-BATCH-E-r001.zip":"EXACT_EXTERNAL_SOURCE",
        "verify_ugel_source_archive.py":"READ_ONLY_EXTERNAL_SOURCE_VERIFIER",
        "PROGRAM-HISTORY.zip":"FROZEN_PROGRAM_CUSTODY",
        "R022-OPERATOR-PROVENANCE.json":"PREDECESSOR_OPERATOR_PROVENANCE",
        "R022-UGEL-TIER1-PASS-EVIDENCE.zip":"PREDECESSOR_OPERATOR_EVIDENCE",
    }
    members = [{"path":name,"sha256":sha(raw),"bytes":len(raw),"role":roles[name]}
               for name, raw in sorted(payload.items())]
    manifest = build_operator_kit_contract(
        subject_id="UCM_R023_SYSTEMIC_REPAIR", revision="r023", members=members,
        runtime_sha256=sha(payload["UCM-v0.1-runtime.zip"]),
        qualification_sha256=sha(payload["UCM-v0.1-QUALIFICATION.json"]),
        cold_boot_sha256=sha(cold_boot.read_bytes()), runner_path="RUN-TIER1.py",
        evidence_glob="UCM-r023-SYSTEMIC-REPAIR-TIER1-EVIDENCE-*.zip")
    payload["KIT-MANIFEST.json"] = canonical(manifest) + b"\n"
    kit = out / "UCM-r023-SYSTEMIC-REPAIR-OPERATOR-KIT.zip"
    deterministic_zip(kit, payload)
    digest = sha(kit.read_bytes())
    ps1 = f'''$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$kit = Join-Path $here "UCM-r023-SYSTEMIC-REPAIR-OPERATOR-KIT.zip"
$expected = "{digest}"
$temp = Join-Path $env:TEMP ("UCM-r023-SYSTEMIC-REPAIR-" + [guid]::NewGuid().ToString("N"))
try {{
  Write-Host "UCM r023 systemic repair operator Tier 1 court"
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
    history.unlink()
    return {"status":"PASS","kit":str(kit),"kit_sha256":digest,
            "launcher":str(out/"RUN.cmd"),"operator_executed":False,
            "case_scope_count":18}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--runtime",type=Path,required=True)
    parser.add_argument("--qualification",type=Path,required=True)
    parser.add_argument("--cold-boot",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(build(args.runtime.resolve(),args.qualification.resolve(),
        args.cold_boot.resolve(),args.output.resolve()),sort_keys=True))
    return 0


if __name__=="__main__":raise SystemExit(main())

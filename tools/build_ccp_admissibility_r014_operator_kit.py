#!/usr/bin/env python3
"""Build, but never execute, the CCP admissibility r014 operator court."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
BOUNDARY = {
    "standing": "INFORMATION_ONLY",
    "authority_effect": "NONE",
    "real_a5": False,
    "g0": "CLOSED",
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def zip_bytes(payloads: dict[str, bytes]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for name, raw in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw)
    return out.getvalue()


def collect_subject() -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    roots = [ROOT / "src", ROOT / "program/ccp-admissibility-r014"]
    optional = [
        ROOT / "docs/CCP-ADMISSIBILITY.md",
        ROOT / "spec/CCP-ADMISSIBILITY-CONTRACT.json",
    ]
    required_files = [
        ROOT / "tools/build_ccp_native_program.py",
        ROOT / "qualification/inputs/ccp-jm/CCP_JM_PIPELINE_v0_1_r001.zip",
    ]
    for base in roots:
        if not base.is_dir():
            raise SystemExit(f"CCP_OPERATOR_REQUIRED_PATH_MISSING:{base.relative_to(ROOT).as_posix()}")
        for path in sorted(base.rglob("*")):
            if (not path.is_file() or "__pycache__" in path.parts
                    or path.suffix in {".pyc", ".pyo"}):
                continue
            members[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    for path in optional:
        if path.is_file():
            members[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    for path in required_files:
        if not path.is_file():
            raise SystemExit(
                f"CCP_OPERATOR_REQUIRED_FILE_MISSING:{path.relative_to(ROOT).as_posix()}")
        members[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    runner = ROOT / "operator-kits/ccp-admissibility-r014/RUN-TIER1.py"
    if not runner.is_file():
        raise SystemExit("CCP_OPERATOR_RUNNER_MISSING")
    members["RUN-TIER1.py"] = runner.read_bytes()
    return members


def powershell_runner(kit_hash: str) -> str:
    return rf"""$ErrorActionPreference='Stop'
$here=Split-Path -Parent $MyInvocation.MyCommand.Path
$kit=Join-Path $here 'KIT.zip'
$expected='{kit_hash}'
$tmp=Join-Path $env:TEMP ('UCM-CCP-ADMISSIBILITY-r014-'+[guid]::NewGuid().ToString('N'))
$courtCode=1
try{{
  Write-Host 'UCM CCP admissibility r014 operator Tier 1 court'
  Write-Host '================================================='
  if(-not (Test-Path -LiteralPath $kit)){{throw 'OPERATOR_KIT_MISSING'}}
  $actual=(Get-FileHash -Algorithm SHA256 -LiteralPath $kit).Hash.ToLowerInvariant()
  if($actual -ne $expected){{throw ('OPERATOR_KIT_HASH_MISMATCH:expected='+$expected+':actual='+$actual)}}
  Write-Host ('[1/7] Verified sealed operator kit: '+$actual)
  New-Item -ItemType Directory -Path $tmp|Out-Null
  Expand-Archive -LiteralPath $kit -DestinationPath $tmp
  Write-Host '[2/7] Extracted exact subject into a disposable workspace.'
  $candidates=@()
  $launcher=Get-Command py -ErrorAction SilentlyContinue
  if($launcher){{$candidates+=,@($launcher.Source,'-3.12');$candidates+=,@($launcher.Source,'-3.13')}}
  foreach($name in @('python3.13','python3.12','python')){{$cmd=Get-Command $name -ErrorAction SilentlyContinue;if($cmd){{$candidates+=,@($cmd.Source)}}}}
  $selected=$null
  foreach($candidate in $candidates){{
    $exe=$candidate[0];$prefix=@();if($candidate.Count -gt 1){{$prefix=$candidate[1..($candidate.Count-1)]}}
    & $exe @prefix -c "import sys,blake3,cryptography;sys.exit(0 if (3,12) <= sys.version_info[:2] < (3,14) else 1)" 2>$null
    if($LASTEXITCODE -eq 0){{$selected=$candidate;break}}
  }}
  if($null -eq $selected){{throw 'PYTHON_3_12_OR_3_13_WITH_BLAKE3_AND_CRYPTOGRAPHY_REQUIRED'}}
  $python=$selected[0];$prefix=@();if($selected.Count -gt 1){{$prefix=$selected[1..($selected.Count-1)]}}
  Write-Host ('[3/7] Runtime ready: '+$python+' '+($prefix -join ' '))
  $evidenceDir=Join-Path $tmp 'evidence'
  New-Item -ItemType Directory -Path $evidenceDir|Out-Null
  Write-Host '[4/7] Running custody checks and adversarial cases with live progress...'
  $env:PYTHONDONTWRITEBYTECODE='1'
  & $python @prefix (Join-Path $tmp 'RUN-TIER1.py') --subject $tmp --out $evidenceDir
  $courtCode=$LASTEXITCODE
  $evidence=Get-ChildItem -LiteralPath $evidenceDir -Filter '*EVIDENCE-*.zip'|Sort-Object Name|Select-Object -First 1
  if($null -eq $evidence){{throw 'TIER1_RUNNER_FAILED_WITHOUT_EVIDENCE'}}
  $destination=Join-Path $here $evidence.Name
  Copy-Item -LiteralPath $evidence.FullName -Destination $destination -Force
  $evidenceHash=(Get-FileHash -Algorithm SHA256 -LiteralPath $destination).Hash.ToLowerInvariant()
  Write-Host ('[5/7] Preserved evidence: '+$destination)
  Write-Host ('       SHA-256: '+$evidenceHash)
  if($courtCode -ne 0){{throw 'TIER1_HOLD_FOR_REPAIR'}}
  Write-Host '[6/7] Court status PASS.'
  Write-Host 'PASS - sealed operator evidence was written beside this command.'
}}finally{{
  if(Test-Path -LiteralPath $tmp){{Remove-Item -LiteralPath $tmp -Recurse -Force}}
  Write-Host '[7/7] Removed disposable review files.'
}}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Package the user-run CCP r014 Tier 1 court")
    parser.add_argument("--out", type=Path,
                        default=ROOT / "dist/UCM-CCP-ADMISSIBILITY-r014-OPERATOR-REVIEW-READY")
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        raise SystemExit(f"CCP_OPERATOR_OUTPUT_EXISTS:{out}")
    subject = collect_subject()
    runner_text = subject["RUN-TIER1.py"].decode("utf-8")
    compile(runner_text, "RUN-TIER1.py", "exec")
    source_rows = [
        {"path": name, "bytes": len(raw), "sha256": sha(raw)}
        for name, raw in sorted(subject.items())
    ]
    manifest_body = {
        "schema": "mosaic.ucm.ccp-admissibility-r014-operator-kit-manifest.v0.1",
        "files": source_rows,
        "file_count": len(source_rows),
        "case_families": [
            "INDEPENDENT_ANCHORS",
            "CHC_THR_NON_EQUIVALENCE",
            "SNAPSHOT_DECISION_CROSS_LINKS",
            "STALE_CURRENT_DISTINCTION",
            "PERIMETER_QUALIFICATION",
            "EVALUATION_BUDGET",
            "GATEWAY_BINDING",
            "PROJECTION_HONESTY",
            "SOURCE_DENOMINATOR_PRESERVATION",
        ],
        "tier1_executed": False,
        "builder_authored": True,
        "operator_executed": False,
        "independent_review": False,
        **BOUNDARY,
    }
    subject["KIT-MANIFEST.json"] = canonical({
        **manifest_body,
        "manifest_root": sha(canonical(manifest_body).rstrip(b"\n")),
    })
    first = zip_bytes(subject)
    second = zip_bytes(subject)
    if first != second:
        raise SystemExit("CCP_OPERATOR_KIT_NONDETERMINISTIC")
    kit_hash = sha(first)
    out.mkdir(parents=True)
    (out / "KIT.zip").write_bytes(first)
    (out / "KIT.sha256").write_text(kit_hash + "\n", encoding="utf-8", newline="\n")
    (out / "RUN.ps1").write_text(powershell_runner(kit_hash), encoding="utf-8", newline="\n")
    (out / "RUN-UCM-CCP-ADMISSIBILITY-r014-TIER1.cmd").write_text(
        '@echo off\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN.ps1"\r\n'
        'if errorlevel 1 echo HOLD_FOR_REPAIR\r\npause\r\n',
        encoding="ascii", newline="")
    (out / "START-HERE.md").write_text(
        "# UCM CCP admissibility r014 operator review\n\n"
        "Double-click `RUN-UCM-CCP-ADMISSIBILITY-r014-TIER1.cmd` on Windows. The launcher "
        "verifies the exact sealed kit hash, extracts it into a disposable workspace, selects "
        "Python 3.12 or 3.13 with blake3 and cryptography, prints live per-case progress, preserves one sealed evidence ZIP "
        "beside the command even when a case fails, removes temporary files, and pauses.\n\n"
        "The builder packaged and syntax-checked this court but did not execute it. Its result is "
        "operator-reproduced builder-authored evidence, not an independent verdict. It remains "
        "INFORMATION_ONLY with authority effect NONE, real A5 false, and G0 closed.\n",
        encoding="utf-8", newline="\n")
    outer_members = {path.name: path.read_bytes() for path in out.iterdir() if path.is_file()}
    portable = zip_bytes({f"{out.name}/{name}": raw for name, raw in outer_members.items()})
    portable_path = out.parent / f"{out.name}.zip"
    portable_path.write_bytes(portable)
    print(json.dumps({
        "status": "PASS",
        "tier1_executed": False,
        "kit_sha256": kit_hash,
        "kit_members": len(subject),
        "portable_zip": str(portable_path),
        "portable_zip_sha256": sha(portable),
        **BOUNDARY,
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

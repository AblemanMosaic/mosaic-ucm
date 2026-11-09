#!/usr/bin/env python3
"""Build, but never execute, the P/PPI r010 operator Tier 1 kit."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def zip_bytes(payloads: dict[str, bytes]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name in sorted(payloads):
            info = zipfile.ZipInfo(name, FIXED_TIME); info.create_system = 3
            info.external_attr = 0o100644 << 16; info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, payloads[name])
    return out.getvalue()


def runner(kit_hash: str, runtime_hash: str) -> str:
    return rf"""$ErrorActionPreference='Stop'
$here=Split-Path -Parent $MyInvocation.MyCommand.Path
$kit=Join-Path $here 'KIT.zip';$expected='{kit_hash}';$runtimeExpected='{runtime_hash}'
$tmp=Join-Path $env:TEMP ('UCM-PIPPI-r010-'+[guid]::NewGuid().ToString('N'))
try{{
 Write-Host 'UCM P/PPI r010 operator Tier 1 court'
 Write-Host '===================================='
 if((Get-FileHash -Algorithm SHA256 -LiteralPath $kit).Hash.ToLowerInvariant() -ne $expected){{throw 'OPERATOR_KIT_HASH_MISMATCH'}}
 Write-Host '[1/7] Verified sealed operator kit.'
 New-Item -ItemType Directory -Path $tmp|Out-Null;Expand-Archive -LiteralPath $kit -DestinationPath $tmp
 if((Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $tmp 'UCM-v0.1-runtime.zip')).Hash.ToLowerInvariant() -ne $runtimeExpected){{throw 'RUNTIME_ARCHIVE_HASH_MISMATCH'}}
 $runtime=Join-Path $tmp 'runtime';Expand-Archive -LiteralPath (Join-Path $tmp 'UCM-v0.1-runtime.zip') -DestinationPath $runtime
 Write-Host '[2/7] Extracted exact runtime into a disposable workspace.'
 $candidates=@();$py=Get-Command py -ErrorAction SilentlyContinue
 if($py){{$candidates+=,@($py.Source,'-3.12');$candidates+=,@($py.Source,'-3.13')}}
 foreach($name in @('python3.13','python3.12','python')){{$cmd=Get-Command $name -ErrorAction SilentlyContinue;if($cmd){{$candidates+=,@($cmd.Source)}}}}
 $selected=$null
 foreach($candidate in $candidates){{$exe=$candidate[0];$prefix=@();if($candidate.Count -gt 1){{$prefix=$candidate[1..($candidate.Count-1)]}};& $exe @prefix -c "import cryptography;print('READY')" 2>$null|Out-Null;if($LASTEXITCODE -eq 0){{$selected=$candidate;break}}}}
 if($null -eq $selected){{throw 'PYTHON_3_12_OR_3_13_WITH_CRYPTOGRAPHY_REQUIRED'}}
 $python=$selected[0];$prefix=@();if($selected.Count -gt 1){{$prefix=$selected[1..($selected.Count-1)]}}
 Write-Host ('[3/7] Runtime ready: '+$python+' '+($prefix -join ' '))
 Write-Host '[4/7] Running positive Windows install/service/dashboard/uninstall smoke...'
 & $python @prefix (Join-Path $runtime 'tools\run_pippi_windows_smoke.py') $runtime --work (Join-Path $tmp 'smoke-work') --output (Join-Path $tmp 'smoke-evidence')
 if($LASTEXITCODE -ne 0){{throw 'WINDOWS_POSITIVE_SMOKE_HOLD'}}
 Write-Host '[5/7] Running adversarial cases with live progress...'
 $evidence=Join-Path $tmp 'evidence';New-Item -ItemType Directory -Path $evidence|Out-Null
 & $python @prefix (Join-Path $tmp 'RUN-TIER1.py') --runtime $runtime --runtime-archive (Join-Path $tmp 'UCM-v0.1-runtime.zip') --qualification (Join-Path $tmp 'UCM-v0.1-QUALIFICATION.json') --out $evidence
 $courtCode=$LASTEXITCODE;$zip=Get-ChildItem -LiteralPath $evidence -Filter '*EVIDENCE-*.zip'|Select-Object -First 1
 if($null -eq $zip){{throw 'TIER1_EVIDENCE_MISSING'}}
 Copy-Item -LiteralPath $zip.FullName -Destination (Join-Path $here $zip.Name) -Force
 Copy-Item -LiteralPath (Join-Path $tmp 'smoke-evidence\PIPPI-WINDOWS-SMOKE.json') -Destination (Join-Path $here 'PIPPI-WINDOWS-SMOKE.json') -Force
 Write-Host '[6/7] Preserved sealed evidence beside this command.'
 if($courtCode -ne 0){{throw 'TIER1_HOLD_FOR_REPAIR'}}
 Write-Host 'PASS - operator evidence is ready for return.'
}}finally{{
 if(Test-Path -LiteralPath $tmp){{Remove-Item -LiteralPath $tmp -Recurse -Force}}
 Write-Host '[7/7] Removed disposable review files.'
}}
"""


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--runtime", type=Path, required=True)
    p.add_argument("--qualification", type=Path, required=True); p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(); out = a.out.resolve()
    if out.exists(): raise SystemExit("PIPPI_R010_OPERATOR_OUTPUT_EXISTS")
    run_path = ROOT / "operator-kits/pippi-r010/RUN-TIER1.py"
    compile(run_path.read_text(encoding="utf-8"), str(run_path), "exec")
    runtime = a.runtime.read_bytes(); qualification = a.qualification.read_bytes()
    manifest = {"schema": "mosaic.ucm.pippi-r010-operator-kit.v0.1",
        "runtime_sha256": sha(runtime), "qualification_sha256": sha(qualification),
        "runner_sha256": sha(run_path.read_bytes()), "tier1_executed": False,
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE", "real_a5": False, "g0": "CLOSED"}
    payloads = {"UCM-v0.1-runtime.zip": runtime, "UCM-v0.1-QUALIFICATION.json": qualification,
                "RUN-TIER1.py": run_path.read_bytes(),
                "KIT-MANIFEST.json": json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode() + b"\n"}
    kit = zip_bytes(payloads); kit_hash = sha(kit); out.mkdir(parents=True)
    (out / "KIT.zip").write_bytes(kit); (out / "KIT.sha256").write_text(kit_hash + "\n", encoding="utf-8")
    (out / "RUN.ps1").write_text(runner(kit_hash, sha(runtime)), encoding="utf-8")
    (out / "RUN-UCM-PIPPI-r010-TIER1.cmd").write_text(
        '@echo off\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN.ps1"\r\n'
        'if errorlevel 1 echo HOLD_FOR_REPAIR\r\npause\r\n', encoding="utf-8")
    (out / "START-HERE.md").write_text(
        "# P/PPI r010 operator review\n\nDouble-click `RUN-UCM-PIPPI-r010-TIER1.cmd`. "
        "It verifies and extracts exact bytes, runs the positive Windows install/service/dashboard/uninstall "
        "smoke, runs the builder-authored adversarial court with live progress, seals evidence beside the "
        "command, removes temporary files, and pauses. This is operator-reproduced evidence, not an independent verdict.\n",
        encoding="utf-8")
    outer_members = {x.name: x.read_bytes() for x in out.iterdir() if x.is_file()}
    portable = zip_bytes({f"{out.name}/{name}": raw for name, raw in outer_members.items()})
    portable_path = out.parent / f"{out.name}.zip"; portable_path.write_bytes(portable)
    print(json.dumps({"status": "PASS", "tier1_executed": False, "kit_sha256": kit_hash,
        "portable_zip": str(portable_path), "portable_zip_sha256": sha(portable)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROGRAM = ROOT / "dist" / "UCM-PIPPI-PROCESS-GOVERNANCE-C1-DOGFOOD"
DEFAULT_OUT = ROOT / "dist" / "UCM-PIPPI-PROCESS-GOVERNANCE-C1-OPERATOR-REVIEW-READY"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def zip_bytes(payloads: dict[str, bytes], *, compressed: bool = True) -> bytes:
    output = io.BytesIO()
    compression = zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED
    with zipfile.ZipFile(output, "w", compression=compression, compresslevel=9) as archive:
        for name in sorted(payloads):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = compression
            archive.writestr(info, payloads[name])
    return output.getvalue()


def collect_subject(program: Path) -> dict[str, bytes]:
    required = {"INDEX.json", "PROCESS-BASELINE.json", "EXACT-EXECUTION-CAPSULE.json",
                "QUALIFICATION-PRODUCER-RECEIPT.json"}
    present = {path.name for path in program.iterdir() if path.is_file()}
    missing = sorted(required - present)
    if missing:
        raise SystemExit(f"PROCESS_OPERATOR_PROGRAM_INCOMPLETE:{','.join(missing)}")
    members: dict[str, bytes] = {}
    for package in (ROOT / "src").iterdir():
        if not package.is_dir():
            continue
        for path in sorted(package.rglob("*")):
            if (path.is_file() and "__pycache__" not in path.parts
                    and path.suffix not in {".pyc", ".pyo"}):
                members[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    for path in sorted(program.rglob("*")):
        if path.is_file() and path.suffix != ".zip":
            members[(Path("program") / path.relative_to(program)).as_posix()] = path.read_bytes()
    members["RUN-TIER1.py"] = (
        ROOT / "operator-kits/process-governance-c1/RUN-TIER1.py").read_bytes()
    return members


def powershell_runner(kit_hash: str) -> str:
    return f"""$ErrorActionPreference='Stop'
$here=Split-Path -Parent $MyInvocation.MyCommand.Path
$kit=Join-Path $here 'KIT.zip'
$expected='{kit_hash}'
$tmp=Join-Path $env:TEMP ('UCM-PIPPI-PROCESS-C1-'+[guid]::NewGuid().ToString('N'))
try{{
  Write-Host 'UCM P/PPI process-governance C1 operator Tier 1 court'
  Write-Host '========================================================'
  $actual=(Get-FileHash -Algorithm SHA256 -LiteralPath $kit).Hash.ToLowerInvariant()
  if($actual -ne $expected){{throw 'OPERATOR_KIT_HASH_MISMATCH'}}
  Write-Host '[1/6] Verified sealed operator kit.'
  New-Item -ItemType Directory -Path $tmp|Out-Null
  Expand-Archive -LiteralPath $kit -DestinationPath $tmp
  Write-Host '[2/6] Extracted exact subject into a disposable workspace.'
  $candidates=@()
  $launcher=Get-Command py -ErrorAction SilentlyContinue
  if($launcher){{$candidates+=,@($launcher.Source,'-3.12');$candidates+=,@($launcher.Source,'-3.13')}}
  foreach($name in @('python3.13','python3.12','python')){{$cmd=Get-Command $name -ErrorAction SilentlyContinue;if($cmd){{$candidates+=,@($cmd.Source)}}}}
  $selected=$null
  foreach($candidate in $candidates){{
    $exe=$candidate[0];$prefix=@();if($candidate.Count -gt 1){{$prefix=$candidate[1..($candidate.Count-1)]}}
    & $exe @prefix -c "import blake3,cryptography;print('READY')" 2>$null | Out-Null
    if($LASTEXITCODE -eq 0){{$selected=$candidate;break}}
  }}
  if($null -eq $selected){{throw 'PYTHON_3_12_OR_3_13_WITH_BLAKE3_AND_CRYPTOGRAPHY_REQUIRED'}}
  $python=$selected[0];$pythonPrefix=@();if($selected.Count -gt 1){{$pythonPrefix=$selected[1..($selected.Count-1)]}}
  Write-Host ('[3/6] Runtime ready: '+$python+' '+($pythonPrefix -join ' '))
  $evidenceDir=Join-Path $tmp 'evidence'
  New-Item -ItemType Directory -Path $evidenceDir|Out-Null
  Write-Host '[4/6] Running custody checks and adversarial cases with live progress...'
  & $python @pythonPrefix (Join-Path $tmp 'RUN-TIER1.py') --subject $tmp --out $evidenceDir
  $courtCode=$LASTEXITCODE
  $evidence=Get-ChildItem -LiteralPath $evidenceDir -Filter '*EVIDENCE-*.zip'|Select-Object -First 1
  if($null -eq $evidence){{throw 'TIER1_EVIDENCE_MISSING'}}
  $destination=Join-Path $here $evidence.Name
  Copy-Item -LiteralPath $evidence.FullName -Destination $destination -Force
  $evidenceHash=(Get-FileHash -Algorithm SHA256 -LiteralPath $destination).Hash.ToLowerInvariant()
  Write-Host ('[5/6] Preserved evidence: '+$destination)
  Write-Host ('       SHA-256: '+$evidenceHash)
  if($courtCode -ne 0){{throw 'TIER1_HOLD_FOR_REPAIR'}}
  Write-Host 'PASS - sealed operator evidence was written beside this command.'
}}finally{{
  if(Test-Path -LiteralPath $tmp){{Remove-Item -LiteralPath $tmp -Recurse -Force}}
  Write-Host '[6/6] Removed disposable review files.'
}}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program", type=Path, default=DEFAULT_PROGRAM)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    program = args.program.resolve()
    out = args.out.resolve()
    if out.exists():
        raise SystemExit(f"PROCESS_OPERATOR_OUTPUT_EXISTS:{out}")
    subject = collect_subject(program)
    manifest_body = {
        "schema": "mosaic.ucm.process-governance-operator-kit-manifest.v0.1",
        "files": [{"path": name, "sha256": sha(raw), "bytes": len(raw)}
                  for name, raw in sorted(subject.items())],
        "file_count": len(subject),
        "operator_authored": True,
        "independent_review": False,
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        "real_a5": False, "g0": "CLOSED",
    }
    subject["MANIFEST.json"] = (json.dumps(manifest_body, sort_keys=True,
                                             separators=(",", ":")) + "\n").encode()
    kit = zip_bytes(subject)
    # Packaging preflight only: imports exact extracted code; it does not run Tier 1.
    import tempfile
    with tempfile.TemporaryDirectory(prefix="ucm-process-kit-preflight-") as raw:
        extracted = Path(raw)
        with zipfile.ZipFile(io.BytesIO(kit)) as archive:
            archive.extractall(extracted)
        probe = ("import sys;sys.path.insert(0," + repr(str(extracted / "src"))
                 + ");import ucm.process_governance;print('PROCESS_KIT_IMPORT_PASS')")
        completed = subprocess.run([sys.executable, "-I", "-c", probe], cwd=extracted,
                                   capture_output=True, text=True, check=False)
        if completed.returncode != 0 or "PROCESS_KIT_IMPORT_PASS" not in completed.stdout:
            raise SystemExit("PROCESS_OPERATOR_IMPORT_PREFLIGHT_FAILED:"
                             + (completed.stderr or completed.stdout).strip())
    out.mkdir(parents=True)
    (out / "KIT.zip").write_bytes(kit)
    kit_hash = sha(kit)
    (out / "KIT.sha256").write_text(kit_hash + "\n", encoding="utf-8")
    (out / "RUN.ps1").write_text(powershell_runner(kit_hash), encoding="utf-8")
    (out / "RUN-UCM-PIPPI-PROCESS-GOVERNANCE-C1-TIER1.cmd").write_text(
        '@echo off\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN.ps1"\r\n'
        'if errorlevel 1 echo HOLD_FOR_REPAIR\r\npause\r\n', encoding="utf-8")
    (out / "START-HERE.md").write_text(
        "# P/PPI process-governance C1 operator review\n\n"
        "Double-click `RUN-UCM-PIPPI-PROCESS-GOVERNANCE-C1-TIER1.cmd`. The launcher "
        "verifies the sealed kit, uses an available Python 3.12 or 3.13 with blake3 and "
        "cryptography, runs the court with live per-case progress, preserves the evidence "
        "ZIP beside the command, removes disposable files and pauses. The result is "
        "operator-reproduced, builder-authored evidence; it is not an independent verdict.\n",
        encoding="utf-8")
    outer_members = {path.name: path.read_bytes() for path in out.iterdir() if path.is_file()}
    outer = zip_bytes({f"{out.name}/{name}": raw for name, raw in outer_members.items()})
    outer_path = out.parent / f"{out.name}.zip"
    outer_path.write_bytes(outer)
    print(json.dumps({"status": "PASS", "kit_sha256": kit_hash,
                      "kit_members": len(subject), "out": str(out),
                      "portable_zip": str(outer_path),
                      "portable_zip_sha256": sha(outer),
                      "tier1_executed": False}, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

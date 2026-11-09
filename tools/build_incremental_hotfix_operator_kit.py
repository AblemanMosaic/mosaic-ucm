from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "UCM-INCREMENTAL-HOTFIX-C1-OPERATOR-REVIEW-READY"
PACKAGE_ROOTS = (ROOT / "src" / "ucm", ROOT / "src" / "uclop", ROOT / "src" / "uclsh")
FIXED_FILES = ("spec/INCREMENTAL-HOTFIX-CONTRACT.json", "operator/incremental-hotfix-c1/RUN-TIER1.py")

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _collect_members() -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    for package_root in PACKAGE_ROOTS:
        for path in sorted(package_root.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
                continue
            members[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    for relative in FIXED_FILES:
        target_name = "RUN-TIER1.py" if relative.endswith("RUN-TIER1.py") else relative
        members[target_name] = (ROOT / relative).read_bytes()
    return members

def _write_zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, members[name])

def _verify_fresh_extraction(kit: Path, expected_members: dict[str, bytes]) -> None:
    """Refuse to seal a kit whose exact extraction cannot import its runtime."""
    with tempfile.TemporaryDirectory(prefix="ucm-hotfix-kit-preflight-") as raw:
        extracted = Path(raw)
        with zipfile.ZipFile(kit) as archive:
            archive.extractall(extracted)
        for name, expected in expected_members.items():
            actual_path = extracted / Path(name)
            if not actual_path.is_file() or actual_path.read_bytes() != expected:
                raise RuntimeError(f"OPERATOR_KIT_MEMBER_MISMATCH:{name}")
        import_probe = (
            "import sys;"
            f"sys.path.insert(0,{str(extracted / 'src')!r});"
            "import ucm.correction_transaction;"
            "import ucm.incremental_hotfix;"
            "print('OPERATOR_KIT_IMPORT_PASS')"
        )
        completed = subprocess.run(
            [sys.executable, "-I", "-c", import_probe],
            cwd=extracted,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0 or "OPERATOR_KIT_IMPORT_PASS" not in completed.stdout:
            diagnostic = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(f"OPERATOR_KIT_IMPORT_FAILED:{diagnostic}")

def _powershell_runner(kit_hash: str) -> str:
    return f"""$ErrorActionPreference='Stop'
$here=Split-Path -Parent $MyInvocation.MyCommand.Path
$kit=Join-Path $here 'KIT.zip'
$expected='{kit_hash}'
$actual=(Get-FileHash -Algorithm SHA256 -LiteralPath $kit).Hash.ToLowerInvariant()
if($actual -ne $expected){{throw 'operator kit hash mismatch'}}
$tmp=Join-Path $env:TEMP ('UCM-HOTFIX-C1-'+[guid]::NewGuid().ToString('N'))
try{{
  Write-Host '[1/5] Verified sealed operator kit.'
  New-Item -ItemType Directory -Path $tmp|Out-Null
  Expand-Archive -LiteralPath $kit -DestinationPath $tmp
  Write-Host '[2/5] Extracted disposable review workspace.'
  $py=Get-Command py -ErrorAction SilentlyContinue
  if($py){{& $py.Source -3.12 (Join-Path $tmp 'RUN-TIER1.py') --subject $tmp --out $tmp}}
  else{{& python (Join-Path $tmp 'RUN-TIER1.py') --subject $tmp --out $tmp}}
  $code=$LASTEXITCODE
  Write-Host '[3/5] Court completed; preserving sealed evidence.'
  Get-ChildItem $tmp -Filter '*EVIDENCE.zip'|Copy-Item -Destination $here -Force
  if($code -ne 0){{throw 'Tier 1 HOLD_FOR_REPAIR'}}
  Write-Host '[4/5] PASS - sealed evidence written beside this command.'
}}finally{{
  if(Test-Path $tmp){{Remove-Item -LiteralPath $tmp -Recurse -Force}}
  Write-Host '[5/5] Disposable review files removed.'
}}
"""

def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    members = _collect_members()
    manifest = {
        "schema": "mosaic.ucm.incremental-hotfix-operator-kit.v0.1",
        "files": [{"path": name, "sha256": _sha256(data), "bytes": len(data)} for name, data in sorted(members.items())],
        "runtime_preflight": "FRESH_EXTRACTION_IMPORT_REQUIRED",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
        "real_a5": False,
        "g0": "CLOSED",
    }
    members["MANIFEST.json"] = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    kit = OUT / "KIT.zip"
    _write_zip(kit, members)
    _verify_fresh_extraction(kit, members)
    kit_hash = _sha256(kit.read_bytes())
    (OUT / "KIT.sha256").write_text(kit_hash + "\n", encoding="utf-8")
    (OUT / "RUN.ps1").write_text(_powershell_runner(kit_hash), encoding="utf-8")
    (OUT / "RUN-INCREMENTAL-HOTFIX-TIER1.cmd").write_text(
        '@echo off\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN.ps1"\r\n'
        'if errorlevel 1 echo HOLD_FOR_REPAIR\r\npause\r\n',
        encoding="utf-8",
    )
    (OUT / "START-HERE.md").write_text(
        "# Incremental hotfix Tier 1\n\n"
        "Double-click RUN-INCREMENTAL-HOTFIX-TIER1.cmd. The sealed kit has already passed a fresh-extraction runtime-import preflight. The command verifies the kit, runs nine cases in a disposable directory, preserves evidence, removes temporary files, and pauses. This is operator-run builder-authored evidence, not independent review.\n",
        encoding="utf-8",
    )
    print(json.dumps({"status":"PASS","runtime_preflight":"PASS","members":len(members),"kit_sha256":kit_hash,"out":str(OUT)}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())


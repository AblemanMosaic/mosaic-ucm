from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root
from ucm.amcas import BOUNDARY
from ucm.artifacts import deterministic_zip, verify_deterministic_zip

SCHEMA = "mosaic.ucm.amcas-parity-tier1-operator-kit.v0.1"
ROLE = "UCM_AMCAS_PARITY_TIER1_OPERATOR_KIT"


def build(out_dir: Path) -> dict:
    release_path = ROOT / "dist/UCM-AMCAS-BASELINE-PARITY-PROGRAM-C1.zip"
    release = release_path.read_bytes()
    payloads = {
        "RUN-TIER1.py": (ROOT / "operator-kits/amcas-parity-c1/RUN-TIER1.py").read_bytes(),
        "subject/UCM-AMCAS-BASELINE-PARITY-PROGRAM-C1.zip": release,
        "subject/examples/amcas/portable-agent.integration.json":
            (ROOT / "examples/amcas/portable-agent.integration.json").read_bytes(),
        "README.md": ("# AMCAS–UCM baseline and parity C1 operator review\n\n"
            "Double-click the adjacent RUN-UCM-AMCAS-PARITY-C1-TIER1.cmd. The command verifies "
            "this archive, uses a disposable workspace, prints live case progress, writes sealed "
            "evidence beside itself, removes temporary files, and pauses.\n\n"
            "The builder packaged but did not execute this adversarial court. INFORMATION_ONLY; "
            "authority effect NONE; real A5 false; G0 closed.\n").encode("utf-8"),
    }
    rows = []
    for base in (ROOT / "src", ROOT / "integration/stage-i3/authoring/plans"):
        for path in sorted(base.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
                continue
            relative = path.relative_to(ROOT).as_posix()
            raw = path.read_bytes()
            payloads[f"subject/{relative}"] = raw
            rows.append({"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    rows.sort(key=lambda row: row["path"])
    body = {"schema": "mosaic.ucm.amcas-parity-tier1-subject.v0.1",
        "release_sha256": hashlib.sha256(release).hexdigest(),
        "source_files": rows, "source_manifest_root": root(rows), **BOUNDARY}
    payloads["SUBJECT.json"] = canonical_bytes({**body, "subject_root": root(body)})
    first = deterministic_zip(payloads, schema=SCHEMA, artifact_role=ROLE)
    second = deterministic_zip(payloads, schema=SCHEMA, artifact_role=ROLE)
    if first != second:
        raise RuntimeError("AMCAS_PARITY_OPERATOR_KIT_NONDETERMINISTIC")
    verify_deterministic_zip(first, expected_schema=SCHEMA, expected_role=ROLE)
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / "UCM-AMCAS-PARITY-C1-TIER1-OPERATOR-KIT.zip"
    archive.write_bytes(first)
    digest = hashlib.sha256(first).hexdigest()
    cmd = f'''@echo off
setlocal EnableExtensions
set "KIT=%~dp0UCM-AMCAS-PARITY-C1-TIER1-OPERATOR-KIT.zip"
set "EXPECTED={digest}"
set "WORK=%TEMP%\\UCM-AMCAS-PARITY-C1-%RANDOM%-%RANDOM%"
set "EXITCODE=1"
echo UCM AMCAS baseline and parity C1 operator Tier 1 court
echo ============================================================
if not exist "%KIT%" (
  echo ERROR: operator kit not found beside this command.
  goto cleanup
)
echo [1/6] Verifying the sealed operator kit...
set "UCM_OPERATOR_KIT=%KIT%"
set "UCM_OPERATOR_EXPECTED=%EXPECTED%"
powershell -NoProfile -Command "$actual=(Get-FileHash -LiteralPath $env:UCM_OPERATOR_KIT -Algorithm SHA256).Hash.ToLowerInvariant(); if($actual -ne $env:UCM_OPERATOR_EXPECTED){{ Write-Host ('ERROR: operator kit hash mismatch. expected=' + $env:UCM_OPERATOR_EXPECTED + ' actual=' + $actual); exit 2 }}; Write-Host ('  Verified SHA-256 ' + $actual)"
if errorlevel 1 goto cleanup
echo [2/6] Creating a disposable review workspace...
mkdir "%WORK%" >nul 2>nul
set "UCM_OPERATOR_WORK=%WORK%"
powershell -NoProfile -Command "Expand-Archive -LiteralPath $env:UCM_OPERATOR_KIT -DestinationPath $env:UCM_OPERATOR_WORK -Force"
if errorlevel 1 goto cleanup
set "PYTHON="
where py >nul 2>nul
if not errorlevel 1 (
  py -3.12 -c "import sys; print(sys.version)" >nul 2>nul
  if not errorlevel 1 set "PYTHON=py -3.12"
)
if not defined PYTHON (
  where python >nul 2>nul
  if not errorlevel 1 set "PYTHON=python"
)
if not defined PYTHON (
  echo ERROR: Python 3.12 or compatible Python was not found.
  goto cleanup
)
echo [3/6] Running custody checks and adversarial cases with live progress...
set PYTHONDONTWRITEBYTECODE=1
%PYTHON% "%WORK%\\RUN-TIER1.py" --kit-root "%WORK%" --out-dir "%~dp0."
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" goto cleanup
echo [4/6] Evidence sealed beside this command.
echo [5/6] Court status PASS.
:cleanup
echo [6/6] Removing disposable review files...
if exist "%WORK%" rmdir /s /q "%WORK%"
if "%EXITCODE%"=="0" (
  echo.
  echo PASS - sealed Tier 1 evidence was written beside this command.
) else (
  echo.
  echo HOLD_FOR_REPAIR - inspect the diagnostic and preserved evidence above.
)
echo.
pause
exit /b %EXITCODE%
'''
    command = out_dir / "RUN-UCM-AMCAS-PARITY-C1-TIER1.cmd"
    command.write_text(cmd, encoding="ascii", newline="\r\n")
    return {"status": "PASS", "archive": str(archive), "archive_sha256": digest,
        "command": str(command), "cases_packaged_not_executed": True, **BOUNDARY}


def main() -> int:
    parser = argparse.ArgumentParser(description="Package operator-run AMCAS parity Tier 1 court")
    parser.add_argument("--out-dir", type=Path,
        default=ROOT / "dist/UCM-AMCAS-PARITY-C1-OPERATOR-REVIEW")
    args = parser.parse_args()
    import json
    print(json.dumps(build(args.out_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

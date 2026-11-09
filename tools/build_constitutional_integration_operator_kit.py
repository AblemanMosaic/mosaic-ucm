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

SCHEMA = "mosaic.ucm.constitutional-integration-tier1-operator-kit.v0.1"
ROLE = "UCM_CONSTITUTIONAL_INTEGRATION_TIER1_OPERATOR_KIT"


def build(out_dir: Path) -> dict:
    release = ROOT / "dist/UCM-APPLICATION-CONSTITUTIONALIZATION-KIT-C1.zip"
    release_raw = release.read_bytes()
    source_rows = []
    payloads = {
        "RUN-TIER1.py": (ROOT / "operator-kits/constitutional-integration-c1/RUN-TIER1.py").read_bytes(),
        "subject/UCM-APPLICATION-CONSTITUTIONALIZATION-KIT-C1.zip": release_raw,
    }
    for path in sorted((ROOT / "src").rglob("*.py")):
        relative = path.relative_to(ROOT).as_posix()
        raw = path.read_bytes()
        payloads[f"subject/{relative}"] = raw
        source_rows.append({"path": relative, "bytes": len(raw),
                            "sha256": hashlib.sha256(raw).hexdigest()})
    subject_body = {"schema": "mosaic.ucm.constitutional-integration-tier1-subject.v0.1",
                    "release_sha256": hashlib.sha256(release_raw).hexdigest(),
                    "source_files": source_rows, "source_manifest_root": root(source_rows),
                    **BOUNDARY}
    payloads["SUBJECT.json"] = canonical_bytes({**subject_body, "subject_root": root(subject_body)})
    payloads["README.md"] = ("# UCM Constitutional Integration C1 operator review\n\n"
        "Double-click the adjacent RUN-UCM-CONSTITUTIONAL-INTEGRATION-C1-TIER1.cmd. "
        "The command verifies this archive, extracts into a disposable directory, prints live case "
        "progress, writes sealed evidence beside the command, removes temporary files, and pauses.\n\n"
        "The operator court is adversarial. It was packaged but not executed by the builder. "
        "INFORMATION_ONLY; authority effect NONE; real A5 false; G0 closed.\n").encode("utf-8")
    raw = deterministic_zip(payloads, schema=SCHEMA, artifact_role=ROLE)
    verify_deterministic_zip(raw, expected_schema=SCHEMA, expected_role=ROLE)
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / "UCM-CONSTITUTIONAL-INTEGRATION-C1-TIER1-OPERATOR-KIT.zip"
    archive.write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    command = f'''@echo off
setlocal EnableExtensions
set "KIT=%~dp0UCM-CONSTITUTIONAL-INTEGRATION-C1-TIER1-OPERATOR-KIT.zip"
set "EXPECTED={sha}"
set "WORK=%TEMP%\\UCM-CONSTITUTIONAL-INTEGRATION-C1-%RANDOM%-%RANDOM%"
set "EXITCODE=1"
echo UCM Constitutional Integration C1 operator Tier 1 court
echo ============================================================
if not exist "%KIT%" (
  echo ERROR: operator kit not found beside this command.
  goto cleanup
)
echo [1/6] Verifying the sealed operator kit...
for /f "tokens=*" %%H in ('powershell -NoProfile -Command "(Get-FileHash -LiteralPath ''%KIT%'' -Algorithm SHA256).Hash.ToLowerInvariant()"') do set "ACTUAL=%%H"
if /I not "%ACTUAL%"=="%EXPECTED%" (
  echo ERROR: operator kit hash mismatch.
  goto cleanup
)
echo [2/6] Creating a disposable review workspace...
mkdir "%WORK%" >nul 2>nul
powershell -NoProfile -Command "Expand-Archive -LiteralPath ''%KIT%'' -DestinationPath ''%WORK%'' -Force"
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
%PYTHON% "%WORK%\\RUN-TIER1.py" --kit-root "%WORK%" --out-dir "%~dp0"
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
    cmd = out_dir / "RUN-UCM-CONSTITUTIONAL-INTEGRATION-C1-TIER1.cmd"
    cmd.write_text(command, encoding="ascii", newline="\r\n")
    return {"status": "PASS", "archive": str(archive), "archive_sha256": sha,
            "command": str(cmd), "cases_packaged_not_executed": True, **BOUNDARY}


def main():
    parser = argparse.ArgumentParser(description="Package the operator-run integration Tier 1 court")
    parser.add_argument("--out-dir", type=Path,
        default=ROOT / "dist/UCM-CONSTITUTIONAL-INTEGRATION-C1-OPERATOR-REVIEW")
    args = parser.parse_args()
    import json
    print(json.dumps(build(args.out_dir), sort_keys=True))


if __name__ == "__main__":
    main()
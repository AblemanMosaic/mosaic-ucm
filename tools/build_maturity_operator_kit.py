"""Build the sealed, user-run UCM maturity Tier 1 operator delivery."""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))

from ucm.artifacts import deterministic_zip, verify_deterministic_zip


SCHEMA = "mosaic.ucm.maturity-tier1-operator-kit.v0.2"
ROLE = "UCM_MATURITY_TIER1_OPERATOR_KIT"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _defined_names(raw: bytes, module: str) -> set[str]:
    try:
        tree = ast.parse(raw, filename=module)
    except (SyntaxError, UnicodeDecodeError) as error:
        raise SystemExit(f"MATURITY_OPERATOR_SUBJECT_MODULE_INVALID:{module}") from error
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update(alias.asname or alias.name.split(".")[0]
                         for alias in node.names if alias.name != "*")
    return names


def build_runner_import_contract(subject: bytes, runner: bytes) -> dict:
    """Bind every subject-owned runner import to a name in the frozen source.

    This is a static packaging check. It neither imports subject code nor runs the
    operator court, and it catches API drift before a user launches the kit.
    """
    try:
        runner_tree = ast.parse(runner, filename="RUN-MATURITY-TIER1.py")
        with zipfile.ZipFile(io.BytesIO(subject)) as archive:
            members = {info.filename: archive.read(info) for info in archive.infolist()
                       if not info.is_dir()}
    except (SyntaxError, zipfile.BadZipFile, OSError, ValueError) as error:
        raise SystemExit("MATURITY_OPERATOR_IMPORT_CONTRACT_INPUT_INVALID") from error
    imports: dict[str, set[str]] = {}
    for node in ast.walk(runner_tree):
        if not isinstance(node, ast.ImportFrom) or node.level != 0 or not node.module:
            continue
        if node.module.split(".", 1)[0] not in {"ucm", "uclop"}:
            continue
        names = {alias.name for alias in node.names}
        if "*" in names:
            raise SystemExit(f"MATURITY_OPERATOR_STAR_IMPORT_FORBIDDEN:{node.module}")
        imports.setdefault(node.module, set()).update(names)
    rows = []
    for module, names in sorted(imports.items()):
        stem = module.replace(".", "/")
        candidates = (f"src/{stem}.py", f"src/{stem}/__init__.py")
        path = next((candidate for candidate in candidates if candidate in members), None)
        if path is None:
            raise SystemExit(f"MATURITY_OPERATOR_SUBJECT_MODULE_MISSING:{module}")
        exports = _defined_names(members[path], module)
        missing = sorted(names - exports)
        if missing:
            raise SystemExit(
                f"MATURITY_OPERATOR_RUNNER_IMPORT_MISMATCH:{module}:{','.join(missing)}")
        rows.append({"module": module, "module_path": path,
                     "module_sha256": sha(members[path]),
                     "import_names": sorted(names)})
    body = {"schema": "mosaic.ucm.maturity-operator-import-contract.v0.1",
            "status": "PASS_STATIC_IMPORT_CONTRACT", "runner_sha256": sha(runner),
            "qualification_source_sha256": sha(subject), "imports": rows,
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
    return {**body, "contract_root": sha(_canonical(body))}


def command(kit_sha: str, verifier_sha: str, subject_sha: str) -> bytes:
    text = rf'''@echo off
setlocal EnableExtensions
title UCM unified maturity Tier 1 operator court
echo UCM unified maturity Tier 1 operator court
echo ============================================================
set "KIT=%~dp0UCM-MATURITY-TIER1-OPERATOR-KIT.zip"
set "VERIFIER=%~dp0VERIFY.py"
set "EXPECTED_KIT={kit_sha}"
set "EXPECTED_VERIFIER={verifier_sha}"
set "EXPECTED_SUBJECT={subject_sha}"
set "PYEXE="
py -3.12 -c "import sys;assert sys.version_info[:2]==(3,12)" >nul 2>nul && set "PYEXE=py -3.12"
if not defined PYEXE py -3.13 -c "import sys;assert sys.version_info[:2]==(3,13)" >nul 2>nul && set "PYEXE=py -3.13"
if not defined PYEXE python -c "import sys;assert (3,12)<=sys.version_info[:2]<(3,14)" >nul 2>nul && set "PYEXE=python"
if not defined PYEXE goto :NO_PYTHON

echo [1/7] Checking exact kit and verifier pins...
for /f %%H in ('%PYEXE% -c "import hashlib,pathlib;print(hashlib.sha256(pathlib.Path(r'%KIT%').read_bytes()).hexdigest())"') do set "ACTUAL_KIT=%%H"
for /f %%H in ('%PYEXE% -c "import hashlib,pathlib;print(hashlib.sha256(pathlib.Path(r'%VERIFIER%').read_bytes()).hexdigest())"') do set "ACTUAL_VERIFIER=%%H"
if /I not "%ACTUAL_KIT%"=="%EXPECTED_KIT%" goto :PIN_FAIL
if /I not "%ACTUAL_VERIFIER%"=="%EXPECTED_VERIFIER%" goto :PIN_FAIL
echo [2/7] Verifying the canonical operator kit...
%PYEXE% "%VERIFIER%" "%KIT%" --schema "{SCHEMA}" --role "{ROLE}" || goto :FAIL
set "WORK=%TEMP%\UCM-MATURITY-TIER1-%RANDOM%-%RANDOM%"
mkdir "%WORK%" || goto :FAIL
echo [3/7] Extracting into a disposable workspace...
%PYEXE% -c "import zipfile;zipfile.ZipFile(r'%KIT%').extractall(r'%WORK%')" || goto :CLEAN_FAIL
echo [4/7] Verifying the exact qualification source...
%PYEXE% "%WORK%\VERIFY.py" "%WORK%\QUALIFICATION-SOURCE.zip" --schema "mosaic.ucm.maturity-qualification-source.v0.1" --role "UCM_MATURITY_QUALIFICATION_SOURCE" || goto :CLEAN_FAIL
echo [5/7] Running the operator-owned consolidated court with live progress...
%PYEXE% "%WORK%\RUN-MATURITY-TIER1.py" --subject "%WORK%\QUALIFICATION-SOURCE.zip" --expected-subject-sha256 "%EXPECTED_SUBJECT%" --output "%WORK%\TIER1-EVIDENCE.zip"
set "COURT_RC=%ERRORLEVEL%"
if not exist "%WORK%\TIER1-EVIDENCE.zip" goto :CLEAN_FAIL
echo [6/7] Verifying and preserving sealed evidence...
%PYEXE% "%WORK%\VERIFY.py" "%WORK%\TIER1-EVIDENCE.zip" --schema "mosaic.ucm.maturity-tier1-evidence.v0.1" --role "UCM_MATURITY_TIER1_EVIDENCE" || goto :CLEAN_FAIL
for /f %%T in ('powershell -NoProfile -Command "(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')"') do set "STAMP=%%T"
copy /Y "%WORK%\TIER1-EVIDENCE.zip" "%~dp0UCM-MATURITY-TIER1-EVIDENCE-%STAMP%.zip" >nul || goto :CLEAN_FAIL
echo [7/7] Removing disposable review files...
rmdir /S /Q "%WORK%"
if not "%COURT_RC%"=="0" goto :HOLD
echo.
echo PASS - sealed Tier 1 evidence was written beside this command.
pause
exit /b 0

:HOLD
echo.
echo HOLD_FOR_REPAIR - sealed evidence was preserved beside this command.
pause
exit /b 2
:NO_PYTHON
echo NOTICE: No suitable Python 3.12 or 3.13 runtime found.
goto :FAIL
:PIN_FAIL
echo ERROR: Operator kit or verifier pin mismatch.
goto :FAIL
:CLEAN_FAIL
if defined WORK if exist "%WORK%" rmdir /S /Q "%WORK%"
:FAIL
echo.
echo ERROR - inspect the diagnostic above.
pause
exit /b 1
'''
    return text.replace("\n", "\r\n").encode("ascii")


def build(qualification_dir: Path, output: Path) -> dict:
    qualification_raw = (qualification_dir / "QUALIFICATION.json").read_bytes()
    qualification = json.loads(qualification_raw)
    if qualification.get("status") != "PASS" or qualification.get("operator_adversarial_status") != "SEPARATE_USER_RUN_REQUIRED":
        raise SystemExit("MATURITY_OPERATOR_QUALIFICATION_INVALID")
    subject = (qualification_dir / "QUALIFICATION-SOURCE.zip").read_bytes()
    expected = qualification["qualification_source_anchor"]["archive_sha256"]
    if sha(subject) != expected:
        raise SystemExit("MATURITY_OPERATOR_SUBJECT_PIN_MISMATCH")
    verifier = (ROOT / "VERIFY.py").read_bytes()
    runner = (ROOT / "review/operator/RUN-MATURITY-TIER1.py").read_bytes()
    import_contract = build_runner_import_contract(subject, runner)
    payloads = {
        "QUALIFICATION-SOURCE.zip": subject,
        "QUALIFICATION.json": qualification_raw,
        "RUN-MATURITY-TIER1.py": runner,
        "OPERATOR-RUNNER-IMPORT-CONTRACT.json": _canonical(import_contract),
        "PREDECESSOR-TIER1-EVIDENCE.zip": (
            ROOT / "review/operator/predecessor-c2/TIER1-HOLD-EVIDENCE.zip").read_bytes(),
        "PREDECESSOR-TIER1-DISPOSITION.json": _canonical(json.loads((
            ROOT / "review/operator/predecessor-c2/DISPOSITION.json").read_text(
                encoding="utf-8"))),
        "VERIFY.py": verifier,
        "REVIEW-WORK-ORDER.md": (ROOT / "review/JOINT-MATURITY-INDEPENDENT-REVIEW-WORK-ORDER.md").read_bytes(),
        "README.txt": ("Double-click RUN-MATURITY-TIER1.cmd beside this archive.\n"
                       "This v0.2 kit carries and disposes the earlier court-schema hold.\n"
                       "The court uses a disposable workspace, preserves sealed evidence, "
                       "and removes temporary files.\n").encode("ascii"),
    }
    first = deterministic_zip(payloads, schema=SCHEMA, artifact_role=ROLE)
    second = deterministic_zip(payloads, schema=SCHEMA, artifact_role=ROLE)
    if first != second:
        raise SystemExit("MATURITY_OPERATOR_KIT_NONDETERMINISTIC")
    verify_deterministic_zip(first, expected_schema=SCHEMA, expected_role=ROLE)
    if output.exists() and any(output.iterdir()):
        raise SystemExit("MATURITY_OPERATOR_OUTPUT_NOT_EMPTY")
    output.mkdir(parents=True, exist_ok=True)
    (output / "UCM-MATURITY-TIER1-OPERATOR-KIT.zip").write_bytes(first)
    (output / "VERIFY.py").write_bytes(verifier)
    (output / "RUN-MATURITY-TIER1.cmd").write_bytes(
        command(sha(first), sha(verifier), expected))
    (output / "README.md").write_text(
        "# UCM maturity Tier 1 operator delivery\n\n"
        "Double-click `RUN-MATURITY-TIER1.cmd`. It verifies pins, extracts into a "
        "temporary directory, prints live case and summary progress, writes sealed "
        "evidence beside the command, removes temporary files, and pauses. The run "
        "is engineering evidence and does not grant authority.\n", encoding="utf-8")
    return {"status": "PASS", "kit_sha256": sha(first),
            "qualification_source_sha256": expected, "operator_court_executed": False,
            "runner_import_contract_root": import_contract["contract_root"],
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.qualification_dir.resolve(), args.output.resolve())
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

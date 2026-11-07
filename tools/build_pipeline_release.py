"""Build the standalone UCM-AMCAS pipeline and portable handoff."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, require, root, strict_loads
from ucm.amcas import BOUNDARY
from ucm.artifacts import deterministic_zip, verify_deterministic_zip
from build_agentic_adaptation_sidecar import build as build_sidecar


RELEASE_SCHEMA = "mosaic.ucm.amcas-integration-pipeline-release.v0.1"
RELEASE_ROLE = "UCM_AMCAS_INTEGRATION_PIPELINE"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def cmd(release_hash: str) -> bytes:
    return f'''@echo off
setlocal
cd /d "%~dp0"
set "DEST=%~1"
if "%DEST%"=="" set "DEST=%CD%\\MOSAIC-UCM-AMCAS-PIPELINE-v0.1"
set "PYEXE=python"
where py >nul 2>nul && set "PYEXE=py -3"
echo [1/3] Verifying and installing the exact pipeline release...
%PYEXE% INSTALL.py "MOSAIC-UCM-AMCAS-INTEGRATION-PIPELINE-v0.1.zip" "%DEST%" --expected-sha256 {release_hash}
if errorlevel 1 goto :fail
echo [2/3] UCM orientation...
%PYEXE% "%DEST%\\tools\\ucm.py" orient
if errorlevel 1 goto :fail
echo [3/3] UCM capability surface...
%PYEXE% "%DEST%\\tools\\ucm.py" capabilities
if errorlevel 1 goto :fail
echo.
echo PASS - UCM-AMCAS Integration Pipeline v0.1 is installed at:
echo %DEST%
pause
exit /b 0
:fail
echo.
echo REFUSED - installation did not complete.
pause
exit /b 1
'''.replace("\n", "\r\n").encode("utf-8")


def build(qualification_dir: Path, output: Path) -> dict:
    qualification_raw = (qualification_dir / "QUALIFICATION.json").read_bytes()
    qualification = strict_loads(qualification_raw)
    require(qualification["status"] == "PASS" and qualification["failures"] == 0
            and qualification["errors"] == 0 and qualification["skips"] == 0,
            "PIPELINE_QUALIFICATION_INVALID")
    software_raw = (qualification_dir / "CANONICAL-SOFTWARE.zip").read_bytes()
    software_anchor_raw = (qualification_dir / "SOFTWARE-ANCHOR.json").read_bytes()
    software_anchor = strict_loads(software_anchor_raw)
    require(software_anchor["archive_sha256"] == sha(software_raw),
            "PIPELINE_SOFTWARE_ANCHOR_MISMATCH")
    sidecar_raw = build_sidecar()
    contract_body = {
        "schema": "mosaic.ucm.amcas-integration-pipeline-contract.v0.1",
        "product": "UCM-AMCAS Integration Pipeline", "version": "v0.1",
        "software_sha256": sha(software_raw), "sidecar_sha256": sha(sidecar_raw),
        "qualification_root": qualification["qualification_root"],
        "commands": ["orient", "capabilities", "validate-amcas", "compile-amcas",
                     "portfolio-import-stage1", "portfolio-import-stage2",
                     "portfolio-import-correspondence-court", "portfolio-status",
                     "portfolio-issue-stage3-instructions",
                     "portfolio-import-stage3-plan", "stage3-validate-plan",
                     "stage4-derive-eligibility", "stage4-build-run-contract",
                     "stage4-validate-observation", "stage4-validate-run-contract",
                     "stage4-c3-derive-eligibility", "stage4-c3-build-run-contract",
                     "stage4-c3-build-terminal-refusal"],
        "canonical_software_scope": "INSTALLABLE_RUNTIME_WITH_BOUND_QUALIFICATION_SEPARATE",
        "runtime_release_separate": True,
        "manual_review_claim": "OPERATOR_REPRODUCED_ADVERSARIAL_EVIDENCE",
        "independent_review_claim_inferred": False,
        "migration_portfolio_embedded": False,
        **BOUNDARY,
    }
    contract = {**contract_body, "contract_root": root(contract_body)}
    payloads = {
        "CANONICAL-SOFTWARE.zip": software_raw,
        "SOFTWARE-ANCHOR.json": software_anchor_raw,
        "UCM-AMCAS-AGENTIC-ADAPTATION-SIDECAR-v0.1.zip": sidecar_raw,
        "PIPELINE-CONTRACT.json": canonical_bytes(contract),
        "QUALIFICATION.json": qualification_raw,
        "START-HERE.md": (ROOT / "pipeline/START-HERE.md").read_bytes(),
    }
    release = deterministic_zip(payloads, schema=RELEASE_SCHEMA, artifact_role=RELEASE_ROLE)
    release_manifest = verify_deterministic_zip(release, expected_schema=RELEASE_SCHEMA,
                                                expected_role=RELEASE_ROLE)
    release_hash = sha(release)
    receipt_body = {
        "schema": "mosaic.ucm.amcas-integration-pipeline-release-receipt.v0.1",
        "release_sha256": release_hash, "release_bytes": len(release),
        "release_manifest_root": release_manifest["manifest_root"],
        "software_sha256": sha(software_raw), "sidecar_sha256": sha(sidecar_raw),
        "qualification_root": qualification["qualification_root"],
        "test_count": qualification["test_count"], "failures": 0, "errors": 0, "skips": 0,
        "migration_track_separate": True, **BOUNDARY,
    }
    receipt = {**receipt_body, "receipt_root": root(receipt_body)}
    output.mkdir(parents=True, exist_ok=True)
    files = {
        "MOSAIC-UCM-AMCAS-INTEGRATION-PIPELINE-v0.1.zip": release,
        "PIPELINE-RELEASE-RECEIPT.json": canonical_bytes(receipt),
        "INSTALL.py": (ROOT / "pipeline/INSTALL.py").read_bytes(),
        "RUN-UCM-AMCAS-INTEGRATION-PIPELINE.cmd": cmd(release_hash),
        "START-HERE.md": (ROOT / "pipeline/START-HERE.md").read_bytes(),
    }
    for name, raw in files.items():
        (output / name).write_bytes(raw)
    boundary = {
        "schema": "codex.exact-artifact-boundary.v1",
        "boundary_id": "ucm-amcas-integration-pipeline-v0.1-handoff",
        "artifacts": [{"source_path": name, "destination_path": name,
                       "sha256": sha(raw), "required_by": "pipeline installer handoff"}
                      for name, raw in sorted(files.items())],
        "runner_required_paths": sorted(files), "allow_extra_artifacts": False,
        "policy": {"maximum_transfers": 1, "maximum_invocations": 1,
                   "maximum_retries": 0, "preserve_prior_custody": True,
                   "terminal_capture": ["stdout", "stderr", "exit_code", "terminal_receipt"]},
    }
    boundary_raw = canonical_bytes(boundary)
    (output / "EXACT-ARTIFACT-BOUNDARY.json").write_bytes(boundary_raw)
    handoff_payloads = {**files, "EXACT-ARTIFACT-BOUNDARY.json": boundary_raw}
    handoff = deterministic_zip(handoff_payloads,
        schema="mosaic.ucm.amcas-integration-pipeline-handoff.v0.1",
        artifact_role="UCM_AMCAS_INTEGRATION_PIPELINE_HANDOFF")
    verify_deterministic_zip(handoff,
        expected_schema="mosaic.ucm.amcas-integration-pipeline-handoff.v0.1",
        expected_role="UCM_AMCAS_INTEGRATION_PIPELINE_HANDOFF")
    (output / "MOSAIC-UCM-AMCAS-INTEGRATION-PIPELINE-v0.1-HANDOFF.zip").write_bytes(handoff)
    return {"status": "PASS", "release_sha256": release_hash,
            "handoff_sha256": sha(handoff), "receipt_root": receipt["receipt_root"],
            "qualification_root": qualification["qualification_root"], **BOUNDARY}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() or not any(args.output.iterdir()),
            "PIPELINE_RELEASE_OUTPUT_NOT_EMPTY")
    result = build(args.qualification_dir.resolve(), args.output.resolve())
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

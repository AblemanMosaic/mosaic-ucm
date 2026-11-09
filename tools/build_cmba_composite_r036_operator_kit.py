#!/usr/bin/env python3
"""Build (never execute) the exact r036 cmba-composite operator review apparatus."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FIXED = (1980, 1, 1, 0, 0, 0)
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def rooted(value, field="root"):
    return value.get(field) == sha(canonical({key: item for key, item in value.items() if key != field}))


def cold_boot_binding(path, expected_runtime_sha256):
    """Check full member custody and BOOT's exact runtime pin without execution."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        manifest = json.loads(archive.read("MANIFEST.json"))
        rows = manifest["members"]
        if (len(names) != len(set(names)) or not rooted(manifest, "manifest_root")
                or len(rows) != manifest["member_count"]
                or [row["path"] for row in rows] != sorted({row["path"] for row in rows})
                or set(names) != {"MANIFEST.json", *(row["path"] for row in rows)}):
            raise ValueError("COLD_BOOT_MANIFEST_CUSTODY_INVALID")
        for row in rows:
            raw = archive.read(row["path"])
            if len(raw) != row["bytes"] or sha(raw) != row["sha256"]:
                raise ValueError("COLD_BOOT_MEMBER_BYTES_INVALID")
        metadata = json.loads(archive.read("BOOT/COLD-BOOT.json"))
        if (not rooted(metadata, "cold_boot_root")
                or metadata.get("runtime_sha256") != expected_runtime_sha256
                or sha(archive.read("UCM/UCM-v0.1-runtime.zip")) != expected_runtime_sha256
                or metadata.get("version") != "v0.1" or metadata.get("revision") != "r036"):
            raise ValueError("COLD_BOOT_RUNTIME_BINDING_MISMATCH")
        return {"manifest_root": manifest["manifest_root"],
                "cold_boot_root": metadata["cold_boot_root"],
                "embedded_runtime_sha256": expected_runtime_sha256,
                "metadata_scope": "MANIFEST_AND_BOOT_PIN_CUSTODY_ONLY"}


def fixture(source_root):
    """Construct both positive modes; no adversarial case is called."""
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
    from test_pippi_cmba_positive import common_turn_fixture
    from test_pippi_cmba_composite_positive import (ccp_fixture, dispatch,
        operation_fixture, terminal)
    from ucm.operation_gateway import OperationGateway
    from ucm.pippi_cmba import CMBA_WHEEL_SHA256, build_cmba_turn_assessment
    from ucm.pippi_cmba_composite import build_composite_assessment, composite_profile
    from ucm.process_governance import build_dkn_locality_binding
    from uclop.canonical import root
    import ucm
    if Path(ucm.__file__).resolve() != ROOT / "src/ucm/__init__.py":
        raise ValueError("BUILDER_SUBJECT_IMPORT_ORIGIN_MISMATCH")
    opening, report, turn = common_turn_fixture()
    cmba = build_cmba_turn_assessment(opening=opening, report=report, turn_record=turn,
        expected_wheel_sha256=CMBA_WHEEL_SHA256)
    evaluation, correspondence, jurisdiction_root = ccp_fixture(turn["turn_record_root"])
    dkn = build_dkn_locality_binding(phase_code="CMBA_R036",
        authority_public_key_hex="41" * 32, semantic_namespace="mosaic.ucm.v0.1",
        universe_root=root({"universe": "r036"}), namespace_policy_root=root({"policy": "r036"}),
        passport=None, possession_receipt_root=None, local_admission_root=None)
    base = {"opening": opening, "report": report, "turn_record": turn,
        "cmba_assessment": cmba, "expected_wheel_sha256": CMBA_WHEEL_SHA256,
        "dkn_locality_binding": dkn, "chc_thr_correspondence": correspondence,
        "ccp_transition_id": "PROPOSE_PUBLICATION", "ccp_evaluation": evaluation}
    observational_inputs = {**base, "operation_history": None}
    observational_result = build_composite_assessment(**observational_inputs)
    revocation, contract = operation_fixture(turn["turn_record_root"], jurisdiction_root)
    anchors = evaluation["expected_anchors"]
    with tempfile.TemporaryDirectory(dir=ROOT.parent) as raw:
        gateway = OperationGateway(Path(raw))
        prepared = gateway.prepare_with_admissibility(contract, evaluation["decision"],
            current_use_snapshot=evaluation["current_use_snapshot"],
            evidence_snapshot=evaluation["evidence_snapshot"],
            jurisdiction_profile=evaluation["jurisdiction_profile"],
            enforcement_perimeter=evaluation["enforcement_perimeter"],
            correspondence=evaluation["correspondence"],
            expected_admissibility_decision_root=evaluation["decision"]["decision_root"],
            expected_current_use_snapshot_root=evaluation["current_use_snapshot"]["current_use_snapshot_root"],
            expected_issuer_public_key_hex=contract["permit"]["issuer_public_key_hex"],
            expected_jurisdiction_root=jurisdiction_root,
            expected_revocation_registry_root=revocation["revocation_registry_root"], **anchors)
        dispatched = gateway.record_dispatch(contract["operation_id"], dispatch(prepared, contract))
        gateway.record_terminal(contract["operation_id"], terminal(dispatched, contract))
        history = {"operation_id": contract["operation_id"], "events": gateway.journal.verify(),
            "expected_issuer_public_key_hex": contract["permit"]["issuer_public_key_hex"],
            "expected_jurisdiction_root": jurisdiction_root,
            "expected_revocation_registry_root": revocation["revocation_registry_root"]}
    effect_inputs = {**base, "operation_history": history}
    effect_result = build_composite_assessment(**effect_inputs)
    return {"schema": "mosaic.ucm.r036-operator-control-fixture.v0.1", "fixture_only": True,
            "source_root": source_root, "profile": composite_profile(),
            "observational": {"inputs": observational_inputs, "result": observational_result},
            "effect_bound": {"inputs": effect_inputs, "result": effect_result}, **BOUNDARY}


def zip_write(path, payload):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, raw in sorted(payload.items()):
            info = zipfile.ZipInfo(name, FIXED)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)


def build(runtime, qualification, source_manifest, output, cold_boot=None):
    source = json.loads(source_manifest.read_text(encoding="utf-8"))
    receipt = json.loads(qualification.read_text(encoding="utf-8"))
    if not rooted(source) or not rooted(receipt):
        raise ValueError("SUBJECT_INPUT_ROOT_INVALID")
    if receipt.get("engineering_revision") != "r036" or receipt.get("source_manifest_root") != source["root"]:
        raise ValueError("QUALIFICATION_SOURCE_BINDING_MISMATCH")
    with zipfile.ZipFile(runtime) as archive:
        runtime_manifest = json.loads(archive.read("MANIFEST.json"))
        if not rooted(runtime_manifest):
            raise ValueError("RUNTIME_MANIFEST_ROOT_INVALID")
        required_runtime = {"src/ucm/__init__.py", "src/ucm/system.py", "src/uclop/canonical.py",
            "src/ucm/pippi_turn_record.py", "src/ucm/pippi_cmba.py",
            "src/ucm/pippi_cmba_composite.py", "src/ucm/ccp_admissibility.py",
            "src/ucm/operation_gateway.py", "src/ucm/operation_proofs.py", "src/ucm/thr_cas.py",
            "vendor/optional-packs/cmba/cmba_core-0.1.0a7-py3-none-any.whl"}
        if not required_runtime <= set(archive.namelist()):
            raise ValueError("OPERATOR_RUNTIME_READ_SET_INCOMPLETE")
    runtime_sha256 = sha(runtime.read_bytes())
    qualified_runtime = [row for row in receipt.get("artifacts", []) if row.get("role") == "UCM_RUNTIME"]
    if (len(qualified_runtime) != 1 or qualified_runtime[0].get("sha256") != runtime_sha256
            or qualified_runtime[0].get("manifest_root") != runtime_manifest["root"]):
        raise ValueError("QUALIFICATION_RUNTIME_BINDING_MISMATCH")
    cold_binding = cold_boot_binding(cold_boot, runtime_sha256) if cold_boot is not None else None
    runner = (ROOT / "tools/cmba_composite_r036_court.py").read_bytes()
    tree = ast.parse(runner)
    ids = next(ast.literal_eval(node.value) for node in tree.body
               if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
                   and target.id == "CASE_IDS" for target in node.targets))
    payload = {"RUN-TIER1.py": runner, "UCM-v0.1-runtime.zip": runtime.read_bytes(),
        "UCM-v0.1-QUALIFICATION.json": qualification.read_bytes(),
        "SOURCE-MANIFEST.json": source_manifest.read_bytes(),
        "CONTROL.json": canonical(fixture(source["root"])) + b"\n"}
    if cold_boot is not None:
        payload["PIPPI-v0.1-adaptive-cold-boot.zip"] = cold_boot.read_bytes()
    boundary = {"schema": "mosaic.ucm.r036-operator-boundary.v0.1",
        "boundary_id": "R036_CMBA_COMPOSITE_OPERATOR",
        "runner_required_paths": sorted({*payload, "BOUNDARY.json", "KIT-MANIFEST.json"}),
        "nested_runtime_read_set": "COMPLETE_VERIFIED_RUNTIME_MANIFEST",
        "runtime_manifest_root": runtime_manifest["root"],
        "optional_cmba_wheel": "vendor/optional-packs/cmba/cmba_core-0.1.0a7-py3-none-any.whl",
        "runner_path": "RUN-TIER1.py", "allow_extra_artifacts": False,
        "external_evidence_directory_required": True, **BOUNDARY}
    boundary["boundary_root"] = sha(canonical(boundary))
    payload["BOUNDARY.json"] = canonical(boundary) + b"\n"
    rows = [{"path": name, "bytes": len(raw), "sha256": sha(raw)} for name, raw in sorted(payload.items())]
    manifest = {"schema": "mosaic.ucm.r036-cmba-composite-operator-kit.v0.1",
        "subject_id": "UCM_R036_CMBA_COMPOSITE", "revision": "r036",
        "members": rows, "member_count": len(rows), "case_ids": list(ids), "case_count": len(ids),
        "runtime_sha256": sha(payload["UCM-v0.1-runtime.zip"]),
        "runtime_manifest_root": runtime_manifest["root"], "source_root": source["root"],
        "runtime_source_boundary": "EXACT",
        "qualification_root": receipt["root"], "qualification_sha256": sha(payload["UCM-v0.1-QUALIFICATION.json"]),
        "cold_boot_sha256": sha(cold_boot.read_bytes()) if cold_boot is not None else None,
        "cold_boot_binding": cold_binding,
        "cold_boot_validation_scope": "CUSTODY_AND_EXACT_RUNTIME_CORRESPONDENCE" if cold_boot is not None else "NOT_INCLUDED",
        "boundary_root": boundary["boundary_root"], "runner_path": "RUN-TIER1.py",
        "builder_authored": True, "operator_executed": False, "tier1_executed": False,
        "independent_review_claimed": False, "adversarial_execution_by_builder": False,
        "launcher_contract": {"verified_external_archive_pin": True, "disposable_workspace": True,
            "live_case_progress": True, "sealed_fault_evidence": True, "raw_exception_text_in_evidence": False,
            "preserve_evidence_before_cleanup": True, "cleanup_resolved_path_check": True,
            "retain_workspace_when_durable_copy_unproven": True,
            "court_and_launcher_status_separated": True,
            "terminal_receipt_after_cleanup": True,
            "pause_after_terminal_status": True}, **BOUNDARY}
    manifest["operator_kit_root"] = sha(canonical(manifest))
    payload["KIT-MANIFEST.json"] = canonical(manifest) + b"\n"
    output.mkdir(parents=True, exist_ok=True)
    kit = output / "UCM-r036-CMBA-COMPOSITE-OPERATOR-KIT.zip"
    zip_write(kit, payload)
    digest = sha(kit.read_bytes())
    ps1 = POWERSHELL.replace("__KIT_SHA256__", digest).replace("__KIT_NAME__", kit.name)
    (output / "RUN.ps1").write_text(ps1, encoding="utf-8", newline="\r\n")
    ps1_sha = sha((output / "RUN.ps1").read_bytes())
    cmd = ('@echo off\r\nsetlocal\r\nset "PIPPI_REVIEW_HOME=%~dp0"\r\n'
        'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command '
        '"$p=Join-Path $env:PIPPI_REVIEW_HOME \'RUN.ps1\'; '
        f'if((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne \'{ps1_sha}\')'
        '{Write-Host \'HOLD_FOR_REPAIR - LAUNCHER_HASH_MISMATCH\'; exit 3}; & $p"\r\n'
        'set "reviewExit=%ERRORLEVEL%"\r\necho.\r\npause\r\nexit /b %reviewExit%\r\n')
    (output / "RUN.cmd").write_text(cmd, encoding="utf-8", newline="")
    start = ("# UCM v0.1 r036 cmba-composite operator review\n\n"
        "Double-click RUN.cmd. The command verifies, extracts, runs the builder-authored court, "
        "preserves and verifies sealed evidence here, removes temporary files only after durable preservation, "
        "writes a separate launcher terminal receipt, and pauses. If preservation cannot be proven, the recovery "
        "workspace is retained and printed.\n\n"
        "The authoring agent has not run the adversarial court. A user-run PASS is operator evidence; "
        "it does not claim an independent review.\n\n"
        f"Kit SHA-256: `{digest}`\n\nFixed case denominator: {len(ids)}.\n\n"
        "Use the runner's --preflight-only option for stdlib custody checks with zero subject imports "
        "and zero adversarial cases. Evidence must be outside the extracted immutable kit.\n\n"
        "Standing INFORMATION_ONLY; authority effect NONE; real A5 false; G0 closed.\n")
    (output / "START-HERE.md").write_text(start, encoding="utf-8", newline="\n")
    delivery = {"schema": "mosaic.ucm.r036-operator-delivery.v0.1",
        "members": [{"path": path.name, "bytes": path.stat().st_size, "sha256": sha(path.read_bytes())}
                    for path in sorted(output.iterdir()) if path.is_file()
                    and path.name in {kit.name, "RUN.ps1", "RUN.cmd", "START-HERE.md"}],
        "operator_kit_root": manifest["operator_kit_root"], **BOUNDARY}
    delivery["delivery_root"] = sha(canonical(delivery))
    (output / "DELIVERY-MANIFEST.json").write_bytes(canonical(delivery) + b"\n")
    return {"status": "PASS", "kit": str(kit), "kit_sha256": digest,
            "operator_kit_root": manifest["operator_kit_root"], "case_count": len(ids),
            "launcher": str(output / "RUN.cmd"), "operator_executed": False,
            "adversarial_cases_executed": 0, **BOUNDARY}


POWERSHELL = r'''$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$kit = Join-Path $here '__KIT_NAME__'
$expected = '__KIT_SHA256__'
$tempBase = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\')
$temp = Join-Path $tempBase ('UCM-r036-CMBA-COMPOSITE-' + [guid]::NewGuid().ToString('N'))
$kitRoot = Join-Path $temp 'kit'
$evidenceRoot = Join-Path $temp 'evidence'
$resultCode = 3
$phase = 'INITIALIZE'
$courtStatus = 'NOT_RUN'
$durableEvidence = $false
$durableFault = $false
$cleanupStatus = 'NOT_ATTEMPTED'
$recoveryRetained = $false
$evidencePath = $null
$evidenceSha256 = $null
$faultPath = $null
function Write-SealedFault($errorRecord) {
  $messageBytes = [Text.Encoding]::UTF8.GetBytes([string]$errorRecord.Exception.Message)
  $hasher = [Security.Cryptography.SHA256]::Create()
  try { $messageHash = [BitConverter]::ToString($hasher.ComputeHash($messageBytes)).Replace('-','').ToLowerInvariant() } finally { $hasher.Dispose() }
  $publicCode='LAUNCHER_FAULT';if($errorRecord.Exception.Message -match '^[A-Z][A-Z0-9_]{1,120}$'){$publicCode=$errorRecord.Exception.Message}
  $record = [ordered]@{schema='mosaic.ucm.r036-operator-launcher-fault.v0.1';status='HOLD_FOR_REPAIR';phase=$phase;diagnostic_code=$publicCode;exception_type=$errorRecord.Exception.GetType().FullName;message_sha256=$messageHash;expected_kit_sha256=$expected;standing='INFORMATION_ONLY';authority_effect='NONE';real_a5=$false;g0='CLOSED'}
  $bytes = [Text.Encoding]::UTF8.GetBytes(($record | ConvertTo-Json -Compress))
  Add-Type -AssemblyName System.IO.Compression
  $faultZip = Join-Path $temp 'LAUNCHER-FAULT.zip'
  $stream = [IO.File]::Open($faultZip,[IO.FileMode]::CreateNew)
  $archive = [IO.Compression.ZipArchive]::new($stream,[IO.Compression.ZipArchiveMode]::Create,$false)
  try { $entry=$archive.CreateEntry('FAULT.json');$entry.LastWriteTime=[DateTimeOffset]::new(1980,1,1,0,0,0,[TimeSpan]::Zero);$entryStream=$entry.Open();try{$entryStream.Write($bytes,0,$bytes.Length)}finally{$entryStream.Dispose()} } finally { $archive.Dispose();$stream.Dispose() }
  $digest=(Get-FileHash -LiteralPath $faultZip -Algorithm SHA256).Hash.ToLowerInvariant()
  $preserved=Join-Path $here ('UCM-r036-CMBA-COMPOSITE-LAUNCHER-FAULT-'+$digest.Substring(0,16)+'.zip')
  Copy-Item -LiteralPath $faultZip -Destination $preserved -Force
  if((Get-FileHash -LiteralPath $preserved -Algorithm SHA256).Hash.ToLowerInvariant() -ne $digest){throw 'PRESERVED_FAULT_HASH_MISMATCH'}
  $script:durableFault=$true
  $script:faultPath=$preserved
  Write-Host ('Fault evidence: '+$preserved)
}
function Write-TerminalReceipt {
  $terminalStatus = if($courtStatus -eq 'PASS' -and $durableEvidence -and $cleanupStatus -eq 'REMOVED'){'PASS'}else{'HOLD_FOR_REPAIR'}
  $record=[ordered]@{schema='mosaic.ucm.r036-operator-launcher-terminal.v0.1';status=$terminalStatus;court_status=$courtStatus;phase=$phase;expected_kit_sha256=$expected;evidence_path=$evidencePath;evidence_sha256=$evidenceSha256;fault_path=$faultPath;durable_preservation_verified=($durableEvidence -or $durableFault);cleanup_status=$cleanupStatus;recovery_workspace_retained=$recoveryRetained;recovery_path=$(if($recoveryRetained){$temp}else{$null});standing='INFORMATION_ONLY';authority_effect='NONE';real_a5=$false;g0='CLOSED'}
  $json=($record|ConvertTo-Json -Compress)
  $bytes=[Text.Encoding]::UTF8.GetBytes($json)
  $hasher=[Security.Cryptography.SHA256]::Create()
  try{$digest=[BitConverter]::ToString($hasher.ComputeHash($bytes)).Replace('-','').ToLowerInvariant()}finally{$hasher.Dispose()}
  $path=Join-Path $here ('UCM-r036-CMBA-COMPOSITE-LAUNCHER-TERMINAL-'+$digest.Substring(0,16)+'.json')
  $pending=$path+'.pending'
  [IO.File]::WriteAllBytes($pending,$bytes)
  Move-Item -LiteralPath $pending -Destination $path -Force
  if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $digest){throw 'TERMINAL_RECEIPT_HASH_MISMATCH'}
  Write-Host ('Terminal receipt: '+$path)
  return $terminalStatus
}
try {
  New-Item -ItemType Directory -Path $temp | Out-Null
  Write-Host 'UCM r036 cmba-composite closure operator Tier 1 court'
  $phase='VERIFY_KIT'; Write-Host '[1/7] Verifying the sealed operator kit...'
  if ((Get-FileHash -LiteralPath $kit -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw 'OPERATOR_KIT_HASH_MISMATCH' }
  $phase='EXTRACT'; Write-Host '[2/7] Extracting into a disposable review workspace...'
  Expand-Archive -LiteralPath $kit -DestinationPath $kitRoot
  $candidates=@((Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),(Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'))
  $exe=$candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
  if(-not $exe){$pythonCommand=Get-Command python -ErrorAction SilentlyContinue;if($pythonCommand){$exe=$pythonCommand.Source}}
  if(-not $exe){throw 'PYTHON_RUNTIME_MISSING'}
  & $exe -I -c 'import sys;raise SystemExit(0 if sys.version_info >= (3,12) else 3)'
  if($LASTEXITCODE -ne 0){throw 'PYTHON_312_OR_NEWER_REQUIRED'}
  $runner=Join-Path $kitRoot 'RUN-TIER1.py'
  $phase='CUSTODY_PREFLIGHT'; Write-Host '[3/7] Running custody preflight (zero attack cases)...'
  & $exe -I -B $runner --kit-root $kitRoot --preflight-only
  if($LASTEXITCODE -ne 0){throw 'CUSTODY_PREFLIGHT_FAILED'}
  $phase='OPERATOR_COURT'; Write-Host '[4/7] Running operator cases with live progress...'
  & $exe -I -B $runner --kit-root $kitRoot --out-dir $evidenceRoot
  $courtCode=$LASTEXITCODE
  $courtStatus=if($courtCode -eq 0){'PASS'}else{'HOLD_FOR_REPAIR'}
  $phase='PRESERVE_EVIDENCE'; Write-Host '[5/7] Preserving sealed evidence beside this command...'
  if(-not (Test-Path -LiteralPath $evidenceRoot)){throw 'TIER1_EVIDENCE_MISSING'}
  $evidence=@(Get-ChildItem -LiteralPath $evidenceRoot -Filter '*.zip')
  if($evidence.Count -ne 1){throw 'TIER1_EVIDENCE_SET_INVALID'}
  $destination=Join-Path $here $evidence[0].Name
  Copy-Item -LiteralPath $evidence[0].FullName -Destination $destination -Force
  $sourceDigest=(Get-FileHash -LiteralPath $evidence[0].FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  $destinationDigest=(Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
  if($destinationDigest -ne $sourceDigest){throw 'PRESERVED_EVIDENCE_HASH_MISMATCH'}
  $durableEvidence=$true
  $evidencePath=$destination
  $evidenceSha256=$destinationDigest
  Write-Host ('Evidence: '+$destination)
  $phase='COURT_RECORDED'; Write-Host ('[6/7] Court status '+$courtStatus+'; final launcher outcome pending cleanup.')
} catch {
  $courtStatus='HOLD_FOR_REPAIR'
  $publicCode=$_.Exception.GetType().Name;if($_.Exception.Message -match '^[A-Z][A-Z0-9_]{1,120}$'){$publicCode=$_.Exception.Message}
  Write-Host ('HOLD_FOR_REPAIR - '+$publicCode)
  try{Write-SealedFault $_}catch{Write-Host 'FAULT_EVIDENCE_WRITE_FAILED'}
  $resultCode=3
} finally {
  $phase='CLEANUP'; Write-Host '[7/7] Resolving disposable review files...'
  if(Test-Path -LiteralPath $temp){
    if($durableEvidence -or $durableFault){
      try{
        $resolved=[IO.Path]::GetFullPath((Resolve-Path -LiteralPath $temp).Path)
        $expectedTarget=[IO.Path]::GetFullPath($temp)
        if($resolved -ne $expectedTarget -or -not $resolved.StartsWith($tempBase+'\',[StringComparison]::OrdinalIgnoreCase) -or (Split-Path -Leaf $resolved) -notlike 'UCM-r036-CMBA-COMPOSITE-*' -or ((Get-Item -LiteralPath $resolved).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'CLEANUP_TARGET_REFUSED'}
        Remove-Item -LiteralPath $resolved -Recurse -Force
        $cleanupStatus='REMOVED'
      }catch{
        $cleanupStatus='FAILED'
        $recoveryRetained=$true
        Write-Host ('Recovery workspace retained: '+$temp)
      }
    }else{
      $cleanupStatus='RETAINED_NO_DURABLE_COPY'
      $recoveryRetained=$true
      Write-Host ('Recovery workspace retained: '+$temp)
    }
  }else{$cleanupStatus='NOT_CREATED'}
}
$phase='TERMINAL_RECEIPT'
try{
  $terminalStatus=Write-TerminalReceipt
  if($terminalStatus -eq 'PASS'){$resultCode=0;Write-Host 'PASS - court evidence is durable, cleanup is complete, and terminal receipt is sealed.'}
  else{$resultCode=3;Write-Host 'HOLD_FOR_REPAIR - inspect the preserved evidence, terminal receipt, or retained recovery workspace.'}
}catch{
  $resultCode=3
  Write-Host 'HOLD_FOR_REPAIR - TERMINAL_RECEIPT_WRITE_FAILED'
  if(Test-Path -LiteralPath $temp){Write-Host ('Recovery workspace: '+$temp)}
}
exit $resultCode
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--cold-boot", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.runtime.resolve(), args.qualification.resolve(),
        args.source_manifest.resolve(), args.output.resolve(),
        args.cold_boot.resolve() if args.cold_boot else None), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

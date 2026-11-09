#!/usr/bin/env python3
"""Build the acceptance-bound r032 native-completion successor program."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import root  # noqa: E402
from ucm.c_preflight import (BASE_CHECKS, CHANNELS, CHECKS_BY_CLASS,
                             build_c_change_preflight)  # noqa: E402
from ucm.native_core import native_core_profile  # noqa: E402

OUT = ROOT / "program/native-completion-r032"
PREDECESSOR_SOURCE_ROOT = "603b6e4d13be2d24e304bae4d20de22fa6843060a4521bcd74f7d17b6d5b089c"
BOUNDARY = {"standing":"INFORMATION_ONLY","authority_effect":"NONE",
            "real_a5":False,"g0":"CLOSED"}
FILES = (
    "README.md", "VERIFY.py", "docs/UCM-NATIVE-COMPLETION.md",
    "docs/LANGUAGES-AND-PROOF.md", "docs/CAPABILITY-SURFACES.md",
    "docs/SYSTEM-CATALOG.md",
    "docs/TRANSTEMPORAL-ARCHIVE-AND-NATIVE-VERIFICATION.md",
    "install/INSTALL-PIPPI.ps1", "install/INSTALL-PIPPI.vbs",
    "native/ucm_native_core.c", "native/ucm_archive_verify.c",
    "src/ucm/native_core.py", "src/ucm/transtemporal_archive.py",
    "src/ucm/amcas_parity.py",
    "src/ucm/system.py", "src/ucm/capabilities.py", "src/ucm/cli.py",
    "src/ucm/pippi_cli.py", "src/ucm/pippi_constitution.py",
    "tests/test_native_core_r032.py", "tests/test_transtemporal_archive.py",
    "tests/test_pippi_cold_boot.py", "tests/test_public_surface.py",
    "tests/test_pippi_portfolio.py", "tests/test_pippi_release_packaging.py",
    "tests/test_public_release_qualification.py",
    "tools/build_native_core_r032_assets.py", "tools/run_native_core_r032_leg.py",
    "tools/build_native_completion_r032_program.py",
    "tools/build_native_completion_r032_operator_kit.py",
    "tools/run_public_release_qualification.py", "tools/release_common.py",
    "tools/refresh_release_identity.py",
    "tools/run_portability_leg.py", "tools/verify_pippi_cold_boot.py",
    "tools/verify_release.py", "tools/verify_runtime_tree.py",
    "operator/native-completion-r032/KIT-DECLARATION.json",
    "operator/native-completion-r032/RUN-TIER1.py",
    "spec/UCM-NATIVE-CORE-PROFILE.json", "spec/UCM-NATIVE-CORE-CORPUS.json",
    "spec/PIPPI-ADAPTIVE-COLD-BOOT-CONTRACT.json",
    "spec/PIPPI-CAPABILITY-SURFACE-REGISTRY.json",
    "spec/PIPPI-CONSTITUTIONAL-STANDARDS-ATLAS.json",
    "spec/PIPPI-PIPELINE-MODEL.json",
    "spec/product-profiles/AUTHORING-PROFILE.json",
    "spec/product-profiles/COMPATIBILITY-PROFILE.json",
    "spec/product-profiles/OPERATIONAL-PROFILE.json",
    "spec/product-profiles/PROFILE-REGISTRY.json",
    "spec/product-profiles/VERIFY_ONLY-PROFILE.json",
    "spec/ucm-system-registry.json",
    "examples/native-core/ucm-arithmetic-truncating_division.json",
    "examples/native-core/ucm-arithmetic-truncating_division.ucln",
    "examples/native-core/ucm-branch-typed_disposition.json",
    "examples/native-core/ucm-branch-typed_disposition.ucln",
    "examples/native-core/ucm-budget-within_limit.json",
    "examples/native-core/ucm-budget-within_limit.ucln",
    "examples/native-core/ucm-gate-held_missing_witness.json",
    "examples/native-core/ucm-gate-held_missing_witness.ucln",
    "examples/native-core/ucm-gate-three_receipts.json",
    "examples/native-core/ucm-gate-three_receipts.ucln",
    "evidence/native-core-r032/WINDOWS-NATIVE-CORE-WITNESS.json",
    "evidence/native-core-r032/WSL-NATIVE-CORE-WITNESS.json",
    "release/PREDECESSOR-r031-QUALIFICATION.json",
    "release/PREDECESSOR-r031-RELEASE-IDENTITY.json",
    "review/r031/INDEPENDENT-REPORT.md", "review/r031/INDEPENDENT-FINDINGS.json",
    "review/r031/INDEPENDENT-RECOMPUTE.json", "review/r031/REVIEWER-EVIDENCE.zip",
    "review/r031/USER-TIER1-PASS-EVIDENCE.zip",
    "operator/transtemporal-native-r031-repaired/RUN-TIER1.py",
    "operator/transtemporal-native-r031-repaired/KIT-DECLARATION.json",
    "operator/transtemporal-native-r031-repaired/COURT-REPAIR.json",
)
CASES = (
    ("R32-01", "The current acceptance program is exact and receipt-addressable",
     "test_native_core_r032.NativeCoreR032Tests.test_r032_program_is_current"),
    ("R32-02", "The repaired r031 court and user evidence are carried in source",
     "test_native_core_r032.NativeCoreR032Tests.test_integrated_r031_repair_is_exact"),
    ("R32-03", "The archive native projection has an external root and denominator",
     "test_transtemporal_archive.TranstemporalArchiveTests.test_native_projection_and_cli_help_are_stable"),
    ("R32-04", "The C17 native core corresponds exactly to the Python fallback",
     "test_native_core_r032.NativeCoreR032Tests.test_native_c17_runtime_corresponds_exactly"),
    ("R32-05", "The fallback and compiler are accessible through public CLI and ABI",
     "test_native_core_r032.NativeCoreR032Tests.test_cli_and_abi_expose_portable_fallback"),
    ("R32-06", "Windows and WSL native witnesses bind the same result set",
     "test_native_core_r032.NativeCoreR032Tests.test_cross_platform_native_witnesses_match"),
    ("R32-07", "P/PPI C standards bind the native completion change denominator",
     "test_native_core_r032.NativeCoreR032Tests.test_pippi_c_preflight_covers_native_completion_denominator"),
    ("R32-08", "The operator court is builder-authored and not builder-executed",
     "test_native_core_r032.NativeCoreR032Tests.test_r032_operator_runner_is_reserved_for_user"),
)


def canonical(value: object) -> bytes:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode()


def seal(body: dict, field: str) -> dict:
    return {**body,field:hashlib.sha256(canonical(body)).hexdigest()}


def build() -> dict[str,dict]:
    rows=[]
    for relative in FILES:
        path=ROOT/relative
        if not path.is_file(): raise SystemExit("R032_DENOMINATOR_MEMBER_MISSING:"+relative)
        raw=path.read_bytes();rows.append({"path":relative,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)})
    denominator=seal({"schema":"mosaic.ucm.r032-source-denominator.v0.1",
        "predecessor_source_root":PREDECESSOR_SOURCE_ROOT,"members":rows,
        "member_count":len(rows),**BOUNDARY},"source_denominator_root")
    classes=["C_RUNTIME","DOCUMENTATION","PYTHON_TOOLING","TESTS"]
    checks=set(BASE_CHECKS)
    for change_class in classes:checks.update(CHECKS_BY_CLASS[change_class])
    preflight=build_c_change_preflight(
        proposal_id="UCM.R032.NATIVE_COMPLETION",
        subject_root=denominator["source_denominator_root"],
        source_manifest_root=PREDECESSOR_SOURCE_ROOT,
        language_standard="C17",
        compiler_profile_root=root({"dialect":"C17","warnings":"ERROR","optimization":"O2"}),
        architecture_contract_root=native_core_profile()["profile_root"],
        change_classes=classes,changed_paths=sorted(FILES),
        declared_write_paths=sorted(FILES),declared_check_ids=sorted(checks),
        requested_effect_classes=["LOCAL_PROCESS","READ_SOURCE","WRITE_WORKSPACE"],
        integration_mode="SIDECAR_PARTIAL",
        mediated_channels=sorted(CHANNELS-{"TOOL_DISPATCH"}),
        native_semantic_authority="NATIVE_C",python_role="AUTHORING_VERIFICATION_ONLY")
    if preflight["decision"]!="READY_FOR_QUICK_CHECKS":
        raise SystemExit("R032_C_PREFLIGHT_REFUSED:"+",".join(preflight["missing_check_ids"]))
    payload={"SOURCE-DENOMINATOR.json":denominator,"C-PREFLIGHT.json":preflight}
    requirements=[];acceptance=[];selections=[]
    for identifier,title,check in CASES:
        requirement=seal({"schema":"mosaic.ucm.r032-requirement.v0.1",
            "requirement_id":identifier,"title":title,
            "source_denominator_root":denominator["source_denominator_root"],
            "program_rule":"ONE_ACCEPTANCE_CASE_PER_IMPLEMENTATION_UNIT",**BOUNDARY},"requirement_root")
        case=seal({"schema":"mosaic.ucm.pippi-acceptance-case.v0.1",
            "acceptance_case_id":identifier,"requirement_root":requirement["requirement_root"],
            "subject_root":denominator["source_denominator_root"],
            "verification_surface":check,"expected_result_code":"PASS",
            "current_status":"UNMET",**BOUNDARY},"acceptance_case_root")
        selection=seal({"schema":"mosaic.ucm.pippi-work-selection.v0.1",
            "acceptance_case_root":case["acceptance_case_root"],
            "work_class":"DIRECT_ACCEPTANCE_CLOSURE","direct_closure_check_id":check,
            "infrastructure_block_root":None,"selection_basis":"DIRECT_CASE_CLOSURE",
            "implementation_effect_authorized":False,**BOUNDARY},"work_selection_root")
        payload[f"{identifier}-REQUIREMENT.json"]=requirement
        payload[f"{identifier}-ACCEPTANCE-CASE.json"]=case
        payload[f"{identifier}-WORK-SELECTION.json"]=selection
        requirements.append(requirement["requirement_root"]);acceptance.append(case["acceptance_case_root"]);selections.append(selection["work_selection_root"])
    windows=json.loads((ROOT/"evidence/native-core-r032/WINDOWS-NATIVE-CORE-WITNESS.json").read_text())
    wsl=json.loads((ROOT/"evidence/native-core-r032/WSL-NATIVE-CORE-WITNESS.json").read_text())
    if windows["result_set_root"]!=wsl["result_set_root"]:
        raise SystemExit("R032_NATIVE_PLATFORM_DIVERGENCE")
    program=seal({"schema":"mosaic.ucm.r032-native-completion-program.v0.1",
        "program_id":"UCM_R032_NATIVE_COMPLETION","version":"v0.1",
        "engineering_revision":"r032","predecessor_revision":"r031",
        "predecessor_source_root":PREDECESSOR_SOURCE_ROOT,
        "source_denominator_root":denominator["source_denominator_root"],
        "c_preflight_root":preflight["preflight_root"],
        "requirement_roots":requirements,"acceptance_case_roots":acceptance,
        "work_selection_roots":selections,
        "native_profile_root":native_core_profile()["profile_root"],
        "native_witness_roots":[windows["witness_root"],wsl["witness_root"]],
        "native_result_set_root":windows["result_set_root"],
        "required_portability_legs":["WINDOWS_NATIVE_C17","WSL_NATIVE_C17"],
        "operator_tier1_status":"NOT_RUN","publication_authorized":False,
        **BOUNDARY},"program_root")
    payload["PROGRAM.json"]=program
    return payload


def main() -> int:
    parser=argparse.ArgumentParser();parser.add_argument("--check",action="store_true");args=parser.parse_args();payload=build()
    if args.check:
        for name,value in payload.items():
            if not (OUT/name).is_file() or (OUT/name).read_bytes()!=canonical(value)+b"\n":
                raise SystemExit("R032_PROGRAM_DRIFT:"+name)
    else:
        OUT.mkdir(parents=True,exist_ok=True)
        for name,value in payload.items():(OUT/name).write_bytes(canonical(value)+b"\n")
    print(json.dumps({"status":"PASS","program_root":payload["PROGRAM.json"]["program_root"],"records":len(payload)},sort_keys=True))
    return 0


if __name__=="__main__":raise SystemExit(main())

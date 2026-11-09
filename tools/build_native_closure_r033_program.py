#!/usr/bin/env python3
"""Build the acceptance-bound r033 native-closure successor program."""
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

OUT = ROOT / "program/native-closure-r033"
PREDECESSOR_SOURCE_ROOT = "d52891c508a55ad7cff7ab2a201c9749407c5991bc04ac489d6a9ae12c9bc94d"
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
    "tests/test_native_core_r032.py", "tests/test_native_closure_r033.py",
    "tests/test_transtemporal_archive.py",
    "tests/test_pippi_cold_boot.py", "tests/test_public_surface.py",
    "tests/test_pippi_portfolio.py", "tests/test_pippi_release_packaging.py",
    "tests/test_public_release_qualification.py",
    "tools/build_native_core_r033_assets.py", "tools/run_native_core_r033_leg.py",
    "tools/build_native_closure_r033_program.py",
    "tools/build_native_closure_r033_operator_kit.py",
    "tools/run_public_release_qualification.py", "tools/release_common.py",
    "tools/refresh_release_identity.py",
    "tools/run_portability_leg.py", "tools/verify_pippi_cold_boot.py",
    "tools/verify_release.py", "tools/verify_runtime_tree.py",
    "operator/native-closure-r033/KIT-DECLARATION.json",
    "operator/native-closure-r033/RUN-TIER1.py",
    "tools/build_frozen_program_registry.py", "tools/build_frozen_operator_registry.py",
    "spec/UCM-NATIVE-CORE-PROFILE.json", "spec/UCM-NATIVE-CORE-CORPUS.json",
    "spec/UCM-NATIVE-CORE-BOUNDARY-CORPUS.json",
    "spec/FROZEN-PROGRAM-REGISTRY.json", "spec/FROZEN-OPERATOR-REGISTRY.json",
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
    "examples/native-core/ucm-boundary-max_registers.json",
    "examples/native-core/ucm-boundary-max_registers.ucln",
    "examples/native-core/ucm-boundary-max_instructions.json",
    "examples/native-core/ucm-boundary-max_instructions.ucln",
    "examples/native-core/ucm-boundary-max_stack.json",
    "examples/native-core/ucm-boundary-max_stack.ucln",
    "examples/native-core/ucm-boundary-max_steps.json",
    "examples/native-core/ucm-boundary-max_steps.ucln",
    "evidence/native-core-r033/WINDOWS-NATIVE-CORE-WITNESS.json",
    "evidence/native-core-r033/WSL-NATIVE-CORE-WITNESS.json",
    "release/PREDECESSOR-r032-QUALIFICATION.json",
    "release/PREDECESSOR-r032-RELEASE-IDENTITY.json",
    "review/r032/INDEPENDENT-REPORT.md", "review/r032/INDEPENDENT-FINDINGS.json",
    "review/r032/INDEPENDENT-RECOMPUTE.json", "review/r032/REVIEWER-EVIDENCE.zip",
    "review/r032/USER-TIER1-PASS-EVIDENCE.zip", "review/r032/PROVENANCE.json",
)
CASES = (
    ("R33-01", "The full declared native profile corresponds at its boundaries",
     "test_native_closure_r033.NativeClosureR033Tests.test_declared_profile_limits_correspond_exactly"),
    ("R33-02", "CLI fallback resolves the exact repository source hermetically",
     "test_native_closure_r033.NativeClosureR033Tests.test_cli_fallback_resolves_exact_repository_source"),
    ("R33-03", "Archive verification binds external rows and denominator",
     "test_transtemporal_archive.TranstemporalArchiveTests.test_native_projection_and_cli_help_are_stable"),
    ("R33-04", "Native projections require external pins and canonical bytes",
     "test_native_closure_r033.NativeClosureR033Tests.test_native_projection_is_externally_pinned_and_canonical"),
    ("R33-05", "r031 and r032 program, court, review and operator history are frozen",
     "test_native_closure_r033.NativeClosureR033Tests.test_r031_and_r032_programs_and_courts_are_frozen"),
    ("R33-06", "Windows and WSL witnesses cover all nine programs",
     "test_native_closure_r033.NativeClosureR033Tests.test_r033_boundary_assets_are_exact"),
    ("R33-07", "The operator court is builder-authored and not builder-executed",
     "test_native_closure_r033.NativeClosureR033Tests.test_r033_operator_runner_is_reserved_for_user"),
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
        if not path.is_file(): raise SystemExit("R033_DENOMINATOR_MEMBER_MISSING:"+relative)
        raw=path.read_bytes();rows.append({"path":relative,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)})
    denominator=seal({"schema":"mosaic.ucm.r033-source-denominator.v0.1",
        "predecessor_source_root":PREDECESSOR_SOURCE_ROOT,"members":rows,
        "member_count":len(rows),**BOUNDARY},"source_denominator_root")
    classes=["C_RUNTIME","DOCUMENTATION","PYTHON_TOOLING","TESTS"]
    checks=set(BASE_CHECKS)
    for change_class in classes:checks.update(CHECKS_BY_CLASS[change_class])
    preflight=build_c_change_preflight(
        proposal_id="UCM.R033.NATIVE_CLOSURE",
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
        raise SystemExit("R033_C_PREFLIGHT_REFUSED:"+",".join(preflight["missing_check_ids"]))
    payload={"SOURCE-DENOMINATOR.json":denominator,"C-PREFLIGHT.json":preflight}
    requirements=[];acceptance=[];selections=[]
    for identifier,title,check in CASES:
        requirement=seal({"schema":"mosaic.ucm.r033-requirement.v0.1",
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
    windows=json.loads((ROOT/"evidence/native-core-r033/WINDOWS-NATIVE-CORE-WITNESS.json").read_text())
    wsl=json.loads((ROOT/"evidence/native-core-r033/WSL-NATIVE-CORE-WITNESS.json").read_text())
    if windows["result_set_root"]!=wsl["result_set_root"]:
        raise SystemExit("R033_NATIVE_PLATFORM_DIVERGENCE")
    program=seal({"schema":"mosaic.ucm.r033-native-closure-program.v0.1",
        "program_id":"UCM_R033_NATIVE_CLOSURE","version":"v0.1",
        "engineering_revision":"r033","predecessor_revision":"r032",
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
                raise SystemExit("R033_PROGRAM_DRIFT:"+name)
    else:
        OUT.mkdir(parents=True,exist_ok=True)
        for name,value in payload.items():(OUT/name).write_bytes(canonical(value)+b"\n")
    print(json.dumps({"status":"PASS","program_root":payload["PROGRAM.json"]["program_root"],"records":len(payload)},sort_keys=True))
    return 0


if __name__=="__main__":raise SystemExit(main())

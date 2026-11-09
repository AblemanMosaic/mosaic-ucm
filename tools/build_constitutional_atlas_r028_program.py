#!/usr/bin/env python3
"""Build the fixed-denominator r028 constitutional-atlas program."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ucm.pippi_work_units import build_acceptance_case, build_work_selection  # noqa: E402

OUT = ROOT / "program/constitutional-atlas-r028"
BOUNDARY = {"standing":"INFORMATION_ONLY", "authority_effect":"NONE",
            "real_a5":False, "g0":"CLOSED"}
SOURCE_PATHS = (
    "src/ucm/pippi_constitution.py", "src/ucm/pippi_credentials.py",
    "src/ucm/pippi_adaptive.py", "src/ucm/pippi_cli.py",
    "src/ucm/pippi_dashboard.py", "src/ucm/pippi_portfolio.py",
    "src/ucm/amcas_parity.py",
    "src/ucm/system.py", "src/ucm/capabilities.py", "src/ucm/__init__.py",
    "tools/build_pippi_constitutional_contracts.py",
    "tools/build_pippi_adaptive_contracts.py", "tools/build_pippi_cold_boot.py",
    "tools/prepare_release_contracts.py", "tools/build_maturity_evolution_assets.py",
    "tools/build_public_vocabulary.py", "tools/build_ccp_courthouse_program.py",
    "tools/build_constitutional_atlas_r028_program.py",
    "tools/build_constitutional_atlas_r028_operator_kit.py",
    "tools/build_r028_review_transport.py",
    "tools/refresh_release_identity.py",
    "tools/release_common.py", "tools/verify_pippi_cold_boot.py",
    "tools/verify_release.py", "tools/run_portability_leg.py",
    "tools/run_public_release_qualification.py",
    "tests/test_pippi_constitution.py", "tests/test_pippi_constitutional_contracts.py",
    "tests/test_pippi_adaptive.py", "tests/test_pippi_cold_boot.py",
    "tests/test_pippi_portfolio.py", "tests/test_pippi_release_packaging.py",
    "tests/test_public_release_qualification.py",
    "tests/test_public_surface.py",
    "tests/test_constitutional_atlas_r028_program.py",
    "tests/test_constitutional_atlas_r028_packaging.py",
    "spec/PIPPI-CONSTITUTIONAL-STANDARDS-ATLAS.json",
    "spec/PIPPI-PIPELINE-MODEL.json", "spec/PIPPI-ADAPTIVE-COLD-BOOT-CONTRACT.json",
    "spec/PIPPI-CAPABILITY-SURFACE-REGISTRY.json",
    "spec/ucm-system-registry.json", "spec/ABI-STABILITY.json",
    "spec/AGENT-LOOP-CONTRACT.json",
    "spec/product-profiles/PROFILE-REGISTRY.json",
    "spec/product-profiles/AUTHORING-PROFILE.json",
    "spec/product-profiles/COMPATIBILITY-PROFILE.json",
    "spec/product-profiles/OPERATIONAL-PROFILE.json",
    "spec/product-profiles/VERIFY_ONLY-PROFILE.json",
    "completions/pippi.bash", "completions/pippi.bash.json",
    "completions/pippi.zsh", "completions/pippi.zsh.json",
    "completions/pippi.fish", "completions/pippi.fish.json",
    "completions/pippi.ps1", "completions/pippi.ps1.json",
    "completions/ucm.bash", "completions/ucm.bash.json",
    "completions/ucm.zsh", "completions/ucm.zsh.json",
    "completions/ucm.fish", "completions/ucm.fish.json",
    "completions/ucm.ps1", "completions/ucm.ps1.json",
    "skill/ucm-pippi-mediated-agent/SKILL.md",
    "skill/ucm-pippi-mediated-agent/references/constitutional-atlas.md",
    "docs/PIPPI-ADAPTIVE-COLD-BOOT.md",
    "docs/PIPPI-CONSTITUTIONAL-ATLAS.md", "docs/R28-REVIEW-WORK-ORDER.md",
    "docs/ACTIVE-SURFACE-GUIDE.md", "docs/CAPABILITY-SURFACES.md",
    "docs/SYSTEM-CATALOG.md",
    "historical/ccp-courthouse-r015/src/ucm/__init__.py",
    "install/INSTALL-PIPPI.ps1", "install/INSTALL-PIPPI.vbs",
    "portable/BOOT/START-HERE.md",
    "operator/constitutional-atlas-r028/KIT-DECLARATION.json",
    "operator/constitutional-atlas-r028/RUN-TIER1.py",
    "PIPPI-AGENT-ACCESS.md", "PIPPI-START-HERE.md", "README.md",
    "VERIFY.py",
)
CASES = (
    ("R28-01", "Every mediation rule is navigable with co-projections and ablation failure modes",
     "test_pippi_constitution.PippiConstitutionTests.test_atlas_has_total_mediation_rule_denominator"),
    ("R28-02", "Pipeline states expose exact governed transitions and CCP gates",
     "test_pippi_constitution.PippiConstitutionTests.test_pipeline_model_is_explainable_and_non_authorizing"),
    ("R28-03", "Context selection exposes scenario, variables, rules, and reason paths",
     "test_pippi_constitution.PippiConstitutionTests.test_context_explanation_shows_exact_reasons_and_variables"),
    ("R28-04", "MosaicID and DKN bind collaborator provenance without granting authority",
     "test_pippi_constitution.PippiConstitutionTests.test_collaborator_binding_uses_verified_passport_and_dkn"),
    ("R28-05", "Signed changes bind predecessor, delta, standards, acceptance, identity, and revision",
     "test_pippi_constitution.PippiConstitutionTests.test_signed_change_capsule_binds_base_delta_identity_and_dkn"),
    ("R28-06", "Credential secrets stay encrypted local while portable records carry opaque references",
     "test_pippi_constitution.PippiConstitutionTests.test_local_credential_vault_is_encrypted_and_nonportable"),
    ("R28-07", "Storage-neutral publication and retrieval retain artifact and signer custody",
     "test_pippi_constitution.PippiConstitutionTests.test_storage_receipt_is_signed_and_storage_never_becomes_identity"),
    ("R28-08", "Generated ABI CLI skill and cold-boot contracts remain one rooted interface",
     "test_pippi_release_packaging.PippiReleasePackagingTests.test_generated_adaptive_contracts_match_live_registries"),
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def records() -> dict[str, dict]:
    members = [{"path": path, "bytes": (ROOT/path).stat().st_size,
                "sha256": sha((ROOT/path).read_bytes())} for path in SOURCE_PATHS]
    denominator_body = {"schema":"mosaic.ucm.r028-source-denominator.v0.1",
                        "members":members, "member_count":len(members), **BOUNDARY}
    denominator = {**denominator_body,
                   "source_denominator_root":sha(canonical(denominator_body))}
    predecessor = json.loads((ROOT/"release/PREDECESSOR-r027-QUALIFICATION.json").read_text())
    result = {"SOURCE-DENOMINATOR.json": denominator}
    requirement_roots=[];case_roots=[];selection_roots=[]
    for case_id,title,test_id in CASES:
        requirement_body={"schema":"mosaic.ucm.r028-requirement.v0.1",
            "requirement_id":case_id,"title":title,
            "source_denominator_root":denominator["source_denominator_root"],
            "program_rule":"ONE_ACCEPTANCE_CASE_PER_IMPLEMENTATION_UNIT",**BOUNDARY}
        requirement={**requirement_body,"requirement_root":sha(canonical(requirement_body))}
        case=build_acceptance_case(acceptance_case_id=case_id,
            subject_root=predecessor["source_manifest_root"],
            requirement_root=requirement["requirement_root"],verification_surface=test_id,
            expected_result_code="PASS",current_status="UNMET")
        selection=build_work_selection(acceptance_case=case,
            work_class="DIRECT_ACCEPTANCE_CLOSURE",direct_closure_check_id=test_id,
            infrastructure_block=None)
        result[f"{case_id}-REQUIREMENT.json"]=requirement
        result[f"{case_id}-ACCEPTANCE-CASE.json"]=case
        result[f"{case_id}-WORK-SELECTION.json"]=selection
        requirement_roots.append(requirement["requirement_root"])
        case_roots.append(case["acceptance_case_root"])
        selection_roots.append(selection["work_selection_root"])
    body={"schema":"mosaic.ucm.r028-constitutional-atlas-program.v0.1",
          "program_id":"UCM_R028_CONSTITUTIONAL_ATLAS", "version":"v0.1",
          "engineering_revision":"r028", "predecessor_revision":"r027",
          "predecessor_source_root":predecessor["source_manifest_root"],
          "predecessor_qualification_root":predecessor["root"],
          "source_denominator_root":denominator["source_denominator_root"],
          "requirement_roots":requirement_roots,"acceptance_case_roots":case_roots,
          "work_selection_roots":selection_roots,
          "required_portability_legs":["WINDOWS_NATIVE","WSL_NATIVE"],
          "operator_tier1_status":"NOT_RUN","publication_authorized":False,**BOUNDARY}
    result["PROGRAM.json"]={**body,"program_root":sha(canonical(body))}
    return result


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write",action="store_true");group.add_argument("--check",action="store_true")
    args=parser.parse_args();mismatches=[]
    for name,value in records().items():
        path=OUT/name;raw=canonical(value)+b"\n"
        if args.write:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        elif not path.is_file() or path.read_bytes()!=raw:mismatches.append(name)
    print(json.dumps({"status":"PASS" if not mismatches else "REFUSED",
        "records":len(records()),"mismatches":mismatches,**BOUNDARY},sort_keys=True))
    return 0 if not mismatches else 3


if __name__=="__main__":raise SystemExit(main())

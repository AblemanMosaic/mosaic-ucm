#!/usr/bin/env python3
"""Build the fixed-denominator r029 collaboration-integrity program."""
from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ucm.pippi_work_units import build_acceptance_case, build_work_selection  # noqa: E402

OUT = ROOT / "program/collaboration-integrity-r029"
BOUNDARY = {"standing":"INFORMATION_ONLY", "authority_effect":"NONE",
            "real_a5":False, "g0":"CLOSED"}
SOURCE_PATHS = (
    "src/ucm/pippi_constitution.py", "src/ucm/pippi_credentials.py",
    "src/ucm/pippi_cli.py", "src/ucm/system.py", "src/ucm/capabilities.py",
    "src/ucm/__init__.py", "tests/test_pippi_constitution.py",
    "tests/test_pippi_cold_boot.py",
    "tests/test_ccp_admissibility_positive.py",
    "tools/build_pippi_constitutional_contracts.py",
    "tools/build_pippi_adaptive_contracts.py", "tools/build_pippi_cold_boot.py",
    "tools/build_collaboration_integrity_r029_program.py",
    "tools/build_collaboration_integrity_r029_operator_kit.py",
    "tools/build_r029_review_transport.py",
    "tools/refresh_release_identity.py", "docs/PIPPI-CONSTITUTIONAL-ATLAS.md",
    "skill/ucm-pippi-mediated-agent/SKILL.md",
    "skill/ucm-pippi-mediated-agent/references/constitutional-atlas.md",
    "PIPPI-AGENT-ACCESS.md",
    "docs/R29-REVIEW-WORK-ORDER.md",
    "spec/PIPPI-CONSTITUTIONAL-STANDARDS-ATLAS.json",
    "spec/PIPPI-PIPELINE-MODEL.json", "spec/PIPPI-ADAPTIVE-COLD-BOOT-CONTRACT.json",
    "spec/PIPPI-CAPABILITY-SURFACE-REGISTRY.json",
    "release/PREDECESSOR-r028-RELEASE-IDENTITY.json",
    "release/PREDECESSOR-r028-QUALIFICATION.json",
    "review/r028-independent/REPORT.md", "review/r028-independent/FINDINGS.json",
    "review/r028-independent/RECOMPUTE.json",
    "review/r028-independent/REVIEWER-EVIDENCE.zip",
    "review/r028-independent/PROVENANCE.json",
    "review/r028-operator/OPERATOR-EVIDENCE.zip",
    "review/r028-operator/PROVENANCE.json",
    "operator/collaboration-integrity-r029/KIT-DECLARATION.json",
    "operator/collaboration-integrity-r029/RUN-TIER1.py",
    "tests/test_collaboration_integrity_r029_program.py",
)
CASES = (
    ("R29-01", "Signer identities are derived from the exact Ed25519 verification key",
     "test_pippi_constitution.PippiConstitutionTests.test_signed_change_capsule_binds_base_delta_identity_and_dkn"),
    ("R29-02", "Publication and retrieval bind verified receipts to actual artifact bytes",
     "test_pippi_constitution.PippiConstitutionTests.test_storage_receipt_verifies_actual_artifact_and_key_bound_identities"),
    ("R29-03", "CCP-required transitions derive readiness from a complete validated evaluation",
     "test_pippi_constitution.PippiConstitutionTests.test_ccp_binding_holds_nonadmitted_transition"),
    ("R29-04", "Local credential writes use fresh randomness and exclusive non-link custody",
     "test_pippi_constitution.PippiConstitutionTests.test_local_credential_vault_is_encrypted_and_nonportable"),
    ("R29-05", "The pipeline terminal model and cold-boot skill closure are complete",
     "test_pippi_cold_boot.PippiColdBootTests.test_deterministic_cold_boot_and_nested_runtime_verification"),
    ("R29-06", "Generated CLI ABI registry and documentation remain one interface",
     "test_pippi_release_packaging.PippiReleasePackagingTests.test_generated_adaptive_contracts_match_live_registries"),
    ("R29-07", "The r028 predecessor review and operator evidence remain exact and separate",
     "test_collaboration_integrity_r029_program.CollaborationIntegrityR029ProgramTests.test_r028_returns_are_exact_and_provenanced"),
)

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()

def sha(raw): return hashlib.sha256(raw).hexdigest()

def records():
    members=[{"path":p,"bytes":(ROOT/p).stat().st_size,"sha256":sha((ROOT/p).read_bytes())}
             for p in SOURCE_PATHS]
    db={"schema":"mosaic.ucm.r029-source-denominator.v0.1","members":members,
        "member_count":len(members),**BOUNDARY}
    denominator={**db,"source_denominator_root":sha(canonical(db))}
    predecessor=json.loads((ROOT/"release/PREDECESSOR-r028-QUALIFICATION.json").read_text())
    result={"SOURCE-DENOMINATOR.json":denominator}; requirements=[]; cases=[]; selections=[]
    for case_id,title,test_id in CASES:
        rb={"schema":"mosaic.ucm.r029-requirement.v0.1","requirement_id":case_id,
            "title":title,"source_denominator_root":denominator["source_denominator_root"],
            "program_rule":"ONE_ACCEPTANCE_CASE_PER_IMPLEMENTATION_UNIT",**BOUNDARY}
        requirement={**rb,"requirement_root":sha(canonical(rb))}
        case=build_acceptance_case(acceptance_case_id=case_id,
            subject_root=predecessor["source_manifest_root"],
            requirement_root=requirement["requirement_root"], verification_surface=test_id,
            expected_result_code="PASS", current_status="UNMET")
        selection=build_work_selection(acceptance_case=case,
            work_class="DIRECT_ACCEPTANCE_CLOSURE", direct_closure_check_id=test_id,
            infrastructure_block=None)
        result[f"{case_id}-REQUIREMENT.json"]=requirement
        result[f"{case_id}-ACCEPTANCE-CASE.json"]=case
        result[f"{case_id}-WORK-SELECTION.json"]=selection
        requirements.append(requirement["requirement_root"]); cases.append(case["acceptance_case_root"])
        selections.append(selection["work_selection_root"])
    body={"schema":"mosaic.ucm.r029-collaboration-integrity-program.v0.1",
          "program_id":"UCM_R029_COLLABORATION_INTEGRITY","version":"v0.1",
          "engineering_revision":"r029","predecessor_revision":"r028",
          "predecessor_source_root":predecessor["source_manifest_root"],
          "predecessor_qualification_root":predecessor["root"],
          "source_denominator_root":denominator["source_denominator_root"],
          "requirement_roots":requirements,"acceptance_case_roots":cases,
          "work_selection_roots":selections,"required_portability_legs":["WINDOWS_NATIVE","WSL_NATIVE"],
          "operator_tier1_status":"NOT_RUN","publication_authorized":False,**BOUNDARY}
    result["PROGRAM.json"]={**body,"program_root":sha(canonical(body))}
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--write",action="store_true");g.add_argument("--check",action="store_true");a=p.parse_args()
    mismatches=[]
    for name,value in records().items():
        path=OUT/name;raw=canonical(value)+b"\n"
        if a.write:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        elif not path.is_file() or path.read_bytes()!=raw:mismatches.append(name)
    print(json.dumps({"status":"PASS" if not mismatches else "REFUSED","records":len(records()),
                      "mismatches":mismatches,**BOUNDARY},sort_keys=True))
    return 0 if not mismatches else 3

if __name__=="__main__":raise SystemExit(main())

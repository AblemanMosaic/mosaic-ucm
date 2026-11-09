#!/usr/bin/env python3
"""Build the fixed-denominator r030 collaboration-closure program."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ucm.pippi_work_units import build_acceptance_case, build_work_selection  # noqa: E402
from ucm.program_history import check_frozen_program_directory  # noqa: E402

OUT = ROOT / "program/collaboration-closure-r030"
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
SOURCE_PATHS = (
    "src/ucm/pippi_constitution.py", "src/ucm/pippi_credentials.py",
    "src/ucm/pippi_cli.py", "src/ucm/pippi_adaptive.py", "src/ucm/system.py",
    "src/ucm/capabilities.py", "src/ucm/__init__.py",
    "tests/test_pippi_constitution.py",
    "tests/test_collaboration_integrity_r029_program.py",
    "tests/test_collaboration_closure_r030_program.py",
    "tools/build_frozen_program_registry.py", "tools/build_frozen_operator_registry.py",
    "tools/build_collaboration_closure_r030_program.py",
    "tools/build_collaboration_closure_r030_operator_kit.py",
    "tools/build_r030_review_transport.py",
    "spec/FROZEN-PROGRAM-REGISTRY.json", "spec/FROZEN-OPERATOR-REGISTRY.json",
    "skill/ucm-pippi-mediated-agent/SKILL.md",
    "skill/ucm-pippi-mediated-agent/references/constitutional-atlas.md",
    "docs/R30-REVIEW-WORK-ORDER.md",
    "release/PREDECESSOR-r029-RELEASE-IDENTITY.json",
    "release/PREDECESSOR-r029-QUALIFICATION.json",
    "review/r029-independent/REPORT.md", "review/r029-independent/FINDINGS.json",
    "review/r029-independent/RECOMPUTE.json",
    "review/r029-independent/REVIEWER-EVIDENCE.zip",
    "review/r029-independent/PROVENANCE.json",
    "review/r029-operator/OPERATOR-EVIDENCE.zip",
    "review/r029-operator/PROVENANCE.json",
    "operator/collaboration-closure-r030/KIT-DECLARATION.json",
    "operator/collaboration-closure-r030/RUN-TIER1.py",
)
CASES = (
    ("R30-01", "The court distinguishes malformed and fully resealed CCP mutations",
     "test_pippi_constitution.PippiConstitutionTests.test_ccp_binding_holds_nonadmitted_transition"),
    ("R30-02", "Credential envelopes are validated before filesystem mutation",
     "test_pippi_constitution.PippiConstitutionTests.test_local_credential_vault_is_encrypted_and_nonportable"),
    ("R30-03", "Publication signing revalidates credential-free storage locators",
     "test_pippi_constitution.PippiConstitutionTests.test_storage_receipt_verifies_actual_artifact_and_key_bound_identities"),
    ("R30-04", "Retrieval receipts have a public post-hoc validator bound to publication",
     "test_pippi_constitution.PippiConstitutionTests.test_storage_receipt_verifies_actual_artifact_and_key_bound_identities"),
    ("R30-05", "r027 through r029 programs and courts remain frozen",
     "test_collaboration_closure_r030_program.CollaborationClosureR030ProgramTests.test_predecessor_programs_and_courts_are_frozen"),
    ("R30-06", "r029 review and user-run HOLD evidence remain exact and separate",
     "test_collaboration_closure_r030_program.CollaborationClosureR030ProgramTests.test_r029_returns_are_exact_and_separate"),
)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def records():
    members = [{"path": path, "bytes": (ROOT / path).stat().st_size,
                "sha256": sha((ROOT / path).read_bytes())} for path in SOURCE_PATHS]
    denominator_body = {"schema": "mosaic.ucm.r030-source-denominator.v0.1",
                        "members": members, "member_count": len(members), **BOUNDARY}
    denominator = {**denominator_body,
                   "source_denominator_root": sha(canonical(denominator_body))}
    predecessor = json.loads(
        (ROOT / "release/PREDECESSOR-r029-QUALIFICATION.json").read_text())
    result = {"SOURCE-DENOMINATOR.json": denominator}
    requirements, cases, selections = [], [], []
    for case_id, title, test_id in CASES:
        requirement_body = {"schema": "mosaic.ucm.r030-requirement.v0.1",
            "requirement_id": case_id, "title": title,
            "source_denominator_root": denominator["source_denominator_root"],
            "program_rule": "ONE_ACCEPTANCE_CASE_PER_IMPLEMENTATION_UNIT", **BOUNDARY}
        requirement = {**requirement_body,
                       "requirement_root": sha(canonical(requirement_body))}
        acceptance = build_acceptance_case(
            acceptance_case_id=case_id, subject_root=predecessor["source_manifest_root"],
            requirement_root=requirement["requirement_root"],
            verification_surface=test_id, expected_result_code="PASS",
            current_status="UNMET")
        selection = build_work_selection(
            acceptance_case=acceptance, work_class="DIRECT_ACCEPTANCE_CLOSURE",
            direct_closure_check_id=test_id, infrastructure_block=None)
        result[f"{case_id}-REQUIREMENT.json"] = requirement
        result[f"{case_id}-ACCEPTANCE-CASE.json"] = acceptance
        result[f"{case_id}-WORK-SELECTION.json"] = selection
        requirements.append(requirement["requirement_root"])
        cases.append(acceptance["acceptance_case_root"])
        selections.append(selection["work_selection_root"])
    body = {"schema": "mosaic.ucm.r030-collaboration-closure-program.v0.1",
        "program_id": "UCM_R030_COLLABORATION_CLOSURE", "version": "v0.1",
        "engineering_revision": "r030", "predecessor_revision": "r029",
        "predecessor_source_root": predecessor["source_manifest_root"],
        "predecessor_qualification_root": predecessor["root"],
        "source_denominator_root": denominator["source_denominator_root"],
        "requirement_roots": requirements, "acceptance_case_roots": cases,
        "work_selection_roots": selections,
        "required_portability_legs": ["WINDOWS_NATIVE", "WSL_NATIVE"],
        "operator_tier1_status": "NOT_RUN",
        "predecessor_operator_result": "HOLD_FOR_REPAIR_COURT_ORACLE_DEFECT",
        "publication_authorized": False, **BOUNDARY}
    result["PROGRAM.json"] = {**body, "program_root": sha(canonical(body))}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        registry = json.loads((ROOT / "spec/FROZEN-PROGRAM-REGISTRY.json").read_text())
        frozen = check_frozen_program_directory(
            source_root=ROOT, registry=registry,
            directory="program/collaboration-closure-r030")
        print(json.dumps({"status": frozen["status"],
                          "records": frozen["member_count"],
                          "directory_root": frozen["directory_root"], **BOUNDARY},
                         sort_keys=True))
        return 0
    mismatches = []
    expected = records()
    for name, value in expected.items():
        path = OUT / name
        raw = canonical(value) + b"\n"
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        elif not path.is_file() or path.read_bytes() != raw:
            mismatches.append(name)
    print(json.dumps({"status": "PASS" if not mismatches else "REFUSED",
                      "records": len(expected), "mismatches": mismatches,
                      **BOUNDARY}, sort_keys=True))
    return 0 if not mismatches else 3


if __name__ == "__main__":
    raise SystemExit(main())

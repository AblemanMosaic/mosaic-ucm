#!/usr/bin/env python3
"""Build or read-only check the eight-case P/PPI CMBA-composite r036 program.

These are construction selections against the frozen r035 subject.  Actual
qualification results and operator evidence are separate, later records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "program/cmba-composite-r036"
PREDECESSOR_SOURCE_ROOT = "b91652b352cbf12b9a0e4083121439f19ae96ca6224caadab874f8f30c5d29aa"
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
FILES = (
    "README.md", "PIPPI-AGENT-ACCESS.md",
    "docs/PIPPI-COMMON-TURN-RECORDS.md", "docs/PIPPI-CMBA-COMPOSITE.md", "docs/PIPPI.md",
    "docs/R36-REVIEW-WORK-ORDER.md",
    "skill/ucm-pippi-mediated-agent/SKILL.md",
    "skill/ucm-pippi-mediated-agent/references/common-turn-records.md",
    "src/ucm/__init__.py", "src/ucm/system.py", "src/ucm/capabilities.py",
    "src/ucm/pippi_adaptive.py", "src/ucm/pippi_cli.py",
    "src/ucm/pippi_turn_record.py", "src/ucm/pippi_cmba.py", "src/ucm/pippi_cmba_composite.py",
    "src/ucm/pippi_constitution.py", "src/ucm/process_governance.py",
    "src/ucm/ccp_admissibility.py", "src/ucm/operation_gateway.py",
    "src/ucm/operation_proofs.py", "src/ucm/thr_cas.py",
    "tests/test_pippi_cmba_composite_positive.py",
    "tests/test_r036_closure.py",
    "tools/build_cmba_composite_r036_program.py",
    "tools/build_cmba_composite_r036_portability.py",
    "tools/run_cmba_composite_r036_positive.py",
    "tools/freeze_cmba_composite_r036.py",
    "tools/build_cmba_composite_r036_operator_kit.py",
    "tools/cmba_composite_r036_court.py",
    "tools/qualify_cmba_composite_r036.py",
    "tools/build_r036_review_transport.py",
    "tools/release_common.py", "tools/build_pippi_adaptive_contracts.py",
    "tools/check_active_generated_contracts.py",
    "vendor/optional-packs/cmba/cmba_core-0.1.0a7-py3-none-any.whl",
)
CASES = (
    ("R036.PROFILE_CONTRACT", "Composite profile contract",
     "Publish one exact profile that enumerates CMBA, DKN, THR, CHC, CCP and conditional G1/G2/G3 co-projections, preserves root distinction, and grants no authority."),
    ("R036.OBSERVATIONAL", "Observational composite",
     "Revalidate the exact common turn, CMBA assessment, DKN locality, CHC correspondence and CCP evaluation, then build separated THR commitments without inventing effect history."),
    ("R036.EFFECT_BOUND", "Effect-bound composite",
     "Require an admitted CCP decision, a validated CCP-bound gateway history, an operation request bound to the exact turn, and complete re-derived G1/G2/G3 receipts for terminal status."),
    ("R036.THR_SEPARATION", "Separated THR domains",
     "Commit exact state, admissibility, meaning, locality and receipt identity separately and refuse a CHC correspondence that names another THR contract."),
    ("R036.CLI_ABI", "Public CLI and ABI parity",
     "Expose discovery, build and verification through the capability registry and P/PPI CLI from one generated route map without creating hub state during profile discovery."),
    ("R036.DOCUMENTATION", "Operator and skill guidance",
     "Explain both modes, every claim ceiling, the exact THR mapping and why the composite cannot replace CCP or the Operational Gateway."),
    ("R036.GENERATED_PARITY", "Active generated-contract parity",
     "Regenerate and check ABI stability, profiles, adaptive contracts and shell completions from the r036 live registry."),
    ("R036.PREDECESSOR_HISTORY", "Frozen predecessor continuity",
     "Retain the exact r035 baseline and existing journal, program and operator records as predecessor history; "
     "construct only new r036 program records, preserve public v0.1, and record construction selections without "
     "claiming that acceptance cases have closed or that independent review has occurred."),
)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def seal(body, field):
    return {**body, field: hashlib.sha256(canonical(body)).hexdigest()}


def build():
    """Return deterministic records without changing the source or output tree."""
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT / "src"))
    from ucm.pippi_work_units import (build_acceptance_case, build_work_selection,
                                       validate_acceptance_case)
    import ucm
    if Path(ucm.__file__).resolve() != ROOT / "src/ucm/__init__.py":
        raise SystemExit("R036_PROGRAM_SUBJECT_IMPORT_ORIGIN_MISMATCH")
    if len(CASES) != 8 or len({case[0] for case in CASES}) != 8:
        raise SystemExit("R036_PROGRAM_CASE_DENOMINATOR_INVALID")
    if len(FILES) != len(set(FILES)) or any(name.startswith("program/cmba-composite-r036/") for name in FILES):
        raise SystemExit("R036_PROGRAM_INPUT_DENOMINATOR_INVALID")
    members = []
    for name in sorted(FILES):
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            raise SystemExit("R036_PROGRAM_INPUT_MISSING_OR_ALIAS:" + name)
        raw = path.read_bytes()
        members.append({"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    denominator = seal({"schema": "mosaic.ucm.r036-CMBA-composite-source-denominator.v0.1",
        "predecessor_source_root": PREDECESSOR_SOURCE_ROOT,
        "members": members, "member_count": len(members),
        "scope": "EXACT_IMPLEMENTATION_DOCUMENTATION_SKILL_AND_OPTIONAL_CMBA_INPUTS",
        "generated_program_outputs_excluded": True, **BOUNDARY}, "source_denominator_root")
    payload = {"SOURCE-DENOMINATOR.json": denominator}
    entries = []
    for index, (check_id, title, requirement_text) in enumerate(CASES, 1):
        identifier = f"R036-{index:02d}"
        requirement = seal({"schema": "mosaic.ucm.r036-CMBA-composite-requirement.v0.1",
            "requirement_id": identifier, "title": title, "requirement": requirement_text,
            "predecessor_source_root": PREDECESSOR_SOURCE_ROOT,
            "source_denominator_root": denominator["source_denominator_root"],
            "direct_closure_check_id": check_id,
            "program_rule": "ONE_ACCEPTANCE_CASE_PER_IMPLEMENTATION_UNIT",
            "status": "CONSTRUCTION_SELECTION_ONLY", "acceptance_case_closed": False,
            "effect_authorized": False, **BOUNDARY}, "requirement_root")
        case = build_acceptance_case(acceptance_case_id=identifier,
            subject_root=PREDECESSOR_SOURCE_ROOT, requirement_root=requirement["requirement_root"],
            verification_surface=check_id, expected_result_code="PASS", current_status="UNMET")
        validate_acceptance_case(case)
        selection = build_work_selection(acceptance_case=case,
            work_class="DIRECT_ACCEPTANCE_CLOSURE", direct_closure_check_id=check_id,
            infrastructure_block=None)
        request = {"acceptance_case": case, "work_class": "DIRECT_ACCEPTANCE_CLOSURE",
                   "direct_closure_check_id": check_id, "infrastructure_block": None}
        if build_work_selection(**request) != selection or selection["implementation_effect_authorized"]:
            raise SystemExit("R036_PROGRAM_SELECTION_REBUILD_MISMATCH")
        payload[f"{identifier}-REQUIREMENT.json"] = requirement
        payload[f"{identifier}-ACCEPTANCE-CASE.json"] = case
        payload[f"{identifier}-SELECTION-INPUT.json"] = request
        payload[f"{identifier}-WORK-SELECTION.json"] = selection
        entries.append({"acceptance_case_id": identifier,
            "requirement_root": requirement["requirement_root"],
            "acceptance_case_root": case["acceptance_case_root"],
            "work_selection_root": selection["work_selection_root"],
            "direct_closure_check_id": check_id,
            "work_class": "DIRECT_ACCEPTANCE_CLOSURE", "acceptance_case_closed": False})
    inventory = seal({"schema": "mosaic.ucm.r036-CMBA-composite-work-selection-inventory.v0.1",
        "program_id": "UCM_R036_CMBA_COMPOSITE", "version": "v0.1", "engineering_revision": "r036",
        "subject_root": PREDECESSOR_SOURCE_ROOT,
        "predecessor_revision": "r035", "predecessor_source_root": PREDECESSOR_SOURCE_ROOT,
        "source_denominator_root": denominator["source_denominator_root"],
        "implementation_members": members, "implementation_member_count": len(members),
        "selections": entries, "acceptance_case_count": len(entries),
        "status": "CONSTRUCTION_SELECTION_ONLY", "acceptance_case_closed": False,
        "capability_granted": False, "effect_authorized": False, **BOUNDARY}, "inventory_root")
    payload["WORK-SELECTION-INVENTORY.json"] = inventory
    payload["PROGRAM.json"] = seal({"schema": "mosaic.ucm.r036-CMBA-composite-program.v0.1",
        "program_id": "UCM_R036_CMBA_COMPOSITE", "version": "v0.1", "engineering_revision": "r036",
        "predecessor_revision": "r035", "predecessor_source_root": PREDECESSOR_SOURCE_ROOT,
        "source_denominator_root": denominator["source_denominator_root"],
        "inventory_root": inventory["inventory_root"], "case_count": len(entries),
        "direct_closure_check_ids": [entry["direct_closure_check_id"] for entry in entries],
        "requirement_roots": [entry["requirement_root"] for entry in entries],
        "acceptance_case_roots": [entry["acceptance_case_root"] for entry in entries],
        "work_selection_roots": [entry["work_selection_root"] for entry in entries],
        "qualification_policy": "MAP_EACH_EXACT_CHECK_ID_TO_LATER_RECORDED_RESULT",
        "required_portability_legs": ["WINDOWS_NATIVE", "WSL_NATIVE"],
        "missing_portability_policy": "HOLD_QUALIFICATION",
        "operator_tier1_status": "NOT_RUN_BY_BUILDER",
        "independent_review_status": "NOT_PERFORMED",
        "status": "CONSTRUCTION_SELECTION_ONLY", "acceptance_case_closed": False,
        "capability_granted": False, "effect_authorized": False, "publication_authorized": False,
        **BOUNDARY}, "program_root")
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build()
    if args.check:
        actual = {path.relative_to(OUT).as_posix() for path in OUT.rglob("*") if path.is_file()} if OUT.is_dir() else set()
        if actual != set(payload):
            raise SystemExit("R036_PROGRAM_RECORD_SET_DRIFT")
        for name, value in sorted(payload.items()):
            if (OUT / name).read_bytes() != canonical(value) + b"\n":
                raise SystemExit("R036_PROGRAM_RECORD_BYTES_DRIFT:" + name)
    else:
        # This new r036 directory is the entire declared write scope.  Existing
        # files outside it, including frozen predecessor programs, are never read
        # as output targets and never rewritten.
        OUT.mkdir(parents=True, exist_ok=True)
        actual = {path.relative_to(OUT).as_posix() for path in OUT.rglob("*") if path.is_file()}
        if actual - set(payload):
            raise SystemExit("R036_PROGRAM_UNDECLARED_OUTPUT_MEMBER")
        for name, value in sorted(payload.items()):
            (OUT / name).write_bytes(canonical(value) + b"\n")
    print(json.dumps({"status": "PASS", "mode": "CHECK_READ_ONLY" if args.check else "WRITE_R036_ONLY",
        "program_root": payload["PROGRAM.json"]["program_root"],
        "inventory_root": payload["WORK-SELECTION-INVENTORY.json"]["inventory_root"],
        "case_count": len(CASES), "record_count": len(payload), "acceptance_case_closed": False,
        "adversarial_cases_executed": 0, **BOUNDARY}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


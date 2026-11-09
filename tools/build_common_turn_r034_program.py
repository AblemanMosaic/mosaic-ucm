#!/usr/bin/env python3
"""Build or read-only check the eight-case P/PPI common-turn r034 program.

These are construction selections against the frozen r033 subject.  Actual
qualification results and operator evidence are separate, later records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "program/common-turn-r034"
PREDECESSOR_SOURCE_ROOT = "169470fe465f9e6a926874ec6df3945f071dca1f7ef488ef103657307eefd605"
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
FILES = (
    "README.md", "PIPPI-AGENT-ACCESS.md",
    "docs/PIPPI-COMMON-TURN-RECORDS.md", "docs/PIPPI.md",
    "skill/ucm-pippi-mediated-agent/SKILL.md",
    "skill/ucm-pippi-mediated-agent/references/common-turn-records.md",
    "src/ucm/__init__.py", "src/ucm/system.py", "src/ucm/capabilities.py",
    "src/ucm/pippi_adaptive.py", "src/ucm/pippi_cli.py",
    "src/ucm/pippi_turn_record.py", "src/ucm/pippi_cmba.py",
    "src/ucm/pippi_turn_workflow.py", "src/ucm/pippi_service.py", "src/ucm/pippi_dashboard.py",
    "src/ucm/profiles.py", "src/ucm/pippi_packs.py",
    "src/ucm/pippi_work_units.py", "src/ucm/pippi_portability.py",
    "tests/test_pippi_turn_record_positive.py", "tests/test_pippi_cmba_positive.py",
    "tests/test_pippi_turn_workflow_positive.py", "tests/test_pippi_cli_common_positive.py",
    "spec/PIPPI-COMMON-TURN-INPUT.schema.json",
    "tools/build_common_turn_r034_program.py",
    "tools/build_common_turn_r034_operator_kit.py", "tools/common_turn_r034_court.py",
    "tools/run_common_turn_r034_demo.py", "tools/qualify_common_turn_r034.py",
    "tools/build_pippi_cold_boot.py", "tools/verify_pippi_cold_boot.py",
    "tools/verify_release.py", "portable/BOOT/START-HERE.md",
    "vendor/optional-packs/cmba/cmba_core-0.1.0a7-py3-none-any.whl",
)
CASES = (
    ("R034.RECORD_MODEL", "Common turn model",
     "Build and revalidate a canonical richer turn record against the exact existing opening and report; "
     "preserve purpose, constitutional context, activity, evidence references, coverage, closure, and predecessor links "
     "without rewriting either legacy record."),
    ("R034.PROVENANCE_BOUNDARY", "Provenance and observation boundary",
     "Preserve each caller-declared claim basis while keeping its assurance DECLARED_NOT_VERIFIED; "
     "a receipt root, host-captured label, or native-turn reference alone cannot establish observation, "
     "host interposition, acceptance closure, capability grant, or effect authorization."),
    ("R034.MISSING_INFORMATION", "Visible missing information",
     "Retain every opening acceptance case and all seven observable channels; represent omitted dispositions "
     "and coverage as UNKNOWN, emit scenario-selected information requests, and distinguish reporting completeness "
     "from evidence verification."),
    ("R034.CMBA_BINDING", "Exact optional CMBA binding",
     "Discover and invoke only the exact optional CMBA wheel by its independently expected hash, verify import origins, "
     "and bind, inspect, evaluate, and replay the exact common turn and its legacy inputs; preserve a structural-only "
     "outcome and the separately scoped r033 native adapter inventory."),
    ("R034.CLI_WORKFLOW", "Agent and operator workflow",
     "Expose the common record, reporting requirements, human projection, validation, and CMBA assessment through "
     "the governed public CLI and ABI with explicit exact inputs, discoverable routes, and unchanged constitutional ceilings."),
    ("R034.PORTABILITY", "Windows and WSL correspondence",
     "Recompute the same canonical positive common-turn and CMBA outputs on Windows and WSL from the exact candidate; "
     "compare their semantic outputs and preserve a qualification hold when either required leg or its evidence is absent."),
    ("R034.OPERATOR_CUSTODY", "Complete operator apparatus",
     "Provide a builder-authored, user-run sealed adversarial kit with complete runtime dependencies, exact source and "
     "qualification pins, a fixed case inventory, stdlib-only custody preflight, flushed progress, sealed fault evidence, "
     "evidence preservation, bounded temporary cleanup, and a pausing double-click launcher; the builder executes zero attacks."),
    ("R034.PREDECESSOR_HISTORY", "Frozen predecessor continuity",
     "Retain the exact r033 baseline and existing journal/program/operator records as predecessor history; "
     "construct only new r034 program records, preserve public v0.1, and record construction selections without "
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
        raise SystemExit("R034_PROGRAM_SUBJECT_IMPORT_ORIGIN_MISMATCH")
    if len(CASES) != 8 or len({case[0] for case in CASES}) != 8:
        raise SystemExit("R034_PROGRAM_CASE_DENOMINATOR_INVALID")
    if len(FILES) != len(set(FILES)) or any(name.startswith("program/common-turn-r034/") for name in FILES):
        raise SystemExit("R034_PROGRAM_INPUT_DENOMINATOR_INVALID")
    members = []
    for name in sorted(FILES):
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            raise SystemExit("R034_PROGRAM_INPUT_MISSING_OR_ALIAS:" + name)
        raw = path.read_bytes()
        members.append({"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    denominator = seal({"schema": "mosaic.ucm.r034-common-turn-source-denominator.v0.1",
        "predecessor_source_root": PREDECESSOR_SOURCE_ROOT,
        "members": members, "member_count": len(members),
        "scope": "EXACT_IMPLEMENTATION_DOCUMENTATION_SKILL_AND_OPTIONAL_CMBA_INPUTS",
        "generated_program_outputs_excluded": True, **BOUNDARY}, "source_denominator_root")
    payload = {"SOURCE-DENOMINATOR.json": denominator}
    entries = []
    for index, (check_id, title, requirement_text) in enumerate(CASES, 1):
        identifier = f"R034-{index:02d}"
        requirement = seal({"schema": "mosaic.ucm.r034-common-turn-requirement.v0.1",
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
            raise SystemExit("R034_PROGRAM_SELECTION_REBUILD_MISMATCH")
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
    inventory = seal({"schema": "mosaic.ucm.r034-common-turn-work-selection-inventory.v0.1",
        "program_id": "UCM_R034_COMMON_TURN", "version": "v0.1", "engineering_revision": "r034",
        "subject_root": PREDECESSOR_SOURCE_ROOT,
        "predecessor_revision": "r033", "predecessor_source_root": PREDECESSOR_SOURCE_ROOT,
        "source_denominator_root": denominator["source_denominator_root"],
        "implementation_members": members, "implementation_member_count": len(members),
        "selections": entries, "acceptance_case_count": len(entries),
        "status": "CONSTRUCTION_SELECTION_ONLY", "acceptance_case_closed": False,
        "capability_granted": False, "effect_authorized": False, **BOUNDARY}, "inventory_root")
    payload["WORK-SELECTION-INVENTORY.json"] = inventory
    payload["PROGRAM.json"] = seal({"schema": "mosaic.ucm.r034-common-turn-program.v0.1",
        "program_id": "UCM_R034_COMMON_TURN", "version": "v0.1", "engineering_revision": "r034",
        "predecessor_revision": "r033", "predecessor_source_root": PREDECESSOR_SOURCE_ROOT,
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
            raise SystemExit("R034_PROGRAM_RECORD_SET_DRIFT")
        for name, value in sorted(payload.items()):
            if (OUT / name).read_bytes() != canonical(value) + b"\n":
                raise SystemExit("R034_PROGRAM_RECORD_BYTES_DRIFT:" + name)
    else:
        # This new r034 directory is the entire declared write scope.  Existing
        # files outside it, including frozen predecessor programs, are never read
        # as output targets and never rewritten.
        OUT.mkdir(parents=True, exist_ok=True)
        actual = {path.relative_to(OUT).as_posix() for path in OUT.rglob("*") if path.is_file()}
        if actual - set(payload):
            raise SystemExit("R034_PROGRAM_UNDECLARED_OUTPUT_MEMBER")
        for name, value in sorted(payload.items()):
            (OUT / name).write_bytes(canonical(value) + b"\n")
    print(json.dumps({"status": "PASS", "mode": "CHECK_READ_ONLY" if args.check else "WRITE_R034_ONLY",
        "program_root": payload["PROGRAM.json"]["program_root"],
        "inventory_root": payload["WORK-SELECTION-INVENTORY.json"]["inventory_root"],
        "case_count": 8, "record_count": len(payload), "acceptance_case_closed": False,
        "adversarial_cases_executed": 0, **BOUNDARY}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

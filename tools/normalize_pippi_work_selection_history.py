#!/usr/bin/env python3
"""Normalize active r016-r018 work-selection records while preserving preimages."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import root
from ucm.pippi_global import BOUNDARY
from ucm.pippi_work_units import build_acceptance_case, build_work_selection


HISTORY = ROOT / "historical" / "pippi-work-selection-preimages"
PROGRAM = ROOT / "program"
OUTPUT = PROGRAM / "pippi-work-selection-normalization-r019"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value) + b"\n")


def rooted(body: dict[str, Any], field: str) -> dict[str, Any]:
    return {**body, field: root(body)}


def _normal_case(*, old_case: dict[str, Any], denominator_root: str) -> dict[str, Any]:
    verification_surface = old_case.get("direct_closure_check_id")
    expected = old_case.get("expected_result_code", old_case.get("expected_code", "PASS"))
    return build_acceptance_case(
        acceptance_case_id=old_case["acceptance_case_id"],
        subject_root=denominator_root,
        requirement_root=old_case["requirement_root"],
        verification_surface=verification_surface,
        expected_result_code=expected,
        current_status="UNMET",
    )


def _r016() -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    source = HISTORY / "pippi-interface-r016"
    denominator = read(source / "SOURCE-DENOMINATOR.json")
    requirement = read(source / "REQUIREMENT.json")
    old_case = read(source / "ACCEPTANCE-CASE.json")
    old_selection = read(source / "WORK-SELECTION.json")
    case = _normal_case(old_case=old_case,
                        denominator_root=denominator["source_denominator_root"])
    selection = build_work_selection(
        acceptance_case=case,
        work_class="DIRECT_ACCEPTANCE_CLOSURE",
        direct_closure_check_id=case["verification_surface"],
        infrastructure_block=None,
    )
    state = read(source / "WORK-UNIT-STATE.json")
    state_body = {key: value for key, value in state.items()
                  if key != "work_unit_state_root"}
    state_body.update({
        "acceptance_case_root": case["acceptance_case_root"],
        "work_selection_root": selection["work_selection_root"],
        "implementation_effect_authorized": False,
        "normalization_revision": "r019",
    })
    state = rooted(state_body, "work_unit_state_root")
    named = {
        "SOURCE-DENOMINATOR.json": denominator,
        "REQUIREMENT.json": requirement,
        "ACCEPTANCE-CASE.json": case,
        "WORK-SELECTION.json": selection,
        "WORK-UNIT-STATE.json": state,
    }
    fields = {
        "SOURCE-DENOMINATOR.json": "source_denominator_root",
        "REQUIREMENT.json": "requirement_root",
        "ACCEPTANCE-CASE.json": "acceptance_case_root",
        "WORK-SELECTION.json": "work_selection_root",
        "WORK-UNIT-STATE.json": "work_unit_state_root",
    }
    inventory_body = {
        "schema": "mosaic.ucm.pippi-interface-program-inventory.v0.2",
        "revision": "r016-normalized-r019",
        "record_roots": {name: value[fields[name]] for name, value in named.items()},
        "records": len(named),
        "historical_preimage_root": old_selection["work_selection_root"],
        **BOUNDARY,
    }
    named["PROGRAM-INVENTORY.json"] = rooted(inventory_body, "program_inventory_root")
    mapping = [{
        "revision": "r016", "acceptance_case_id": case["acceptance_case_id"],
        "preimage_acceptance_case_root": old_case["acceptance_case_root"],
        "normalized_acceptance_case_root": case["acceptance_case_root"],
        "preimage_work_selection_root": old_selection["work_selection_root"],
        "normalized_work_selection_root": selection["work_selection_root"],
        "subject_root": denominator["source_denominator_root"],
    }]
    return named, mapping


def _adaptive(revision: str) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    source = HISTORY / f"pippi-adaptive-{revision}"
    denominator = read(source / "SOURCE-DENOMINATOR.json")
    old_program = read(source / "PROGRAM.json")
    result: dict[str, dict[str, Any]] = {"SOURCE-DENOMINATOR.json": denominator}
    mappings = []
    new_case_roots = []
    new_selection_roots = []
    for path in sorted(source.glob("*-ACCEPTANCE-CASE.json")):
        prefix = path.name.removesuffix("-ACCEPTANCE-CASE.json")
        old_case = read(path)
        requirement_name = prefix + "-REQUIREMENT.json"
        selection_name = prefix + "-WORK-SELECTION.json"
        requirement = read(source / requirement_name)
        old_selection = read(source / selection_name)
        case = _normal_case(old_case=old_case,
                            denominator_root=denominator["source_denominator_root"])
        selection = build_work_selection(
            acceptance_case=case,
            work_class="DIRECT_ACCEPTANCE_CLOSURE",
            direct_closure_check_id=case["verification_surface"],
            infrastructure_block=None,
        )
        result[requirement_name] = requirement
        result[path.name] = case
        result[selection_name] = selection
        new_case_roots.append(case["acceptance_case_root"])
        new_selection_roots.append(selection["work_selection_root"])
        mappings.append({
            "revision": revision,
            "acceptance_case_id": case["acceptance_case_id"],
            "preimage_acceptance_case_root": old_case["acceptance_case_root"],
            "normalized_acceptance_case_root": case["acceptance_case_root"],
            "preimage_work_selection_root": old_selection["work_selection_root"],
            "normalized_work_selection_root": selection["work_selection_root"],
            "subject_root": denominator["source_denominator_root"],
        })
    program_body = {key: value for key, value in old_program.items() if key != "program_root"}
    program_body.update({
        "schema": "mosaic.ucm.pippi-adaptive-program.v0.2",
        "revision": revision + "-normalized-r019",
        "acceptance_case_roots": new_case_roots,
        "work_selection_roots": new_selection_roots,
        "normalization_status": "CANONICAL_WORK_UNIT_PROTOCOL",
    })
    result["PROGRAM.json"] = rooted(program_body, "program_root")
    return result, mappings


def expected() -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, Any]]:
    programs: dict[str, dict[str, dict[str, Any]]] = {}
    mappings: list[dict[str, Any]] = []
    programs["pippi-interface-r016"], rows = _r016(); mappings.extend(rows)
    for revision in ("r017", "r018"):
        key = f"pippi-adaptive-{revision}"
        programs[key], rows = _adaptive(revision); mappings.extend(rows)
    preimages = []
    for path in sorted(HISTORY.rglob("*.json")):
        preimages.append({"path": path.relative_to(HISTORY).as_posix(),
                          "sha256": sha(path), "bytes": path.stat().st_size})
    body = {
        "schema": "mosaic.ucm.pippi-work-selection-normalization.v0.1",
        "repair_revision": "r019",
        "preimage_members": preimages,
        "mappings": mappings,
        "mapping_count": len(mappings),
        "active_programs": sorted(programs),
        "implementation_effect_authorized": False,
        **BOUNDARY,
    }
    return programs, rooted(body, "normalization_root")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    programs, receipt = expected()
    mismatches = []
    for program_name, records in programs.items():
        for name, value in records.items():
            path = PROGRAM / program_name / name
            raw = canonical(value) + b"\n"
            if args.write:
                write(path, value)
            elif not path.is_file() or path.read_bytes() != raw:
                mismatches.append(f"{program_name}/{name}")
    receipt_path = OUTPUT / "NORMALIZATION.json"
    if args.write:
        write(receipt_path, receipt)
    elif not receipt_path.is_file() or receipt_path.read_bytes() != canonical(receipt) + b"\n":
        mismatches.append("pippi-work-selection-normalization-r019/NORMALIZATION.json")
    print(json.dumps({
        "status": "PASS" if not mismatches else "REFUSED",
        "mode": "WRITE" if args.write else "CHECK",
        "normalized_records": receipt["mapping_count"],
        "normalization_root": receipt["normalization_root"],
        "mismatches": mismatches,
        **BOUNDARY,
    }, sort_keys=True))
    return 0 if not mismatches else 3


if __name__ == "__main__":
    raise SystemExit(main())

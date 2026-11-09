#!/usr/bin/env python3
"""Rebuild the frozen r015 direct-closure records for CCP at Courthouse G1.

This builder is deterministic and non-authorizing.  It records the exact
implementation denominator and the local observation that Courthouse lattice
installation remains external; it never installs or dispatches a route.

Successors may change a denominator member.  In that case this historical
builder reads the exact carried r015 preimage rather than silently rebinding
the frozen program to successor bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "program/ccp-courthouse-r015"
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
FILES = (
    "src/ucm/ccp_admissibility.py",
    "src/ucm/ccp_courthouse.py",
    "src/ucm/courthouse_workflow.py",
    "src/ucm/capabilities.py",
    "src/ucm/system.py",
    "src/ucm/cli.py",
    "src/ucm/__init__.py",
    "tests/test_ccp_courthouse_positive.py",
    "docs/CCP-COURTHOUSE-BOUNDARY.md",
    "docs/CCP-ADMISSIBILITY.md",
    "docs/COURTHOUSE-VNEXT-WORKFLOW-IR.md",
    "PIPPI-AGENT-ACCESS.md",
)
FROZEN_PREIMAGES = {
    "PIPPI-AGENT-ACCESS.md":
        "historical/ccp-courthouse-r015/PIPPI-AGENT-ACCESS.md",
    "src/ucm/capabilities.py":
        "historical/ccp-courthouse-r015/src/ucm/capabilities.py",
    "src/ucm/system.py":
        "historical/ccp-courthouse-r015/src/ucm/system.py",
    "src/ucm/cli.py":
        "historical/ccp-courthouse-r015/src/ucm/cli.py",
    "src/ucm/__init__.py":
        "historical/ccp-courthouse-r015/src/ucm/__init__.py",
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def rooted(body: dict[str, Any], field: str) -> dict[str, Any]:
    return {**body, field: sha(canonical(body))}


def build() -> dict[str, dict[str, Any]]:
    rows = []
    for relative in FILES:
        path = ROOT / FROZEN_PREIMAGES.get(relative, relative)
        if not path.is_file():
            raise SystemExit(f"CCP_COURTHOUSE_SOURCE_MISSING:{relative}")
        raw = path.read_bytes()
        rows.append({"path": relative, "bytes": len(raw), "sha256": sha(raw)})
    denominator = rooted({
        "schema": "mosaic.ucm.ccp-courthouse-source-denominator.v0.1",
        "revision": "r015",
        "files": rows,
        "file_count": len(rows),
        "scope": "POINT_OF_USE_ADMISSIBILITY_TO_COURTHOUSE_G1",
        **BOUNDARY,
    }, "source_denominator_root")
    requirement = rooted({
        "schema": "mosaic.ucm.ccp-courthouse-requirement.v0.1",
        "requirement_id": "CCP-R015-COURTHOUSE-G1",
        "subject_root": denominator["source_denominator_root"],
        "objective": (
            "Require one exact current CCP ADMIT decision to bind the P/PPI "
            "work unit and Workflow IR request before Courthouse G1, then "
            "require G1 to carry the admission, decision, and current-use roots."
        ),
        "required_outcomes": [
            "ADMISSION_ENVELOPE_EXACT",
            "COURTHOUSE_SUBMISSION_NOT_DISPATCHED",
            "G1_CARRIES_POINT_OF_USE_ROOTS",
            "HUMAN_STATUS_NONAUTHORIZING",
            "EXTERNAL_LATTICE_STATUS_EXPLICIT",
        ],
        **BOUNDARY,
    }, "requirement_root")

    # Import only after the source denominator is frozen for this build.
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from ucm.pippi_work_units import (build_acceptance_case,
                                      build_work_selection,
                                      build_work_unit_state)

    case = build_acceptance_case(
        acceptance_case_id="CCP-COURTHOUSE-01",
        subject_root=denominator["source_denominator_root"],
        requirement_root=requirement["requirement_root"],
        verification_surface="VERIFY_ADMISSIBLE_COURTHOUSE_RESULT",
        expected_result_code="PASS_CCP_COURTHOUSE_G1_BOUNDARY",
        current_status="UNMET")
    selection = build_work_selection(
        acceptance_case=case, work_class="DIRECT_ACCEPTANCE_CLOSURE",
        direct_closure_check_id=(
            "test_bound_g1_result_imports_without_creating_authority"),
        infrastructure_block=None)
    state = build_work_unit_state(
        work_unit_id="CCP-R015-W01",
        lifecycle_phase="DORMANT_CANDIDATE",
        acceptance_case=case,
        work_class="DIRECT_ACCEPTANCE_CLOSURE",
        direct_closure_check_id=(
            "test_bound_g1_result_imports_without_creating_authority"),
        infrastructure_block=None,
        execution_holds=["EXTERNAL_COURTHOUSE_CAPABILITY_LATTICE_REQUIRED"],
        release_blockers=["CACHE_FREE_QUALIFICATION_REQUIRED",
                          "OPERATOR_TIER1_REQUIRED"],
        qualification_gaps=["COURTHOUSE_ROUTE_NOT_INSTALLED"],
        user_acceptance_pending=False,
        allowed_effect_classes=["PURE_COMPUTATION"],
        forbidden_targets=["LIVE_COURTHOUSE", "NETWORK", "PRODUCTION_GATEWAY"],
        retry_limit=2, repair_attempts=0,
        implemented_work_packages=1, total_work_packages=1,
        proof_level="TARGETED_POSITIVE_PASS_PENDING_QUALIFICATION",
        operational_maturity="INFORMATION_ONLY",
        required_next_gate="CACHE_FREE_QUALIFICATION")
    orientation = rooted({
        "schema": "mosaic.ucm.ccp-courthouse-orientation-observation.v0.1",
        "observation": "CAPABILITY_LATTICE_ABSENT",
        "consequence": "PORTABLE_ADAPTER_STAGED_ROUTE_NOT_INSTALLED",
        "resolution_owner": "EXTERNAL_COURTHOUSE_SESSION",
        "installation_authorized": False,
        "dispatch_authorized": False,
        **BOUNDARY,
    }, "observation_root")
    inventory = rooted({
        "schema": "mosaic.ucm.ccp-courthouse-program-inventory.v0.1",
        "revision": "r015",
        "acceptance_case_id": "CCP-COURTHOUSE-01",
        "record_roots": {
            "source_denominator": denominator["source_denominator_root"],
            "requirement": requirement["requirement_root"],
            "acceptance_case": case["acceptance_case_root"],
            "work_selection": selection["work_selection_root"],
            "work_unit_state": state["work_unit_state_root"],
            "orientation": orientation["observation_root"],
        },
        "status": "CONSTRUCTED_NOT_QUALIFIED",
        **BOUNDARY,
    }, "program_inventory_root")
    return {
        "SOURCE-DENOMINATOR.json": denominator,
        "REQUIREMENT.json": requirement,
        "ACCEPTANCE-CASE.json": case,
        "WORK-SELECTION.json": selection,
        "WORK-UNIT-STATE.json": state,
        "AOK-ORIENTATION.json": orientation,
        "PROGRAM-INVENTORY.json": inventory,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    records = build()
    if args.write:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        for name, value in records.items():
            (OUTPUT / name).write_bytes(canonical(value) + b"\n")
    else:
        for name, value in records.items():
            path = OUTPUT / name
            if not path.is_file() or path.read_bytes() != canonical(value) + b"\n":
                raise SystemExit(f"CCP_COURTHOUSE_PROGRAM_MISMATCH:{name}")
    print(json.dumps({"status": "PASS", "mode": "WRITE" if args.write else "CHECK",
                      "records": len(records),
                      "program_inventory_root": records["PROGRAM-INVENTORY.json"][
                          "program_inventory_root"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

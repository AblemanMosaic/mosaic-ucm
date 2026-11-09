#!/usr/bin/env python3
"""Build the P/PPI work-selection record for the r011 archive-verifier repair."""
from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import root  # noqa: E402
from ucm.pippi_work_units import build_acceptance_case, build_work_selection  # noqa: E402


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def main() -> int:
    output = ROOT / "program" / "pippi-r011"
    output.mkdir(parents=True, exist_ok=True)
    requirement = {
        "requirement": "BUNDLED_VERIFIER_ACCEPTS_EVERY_CANONICAL_PUBLIC_RELEASE_ARCHIVE",
        "consumer_finding": "SDK_VERIFY_COMPRESSION_CONTRACT_MISMATCH",
    }
    requirement_root = root(requirement)
    acceptance_case = build_acceptance_case(
        acceptance_case_id="PIPPI-R011-ARCHIVE-SELF-VERIFY",
        subject_root="476c2ecb4d3732a3288ac8eec2cb3c86ce3c741f424905d9920bd51c5fb497b1",
        requirement_root=requirement_root,
        verification_surface="test_sdk_bundled_verifier_accepts_all_canonical_release_archives",
        expected_result_code="PASS",
        current_status="UNMET",
    )
    selection = build_work_selection(
        acceptance_case=acceptance_case,
        work_class="DIRECT_ACCEPTANCE_CLOSURE",
        direct_closure_check_id="test_sdk_bundled_verifier_accepts_all_canonical_release_archives",
        infrastructure_block=None,
    )
    selection_input = {
        "acceptance_case": acceptance_case,
        "work_class": "DIRECT_ACCEPTANCE_CLOSURE",
        "direct_closure_check_id": selection["direct_closure_check_id"],
        "infrastructure_block": None,
    }
    inventory_body = {
        "schema": "mosaic.ucm.pippi-r011-work-selection-inventory.v0.1",
        "revision": "r011",
        "predecessor_source_root": acceptance_case["subject_root"],
        "selections": [{
            "acceptance_case_id": acceptance_case["acceptance_case_id"],
            "acceptance_case_root": acceptance_case["acceptance_case_root"],
            "requirement_root": requirement_root,
            "direct_closure_check_id": selection["direct_closure_check_id"],
            "work_selection_root": selection["work_selection_root"],
        }],
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
        "real_a5": False,
        "g0": "CLOSED",
    }
    records = {
        "archive-self-verify-requirement.json": requirement,
        "archive-self-verify-selection.json": selection_input,
        "archive-self-verify-selection-verification.json": selection,
        "WORK-SELECTION-INVENTORY.json": {
            **inventory_body, "inventory_root": root(inventory_body)},
    }
    for name, value in records.items():
        (output / name).write_bytes(canonical(value) + b"\n")
    print(json.dumps({"status": "PASS", "output": str(output),
                      "acceptance_case_root": acceptance_case["acceptance_case_root"],
                      "work_selection_root": selection["work_selection_root"]},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

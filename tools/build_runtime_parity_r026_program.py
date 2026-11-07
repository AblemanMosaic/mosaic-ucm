#!/usr/bin/env python3
"""Build the fixed-denominator r026 runtime-parity repair program."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ucm.pippi_work_units import build_acceptance_case, build_work_selection  # noqa: E402

OUT = ROOT / "program/runtime-parity-r026"
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
SOURCE_PATHS = (
    "src/ucm/pippi_adaptive.py", "src/ucm/pippi_portability.py",
    "src/ucm/pippi_portability_evidence.py", "src/ucm/pippi_cli.py",
    "tools/build_pippi_adaptive_contracts.py", "tools/build_pippi_cold_boot.py",
    "tools/build_portability_source_archive.py", "tools/run_portability_leg.py",
    "tools/run_public_release_qualification.py", "tools/build_release.py",
    "tools/build_frozen_operator_registry.py", "tools/build_frozen_program_registry.py",
    "tools/build_runtime_parity_r026_program.py",
    "tools/build_runtime_parity_r026_operator_kit.py",
    "tools/build_r026_review_transport.py", "tools/release_common.py",
    "tools/verify_pippi_cold_boot.py", "tools/verify_release.py", "VERIFY.py",
    "tests/test_pippi_adaptive.py", "tests/test_pippi_cold_boot.py",
    "tests/test_pippi_portability.py", "tests/test_pippi_release_packaging.py",
    "docs/PORTABILITY-DETERMINISM.md", "docs/R26-REVIEW-WORK-ORDER.md",
    "operator/runtime-parity-r026/KIT-DECLARATION.json",
    "operator/runtime-parity-r026/RUN-TIER1.py",
    "spec/FROZEN-OPERATOR-REGISTRY.json", "spec/FROZEN-PROGRAM-REGISTRY.json",
    "spec/PIPPI-ADAPTIVE-COLD-BOOT-CONTRACT.json",
    "spec/PIPPI-CAPABILITY-SURFACE-REGISTRY.json",
    "spec/PIPPI-MEDIATION-LIBRARY.json",
)
CASES = ((
    "R26-01",
    "The staged runtime and cold boot carry the exact generated adaptive contracts",
    "test_pippi_release_packaging.PippiReleasePackagingTests.test_runtime_builder_carries_complete_pippi_install_boundary",
),)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def records() -> dict[str, dict]:
    members = [{"path": path, "bytes": (ROOT / path).stat().st_size,
                "sha256": sha((ROOT / path).read_bytes())}
               for path in SOURCE_PATHS]
    denominator_body = {
        "schema": "mosaic.ucm.runtime-parity-source-denominator.v0.1",
        "members": members, "member_count": len(members), **BOUNDARY}
    denominator = {**denominator_body,
                   "source_denominator_root": sha(canonical(denominator_body))}
    predecessor = json.loads(
        (ROOT / "release/PREDECESSOR-r025-QUALIFICATION.json").read_text())
    result: dict[str, dict] = {"SOURCE-DENOMINATOR.json": denominator}
    requirement_roots = []
    case_roots = []
    selection_roots = []
    for case_id, title, test_id in CASES:
        req_body = {
            "schema": "mosaic.ucm.runtime-parity-requirement.v0.1",
            "requirement_id": case_id, "title": title,
            "source_denominator_root": denominator["source_denominator_root"],
            "program_rule": "ONE_ACCEPTANCE_CASE_PER_IMPLEMENTATION_UNIT",
            **BOUNDARY}
        req = {**req_body, "requirement_root": sha(canonical(req_body))}
        case = build_acceptance_case(
            acceptance_case_id=case_id,
            subject_root=predecessor["source_manifest_root"],
            requirement_root=req["requirement_root"],
            verification_surface=test_id,
            expected_result_code="PASS", current_status="UNMET")
        selection = build_work_selection(
            acceptance_case=case, work_class="DIRECT_ACCEPTANCE_CLOSURE",
            direct_closure_check_id=test_id, infrastructure_block=None)
        result[f"{case_id}-REQUIREMENT.json"] = req
        result[f"{case_id}-ACCEPTANCE-CASE.json"] = case
        result[f"{case_id}-WORK-SELECTION.json"] = selection
        requirement_roots.append(req["requirement_root"])
        case_roots.append(case["acceptance_case_root"])
        selection_roots.append(selection["work_selection_root"])
    body = {
        "schema": "mosaic.ucm.runtime-parity-program.v0.1",
        "program_id": "UCM_R026_RUNTIME_PARITY",
        "version": "v0.1", "engineering_revision": "r026",
        "predecessor_revision": "r025",
        "predecessor_source_root": predecessor["source_manifest_root"],
        "predecessor_qualification_root": predecessor["root"],
        "source_denominator_root": denominator["source_denominator_root"],
        "requirement_roots": requirement_roots,
        "acceptance_case_roots": case_roots,
        "work_selection_roots": selection_roots,
        "required_portability_legs": ["WINDOWS_NATIVE", "WSL_NATIVE"],
        "operator_tier1_status": "NOT_RUN", "publication_authorized": False,
        **BOUNDARY}
    result["PROGRAM.json"] = {**body, "program_root": sha(canonical(body))}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    mismatches = []
    for name, value in records().items():
        path = OUT / name
        raw = canonical(value) + b"\n"
        if args.write:
            OUT.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        elif not path.is_file() or path.read_bytes() != raw:
            mismatches.append(name)
    print(json.dumps({"status": "PASS" if not mismatches else "REFUSED",
                      "records": len(records()), "mismatches": mismatches,
                      **BOUNDARY}, sort_keys=True))
    return 0 if not mismatches else 3


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build the fixed-denominator r024 portability-determinism program."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ucm.pippi_work_units import build_acceptance_case, build_work_selection  # noqa: E402

OUT = ROOT / "program/portability-determinism-r024"
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
SOURCE_PATHS = (
    "src/ucm/program_history.py", "src/ucm/operator_history.py",
    "src/ucm/pippi_portability.py", "src/ucm/pippi_adaptive.py",
    "src/ucm/pippi_cli.py", "src/ucm/system.py", "src/ucm/capabilities.py",
    "src/ucm/pippi_global.py", "src/ucm/pippi_portfolio.py",
    "src/ucm/pippi_reviews.py", "src/ucm/subject.py",
    "src/mosaic_ui/ablate.py", "src/mosaic_ui/pilot.py",
    "src/mosaic_ui/release.py",
    "tools/build_frozen_operator_registry.py", "tools/build_frozen_program_registry.py",
    "tools/build_portability_determinism_r024_program.py",
    "tools/run_portability_leg.py", "tools/compare_portability_witnesses.py",
    "tools/build_portability_source_archive.py",
    "tools/release_common.py",
    "tools/run_public_release_qualification.py",
    "tools/build_portability_r024_operator_kit.py",
    "tools/build_r024_review_transport.py", "docs/R24-REVIEW-WORK-ORDER.md",
    "docs/PORTABILITY-DETERMINISM.md",
    "operator/portability-determinism-r024/KIT-DECLARATION.json",
    "operator/portability-determinism-r024/RUN-TIER1.py",
    "tests/test_pippi_portability.py", "tests/test_pippi_adaptive.py",
    "tests/test_public_surface.py",
    "spec/FROZEN-OPERATOR-REGISTRY.json", "spec/FROZEN-PROGRAM-REGISTRY.json",
)
CASES = (
    ("R24-01", "Filesystem ordering is canonical across Windows and POSIX",
     "test_pippi_portability.PippiPortabilityTests.test_program_history_order_is_platform_neutral"),
    ("R24-02", "Predecessor operator courts are immutable and successor-named",
     "test_pippi_portability.PippiPortabilityTests.test_operator_registry_covers_original_and_successor"),
    ("R24-03", "Execution context and portability rules are injected at turn opening",
     "test_pippi_adaptive.PippiAdaptiveTests.test_turn_open_report_reconcile"),
    ("R24-04", "Portable-source inspection refuses host-flavoured path sorting",
     "test_pippi_portability.PippiPortabilityTests.test_source_inspection_refuses_host_flavoured_path_sort"),
    ("R24-05", "Windows-native and WSL-native witnesses must correspond",
     "test_pippi_portability.PippiPortabilityTests.test_windows_and_wsl_witnesses_allow_portable_claim"),
    ("R24-06", "Missing or mounted WSL evidence cannot support a portable claim",
     "test_pippi_portability.PippiPortabilityTests.test_missing_or_mounted_wsl_leg_cannot_claim_portability"),
)


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
        "schema": "mosaic.ucm.portability-determinism-source-denominator.v0.1",
        "members": members, "member_count": len(members), **BOUNDARY}
    denominator = {**denominator_body,
                   "source_denominator_root": sha(canonical(denominator_body))}
    predecessor = json.loads(
        (ROOT / "release/PREDECESSOR-r023-QUALIFICATION.json").read_text())
    result: dict[str, dict] = {"SOURCE-DENOMINATOR.json": denominator}
    requirement_roots = []
    case_roots = []
    selection_roots = []
    for case_id, title, test_id in CASES:
        req_body = {
            "schema": "mosaic.ucm.portability-determinism-requirement.v0.1",
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
        "schema": "mosaic.ucm.portability-determinism-program.v0.1",
        "program_id": "UCM_R024_PORTABILITY_DETERMINISM",
        "version": "v0.1", "engineering_revision": "r024",
        "predecessor_revision": "r023",
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

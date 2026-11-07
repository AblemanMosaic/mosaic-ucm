#!/usr/bin/env python3
"""Build the fixed-denominator r023 systemic repair program."""
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

OUT = ROOT / "program/systemic-repair-r023"
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
SOURCE_PATHS = (
    "src/ucm/dependency_graph.py", "src/ucm/program_history.py", "src/ucm/ugel.py",
    "tools/build_frozen_program_registry.py", "tools/verify_ugel_source_archive.py",
    "tools/build_r022_ugel_return_provenance.py",
    "tools/build_systemic_repair_r023_program.py",
    "tests/test_dependency_graph.py", "tests/test_program_history.py",
    "tests/test_ugel_integration.py", "tests/test_ugel_source_custody.py",
    "tests/test_systemic_repair_r023.py",
    "spec/FROZEN-PROGRAM-REGISTRY.json",
    "review/ugel-r022-operator-return/PROVENANCE.json",
    "qualification/inputs/ugel/UGEL-BATCH-E-r001.zip",
)
CASES = (
    ("R23-01", "Dependency reuse rechecks external custody anchors at point of use",
     "test_dependency_graph.DependencyGraphTests.test_reuse_rechecks_external_custody_anchors_at_point_of_use"),
    ("R23-02", "Predecessor program records are immutable and exact-preimage bound",
     "test_program_history.ProgramHistoryTests.test_historical_builders_check_custody_instead_of_rewriting"),
    ("R23-03", "Delivered UGEL Batch E archive independently recomputes exact source custody",
     "test_ugel_source_custody.UgelSourceCustodyTests.test_exact_batch_e_source_archive_is_closed_and_pinned"),
    ("R23-04", "UGEL text limits are enforced by the UCM correspondence layer",
     "test_ugel_integration.UgelIntegrationTests.test_call_text_limit_is_enforced_before_correspondence"),
    ("R23-05", "UGEL terminal receipts revalidate result and correspondence roots",
     "test_ugel_integration.UgelIntegrationTests.test_terminal_body_recomputes_result_and_correspondence_roots"),
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def records() -> dict[str, dict]:
    members = [{"path": path, "bytes": (ROOT / path).stat().st_size,
                "sha256": sha((ROOT / path).read_bytes())} for path in SOURCE_PATHS]
    denominator_body = {"schema": "mosaic.ucm.systemic-repair-source-denominator.v0.1",
                        "members": members, "member_count": len(members), **BOUNDARY}
    denominator = {**denominator_body,
                   "source_denominator_root": sha(canonical(denominator_body))}
    predecessor = json.loads(
        (ROOT / "release/PREDECESSOR-r022-QUALIFICATION.json").read_text())
    result: dict[str, dict] = {"SOURCE-DENOMINATOR.json": denominator}
    requirement_roots = []
    case_roots = []
    selection_roots = []
    for case_id, title, test_id in CASES:
        req_body = {"schema": "mosaic.ucm.systemic-repair-requirement.v0.1",
                    "requirement_id": case_id, "title": title,
                    "source_denominator_root": denominator["source_denominator_root"],
                    "program_rule": "ONE_ACCEPTANCE_CASE_PER_IMPLEMENTATION_UNIT", **BOUNDARY}
        req = {**req_body, "requirement_root": sha(canonical(req_body))}
        case = build_acceptance_case(
            acceptance_case_id=case_id, subject_root=predecessor["source_manifest_root"],
            requirement_root=req["requirement_root"], verification_surface=test_id,
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
    body = {"schema": "mosaic.ucm.systemic-repair-program.v0.1",
            "program_id": "UCM_R023_SYSTEMIC_REPAIR", "version": "v0.1",
            "engineering_revision": "r023", "predecessor_revision": "r022",
            "predecessor_source_root": predecessor["source_manifest_root"],
            "predecessor_qualification_root": predecessor["root"],
            "source_denominator_root": denominator["source_denominator_root"],
            "requirement_roots": requirement_roots,
            "acceptance_case_roots": case_roots,
            "work_selection_roots": selection_roots,
            "operator_tier1_status": "NOT_RUN", "publication_authorized": False,
            **BOUNDARY}
    result["PROGRAM.json"] = {**body, "program_root": sha(canonical(body))}
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        print(json.dumps({
            "status": "REFUSED", "mode": "WRITE",
            "reason_code": "FROZEN_PROGRAM_MUTATION_REFUSED",
            "directory": "program/systemic-repair-r023", **BOUNDARY,
        }, sort_keys=True))
        return 3
    registry = json.loads(
        (ROOT / "spec/FROZEN-PROGRAM-REGISTRY.json").read_text(encoding="utf-8"))
    checked = check_frozen_program_directory(
        source_root=ROOT, registry=registry,
        directory="program/systemic-repair-r023")
    print(json.dumps({**checked, "mode": "CHECK"}, sort_keys=True))
    return 0
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
                      "records": len(records()), "mismatches": mismatches, **BOUNDARY},
                     sort_keys=True))
    return 0 if not mismatches else 3


if __name__ == "__main__":
    raise SystemExit(main())

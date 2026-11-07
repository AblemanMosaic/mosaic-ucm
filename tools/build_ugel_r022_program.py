#!/usr/bin/env python3
"""Build and check the exact r022 UGEL integration program."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ucm.pippi_work_units import build_acceptance_case, build_work_selection
from ucm.program_history import check_frozen_program_directory

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "program" / "ugel-executor-r022"
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
SOURCE_PATHS = (
    "src/ucm/ugel.py", "src/ucm/system.py", "src/ucm/capabilities.py",
    "src/ucm/cli.py", "src/ucm/pippi_packs.py",
    "src/ucm/dependency_adapters.py", "tests/test_ugel_integration.py",
    "docs/UGEL-EXECUTOR-INTEGRATION.md", "PIPPI-AGENT-ACCESS.md",
    "skill/ucm-pippi-mediated-agent/SKILL.md",
    "skill/ucm-pippi-mediated-agent/references/external-executors.md",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def records() -> dict[str, dict]:
    rows = [{"path": path, "sha256": sha((ROOT / path).read_bytes()),
             "bytes": (ROOT / path).stat().st_size} for path in SOURCE_PATHS]
    denominator_body = {
        "schema": "mosaic.ucm.ugel-source-denominator.v0.1",
        "members": rows, "member_count": len(rows), **BOUNDARY,
    }
    denominator = {**denominator_body,
                   "source_denominator_root": sha(canonical(denominator_body))}
    requirement_body = {
        "schema": "mosaic.ucm.ugel-program-requirement.v0.1",
        "requirement_id": "UGEL-R022-01",
        "title": "Route one exact sim.add request through Pippi, external UGEL, the Operational Gateway, and dependency evidence",
        "source_denominator_root": denominator["source_denominator_root"],
        "depends_on": [],
        "program_rule": "ONE_ACCEPTANCE_CASE_PER_IMPLEMENTATION_UNIT",
        **BOUNDARY,
    }
    requirement = {**requirement_body,
                   "requirement_root": sha(canonical(requirement_body))}
    test_id = "test_ugel_integration.UgelIntegrationTests.test_sim_add_crosses_pippi_gateway_receipts_and_dependency_evidence"
    acceptance = build_acceptance_case(
        acceptance_case_id="UGEL-R022-01",
        subject_root="622899782f4b47123426504bdbc7604a81e5f989cf799644975dfdb5ee89baad",
        requirement_root=requirement["requirement_root"],
        verification_surface=test_id, expected_result_code="PASS",
        current_status="UNMET")
    selection = build_work_selection(
        acceptance_case=acceptance, work_class="DIRECT_ACCEPTANCE_CLOSURE",
        direct_closure_check_id=test_id, infrastructure_block=None)
    body = {
        "schema": "mosaic.ucm.ugel-integration-program.v0.1",
        "program_id": "UCM_UGEL_EXECUTOR_INTEGRATION",
        "version": "v0.1", "engineering_revision": "r022",
        "predecessor_revision": "r021",
        "predecessor_source_root": acceptance["subject_root"],
        "source_denominator_root": denominator["source_denominator_root"],
        "requirement_roots": [requirement["requirement_root"]],
        "acceptance_case_roots": [acceptance["acceptance_case_root"]],
        "work_selection_roots": [selection["work_selection_root"]],
        "external_executor_status": "DECLARED_UNBOUND",
        "operator_tier1_status": "NOT_RUN",
        "publication_authorized": False,
        **BOUNDARY,
    }
    return {
        "SOURCE-DENOMINATOR.json": denominator,
        "UGEL-R022-01-REQUIREMENT.json": requirement,
        "UGEL-R022-01-ACCEPTANCE-CASE.json": acceptance,
        "UGEL-R022-01-WORK-SELECTION.json": selection,
        "PROGRAM.json": {**body, "program_root": sha(canonical(body))},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    registry = json.loads((ROOT / "spec/FROZEN-PROGRAM-REGISTRY.json").read_text(encoding="utf-8"))
    if args.write:
        print(json.dumps({"status": "REFUSED",
                          "reason_code": "FROZEN_PROGRAM_MUTATION_REFUSED",
                          "directory": "program/ugel-executor-r022", **BOUNDARY},
                         sort_keys=True))
        return 3
    frozen = check_frozen_program_directory(
        source_root=ROOT, registry=registry,
        directory="program/ugel-executor-r022")
    print(json.dumps({**frozen, "records": 5}, sort_keys=True))
    return 0
    # Historical records are never regenerated from current source.
    mismatches = []
    for name, value in records().items():
        path = OUT / name
        expected = canonical(value) + b"\n"
        if args.write:
            path.write_bytes(expected)
        elif not path.is_file() or path.read_bytes() != expected:
            mismatches.append(name)
    print(json.dumps({"status": "PASS" if not mismatches else "REFUSED",
                      "mismatches": mismatches, "records": 5, **BOUNDARY},
                     sort_keys=True))
    return 0 if not mismatches else 3


if __name__ == "__main__":
    raise SystemExit(main())

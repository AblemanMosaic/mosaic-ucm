#!/usr/bin/env python3
"""Build the governed r021 Dependency and Evidence Graph program records."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import root  # noqa: E402
from ucm.pippi_work_units import (  # noqa: E402
    build_acceptance_case, build_work_selection, validate_acceptance_case,
)


PREDECESSOR_SOURCE_ROOT = "fcec12cf373850d414d475397ea012aeb7ef35eb13283f8c3ae9de32bd2535b5"
BOUNDARY = {
    "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    "real_a5": False, "g0": "CLOSED",
}

# Cases 29 and 30 remain explicit conditional non-selections. This avoids
# manufacturing shared infrastructure without a named consumer or blocker.
CASES = [
    (1, "Typed canonical values and equality", []),
    (2, "Immutable complete input snapshots", [1]),
    (3, "Definition invocation output and receipt identity", [1]),
    (4, "Trusted prior and cache admission", [2, 3]),
    (5, "Dependency kinds and closure completeness", [3]),
    (6, "Blocked outcomes and current-use validity", [3, 5]),
    (7, "Target slicing graph evolution and changed-output pruning", [2, 4, 5, 6]),
    (8, "Full versus incremental conformance oracle", [7]),
    (9, "Existing planner consolidation", [8]),
    (10, "Journal and concurrent project reconciliation", [9]),
    (11, "Dependency-aware standards and context", [10]),
    (12, "Registered CLI ABI and adapter surfaces", [9]),
    (13, "Native user and agent observatory", [10, 11, 12]),
    (14, "AMCAS baseline and dependency parity", [8, 12]),
    (15, "Real Workflow IR CCP and Gateway compatibility", [6, 14]),
    (16, "Effect history and recovery separation", [15]),
    (17, "Verified CAS and transtemporal reuse", [4, 8]),
    (18, "Portable complete graph closure", [10, 14, 17]),
    (19, "Incremental development checks with fixed denominators", [9, 14, 17]),
    (20, "Compiler and native proof adapters", [8, 17]),
    (21, "C and ordinary software evidence adapter", [5, 19]),
    (22, "Policy packs and optional component planning", [9, 14]),
    (23, "Architecture traceability and realization comparison", [14, 20, 21]),
    (24, "LLM and live observation honesty", [6, 11, 17]),
    (25, "Measured bounded performance", [13, 17, 19]),
    (26, "Reuse graduation policy", [18, 19, 25]),
    (27, "Documentation skills and self-governed release campaign", [13, 14, 16, 18, 23, 24, 26]),
    (28, "Single release qualification and exact operator apparatus", [27]),
    (29, "Optional provenance and ordinary-tool interchange", [28]),
    (30, "Conditional advanced optimization", [28]),
]


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"


SURFACES = {
    1: "test_dependency_graph.DependencyGraphTests.test_bool_and_integer_are_not_equal",
    2: "test_dependency_graph.DependencyGraphTests.test_sequential_delta_preserves_prior_change",
    3: "test_dependency_graph.DependencyGraphTests.test_policy_changes_definition_and_invocation_identity",
    4: "test_dependency_graph.DependencyGraphTests.test_self_rooted_prior_is_not_admitted",
    5: "test_dependency_graph.DependencyGraphTests.test_declared_closure_never_reuses",
    6: "test_dependency_graph.DependencyGraphTests.test_current_use_blocks_expired_or_failed_prerequisite",
    7: "test_dependency_graph.DependencyGraphTests.test_verified_reuse_preserves_unaffected_outputs",
    8: "test_dependency_graph.DependencyGraphTests.test_compare_explain_and_rebuild_oracle",
    9: "test_dependency_adapters.DependencyAdapterTests.test_project_content_and_replan_use_one_graph_core",
    10: "test_dependency_adapters.DependencyAdapterTests.test_journal_fold_preserves_two_session_updates",
    11: "test_dependency_adapters.DependencyAdapterTests.test_pippi_turn_detects_graph_drift",
    12: "test_dependency_program.DependencyProgramTests.test_cli_abi_profile_and_no_implicit_write",
    13: "test_dependency_adapters.DependencyAdapterTests.test_observatory_uses_rooted_status_without_global_held",
    14: "test_dependency_adapters.DependencyAdapterTests.test_amcas_profile_is_explicit_migration_when_unbound",
    15: "test_dependency_program.DependencyProgramTests.test_native_workflow_ir_accepts_only_ready_dependency_binding",
    16: "test_dependency_adapters.DependencyAdapterTests.test_effect_projection_refuses_automatic_retry",
    17: "test_dependency_adapters.DependencyAdapterTests.test_storage_indexes_do_not_turn_missing_bytes_into_reuse",
    18: "test_dependency_graph.DependencyGraphTests.test_portable_closure_has_no_credentials",
    19: "test_dependency_adapters.DependencyAdapterTests.test_development_check_denominator_is_total_and_release_full",
    20: "test_dependency_adapters.DependencyAdapterTests.test_compiler_and_proof_binding_requires_revalidation",
    21: "test_dependency_adapters.DependencyAdapterTests.test_c_depfile_controls_reuse_eligibility",
    22: "test_dependency_adapters.DependencyAdapterTests.test_policy_pack_plan_preserves_native_validation_and_needs_packs",
    23: "test_dependency_adapters.DependencyAdapterTests.test_architecture_similarity_never_establishes_equivalence",
    24: "test_dependency_adapters.DependencyAdapterTests.test_observation_retrieval_is_honest",
    25: "test_dependency_adapters.DependencyAdapterTests.test_benchmark_and_reuse_graduation_are_bounded",
    26: "test_dependency_program.DependencyProgramTests.test_release_lane_never_graduates_reuse",
    27: "test_dependency_program.DependencyProgramTests.test_documented_self_governed_boundary_demo",
    28: "test_dependency_program.DependencyProgramTests.test_release_and_operator_apparatus_are_exact_and_unexecuted",
    29: "test_dependency_program.DependencyProgramTests.test_optional_interchange_is_conditionally_not_selected",
    30: "test_dependency_program.DependencyProgramTests.test_advanced_optimization_is_conditionally_not_selected",
}


def records() -> dict[str, object]:
    generated: dict[str, object] = {}
    inventory_rows = []
    for number, title, dependencies in CASES:
        case_id = f"DG-{number:02d}"
        requirement = {
            "schema": "mosaic.ucm.dependency-program-requirement.v0.1",
            "requirement_id": case_id,
            "title": title,
            "depends_on": [f"DG-{item:02d}" for item in dependencies],
            "program_rule": "ONE_ACCEPTANCE_CASE_PER_IMPLEMENTATION_UNIT",
            "predecessor_source_root": PREDECESSOR_SOURCE_ROOT,
            **BOUNDARY,
        }
        requirement_root = root(requirement)
        surface = SURFACES[number]
        case = build_acceptance_case(
            acceptance_case_id=case_id, subject_root=PREDECESSOR_SOURCE_ROOT,
            requirement_root=requirement_root, verification_surface=surface,
            expected_result_code="PASS", current_status="UNMET")
        generated[f"{case_id}-REQUIREMENT.json"] = requirement
        generated[f"{case_id}-ACCEPTANCE-CASE.json"] = case
        if number <= 28:
            selection = build_work_selection(
                acceptance_case=case, work_class="DIRECT_ACCEPTANCE_CLOSURE",
                direct_closure_check_id=surface, infrastructure_block=None)
            generated[f"{case_id}-WORK-SELECTION.json"] = selection
            disposition = "SELECTED_DIRECT_CLOSURE"
            selection_root = selection["work_selection_root"]
        else:
            body = {
                "schema": "mosaic.ucm.conditional-work-disposition.v0.1",
                "acceptance_case_root": case["acceptance_case_root"],
                "disposition": "NOT_SELECTED_NO_NAMED_CONSUMER_OR_BLOCKER",
                "selection_condition": (
                    "A named consumer or exact blocked acceptance case supplies rooted evidence."),
                "implementation_effect_authorized": False,
                **BOUNDARY,
            }
            disposition_record = {**body, "disposition_root": root(body)}
            generated[f"{case_id}-CONDITIONAL-DISPOSITION.json"] = disposition_record
            disposition = disposition_record["disposition"]
            selection_root = None
        inventory_rows.append({
            "acceptance_case_id": case_id,
            "acceptance_case_root": case["acceptance_case_root"],
            "requirement_root": requirement_root,
            "verification_surface": surface,
            "disposition": disposition,
            "work_selection_root": selection_root,
        })
    body = {
        "schema": "mosaic.ucm.dependency-program-inventory.v0.1",
        "program_id": "UCM-DEPENDENCY-EVIDENCE-GRAPH-r021",
        "public_version": "v0.1", "revision": "r021",
        "predecessor_source_root": PREDECESSOR_SOURCE_ROOT,
        "acceptance_cases": inventory_rows,
        "selected_direct_cases": 28, "conditional_not_selected_cases": 2,
        "shared_infrastructure_selections": 0,
        **BOUNDARY,
    }
    generated["PROGRAM-INVENTORY.json"] = {**body, "inventory_root": root(body)}
    return generated


def verify(directory: Path) -> dict[str, object]:
    expected = records()
    actual = {path.name: path.read_bytes() for path in directory.glob("*.json")}
    expected_bytes = {name: canonical(value) for name, value in expected.items()}
    if actual != expected_bytes:
        raise SystemExit("DEPENDENCY_PROGRAM_BYTES_OR_SET_MISMATCH")
    for number, _title, _dependencies in CASES:
        validate_acceptance_case(expected[f"DG-{number:02d}-ACCEPTANCE-CASE.json"])
    return {"status": "PASS", "records": len(expected),
            "inventory_root": expected["PROGRAM-INVENTORY.json"]["inventory_root"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = ROOT / "program" / "dependency-graph-r021"
    if args.check:
        print(json.dumps(verify(output), sort_keys=True)); return 0
    output.mkdir(parents=True, exist_ok=True)
    expected = records()
    expected_names = set(expected)
    for old in output.glob("*.json"):
        if old.name not in expected_names:
            old.unlink()
    for name, value in expected.items():
        (output / name).write_bytes(canonical(value))
    print(json.dumps(verify(output), sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())

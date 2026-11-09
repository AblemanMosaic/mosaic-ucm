"""Exact reconciliation of application-authored and pipeline-bound Stage I3 plans."""
from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path

from uclop.canonical import canonical_bytes, require, root, strict_loads
from ucm.amcas import BOUNDARY
from ucm.stage3 import required_instruction_evidence, validate_instruction, validate_plan


INSTRUCTION_STABLE_FIELDS = (
    "application_id", "thread_id", "predecessor_portfolio_sha256",
    "portfolio_status_root", "preflight_root", "court_root",
    "court_evidence_sha256", "stage_i1_artifact_sha256",
    "stage_i2_artifact_sha256", "stage_i1_status", "matched_relations",
    "cm1_requirements", "cm2_priorities", "requested_plan_fields", "mode",
)
PLAN_BINDING_FIELDS = {"instruction_root", "required_evidence_roots", "plan_root"}


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _load_exact(path: Path) -> tuple[bytes, dict, bool]:
    raw = path.read_bytes()
    value = strict_loads(raw)
    return raw, value, canonical_bytes(value) == raw


def _plan_semantics(plan: dict) -> dict:
    return {key: value for key, value in plan.items() if key not in PLAN_BINDING_FIELDS}


def _validate_legacy_authoring_plan(plan: dict, instruction: dict) -> dict:
    """Validate legacy authoring bytes through the documented evidence-set shim."""
    checked = deepcopy(plan)
    checked["required_evidence_roots"] = sorted(
        set(checked["required_evidence_roots"])
        | required_instruction_evidence(instruction))
    checked["plan_root"] = root({key: value for key, value in checked.items()
                                 if key != "plan_root"})
    validate_plan(checked, expected_instruction=instruction)
    return plan


def _instruction_path(root_path: Path, application_id: str) -> Path:
    return root_path / "instructions" / (application_id.replace(".", "-") + "-STAGE-I3-INSTRUCTION.json")


def _plan_path(root_path: Path, application_id: str) -> Path:
    return root_path / "plans" / (application_id.replace(".", "-") + "-STAGE-I3-PLAN.json")


def reconcile_stage_i3(
    authoring_root: Path,
    bound_root: Path,
    expected_application_ids: list[str],
    baseline: dict,
    baseline_sha256: str,
) -> dict:
    """Prove a binding-only transition across an exact seven-application roster."""
    require(len(expected_application_ids) == len(set(expected_application_ids)),
            "ECOSYSTEM_STAGE_I3_DENOMINATOR_DUPLICATE")
    baseline_body = {key: value for key, value in baseline.items() if key != "baseline_root"}
    require(root(baseline_body) == baseline["baseline_root"],
            "ECOSYSTEM_STAGE_I3_BASELINE_ROOT_INVALID")
    require(baseline["fixed_denominator"] == len(expected_application_ids),
            "ECOSYSTEM_STAGE_I3_BASELINE_DENOMINATOR_INVALID")
    baseline_rows = {row["application_id"]: row for row in baseline["applications"]}
    require(list(baseline_rows) == expected_application_ids,
            "ECOSYSTEM_STAGE_I3_BASELINE_ROSTER_INVALID")
    rows = []
    for application_id in expected_application_ids:
        source_instruction_raw, source_instruction, source_instruction_canonical = _load_exact(
            _instruction_path(authoring_root, application_id))
        bound_instruction_raw, bound_instruction, bound_instruction_canonical = _load_exact(
            _instruction_path(bound_root, application_id))
        source_plan_raw, source_plan, source_plan_canonical = _load_exact(
            _plan_path(authoring_root, application_id))
        bound_plan_raw, bound_plan, bound_plan_canonical = _load_exact(
            _plan_path(bound_root, application_id))
        require(bound_instruction_canonical and bound_plan_canonical,
                "ECOSYSTEM_STAGE_I3_PIPELINE_BOUND_INPUT_NONCANONICAL")

        source_instruction = validate_instruction(source_instruction)
        bound_instruction = validate_instruction(bound_instruction)
        source_plan = _validate_legacy_authoring_plan(source_plan, source_instruction)
        bound_plan = validate_plan(bound_plan, expected_instruction=bound_instruction)

        require(source_instruction["application_id"] == application_id
                and bound_instruction["application_id"] == application_id,
                "ECOSYSTEM_STAGE_I3_APPLICATION_INVALID")
        for key in INSTRUCTION_STABLE_FIELDS:
            require(source_instruction[key] == bound_instruction[key],
                    "ECOSYSTEM_STAGE_I3_INSTRUCTION_SEMANTIC_DRIFT:" + key)

        source_semantics = _plan_semantics(source_plan)
        bound_semantics = _plan_semantics(bound_plan)
        require(source_semantics == bound_semantics,
                "ECOSYSTEM_STAGE_I3_PLAN_SEMANTIC_DRIFT")
        source_external = (set(source_plan["required_evidence_roots"])
                           - required_instruction_evidence(source_instruction))
        bound_external = (set(bound_plan["required_evidence_roots"])
                          - required_instruction_evidence(bound_instruction))
        require(source_external == bound_external,
                "ECOSYSTEM_STAGE_I3_EXTERNAL_EVIDENCE_DRIFT")
        baseline_row = baseline_rows[application_id]
        require(baseline_row["stage_i3_instruction_sha256"] == sha256(bound_instruction_raw)
                and baseline_row["stage_i3_plan_sha256"] == sha256(bound_plan_raw)
                and baseline_row["stage_i3_plan_status"] == bound_plan["plan_status"],
                "ECOSYSTEM_STAGE_I3_BASELINE_BINDING_INVALID")

        rows.append({
            "application_id": application_id,
            "authoring_instruction_sha256": sha256(source_instruction_raw),
            "authoring_instruction_root": source_instruction["instruction_root"],
            "authoring_plan_sha256": sha256(source_plan_raw),
            "authoring_plan_root": source_plan["plan_root"],
            "authoring_instruction_canonical": source_instruction_canonical,
            "authoring_plan_canonical": source_plan_canonical,
            "pipeline_bound_instruction_sha256": sha256(bound_instruction_raw),
            "pipeline_bound_instruction_root": bound_instruction["instruction_root"],
            "pipeline_bound_plan_sha256": sha256(bound_plan_raw),
            "pipeline_bound_plan_root": bound_plan["plan_root"],
            "pipeline_bound_instruction_canonical": bound_instruction_canonical,
            "pipeline_bound_plan_canonical": bound_plan_canonical,
            "semantic_root": root(source_semantics),
            "semantic_change": "NONE",
            "binding_change": "PIPELINE_RELEASE_INSTRUCTION_AND_REQUIRED_EVIDENCE_SET",
            "authoring_pipeline_release_sha256": source_instruction["pipeline_release_sha256"],
            "pipeline_bound_release_sha256": bound_instruction["pipeline_release_sha256"],
            "required_evidence_roots_added": sorted(
                set(bound_plan["required_evidence_roots"])
                - set(source_plan["required_evidence_roots"])),
            "required_evidence_roots_removed": sorted(
                set(source_plan["required_evidence_roots"])
                - set(bound_plan["required_evidence_roots"])),
            "authoring_validation_mode": "LEGACY_REQUIRED_EVIDENCE_AUGMENTATION",
            "plan_status": bound_plan["plan_status"],
            "capability_projection_count": len(bound_plan["capability_projections"]),
            "correspondence_case_count": len(bound_plan["correspondence_cases"]),
            "relation_disposition_count": len(bound_plan["relation_dispositions"]),
            "hold_count": len(bound_plan["holds"]),
            "holds_preserved": source_plan["holds"] == bound_plan["holds"],
        })

    body = {
        "schema": "mosaic.ucm.ecosystem-stage-i3-reconciliation.v0.2",
        "fixed_denominator": len(rows),
        "application_ids": expected_application_ids,
        "ecosystem_baseline_sha256": baseline_sha256,
        "ecosystem_baseline_root": baseline["baseline_root"],
        "applications": rows,
        "semantic_changes": 0,
        "binding_only_changes": len(rows),
        "capability_projection_count": sum(row["capability_projection_count"] for row in rows),
        "correspondence_case_count": sum(row["correspondence_case_count"] for row in rows),
        "relation_disposition_count": sum(row["relation_disposition_count"] for row in rows),
        "plan_status_counts": {
            "READY_FOR_SHADOW_REVIEW": sum(
                row["plan_status"] == "READY_FOR_SHADOW_REVIEW" for row in rows),
            "HOLD_FOR_REPAIR": sum(row["plan_status"] == "HOLD_FOR_REPAIR" for row in rows),
        },
        "stage_i3_shadow_authorized": False,
        "application_execution_observed": False,
        "composition_authorized": False,
        "non_claims": [
            "NO_APPLICATION_EXECUTION", "NO_APPLICATION_CONTACT",
            "NO_HOLD_CLEARANCE", "NO_AUTHORITY_GRANT",
        ],
        **BOUNDARY,
    }
    require(all(row["holds_preserved"] for row in rows),
            "ECOSYSTEM_STAGE_I3_HOLD_DRIFT")
    return {**body, "reconciliation_root": root(body)}

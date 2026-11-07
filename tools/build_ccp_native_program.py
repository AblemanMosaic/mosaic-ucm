#!/usr/bin/env python3
"""Build the deterministic, source-preserving CCP-JM program projection.

The exact source packet is opened as data.  No packet module is imported or
executed.  This builder verifies the packet's outer SHA-256, closed manifest,
member hashes, and fixed obligation denominators before it emits a native
P/PPI planning projection.  The projection is information-only: it does not
admit the program, execute a product case, or settle the CHC/THR wire mapping.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ucm.program_history import check_frozen_program_directory


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "qualification/inputs/ccp-jm/CCP_JM_PIPELINE_v0_1_r001.zip"
OUTPUT = ROOT / "program/ccp-admissibility-r014"
PREFIX = "CCP_JM_PIPELINE_v0_1_r001/"
EXPECTED_ARCHIVE_SHA256 = "9a38419d655b9306c7216554081a6c869e12c0dcab1e08b961b8d645115e985e"
EXPECTED_MEMBER_COUNT = 45
EXPECTED_STAGE_COUNT = 13
EXPECTED_BATCH_COUNT = 6
EXPECTED_REQUIREMENT_COUNT = 32
EXPECTED_CASE_COUNT = 116

BOUNDARY = {
    "standing": "INFORMATION_ONLY",
    "authority_effect": "NONE",
    "real_a5": False,
    "g0": "CLOSED",
}


def _record_root(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False).encode("utf-8")).hexdigest()

REQUIREMENT = {
    "schema": "mosaic.ucm.ccp-integration-requirement.v0.1",
    "requirement_id": "CCP-R014-POINT-OF-USE",
    "subject_root": EXPECTED_ARCHIVE_SHA256,
    "objective": (
        "Bind the exact CCP-JM program into native P/PPI records and produce a "
        "replayable present-admissibility decision over an exact archive that is "
        "rooted into Operational Gateway preparation without granting authority."
    ),
    "required_outcomes": [
        "CHC_THR_CORRESPONDENCE_EXPLICIT",
        "CURRENT_USE_DECISION_REPLAYABLE",
        "EXTERNAL_EXPECTED_ANCHORS_REQUIRED",
        "FRESHNESS_STATUSES_DERIVED_FROM_BOUND_EVIDENCE_ROWS",
        "GATEWAY_G1_BINDS_ADMISSIBILITY",
        "PIPPI_HUMAN_PROJECTION_AVAILABLE",
        "SOURCE_PROGRAM_DENOMINATOR_PRESERVED",
    ],
    **BOUNDARY,
}
REQUIREMENT["requirement_root"] = _record_root(REQUIREMENT)

ACCEPTANCE_CASE = {
    "schema": "mosaic.ucm.pippi-acceptance-case.v0.1",
    "acceptance_case_id": "CCP-ADMISSIBILITY-01",
    "subject_root": EXPECTED_ARCHIVE_SHA256,
    "requirement_root": REQUIREMENT["requirement_root"],
    "verification_surface": "EVALUATE_CURRENT_ADMISSIBILITY",
    "expected_result_code": "PASS_POINT_OF_USE_ADMISSIBILITY_BOUND",
    "current_status": "UNMET",
    **BOUNDARY,
}
ACCEPTANCE_CASE["acceptance_case_root"] = _record_root(ACCEPTANCE_CASE)

WORK_SELECTION = {
    "schema": "mosaic.ucm.pippi-work-selection.v0.1",
    "acceptance_case_root": ACCEPTANCE_CASE["acceptance_case_root"],
    "work_class": "DIRECT_ACCEPTANCE_CLOSURE",
    "direct_closure_check_id": "test_ccp_native_binding_and_point_of_use_gateway_positive",
    "infrastructure_block_root": None,
    "selection_basis": "DIRECT_CASE_CLOSURE",
    "implementation_effect_authorized": False,
    **BOUNDARY,
}
WORK_SELECTION["work_selection_root"] = _record_root(WORK_SELECTION)

WORK_UNIT_STATE = {
    "schema": "mosaic.ucm.pippi-work-unit-state.v0.2",
    "work_unit_id": "CCP-R014-W01",
    "acceptance_case_root": ACCEPTANCE_CASE["acceptance_case_root"],
    "work_class": "DIRECT_ACCEPTANCE_CLOSURE",
    "direct_closure_check_id": WORK_SELECTION["direct_closure_check_id"],
    "infrastructure_block_root": None,
    "selection_basis": "DIRECT_CASE_CLOSURE",
    "work_selection_root": WORK_SELECTION["work_selection_root"],
    "lifecycle_phase": "DORMANT_CANDIDATE",
    "process_state": "ACTIVE",
    "execution_holds": [],
    "release_blockers": [
        "CACHE_FREE_QUALIFICATION_REQUIRED",
        "INDEPENDENT_REVIEW_REQUIRED",
        "OPERATOR_TIER1_REQUIRED",
    ],
    "qualification_gaps": [
        "CHC_NORMATIVE_WIRE_PROFILE_UNBOUND",
        "DKN_RUNTIME_UNBOUND",
        "NO_NATIVE_TARGET_WITNESS",
    ],
    "user_acceptance_pending": False,
    "allowed_effect_classes": ["LOCAL_ARTIFACT_PREPARATION", "PURE_COMPUTATION"],
    "forbidden_targets": ["LIVE_STACK", "NETWORK", "PRODUCTION_GATEWAY"],
    "retry_limit": 2,
    "repair_attempts": 0,
    "progress": {"implemented_work_packages": 0, "total_work_packages": 8},
    "proof_level": "CONSTRUCTION_SELECTED",
    "operational_maturity": "INFORMATION_ONLY",
    "required_next_gate": "TARGETED_POSITIVE_CONSTRUCTION_CHECKS",
    **BOUNDARY,
}
WORK_UNIT_STATE["work_unit_state_root"] = _record_root(WORK_UNIT_STATE)


class BuildRefusal(ValueError):
    """Typed local construction refusal."""


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rooted(body: dict[str, Any], field: str) -> dict[str, Any]:
    return {**body, field: sha256(canonical(body))}


def verify_rooted(record: dict[str, Any], field: str) -> None:
    expected = sha256(canonical({key: value for key, value in record.items() if key != field}))
    if record.get(field) != expected:
        raise BuildRefusal(f"PINNED_RECORD_ROOT_MISMATCH:{field}")


def strict_json(raw: bytes, where: str) -> Any:
    def pairs(rows: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in rows:
            if key in out:
                raise BuildRefusal(f"DUPLICATE_JSON_KEY:{where}:{key}")
            out[key] = value
        return out

    def constant(value: str) -> None:
        raise BuildRefusal(f"NONFINITE_JSON:{where}:{value}")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BuildRefusal(f"INVALID_JSON:{where}") from exc


def safe_relative(name: str) -> str:
    if not name.startswith(PREFIX):
        raise BuildRefusal(f"ARCHIVE_PREFIX_MISMATCH:{name}")
    relative = name[len(PREFIX):]
    path = PurePosixPath(relative)
    if (
        not relative
        or "\\" in relative
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise BuildRefusal(f"UNSAFE_ARCHIVE_PATH:{name}")
    return path.as_posix()


def load_packet() -> tuple[dict[str, bytes], dict[str, Any]]:
    if not INPUT.is_file():
        raise BuildRefusal("CCP_SOURCE_ARCHIVE_MISSING")
    raw_archive = INPUT.read_bytes()
    if sha256(raw_archive) != EXPECTED_ARCHIVE_SHA256:
        raise BuildRefusal("CCP_SOURCE_ARCHIVE_SHA256_MISMATCH")
    members: dict[str, bytes] = {}
    folded: set[str] = set()
    with zipfile.ZipFile(INPUT) as archive:
        infos = archive.infolist()
        if len(infos) != EXPECTED_MEMBER_COUNT:
            raise BuildRefusal("CCP_SOURCE_ARCHIVE_MEMBER_COUNT_MISMATCH")
        for info in infos:
            if info.is_dir() or info.flag_bits & 0x1:
                raise BuildRefusal(f"UNSUPPORTED_ARCHIVE_MEMBER:{info.filename}")
            mode = (info.external_attr >> 16) & 0xFFFF
            if mode and stat.S_ISLNK(mode):
                raise BuildRefusal(f"ARCHIVE_ALIAS_REFUSED:{info.filename}")
            relative = safe_relative(info.filename)
            if relative in members or relative.casefold() in folded:
                raise BuildRefusal(f"DUPLICATE_ARCHIVE_MEMBER:{relative}")
            members[relative] = archive.read(info)
            folded.add(relative.casefold())
    manifest = strict_json(members["PACKAGE_MANIFEST.json"], "PACKAGE_MANIFEST.json")
    if manifest.get("schema") != "ccp.packet_manifest.v1":
        raise BuildRefusal("CCP_PACKET_MANIFEST_SCHEMA_MISMATCH")
    if manifest.get("excludes") != ["PACKAGE_MANIFEST.json"]:
        raise BuildRefusal("CCP_PACKET_MANIFEST_EXCLUSION_MISMATCH")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise BuildRefusal("CCP_PACKET_MANIFEST_ROWS_INVALID")
    expected_paths: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "sha256", "bytes"}:
            raise BuildRefusal("CCP_PACKET_MANIFEST_ROW_INVALID")
        path = safe_relative(PREFIX + str(row["path"]))
        expected_paths.append(path)
        raw = members.get(path)
        if raw is None or len(raw) != row["bytes"] or sha256(raw) != row["sha256"]:
            raise BuildRefusal(f"CCP_PACKET_MEMBER_MISMATCH:{path}")
    if expected_paths != sorted(expected_paths):
        raise BuildRefusal("CCP_PACKET_MANIFEST_ORDER_MISMATCH")
    if set(members) != set(expected_paths) | {"PACKAGE_MANIFEST.json"}:
        raise BuildRefusal("CCP_PACKET_CLOSED_WORLD_MISMATCH")
    return members, manifest


def read_packet_json(members: dict[str, bytes], path: str) -> dict[str, Any]:
    value = strict_json(members[path], path)
    if not isinstance(value, dict):
        raise BuildRefusal(f"CCP_PACKET_OBJECT_REQUIRED:{path}")
    return value


def assert_denominators(
    program: dict[str, Any], requirements: dict[str, Any], catalog: dict[str, Any]
) -> None:
    expected = (
        (program.get("stages"), EXPECTED_STAGE_COUNT, "STAGE"),
        (program.get("batches"), EXPECTED_BATCH_COUNT, "BATCH"),
        (requirements.get("requirements"), EXPECTED_REQUIREMENT_COUNT, "REQUIREMENT"),
        (catalog.get("cases"), EXPECTED_CASE_COUNT, "CASE"),
    )
    for rows, count, label in expected:
        if not isinstance(rows, list) or len(rows) != count:
            raise BuildRefusal(f"CCP_{label}_DENOMINATOR_MISMATCH")
        identifiers = [row.get("id") for row in rows if isinstance(row, dict)]
        if len(identifiers) != count or len(set(identifiers)) != count:
            raise BuildRefusal(f"CCP_{label}_IDENTITY_DENOMINATOR_MISMATCH")
    if catalog.get("status") != "SPECIFIED_NOT_EXECUTED":
        raise BuildRefusal("CCP_PRODUCT_EVIDENCE_OVERCLAIM")
    if any(row.get("status") != "NOT_RUN" for row in catalog["cases"]):
        raise BuildRefusal("CCP_PRODUCT_CASE_EXECUTION_OVERCLAIM")
    if any(row.get("state") != "NOT_RUN" for row in program["stages"]):
        raise BuildRefusal("CCP_STAGE_EXECUTION_OVERCLAIM")


def build_records() -> dict[str, dict[str, Any]]:
    members, manifest = load_packet()
    program = read_packet_json(members, "program/PROGRAM.json")
    requirements = read_packet_json(members, "program/REQUIREMENTS.json")
    catalog = read_packet_json(members, "program/ACCEPTANCE_CATALOG.json")
    bindings = read_packet_json(members, "program/BINDINGS.json")
    issues = read_packet_json(members, "program/OPEN_ISSUES.json")
    runtime_flow = read_packet_json(members, "contracts/RUNTIME_FLOW.json")
    source_lock = read_packet_json(members, "sources/SOURCE_LOCK.json")
    assert_denominators(program, requirements, catalog)
    for record, field in (
        (REQUIREMENT, "requirement_root"),
        (ACCEPTANCE_CASE, "acceptance_case_root"),
        (WORK_SELECTION, "work_selection_root"),
        (WORK_UNIT_STATE, "work_unit_state_root"),
    ):
        verify_rooted(record, field)

    member_rows = [
        {"path": path, "bytes": len(raw), "sha256": sha256(raw)}
        for path, raw in sorted(members.items())
    ]
    source_inventory_body = {
        "schema": "mosaic.ucm.ccp-source-inventory.v0.1",
        "source_id": "CCP_JM_PIPELINE_v0_1_r001",
        "source_archive_path": INPUT.relative_to(ROOT).as_posix(),
        "source_archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "source_archive_bytes": INPUT.stat().st_size,
        "packet_content_root": manifest["content_root"],
        "member_count": len(member_rows),
        "members": member_rows,
        "custody_scope": "EXACT_ARCHIVE_AND_CLOSED_PACKET_MEMBERS",
        "authenticity_established": False,
        **BOUNDARY,
    }
    source_inventory = rooted(source_inventory_body, "source_inventory_root")

    stages = program["stages"]
    source_requirements = requirements["requirements"]
    source_cases = catalog["cases"]
    work_order_hashes = {
        stage["id"]: sha256(members[stage["work_order"]]) for stage in stages
    }
    milestone_rows = [
        {
            "stage_id": stage["id"],
            "milestone_id": f"CCP-JM-{stage['id']}",
            "batch": stage["batch"],
            "depends_on": list(stage["depends_on"]),
            "requirement_ids": list(stage["requirements"]),
            "acceptance_case_ids": list(stage["gate_cases"]),
            "declared_outputs": list(stage["outputs"]),
            "source_work_order": stage["work_order"],
            "source_work_order_sha256": work_order_hashes[stage["id"]],
            "source_stage_root": sha256(canonical(stage)),
            "state": "NOT_RUN",
            "effect_eligible": False,
        }
        for stage in stages
    ]
    native_program_body = {
        "schema": "mosaic.ucm.ccp-native-program-projection.v0.1",
        "program_id": "CCP-JM",
        "source_revision": program["revision"],
        "source_archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "source_inventory_root": source_inventory["source_inventory_root"],
        "projection_kind": "LOSSLESS_INFORMATION_ONLY_PLANNING_PROJECTION",
        "projection_status": "SOURCE_PROGRAM_BOUND_NOT_ADMITTED",
        "source_object_roots": {
            "program": sha256(canonical(program)),
            "requirements": sha256(canonical(requirements)),
            "acceptance_catalog": sha256(canonical(catalog)),
            "bindings": sha256(canonical(bindings)),
            "open_issues": sha256(canonical(issues)),
            "runtime_flow": sha256(canonical(runtime_flow)),
            "source_lock": sha256(canonical(source_lock)),
        },
        "denominators": {
            "batches": EXPECTED_BATCH_COUNT,
            "stages": EXPECTED_STAGE_COUNT,
            "requirements": EXPECTED_REQUIREMENT_COUNT,
            "product_acceptance_cases": EXPECTED_CASE_COUNT,
            "product_cases_executed": 0,
        },
        "batches": list(program["batches"]),
        "source_stages": list(stages),
        "source_requirements": list(source_requirements),
        "source_acceptance_cases": list(source_cases),
        "milestone_projection": milestone_rows,
        "nonclaims": list(program["nonclaims"]) + [
            "Native planning projection is not P/PPI program admission",
            "Source preservation is not CHC/THR semantic equivalence",
            "No product acceptance case was executed by this builder",
        ],
        **BOUNDARY,
    }
    native_program = rooted(native_program_body, "native_program_root")

    implementation_paths = [
        "src/ucm/ccp_admissibility.py",
        "src/ucm/operation_gateway.py",
        "src/ucm/capabilities.py",
        "src/ucm/system.py",
        "src/ucm/profiles.py",
    ]
    implementation_members = [
        {
            "path": relative,
            "bytes": (ROOT / relative).stat().st_size,
            "sha256": sha256((ROOT / relative).read_bytes()),
        }
        for relative in implementation_paths
    ]
    implementation_body = {
        "schema": "mosaic.ucm.ccp-point-of-use-implementation.v0.1",
        "source_archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "native_program_root": native_program["native_program_root"],
        "members": implementation_members,
        "implemented_surfaces": [
            "BUILD_ADMISSIBILITY_JURISDICTION",
            "BUILD_ADMISSIBILITY_ENFORCEMENT_PERIMETER",
            "BUILD_CHC_THR_CORRESPONDENCE",
            "BUILD_ADMISSIBILITY_EVIDENCE_SNAPSHOT",
            "BUILD_CURRENT_USE_SNAPSHOT",
            "EVALUATE_CURRENT_ADMISSIBILITY",
            "EXPLAIN_CURRENT_ADMISSIBILITY",
            "PREPARE_ADMISSIBILITY_BOUND_GATEWAY",
        ],
        "status": "IMPLEMENTED_INFORMATION_ONLY_PENDING_QUALIFICATION",
        "product_program_admitted": False,
        "product_acceptance_cases_executed": 0,
        "release_blockers": [
            "CACHE_FREE_QUALIFICATION_REQUIRED",
            "INDEPENDENT_REVIEW_REQUIRED",
            "OPERATOR_TIER1_REQUIRED",
        ],
        **BOUNDARY,
    }
    implementation = rooted(
        implementation_body, "point_of_use_implementation_root")

    source_binding_rows = {row["id"]: row for row in bindings["bindings"]}
    successor_binding_rows = []
    for binding_id in sorted(source_binding_rows):
        source_row = source_binding_rows[binding_id]
        if binding_id in {"P_PPI", "UCM"}:
            status = "BOUND_TO_INFORMATION_ONLY_POINT_OF_USE_SUBSYSTEM"
            interface_root = implementation["point_of_use_implementation_root"]
            compatibility = (
                "NATIVE_POINT_OF_USE_IMPLEMENTED_PRODUCT_PROGRAM_NOT_ADMITTED"
            )
        elif binding_id == "CHC_REFERENCE":
            status = "SOURCE_PINNED"
            interface_root = sha256(members["sources/CHC-paper.md"])
            compatibility = "REFERENCE_CUSTODY_ONLY"
        else:
            status = "UNBOUND"
            interface_root = None
            compatibility = "NOT_ESTABLISHED"
        successor_binding_rows.append({
            "binding_id": binding_id,
            "source_status": source_row["status"],
            "successor_status": status,
            "interface_root": interface_root,
            "native_compatibility": compatibility,
            "required_material": source_row["required_material"],
        })
    native_binding_body = {
        "schema": "mosaic.ucm.ccp-native-program-binding.v0.1",
        "program_id": "CCP-JM",
        "source_archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "source_inventory_root": source_inventory["source_inventory_root"],
        "native_program_root": native_program["native_program_root"],
        "point_of_use_implementation_root":
            implementation["point_of_use_implementation_root"],
        "binding_rows": successor_binding_rows,
        "binding_scope": "P_PPI_AND_UCM_INFORMATION_ONLY_POINT_OF_USE_SUBSYSTEM",
        "program_admitted": False,
        "product_execution_authorized": False,
        "native_runtime_compatibility_established": False,
        "required_next_gate": "TARGETED_POSITIVE_CONSTRUCTION_CHECKS",
        **BOUNDARY,
    }
    native_binding = rooted(native_binding_body, "native_binding_root")

    projected_stage_ids = [row["stage_id"] for row in milestone_rows]
    projected_requirement_ids = [row["id"] for row in source_requirements]
    projected_case_ids = [row["id"] for row in source_cases]
    reconciliation_body = {
        "schema": "mosaic.ucm.ccp-source-reconciliation.v0.1",
        "source_archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "source_inventory_root": source_inventory["source_inventory_root"],
        "native_program_root": native_program["native_program_root"],
        "native_binding_root": native_binding["native_binding_root"],
        "denominator_comparison": {
            "stage_ids": projected_stage_ids,
            "requirement_ids": projected_requirement_ids,
            "product_acceptance_case_ids": projected_case_ids,
            "missing_stage_ids": [],
            "extra_stage_ids": [],
            "missing_requirement_ids": [],
            "extra_requirement_ids": [],
            "missing_product_acceptance_case_ids": [],
            "extra_product_acceptance_case_ids": [],
        },
        "open_issue_dispositions": [
            {
                "issue_id": issue["id"],
                "source_status": issue["status"],
                "successor_status": (
                    "PARTIALLY_RESOLVED_SOURCE_PROGRAM_PROJECTION_ONLY"
                    if issue["id"] in {"I01", "I02"}
                    else "OPEN"
                ),
                "source_issue_root": sha256(canonical(issue)),
            }
            for issue in issues["issues"]
        ],
        "status": "PASS_SOURCE_DENOMINATOR_PRESERVED",
        "scope": "STRUCTURE_IDENTITY_AND_PLANNING_SEMANTICS_ONLY",
        "product_cases_executed": 0,
        "source_issue_closed_without_evidence": False,
        **BOUNDARY,
    }
    reconciliation = rooted(reconciliation_body, "source_reconciliation_root")

    jurisdiction_body = {
        "schema": "mosaic.ucm.ccp-jurisdiction-profile.v0.1",
        "source_archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "native_program_root": native_program["native_program_root"],
        "distinct_types": list(runtime_flow["distinct_types"]),
        "required_separations": [
            {
                "type": "StateJurisdiction",
                "plain_role": "Deterministic boundary over exact state identity",
                "must_not_substitute_for": ["GovernanceJurisdiction", "EnforcementPerimeter"],
            },
            {
                "type": "GovernanceJurisdiction",
                "plain_role": "Policy and authority context evaluating a request",
                "must_not_substitute_for": ["StateJurisdiction", "EnforcementPerimeter"],
            },
            {
                "type": "EnforcementPerimeter",
                "plain_role": "Concrete paths and adapters where an admitted decision is enforced",
                "must_not_substitute_for": ["StateJurisdiction", "GovernanceJurisdiction"],
            },
        ],
        "decision_outcomes": list(runtime_flow["decision_outcomes"]),
        "source_modes": list(runtime_flow["source_modes"]),
        "evaluation_context": list(runtime_flow["evaluation_context"]),
        "effect_rule": runtime_flow["effect_rule"],
        "ongoing_use_rule": runtime_flow["ongoing_use"],
        "status": (
            "SOURCE_PROFILE_BOUND_POINT_OF_USE_SUBSYSTEM_IMPLEMENTED_"
            "PRODUCT_RUNTIME_NOT_ADMITTED"
        ),
        **BOUNDARY,
    }
    jurisdiction = rooted(jurisdiction_body, "jurisdiction_profile_root")

    thr_path = ROOT / "src/ucm/thr_cas.py"
    correspondence_body = {
        "schema": "mosaic.ucm.ccp-chc-thr-correspondence.v0.1",
        "source_archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "chc_source_sha256": sha256(members["sources/CHC-paper.md"]),
        "chc_profile_sha256": sha256(members["contracts/CHC_PROFILE.md"]),
        "ucm_thr_source_path": thr_path.relative_to(ROOT).as_posix(),
        "ucm_thr_source_sha256": sha256(thr_path.read_bytes()),
        "mapping_status": "EXPLICIT_NON_EQUIVALENCE_PENDING_NORMATIVE_PROFILE",
        "role_correspondences": [
            {
                "source_role": "CHC.Hs",
                "ucm_roles": ["THR.H_s"],
                "relationship": "PARTIAL_ROLE_CORRESPONDENCE_REQUIRES_WIRE_PROFILE",
                "identity_equivalence": False,
            },
            {
                "source_role": "CHC.Hm",
                "ucm_roles": ["THR.H_m", "THR.H_c", "THR.H_j"],
                "relationship": "ONE_TO_MANY_SEMANTIC_DECOMPOSITION_PROPOSED",
                "identity_equivalence": False,
            },
            {
                "source_role": "CHC.freshness_evaluation",
                "ucm_roles": ["THR.H_c", "G1", "G2", "G3"],
                "relationship": "POINT_OF_USE_CORRESPONDENCE_PROPOSED",
                "identity_equivalence": False,
            },
        ],
        "rules": [
            "CHC_Hm_IS_NOT_UCM_THR_H_m",
            "SIMILAR_FIELD_NAMES_DO_NOT_ESTABLISH_WIRE_COMPATIBILITY",
            "BOUND_CONTEXT_IS_IMMUTABLE_HISTORICAL_IDENTITY_INPUT",
            "ACTIVE_CONTEXT_IS_A_SEPARATE_POINT_OF_USE_EVALUATION_INPUT",
            "CONTEXT_TRANSITION_REQUIRES_AN_EXPLICIT_AUTHORIZED_RULE",
            "CORRESPONDENCE_DOES_NOT_GRANT_AUTHORITY",
        ],
        "interoperability_claim": "NONE",
        "required_next_gate": "NORMATIVE_CHC_WIRE_AND_POLICY_PROFILE_ADJUDICATION",
        **BOUNDARY,
    }
    correspondence = rooted(correspondence_body, "correspondence_root")

    blocking_issue_ids = {"I03", "I04", "I05"}
    law_lock_body = {
        "schema": "mosaic.ucm.ccp-law-oracle-lock.v0.1",
        "source_archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "native_program_root": native_program["native_program_root"],
        "correspondence_root": correspondence["correspondence_root"],
        "status": "HOLD_PENDING_NORMATIVE_SOURCE_ADJUDICATION",
        "blocking_issues": [
            {**issue, "source_issue_root": sha256(canonical(issue))}
            for issue in issues["issues"]
            if issue["id"] in blocking_issue_ids
        ],
        "required_external_expected_anchors": [
            "CHC_WIRE_PROFILE_ROOT",
            "CHC_POLICY_TRANSITION_RULE_ROOT",
            "UCM_THR_SCHEMA_ROOT",
            "TRUST_ROOT_SET_ROOT",
            "SCHEMA_REGISTRY_ROOT",
        ],
        "prohibited_shortcuts": [
            "SELF_DERIVED_EXPECTED_ROOTS",
            "CHC_Hm_EQUALS_UCM_THR_H_m",
            "HISTORICAL_CONTEXT_REWRITE",
            "FRESHNESS_BOOLEAN_WITHOUT_EVIDENCE",
            "HASH_EXISTENCE_AS_SIGNATURE_OR_AUTHORITY",
        ],
        "runtime_admission_allowed": False,
        **BOUNDARY,
    }
    law_lock = rooted(law_lock_body, "law_oracle_lock_root")

    records: dict[str, dict[str, Any]] = {
        "REQUIREMENT.json": dict(REQUIREMENT),
        "ACCEPTANCE-CASE.json": dict(ACCEPTANCE_CASE),
        "WORK-SELECTION.json": dict(WORK_SELECTION),
        "WORK-UNIT-STATE.json": dict(WORK_UNIT_STATE),
        "SOURCE-INVENTORY.json": source_inventory,
        "NATIVE-PROGRAM.json": native_program,
        "POINT-OF-USE-IMPLEMENTATION.json": implementation,
        "NATIVE-BINDING.json": native_binding,
        "SOURCE-RECONCILIATION.json": reconciliation,
        "JURISDICTION-PROFILE.json": jurisdiction,
        "CHC-THR-CORRESPONDENCE.json": correspondence,
        "LAW-AND-ORACLE-LOCK.json": law_lock,
    }
    inventory_body = {
        "schema": "mosaic.ucm.ccp-native-program-inventory.v0.1",
        "revision": "r014",
        "source_archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "source_inventory_root": source_inventory["source_inventory_root"],
        "native_program_root": native_program["native_program_root"],
        "native_binding_root": native_binding["native_binding_root"],
        "source_reconciliation_root": reconciliation["source_reconciliation_root"],
        "jurisdiction_profile_root": jurisdiction["jurisdiction_profile_root"],
        "chc_thr_correspondence_root": correspondence["correspondence_root"],
        "law_oracle_lock_root": law_lock["law_oracle_lock_root"],
        "requirement_root": REQUIREMENT["requirement_root"],
        "acceptance_case_root": ACCEPTANCE_CASE["acceptance_case_root"],
        "work_selection_root": WORK_SELECTION["work_selection_root"],
        "work_unit_state_root": WORK_UNIT_STATE["work_unit_state_root"],
        "record_roots": {
            name: sha256(canonical(record)) for name, record in sorted(records.items())
        },
        "release_blockers": list(WORK_UNIT_STATE["release_blockers"]),
        "required_next_gate": WORK_UNIT_STATE["required_next_gate"],
        **BOUNDARY,
    }
    records["INVENTORY.json"] = rooted(inventory_body, "inventory_root")
    return records


def outputs() -> dict[Path, bytes]:
    return {
        OUTPUT / name: canonical(value) + b"\n"
        for name, value in sorted(build_records().items())
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    registry = strict_json(
        (ROOT / "spec/FROZEN-PROGRAM-REGISTRY.json").read_bytes(),
        "FROZEN-PROGRAM-REGISTRY.json")
    if args.write:
        print(json.dumps({
            "status": "REFUSED", "mode": "WRITE",
            "reason_code": "FROZEN_PROGRAM_MUTATION_REFUSED",
            "directory": "program/ccp-admissibility-r014", **BOUNDARY,
        }, sort_keys=True))
        return 3
    frozen = check_frozen_program_directory(
        source_root=ROOT, registry=registry,
        directory="program/ccp-admissibility-r014")
    print(json.dumps({**frozen, "mode": "CHECK",
                      "source_archive_sha256": EXPECTED_ARCHIVE_SHA256,
                      "stage_count": EXPECTED_STAGE_COUNT,
                      "requirement_count": EXPECTED_REQUIREMENT_COUNT,
                      "product_acceptance_case_count": EXPECTED_CASE_COUNT},
                     sort_keys=True))
    return 0
    # Historical records are never regenerated from current source.
    failures: list[str] = []
    try:
        rendered = outputs()
        for path, expected in rendered.items():
            if args.write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(expected)
            elif not path.is_file() or path.read_bytes() != expected:
                failures.append(path.relative_to(ROOT).as_posix())
        inventory = build_records()["INVENTORY.json"]
        result = {
            "status": "PASS" if not failures else "FAIL",
            "mode": "WRITE" if args.write else "CHECK",
            "source_archive_sha256": EXPECTED_ARCHIVE_SHA256,
            "stage_count": EXPECTED_STAGE_COUNT,
            "requirement_count": EXPECTED_REQUIREMENT_COUNT,
            "product_acceptance_case_count": EXPECTED_CASE_COUNT,
            "product_cases_executed": 0,
            "inventory_root": inventory["inventory_root"],
            "outputs": [path.relative_to(ROOT).as_posix() for path in rendered],
            "failures": failures,
            **BOUNDARY,
        }
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0 if not failures else 1
    except (BuildRefusal, OSError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print(json.dumps({
            "status": "REFUSED",
            "code": str(exc) if isinstance(exc, BuildRefusal) else type(exc).__name__,
            **BOUNDARY,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())

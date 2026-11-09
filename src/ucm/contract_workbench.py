"""Deterministic authoring, migration, and explanation aids for UCM contracts.

The functions in this module are writer and reviewer aids.  They never execute
an application, grant authority, or turn a draft into an accepted contract.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY, make_contract, validate_contract as validate_amcas
from .authoring import lint_amcas_contract, lint_realization_contract
from .realization import (select_configuration, validate_configuration,
                          validate_contract as validate_realization)


CONTRACT_KINDS = {"REALIZATION", "AMCAS"}


def _draft_root(value: dict[str, Any], field: str) -> dict[str, Any]:
    body = {key: deepcopy(item) for key, item in value.items() if key != field}
    return {**body, field: root(body)}


def initialize_realization_contract(*, contract_id: str, subject_id: str,
                                    subject_root: str,
                                    description: str) -> dict[str, Any]:
    """Create a small, valid, deliberately unbound realization contract."""
    require(type(contract_id) is str and contract_id, "UCM_CONTRACT_ID_INVALID")
    require(type(subject_id) is str and subject_id, "UCM_SUBJECT_ID_INVALID")
    require_root(subject_root)
    require(type(description) is str and description.strip(),
            "UCM_CONTRACT_DESCRIPTION_INVALID")
    body = {
        "schema": "mosaic.realization-space-contract.v0.1",
        "contract_id": contract_id,
        "contract_version": "0.1.0-draft",
        "description": description.strip(),
        "subject": {
            "subject_id": subject_id,
            "subject_schema": "mosaic.ucm.unbound-subject.v0.1",
            "authority_owner": "UNBOUND",
            "source_roots": [f"sha256:{subject_root}"],
            "preserved_identity": ["EXACT_SUBJECT_ROOT"],
            "forbidden_overrides": ["AUTHORITY", "IDENTITY"],
        },
        "possibility": {
            "intended_variation": ["AUTHOR_DEFINED_CONFIGURATION"],
            "excluded_claims": ["AUTHORITY_GRANT", "DEPLOYMENT_APPROVAL"],
        },
        "axes": [{
            "id": "PROFILE", "label": "Unbound authoring profile",
            "value_type": "ENUM", "domain": {"values": ["BOUND", "UNBOUND"]},
            "default": "UNBOUND", "ownership": "AUTHORIAL",
            "mutability": "INSTANCE", "continuity": "DISCRETE",
            "authority_effect": "NONE",
        }],
        "constraints": [{
            "id": "PROFILE_REMAINS_UNBOUND", "kind": "CLAIM_BOUNDARY",
            "severity": "HARD", "operator": "EQUALS",
            "terms": {"axis": "PROFILE", "value": "UNBOUND"},
            "explanation": "The scaffold is not an admitted operational profile.",
            "refusal_code": "UCM_DRAFT_PROFILE_BOUND",
        }],
        "capabilities": ["VALIDATE", "EXPLAIN", "TRACE"],
        "selection": {"default_policy": "EXACT_DEFAULTS",
                      "seed_required_for_non_unique": False,
                      "fallback_policy": "REFUSE"},
        "lowering": {"targets": [{
            "target_id": "UNBOUND_TARGET", "runtime_family": "UNBOUND",
            "adapter_version": "0.1.0-draft", "required_capabilities": [],
            "optional_capabilities": [],
            "preservation_criteria": ["EXACT_SUBJECT_ROOT"],
            "known_losses": [], "fallbacks": [],
        }], "allowed_results": ["REFUSED"]},
        "evidence": {
            "required_roots": ["SUBJECT_ROOT"],
            "required_fields": ["standing", "authority_effect"],
            "non_claims": ["NOT_CAMPAIGN_READY", "NOT_EXECUTION_AUTHORITY"],
        },
        "authority": {
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "self_admission": False, "release_gate": False,
            "track_a_dependency": "NONE",
            "claim_boundary": "AUTHORING_SCAFFOLD_ONLY",
        },
    }
    return validate_realization(_draft_root(body, "root"))


def compile_authoring_profile(source: str) -> dict[str, Any]:
    """Compile the small line-oriented writer profile into canonical RSC JSON.

    The profile intentionally covers only enum and boolean axes plus hard
    equality constraints.  Authors use canonical JSON for richer semantics.
    """
    require(type(source) is str and source.strip(), "UCM_AUTHORING_PROFILE_EMPTY")
    scalars: dict[str, str] = {}
    axis_rows: dict[str, str] = {}
    constraint_rows: dict[str, str] = {}
    for number, raw in enumerate(source.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        require("=" in line, "UCM_AUTHORING_PROFILE_SYNTAX", detail=str(number))
        key, value = (part.strip() for part in line.split("=", 1))
        require(key and value, "UCM_AUTHORING_PROFILE_SYNTAX", detail=str(number))
        target = (axis_rows if key.startswith("axis.") else
                  constraint_rows if key.startswith("require.") else scalars)
        require(key not in target, "UCM_AUTHORING_PROFILE_DUPLICATE", detail=key)
        target[key] = value
    required = {"contract_id", "subject_id", "subject_root", "description"}
    require(set(scalars) == required, "UCM_AUTHORING_PROFILE_FIELDS_INVALID",
            detail=",".join(sorted(set(scalars) ^ required)))
    require_root(scalars["subject_root"])
    axes = []
    for key, expression in sorted(axis_rows.items()):
        axis_id = key.removeprefix("axis.")
        parts = expression.split(":")
        require(len(parts) in {2, 3}, "UCM_AUTHORING_AXIS_INVALID", detail=axis_id)
        kind = parts[0].upper()
        if kind == "BOOLEAN":
            require(len(parts) == 2 and parts[1].lower() in {"true", "false"},
                    "UCM_AUTHORING_AXIS_INVALID", detail=axis_id)
            domain, default = {}, parts[1].lower() == "true"
        else:
            require(kind == "ENUM" and len(parts) == 3,
                    "UCM_AUTHORING_AXIS_INVALID", detail=axis_id)
            values, default = parts[1].split("|"), parts[2]
            require(all(values) and len(values) == len(set(values)) and default in values,
                    "UCM_AUTHORING_AXIS_INVALID", detail=axis_id)
            domain = {"values": values}
        axes.append({"id": axis_id, "label": axis_id.replace("_", " ").title(),
                     "value_type": kind, "domain": domain, "default": default,
                     "ownership": "AUTHORIAL", "mutability": "INSTANCE",
                     "continuity": "DISCRETE", "authority_effect": "NONE"})
    require(bool(axes), "UCM_AUTHORING_AXES_EMPTY")
    axis_map = {row["id"]: row for row in axes}
    constraints = []
    for key, expression in sorted(constraint_rows.items()):
        constraint_id = key.removeprefix("require.")
        require("==" in expression, "UCM_AUTHORING_CONSTRAINT_INVALID",
                detail=constraint_id)
        axis_id, raw_value = (part.strip() for part in expression.split("==", 1))
        require(axis_id in axis_map, "UCM_AUTHORING_CONSTRAINT_AXIS_UNKNOWN",
                detail=axis_id)
        axis = axis_map[axis_id]
        value: Any = raw_value
        if axis["value_type"] == "BOOLEAN":
            require(raw_value.lower() in {"true", "false"},
                    "UCM_AUTHORING_CONSTRAINT_INVALID", detail=constraint_id)
            value = raw_value.lower() == "true"
        constraints.append({
            "id": constraint_id, "kind": "INVARIANT", "severity": "HARD",
            "operator": "EQUALS", "terms": {"axis": axis_id, "value": value},
            "explanation": f"Author profile requires {axis_id} == {raw_value}.",
            "refusal_code": f"{constraint_id}_REFUSED",
        })
    require(bool(constraints), "UCM_AUTHORING_CONSTRAINTS_EMPTY")
    body = {
        "schema": "mosaic.realization-space-contract.v0.1",
        "contract_id": scalars["contract_id"], "contract_version": "0.1.0-draft",
        "description": scalars["description"],
        "subject": {"subject_id": scalars["subject_id"],
                    "subject_schema": "mosaic.ucm.unbound-subject.v0.1",
                    "authority_owner": "UNBOUND",
                    "source_roots": [f"sha256:{scalars['subject_root']}"],
                    "preserved_identity": ["EXACT_SUBJECT_ROOT"],
                    "forbidden_overrides": ["AUTHORITY", "IDENTITY"]},
        "possibility": {"intended_variation": ["DECLARED_AXES_ONLY"],
                        "excluded_claims": ["AUTHORITY_GRANT", "DEPLOYMENT_APPROVAL"]},
        "axes": axes, "constraints": constraints,
        "capabilities": ["VALIDATE", "EXPLAIN", "TRACE"],
        "selection": {"default_policy": "EXACT_DEFAULTS",
                      "seed_required_for_non_unique": False, "fallback_policy": "REFUSE"},
        "lowering": {"targets": [{"target_id": "UNBOUND_TARGET",
                                    "runtime_family": "UNBOUND", "adapter_version": "0.1.0-draft",
                                    "required_capabilities": [], "optional_capabilities": [],
                                    "preservation_criteria": ["EXACT_SUBJECT_ROOT"],
                                    "known_losses": [], "fallbacks": []}],
                     "allowed_results": ["REFUSED"]},
        "evidence": {"required_roots": ["SUBJECT_ROOT"],
                     "required_fields": ["standing", "authority_effect"],
                     "non_claims": ["NOT_CAMPAIGN_READY", "NOT_EXECUTION_AUTHORITY"]},
        "authority": {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
                      "self_admission": False, "release_gate": False,
                      "track_a_dependency": "NONE",
                      "claim_boundary": "AUTHORING_SCAFFOLD_ONLY"},
    }
    contract = validate_realization(_draft_root(body, "root"))
    result_body = {"schema": "mosaic.ucm.authoring-profile-compilation.v0.1",
                   "source_root": root({"source": source}), "contract": contract,
                   "status": "PASS_COMPILED_DRAFT", **BOUNDARY}
    return {**result_body, "compilation_root": root(result_body)}


def initialize_amcas_contract(*, integration_id: str, application_id: str,
                              application_name: str, subject_root: str,
                              manifest_root: str,
                              realization_contract: dict[str, Any]) -> dict[str, Any]:
    realization = validate_realization(realization_contract)
    require_root(subject_root); require_root(manifest_root)
    return make_contract(
        integration_id=integration_id,
        application={"id": application_id, "name": application_name,
                     "version": "0.1.0-draft"},
        subject={"source_root": subject_root, "manifest_root": manifest_root,
                 "path_policy": "PORTABLE_POSIX_RELATIVE_V1"},
        identities={"user_required": False, "agent_required": False,
                    "jurisdiction": {"namespace_id": application_id,
                                     "universe_root": None, "epoch_id": None,
                                     "semantic_namespace": None},
                    "session_distinct": True, "possession_required": False,
                    "delegation_required": False},
        cm1={"membership_policy": "ALL_APPLICABLE_REQUIREMENTS_PASS",
             "requirements": [{
                 "id": "EXACT_SUBJECT", "kind": "EVIDENCE",
                 "statement": "Bind the exact application subject before review.",
                 "subject_root": subject_root,
                 "verifier": "AMCAS_SOURCE_BINDING_V1",
                 "evidence_required": True, "applicability": "REQUIRED",
             }]},
        cm2={"selection_policy": "CM1_THEN_CM2_LEXICOGRAPHIC",
             "preferences": []},
        capabilities=[], effects=[],
        dependencies=[{"id": "UCM_CORE", "kind": "TOOL",
                       "root": root({"name": "mosaic-ucm", "version": "v0.1"}),
                       "required": True}],
        acceptance=[{"id": "SOURCE_BOUND", "obligation": "CM1:EXACT_SUBJECT",
                     "evidence_schema": "mosaic.source-binding.v0.1",
                     "required": True}],
        portability={"profiles": ["JOURNAL"], "journal_export_required": True,
                     "offline_closure_required": True},
        reporting={"required_sections": ["requirements", "capabilities", "operations",
                                         "findings", "limitations", "portable_artifacts"],
                   "progress_channel": "NONSEMANTIC_JSONL_V1"},
        realization_contract=realization,
        integration_boundary={
            "semantic_authority": f"{application_id}.NATIVE",
            "effect_executor": f"{application_id}.NATIVE",
            "identity_binding_status": "UNBOUND",
            "jurisdiction_binding_status": "UNBOUND",
            "gate_namespace": "UCM.INTEGRATION",
            "control_plane_root": root({"application_id": application_id,
                                        "status": "UNBOUND"}),
        })


def doctor_contract(kind: str, contract: Any) -> dict[str, Any]:
    normalized = kind.upper()
    require(normalized in CONTRACT_KINDS, "UCM_CONTRACT_KIND_INVALID")
    lint = (lint_realization_contract(contract) if normalized == "REALIZATION"
            else lint_amcas_contract(contract))
    blocking = [row for row in lint["issues"] if row["severity"] == "ERROR"]
    placeholders: list[str] = []
    if normalized == "REALIZATION" and type(contract) is dict:
        if contract.get("subject", {}).get("authority_owner") == "UNBOUND":
            placeholders.append("SUBJECT_AUTHORITY_OWNER_UNBOUND")
        if contract.get("authority", {}).get("claim_boundary") in {
                "AUTHORING_SCAFFOLD_ONLY", "UNBOUND_CONFIGURATION_ONLY"}:
            placeholders.append("CLAIM_BOUNDARY_UNBOUND")
    if normalized == "AMCAS" and type(contract) is dict:
        boundary = contract.get("integration_boundary", {})
        for field in ("identity_binding_status", "jurisdiction_binding_status"):
            if boundary.get(field) == "UNBOUND":
                placeholders.append(field.upper() + "_UNBOUND")
    if blocking:
        readiness = "REFUSED_INVALID"
    elif placeholders:
        readiness = "PASS_AUTHORING_ONLY"
    else:
        readiness = "PASS_CAMPAIGN_READY"
    body = {
        "schema": "mosaic.ucm.contract-doctor.v0.1",
        "contract_kind": normalized,
        "contract_root": lint["contract_root"],
        "lint_root": lint["lint_root"],
        "blocking_issues": blocking,
        "unbound_markers": sorted(placeholders),
        "readiness": readiness,
        "non_claims": ["READINESS_IS_NOT_AUTHORITY", "NO_EFFECT_EXECUTED"],
        **BOUNDARY,
    }
    return {**body, "doctor_root": root(body)}


def classify_contract_compatibility(*, predecessor: Any, successor: Any,
                                    known_roots: list[str]) -> dict[str, Any]:
    require(type(predecessor) is dict and type(successor) is dict,
            "UCM_MIGRATION_INPUT_INVALID")
    require(type(known_roots) is list and len(known_roots) == len(set(known_roots)),
            "UCM_MIGRATION_HISTORY_INVALID")
    for value in known_roots:
        require_root(value)
    before, after = root(predecessor), root(successor)
    if before == after:
        status, reasons = "SUPPORTED_EXACT", []
    elif successor.get("revision", {}).get("predecessor_root") == before:
        status, reasons = "SUPPORTED_SUCCESSOR", []
    elif before in known_roots:
        status, reasons = "NEEDS_DECLARED_MIGRATION", ["SUCCESSOR_DOES_NOT_NAME_PREDECESSOR"]
    else:
        status, reasons = "REJECTED_UNKNOWN_PREDECESSOR", ["PREDECESSOR_NOT_IN_HISTORY"]
    body = {
        "schema": "mosaic.ucm.contract-compatibility.v0.1",
        "predecessor_root": before, "successor_root": after,
        "known_history_root": root(sorted(known_roots)),
        "status": status, "reason_codes": reasons,
        "journal_rule": ("OLD_EVENTS_REMAIN_VALID_UNDER_THEIR_PINNED_CONTRACT;"
                         "NEW_EVENTS_REQUIRE_THE_SUCCESSOR_ROOT"),
        **BOUNDARY,
    }
    return {**body, "compatibility_root": root(body)}


def explain_selection(contract: Any, candidates: Any) -> dict[str, Any]:
    validated = validate_realization(contract)
    require(type(candidates) is list and bool(candidates), "RSC_SELECTION_EMPTY")
    rows = []
    for index, candidate in enumerate(candidates):
        configuration = candidate.get("configuration") if (
            type(candidate) is dict and set(candidate) == {"configuration", "metrics"}) else candidate
        checked = validate_configuration(validated, configuration)
        failed = [row for row in checked["constraint_checks"] if row["status"] == "FAIL"]
        rows.append({
            "candidate_index": index,
            "configuration_root": checked["configuration_root"],
            "status": checked["status"],
            "failed_constraints": [{"constraint_id": row["constraint_id"],
                                    "refusal_code": row["refusal_code"],
                                    "severity": row["severity"]} for row in failed],
        })
    try:
        selection = select_configuration(validated, candidates)
        selected_root = selection["selected_configuration_root"]
        selection_root = selection["root"]
        status = "PASS_EXPLAINED"
    except ValueError:
        selected_root = None
        selection_root = None
        status = "REFUSED_NO_SELECTION"
    lines = []
    for row in rows:
        if row["failed_constraints"]:
            codes = ", ".join(item["refusal_code"] for item in row["failed_constraints"])
            lines.append(f"candidate {row['candidate_index']}: eliminated by {codes}")
        elif row["configuration_root"] == selected_root:
            lines.append(f"candidate {row['candidate_index']}: selected")
        else:
            lines.append(f"candidate {row['candidate_index']}: admissible but not selected")
    body = {
        "schema": "mosaic.ucm.realization-selection-explanation.v0.1",
        "contract_root": validated["root"],
        "candidate_set_root": root(candidates),
        "selection_root": selection_root,
        "selected_configuration_root": selected_root,
        "ordered_evaluations": rows,
        "human_lines": lines,
        "status": status,
        **BOUNDARY,
    }
    return {**body, "explanation_root": root(body)}


def compare_configurations(contract: Any, left: Any, right: Any) -> dict[str, Any]:
    validated = validate_realization(contract)
    first = validate_configuration(validated, left)
    second = validate_configuration(validated, right)
    changed = []
    for axis in sorted(validated["axes"], key=lambda row: row["id"]):
        axis_id = axis["id"]
        if left[axis_id] != right[axis_id]:
            changed.append({"axis_id": axis_id, "left": left[axis_id],
                            "right": right[axis_id], "ownership": axis["ownership"],
                            "mutability": axis["mutability"]})
    body = {
        "schema": "mosaic.ucm.realization-configuration-diff.v0.1",
        "contract_root": validated["root"],
        "left_root": first["configuration_root"],
        "right_root": second["configuration_root"],
        "left_status": first["status"], "right_status": second["status"],
        "admissibility": ("BOTH" if first["status"] == second["status"] == "PASS_ADMISSIBLE"
                          else "LEFT_ONLY" if first["status"] == "PASS_ADMISSIBLE"
                          else "RIGHT_ONLY" if second["status"] == "PASS_ADMISSIBLE"
                          else "NEITHER"),
        "changed_axes": changed,
        "left_failed_constraints": [row for row in first["constraint_checks"]
                                    if row["status"] == "FAIL"],
        "right_failed_constraints": [row for row in second["constraint_checks"]
                                     if row["status"] == "FAIL"],
        **BOUNDARY,
    }
    return {**body, "diff_root": root(body)}


def domain_contract_diff(before: Any, after: Any) -> dict[str, Any]:
    """Compare AMCAS or realization contracts by semantic identity, not list index."""
    require(type(before) is dict and type(after) is dict,
            "UCM_CONTRACT_DIFF_INPUT_INVALID")
    schema = before.get("schema")
    require(schema == after.get("schema"), "UCM_CONTRACT_DIFF_SCHEMA_MISMATCH")
    if schema == "mosaic.realization-space-contract.v0.1":
        left, right = validate_realization(before), validate_realization(after)
        collections = {
            "AXES": (left["axes"], right["axes"], "id"),
            "CONSTRAINTS": (left["constraints"], right["constraints"], "id"),
            "OBJECTIVES": (left.get("objectives", []), right.get("objectives", []), "metric_id"),
            "LOWERING_TARGETS": (left["lowering"]["targets"], right["lowering"]["targets"], "target_id"),
        }
        authority_changed = left["authority"] != right["authority"]
        verifier_swaps: list[dict[str, Any]] = []
        kind = "REALIZATION"
    elif schema in {"mosaic.amcas.integration-contract.v0.1",
                    "mosaic.amcas.integration-contract.v0.2"}:
        left, right = validate_amcas(before), validate_amcas(after)
        collections = {
            "CM1_REQUIREMENTS": (left["cm1"]["requirements"], right["cm1"]["requirements"], "id"),
            "CM2_PREFERENCES": (left["cm2"]["preferences"], right["cm2"]["preferences"], "id"),
            "CAPABILITIES": (left["capabilities"], right["capabilities"], "id"),
            "EFFECTS": (left["effects"], right["effects"], "id"),
            "DEPENDENCIES": (left["dependencies"], right["dependencies"], "id"),
            "ACCEPTANCE": (left["acceptance"], right["acceptance"], "id"),
        }
        authority_changed = left["authority_ceiling"] != right["authority_ceiling"]
        before_requirements = {row["id"]: row for row in left["cm1"]["requirements"]}
        after_requirements = {row["id"]: row for row in right["cm1"]["requirements"]}
        verifier_swaps = [
            {"requirement_id": identifier,
             "before": before_requirements[identifier]["verifier"],
             "after": after_requirements[identifier]["verifier"]}
            for identifier in sorted(set(before_requirements) & set(after_requirements))
            if before_requirements[identifier]["verifier"] != after_requirements[identifier]["verifier"]
        ]
        kind = "AMCAS"
    else:
        require(False, "UCM_CONTRACT_DIFF_SCHEMA_UNSUPPORTED")
    changes = []
    for domain, (before_rows, after_rows, id_field) in collections.items():
        before_map = {row[id_field]: row for row in before_rows}
        after_map = {row[id_field]: row for row in after_rows}
        changes.append({
            "domain": domain,
            "added": sorted(set(after_map) - set(before_map)),
            "removed": sorted(set(before_map) - set(after_map)),
            "modified": sorted(identifier for identifier in set(before_map) & set(after_map)
                               if before_map[identifier] != after_map[identifier]),
        })
    authority_adjacent = authority_changed or bool(verifier_swaps) or any(
        row["domain"] == "EFFECTS" and (row["added"] or row["removed"] or row["modified"])
        for row in changes)
    body = {
        "schema": "mosaic.ucm.domain-contract-diff.v0.1",
        "contract_kind": kind, "before_root": root(before), "after_root": root(after),
        "domain_changes": changes, "verifier_swaps": verifier_swaps,
        "authority_ceiling_changed": authority_changed,
        "authority_adjacent_change": authority_adjacent,
        "status": "IDENTICAL" if root(before) == root(after) else "CHANGED",
        **BOUNDARY,
    }
    return {**body, "diff_root": root(body)}

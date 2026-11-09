"""Pure point-of-use admissibility records for the CCP-JM integration.

The module evaluates a complete frozen snapshot.  It performs no evidence
collection, clock read, network access, effect, or capability grant.  An
``ADMIT`` decision means only that the supplied snapshot is admissible under
this information-only profile; the Operational Gateway must independently
authorize any effect.

CHC and UCM's Five-Commitment Three-Hash Rule remain distinct contracts.  The
correspondence record below relates roles while explicitly denying digest and
wire equivalence.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY


__all__ = [
    "build_jurisdiction_profile", "validate_jurisdiction_profile",
    "build_enforcement_perimeter", "validate_enforcement_perimeter",
    "build_chc_thr_correspondence", "validate_chc_thr_correspondence",
    "build_evidence_snapshot", "validate_evidence_snapshot",
    "build_current_use_snapshot", "validate_current_use_snapshot",
    "evaluate_current_admissibility", "validate_admissibility_decision",
    "build_admissibility_projection", "validate_admissibility_projection",
]


JURISDICTION_SCHEMA = "mosaic.ucm.ccp-jurisdiction-profile.v0.1"
PERIMETER_SCHEMA = "mosaic.ucm.ccp-enforcement-perimeter.v0.1"
CORRESPONDENCE_SCHEMA = "mosaic.ucm.ccp-chc-thr-correspondence.v0.1"
EVIDENCE_SCHEMA = "mosaic.ucm.ccp-evidence-snapshot.v0.1.r014"
CURRENT_USE_SCHEMA = "mosaic.ucm.ccp-current-use-snapshot.v0.1"
DECISION_SCHEMA = "mosaic.ucm.ccp-current-use-decision.v0.1"
PROJECTION_SCHEMA = "mosaic.ucm.ccp-current-use-human-projection.v0.1"

DECISIONS = {"ADMIT", "REFUSE", "DEFER", "UNRESOLVED"}
SOURCE_MODES = {"LOCAL", "LAN", "INTERNET", "P2P"}
EVIDENCE_STATUSES = {"PASS", "FAIL", "UNAVAILABLE", "UNRESOLVED"}
STATE_STATUSES = {"CURRENT", "STALE"}
SEMANTIC_STATUSES = {"CURRENT", "STALE"}
REVOCATION_STATUSES = {"CURRENT_CLEAR", "REVOKED", "STALE", "UNAVAILABLE"}
CHECKPOINT_STATUSES = {"CURRENT", "STALE", "ROLLBACK", "UNRESOLVED"}
POLICY_STATUSES = {"CURRENT", "STALE"}
SCHEMA_STATUSES = {"CURRENT", "STALE", "UNRESOLVED"}
STATUS_DOMAINS = {
    "state": STATE_STATUSES,
    "semantic": SEMANTIC_STATUSES,
    "revocation": REVOCATION_STATUSES,
    "checkpoint": CHECKPOINT_STATUSES,
    "policy": POLICY_STATUSES,
    "schema": SCHEMA_STATUSES,
}
STATUS_OBSERVATIONS = {
    "state": {"CURRENT"},
    "semantic": {"CURRENT"},
    "revocation": {"CURRENT_CLEAR", "REVOKED"},
    "checkpoint": {"CURRENT", "ROLLBACK"},
    "policy": {"CURRENT"},
    "schema": {"CURRENT"},
}
EFFECT_CLASSES = {
    "NONE", "PURE_COMPUTATION", "READ", "READ_ONLY",
    "LOCAL_ARTIFACT_PREPARATION", "WRITE_WORKSPACE", "WRITE_EXTERNAL",
    "DELETE_WORKSPACE", "NETWORK", "INSTALL", "PROCESS", "DEVICE",
    "PERSISTENT_HOST_STATE", "AUTHORITY_CHANGE",
}

ROLE_MAPPINGS = [
    {
        "chc_role": "CHC_FRESHNESS_EVALUATION",
        "thr_role": "THR_H_c_ADMISSIBILITY",
        "relationship": "EVALUATION_ROLE_CORRESPONDENCE",
        "identity_rule": "DIGESTS_ARE_NOT_EQUIVALENT",
    },
    {
        "chc_role": "CHC_H_m_SEMANTIC_IDENTITY",
        "thr_role": "THR_H_m_MEANING",
        "relationship": "MEANING_ROLE_CORRESPONDENCE",
        "identity_rule": "DIGESTS_ARE_NOT_EQUIVALENT",
    },
    {
        "chc_role": "CHC_H_s_STATE_IDENTITY",
        "thr_role": "THR_H_s_STATE",
        "relationship": "STATE_ROLE_CORRESPONDENCE",
        "identity_rule": "DIGESTS_ARE_NOT_EQUIVALENT",
    },
]


def _identifier(value: Any, code: str) -> str:
    require(type(value) is str and value == value.strip() and 0 < len(value) <= 192
            and all(ch.isalnum() or ch in "._:-" for ch in value), code)
    return value


def _text(value: Any, code: str, maximum: int = 4096) -> str:
    require(type(value) is str and value == value.strip()
            and 0 < len(value) <= maximum, code)
    return value


def _strings(value: Any, code: str, *, allow_empty: bool = True) -> list[str]:
    require(type(value) is list and value == sorted(set(value)), code)
    require(allow_empty or bool(value), code)
    for item in value:
        _identifier(item, code)
    return deepcopy(value)


def _roots(value: Any, code: str) -> list[str]:
    require(type(value) is list and value == sorted(set(value)), code)
    for item in value:
        require_root(item)
    return deepcopy(value)


def _boundary(item: dict[str, Any], code: str) -> None:
    require({key: item[key] for key in BOUNDARY} == BOUNDARY, code)


def build_jurisdiction_profile(
        *, profile_id: str, application_id: str, subject_root: str,
        state_boundary_id: str, state_root: str, manifest_root: str,
        path_policy: str, governance_jurisdiction_root: str,
        bound_policy_root: str, bound_schema_registry_root: str,
        bound_trust_root: str, transition_rule_root: str,
        allowed_operations: list[str], evidence_modes: list[str]) -> dict[str, Any]:
    """Bind state and governance jurisdictions without creating authority."""
    _identifier(profile_id, "CCP_JURISDICTION_PROFILE_ID_INVALID")
    _identifier(application_id, "CCP_APPLICATION_ID_INVALID")
    _identifier(state_boundary_id, "CCP_STATE_BOUNDARY_ID_INVALID")
    require_root(subject_root); require_root(state_root); require_root(manifest_root)
    require(path_policy in {"PORTABLE_POSIX_RELATIVE_V1", "EXACT_ARCHIVE_MEMBERS_V1"},
            "CCP_STATE_PATH_POLICY_INVALID")
    for value in (governance_jurisdiction_root, bound_policy_root,
                  bound_schema_registry_root, bound_trust_root,
                  transition_rule_root):
        require_root(value)
    operations = _strings(allowed_operations, "CCP_ALLOWED_OPERATIONS_INVALID",
                          allow_empty=False)
    modes = _strings(evidence_modes, "CCP_EVIDENCE_MODES_INVALID",
                     allow_empty=False)
    require(set(modes) <= SOURCE_MODES, "CCP_EVIDENCE_MODE_UNSUPPORTED")
    body = {
        "schema": JURISDICTION_SCHEMA,
        "profile_id": profile_id,
        "application_id": application_id,
        "subject_root": subject_root,
        "state_jurisdiction": {
            "boundary_id": state_boundary_id,
            "state_root": state_root,
            "manifest_root": manifest_root,
            "path_policy": path_policy,
        },
        "governance_jurisdiction": {
            "jurisdiction_root": governance_jurisdiction_root,
            "bound_policy_root": bound_policy_root,
            "bound_schema_registry_root": bound_schema_registry_root,
            "bound_trust_root": bound_trust_root,
            "transition_rule_root": transition_rule_root,
        },
        "allowed_operations": operations,
        "evidence_modes": modes,
        "profile_status": "UCM_INFORMATION_ONLY_BOUND",
        **BOUNDARY,
    }
    return {**body, "jurisdiction_profile_root": root(body)}


def validate_jurisdiction_profile(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "profile_id", "application_id", "subject_root",
        "state_jurisdiction", "governance_jurisdiction", "allowed_operations",
        "evidence_modes", "profile_status", "standing", "authority_effect",
        "real_a5", "g0", "jurisdiction_profile_root",
    })
    require(item["schema"] == JURISDICTION_SCHEMA,
            "CCP_JURISDICTION_SCHEMA_INVALID")
    state = exact_keys(item["state_jurisdiction"], {
        "boundary_id", "state_root", "manifest_root", "path_policy",
    })
    governance = exact_keys(item["governance_jurisdiction"], {
        "jurisdiction_root", "bound_policy_root", "bound_schema_registry_root",
        "bound_trust_root", "transition_rule_root",
    })
    expected = build_jurisdiction_profile(
        profile_id=item["profile_id"], application_id=item["application_id"],
        subject_root=item["subject_root"], state_boundary_id=state["boundary_id"],
        state_root=state["state_root"], manifest_root=state["manifest_root"],
        path_policy=state["path_policy"],
        governance_jurisdiction_root=governance["jurisdiction_root"],
        bound_policy_root=governance["bound_policy_root"],
        bound_schema_registry_root=governance["bound_schema_registry_root"],
        bound_trust_root=governance["bound_trust_root"],
        transition_rule_root=governance["transition_rule_root"],
        allowed_operations=item["allowed_operations"],
        evidence_modes=item["evidence_modes"])
    require(item == expected, "CCP_JURISDICTION_PROFILE_INVALID")
    return deepcopy(item)


def build_enforcement_perimeter(
        *, perimeter_id: str, jurisdiction_profile_root: str,
        adapter_root: str, intercepted_operations: list[str],
        excluded_bypass_classes: list[str], continuing_use_policy: str,
        qualification_status: str) -> dict[str, Any]:
    """Describe the claimed interception scope; this is not proof of it."""
    _identifier(perimeter_id, "CCP_PERIMETER_ID_INVALID")
    require_root(jurisdiction_profile_root); require_root(adapter_root)
    operations = _strings(intercepted_operations,
                          "CCP_PERIMETER_OPERATIONS_INVALID", allow_empty=False)
    bypasses = _strings(excluded_bypass_classes,
                        "CCP_PERIMETER_BYPASS_CLASSES_INVALID")
    require(continuing_use_policy in {
        "LAUNCH_ONLY_RECHECK_REQUIRED", "LEASED_RECHECK", "CONTINUOUS_RECHECK",
    }, "CCP_CONTINUING_USE_POLICY_INVALID")
    require(qualification_status in {"DECLARED_ONLY", "QUALIFIED_SCOPED"},
            "CCP_PERIMETER_QUALIFICATION_INVALID")
    body = {
        "schema": PERIMETER_SCHEMA,
        "perimeter_id": perimeter_id,
        "jurisdiction_profile_root": jurisdiction_profile_root,
        "adapter_root": adapter_root,
        "intercepted_operations": operations,
        "excluded_bypass_classes": bypasses,
        "continuing_use_policy": continuing_use_policy,
        "qualification_status": qualification_status,
        "enforcement_claim": "SCOPED_DECLARATION_NOT_GLOBAL_ENFORCEMENT",
        **BOUNDARY,
    }
    return {**body, "enforcement_perimeter_root": root(body)}


def validate_enforcement_perimeter(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "perimeter_id", "jurisdiction_profile_root", "adapter_root",
        "intercepted_operations", "excluded_bypass_classes",
        "continuing_use_policy", "qualification_status", "enforcement_claim",
        "standing", "authority_effect", "real_a5", "g0",
        "enforcement_perimeter_root",
    })
    require(item["schema"] == PERIMETER_SCHEMA,
            "CCP_PERIMETER_SCHEMA_INVALID")
    expected = build_enforcement_perimeter(
        perimeter_id=item["perimeter_id"],
        jurisdiction_profile_root=item["jurisdiction_profile_root"],
        adapter_root=item["adapter_root"],
        intercepted_operations=item["intercepted_operations"],
        excluded_bypass_classes=item["excluded_bypass_classes"],
        continuing_use_policy=item["continuing_use_policy"],
        qualification_status=item["qualification_status"])
    require(item == expected, "CCP_ENFORCEMENT_PERIMETER_INVALID")
    return deepcopy(item)


def build_chc_thr_correspondence(
        *, correspondence_id: str, correspondence_version: str,
        chc_source_root: str, chc_profile_root: str,
        thr_contract_root: str,
        role_mappings: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Relate CHC and THR roles while explicitly denying digest equivalence."""
    _identifier(correspondence_id, "CCP_CORRESPONDENCE_ID_INVALID")
    _identifier(correspondence_version, "CCP_CORRESPONDENCE_VERSION_INVALID")
    require_root(chc_source_root); require_root(chc_profile_root)
    require_root(thr_contract_root)
    mappings = deepcopy(ROLE_MAPPINGS if role_mappings is None else role_mappings)
    require(type(mappings) is list and bool(mappings),
            "CCP_CORRESPONDENCE_MAPPINGS_INVALID")
    checked = []
    seen: set[str] = set()
    for raw in mappings:
        row = exact_keys(raw, {
            "chc_role", "thr_role", "relationship", "identity_rule",
        })
        chc_role = _identifier(row["chc_role"],
                               "CCP_CORRESPONDENCE_ROLE_INVALID")
        require(chc_role not in seen, "CCP_CORRESPONDENCE_ROLE_DUPLICATE")
        seen.add(chc_role)
        _identifier(row["thr_role"], "CCP_CORRESPONDENCE_ROLE_INVALID")
        _identifier(row["relationship"], "CCP_CORRESPONDENCE_RELATION_INVALID")
        require(row["identity_rule"] == "DIGESTS_ARE_NOT_EQUIVALENT",
                "CCP_CORRESPONDENCE_IDENTITY_RULE_INVALID")
        checked.append(deepcopy(row))
    checked.sort(key=lambda row: row["chc_role"])
    require(checked == ROLE_MAPPINGS,
            "CCP_CORRESPONDENCE_REQUIRED_ROLES_MISSING")
    body = {
        "schema": CORRESPONDENCE_SCHEMA,
        "correspondence_id": correspondence_id,
        "correspondence_version": correspondence_version,
        "chc_source_root": chc_source_root,
        "chc_profile_root": chc_profile_root,
        "thr_contract_root": thr_contract_root,
        "role_mappings": checked,
        "digest_equivalence": "DIGESTS_ARE_NOT_EQUIVALENT",
        "wire_compatibility": "NO_WIRE_COMPATIBILITY_ASSERTED",
        "normative_status": "UCM_INFORMATION_ONLY_PROFILE",
        "native_chc_interoperability": "UNBOUND",
        **BOUNDARY,
    }
    return {**body, "correspondence_root": root(body)}


def validate_chc_thr_correspondence(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "correspondence_id", "correspondence_version",
        "chc_source_root", "chc_profile_root", "thr_contract_root",
        "role_mappings", "digest_equivalence", "wire_compatibility",
        "normative_status", "native_chc_interoperability", "standing",
        "authority_effect", "real_a5", "g0", "correspondence_root",
    })
    require(item["schema"] == CORRESPONDENCE_SCHEMA,
            "CCP_CORRESPONDENCE_SCHEMA_INVALID")
    expected = build_chc_thr_correspondence(
        correspondence_id=item["correspondence_id"],
        correspondence_version=item["correspondence_version"],
        chc_source_root=item["chc_source_root"],
        chc_profile_root=item["chc_profile_root"],
        thr_contract_root=item["thr_contract_root"],
        role_mappings=item["role_mappings"])
    require(item == expected, "CCP_CHC_THR_CORRESPONDENCE_INVALID")
    return deepcopy(item)


def _evidence_rows(value: Any, *, subject_root: str,
                   authenticated_epoch: int) -> list[dict[str, Any]]:
    require(type(value) is list and bool(value), "CCP_EVIDENCE_ROWS_INVALID")
    rows = []
    seen: set[str] = set()
    for raw in value:
        row = exact_keys(raw, {
            "evidence_id", "evidence_kind", "subject_root", "evidence_root",
            "source_mode", "verification_status", "observed_epoch",
            "valid_until_epoch", "admissibility_status_claim",
        })
        evidence_id = _identifier(row["evidence_id"],
                                  "CCP_EVIDENCE_ID_INVALID")
        require(evidence_id not in seen, "CCP_EVIDENCE_ID_DUPLICATE")
        seen.add(evidence_id)
        _identifier(row["evidence_kind"], "CCP_EVIDENCE_KIND_INVALID")
        require(row["subject_root"] == subject_root,
                "CCP_EVIDENCE_SUBJECT_MISMATCH")
        require_root(row["evidence_root"])
        require(row["source_mode"] in SOURCE_MODES,
                "CCP_EVIDENCE_MODE_UNSUPPORTED")
        require(row["verification_status"] in EVIDENCE_STATUSES,
                "CCP_EVIDENCE_STATUS_INVALID")
        require(type(row["observed_epoch"]) is int
                and type(row["valid_until_epoch"]) is int
                and 0 <= row["observed_epoch"] <= authenticated_epoch
                and row["valid_until_epoch"] >= row["observed_epoch"],
                "CCP_EVIDENCE_EPOCH_INVALID")
        claim = row["admissibility_status_claim"]
        if claim is not None:
            claim = exact_keys(claim, {"domain", "observed_status"})
            require(claim["domain"] in STATUS_DOMAINS,
                    "CCP_STATUS_EVIDENCE_DOMAIN_INVALID")
            require(claim["observed_status"]
                    in STATUS_OBSERVATIONS[claim["domain"]],
                    "CCP_STATUS_EVIDENCE_OBSERVATION_INVALID")
            row["admissibility_status_claim"] = claim
        rows.append(deepcopy(row))
    rows.sort(key=lambda row: row["evidence_id"])
    return rows


def _derive_statuses(*, rows: list[dict[str, Any]],
                     status_evidence_ids: Any,
                     authenticated_epoch: int) -> tuple[dict[str, str], dict[str, str]]:
    links = exact_keys(status_evidence_ids, set(STATUS_DOMAINS))
    for evidence_id in links.values():
        _identifier(evidence_id, "CCP_STATUS_EVIDENCE_ID_INVALID")
    require(len(set(links.values())) == len(STATUS_DOMAINS),
            "CCP_STATUS_EVIDENCE_ID_REUSED")
    by_id = {row["evidence_id"]: row for row in rows}
    statuses: dict[str, str] = {}
    for domain in sorted(STATUS_DOMAINS):
        row = by_id.get(links[domain])
        require(row is not None, "CCP_STATUS_EVIDENCE_MISSING")
        claim = row["admissibility_status_claim"]
        require(type(claim) is dict and claim["domain"] == domain,
                "CCP_STATUS_EVIDENCE_CROSS_LINK_INVALID")
        verification = row["verification_status"]
        require(verification != "FAIL", "CCP_STATUS_EVIDENCE_FAILED")
        if verification == "UNAVAILABLE":
            require(domain == "revocation",
                    "CCP_STATUS_EVIDENCE_UNAVAILABLE_INVALID")
            status = "UNAVAILABLE"
        elif verification == "UNRESOLVED":
            require(domain in {"checkpoint", "schema"},
                    "CCP_STATUS_EVIDENCE_UNRESOLVED_INVALID")
            status = "UNRESOLVED"
        else:
            observed = claim["observed_status"]
            if observed in {"REVOKED", "ROLLBACK"}:
                status = observed
            elif row["valid_until_epoch"] < authenticated_epoch:
                status = "STALE"
            else:
                status = observed
        require(status in STATUS_DOMAINS[domain],
                "CCP_STATUS_EVIDENCE_DERIVATION_INVALID")
        statuses[domain] = status
    return statuses, deepcopy(links)


def build_evidence_snapshot(
        *, snapshot_id: str, subject_root: str, state_identity_root: str,
        semantic_identity_root: str, jurisdiction_profile_root: str,
        enforcement_perimeter_root: str, active_policy_root: str,
        active_schema_registry_root: str, active_trust_root: str,
        checkpoint_root: str, checkpoint_sequence: int,
        persistent_maximum_sequence: int, authenticated_epoch: int,
        evidence: list[dict[str, Any]],
        status_evidence_ids: dict[str, str],
        unresolved_requirements: list[str]) -> dict[str, Any]:
    """Freeze all evaluator inputs; acquisition remains outside this module."""
    _identifier(snapshot_id, "CCP_EVIDENCE_SNAPSHOT_ID_INVALID")
    for value in (subject_root, state_identity_root, semantic_identity_root,
                  jurisdiction_profile_root, enforcement_perimeter_root,
                  active_policy_root, active_schema_registry_root,
                  active_trust_root, checkpoint_root):
        require_root(value)
    require(type(checkpoint_sequence) is int and checkpoint_sequence >= 0
            and type(persistent_maximum_sequence) is int
            and persistent_maximum_sequence >= 0
            and type(authenticated_epoch) is int and authenticated_epoch >= 0,
            "CCP_EVIDENCE_COUNTER_INVALID")
    require(checkpoint_sequence <= persistent_maximum_sequence,
            "CCP_CHECKPOINT_EXCEEDS_PERSISTENT_MAXIMUM")
    rows = _evidence_rows(evidence, subject_root=subject_root,
                          authenticated_epoch=authenticated_epoch)
    statuses, status_links = _derive_statuses(
        rows=rows, status_evidence_ids=status_evidence_ids,
        authenticated_epoch=authenticated_epoch)
    require((checkpoint_sequence < persistent_maximum_sequence)
            == (statuses["checkpoint"] == "ROLLBACK"),
            "CCP_CHECKPOINT_ROLLBACK_CLASSIFICATION_INVALID")
    unresolved = _strings(unresolved_requirements,
                          "CCP_UNRESOLVED_REQUIREMENTS_INVALID")
    body = {
        "schema": EVIDENCE_SCHEMA,
        "snapshot_id": snapshot_id,
        "subject_root": subject_root,
        "state_identity_root": state_identity_root,
        "semantic_identity_root": semantic_identity_root,
        "jurisdiction_profile_root": jurisdiction_profile_root,
        "enforcement_perimeter_root": enforcement_perimeter_root,
        "active_policy_root": active_policy_root,
        "active_schema_registry_root": active_schema_registry_root,
        "active_trust_root": active_trust_root,
        "checkpoint_root": checkpoint_root,
        "checkpoint_sequence": checkpoint_sequence,
        "persistent_maximum_sequence": persistent_maximum_sequence,
        "authenticated_epoch": authenticated_epoch,
        "statuses": statuses,
        "status_evidence_ids": status_links,
        "evidence": rows,
        "unresolved_requirements": unresolved,
        "acquisition_claim": "FROZEN_INPUTS_ONLY_NO_AMBIENT_READS",
        **BOUNDARY,
    }
    return {**body, "evidence_snapshot_root": root(body)}


def validate_evidence_snapshot(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "snapshot_id", "subject_root", "state_identity_root",
        "semantic_identity_root", "jurisdiction_profile_root",
        "enforcement_perimeter_root", "active_policy_root",
        "active_schema_registry_root", "active_trust_root", "checkpoint_root",
        "checkpoint_sequence", "persistent_maximum_sequence",
        "authenticated_epoch", "statuses", "status_evidence_ids", "evidence",
        "unresolved_requirements", "acquisition_claim", "standing",
        "authority_effect", "real_a5", "g0", "evidence_snapshot_root",
    })
    require(item["schema"] == EVIDENCE_SCHEMA,
            "CCP_EVIDENCE_SNAPSHOT_SCHEMA_INVALID")
    exact_keys(item["statuses"], {
        "state", "semantic", "revocation", "checkpoint", "policy", "schema",
    })
    expected = build_evidence_snapshot(
        snapshot_id=item["snapshot_id"], subject_root=item["subject_root"],
        state_identity_root=item["state_identity_root"],
        semantic_identity_root=item["semantic_identity_root"],
        jurisdiction_profile_root=item["jurisdiction_profile_root"],
        enforcement_perimeter_root=item["enforcement_perimeter_root"],
        active_policy_root=item["active_policy_root"],
        active_schema_registry_root=item["active_schema_registry_root"],
        active_trust_root=item["active_trust_root"],
        checkpoint_root=item["checkpoint_root"],
        checkpoint_sequence=item["checkpoint_sequence"],
        persistent_maximum_sequence=item["persistent_maximum_sequence"],
        authenticated_epoch=item["authenticated_epoch"],
        evidence=item["evidence"],
        status_evidence_ids=item["status_evidence_ids"],
        unresolved_requirements=item["unresolved_requirements"])
    require(item == expected, "CCP_EVIDENCE_SNAPSHOT_INVALID")
    return deepcopy(item)


def build_current_use_snapshot(
        *, request_id: str, operation: str, subject_root: str,
        target_root: str, handler_root: str, runtime_root: str,
        dependency_closure_root: str, state_identity_root: str,
        semantic_identity_root: str, jurisdiction_profile_root: str,
        enforcement_perimeter_root: str, correspondence_root: str,
        evidence_snapshot_root: str, active_policy_root: str,
        active_schema_registry_root: str, active_trust_root: str,
        checkpoint_root: str, authenticated_epoch: int,
        requested_effect_classes: list[str], max_steps: int,
        max_evidence_rows: int) -> dict[str, Any]:
    """Bind the exact object, operation, runtime closure, and frozen evidence."""
    _identifier(request_id, "CCP_CURRENT_USE_REQUEST_ID_INVALID")
    _identifier(operation, "CCP_CURRENT_USE_OPERATION_INVALID")
    for value in (subject_root, target_root, handler_root, runtime_root,
                  dependency_closure_root, state_identity_root,
                  semantic_identity_root, jurisdiction_profile_root,
                  enforcement_perimeter_root, correspondence_root,
                  evidence_snapshot_root, active_policy_root,
                  active_schema_registry_root, active_trust_root,
                  checkpoint_root):
        require_root(value)
    require(type(authenticated_epoch) is int and authenticated_epoch >= 0,
            "CCP_CURRENT_USE_EPOCH_INVALID")
    effects = _strings(requested_effect_classes,
                       "CCP_CURRENT_USE_EFFECTS_INVALID", allow_empty=False)
    require(set(effects) <= EFFECT_CLASSES, "CCP_CURRENT_USE_EFFECT_UNSUPPORTED")
    require(type(max_steps) is int and max_steps > 0
            and type(max_evidence_rows) is int and max_evidence_rows > 0,
            "CCP_CURRENT_USE_BUDGET_INVALID")
    body = {
        "schema": CURRENT_USE_SCHEMA,
        "request_id": request_id,
        "operation": operation,
        "subject_root": subject_root,
        "target_root": target_root,
        "handler_root": handler_root,
        "runtime_root": runtime_root,
        "dependency_closure_root": dependency_closure_root,
        "state_identity_root": state_identity_root,
        "semantic_identity_root": semantic_identity_root,
        "jurisdiction_profile_root": jurisdiction_profile_root,
        "enforcement_perimeter_root": enforcement_perimeter_root,
        "correspondence_root": correspondence_root,
        "evidence_snapshot_root": evidence_snapshot_root,
        "active_policy_root": active_policy_root,
        "active_schema_registry_root": active_schema_registry_root,
        "active_trust_root": active_trust_root,
        "checkpoint_root": checkpoint_root,
        "authenticated_epoch": authenticated_epoch,
        "requested_effect_classes": effects,
        "evaluation_budget": {
            "max_steps": max_steps,
            "max_evidence_rows": max_evidence_rows,
        },
        **BOUNDARY,
    }
    return {**body, "current_use_snapshot_root": root(body)}


def validate_current_use_snapshot(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "request_id", "operation", "subject_root", "target_root",
        "handler_root", "runtime_root", "dependency_closure_root",
        "state_identity_root", "semantic_identity_root",
        "jurisdiction_profile_root", "enforcement_perimeter_root",
        "correspondence_root", "evidence_snapshot_root", "active_policy_root",
        "active_schema_registry_root", "active_trust_root", "checkpoint_root",
        "authenticated_epoch", "requested_effect_classes", "evaluation_budget",
        "standing", "authority_effect", "real_a5", "g0",
        "current_use_snapshot_root",
    })
    require(item["schema"] == CURRENT_USE_SCHEMA,
            "CCP_CURRENT_USE_SCHEMA_INVALID")
    budget = exact_keys(item["evaluation_budget"], {
        "max_steps", "max_evidence_rows",
    })
    expected = build_current_use_snapshot(
        request_id=item["request_id"], operation=item["operation"],
        subject_root=item["subject_root"], target_root=item["target_root"],
        handler_root=item["handler_root"], runtime_root=item["runtime_root"],
        dependency_closure_root=item["dependency_closure_root"],
        state_identity_root=item["state_identity_root"],
        semantic_identity_root=item["semantic_identity_root"],
        jurisdiction_profile_root=item["jurisdiction_profile_root"],
        enforcement_perimeter_root=item["enforcement_perimeter_root"],
        correspondence_root=item["correspondence_root"],
        evidence_snapshot_root=item["evidence_snapshot_root"],
        active_policy_root=item["active_policy_root"],
        active_schema_registry_root=item["active_schema_registry_root"],
        active_trust_root=item["active_trust_root"],
        checkpoint_root=item["checkpoint_root"],
        authenticated_epoch=item["authenticated_epoch"],
        requested_effect_classes=item["requested_effect_classes"],
        max_steps=budget["max_steps"],
        max_evidence_rows=budget["max_evidence_rows"])
    require(item == expected, "CCP_CURRENT_USE_SNAPSHOT_INVALID")
    return deepcopy(item)


def _expected_anchors(
        *, expected_subject_root: str,
        expected_jurisdiction_profile_root: str,
        expected_enforcement_perimeter_root: str,
        expected_correspondence_root: str, expected_policy_root: str,
        expected_schema_registry_root: str, expected_trust_root: str,
        expected_checkpoint_root: str) -> dict[str, str]:
    result = {
        "subject_root": expected_subject_root,
        "jurisdiction_profile_root": expected_jurisdiction_profile_root,
        "enforcement_perimeter_root": expected_enforcement_perimeter_root,
        "correspondence_root": expected_correspondence_root,
        "policy_root": expected_policy_root,
        "schema_registry_root": expected_schema_registry_root,
        "trust_root": expected_trust_root,
        "checkpoint_root": expected_checkpoint_root,
    }
    for value in result.values():
        require_root(value)
    return result


def evaluate_current_admissibility(
        *, current_use_snapshot: dict[str, Any],
        evidence_snapshot: dict[str, Any],
        jurisdiction_profile: dict[str, Any],
        enforcement_perimeter: dict[str, Any],
        correspondence: dict[str, Any], expected_subject_root: str,
        expected_jurisdiction_profile_root: str,
        expected_enforcement_perimeter_root: str,
        expected_correspondence_root: str, expected_policy_root: str,
        expected_schema_registry_root: str, expected_trust_root: str,
        expected_checkpoint_root: str) -> dict[str, Any]:
    """Evaluate a frozen snapshot against independently supplied anchors."""
    use = validate_current_use_snapshot(current_use_snapshot)
    evidence = validate_evidence_snapshot(evidence_snapshot)
    profile = validate_jurisdiction_profile(jurisdiction_profile)
    perimeter = validate_enforcement_perimeter(enforcement_perimeter)
    mapping = validate_chc_thr_correspondence(correspondence)
    anchors = _expected_anchors(
        expected_subject_root=expected_subject_root,
        expected_jurisdiction_profile_root=expected_jurisdiction_profile_root,
        expected_enforcement_perimeter_root=expected_enforcement_perimeter_root,
        expected_correspondence_root=expected_correspondence_root,
        expected_policy_root=expected_policy_root,
        expected_schema_registry_root=expected_schema_registry_root,
        expected_trust_root=expected_trust_root,
        expected_checkpoint_root=expected_checkpoint_root)

    refused: list[str] = []
    deferred: list[str] = []
    unresolved: list[str] = list(evidence["unresolved_requirements"])

    root_checks = {
        "SUBJECT_ANCHOR_MISMATCH": (use["subject_root"], anchors["subject_root"]),
        "JURISDICTION_ANCHOR_MISMATCH": (
            use["jurisdiction_profile_root"], anchors["jurisdiction_profile_root"]),
        "PERIMETER_ANCHOR_MISMATCH": (
            use["enforcement_perimeter_root"],
            anchors["enforcement_perimeter_root"]),
        "CORRESPONDENCE_ANCHOR_MISMATCH": (
            use["correspondence_root"], anchors["correspondence_root"]),
        "POLICY_ANCHOR_MISMATCH": (
            use["active_policy_root"], anchors["policy_root"]),
        "SCHEMA_ANCHOR_MISMATCH": (
            use["active_schema_registry_root"], anchors["schema_registry_root"]),
        "TRUST_ANCHOR_MISMATCH": (
            use["active_trust_root"], anchors["trust_root"]),
        "CHECKPOINT_ANCHOR_MISMATCH": (
            use["checkpoint_root"], anchors["checkpoint_root"]),
        "PROFILE_SUBJECT_MISMATCH": (profile["subject_root"], use["subject_root"]),
        "PROFILE_ROOT_MISMATCH": (
            profile["jurisdiction_profile_root"], use["jurisdiction_profile_root"]),
        "PERIMETER_ROOT_MISMATCH": (
            perimeter["enforcement_perimeter_root"],
            use["enforcement_perimeter_root"]),
        "PERIMETER_PROFILE_MISMATCH": (
            perimeter["jurisdiction_profile_root"],
            profile["jurisdiction_profile_root"]),
        "CORRESPONDENCE_ROOT_MISMATCH": (
            mapping["correspondence_root"], use["correspondence_root"]),
        "EVIDENCE_ROOT_MISMATCH": (
            evidence["evidence_snapshot_root"], use["evidence_snapshot_root"]),
        "EVIDENCE_SUBJECT_MISMATCH": (
            evidence["subject_root"], use["subject_root"]),
        "EVIDENCE_JURISDICTION_MISMATCH": (
            evidence["jurisdiction_profile_root"],
            use["jurisdiction_profile_root"]),
        "EVIDENCE_PERIMETER_MISMATCH": (
            evidence["enforcement_perimeter_root"],
            use["enforcement_perimeter_root"]),
        "STATE_IDENTITY_MISMATCH": (
            evidence["state_identity_root"], use["state_identity_root"]),
        "SEMANTIC_IDENTITY_MISMATCH": (
            evidence["semantic_identity_root"], use["semantic_identity_root"]),
        "EVIDENCE_POLICY_MISMATCH": (
            evidence["active_policy_root"], use["active_policy_root"]),
        "EVIDENCE_SCHEMA_MISMATCH": (
            evidence["active_schema_registry_root"],
            use["active_schema_registry_root"]),
        "EVIDENCE_TRUST_MISMATCH": (
            evidence["active_trust_root"], use["active_trust_root"]),
        "EVIDENCE_CHECKPOINT_MISMATCH": (
            evidence["checkpoint_root"], use["checkpoint_root"]),
        "EVIDENCE_EPOCH_MISMATCH": (
            evidence["authenticated_epoch"], use["authenticated_epoch"]),
        "PROFILE_POLICY_MISMATCH": (
            profile["governance_jurisdiction"]["bound_policy_root"],
            use["active_policy_root"]),
        "PROFILE_SCHEMA_MISMATCH": (
            profile["governance_jurisdiction"]["bound_schema_registry_root"],
            use["active_schema_registry_root"]),
        "PROFILE_TRUST_MISMATCH": (
            profile["governance_jurisdiction"]["bound_trust_root"],
            use["active_trust_root"]),
    }
    refused.extend(code for code, values in root_checks.items()
                   if values[0] != values[1])
    if use["operation"] not in profile["allowed_operations"]:
        refused.append("OPERATION_OUTSIDE_JURISDICTION_PROFILE")
    if use["operation"] not in perimeter["intercepted_operations"]:
        refused.append("OPERATION_OUTSIDE_ENFORCEMENT_PERIMETER")
    if perimeter["qualification_status"] != "QUALIFIED_SCOPED":
        unresolved.append("ENFORCEMENT_PERIMETER_NOT_QUALIFIED")
    if len(evidence["evidence"]) > use["evaluation_budget"]["max_evidence_rows"]:
        refused.append("EVALUATION_BUDGET_EXCEEDED")

    statuses = evidence["statuses"]
    if statuses["state"] == "STALE":
        refused.append("STALE_STATE")
    if statuses["semantic"] == "STALE":
        refused.append("STALE_SEMANTIC_ATTESTATION")
    if statuses["revocation"] == "REVOKED":
        refused.append("AUTHENTICATED_REVOCATION")
    elif statuses["revocation"] in {"STALE", "UNAVAILABLE"}:
        deferred.append("STALE_REVOCATION_STATE")
    if statuses["checkpoint"] == "ROLLBACK":
        refused.append("CHECKPOINT_ROLLBACK")
    elif statuses["checkpoint"] == "STALE":
        deferred.append("STALE_CHECKPOINT")
    elif statuses["checkpoint"] == "UNRESOLVED":
        unresolved.append("CHECKPOINT_CONTINUITY_UNRESOLVED")
    if statuses["policy"] == "STALE":
        refused.append("POLICY_STALE")
    if statuses["schema"] == "STALE":
        deferred.append("SCHEMA_STATE_STALE")
    elif statuses["schema"] == "UNRESOLVED":
        unresolved.append("SCHEMA_STATE_UNRESOLVED")

    for row in evidence["evidence"]:
        if row["source_mode"] not in profile["evidence_modes"]:
            refused.append(
                f"EVIDENCE_MODE_OUTSIDE_JURISDICTION:{row['evidence_id']}")
        if row["verification_status"] == "FAIL":
            refused.append(f"EVIDENCE_FAILED:{row['evidence_id']}")
        elif row["verification_status"] == "UNAVAILABLE":
            deferred.append(f"EVIDENCE_UNAVAILABLE:{row['evidence_id']}")
        elif row["verification_status"] == "UNRESOLVED":
            unresolved.append(f"EVIDENCE_UNRESOLVED:{row['evidence_id']}")
        if row["valid_until_epoch"] < use["authenticated_epoch"]:
            deferred.append(f"EVIDENCE_EXPIRED:{row['evidence_id']}")

    # A step is one declared root/cross-link check, one fixed status or scope
    # rule, or one of four checks applied to an evidence row.  This is a
    # logical evaluation budget, not an estimate of Python instructions.
    evaluation_steps = len(root_checks) + 10 + 4 * len(evidence["evidence"])
    step_budget = use["evaluation_budget"]["max_steps"]
    if evaluation_steps > step_budget:
        refused.append("EVALUATION_STEP_BUDGET_EXCEEDED")

    refused = sorted(set(refused))
    deferred = sorted(set(deferred))
    unresolved = sorted(set(unresolved))
    if refused:
        decision, reasons = "REFUSE", refused
    elif unresolved:
        decision, reasons = "UNRESOLVED", unresolved
    elif deferred:
        decision, reasons = "DEFER", deferred
    else:
        decision, reasons = "ADMIT", ["CURRENT_USE_CONTEXT_ADMISSIBLE"]
    require(decision in DECISIONS, "CCP_ADMISSIBILITY_DECISION_INVALID")
    body = {
        "schema": DECISION_SCHEMA,
        "current_use_snapshot_root": use["current_use_snapshot_root"],
        "evidence_snapshot_root": evidence["evidence_snapshot_root"],
        "jurisdiction_profile_root": profile["jurisdiction_profile_root"],
        "enforcement_perimeter_root": perimeter["enforcement_perimeter_root"],
        "correspondence_root": mapping["correspondence_root"],
        "expected_anchors": anchors,
        "decision": decision,
        "reason_codes": reasons,
        "unresolved_prerequisites": unresolved,
        "evaluation_steps": evaluation_steps,
        "evaluation_step_budget": step_budget,
        "historical_identities_unchanged": (
            use["state_identity_root"] == evidence["state_identity_root"]
            and use["semantic_identity_root"] == evidence["semantic_identity_root"]),
        "decision_scope": "UCM_INFORMATION_ONLY_POINT_OF_USE",
        "gateway_disposition": (
            "SEPARATE_GATEWAY_AUTHORIZATION_REQUIRED"
            if decision == "ADMIT" else "NOT_ELIGIBLE_FOR_EFFECT"),
        "effect_authorized": False,
        **BOUNDARY,
    }
    return {**body, "decision_root": root(body)}


def _validate_decision_shape(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "current_use_snapshot_root", "evidence_snapshot_root",
        "jurisdiction_profile_root", "enforcement_perimeter_root",
        "correspondence_root", "expected_anchors", "decision", "reason_codes",
        "unresolved_prerequisites", "evaluation_steps",
        "evaluation_step_budget", "historical_identities_unchanged",
        "decision_scope", "gateway_disposition", "effect_authorized", "standing",
        "authority_effect", "real_a5", "g0", "decision_root",
    })
    require(item["schema"] == DECISION_SCHEMA
            and item["decision"] in DECISIONS,
            "CCP_ADMISSIBILITY_DECISION_SCHEMA_INVALID")
    for field in (
            "current_use_snapshot_root", "evidence_snapshot_root",
            "jurisdiction_profile_root", "enforcement_perimeter_root",
            "correspondence_root", "decision_root"):
        require_root(item[field])
    anchors = exact_keys(item["expected_anchors"], {
        "subject_root", "jurisdiction_profile_root",
        "enforcement_perimeter_root", "correspondence_root", "policy_root",
        "schema_registry_root", "trust_root", "checkpoint_root",
    })
    for value_root in anchors.values():
        require_root(value_root)
    _strings(item["reason_codes"], "CCP_ADMISSIBILITY_REASONS_INVALID",
             allow_empty=False)
    _strings(item["unresolved_prerequisites"],
             "CCP_ADMISSIBILITY_UNRESOLVED_INVALID")
    require(type(item["evaluation_steps"]) is int
            and item["evaluation_steps"] > 0
            and type(item["evaluation_step_budget"]) is int
            and item["evaluation_step_budget"] > 0,
            "CCP_ADMISSIBILITY_EVALUATION_BUDGET_INVALID")
    require(type(item["historical_identities_unchanged"]) is bool
            and item["decision_scope"] == "UCM_INFORMATION_ONLY_POINT_OF_USE"
            and item["effect_authorized"] is False,
            "CCP_ADMISSIBILITY_CEILING_INVALID")
    require(item["gateway_disposition"] == (
        "SEPARATE_GATEWAY_AUTHORIZATION_REQUIRED"
        if item["decision"] == "ADMIT" else "NOT_ELIGIBLE_FOR_EFFECT"),
        "CCP_ADMISSIBILITY_GATEWAY_DISPOSITION_INVALID")
    _boundary(item, "CCP_ADMISSIBILITY_AUTHORITY_CEILING_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items()
            if key != "decision_root"}
    require(item["decision_root"] == root(body),
            "CCP_ADMISSIBILITY_DECISION_ROOT_INVALID")
    return deepcopy(item)


def validate_admissibility_decision(
        value: Any, *, current_use_snapshot: dict[str, Any],
        evidence_snapshot: dict[str, Any],
        jurisdiction_profile: dict[str, Any],
        enforcement_perimeter: dict[str, Any],
        correspondence: dict[str, Any], expected_subject_root: str,
        expected_jurisdiction_profile_root: str,
        expected_enforcement_perimeter_root: str,
        expected_correspondence_root: str, expected_policy_root: str,
        expected_schema_registry_root: str, expected_trust_root: str,
        expected_checkpoint_root: str) -> dict[str, Any]:
    item = _validate_decision_shape(value)
    expected = evaluate_current_admissibility(
        current_use_snapshot=current_use_snapshot,
        evidence_snapshot=evidence_snapshot,
        jurisdiction_profile=jurisdiction_profile,
        enforcement_perimeter=enforcement_perimeter,
        correspondence=correspondence,
        expected_subject_root=expected_subject_root,
        expected_jurisdiction_profile_root=expected_jurisdiction_profile_root,
        expected_enforcement_perimeter_root=expected_enforcement_perimeter_root,
        expected_correspondence_root=expected_correspondence_root,
        expected_policy_root=expected_policy_root,
        expected_schema_registry_root=expected_schema_registry_root,
        expected_trust_root=expected_trust_root,
        expected_checkpoint_root=expected_checkpoint_root)
    require(item == expected, "CCP_ADMISSIBILITY_DECISION_INVALID")
    return deepcopy(item)


def build_admissibility_projection(
        *, decision: dict[str, Any], current_use_snapshot: dict[str, Any],
        evidence_snapshot: dict[str, Any],
        jurisdiction_profile: dict[str, Any],
        enforcement_perimeter: dict[str, Any], correspondence: dict[str, Any],
        expected_subject_root: str, expected_jurisdiction_profile_root: str,
        expected_enforcement_perimeter_root: str,
        expected_correspondence_root: str, expected_policy_root: str,
        expected_schema_registry_root: str, expected_trust_root: str,
        expected_checkpoint_root: str) -> dict[str, Any]:
    """Render the rooted decision for a human without becoming authority."""
    checked = validate_admissibility_decision(
        decision, current_use_snapshot=current_use_snapshot,
        evidence_snapshot=evidence_snapshot,
        jurisdiction_profile=jurisdiction_profile,
        enforcement_perimeter=enforcement_perimeter,
        correspondence=correspondence,
        expected_subject_root=expected_subject_root,
        expected_jurisdiction_profile_root=expected_jurisdiction_profile_root,
        expected_enforcement_perimeter_root=expected_enforcement_perimeter_root,
        expected_correspondence_root=expected_correspondence_root,
        expected_policy_root=expected_policy_root,
        expected_schema_registry_root=expected_schema_registry_root,
        expected_trust_root=expected_trust_root,
        expected_checkpoint_root=expected_checkpoint_root)
    use = validate_current_use_snapshot(current_use_snapshot)
    evidence = validate_evidence_snapshot(evidence_snapshot)
    profile = validate_jurisdiction_profile(jurisdiction_profile)
    require(checked["current_use_snapshot_root"] == use["current_use_snapshot_root"]
            and checked["evidence_snapshot_root"] == evidence["evidence_snapshot_root"]
            and checked["jurisdiction_profile_root"]
            == profile["jurisdiction_profile_root"],
            "CCP_PROJECTION_DECISION_BINDING_INVALID")
    answer = {
        "ADMIT": "YES_SUBJECT_TO_SEPARATE_GATEWAY_AUTHORIZATION",
        "REFUSE": "NO_REFUSED",
        "DEFER": "NOT_YET_CURRENT_EVIDENCE_REQUIRED",
        "UNRESOLVED": "NOT_DETERMINED_UNRESOLVED_RULES",
    }[checked["decision"]]
    next_action = {
        "ADMIT": "SUBMIT_EXACT_DECISION_ROOT_TO_OPERATIONAL_GATEWAY_G1",
        "REFUSE": "DO_NOT_DISPATCH_REPAIR_REFUSAL_REASONS",
        "DEFER": "ACQUIRE_AUTHORIZED_EVIDENCE_AND_BUILD_NEW_SNAPSHOT",
        "UNRESOLVED": "RESOLVE_NAMED_PREREQUISITES_BEFORE_REEVALUATION",
    }[checked["decision"]]
    newest = max(row["observed_epoch"] for row in evidence["evidence"])
    body = {
        "schema": PROJECTION_SCHEMA,
        "question": "Can I use this now?",
        "answer": answer,
        "decision": checked["decision"],
        "decision_root": checked["decision_root"],
        "checked_subject": {
            "subject_root": use["subject_root"],
            "state_identity_root": use["state_identity_root"],
            "semantic_identity_root": use["semantic_identity_root"],
        },
        "checked_jurisdiction": {
            "profile_id": profile["profile_id"],
            "jurisdiction_profile_root": profile["jurisdiction_profile_root"],
        },
        "evidence_age_epochs": use["authenticated_epoch"] - newest,
        "reason_codes": deepcopy(checked["reason_codes"]),
        "unresolved_prerequisites": deepcopy(
            checked["unresolved_prerequisites"]),
        "next_action": next_action,
        "projection_is_evidence": False,
        "projection_is_authority": False,
        **BOUNDARY,
    }
    return {**body, "projection_root": root(body)}


def validate_admissibility_projection(
        value: Any, *, decision: dict[str, Any],
        current_use_snapshot: dict[str, Any],
        evidence_snapshot: dict[str, Any],
        jurisdiction_profile: dict[str, Any],
        enforcement_perimeter: dict[str, Any], correspondence: dict[str, Any],
        expected_subject_root: str, expected_jurisdiction_profile_root: str,
        expected_enforcement_perimeter_root: str,
        expected_correspondence_root: str, expected_policy_root: str,
        expected_schema_registry_root: str, expected_trust_root: str,
        expected_checkpoint_root: str) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "question", "answer", "decision", "decision_root",
        "checked_subject", "checked_jurisdiction", "evidence_age_epochs",
        "reason_codes", "unresolved_prerequisites", "next_action",
        "projection_is_evidence", "projection_is_authority", "standing",
        "authority_effect", "real_a5", "g0", "projection_root",
    })
    require(item["schema"] == PROJECTION_SCHEMA,
            "CCP_PROJECTION_SCHEMA_INVALID")
    expected = build_admissibility_projection(
        decision=decision, current_use_snapshot=current_use_snapshot,
        evidence_snapshot=evidence_snapshot,
        jurisdiction_profile=jurisdiction_profile,
        enforcement_perimeter=enforcement_perimeter,
        correspondence=correspondence,
        expected_subject_root=expected_subject_root,
        expected_jurisdiction_profile_root=expected_jurisdiction_profile_root,
        expected_enforcement_perimeter_root=expected_enforcement_perimeter_root,
        expected_correspondence_root=expected_correspondence_root,
        expected_policy_root=expected_policy_root,
        expected_schema_registry_root=expected_schema_registry_root,
        expected_trust_root=expected_trust_root,
        expected_checkpoint_root=expected_checkpoint_root)
    require(item == expected, "CCP_CURRENT_USE_PROJECTION_INVALID")
    return deepcopy(item)

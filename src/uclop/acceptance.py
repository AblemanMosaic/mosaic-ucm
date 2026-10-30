from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import exact_keys, require, require_root, root


STAGES = (
    "S0_NATIVE_REPLAY",
    "S1_PROTECTED_SHADOW",
    "S2_INFORMATION_ONLY_FEDERATION",
    "S3_REAL_A5_QUALIFICATION",
    "S4_G0_OPENING",
    "S5_LIMITED_STANDING",
    "S6_PRODUCTION_ACTIVATION",
)

STAGE_DEFINITIONS = {
    "S0_NATIVE_REPLAY": {
        "entry": ["ARTIFACT_PINS", "CLOSED_FILE_SET", "HOST_PROFILE", "REVIEW_RECORD", "TEMPORARY_CUSTODY", "NO_EFFECT_CREDENTIALS"],
        "acceptance": ["SOURCE_ROOT", "TRANSPORT_ROOT", "DEPENDENCY_ROOT", "HOST_PROFILE_ROOT", "COURT_ROOT", "TERMINAL_ROOT", "CLEANUP_ROOT"],
        "rollback": ["STOP_PROCESS", "PRESERVE_TERMINAL_EVIDENCE", "CAPTURE_TEMP_MANIFEST", "REMOVE_DECLARED_TEMP_CUSTODY", "VERIFY_FROZEN_INPUTS"],
        "ceiling": "TEMPORARY_EXACT_BYTE_EXECUTION",
    },
    "S1_PROTECTED_SHADOW": {
        "entry": ["S0_ACCEPTANCE", "INSTALL_MANIFEST", "PREIMAGE", "IDENTITY_AND_ACL_PLAN", "NETWORK_PLAN", "KEYSTORE_ADAPTER", "MONOTONIC_STATE_ADAPTER", "ROLLBACK_PACKAGE", "HOST_AUTHORIZATION"],
        "acceptance": ["PREIMAGE_ROOT", "POSTIMAGE_ROOT", "EXECUTION_IDENTITIES", "ACL_ROOT", "SERVICE_ROOT", "NETWORK_ROOT", "RUNTIME_ROOT", "ROLLBACK_REHEARSAL_ROOT"],
        "rollback": ["DISABLE_ENTRYPOINTS", "PRESERVE_STATE_AND_LOGS", "RESTORE_PREIMAGE", "REVOKE_SHADOW_SESSIONS", "QUARANTINE_KEYS", "VERIFY_PRIOR_RUNTIME"],
        "ceiling": "ONE_HOST_PROTECTED_SHADOW",
    },
    "S2_INFORMATION_ONLY_FEDERATION": {
        "entry": ["S1_ACCEPTANCE_EACH_HOST", "DISTINCT_TRIAL_IDENTITIES", "SEPARATE_PRIVATE_CUSTODY", "PINNED_PEER_REGISTRIES", "DURABLE_MONOTONIC_STATE", "AUTHORIZED_ENDPOINTS", "MESSAGE_CEILINGS"],
        "acceptance": ["NODE_TRANSCRIPT_ROOTS", "REGISTRY_ROOTS", "GENESIS_ROOTS", "STATE_CAPSULE_ROOTS", "DOSSIER_ROOTS", "OBSERVATION_ROOTS", "REPLAY_REFUSAL_ROOT"],
        "rollback": ["SUSPEND_TRANSPORTS", "REFUSE_NEW_EXCHANGE", "PRESERVE_HISTORIES", "REVOKE_TRIAL_SESSIONS", "RETAIN_RETIREMENT_HISTORY", "RESTORE_LOCAL_PIN"],
        "ceiling": "AUTHENTICATED_INFORMATION_ONLY_EXCHANGE",
    },
    "S3_REAL_A5_QUALIFICATION": {
        "entry": ["S2_ACCEPTANCE", "INDEPENDENT_ROLE_CUSTODY", "WITNESSED_KEY_CEREMONY", "ROLE_COLLISION_REFUSAL", "RECOVERY_AND_REVOCATION_TESTS", "EVIDENCE_SOURCE_BINDING", "INDEPENDENT_REVIEW"],
        "acceptance": ["IDENTITY_ROOTS", "PUBLIC_KEY_ROOTS", "CUSTODY_ATTESTATION_ROOTS", "CHALLENGE_ROOTS", "INDEPENDENCE_ROOT", "REVIEW_ROOT", "A5_PROPOSAL_ROOT"],
        "rollback": ["SUSPEND_PROPOSED_BINDING", "REVOKE_AFFECTED_KEYS", "PRESERVE_IDENTITY_LINEAGE", "MARK_DEPENDENTS_FOR_REQUALIFICATION", "REFUSE_FIXTURE_FALLBACK"],
        "ceiling": "UNBOUND_A5_PROPOSAL",
    },
    "S4_G0_OPENING": {
        "entry": ["GOVERNOR_A5_DECISION", "COMPUTATION_CONTRACT", "PINNED_INPUTS_AND_RUNTIME", "OBLIGATION_INVENTORY", "RESOURCE_BUDGET", "ROLLBACK_PLAN", "INDEPENDENT_VERTICAL_REVIEW"],
        "acceptance": ["GOVERNOR_DECISION_ROOT", "A5_BINDING_ROOT", "COMPUTATION_ROOT", "OBLIGATION_ROOT", "EXECUTION_ROOT", "RESOURCE_ROOT", "OUTPUT_ROOT", "SESSION_CLOSURE_ROOT"],
        "rollback": ["STOP_NEW_COMPUTATIONS", "CLOSE_SESSION", "PRESERVE_RECEIPTS", "RESTORE_RUNTIME_STATE", "SUSPEND_INPUTS", "REQUIRE_REQUALIFICATION"],
        "ceiling": "ONE_BOUNDED_G0_COMPUTATION",
    },
    "S5_LIMITED_STANDING": {
        "entry": ["S4_ACCEPTANCE", "EXACT_CLAIM_SEMANTICS", "DEPENDENCY_CLOSURE", "JURISDICTION_AND_EXPIRY", "REVOCATION_RULES", "INDEPENDENT_CLAIM_REVIEW", "GOVERNOR_CLAIM_DECISION"],
        "acceptance": ["CLAIM_ROOTS", "STANDING_TYPE", "JURISDICTION_ROOT", "DEPENDENCY_ROOT", "EVIDENCE_ROOT", "REVIEW_ROOT", "DECISION_ROOT", "EXPIRY_ROOT"],
        "rollback": ["SUSPEND_AFFECTED_STANDING", "PROPAGATE_SUSPICION", "PRESERVE_STANDING_EVENTS", "BLOCK_DOWNSTREAM_USE", "REQUIRE_NEW_DECISION"],
        "ceiling": "EXACT_LISTED_CLAIMS_ONLY",
    },
    "S6_PRODUCTION_ACTIVATION": {
        "entry": ["S5_COVERAGE", "QUALIFIED_RELEASE", "OPERATIONAL_IDENTITIES", "PINNED_HOSTS_AND_ENDPOINTS", "MONITORING_AND_INCIDENT_READINESS", "CANARY_REHEARSAL", "GOVERNOR_RELEASE_DECISION"],
        "acceptance": ["RELEASE_ROOT", "POSTIMAGE_ROOT", "HOST_ROOTS", "ROUTING_ROOT", "CANARY_ROOT", "HEALTH_ROOT", "MONITORING_ROOT", "DECISION_ROOT", "ACTIVATION_WINDOW_ROOT"],
        "rollback": ["STOP_OR_DIVERT_TRAFFIC", "DEACTIVATE_RELEASE", "RESTORE_LAST_ADMITTED_VERSION", "PRESERVE_INCIDENT_EVIDENCE", "REVOKE_RELEASE_SESSIONS", "VERIFY_RECOVERY"],
        "ceiling": "NAMED_RELEASE_HOSTS_ROUTES_AND_WINDOW",
    },
}


def stage_rank(stage: Any) -> int:
    require(stage in STAGES, "ACCEPTANCE_STAGE_INVALID")
    return STAGES.index(stage)


def build_acceptance_constitution(*, subject_root: str, predecessor_root: str) -> dict[str, Any]:
    stages = []
    for ordinal, stage in enumerate(STAGES):
        definition = STAGE_DEFINITIONS[stage]
        stages.append({
            "stage": stage,
            "ordinal": ordinal,
            "entry_criteria": list(definition["entry"]),
            "acceptance_evidence": list(definition["acceptance"]),
            "rollback_actions": list(definition["rollback"]),
            "authority_ceiling": definition["ceiling"],
            "automatic_promotion": False,
        })
    body = {
        "schema": "ucl.ucm.acceptance_constitution.v1",
        "subject_root": require_root(subject_root),
        "predecessor_root": require_root(predecessor_root),
        "stages": stages,
        "maximum_executable_stage": "S2_INFORMATION_ONLY_FEDERATION",
        "later_stages_are_specification_only": True,
        "automatic_promotion": False,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "constitution_root": root(body)}


def verify_acceptance_constitution(value: Any, *, expected_subject_root: str, expected_predecessor_root: str) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "subject_root", "predecessor_root", "stages", "maximum_executable_stage", "later_stages_are_specification_only", "automatic_promotion", "standing", "authority_effect", "constitution_root"}, "$.constitution")
    expected = build_acceptance_constitution(subject_root=expected_subject_root, predecessor_root=expected_predecessor_root)
    require(item == expected, "ACCEPTANCE_CONSTITUTION_RECOMPUTATION_MISMATCH")
    return deepcopy({key: item[key] for key in item if key != "constitution_root"})


def make_stage_entry_packet(
    *, constitution: dict[str, Any], stage: str, subject_root: str,
    prior_acceptance: dict[str, Any] | None, evidence_roots: dict[str, str],
    decision_root: str,
) -> dict[str, Any]:
    stage_rank(stage)
    require(subject_root == constitution["subject_root"], "STAGE_SUBJECT_MISMATCH")
    expected_names = STAGE_DEFINITIONS[stage]["entry"]
    require(list(evidence_roots) == sorted(expected_names) and set(evidence_roots) == set(expected_names), "STAGE_ENTRY_EVIDENCE_SET_INVALID")
    for value in evidence_roots.values():
        require_root(value)
    prior_root = None
    if stage != STAGES[0]:
        require(type(prior_acceptance) is dict, "PRIOR_STAGE_ACCEPTANCE_REQUIRED")
        verify_stage_acceptance(prior_acceptance, constitution=constitution)
        require(prior_acceptance["stage"] == STAGES[stage_rank(stage) - 1], "PRIOR_STAGE_SEQUENCE_INVALID")
        require(prior_acceptance["status"] == "ACCEPTED", "PRIOR_STAGE_NOT_ACCEPTED")
        prior_root = prior_acceptance["acceptance_root"]
        require(prior_root in evidence_roots.values(), "PRIOR_STAGE_ROOT_NOT_BOUND")
    else:
        require(prior_acceptance is None, "PRIOR_STAGE_UNEXPECTED")
    body = {
        "schema": "ucl.ucm.stage_entry_packet.v1",
        "constitution_root": constitution["constitution_root"],
        "subject_root": subject_root,
        "stage": stage,
        "ordinal": stage_rank(stage),
        "prior_acceptance_root": prior_root,
        "evidence_roots": dict(sorted(evidence_roots.items())),
        "decision_root": require_root(decision_root),
        "executable_here": stage_rank(stage) <= stage_rank(constitution["maximum_executable_stage"]),
        "authority_ceiling": STAGE_DEFINITIONS[stage]["ceiling"],
        "automatic_promotion": False,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "entry_root": root(body)}


def make_stage_acceptance(
    *, constitution: dict[str, Any], entry_packet: dict[str, Any], evidence_roots: dict[str, str],
    accepted: bool, reviewer_root: str,
) -> dict[str, Any]:
    verify_stage_entry_packet(entry_packet, constitution=constitution)
    stage = entry_packet["stage"]
    expected_names = STAGE_DEFINITIONS[stage]["acceptance"]
    require(list(evidence_roots) == sorted(expected_names) and set(evidence_roots) == set(expected_names), "STAGE_ACCEPTANCE_EVIDENCE_SET_INVALID")
    for value in evidence_roots.values():
        require_root(value)
    require(type(accepted) is bool, "STAGE_ACCEPTANCE_STATUS_INVALID")
    require(entry_packet["executable_here"] or not accepted, "STAGE_ABOVE_EXECUTABLE_CEILING")
    body = {
        "schema": "ucl.ucm.stage_acceptance.v1",
        "constitution_root": constitution["constitution_root"],
        "subject_root": entry_packet["subject_root"],
        "stage": stage,
        "ordinal": stage_rank(stage),
        "entry_root": entry_packet["entry_root"],
        "evidence_roots": dict(sorted(evidence_roots.items())),
        "reviewer_root": require_root(reviewer_root),
        "status": "ACCEPTED" if accepted else "HELD",
        "automatic_promotion": False,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "acceptance_root": root(body)}


def verify_stage_entry_packet(value: Any, *, constitution: dict[str, Any]) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "constitution_root", "subject_root", "stage", "ordinal", "prior_acceptance_root", "evidence_roots", "decision_root", "executable_here", "authority_ceiling", "automatic_promotion", "standing", "authority_effect", "entry_root"}, "$.entry")
    body = {key: item[key] for key in item if key != "entry_root"}
    require(item["schema"] == "ucl.ucm.stage_entry_packet.v1" and item["entry_root"] == root(body), "STAGE_ENTRY_ROOT_INVALID")
    stage_rank(item["stage"])
    require(item["constitution_root"] == constitution["constitution_root"] and item["subject_root"] == constitution["subject_root"], "STAGE_ENTRY_CONTEXT_MISMATCH")
    require(type(item["ordinal"]) is int and type(item["ordinal"]) is not bool and item["ordinal"] == stage_rank(item["stage"]), "STAGE_ENTRY_ORDINAL_INVALID")
    expected = STAGE_DEFINITIONS[item["stage"]]
    require(set(item["evidence_roots"]) == set(expected["entry"]) and list(item["evidence_roots"]) == sorted(item["evidence_roots"]), "STAGE_ENTRY_EVIDENCE_SET_INVALID")
    for value_root in item["evidence_roots"].values(): require_root(value_root)
    require(item["executable_here"] is (item["ordinal"] <= stage_rank(constitution["maximum_executable_stage"])), "STAGE_EXECUTABLE_FLAG_INVALID")
    require(item["authority_ceiling"] == expected["ceiling"] and item["automatic_promotion"] is False, "STAGE_ENTRY_CEILING_INVALID")
    require(item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "STAGE_ENTRY_AUTHORITY_INVALID")
    return deepcopy(body)


def verify_stage_acceptance(value: Any, *, constitution: dict[str, Any]) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "constitution_root", "subject_root", "stage", "ordinal", "entry_root", "evidence_roots", "reviewer_root", "status", "automatic_promotion", "standing", "authority_effect", "acceptance_root"}, "$.acceptance")
    body = {key: item[key] for key in item if key != "acceptance_root"}
    require(item["schema"] == "ucl.ucm.stage_acceptance.v1" and item["acceptance_root"] == root(body), "STAGE_ACCEPTANCE_ROOT_INVALID")
    stage_rank(item["stage"])
    require(item["constitution_root"] == constitution["constitution_root"] and item["subject_root"] == constitution["subject_root"], "STAGE_ACCEPTANCE_CONTEXT_MISMATCH")
    require(type(item["ordinal"]) is int and type(item["ordinal"]) is not bool and item["ordinal"] == stage_rank(item["stage"]), "STAGE_ACCEPTANCE_ORDINAL_INVALID")
    require(set(item["evidence_roots"]) == set(STAGE_DEFINITIONS[item["stage"]]["acceptance"]) and list(item["evidence_roots"]) == sorted(item["evidence_roots"]), "STAGE_ACCEPTANCE_EVIDENCE_SET_INVALID")
    for value_root in item["evidence_roots"].values(): require_root(value_root)
    require_root(item["entry_root"]); require_root(item["reviewer_root"])
    require(item["status"] in {"ACCEPTED", "HELD"} and item["automatic_promotion"] is False, "STAGE_ACCEPTANCE_STATUS_INVALID")
    require(item["status"] != "ACCEPTED" or item["ordinal"] <= stage_rank(constitution["maximum_executable_stage"]), "STAGE_ABOVE_EXECUTABLE_CEILING")
    require(item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "STAGE_ACCEPTANCE_AUTHORITY_INVALID")
    return deepcopy(body)


def verify_acceptance_chain(*, constitution: dict[str, Any], entries: list[dict[str, Any]], acceptances: list[dict[str, Any]]) -> dict[str, Any]:
    require(type(entries) is list and type(acceptances) is list and len(entries) == len(acceptances) and entries, "ACCEPTANCE_CHAIN_LENGTH_INVALID")
    require(len(entries) <= len(STAGES), "ACCEPTANCE_CHAIN_LENGTH_INVALID")
    prior_root = None
    roots: list[str] = []
    for index, (entry, acceptance) in enumerate(zip(entries, acceptances)):
        verify_stage_entry_packet(entry, constitution=constitution)
        verify_stage_acceptance(acceptance, constitution=constitution)
        expected_stage = STAGES[index]
        require(entry["stage"] == acceptance["stage"] == expected_stage, "ACCEPTANCE_CHAIN_STAGE_INVALID")
        require(entry["prior_acceptance_root"] == prior_root, "ACCEPTANCE_CHAIN_PREDECESSOR_INVALID")
        if index:
            require(prior_root in entry["evidence_roots"].values(), "ACCEPTANCE_CHAIN_PREDECESSOR_NOT_BOUND")
        require(acceptance["entry_root"] == entry["entry_root"], "ACCEPTANCE_CHAIN_ENTRY_MISMATCH")
        require(acceptance["status"] == "ACCEPTED", "ACCEPTANCE_CHAIN_NOT_ACCEPTED")
        prior_root = acceptance["acceptance_root"]
        roots.append(prior_root)
    body = {
        "schema": "ucl.ucm.acceptance_chain_verification.v1",
        "constitution_root": constitution["constitution_root"],
        "accepted_stages": [entry["stage"] for entry in entries],
        "acceptance_roots": roots,
        "terminal_acceptance_root": prior_root,
        "status": "PASS",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "verification_root": root(body)}


def build_rollback_contract(*, constitution: dict[str, Any], stage: str, subject_root: str, preimage_root: str, dependent_roots: list[str]) -> dict[str, Any]:
    stage_rank(stage)
    require(subject_root == constitution["subject_root"], "ROLLBACK_SUBJECT_MISMATCH")
    require(type(dependent_roots) is list and dependent_roots == sorted(dependent_roots) and len(dependent_roots) == len(set(dependent_roots)), "ROLLBACK_DEPENDENCY_SET_INVALID")
    for value in dependent_roots: require_root(value)
    body = {
        "schema": "ucl.ucm.stage_rollback_contract.v1",
        "constitution_root": constitution["constitution_root"],
        "subject_root": subject_root,
        "stage": stage,
        "preimage_root": require_root(preimage_root),
        "dependent_roots": dependent_roots,
        "actions": list(STAGE_DEFINITIONS[stage]["rollback"]),
        "history_rewrite_allowed": False,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "rollback_root": root(body)}

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import exact_keys, require, require_root, root
from .custody import verify_asymmetric
from .ecosystem import STAGES, stage_rank


STAGE_REQUIREMENTS = {
    "D3_REAL_IDENTITY_SEATING": {
        "EXTERNAL_REVIEW_VERDICT": "REVIEWER",
        "GOVERNOR_DECISION": "GOVERNOR",
        "IDENTITY_CEREMONY": "WITNESS",
        "OS_IDENTITY_ATTESTATION": "WITNESS",
        "REVOCATION_RECOVERY_CONTRACT": "RECOVERY",
    },
    "D4_PROTECTED_INSTALLATION": {
        "D3_ACCEPTANCE": "GOVERNOR",
        "HOST_CHANGE_AUTHORIZATION": "GOVERNOR",
        "PREIMAGE": "WITNESS",
        "STAGED_OBSERVATION": "WITNESS",
        "ROLLBACK_PLAN": "REVIEWER",
        "PROTECTED_EXECUTOR": "WITNESS",
        "POSTIMAGE_ACCEPTANCE": "REVIEWER",
    },
    "D5_PRODUCTION_ACTIVATION": {
        "D4_ACCEPTANCE": "GOVERNOR",
        "A5_DECISION": "GOVERNOR",
        "G0_DECISION": "GOVERNOR",
        "STANDING_DECISION": "GOVERNOR",
        "RELEASE_DECISION": "REVIEWER",
        "PRODUCTION_ROUTE_DECISION": "WITNESS",
        "MONITORING_AND_SHUTDOWN_CONTRACT": "REVIEWER",
    },
}
PREDECESSOR_STAGE = {
    "D3_REAL_IDENTITY_SEATING": "D2_INDEPENDENT_REVIEW",
    "D4_PROTECTED_INSTALLATION": "D3_REAL_IDENTITY_SEATING",
    "D5_PRODUCTION_ACTIVATION": "D4_PROTECTED_INSTALLATION",
}
ROLLBACK_RULES = {
    "D3_REAL_IDENTITY_SEATING": ["RETIRE_NEW_IDENTITIES", "RESTORE_PRIOR_IDENTITY_REGISTRY", "PRESERVE_HISTORY"],
    "D4_PROTECTED_INSTALLATION": ["STOP_NEW_RUNTIME", "RESTORE_PREIMAGE", "VERIFY_RESTORED_ROOT", "PRESERVE_HISTORY"],
    "D5_PRODUCTION_ACTIVATION": ["DISABLE_PRODUCTION_ROUTE", "RESTORE_D4_RUNTIME", "VERIFY_MONITORING", "PRESERVE_HISTORY"],
}
ACCEPTANCE_CHECKS = {
    "D3_REAL_IDENTITY_SEATING": ["ALL_IDENTITIES_DISTINCT", "PROVIDERS_EXTERNAL", "RETIREMENT_READY", "NO_PRIVATE_MATERIAL_EXPORTED"],
    "D4_PROTECTED_INSTALLATION": ["EXACT_CANDIDATE", "PROTECTED_EXECUTION", "HEALTH_PASS", "ROLLBACK_REHEARSED", "POSTIMAGE_MATCH"],
    "D5_PRODUCTION_ACTIVATION": ["REAL_A5_BOUND", "G0_BOUND", "STANDING_BOUND", "RELEASE_BOUND", "ROUTE_BOUND", "SHUTDOWN_READY"],
}


def _required_roles(stage: str) -> list[str]:
    return sorted(set(STAGE_REQUIREMENTS[stage].values()))


def _signer_pins(stage: str, role_key_roots: dict[str, str]) -> dict[str, str]:
    require(type(role_key_roots) is dict and set(role_key_roots) == set(_required_roles(stage)), "STAGE_SIGNER_PIN_SET_INVALID")
    return {role: require_root(role_key_roots[role]) for role in _required_roles(stage)}


def compile_stage_contract(*, stage: str, subject_root: str, predecessor_acceptance_root: str, role_key_roots: dict[str, str]) -> dict[str, Any]:
    require(stage in STAGE_REQUIREMENTS, "STAGE_CONTRACT_STAGE_INVALID")
    signer_pins = _signer_pins(stage, role_key_roots)
    body = {
        "schema": "ucl.ucm.deployment_stage_contract.v1", "stage": stage,
        "predecessor_stage": PREDECESSOR_STAGE[stage], "subject_root": require_root(subject_root),
        "predecessor_acceptance_root": require_root(predecessor_acceptance_root),
        "signer_pins": signer_pins, "identity_set_root": root(signer_pins),
        "entry_requirements": [{"requirement_id": key, "required_role": STAGE_REQUIREMENTS[stage][key]} for key in sorted(STAGE_REQUIREMENTS[stage])],
        "rollback_rules": ROLLBACK_RULES[stage], "acceptance_checks": ACCEPTANCE_CHECKS[stage],
        "maximum_effect_class": {"D3_REAL_IDENTITY_SEATING": "NONE", "D4_PROTECTED_INSTALLATION": "HOST_SECURITY", "D5_PRODUCTION_ACTIVATION": "PRODUCTION"}[stage],
        "automatic_entry": False, "automatic_acceptance": False, "separate_governor_decision_required": True,
        "current_program_can_execute": False, "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    }
    return {**body, "contract_root": root(body)}


def verify_stage_contract(value: Any, *, expected_subject_root: str, expected_predecessor_acceptance_root: str, expected_role_key_roots: dict[str, str] | None = None) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "stage", "predecessor_stage", "subject_root", "predecessor_acceptance_root", "signer_pins", "identity_set_root", "entry_requirements", "rollback_rules", "acceptance_checks", "maximum_effect_class", "automatic_entry", "automatic_acceptance", "separate_governor_decision_required", "current_program_can_execute", "standing", "authority_effect", "contract_root"}, "$.stage_contract")
    body = {key: item[key] for key in item if key != "contract_root"}
    require(item["schema"] == "ucl.ucm.deployment_stage_contract.v1" and item["contract_root"] == root(body), "STAGE_CONTRACT_ROOT_INVALID")
    require(item["stage"] in STAGE_REQUIREMENTS and item["predecessor_stage"] == PREDECESSOR_STAGE[item["stage"]], "STAGE_CONTRACT_SEQUENCE_INVALID")
    require(item["subject_root"] == require_root(expected_subject_root) and item["predecessor_acceptance_root"] == require_root(expected_predecessor_acceptance_root), "STAGE_CONTRACT_CONTEXT_MISMATCH")
    signer_pins = _signer_pins(item["stage"], item["signer_pins"])
    require(item["identity_set_root"] == root(signer_pins), "STAGE_SIGNER_PIN_SET_INVALID")
    if expected_role_key_roots is not None:
        require(signer_pins == _signer_pins(item["stage"], expected_role_key_roots), "STAGE_SIGNER_EXTERNAL_PIN_MISMATCH")
    expected_requirements = [{"requirement_id": key, "required_role": STAGE_REQUIREMENTS[item["stage"]][key]} for key in sorted(STAGE_REQUIREMENTS[item["stage"]])]
    require(item["entry_requirements"] == expected_requirements and item["rollback_rules"] == ROLLBACK_RULES[item["stage"]] and item["acceptance_checks"] == ACCEPTANCE_CHECKS[item["stage"]], "STAGE_CONTRACT_CONTENT_INVALID")
    require(item["automatic_entry"] is False and item["automatic_acceptance"] is False and item["separate_governor_decision_required"] is True and item["current_program_can_execute"] is False, "STAGE_CONTRACT_AUTHORITY_INVALID")
    require(item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "STAGE_CONTRACT_AUTHORITY_INVALID")
    return deepcopy(body)


def requirement_body(*, stage: str, requirement_id: str, subject_root: str, artifact_root: str, decision: str, sequence: int) -> dict[str, Any]:
    require(stage in STAGE_REQUIREMENTS and requirement_id in STAGE_REQUIREMENTS[stage], "STAGE_REQUIREMENT_INVALID")
    require(decision in {"ACCEPT", "REFUSE"}, "STAGE_REQUIREMENT_DECISION_INVALID")
    require(type(sequence) is int and type(sequence) is not bool and sequence > 0, "STAGE_REQUIREMENT_SEQUENCE_INVALID")
    return {
        "schema": "ucl.ucm.stage_requirement_attestation.v1", "stage": stage,
        "requirement_id": requirement_id, "subject_root": require_root(subject_root),
        "artifact_root": require_root(artifact_root), "decision": decision, "sequence": sequence,
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    }


def verify_stage_entry(
    *, contract: dict[str, Any], attestations: list[dict[str, Any]],
    identities: dict[str, dict[str, Any]], expected_subject_root: str,
    expected_predecessor_acceptance_root: str,
    expected_role_key_roots: dict[str, str],
) -> dict[str, Any]:
    # The expected signer set is an input from the caller's trust boundary.  It
    # must never be inferred from the contract being checked: doing so would
    # let a re-rooted contract appoint its own validating keys.
    verify_stage_contract(
        contract,
        expected_subject_root=expected_subject_root,
        expected_predecessor_acceptance_root=expected_predecessor_acceptance_root,
        expected_role_key_roots=expected_role_key_roots,
    )
    stage = contract["stage"]
    require(type(attestations) is list and len(attestations) == len(STAGE_REQUIREMENTS[stage]), "STAGE_ATTESTATION_SET_INVALID")
    checked: dict[str, str] = {}
    seen_sequences: set[tuple[str, int]] = set()
    for signed in attestations:
        require(type(signed) is dict and type(signed.get("body")) is dict, "STAGE_ATTESTATION_INVALID")
        candidate = signed["body"]
        requirement_id = candidate.get("requirement_id")
        require(requirement_id in STAGE_REQUIREMENTS[stage] and requirement_id not in checked, "STAGE_ATTESTATION_REQUIREMENT_INVALID")
        role = STAGE_REQUIREMENTS[stage][requirement_id]
        require(role in identities, "STAGE_ATTESTATION_IDENTITY_MISSING")
        identity = exact_keys(identities[role], {"schema", "role", "key_root", "public_key_hex", "generation"}, f"$.identities.{role}")
        require(identity["role"] == role, "STAGE_ATTESTATION_ROLE_MISMATCH")
        require(
            identity["key_root"] == contract["signer_pins"][role] == expected_role_key_roots[role],
            "STAGE_SIGNER_EXTERNAL_PIN_MISMATCH",
        )
        body = verify_asymmetric(signed, "UCL_UCM_STAGE_REQUIREMENT_V1", expected_key_root=identity["key_root"], public_key_hex=identity["public_key_hex"])
        exact_keys(body, {"schema", "stage", "requirement_id", "subject_root", "artifact_root", "decision", "sequence", "standing", "authority_effect"}, "$.attestation.body")
        require(body == requirement_body(stage=stage, requirement_id=requirement_id, subject_root=expected_subject_root, artifact_root=body["artifact_root"], decision=body["decision"], sequence=body["sequence"]), "STAGE_ATTESTATION_BODY_INVALID")
        require(body["decision"] == "ACCEPT", "STAGE_REQUIREMENT_REFUSED", detail=requirement_id)
        require((role, body["sequence"]) not in seen_sequences, "STAGE_ATTESTATION_SEQUENCE_REUSED")
        seen_sequences.add((role, body["sequence"])); checked[requirement_id] = body["body_root"] if "body_root" in body else signed["body_root"]
    require(set(checked) == set(STAGE_REQUIREMENTS[stage]), "STAGE_ATTESTATION_SET_INVALID")
    body = {
        "schema": "ucl.ucm.stage_entry_verification.v1", "contract_root": contract["contract_root"],
        "stage": stage, "subject_root": expected_subject_root,
        "attestation_roots": {key: checked[key] for key in sorted(checked)},
        "status": "ENTRY_CRITERIA_VERIFIED", "entry_executed": False,
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    }
    return {**body, "entry_verification_root": root(body)}


def compile_stage_acceptance_proposal(*, contract: dict[str, Any], entry_verification: dict[str, Any], check_evidence: dict[str, str], rollback_rehearsal_root: str) -> dict[str, Any]:
    require(type(entry_verification) is dict and entry_verification.get("schema") == "ucl.ucm.stage_entry_verification.v1", "STAGE_ENTRY_VERIFICATION_INVALID")
    entry_body = {key: value for key, value in entry_verification.items() if key != "entry_verification_root"}
    require(entry_verification.get("entry_verification_root") == root(entry_body) and entry_verification.get("contract_root") == contract.get("contract_root"), "STAGE_ENTRY_VERIFICATION_INVALID")
    stage = contract["stage"]
    require(type(check_evidence) is dict and set(check_evidence) == set(ACCEPTANCE_CHECKS[stage]), "STAGE_ACCEPTANCE_CHECK_SET_INVALID")
    checked = {key: require_root(check_evidence[key]) for key in sorted(check_evidence)}
    body = {
        "schema": "ucl.ucm.stage_acceptance_proposal.v1", "stage": stage,
        "contract_root": contract["contract_root"], "entry_verification_root": entry_verification["entry_verification_root"],
        "check_evidence": checked, "rollback_rehearsal_root": require_root(rollback_rehearsal_root),
        "status": "UNBOUND_ACCEPTANCE_PROPOSAL", "accepted": False, "executed": False,
        "separate_governor_decision_required": True, "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    }
    return {**body, "acceptance_proposal_root": root(body)}


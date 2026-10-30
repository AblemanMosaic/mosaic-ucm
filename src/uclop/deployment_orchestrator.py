from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import exact_keys, require, require_root, root
from .deployment_contracts import ACCEPTANCE_CHECKS, STAGES, verify_stage_contract, verify_stage_entry
from .platform_profiles import verify_platform_profile
from .release_management import verify_rollback_receipt


def make_custody_proposal(*, subject_root: str, required_roles: list[str]) -> dict[str, Any]:
    require(type(required_roles) is list and required_roles == sorted(required_roles) and len(required_roles) == len(set(required_roles)) and required_roles and all(type(role) is str and role for role in required_roles), "CUSTODY_PROPOSAL_ROLE_SET_INVALID")
    body = {
        "schema": "ucl.ucm.oef_c2_custody_proposal.v1", "subject_root": require_root(subject_root),
        "required_roles": list(required_roles), "identities_seated": False, "private_material_included": False,
        "status": "UNBOUND_PROPOSAL", "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    }
    return {**body, "custody_proposal_root": root(body)}


def verify_custody_proposal(value: Any, *, expected_subject_root: str) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "subject_root", "required_roles", "identities_seated", "private_material_included", "status", "standing", "authority_effect", "custody_proposal_root"}, "$.custody_proposal")
    expected = make_custody_proposal(subject_root=expected_subject_root, required_roles=item["required_roles"])
    require(item == expected, "CUSTODY_PROPOSAL_INVALID")
    return deepcopy({key: item[key] for key in item if key != "custody_proposal_root"})


def make_stage_dry_run(
    *, contract: dict[str, Any], expected_subject_root: str,
    expected_predecessor_acceptance_root: str, entry_verification: dict[str, Any],
    entry_attestations: list[dict[str, Any]], identities: dict[str, dict[str, Any]],
    expected_role_key_roots: dict[str, str],
    expected_upgrade_plan_root: str,
    check_evidence: dict[str, str], rollback_rehearsal: dict[str, Any],
    platform_profile: dict[str, Any], custody_proposal: dict[str, Any],
) -> dict[str, Any]:
    verify_stage_contract(contract, expected_subject_root=expected_subject_root, expected_predecessor_acceptance_root=expected_predecessor_acceptance_root, expected_role_key_roots=expected_role_key_roots)
    entry = exact_keys(entry_verification, {
        "schema", "contract_root", "stage", "subject_root", "attestation_roots", "status",
        "entry_executed", "standing", "authority_effect", "entry_verification_root",
    }, "$.entry_verification")
    entry_body = {key: entry[key] for key in entry if key != "entry_verification_root"}
    require(entry["schema"] == "ucl.ucm.stage_entry_verification.v1" and entry["entry_verification_root"] == root(entry_body), "STAGE_ENTRY_VERIFICATION_INVALID")
    require(entry["contract_root"] == contract["contract_root"] and entry["stage"] == contract["stage"] and entry["subject_root"] == expected_subject_root, "STAGE_ENTRY_VERIFICATION_CONTEXT_MISMATCH")
    require(entry["status"] == "ENTRY_CRITERIA_VERIFIED" and entry["entry_executed"] is False, "STAGE_ENTRY_ALREADY_EXECUTED")
    recomputed_entry = verify_stage_entry(
        contract=contract, attestations=entry_attestations, identities=identities,
        expected_subject_root=expected_subject_root,
        expected_predecessor_acceptance_root=expected_predecessor_acceptance_root,
        expected_role_key_roots=expected_role_key_roots,
    )
    require(recomputed_entry == entry_verification, "STAGE_ENTRY_VERIFICATION_RECOMPUTATION_MISMATCH")
    require(type(check_evidence) is dict and set(check_evidence) == set(ACCEPTANCE_CHECKS[contract["stage"]]), "STAGE_ACCEPTANCE_CHECK_SET_INVALID")
    checked = {key: require_root(check_evidence[key]) for key in sorted(check_evidence)}
    upgrade_plan_root = require_root(expected_upgrade_plan_root)
    verify_rollback_receipt(rollback_rehearsal, expected_upgrade_plan_root=upgrade_plan_root)
    verify_platform_profile(platform_profile)
    verify_custody_proposal(custody_proposal, expected_subject_root=expected_subject_root)
    body = {
        "schema": "ucl.ucm.stage_dry_run.v1", "stage": contract["stage"],
        "contract": deepcopy(contract), "contract_root": contract["contract_root"], "subject_root": require_root(expected_subject_root),
        "predecessor_acceptance_root": require_root(expected_predecessor_acceptance_root),
        "entry_verification": deepcopy(entry_verification), "entry_verification_root": entry["entry_verification_root"],
        "entry_attestations": deepcopy(entry_attestations), "identities": deepcopy(identities),
        "externally_pinned_role_key_roots": {key: expected_role_key_roots[key] for key in sorted(expected_role_key_roots)},
        "external_signer_pin_set_root": root({key: expected_role_key_roots[key] for key in sorted(expected_role_key_roots)}),
        "acceptance_check_evidence": checked,
        "externally_pinned_upgrade_plan_root": upgrade_plan_root,
        "rollback_rehearsal": deepcopy(rollback_rehearsal), "rollback_rehearsal_root": rollback_rehearsal["rollback_receipt_root"],
        "platform_profile": deepcopy(platform_profile), "platform_profile_root": platform_profile["profile_root"],
        "custody_proposal": deepcopy(custody_proposal), "custody_proposal_root": custody_proposal["custody_proposal_root"],
        "fixture_only": True, "predecessor_acceptance_effective": False, "entry_evidence_authoritative": False,
        "status": "DRY_RUN_READY", "entry_executed": False, "acceptance_granted": False,
        "stage_advanced": False, "separate_governor_decision_required": True,
        "effect_observed": "NONE", "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    }
    return {**body, "dry_run_root": root(body)}


def compile_deployment_program(
    *, subject_root: str, dry_runs: list[dict[str, Any]],
    expected_role_key_roots_by_stage: dict[str, dict[str, str]],
    expected_upgrade_plan_roots_by_stage: dict[str, str],
) -> dict[str, Any]:
    require(type(dry_runs) is list and dry_runs, "DEPLOYMENT_PROGRAM_EMPTY")
    ordered: list[dict[str, Any]] = []
    stages: list[str] = []
    for index, item in enumerate(dry_runs):
        item = exact_keys(item, {
            "schema", "stage", "contract_root", "subject_root", "predecessor_acceptance_root",
            "contract", "entry_verification", "entry_verification_root", "entry_attestations", "identities",
            "externally_pinned_role_key_roots", "external_signer_pin_set_root",
            "acceptance_check_evidence", "externally_pinned_upgrade_plan_root",
            "rollback_rehearsal", "rollback_rehearsal_root",
            "platform_profile", "platform_profile_root", "custody_proposal", "custody_proposal_root", "status", "entry_executed",
            "fixture_only", "predecessor_acceptance_effective", "entry_evidence_authoritative",
            "acceptance_granted", "stage_advanced", "separate_governor_decision_required",
            "effect_observed", "standing", "authority_effect", "dry_run_root",
        }, f"$.dry_runs[{index}]")
        body = {key: item[key] for key in item if key != "dry_run_root"}
        require(item["schema"] == "ucl.ucm.stage_dry_run.v1" and item["dry_run_root"] == root(body), "STAGE_DRY_RUN_ROOT_INVALID")
        require(item["subject_root"] == subject_root and item["status"] == "DRY_RUN_READY", "STAGE_DRY_RUN_CONTEXT_INVALID")
        require(item["stage"] in expected_role_key_roots_by_stage, "STAGE_EXTERNAL_PIN_SET_MISSING")
        expected_pins = expected_role_key_roots_by_stage[item["stage"]]
        verify_stage_contract(item["contract"], expected_subject_root=subject_root, expected_predecessor_acceptance_root=item["predecessor_acceptance_root"], expected_role_key_roots=expected_pins)
        require(item["externally_pinned_role_key_roots"] == {key: expected_pins[key] for key in sorted(expected_pins)} and item["external_signer_pin_set_root"] == root(item["externally_pinned_role_key_roots"]), "STAGE_EXTERNAL_PIN_SET_MISMATCH")
        require(item["contract_root"] == item["contract"]["contract_root"] and item["stage"] == item["contract"]["stage"], "STAGE_DRY_RUN_CONTRACT_MISMATCH")
        recomputed_entry = verify_stage_entry(contract=item["contract"], attestations=item["entry_attestations"], identities=item["identities"], expected_subject_root=subject_root, expected_predecessor_acceptance_root=item["predecessor_acceptance_root"], expected_role_key_roots=expected_pins)
        require(item["entry_verification"] == recomputed_entry and item["entry_verification_root"] == recomputed_entry["entry_verification_root"], "STAGE_DRY_RUN_ENTRY_MISMATCH")
        require(type(item["acceptance_check_evidence"]) is dict and set(item["acceptance_check_evidence"]) == set(ACCEPTANCE_CHECKS[item["stage"]]), "STAGE_ACCEPTANCE_CHECK_SET_INVALID")
        for evidence_root in item["acceptance_check_evidence"].values(): require_root(evidence_root)
        require(item["stage"] in expected_upgrade_plan_roots_by_stage, "STAGE_UPGRADE_PLAN_PIN_MISSING")
        expected_upgrade_plan_root = require_root(expected_upgrade_plan_roots_by_stage[item["stage"]])
        require(item["externally_pinned_upgrade_plan_root"] == expected_upgrade_plan_root, "STAGE_UPGRADE_PLAN_PIN_MISMATCH")
        verify_rollback_receipt(item["rollback_rehearsal"], expected_upgrade_plan_root=expected_upgrade_plan_root)
        require(item["rollback_rehearsal_root"] == item["rollback_rehearsal"]["rollback_receipt_root"], "STAGE_DRY_RUN_ROLLBACK_MISMATCH")
        verify_platform_profile(item["platform_profile"])
        require(item["platform_profile_root"] == item["platform_profile"]["profile_root"], "STAGE_DRY_RUN_PLATFORM_MISMATCH")
        verify_custody_proposal(item["custody_proposal"], expected_subject_root=subject_root)
        require(item["custody_proposal_root"] == item["custody_proposal"]["custody_proposal_root"], "STAGE_DRY_RUN_CUSTODY_MISMATCH")
        require(item["entry_executed"] is False and item["acceptance_granted"] is False and item["stage_advanced"] is False, "STAGE_DRY_RUN_AUTHORITY_INVALID")
        require(item["fixture_only"] is True and item["predecessor_acceptance_effective"] is False and item["entry_evidence_authoritative"] is False, "STAGE_DRY_RUN_SCOPE_INVALID")
        require(item["separate_governor_decision_required"] is True, "STAGE_DRY_RUN_AUTHORITY_INVALID")
        require(item["effect_observed"] == "NONE" and item["authority_effect"] == "NONE" and item["standing"] == "INFORMATION_ONLY", "STAGE_DRY_RUN_AUTHORITY_INVALID")
        stages.append(item["stage"]); ordered.append(deepcopy(item))
    expected_prefix = list(STAGES[1:1 + len(stages)])
    require(stages == expected_prefix, "DEPLOYMENT_PROGRAM_STAGE_ORDER_INVALID")
    require(set(expected_role_key_roots_by_stage) == set(stages), "STAGE_EXTERNAL_PIN_POLICY_INVALID")
    require(set(expected_upgrade_plan_roots_by_stage) == set(stages), "STAGE_UPGRADE_PLAN_PIN_POLICY_INVALID")
    pin_policy = {stage: {key: expected_role_key_roots_by_stage[stage][key] for key in sorted(expected_role_key_roots_by_stage[stage])} for stage in sorted(expected_role_key_roots_by_stage)}
    body = {
        "schema": "ucl.ucm.deployment_program.v1", "subject_root": require_root(subject_root),
        "dry_runs": ordered, "stage_order": stages, "all_entry_criteria_rehearsed": True,
        "external_signer_pin_policy_root": root(pin_policy),
        "all_rollbacks_rehearsed": True, "admitted": False, "installed": False, "released": False,
        "fixture_only": True, "predecessor_acceptances_effective": False,
        "production_active": False, "real_a5": False, "g0": "CLOSED",
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    }
    return {**body, "program_root": root(body)}


def verify_deployment_program(
    value: Any, *, expected_subject_root: str,
    expected_role_key_roots_by_stage: dict[str, dict[str, str]],
    expected_upgrade_plan_roots_by_stage: dict[str, str],
) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "subject_root", "dry_runs", "stage_order", "all_entry_criteria_rehearsed",
        "all_rollbacks_rehearsed", "external_signer_pin_policy_root", "admitted", "installed", "released", "production_active",
        "fixture_only", "predecessor_acceptances_effective",
        "real_a5", "g0", "standing", "authority_effect", "program_root",
    }, "$.deployment_program")
    body = {key: item[key] for key in item if key != "program_root"}
    require(item["schema"] == "ucl.ucm.deployment_program.v1" and item["program_root"] == root(body), "DEPLOYMENT_PROGRAM_ROOT_INVALID")
    rebuilt = compile_deployment_program(
        subject_root=expected_subject_root, dry_runs=item["dry_runs"],
        expected_role_key_roots_by_stage=expected_role_key_roots_by_stage,
        expected_upgrade_plan_roots_by_stage=expected_upgrade_plan_roots_by_stage,
    )
    require(rebuilt == item, "DEPLOYMENT_PROGRAM_RECOMPUTATION_MISMATCH")
    return deepcopy(body)


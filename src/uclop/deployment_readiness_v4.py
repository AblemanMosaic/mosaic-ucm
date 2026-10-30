from __future__ import annotations

from copy import deepcopy
import re
import unicodedata
from typing import Any

from .canonical import exact_keys, require, require_root, root
from .custody import CustodyProvider, verify_asymmetric


STAGE_ORDER = {
    "D0_PACKAGE_PREFLIGHT": 0,
    "D1_DISPOSABLE_PROTECTED_REHEARSAL": 1,
    "D2_INDEPENDENT_REVIEW": 2,
    "D3_REAL_IDENTITY_SEATING": 3,
    "D4_PROTECTED_INSTALLATION": 4,
    "D5_PRODUCTION_ACTIVATION": 5,
}
EXECUTABLE_CEILING = "D2_INDEPENDENT_REVIEW"
STAGE_CRITERIA = {
    "D0_PACKAGE_PREFLIGHT": ("EXACT_DEPENDENCY_PIN", "CLOSED_SOURCE_MANIFEST", "PREDECESSOR_QUALIFICATION", "AUTHORITY_CEILING", "NO_EFFECT_BOUNDARY"),
    "D1_DISPOSABLE_PROTECTED_REHEARSAL": ("D0_ACCEPTANCE", "PROTECTED_EXECUTION_PLAN", "DISPOSABLE_ROOT", "ROLLBACK_CONTRACT", "NETWORK_DENIAL", "PERSISTENT_EFFECT_DENIAL"),
    "D2_INDEPENDENT_REVIEW": ("D1_ACCEPTANCE", "DETERMINISTIC_FREEZE", "RECONSTRUCTION_PROOF", "EXTERNAL_PINS", "REVIEW_WORK_ORDER", "REVIEWER_AUTHORITY_CEILING"),
    "D3_REAL_IDENTITY_SEATING": ("INDEPENDENT_QUALIFICATION", "GOVERNOR_DECISION", "CUSTODY_CEREMONY", "OS_IDENTITY_ATTESTATION", "REVOCATION_AND_RECOVERY_PLAN"),
    "D4_PROTECTED_INSTALLATION": ("D3_ACCEPTANCE", "HOST_CHANGE_AUTHORIZATION", "STAGED_ARTIFACT_OBSERVATION", "INSTALL_ROLLBACK_PLAN", "PROTECTED_EXECUTOR", "POSTINSTALL_ACCEPTANCE"),
    "D5_PRODUCTION_ACTIVATION": ("D4_ACCEPTANCE", "REAL_A5_DECISION", "G0_DECISION", "STANDING_DECISION", "RELEASE_DECISION", "PRODUCTION_ROUTE_DECISION"),
}
STAGE_ACCEPTANCE = {
    "D0_PACKAGE_PREFLIGHT": ("DEPENDENCY_VERIFIED", "SOURCE_ROOT_RECOMPUTED", "PREDECESSOR_QUALIFICATION_VERIFIED", "CEILING_PRESERVED", "ZERO_EFFECTS"),
    "D1_DISPOSABLE_PROTECTED_REHEARSAL": ("PLAN_BOUND", "CANDIDATE_UNCHANGED", "WRITES_CONFINED", "NETWORK_REFUSED", "PERSISTENT_EFFECTS_REFUSED", "ROLLBACK_REHEARSED"),
    "D2_INDEPENDENT_REVIEW": ("TRANSPORT_PINNED", "SOURCE_RECONSTRUCTED", "COURTS_ATTACKED", "VERDICT_BOUND", "ZERO_AUTHORITY_EFFECT"),
    "D3_REAL_IDENTITY_SEATING": ("GOVERNOR_SOURCE_AUTHENTICATED", "PUBLIC_KEYS_VERIFIED", "OS_IDENTITIES_VERIFIED", "CUSTODIANS_DISTINCT", "RECOVERY_BOUND"),
    "D4_PROTECTED_INSTALLATION": ("PREIMAGE_CAPTURED", "INSTALLATION_EXACT", "HOST_POLICY_EFFECTIVE", "ROLLBACK_PROVEN", "POSTIMAGE_ACCEPTED"),
    "D5_PRODUCTION_ACTIVATION": ("A5_BOUND", "G0_OPEN", "STANDING_GRANTED", "RELEASE_GRANTED", "PRODUCTION_ROUTE_ACTIVE"),
}
_ORDERED_STAGES = tuple(STAGE_ORDER)
PREVIOUS_STAGE = {_ORDERED_STAGES[i]: _ORDERED_STAGES[i - 1] for i in range(1, len(_ORDERED_STAGES))}
PREDECESSOR_CRITERION = {"D1_DISPOSABLE_PROTECTED_REHEARSAL": "D0_ACCEPTANCE", "D2_INDEPENDENT_REVIEW": "D1_ACCEPTANCE", "D3_REAL_IDENTITY_SEATING": "INDEPENDENT_QUALIFICATION", "D4_PROTECTED_INSTALLATION": "D3_ACCEPTANCE", "D5_PRODUCTION_ACTIVATION": "D4_ACCEPTANCE"}

ROLLBACK_ACTIONS = {"DELETE_DISPOSABLE_OUTPUT", "RESTORE_FIXTURE_STATE", "VERIFY_CANDIDATE_PREIMAGE", "VERIFY_PROTECTED_STATE", "PRESERVE_TERMINAL_EVIDENCE"}
PORTABILITY_CAPABILITIES = {"ATOMIC_REPLACE", "FSYNC_FILE", "ISOLATED_PYTHON", "STRICT_UTF8", "DISPOSABLE_DIRECTORY", "AUDIT_HOOK", "PATH_CASE_OBSERVATION", "SYMLINK_OBSERVATION", "TERMINAL_CAPTURE"}
CEREMONY_ROLES = ("GOVERNOR", "H_M", "H_J", "RECOVERY", "WITNESS", "REVIEWER")
ROLE_ADDRESSES = {role: "ucl://role/" + role.casefold() for role in CEREMONY_ROLES}
CEREMONY_DOMAIN = "UCL_UCM_DEPLOYMENT_IDENTITY_CEREMONY_V2"
ACCEPTANCE_DOMAIN = "UCL_UCM_DEPLOYMENT_STAGE_ACCEPTANCE_V3"
ROLLBACK_DOMAIN = "UCL_UCM_DEPLOYMENT_ROLLBACK_RECEIPT_V3"
EXECUTION_DOMAIN = "UCL_UCM_PROTECTED_EXECUTION_RECEIPT_V3"
REVIEW_DOMAIN = "UCL_UCM_INDEPENDENT_REVIEW_RESULT_V2"
QUALIFYING_REVIEW_VERDICTS = {"QUALIFIED_RECOMMENDATION_ONLY"}
REVIEW_VERDICTS = QUALIFYING_REVIEW_VERDICTS | {"HOLD_FOR_REPAIR", "NOT_QUALIFIED"}
SECRET_KEYS = {"privatekey", "privatekeyhex", "seed", "seedhex", "secret", "token", "password", "passwd", "apikey", "accesstoken", "bearertoken", "credential", "clientsecret", "jwt", "authorization", "signingkey", "mnemonic", "passphrase"}
DAR_C5_STAGE_CONTRACT_ROOT = "cac219d9cb4370c2f9bd35e37cf2883c8a8b64c7491a7c4f7542e96a35e36495"
DAR_C5_WITNESS_KEY_ROOT = "7599776c3085e3f9da0d13071eb0b4ab50fd2bf64c06dd92c2365af3a328eca3"


def _require_contract_pinned_signer(stage_contract_root: str, identity: dict[str, Any], role: str, expected_key_root: str | None = None) -> None:
    """Require a signer pin that does not come from the evidence being checked."""
    require(identity.get("role") == role, "DEPLOYMENT_ACCEPTANCE_ROLE_INVALID")
    if stage_contract_root == DAR_C5_STAGE_CONTRACT_ROOT and role == "WITNESS":
        require(identity.get("key_root") == DAR_C5_WITNESS_KEY_ROOT, "STAGE_CONTRACT_SIGNER_PIN_MISMATCH")
    else:
        require(expected_key_root is not None, "LEGACY_STAGE_SIGNER_EXTERNAL_PIN_REQUIRED")
        require(identity.get("key_root") == require_root(expected_key_root), "STAGE_CONTRACT_SIGNER_PIN_MISMATCH")


def _nonempty_text(value: Any, code: str) -> str:
    require(type(value) is str and bool(value.strip()), code)
    return value


def _stage(value: Any) -> str:
    require(type(value) is str and value in STAGE_ORDER, "DEPLOYMENT_STAGE_INVALID")
    return value


def _within_ceiling(stage: str) -> None:
    require(STAGE_ORDER[stage] <= STAGE_ORDER[EXECUTABLE_CEILING], "DEPLOYMENT_STAGE_ABOVE_EXPERIMENTAL_CEILING")


def _safe_relpath(value: Any, path: str = "$") -> str:
    require(type(value) is str and bool(value), "ARTIFACT_PATH_INVALID", path)
    normalized = value.replace("\\", "/")
    require(not normalized.startswith("/") and not re.match(r"^[A-Za-z]:", normalized), "ARTIFACT_PATH_ABSOLUTE", path)
    parts = normalized.split("/")
    require(all(part not in {"", ".", ".."} for part in parts), "ARTIFACT_PATH_UNSAFE", path)
    require(len(parts) <= 32 and all(len(part.encode("utf-8")) <= 128 for part in parts) and len(normalized.encode("utf-8")) <= 1024, "ARTIFACT_PATH_LIMIT", path)
    return normalized


def _root_map(value: Any, expected: tuple[str, ...], path: str) -> dict[str, str]:
    require(type(value) is dict and set(value) == set(expected), "EVIDENCE_SET_INVALID", path)
    return {key: require_root(value[key], f"{path}.{key}") for key in sorted(value)}


def artifact_evidence_binding(criterion: str, artifact_kind: str, artifact: Any, *, stage_contract_root: str) -> dict[str, Any]:
    """Return the external binding a verifier must derive from the named subject.

    A binding is deliberately not taken from an evidence envelope.  Admission
    code must derive it from the source manifest, qualification, execution
    result, rollback receipt, or independently pinned review it is checking.
    """
    _nonempty_text(criterion, "EVIDENCE_CRITERION_INVALID")
    _nonempty_text(artifact_kind, "EVIDENCE_KIND_INVALID")
    return {
        "criterion": criterion,
        "artifact_kind": artifact_kind,
        "artifact_root": root(artifact),
        "derivation": "SUBJECT_STAGE_CONTRACT",
        "stage_contract_root": require_root(stage_contract_root),
    }


def make_artifact_evidence(criterion: str, artifact_kind: str, artifact: Any) -> dict[str, Any]:
    _nonempty_text(criterion, "EVIDENCE_CRITERION_INVALID"); _nonempty_text(artifact_kind, "EVIDENCE_KIND_INVALID")
    body = {"schema": "ucl.ucm.typed_artifact_evidence.v1", "criterion": criterion, "artifact_kind": artifact_kind, "artifact": deepcopy(artifact), "artifact_root": root(artifact), "status": "PASS", "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "evidence_root": root(body)}


def verify_artifact_evidence(value: Any, *, criterion: str, expected_binding: dict[str, Any]) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "criterion", "artifact_kind", "artifact", "artifact_root", "status", "standing", "authority_effect", "evidence_root"}, "$.evidence")
    body = {key: item[key] for key in item if key != "evidence_root"}
    require(item["schema"] == "ucl.ucm.typed_artifact_evidence.v1" and item["criterion"] == criterion, "EVIDENCE_CRITERION_MISMATCH")
    binding = exact_keys(
        expected_binding,
        {"criterion", "artifact_kind", "artifact_root", "derivation", "stage_contract_root"},
        "$.expected_binding",
    )
    require(binding["criterion"] == criterion, "EVIDENCE_BINDING_CRITERION_MISMATCH")
    require(binding["derivation"] == "SUBJECT_STAGE_CONTRACT", "EVIDENCE_BINDING_DERIVATION_INVALID")
    require_root(binding["stage_contract_root"])
    _nonempty_text(item["artifact_kind"], "EVIDENCE_KIND_INVALID")
    require(item["artifact_kind"] == binding["artifact_kind"], "EVIDENCE_KIND_MISMATCH")
    require(item["artifact_root"] == root(item["artifact"]), "EVIDENCE_ARTIFACT_ROOT_INVALID")
    require(item["artifact_root"] == require_root(binding["artifact_root"]), "EVIDENCE_SUBJECT_BINDING_MISMATCH")
    require(item["status"] == "PASS" and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "EVIDENCE_STATUS_INVALID")
    require(item["evidence_root"] == root(body), "EVIDENCE_ROOT_INVALID")
    return deepcopy(body)


def derive_evidence_bindings(materials: dict[str, Any], expected: tuple[str, ...], *, stage_contract_root: str) -> dict[str, Any]:
    """Derive expectations from authoritative subject material, never envelopes.

    ``materials`` is a separately constructed mapping of criterion to an exact
    artifact kind and artifact body.  Callers must bind it to the externally
    pinned stage contract root.  Evidence envelopes are produced only after
    this mapping exists.
    """
    require(type(materials) is dict and set(materials) == set(expected), "EVIDENCE_MATERIAL_SET_INVALID")
    result = {}
    for criterion in sorted(materials):
        material = exact_keys(materials[criterion], {"artifact_kind", "artifact"}, f"$.materials.{criterion}")
        result[criterion] = artifact_evidence_binding(
            criterion,
            material["artifact_kind"],
            material["artifact"],
            stage_contract_root=stage_contract_root,
        )
    return result


def evidence_bindings(value: dict[str, Any], expected: tuple[str, ...]) -> dict[str, Any]:
    """Retired unsafe helper retained only as a typed refusal boundary."""
    require(type(value) is dict and set(value) == set(expected), "EVIDENCE_SET_INVALID")
    require(False, "EVIDENCE_SELF_BINDING_FORBIDDEN")
    raise AssertionError


def _evidence_map(value: Any, expected: tuple[str, ...], expected_bindings: dict[str, Any], *, stage_contract_root: str) -> dict[str, Any]:
    require(type(value) is dict and set(value) == set(expected), "EVIDENCE_SET_INVALID")
    require(type(expected_bindings) is dict and set(expected_bindings) == set(expected), "EVIDENCE_BINDING_SET_INVALID")
    checked = {}
    for criterion in sorted(value):
        binding = exact_keys(
            expected_bindings[criterion],
            {"criterion", "artifact_kind", "artifact_root", "derivation", "stage_contract_root"},
            f"$.bindings.{criterion}",
        )
        require(binding["derivation"] == "SUBJECT_STAGE_CONTRACT", "EVIDENCE_BINDING_DERIVATION_INVALID")
        require(binding["stage_contract_root"] == require_root(stage_contract_root), "EVIDENCE_STAGE_CONTRACT_MISMATCH")
        verify_artifact_evidence(value[criterion], criterion=criterion, expected_binding=expected_bindings[criterion])
        checked[criterion] = value[criterion]
    return checked


def stage_specification(stage: str) -> dict[str, Any]:
    stage = _stage(stage)
    body = {"schema": "ucl.ucm.deployment_stage_specification.v2", "stage": stage, "stage_order": STAGE_ORDER[stage], "entry_criteria": list(STAGE_CRITERIA[stage]), "acceptance_checks": list(STAGE_ACCEPTANCE[stage]), "predecessor_stage": PREVIOUS_STAGE.get(stage, "GENESIS"), "executable_in_this_program": STAGE_ORDER[stage] <= STAGE_ORDER[EXECUTABLE_CEILING], "maximum_executable_stage": EXECUTABLE_CEILING, "automatic_entry": False, "automatic_promotion": False, "real_a5": False, "g0": "CLOSED", "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "specification_root": root(body)}


def make_independent_review_result(provider: CustodyProvider, handle: str, *, subject_root: str, qualification_root: str, evidence_archive_root: str, report_root: str, findings: list[dict[str, Any]], verdict: str) -> dict[str, Any]:
    identity = provider.identity(handle); require(identity["role"] == "REVIEWER", "REVIEWER_ROLE_INVALID")
    require(verdict in REVIEW_VERDICTS and type(findings) is list, "REVIEW_VERDICT_INVALID")
    body = {"schema": "ucl.ucm.independent_review_result.v2", "subject_root": require_root(subject_root), "qualification_root": require_root(qualification_root), "evidence_archive_root": require_root(evidence_archive_root), "report_root": require_root(report_root), "findings": deepcopy(findings), "findings_root": root(findings), "verdict": verdict, "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    signed = provider.sign(handle, REVIEW_DOMAIN, body)
    return {**signed, "review_root": root(signed)}


def verify_independent_review_result(value: Any, *, expected_subject_root: str, expected_qualification_root: str, expected_identity: dict[str, Any]) -> dict[str, Any]:
    item = exact_keys(value, {"body", "body_root", "signature", "key_root", "signature_algorithm", "review_root"}, "$.review")
    require(expected_identity.get("role") == "REVIEWER", "REVIEWER_ROLE_INVALID")
    signed = {key: item[key] for key in ("body", "body_root", "signature", "key_root", "signature_algorithm")}
    body = verify_asymmetric(signed, REVIEW_DOMAIN, expected_key_root=expected_identity["key_root"], public_key_hex=expected_identity["public_key_hex"])
    exact_keys(body, {"schema", "subject_root", "qualification_root", "evidence_archive_root", "report_root", "findings", "findings_root", "verdict", "standing", "authority_effect"}, "$.review.body")
    require(body["schema"] == "ucl.ucm.independent_review_result.v2" and body["subject_root"] == require_root(expected_subject_root) and body["qualification_root"] == require_root(expected_qualification_root), "REVIEW_SUBJECT_OR_QUALIFICATION_MISMATCH")
    require(body["findings_root"] == root(body["findings"]) and body["verdict"] in REVIEW_VERDICTS, "REVIEW_CONTENT_INVALID")
    require(body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE" and item["review_root"] == root(signed), "REVIEW_ROOT_INVALID")
    return deepcopy(body)


def _verify_acceptance_signature(
    value: Any,
    *,
    expected_identity: dict[str, Any],
    expected_subject_root: str,
    expected_stage: str,
    expected_entry_packet_root: str,
    expected_check_bindings: dict[str, Any],
    expected_stage_contract_root: str,
    expected_signer_key_root: str | None = None,
) -> dict[str, Any]:
    """Verify the complete predecessor contract, not just its signature."""
    body = verify_stage_acceptance_receipt(
        value,
        expected_entry_packet_root=expected_entry_packet_root,
        expected_identity=expected_identity,
        expected_check_bindings=expected_check_bindings,
        expected_stage_contract_root=expected_stage_contract_root,
        expected_subject_root=expected_subject_root,
        expected_signer_key_root=expected_signer_key_root,
    )
    require(body["stage"] == expected_stage, "DEPLOYMENT_PREDECESSOR_STAGE_INVALID")
    return body


def make_stage_entry_packet(
    stage: str,
    *,
    subject_root: str,
    stage_contract_root: str,
    predecessor_acceptance: Any,
    predecessor_identity: dict[str, Any] | None,
    predecessor_entry_packet_root: str | None = None,
    predecessor_check_bindings: dict[str, Any] | None = None,
    predecessor_stage_contract_root: str | None = None,
    expected_predecessor_key_root: str | None = None,
    criteria_evidence: dict[str, Any],
    criteria_bindings: dict[str, Any],
    rollback_contract_root: str,
) -> dict[str, Any]:
    stage = _stage(stage); _within_ceiling(stage); stage_contract_root = require_root(stage_contract_root)
    checked = _evidence_map(criteria_evidence, STAGE_CRITERIA[stage], criteria_bindings, stage_contract_root=stage_contract_root)
    if stage == "D0_PACKAGE_PREFLIGHT":
        require(predecessor_acceptance == "GENESIS" and predecessor_identity is None, "DEPLOYMENT_PREDECESSOR_INVALID"); predecessor_root = "GENESIS"
    else:
        require(type(predecessor_identity) is dict, "DEPLOYMENT_PREDECESSOR_IDENTITY_REQUIRED")
        _require_contract_pinned_signer(stage_contract_root, predecessor_identity, "WITNESS", expected_predecessor_key_root)
        require(predecessor_entry_packet_root is not None and type(predecessor_check_bindings) is dict and predecessor_stage_contract_root is not None, "DEPLOYMENT_PREDECESSOR_CONTRACT_REQUIRED")
        prior = _verify_acceptance_signature(
            predecessor_acceptance,
            expected_identity=predecessor_identity,
            expected_subject_root=subject_root,
            expected_stage=PREVIOUS_STAGE[stage],
            expected_entry_packet_root=predecessor_entry_packet_root,
            expected_check_bindings=predecessor_check_bindings,
            expected_stage_contract_root=predecessor_stage_contract_root,
            expected_signer_key_root=expected_predecessor_key_root,
        )
        require(prior["accepted_for_next_stage"] is True, "DEPLOYMENT_PREDECESSOR_STAGE_INVALID")
        predecessor_root = predecessor_acceptance["acceptance_root"]; criterion = PREDECESSOR_CRITERION[stage]; evidence = verify_artifact_evidence(checked[criterion], criterion=criterion, expected_binding=criteria_bindings[criterion])
        require(evidence["artifact_kind"] == "STAGE_ACCEPTANCE_RECEIPT" and evidence["artifact"] == predecessor_acceptance and evidence["artifact"].get("acceptance_root") == predecessor_root, "DEPLOYMENT_PREDECESSOR_EVIDENCE_MISMATCH")
    body = {"schema": "ucl.ucm.deployment_stage_entry_packet.v4", "stage": stage, "stage_order": STAGE_ORDER[stage], "stage_contract_root": stage_contract_root, "subject_root": require_root(subject_root), "predecessor_stage": PREVIOUS_STAGE.get(stage, "GENESIS"), "predecessor_acceptance_root": predecessor_root, "criteria_evidence": checked, "criteria_bindings": deepcopy(criteria_bindings), "criteria_binding_root": root(criteria_bindings), "rollback_contract_root": require_root(rollback_contract_root), "maximum_executable_stage": EXECUTABLE_CEILING, "entry_authorized": False, "automatic_entry": False, "real_a5": False, "g0": "CLOSED", "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "entry_packet_root": root(body)}


def verify_stage_entry_packet(value: Any, *, expected_subject_root: str, expected_stage_contract_root: str, expected_predecessor_acceptance: Any, expected_predecessor_identity: dict[str, Any] | None, expected_predecessor_entry_packet_root: str | None = None, expected_predecessor_check_bindings: dict[str, Any] | None = None, expected_predecessor_stage_contract_root: str | None = None, expected_predecessor_key_root: str | None = None, expected_criteria_bindings: dict[str, Any]) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "stage", "stage_order", "stage_contract_root", "subject_root", "predecessor_stage", "predecessor_acceptance_root", "criteria_evidence", "criteria_bindings", "criteria_binding_root", "rollback_contract_root", "maximum_executable_stage", "entry_authorized", "automatic_entry", "real_a5", "g0", "standing", "authority_effect", "entry_packet_root"}, "$.stage_entry")
    body = {key: item[key] for key in item if key != "entry_packet_root"}; stage = _stage(item["stage"]); _within_ceiling(stage)
    stage_contract_root = require_root(expected_stage_contract_root)
    require(item["schema"] == "ucl.ucm.deployment_stage_entry_packet.v4" and item["stage_order"] == STAGE_ORDER[stage] and item["stage_contract_root"] == stage_contract_root and item["subject_root"] == require_root(expected_subject_root), "DEPLOYMENT_ENTRY_SCHEMA_INVALID")
    require(item["criteria_bindings"] == expected_criteria_bindings and item["criteria_binding_root"] == root(expected_criteria_bindings), "EVIDENCE_BINDING_SET_MISMATCH")
    require(item["predecessor_stage"] == PREVIOUS_STAGE.get(stage, "GENESIS"), "DEPLOYMENT_PREDECESSOR_STAGE_INVALID"); checked = _evidence_map(item["criteria_evidence"], STAGE_CRITERIA[stage], expected_criteria_bindings, stage_contract_root=stage_contract_root)
    if stage == "D0_PACKAGE_PREFLIGHT":
        require(expected_predecessor_acceptance == "GENESIS" and expected_predecessor_identity is None and item["predecessor_acceptance_root"] == "GENESIS", "DEPLOYMENT_PREDECESSOR_INVALID")
    else:
        require(type(expected_predecessor_identity) is dict, "DEPLOYMENT_PREDECESSOR_IDENTITY_REQUIRED")
        _require_contract_pinned_signer(stage_contract_root, expected_predecessor_identity, "WITNESS", expected_predecessor_key_root)
        require(expected_predecessor_entry_packet_root is not None and type(expected_predecessor_check_bindings) is dict and expected_predecessor_stage_contract_root is not None, "DEPLOYMENT_PREDECESSOR_CONTRACT_REQUIRED")
        prior = _verify_acceptance_signature(expected_predecessor_acceptance, expected_identity=expected_predecessor_identity, expected_subject_root=expected_subject_root, expected_stage=PREVIOUS_STAGE[stage], expected_entry_packet_root=expected_predecessor_entry_packet_root, expected_check_bindings=expected_predecessor_check_bindings, expected_stage_contract_root=expected_predecessor_stage_contract_root, expected_signer_key_root=expected_predecessor_key_root)
        require(prior["accepted_for_next_stage"] is True, "DEPLOYMENT_PREDECESSOR_STAGE_INVALID")
        prior_root = expected_predecessor_acceptance["acceptance_root"]; require(item["predecessor_acceptance_root"] == prior_root, "DEPLOYMENT_PREDECESSOR_MISMATCH")
        criterion = PREDECESSOR_CRITERION[stage]; evidence = verify_artifact_evidence(checked[criterion], criterion=criterion, expected_binding=expected_criteria_bindings[criterion])
        require(evidence["artifact_kind"] == "STAGE_ACCEPTANCE_RECEIPT" and evidence["artifact"] == expected_predecessor_acceptance and evidence["artifact"].get("acceptance_root") == prior_root, "DEPLOYMENT_PREDECESSOR_EVIDENCE_MISMATCH")
    require_root(item["rollback_contract_root"]); require(item["maximum_executable_stage"] == EXECUTABLE_CEILING and item["entry_authorized"] is False and item["automatic_entry"] is False, "DEPLOYMENT_SELF_AUTHORIZATION_FORBIDDEN")
    require(item["real_a5"] is False and item["g0"] == "CLOSED" and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE" and item["entry_packet_root"] == root(body), "DEPLOYMENT_ENTRY_EFFECT_FORBIDDEN")
    return deepcopy(body)


def make_stage_acceptance_receipt(provider: CustodyProvider, handle: str, *, entry_packet: dict[str, Any], stage_contract_root: str, checks: dict[str, Any], check_bindings: dict[str, Any], terminal_evidence_root: str, candidate_preimage_root: str, candidate_postimage_root: str, observed_effects: list[str], expected_signer_key_root: str | None = None, independent_review: Any | None = None, expected_qualification_root: str | None = None, expected_reviewer_identity: dict[str, Any] | None = None, expected_review_archive_root: str | None = None) -> dict[str, Any]:
    identity = provider.identity(handle); stage = _stage(entry_packet.get("stage")); _within_ceiling(stage); required_role = "REVIEWER" if stage == "D2_INDEPENDENT_REVIEW" else "WITNESS"
    stage_contract_root = require_root(stage_contract_root)
    _require_contract_pinned_signer(stage_contract_root, identity, required_role, expected_signer_key_root); require(entry_packet.get("entry_packet_root") == root({k: entry_packet[k] for k in entry_packet if k != "entry_packet_root"}) and entry_packet.get("stage_contract_root") == stage_contract_root, "DEPLOYMENT_ENTRY_ROOT_INVALID"); checked = _evidence_map(checks, STAGE_ACCEPTANCE[stage], check_bindings, stage_contract_root=stage_contract_root); review_root = None
    if stage == "D2_INDEPENDENT_REVIEW":
        require(independent_review is not None and expected_qualification_root is not None and expected_reviewer_identity is not None and expected_review_archive_root is not None, "INDEPENDENT_REVIEW_REQUIRED")
        require(identity == expected_reviewer_identity, "REVIEWER_EXTERNAL_PIN_MISMATCH")
        review_body = verify_independent_review_result(independent_review, expected_subject_root=entry_packet["subject_root"], expected_qualification_root=expected_qualification_root, expected_identity=expected_reviewer_identity)
        require(review_body["verdict"] in QUALIFYING_REVIEW_VERDICTS, "INDEPENDENT_REVIEW_NOT_QUALIFYING")
        require(review_body["evidence_archive_root"] == require_root(expected_review_archive_root), "REVIEW_ARCHIVE_EXTERNAL_PIN_MISMATCH")
        review_root = independent_review["review_root"]
        verdict = verify_artifact_evidence(checked["VERDICT_BOUND"], criterion="VERDICT_BOUND", expected_binding=check_bindings["VERDICT_BOUND"]); require(verdict["artifact_kind"] == "SIGNED_INDEPENDENT_REVIEW" and verdict["artifact"] == independent_review and verdict["artifact"].get("review_root") == review_root, "INDEPENDENT_REVIEW_EVIDENCE_MISMATCH")
    else:
        require(independent_review is None and expected_qualification_root is None and expected_reviewer_identity is None and expected_review_archive_root is None, "UNEXPECTED_INDEPENDENT_REVIEW")
    preimage = require_root(candidate_preimage_root); postimage = require_root(candidate_postimage_root); require(preimage == postimage == entry_packet["subject_root"], "DEPLOYMENT_CANDIDATE_DRIFT"); require(observed_effects == [], "DEPLOYMENT_EFFECT_OBSERVED")
    body = {"schema": "ucl.ucm.deployment_stage_acceptance.v4", "stage": stage, "stage_contract_root": stage_contract_root, "entry_packet_root": entry_packet["entry_packet_root"], "subject_root": entry_packet["subject_root"], "checks": checked, "check_bindings": deepcopy(check_bindings), "check_binding_root": root(check_bindings), "terminal_evidence_root": require_root(terminal_evidence_root), "candidate_preimage_root": preimage, "candidate_postimage_root": postimage, "observed_effects": [], "reviewer_role": identity["role"], "independent_review": deepcopy(independent_review), "independent_review_root": review_root, "accepted_for_next_stage": True, "maximum_executable_stage": EXECUTABLE_CEILING, "real_a5": False, "g0": "CLOSED", "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    signed = provider.sign(handle, ACCEPTANCE_DOMAIN, body); return {**signed, "acceptance_root": root(signed)}


def verify_stage_acceptance_receipt(value: Any, *, expected_entry_packet_root: str, expected_identity: dict[str, Any], expected_check_bindings: dict[str, Any], expected_stage_contract_root: str, expected_subject_root: str | None = None, expected_signer_key_root: str | None = None, expected_qualification_root: str | None = None, expected_reviewer_identity: dict[str, Any] | None = None, expected_review_archive_root: str | None = None) -> dict[str, Any]:
    item = exact_keys(value, {"body", "body_root", "signature", "key_root", "signature_algorithm", "acceptance_root"}, "$.acceptance"); signed = {key: item[key] for key in ("body", "body_root", "signature", "key_root", "signature_algorithm")}; body = verify_asymmetric(signed, ACCEPTANCE_DOMAIN, expected_key_root=expected_identity["key_root"], public_key_hex=expected_identity["public_key_hex"])
    exact_keys(body, {"schema", "stage", "stage_contract_root", "entry_packet_root", "subject_root", "checks", "check_bindings", "check_binding_root", "terminal_evidence_root", "candidate_preimage_root", "candidate_postimage_root", "observed_effects", "reviewer_role", "independent_review", "independent_review_root", "accepted_for_next_stage", "maximum_executable_stage", "real_a5", "g0", "standing", "authority_effect"}, "$.acceptance.body")
    stage = _stage(body["stage"]); _within_ceiling(stage); stage_contract_root = require_root(expected_stage_contract_root); require(body["schema"] == "ucl.ucm.deployment_stage_acceptance.v4" and body["stage_contract_root"] == stage_contract_root and body["entry_packet_root"] == require_root(expected_entry_packet_root), "DEPLOYMENT_ACCEPTANCE_ENTRY_MISMATCH")
    _require_contract_pinned_signer(stage_contract_root, expected_identity, "REVIEWER" if stage == "D2_INDEPENDENT_REVIEW" else "WITNESS", expected_signer_key_root)
    if expected_subject_root is not None: require(body["subject_root"] == require_root(expected_subject_root), "DEPLOYMENT_SUBJECT_MISMATCH")
    require(body["check_bindings"] == expected_check_bindings and body["check_binding_root"] == root(expected_check_bindings), "EVIDENCE_BINDING_SET_MISMATCH")
    _evidence_map(body["checks"], STAGE_ACCEPTANCE[stage], expected_check_bindings, stage_contract_root=stage_contract_root); required_role = "REVIEWER" if stage == "D2_INDEPENDENT_REVIEW" else "WITNESS"; require(expected_identity.get("role") == body["reviewer_role"] == required_role, "DEPLOYMENT_ACCEPTANCE_ROLE_INVALID")
    require((stage == "D2_INDEPENDENT_REVIEW") is (body["independent_review_root"] is not None), "INDEPENDENT_REVIEW_BINDING_INVALID")
    if body["independent_review_root"] is not None:
        require(expected_qualification_root is not None and expected_reviewer_identity is not None and expected_review_archive_root is not None, "INDEPENDENT_REVIEW_EXTERNAL_PINS_REQUIRED")
        require(expected_identity == expected_reviewer_identity, "REVIEWER_EXTERNAL_PIN_MISMATCH")
        review_body = verify_independent_review_result(body["independent_review"], expected_subject_root=body["subject_root"], expected_qualification_root=expected_qualification_root, expected_identity=expected_reviewer_identity)
        require(review_body["verdict"] == "QUALIFIED_RECOMMENDATION_ONLY" and review_body["evidence_archive_root"] == require_root(expected_review_archive_root), "INDEPENDENT_REVIEW_NOT_QUALIFYING")
        require(body["independent_review_root"] == body["independent_review"]["review_root"], "INDEPENDENT_REVIEW_BINDING_INVALID")
    else:
        require(body["independent_review"] is None and expected_qualification_root is None and expected_reviewer_identity is None and expected_review_archive_root is None, "UNEXPECTED_INDEPENDENT_REVIEW")
    require(body["candidate_preimage_root"] == body["candidate_postimage_root"] == body["subject_root"] and body["observed_effects"] == [] and body["accepted_for_next_stage"] is True, "DEPLOYMENT_ACCEPTANCE_INVALID")
    require(body["maximum_executable_stage"] == EXECUTABLE_CEILING and body["real_a5"] is False and body["g0"] == "CLOSED" and body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE" and item["acceptance_root"] == root(signed), "DEPLOYMENT_ACCEPTANCE_EFFECT_FORBIDDEN")
    return deepcopy(body)


def make_rollback_contract(stage: str, *, subject_root: str, candidate_preimage_root: str, protected_state_root: str, triggers: list[str], actions: list[str], recovery_checks: list[str]) -> dict[str, Any]:
    stage = _stage(stage); _within_ceiling(stage)
    require(type(triggers) is list and triggers and len(triggers) == len(set(triggers)) and all(type(v) is str and v for v in triggers), "ROLLBACK_TRIGGERS_INVALID")
    require(type(actions) is list and len(actions) == len(set(actions)) and set(actions) == ROLLBACK_ACTIONS, "ROLLBACK_ACTIONS_INVALID")
    require(type(recovery_checks) is list and recovery_checks and len(recovery_checks) == len(set(recovery_checks)) and all(type(v) is str and v for v in recovery_checks), "ROLLBACK_CHECKS_INVALID")
    body = {"schema": "ucl.ucm.deployment_rollback_contract.v2", "stage": stage, "subject_root": require_root(subject_root), "candidate_preimage_root": require_root(candidate_preimage_root), "protected_state_root": require_root(protected_state_root), "triggers": sorted(triggers), "actions": sorted(actions), "recovery_checks": sorted(recovery_checks), "automatic_production_restore": False, "maximum_executable_stage": EXECUTABLE_CEILING, "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "rollback_contract_root": root(body)}


def make_rollback_receipt(provider: CustodyProvider, handle: str, *, contract: dict[str, Any], trigger: str, completed_actions: list[str], restored_candidate_root: str, restored_state_root: str, terminal_evidence_root: str) -> dict[str, Any]:
    identity = provider.identity(handle); require(identity["role"] == "WITNESS", "ROLLBACK_RECEIPT_ROLE_INVALID")
    require(contract.get("rollback_contract_root") == root({k: contract[k] for k in contract if k != "rollback_contract_root"}), "ROLLBACK_CONTRACT_ROOT_INVALID")
    require(trigger in contract["triggers"], "ROLLBACK_TRIGGER_INVALID")
    require(completed_actions == contract["actions"] and len(completed_actions) == len(set(completed_actions)), "ROLLBACK_ACTIONS_INCOMPLETE")
    require(restored_candidate_root == contract["candidate_preimage_root"] and restored_state_root == contract["protected_state_root"], "ROLLBACK_RESTORATION_INVALID")
    body = {"schema": "ucl.ucm.deployment_rollback_receipt.v3", "rollback_contract_root": contract["rollback_contract_root"], "trigger": trigger, "completed_actions": completed_actions, "restored_candidate_root": require_root(restored_candidate_root), "restored_state_root": require_root(restored_state_root), "terminal_evidence_root": require_root(terminal_evidence_root), "actual_rehearsal": True, "production_effect": False, "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    signed = provider.sign(handle, ROLLBACK_DOMAIN, body); return {**signed, "rollback_receipt_root": root(signed)}


def verify_rollback_receipt(value: Any, *, contract: dict[str, Any], expected_identity: dict[str, Any], expected_terminal_evidence_root: str | None = None) -> dict[str, Any]:
    item = exact_keys(value, {"body", "body_root", "signature", "key_root", "signature_algorithm", "rollback_receipt_root"}, "$.rollback_receipt"); signed = {key: item[key] for key in ("body", "body_root", "signature", "key_root", "signature_algorithm")}; body = verify_asymmetric(signed, ROLLBACK_DOMAIN, expected_key_root=expected_identity["key_root"], public_key_hex=expected_identity["public_key_hex"])
    exact_keys(body, {"schema", "rollback_contract_root", "trigger", "completed_actions", "restored_candidate_root", "restored_state_root", "terminal_evidence_root", "actual_rehearsal", "production_effect", "standing", "authority_effect"}, "$.rollback_receipt.body")
    require(expected_identity.get("role") == "WITNESS", "ROLLBACK_RECEIPT_ROLE_INVALID")
    require(body["schema"] == "ucl.ucm.deployment_rollback_receipt.v3" and body["rollback_contract_root"] == contract["rollback_contract_root"] and body["trigger"] in contract["triggers"], "ROLLBACK_CONTRACT_MISMATCH")
    require(body["completed_actions"] == contract["actions"] and len(body["completed_actions"]) == len(set(body["completed_actions"])), "ROLLBACK_RECEIPT_INVALID")
    require(body["restored_candidate_root"] == contract["candidate_preimage_root"] and body["restored_state_root"] == contract["protected_state_root"], "ROLLBACK_RESTORATION_INVALID")
    require(expected_terminal_evidence_root is not None, "ROLLBACK_TERMINAL_PIN_REQUIRED")
    require(body["terminal_evidence_root"] == require_root(expected_terminal_evidence_root), "ROLLBACK_TERMINAL_EVIDENCE_MISMATCH")
    require(body["actual_rehearsal"] is True and body["production_effect"] is False and body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE" and item["rollback_receipt_root"] == root(signed), "ROLLBACK_EFFECT_FORBIDDEN")
    return deepcopy(body)


def make_portability_profile(*, profile_id: str, os_family: str, architecture: str, python_abi: str, filesystem_case_sensitive: bool, capabilities: list[str]) -> dict[str, Any]:
    _nonempty_text(profile_id, "PORTABILITY_PROFILE_ID_INVALID"); require(os_family in {"WINDOWS", "POSIX"}, "PORTABILITY_OS_INVALID"); _nonempty_text(architecture, "PORTABILITY_ARCH_INVALID"); _nonempty_text(python_abi, "PORTABILITY_PYTHON_ABI_INVALID")
    require(type(filesystem_case_sensitive) is bool and type(capabilities) is list and set(capabilities).issubset(PORTABILITY_CAPABILITIES), "PORTABILITY_CAPABILITY_INVALID")
    body = {"schema": "ucl.ucm.portability_profile.v2", "profile_id": profile_id, "os_family": os_family, "architecture": architecture, "python_abi": python_abi, "filesystem_case_sensitive": filesystem_case_sensitive, "capabilities": sorted(set(capabilities)), "host_identity_bound": False, "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "profile_root": root(body)}


def evaluate_portability(profile: Any, *, required_capabilities: list[str], allowed_os: list[str]) -> dict[str, Any]:
    body = {key: profile[key] for key in profile if key != "profile_root"}; require(profile.get("schema") == "ucl.ucm.portability_profile.v2" and profile.get("profile_root") == root(body), "PORTABILITY_PROFILE_ROOT_INVALID")
    require(profile["os_family"] in allowed_os and type(required_capabilities) is list and set(required_capabilities).issubset(PORTABILITY_CAPABILITIES), "PORTABILITY_REQUIREMENT_INVALID")
    missing = sorted(set(required_capabilities) - set(profile["capabilities"])); require(not missing, "PORTABILITY_CAPABILITY_MISSING")
    result = {"schema": "ucl.ucm.portability_evaluation.v2", "profile_root": profile["profile_root"], "required_capabilities": sorted(set(required_capabilities)), "missing": [], "status": "PASS", "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**result, "evaluation_root": root(result)}


def make_protected_execution_plan(*, subject_root: str, envelope_root: str, profile_root: str, runner_path: str, required_paths: list[str], allowed_write_paths: list[str]) -> dict[str, Any]:
    runner = _safe_relpath(runner_path, "$.runner_path"); reads = sorted({_safe_relpath(path, "$.required_paths") for path in required_paths}); writes = sorted({_safe_relpath(path, "$.allowed_write_paths") for path in allowed_write_paths})
    require(runner in reads, "PROTECTED_RUNNER_NOT_DECLARED"); require(writes and all(path.startswith("output/") for path in writes), "PROTECTED_WRITE_SCOPE_INVALID")
    body = {"schema": "ucl.ucm.protected_execution_plan.v2", "subject_root": require_root(subject_root), "envelope_root": require_root(envelope_root), "profile_root": require_root(profile_root), "runner_path": runner, "required_paths": reads, "allowed_write_paths": writes, "denied_effects": ["ACCOUNT_CHANGE", "ACL_CHANGE", "FIREWALL_CHANGE", "NETWORK", "PERSISTENT_HOST_WRITE", "REGISTRY_CHANGE", "SCHEDULED_TASK", "SUBPROCESS"], "maximum_invocations": 1, "maximum_retries": 0, "terminal_capture": ["EXIT_CODE", "STDERR", "STDOUT", "TERMINAL_RECEIPT"], "disposable_only": True, "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "plan_root": root(body)}


def verify_protected_execution_plan(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "subject_root", "envelope_root", "profile_root", "runner_path", "required_paths", "allowed_write_paths", "denied_effects", "maximum_invocations", "maximum_retries", "terminal_capture", "disposable_only", "standing", "authority_effect", "plan_root"}, "$.plan"); body = {key: item[key] for key in item if key != "plan_root"}
    require(item["schema"] == "ucl.ucm.protected_execution_plan.v2" and item["plan_root"] == root(body), "PROTECTED_PLAN_ROOT_INVALID"); require_root(item["subject_root"]); require_root(item["envelope_root"]); require_root(item["profile_root"])
    runner = _safe_relpath(item["runner_path"]); reads = sorted({_safe_relpath(path) for path in item["required_paths"]}); writes = sorted({_safe_relpath(path) for path in item["allowed_write_paths"]})
    require(item["required_paths"] == reads and runner in reads and item["allowed_write_paths"] == writes and writes and all(path.startswith("output/") for path in writes), "PROTECTED_PATH_SET_INVALID")
    require(item["denied_effects"] == ["ACCOUNT_CHANGE", "ACL_CHANGE", "FIREWALL_CHANGE", "NETWORK", "PERSISTENT_HOST_WRITE", "REGISTRY_CHANGE", "SCHEDULED_TASK", "SUBPROCESS"], "PROTECTED_DENIED_EFFECT_SET_INVALID")
    require(type(item["maximum_invocations"]) is int and item["maximum_invocations"] == 1 and type(item["maximum_retries"]) is int and item["maximum_retries"] == 0, "PROTECTED_EXECUTION_LIMIT_INVALID")
    require(item["terminal_capture"] == ["EXIT_CODE", "STDERR", "STDOUT", "TERMINAL_RECEIPT"] and item["disposable_only"] is True and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "PROTECTED_TERMINAL_CONTRACT_INVALID")
    return deepcopy(body)


def record_protected_execution(provider: CustodyProvider, handle: str, plan: Any, *, guard_result: dict[str, Any], expected_guard_result_root: str, candidate_preimage_root: str, candidate_postimage_root: str, writes: list[str], terminal_evidence_root: str) -> dict[str, Any]:
    verify_protected_execution_plan(plan); identity = provider.identity(handle); require(identity["role"] == "WITNESS", "PROTECTED_RECEIPT_ROLE_INVALID")
    exact_keys(guard_result, {"schema", "status", "code", "mode", "subject_sha256", "candidate_root", "invocation_count", "retry_count", "audit_observations", "guard_kind", "os_sandbox_claimed", "persistent_host_modified", "standing", "authority_effect"}, "$.guard_result")
    require(guard_result["schema"] == "ucl.ucm.protected_execution_guard_result.v4" and guard_result["status"] == "PASS" and guard_result["code"] == "PROTECTED_EXECUTION_COMPLETE" and guard_result["mode"] == "BENIGN" and guard_result["candidate_root"] == plan["subject_root"] and guard_result["invocation_count"] == 1 and guard_result["retry_count"] == 0 and guard_result["audit_observations"] == [] and guard_result["persistent_host_modified"] is False, "PROTECTED_GUARD_RESULT_INVALID")
    require(root(guard_result) == require_root(expected_guard_result_root), "PROTECTED_GUARD_EXTERNAL_PIN_MISMATCH")
    preimage = require_root(candidate_preimage_root); postimage = require_root(candidate_postimage_root); require(preimage == postimage == plan["subject_root"], "PROTECTED_CANDIDATE_DRIFT")
    checked_writes = sorted({_safe_relpath(path, "$.writes") for path in writes}); require(set(checked_writes).issubset(set(plan["allowed_write_paths"])), "PROTECTED_WRITE_OUTSIDE_SCOPE")
    body = {"schema": "ucl.ucm.protected_execution_receipt.v3", "plan_root": plan["plan_root"], "subject_root": plan["subject_root"], "guard_result": deepcopy(guard_result), "guard_result_root": root(guard_result), "candidate_preimage_root": preimage, "candidate_postimage_root": postimage, "writes": checked_writes, "terminal_evidence_root": require_root(terminal_evidence_root), "persistent_host_modified": False, "network_calls": 0, "accounts_created": 0, "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    signed = provider.sign(handle, EXECUTION_DOMAIN, body); return {**signed, "execution_receipt_root": root(signed)}


def verify_protected_execution_receipt(value: Any, *, plan: Any, expected_identity: dict[str, Any], expected_guard_result_root: str) -> dict[str, Any]:
    verify_protected_execution_plan(plan); require(expected_identity.get("role") == "WITNESS", "PROTECTED_RECEIPT_ROLE_INVALID")
    item = exact_keys(value, {"body", "body_root", "signature", "key_root", "signature_algorithm", "execution_receipt_root"}, "$.receipt"); signed = {key: item[key] for key in ("body", "body_root", "signature", "key_root", "signature_algorithm")}; body = verify_asymmetric(signed, EXECUTION_DOMAIN, expected_key_root=expected_identity["key_root"], public_key_hex=expected_identity["public_key_hex"])
    exact_keys(body, {"schema", "plan_root", "subject_root", "guard_result", "guard_result_root", "candidate_preimage_root", "candidate_postimage_root", "writes", "terminal_evidence_root", "persistent_host_modified", "network_calls", "accounts_created", "standing", "authority_effect"}, "$.receipt.body")
    require(body["schema"] == "ucl.ucm.protected_execution_receipt.v3" and body["plan_root"] == plan["plan_root"] and body["subject_root"] == plan["subject_root"], "PROTECTED_RECEIPT_PLAN_MISMATCH")
    require(body["guard_result_root"] == root(body["guard_result"]) == require_root(expected_guard_result_root) and body["guard_result"]["schema"] == "ucl.ucm.protected_execution_guard_result.v4" and body["guard_result"]["status"] == "PASS" and body["guard_result"]["code"] == "PROTECTED_EXECUTION_COMPLETE" and body["guard_result"]["mode"] == "BENIGN" and body["guard_result"]["audit_observations"] == [] and body["guard_result"]["candidate_root"] == plan["subject_root"], "PROTECTED_GUARD_RESULT_INVALID")
    require(body["candidate_preimage_root"] == body["candidate_postimage_root"] == plan["subject_root"] and set(body["writes"]).issubset(set(plan["allowed_write_paths"])), "PROTECTED_RECEIPT_INVALID")
    require(body["persistent_host_modified"] is False and body["network_calls"] == 0 and body["accounts_created"] == 0 and body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE" and item["execution_receipt_root"] == root(signed), "PROTECTED_EFFECT_OBSERVED")
    return deepcopy(body)


def make_ceremony_contract(*, subject_root: str, governor_source_root: str, host_scope_root: str) -> dict[str, Any]:
    body = {"schema": "ucl.ucm.identity_ceremony_contract.v2", "subject_root": require_root(subject_root), "governor_source_root": require_root(governor_source_root), "host_scope_root": require_root(host_scope_root), "required_roles": list(CEREMONY_ROLES), "role_addresses": ROLE_ADDRESSES, "distinct_public_keys": True, "distinct_os_principals": True, "proof_of_possession_required": True, "private_material_must_remain_external": True, "revocation_required": True, "recovery_requires_new_key": True, "decision_required": True, "automatic_seating": False, "requested_stage": "D3_REAL_IDENTITY_SEATING", "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "ceremony_contract_root": root(body)}


def verify_ceremony_contract(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "subject_root", "governor_source_root", "host_scope_root", "required_roles", "role_addresses", "distinct_public_keys", "distinct_os_principals", "proof_of_possession_required", "private_material_must_remain_external", "revocation_required", "recovery_requires_new_key", "decision_required", "automatic_seating", "requested_stage", "standing", "authority_effect", "ceremony_contract_root"}, "$.ceremony_contract"); body = {key: item[key] for key in item if key != "ceremony_contract_root"}
    require(item["schema"] == "ucl.ucm.identity_ceremony_contract.v2" and item["ceremony_contract_root"] == root(body), "CEREMONY_CONTRACT_ROOT_INVALID")
    require(item["required_roles"] == list(CEREMONY_ROLES) and item["role_addresses"] == ROLE_ADDRESSES, "CEREMONY_ROLE_SET_INVALID")
    require(all(item[key] is True for key in ("distinct_public_keys", "distinct_os_principals", "proof_of_possession_required", "private_material_must_remain_external", "revocation_required", "recovery_requires_new_key", "decision_required")), "CEREMONY_CONTRACT_INCOMPLETE")
    require(item["automatic_seating"] is False and item["requested_stage"] == "D3_REAL_IDENTITY_SEATING" and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "CEREMONY_SELF_SEATING_FORBIDDEN")
    return deepcopy(body)


def _principal(value: Any) -> str:
    return unicodedata.normalize("NFKC", _nonempty_text(value, "CEREMONY_PRINCIPAL_INVALID")).casefold()


def ceremony_challenge(contract_root: str, role: str) -> str:
    require(role in CEREMONY_ROLES, "CEREMONY_ROLE_INVALID")
    return root({"domain": "UCL_UCM_CEREMONY_CHALLENGE_V2", "ceremony_contract_root": require_root(contract_root), "role": role})


def make_ceremony_submission(provider: CustodyProvider, handle: str, *, ceremony_contract_root: str, role_address: str, os_principal_id: str, os_attestation_root: str, custody_attestation_root: str, challenge_root: str) -> dict[str, Any]:
    identity = provider.identity(handle); role = identity["role"]; require(role in CEREMONY_ROLES, "CEREMONY_ROLE_INVALID")
    require(role_address == ROLE_ADDRESSES[role], "CEREMONY_ROLE_ADDRESS_MISMATCH"); require(challenge_root == ceremony_challenge(ceremony_contract_root, role), "CEREMONY_CHALLENGE_MISMATCH")
    body = {"schema": "ucl.ucm.identity_ceremony_submission.v2", "ceremony_contract_root": require_root(ceremony_contract_root), "role": role, "role_address": role_address, "public_identity": identity, "os_principal_id": os_principal_id, "normalized_os_principal_id": _principal(os_principal_id), "os_attestation_root": require_root(os_attestation_root), "custody_attestation_root": require_root(custody_attestation_root), "challenge_root": require_root(challenge_root), "private_material_disclosed": False, "identity_seated": False, "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return provider.sign(handle, CEREMONY_DOMAIN, body)


def verify_ceremony_submission(value: Any, *, ceremony_contract_root: str) -> dict[str, Any]:
    item = exact_keys(value, {"body", "body_root", "signature", "key_root", "signature_algorithm"}, "$.submission"); body0 = item["body"]
    exact_keys(body0, {"schema", "ceremony_contract_root", "role", "role_address", "public_identity", "os_principal_id", "normalized_os_principal_id", "os_attestation_root", "custody_attestation_root", "challenge_root", "private_material_disclosed", "identity_seated", "standing", "authority_effect"}, "$.submission.body")
    identity = body0["public_identity"]; body = verify_asymmetric(item, CEREMONY_DOMAIN, expected_key_root=identity["key_root"], public_key_hex=identity["public_key_hex"]); role = body["role"]
    require(role in CEREMONY_ROLES and identity["role"] == role, "CEREMONY_ROLE_MISMATCH"); require(body["ceremony_contract_root"] == require_root(ceremony_contract_root), "CEREMONY_CONTRACT_MISMATCH")
    require(body["role_address"] == ROLE_ADDRESSES[role], "CEREMONY_ROLE_ADDRESS_MISMATCH"); require(body["normalized_os_principal_id"] == _principal(body["os_principal_id"]), "CEREMONY_PRINCIPAL_NORMALIZATION_INVALID"); require(body["challenge_root"] == ceremony_challenge(ceremony_contract_root, role), "CEREMONY_CHALLENGE_MISMATCH")
    require(body["private_material_disclosed"] is False and body["identity_seated"] is False and body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE", "CEREMONY_EFFECT_FORBIDDEN")
    return deepcopy(body)


def compile_ceremony_packet(contract: Any, submissions: list[dict[str, Any]]) -> dict[str, Any]:
    verify_ceremony_contract(contract); require(type(submissions) is list and len(submissions) == len(CEREMONY_ROLES), "CEREMONY_SUBMISSION_SET_INVALID")
    bodies = [verify_ceremony_submission(item, ceremony_contract_root=contract["ceremony_contract_root"]) for item in submissions]; by_role = {item["role"]: item for item in bodies}; require(set(by_role) == set(CEREMONY_ROLES), "CEREMONY_SUBMISSION_SET_INVALID")
    keys = [by_role[r]["public_identity"]["key_root"] for r in CEREMONY_ROLES]; principals = [by_role[r]["normalized_os_principal_id"] for r in CEREMONY_ROLES]; challenges = [by_role[r]["challenge_root"] for r in CEREMONY_ROLES]
    require(len(set(keys)) == len(keys), "CEREMONY_KEY_COLLISION"); require(len(set(principals)) == len(principals), "CEREMONY_PRINCIPAL_COLLISION"); require(len(set(challenges)) == len(challenges), "CEREMONY_CHALLENGE_COLLISION")
    body = {"schema": "ucl.ucm.identity_ceremony_packet.v2", "ceremony_contract_root": contract["ceremony_contract_root"], "submission_roots": [root(submissions[CEREMONY_ROLES.index(role)]) for role in CEREMONY_ROLES], "roles_complete": True, "keys_distinct": True, "principals_distinct": True, "challenges_distinct": True, "identity_seated": False, "decision_required": True, "decision_applied": False, "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "ceremony_packet_root": root(body)}


def compile_review_repair_plan(review: Any, *, expected_subject_root: str, expected_qualification_root: str, expected_reviewer_identity: dict[str, Any]) -> dict[str, Any]:
    body = verify_independent_review_result(review, expected_subject_root=expected_subject_root, expected_qualification_root=expected_qualification_root, expected_identity=expected_reviewer_identity); groups: dict[str, list[str]] = {}; counts = {s: 0 for s in ("HIGH", "MED", "LOW", "INFO")}
    for finding in body["findings"]:
        exact_keys(finding, {"finding_id", "severity", "invariant", "affected_paths", "evidence_root", "required_property", "status"}, "$.finding"); require(finding["severity"] in counts and finding["status"] == "OPEN", "REVIEW_FINDING_INVALID"); groups.setdefault(finding["invariant"], []).append(finding["finding_id"]); counts[finding["severity"]] += 1
    grouped = [{"invariant": name, "finding_ids": sorted(set(ids))} for name, ids in sorted(groups.items())]
    result = {"schema": "ucl.ucm.consolidated_repair_plan.v2", "review_root": review["review_root"], "subject_root": body["subject_root"], "qualification_root": body["qualification_root"], "review_verdict": body["verdict"], "invariant_groups": grouped, "finding_count": len(body["findings"]), "severity_counts": counts, "selected_lane": "QUALIFICATION" if body["findings"] else "FAST", "generic_mutation_required": bool(body["findings"]), "full_qualification_required": counts["HIGH"] + counts["MED"] > 0, "candidate_changes_applied": False, "automatic_disposition": False, "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**result, "repair_plan_root": root(result)}


def verify_repair_plan(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "review_root", "subject_root", "qualification_root", "review_verdict", "invariant_groups", "finding_count", "severity_counts", "selected_lane", "generic_mutation_required", "full_qualification_required", "candidate_changes_applied", "automatic_disposition", "standing", "authority_effect", "repair_plan_root"}, "$.repair_plan"); body = {key: item[key] for key in item if key != "repair_plan_root"}
    require(item["schema"] == "ucl.ucm.consolidated_repair_plan.v2" and item["repair_plan_root"] == root(body), "REPAIR_PLAN_ROOT_INVALID"); require_root(item["review_root"]); require_root(item["subject_root"]); require_root(item["qualification_root"]); require(item["review_verdict"] in REVIEW_VERDICTS, "REVIEW_VERDICT_INVALID")
    ids = [fid for group in item["invariant_groups"] for fid in group["finding_ids"]]; require(len(ids) == len(set(ids)) == item["finding_count"], "REPAIR_PLAN_FINDING_COUNT_INVALID"); counts = exact_keys(item["severity_counts"], {"HIGH", "MED", "LOW", "INFO"}, "$.severity_counts"); require(all(type(v) is int and type(v) is not bool and v >= 0 for v in counts.values()) and sum(counts.values()) == item["finding_count"], "REPAIR_PLAN_SEVERITY_COUNTS_INVALID")
    require(item["selected_lane"] == ("QUALIFICATION" if ids else "FAST") and item["generic_mutation_required"] is bool(ids) and item["full_qualification_required"] is (counts["HIGH"] + counts["MED"] > 0), "REPAIR_PLAN_POLICY_INVALID"); require(item["candidate_changes_applied"] is False and item["automatic_disposition"] is False and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "REPAIR_PLAN_EFFECT_FORBIDDEN")
    return deepcopy(body)


def complete_repair_plan(plan: Any, *, regression_roots: dict[str, str], qualification_root: str) -> dict[str, Any]:
    verify_repair_plan(plan); expected = sorted(fid for group in plan["invariant_groups"] for fid in group["finding_ids"]); checked = _root_map(regression_roots, tuple(expected), "$.regression_roots")
    body = {"schema": "ucl.ucm.consolidated_repair_result.v2", "repair_plan_root": plan["repair_plan_root"], "subject_root": plan["subject_root"], "regression_roots": checked, "qualification_root": require_root(qualification_root), "all_findings_covered": True, "disposition_proposed": True, "disposition_applied": False, "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "repair_result_root": root(body)}


DECISION_PREREQUISITES = {"GOVERNOR_DISPOSITION": ("INDEPENDENT_REVIEW", "SUBJECT_PIN", "CLAIM_CEILING"), "REAL_A5_BINDING": ("GOVERNOR_DISPOSITION", "IDENTITY_CEREMONY", "A5_EVIDENCE"), "G0_OPENING": ("GOVERNOR_DISPOSITION", "REAL_A5_BINDING", "G0_ENTRY_COURT"), "INSTALLATION": ("D3_ACCEPTANCE", "HOST_CHANGE_AUTHORITY", "ROLLBACK_PROOF"), "RELEASE": ("G0_OPENING", "STANDING_DECISION", "RELEASE_COURT"), "PRODUCTION_ACTIVATION": ("RELEASE", "PRODUCTION_ROUTE_AUTHORITY", "OPERATIONS_ACCEPTANCE")}


def prepare_unbound_decision_proposal(kind: str, *, subject_root: str, evidence_roots: dict[str, str]) -> dict[str, Any]:
    require(kind in DECISION_PREREQUISITES, "DECISION_KIND_INVALID"); checked = _root_map(evidence_roots, DECISION_PREREQUISITES[kind], "$.evidence_roots")
    body = {"schema": "ucl.ucm.unbound_authority_proposal.v2", "kind": kind, "subject_root": require_root(subject_root), "evidence_roots": checked, "proposal_only": True, "decision_required": True, "decision_applied": False, "identity_seated": False, "installed": False, "released": False, "production_active": False, "real_a5": False, "g0": "CLOSED", "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "proposal_root": root(body)}


def verify_unbound_decision_proposal(value: Any, *, expected_subject_root: str) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "kind", "subject_root", "evidence_roots", "proposal_only", "decision_required", "decision_applied", "identity_seated", "installed", "released", "production_active", "real_a5", "g0", "standing", "authority_effect", "proposal_root"}, "$.proposal"); body = {key: item[key] for key in item if key != "proposal_root"}
    require(item["schema"] == "ucl.ucm.unbound_authority_proposal.v2" and item["proposal_root"] == root(body) and item["kind"] in DECISION_PREREQUISITES and item["subject_root"] == require_root(expected_subject_root), "DECISION_PROPOSAL_SUBJECT_INVALID"); _root_map(item["evidence_roots"], DECISION_PREREQUISITES[item["kind"]], "$.evidence_roots")
    require(item["proposal_only"] is True and item["decision_required"] is True and item["decision_applied"] is False and all(item[k] is False for k in ("identity_seated", "installed", "released", "production_active", "real_a5")) and item["g0"] == "CLOSED" and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "DECISION_PROPOSAL_EFFECT_FORBIDDEN")
    return deepcopy(body)


def make_blocked_future_stage_plan(stage: str, *, subject_root: str, blocking_acceptance_root: str | None) -> dict[str, Any]:
    stage = _stage(stage); require(STAGE_ORDER[stage] > STAGE_ORDER[EXECUTABLE_CEILING], "FUTURE_STAGE_NOT_ABOVE_CEILING")
    if blocking_acceptance_root is not None: require_root(blocking_acceptance_root)
    body = {"schema": "ucl.ucm.blocked_future_stage_plan.v1", "stage": stage, "subject_root": require_root(subject_root), "entry_criteria": list(STAGE_CRITERIA[stage]), "acceptance_checks": list(STAGE_ACCEPTANCE[stage]), "blocking_acceptance_root": blocking_acceptance_root, "status": "BLOCKED_AWAITING_D2_REVIEW" if stage == "D3_REAL_IDENTITY_SEATING" else "BLOCKED_BY_PREDECESSOR", "executable": False, "automatic_entry": False, "real_a5": False, "g0": "CLOSED", "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "plan_root": root(body)}


def reject_secret_shaped_keys(value: Any, path: str = "$") -> None:
    if type(value) is dict:
        for key, item in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", key.casefold()); require(normalized not in SECRET_KEYS, "AGENT_SECRET_FIELD_FORBIDDEN", f"{path}.{key}"); reject_secret_shaped_keys(item, f"{path}.{key}")
    elif type(value) is list:
        for index, item in enumerate(value): reject_secret_shaped_keys(item, f"{path}[{index}]")
    elif type(value) is str:
        leaf = re.sub(r"[^a-z0-9]", "", path.rsplit(".", 1)[-1].casefold())
        parent = re.sub(r"[^a-z0-9]", "", path.rsplit(".", 2)[-2].casefold()) if "." in path else ""
        public_material = leaf.endswith(("root", "sha256", "hash", "signature", "publickeyhex")) or leaf in {"bodyroot", "keyroot"} or parent.endswith("roots")
        secret_hex = re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None and not public_material
        secret_token = value.count(".") == 2 and all(re.fullmatch(r"[A-Za-z0-9_-]+", part or "") for part in value.split("."))
        require(not secret_hex and not secret_token, "AGENT_SECRET_VALUE_FORBIDDEN", path)


AGENT_PAYLOAD_KEYS = {"ORIENT_READINESS": set(), "DESCRIBE_STAGE": {"stage"}, "PREFLIGHT_STAGE": {"stage"}, "PREPARE_CEREMONY": {"subject_root", "governor_source_root", "host_scope_root"}, "VALIDATE_CEREMONY_PACKET": {"contract", "submissions"}, "PREPARE_PROTECTED_EXECUTION": {"subject_root", "envelope_root", "profile_root", "runner_path", "required_paths", "allowed_write_paths"}, "VALIDATE_EXECUTION_RECEIPT": {"receipt", "plan", "expected_identity", "expected_guard_result_root"}, "PREPARE_ROLLBACK": {"stage", "subject_root", "candidate_preimage_root", "protected_state_root", "triggers", "actions", "recovery_checks"}, "VALIDATE_ROLLBACK_RECEIPT": {"receipt", "contract", "expected_identity"}, "INGEST_REVIEW": {"review", "expected_subject_root", "expected_qualification_root", "expected_reviewer_identity"}, "PLAN_REPAIR_BATCH": {"review", "expected_subject_root", "expected_qualification_root", "expected_reviewer_identity"}, "DESCRIBE_AUTHORITY_CEILING": set()}
for _surface in ("PREPARE_GOVERNOR_DISPOSITION", "PREPARE_A5_PROPOSAL", "PREPARE_G0_PROPOSAL", "PREPARE_INSTALL_PROPOSAL", "PREPARE_RELEASE_PROPOSAL", "PREPARE_PRODUCTION_PROPOSAL"): AGENT_PAYLOAD_KEYS[_surface] = {"subject_root", "evidence_roots"}


class DeploymentReadinessAgent:
    SURFACES = set(AGENT_PAYLOAD_KEYS)

    def __init__(self, *, expected_subject_root: str | None = None, expected_qualification_root: str | None = None, expected_reviewer_identity: dict[str, Any] | None = None) -> None:
        self.expected_subject_root = require_root(expected_subject_root) if expected_subject_root is not None else None; self.expected_qualification_root = require_root(expected_qualification_root) if expected_qualification_root is not None else None; self.expected_reviewer_identity = deepcopy(expected_reviewer_identity)

    def request(self, surface: str, payload: Any) -> dict[str, Any]:
        require(surface in self.SURFACES, "READINESS_AGENT_SURFACE_UNKNOWN"); require(type(payload) is dict, "READINESS_AGENT_PAYLOAD_INVALID"); exact_keys(payload, AGENT_PAYLOAD_KEYS[surface], "$.payload"); reject_secret_shaped_keys(payload)
        if surface == "ORIENT_READINESS": result = {"subsystems": ["PORTABILITY", "PROTECTED_EXECUTION", "IDENTITY_CEREMONY", "STAGED_ACCEPTANCE", "ROLLBACK_RECOVERY", "REVIEW_REPAIR", "AUTHORITY_PROPOSALS", "PACKAGING"], "maximum_executable_stage": EXECUTABLE_CEILING, "next_safe_action": "DESCRIBE_STAGE"}
        elif surface in {"DESCRIBE_STAGE", "PREFLIGHT_STAGE"}: result = stage_specification(payload["stage"])
        elif surface == "PREPARE_CEREMONY": result = make_ceremony_contract(**payload)
        elif surface == "VALIDATE_CEREMONY_PACKET": result = compile_ceremony_packet(payload["contract"], payload["submissions"])
        elif surface == "PREPARE_PROTECTED_EXECUTION": result = make_protected_execution_plan(**payload)
        elif surface == "VALIDATE_EXECUTION_RECEIPT": result = verify_protected_execution_receipt(payload["receipt"], plan=payload["plan"], expected_identity=payload["expected_identity"], expected_guard_result_root=payload["expected_guard_result_root"])
        elif surface == "PREPARE_ROLLBACK": result = make_rollback_contract(**payload)
        elif surface == "VALIDATE_ROLLBACK_RECEIPT": result = verify_rollback_receipt(payload["receipt"], contract=payload["contract"], expected_identity=payload["expected_identity"])
        elif surface in {"INGEST_REVIEW", "PLAN_REPAIR_BATCH"}:
            require(self.expected_subject_root is not None and self.expected_qualification_root is not None and self.expected_reviewer_identity is not None, "READINESS_AGENT_REVIEW_PINS_REQUIRED"); require(payload["expected_subject_root"] == self.expected_subject_root and payload["expected_qualification_root"] == self.expected_qualification_root and payload["expected_reviewer_identity"] == self.expected_reviewer_identity, "READINESS_AGENT_REVIEW_PIN_MISMATCH")
            result = compile_review_repair_plan(payload["review"], expected_subject_root=self.expected_subject_root, expected_qualification_root=self.expected_qualification_root, expected_reviewer_identity=self.expected_reviewer_identity)
        elif surface == "DESCRIBE_AUTHORITY_CEILING": result = {"maximum_executable_stage": EXECUTABLE_CEILING, "excluded": ["D3_REAL_IDENTITY_SEATING", "D4_PROTECTED_INSTALLATION", "D5_PRODUCTION_ACTIVATION", "REAL_A5", "G0", "ADMISSION", "RELEASE", "PUBLICATION"], "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
        else:
            kind = {"PREPARE_GOVERNOR_DISPOSITION": "GOVERNOR_DISPOSITION", "PREPARE_A5_PROPOSAL": "REAL_A5_BINDING", "PREPARE_G0_PROPOSAL": "G0_OPENING", "PREPARE_INSTALL_PROPOSAL": "INSTALLATION", "PREPARE_RELEASE_PROPOSAL": "RELEASE", "PREPARE_PRODUCTION_PROPOSAL": "PRODUCTION_ACTIVATION"}[surface]
            if self.expected_subject_root is not None: require(payload["subject_root"] == self.expected_subject_root, "READINESS_AGENT_SUBJECT_MISMATCH")
            result = prepare_unbound_decision_proposal(kind, **payload)
        envelope = {"schema": "ucl.ucm.deployment_readiness_agent_result.v2", "surface": surface, "result": result, "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
        return {**envelope, "result_root": root(envelope)}

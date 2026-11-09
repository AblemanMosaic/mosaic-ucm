"""Stable public-boundary policies and pure governance receipts."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from uclop.canonical import canonical_bytes, exact_keys, require, require_root, root

from .system import BOUNDARY, VERSION, capability_registry


EXIT_CODES = {
    "SUCCESS": 0,
    "TYPED_REFUSAL": 3,
    "USAGE_ERROR": 64,
    "UNSUPPORTED_SURFACE": 69,
    "INTERNAL_FAULT": 70,
    "CUSTODY_FAILURE": 74,
}

SUPPORTED_ENVIRONMENT_VARIABLES = {
    "UCM_OUTPUT_MODE": {"values": ["JSON", "PRETTY"], "default": "JSON"},
    "UCM_STRICT_ENV": {"values": ["0", "1"], "default": "0"},
}


def abi_stability_table() -> dict[str, Any]:
    registry = capability_registry()
    rows = []
    for surface in registry["surfaces"]:
        rows.append({
            "surface": surface["name"],
            "request_schema": surface["request_schema"],
            "result_schema": surface["result_schema"],
            "stability": "FROZEN_WITHIN_V0_1",
            "additive_result_fields": "REQUIRE_NEW_SCHEMA",
            "deprecation": "ONE_PUBLISHED_SUCCESSOR_AND_TYPED_POINTER",
        })
    body = {
        "schema": "mosaic.ucm.abi-stability-table.v0.1",
        "ucm_version": VERSION,
        "capability_registry_root": registry["root"],
        "surfaces": rows,
        "rules": [
            "EXISTING_SCHEMA_MEANING_DOES_NOT_CHANGE",
            "NEW_FIELDS_REQUIRE_A_NEW_RESULT_SCHEMA",
            "NEW_SURFACES_START_EXPERIMENTAL_AND_NON_GRANTING",
            "DEPRECATED_SURFACES_REFUSE_WITH_CURRENT_SURFACE_POINTER",
            "REPAIR_DELTAS_MAY_FIX_IMPLEMENTATION_WITHOUT_BROADENING_AUTHORITY",
        ],
        "exit_codes": deepcopy(EXIT_CODES),
        **BOUNDARY,
    }
    return {**body, "stability_root": root(body)}


def inspect_environment(environment: Mapping[str, str], *, strict: bool) -> dict[str, Any]:
    require(hasattr(environment, "items"), "UCM_ENVIRONMENT_INVALID")
    known, unknown, invalid = {}, [], []
    for name, value in sorted(environment.items()):
        if not name.startswith("UCM_"):
            continue
        if name not in SUPPORTED_ENVIRONMENT_VARIABLES:
            unknown.append(name)
            continue
        if value not in SUPPORTED_ENVIRONMENT_VARIABLES[name]["values"]:
            invalid.append(name)
        else:
            known[name] = value
    status = "PASS" if not invalid and (not strict or not unknown) else "REFUSED_ENVIRONMENT"
    body = {
        "schema": "mosaic.ucm.environment-policy-result.v0.1",
        "strict": strict, "recognized": known,
        "unknown_ucm_variables": unknown, "invalid_ucm_variables": invalid,
        "status": status,
        "reason_codes": (["UCM_ENV_VALUE_INVALID"] if invalid else [])
                        + (["UCM_ENV_UNKNOWN"] if strict and unknown else []),
        **BOUNDARY,
    }
    return {**body, "environment_result_root": root(body)}


def external_approval_signing_body(*, approval_id: str, operation_root: str,
                                   approver_identity_root: str,
                                   approver_public_key_hex: str,
                                   policy_root: str, decision: str,
                                   issued_at: int,
                                   not_after: int | None) -> dict[str, Any]:
    require(type(approval_id) is str and approval_id,
            "UCM_APPROVAL_ID_INVALID")
    for value in (operation_root, approver_identity_root, policy_root):
        require_root(value)
    require(decision in {"APPROVE", "REFUSE"}, "UCM_APPROVAL_DECISION_INVALID")
    require(type(issued_at) is int and (not_after is None or
            (type(not_after) is int and not_after >= issued_at)),
            "UCM_APPROVAL_TIME_INVALID")
    require(type(approver_public_key_hex) is str and len(approver_public_key_hex) == 64,
            "UCM_APPROVAL_PUBLIC_KEY_INVALID")
    try:
        key_bytes = bytes.fromhex(approver_public_key_hex)
    except ValueError as exc:
        raise ValueError("UCM_APPROVAL_PUBLIC_KEY_INVALID") from exc
    require(len(key_bytes) == 32, "UCM_APPROVAL_PUBLIC_KEY_INVALID")
    return {
        "schema": "mosaic.ucm.external-human-approval.v0.1",
        "approval_id": approval_id, "operation_root": operation_root,
        "approver_identity_root": approver_identity_root,
        "approver_public_key_hex": approver_public_key_hex,
        "policy_root": policy_root, "decision": decision,
        "issued_at": issued_at, "not_after": not_after,
        "non_claims": ["UCM_DID_NOT_GRANT_AUTHORITY", "EXTERNAL_APPROVAL_ONLY"],
        **BOUNDARY,
    }


def build_external_approval(*, approval_id: str, operation_root: str,
                            approver_identity_root: str,
                            approver_public_key_hex: str, policy_root: str,
                            decision: str, issued_at: int,
                            not_after: int | None,
                            signature_hex: str) -> dict[str, Any]:
    body = external_approval_signing_body(
        approval_id=approval_id, operation_root=operation_root,
        approver_identity_root=approver_identity_root,
        approver_public_key_hex=approver_public_key_hex,
        policy_root=policy_root, decision=decision, issued_at=issued_at,
        not_after=not_after)
    require(type(signature_hex) is str and len(signature_hex) == 128,
            "UCM_APPROVAL_SIGNATURE_INVALID")
    try:
        signature = bytes.fromhex(signature_hex)
    except ValueError as exc:
        raise ValueError("UCM_APPROVAL_SIGNATURE_INVALID") from exc
    require(len(signature) == 64, "UCM_APPROVAL_SIGNATURE_INVALID")
    signed = {**body, "signature_hex": signature_hex}
    return {**signed, "approval_root": root(signed)}


def verify_external_approval(value: Any, *, expected_operation_root: str,
                             expected_policy_root: str, now: int) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "approval_id", "operation_root", "approver_identity_root",
        "approver_public_key_hex", "policy_root", "decision", "issued_at",
        "not_after", "non_claims", "standing", "authority_effect", "real_a5",
        "g0", "signature_hex", "approval_root",
    })
    expected = build_external_approval(
        approval_id=item["approval_id"], operation_root=item["operation_root"],
        approver_identity_root=item["approver_identity_root"],
        approver_public_key_hex=item["approver_public_key_hex"],
        policy_root=item["policy_root"], decision=item["decision"],
        issued_at=item["issued_at"], not_after=item["not_after"],
        signature_hex=item["signature_hex"])
    require(item == expected, "UCM_APPROVAL_INVALID")
    signing_body = external_approval_signing_body(
        approval_id=item["approval_id"], operation_root=item["operation_root"],
        approver_identity_root=item["approver_identity_root"],
        approver_public_key_hex=item["approver_public_key_hex"],
        policy_root=item["policy_root"], decision=item["decision"],
        issued_at=item["issued_at"], not_after=item["not_after"])
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(item["approver_public_key_hex"])).verify(
                bytes.fromhex(item["signature_hex"]), canonical_bytes(signing_body))
    except Exception as exc:
        raise ValueError("UCM_APPROVAL_SIGNATURE_INVALID") from exc
    require(item["operation_root"] == require_root(expected_operation_root),
            "UCM_APPROVAL_OPERATION_MISMATCH")
    require(item["policy_root"] == require_root(expected_policy_root),
            "UCM_APPROVAL_POLICY_MISMATCH")
    require(type(now) is int and now >= item["issued_at"],
            "UCM_APPROVAL_NOT_YET_VALID")
    require(item["not_after"] is None or now <= item["not_after"],
            "UCM_APPROVAL_EXPIRED")
    require(item["decision"] == "APPROVE", "UCM_APPROVAL_REFUSED")
    return deepcopy(item)


def time_policy() -> dict[str, Any]:
    body = {
        "schema": "mosaic.ucm.time-and-freshness-policy.v0.1",
        "clock_source": "CALLER_SUPPLIED_INTEGER",
        "system_clock_read_by_CORE": False,
        "allowed_clock_skew_seconds": 0,
        "interval_rule": "NOT_BEFORE_LE_NOW_LE_NOT_AFTER_INCLUSIVE",
        "monotonicity": "JOURNAL_SEQUENCE_NOT_WALL_CLOCK",
        "refusal_codes": ["UCM_EVIDENCE_NOT_YET_VALID", "UCM_EVIDENCE_EXPIRED",
                          "UCM_APPROVAL_NOT_YET_VALID", "UCM_APPROVAL_EXPIRED"],
        **BOUNDARY,
    }
    return {**body, "policy_root": root(body)}


def shell_completion(shell: str) -> dict[str, Any]:
    require(shell in {"bash", "zsh", "fish", "powershell"},
            "UCM_COMPLETION_SHELL_UNSUPPORTED")
    surfaces = [row["name"] for row in capability_registry()["surfaces"]]
    commands = [
        "orient", "capabilities", "profiles", "doctor", "smoke",
        "contract-init", "contract-doctor", "contract-lint", "contract-diff",
        "contract-compatibility", "explain-selection", "configuration-diff",
        "journal-summary", "journal-query", "journal-diff", "pretty",
        "abi-stability", "environment-check", "process-build",
        "operational-invoke", "invoke",
    ]
    words_list = sorted(set(commands + surfaces))
    words = " ".join(words_list)
    if shell == "powershell":
        script = ("Register-ArgumentCompleter -Native -CommandName ucm -ScriptBlock {\n"
                  "  param($wordToComplete)\n"
                  f"  @('{"','".join(words_list)}') | Where-Object {{ $_ -like \"$wordToComplete*\" }}\n"
                  "}\n")
    elif shell == "fish":
        script = "\n".join(f"complete -c ucm -f -a '{name}'" for name in words_list) + "\n"
    elif shell == "zsh":
        script = f"#compdef ucm\n_arguments '1:command:(({words}))'\n"
    else:
        script = ("_ucm_complete() { COMPREPLY=( $(compgen -W '"
                  + words + "' -- \"${COMP_WORDS[1]}\") ); }\ncomplete -F _ucm_complete ucm\n")
    body = {
        "schema": "mosaic.ucm.shell-completion.v0.1", "shell": shell,
        "capability_registry_root": capability_registry()["root"],
        "commands": sorted(commands), "surface_names": surfaces,
        "script": script, **BOUNDARY,
    }
    return {**body, "completion_root": root(body)}

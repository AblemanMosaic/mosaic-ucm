"""Time-bounded external evidence envelopes.

Subject identity, permit validity, and evidence freshness are deliberately
separate.  An unchanged subject does not make an old attestation current.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .system import BOUNDARY


def build_evidence_envelope(*, evidence_id: str, subject_root: str,
                            policy_root: str, issuer_root: str,
                            verifier_root: str, environment_root: str,
                            result_root: str, result_status: str,
                            issued_at: int, not_before: int,
                            not_after: int | None) -> dict[str, Any]:
    require(type(evidence_id) is str and evidence_id, "UCM_EVIDENCE_ID_INVALID")
    for value in (subject_root, policy_root, issuer_root, verifier_root,
                  environment_root, result_root):
        require_root(value)
    require(result_status in {"PASS", "FAIL", "INFORMATION_ONLY"},
            "UCM_EVIDENCE_STATUS_INVALID")
    require(type(issued_at) is int and type(not_before) is int
            and not_before <= issued_at, "UCM_EVIDENCE_TIME_INVALID")
    require(not_after is None or (type(not_after) is int and issued_at <= not_after),
            "UCM_EVIDENCE_TIME_INVALID")
    body = {
        "schema": "mosaic.ucm.external-evidence-envelope.v0.1",
        "evidence_id": evidence_id,
        "subject_root": subject_root,
        "policy_root": policy_root,
        "issuer_root": issuer_root,
        "verifier_root": verifier_root,
        "environment_root": environment_root,
        "result_root": result_root,
        "result_status": result_status,
        "issued_at": issued_at,
        "not_before": not_before,
        "not_after": not_after,
        **BOUNDARY,
    }
    return {**body, "evidence_root": root(body)}


def validate_evidence_envelope(value: Any, *, expected_subject_root: str,
                               expected_policy_root: str, now: int) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "evidence_id", "subject_root", "policy_root", "issuer_root",
        "verifier_root", "environment_root", "result_root", "result_status",
        "issued_at", "not_before", "not_after", "standing", "authority_effect",
        "real_a5", "g0", "evidence_root",
    })
    require(type(now) is int, "UCM_EVIDENCE_NOW_INVALID")
    expected = build_evidence_envelope(
        evidence_id=item["evidence_id"], subject_root=item["subject_root"],
        policy_root=item["policy_root"], issuer_root=item["issuer_root"],
        verifier_root=item["verifier_root"], environment_root=item["environment_root"],
        result_root=item["result_root"], result_status=item["result_status"],
        issued_at=item["issued_at"], not_before=item["not_before"],
        not_after=item["not_after"])
    require(item == expected, "UCM_EVIDENCE_ENVELOPE_INVALID")
    require(item["subject_root"] == require_root(expected_subject_root),
            "UCM_EVIDENCE_SUBJECT_MISMATCH")
    require(item["policy_root"] == require_root(expected_policy_root),
            "UCM_EVIDENCE_POLICY_MISMATCH")
    require(now >= item["not_before"], "UCM_EVIDENCE_NOT_YET_VALID")
    require(item["not_after"] is None or now <= item["not_after"],
            "UCM_EVIDENCE_EXPIRED")
    return deepcopy(item)

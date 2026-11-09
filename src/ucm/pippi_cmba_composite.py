"""Composite CMBA boundary for one exact P/PPI common turn.

The composite preserves each constitutional co-projection as an independently
validated record.  It never treats equal bytes or a shared envelope as proof
that CMBA, DKN, THR, CHC, CCP, or the operational gateway mean the same thing.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import canonical_bytes, exact_keys, require, root

from .amcas import BOUNDARY
from .ccp_admissibility import validate_chc_thr_correspondence
from .operation_gateway import validate_operation_history
from .operation_proofs import build_operation_proof_bundle
from .pippi_cmba import validate_cmba_turn_assessment
from .pippi_constitution import build_ccp_transition_binding
from .pippi_turn_record import validate_turn_record
from .process_governance import validate_dkn_locality_binding
from .thr_cas import build_thr_manifest, verify_thr_manifest


SCHEMA = "mosaic.ucm.pippi-cmba-composite-assessment.v0.1"
PROFILE_SCHEMA = "mosaic.ucm.pippi-cmba-composite-profile.v0.1"
THR_CONTRACT = {
    "schema": "mosaic.ucm.pippi-cmba-composite-thr-contract.v0.1",
    "state": "EXACT_CANONICAL_INPUT_BYTES",
    "admissibility": "CCP_AND_CHC_GOVERNANCE_ROOTS",
    "meaning": "CMBA_PROFILE_BINDING_AND_TURN_ROOTS",
    "locality": "DKN_AND_CHC_LOCALITY_ROOTS",
    "receipt_identity": "G1_G2_G3_AND_OPERATION_PROOF_ROOTS",
    "digest_identity_rule": "CO_PROJECTION_ROOTS_REMAIN_DISTINCT",
    **BOUNDARY,
}
THR_CONTRACT_ROOT = root(THR_CONTRACT)


def composite_profile() -> dict[str, Any]:
    body = {
        "schema": PROFILE_SCHEMA,
        "profile_id": "PIPPI.CMBA.COMPOSITE.V1",
        "required_co_projections": ["CHC_THR", "CMBA", "CCP", "DKN", "THR"],
        "conditional_co_projections": ["G1_SENTINEL", "G2_WITNESS", "G3_DIAGNOSTIC"],
        "thr_contract": deepcopy(THR_CONTRACT),
        "thr_contract_root": THR_CONTRACT_ROOT,
        "modes": ["EFFECT_BOUND", "OBSERVATIONAL"],
        "identity_rule": "ROOTS_ARE_BOUND_BUT_NEVER_COLLAPSED",
        "effect_rule": "ONLY_VALIDATED_OPERATION_HISTORY_MAY_SUPPLY_GATE_RECEIPTS",
        "claim_ceiling": "STRUCTURE_CUSTODY_AND_EXACT_CROSS_LINKS_ONLY",
        "effect_authorized": False,
        **BOUNDARY,
    }
    return {**body, "profile_root": root(body)}


def _operation_projection(operation_history: dict[str, Any] | None, *,
                          turn_record_root: str,
                          ccp_binding: dict[str, Any]) -> tuple[dict[str, Any], dict[str, bytes]]:
    if operation_history is None:
        return ({
            "mode": "OBSERVATIONAL", "operation_id": None, "contract_root": None,
            "state_root": None, "state": "NOT_APPLICABLE", "g1_root": None,
            "g2_root": None, "g3_root": None, "proof_root": None,
            "status": "NO_EFFECT_HISTORY_DECLARED", "effect_authorized": False,
        }, {})
    item = exact_keys(operation_history, {
        "operation_id", "events", "expected_issuer_public_key_hex",
        "expected_jurisdiction_root", "expected_revocation_registry_root",
    })
    require(ccp_binding["transition_ready"] is True
            and ccp_binding["current_use_status"] == "ADMIT",
            "PIPPI_CMBA_COMPOSITE_EFFECT_CCP_NOT_ADMITTED")
    checked = validate_operation_history(
        operation_id=item["operation_id"], events=item["events"],
        expected_issuer_public_key_hex=item["expected_issuer_public_key_hex"],
        expected_jurisdiction_root=item["expected_jurisdiction_root"],
        expected_revocation_registry_root=item["expected_revocation_registry_root"])
    authorized = [row for row in item["events"]
                  if row.get("event_type") == "OPERATION_AUTHORIZED"
                  and row.get("payload", {}).get("operation_id") == item["operation_id"]]
    require(len(authorized) == 1
            and type(authorized[0]["payload"].get("admissibility_bundle")) is dict,
            "PIPPI_CMBA_COMPOSITE_ADMISSIBILITY_BOUND_HISTORY_REQUIRED")
    bundle = authorized[0]["payload"]["admissibility_bundle"]
    require(bundle["decision"]["decision_root"] == ccp_binding["current_use_decision_root"],
            "PIPPI_CMBA_COMPOSITE_CCP_OPERATION_MISMATCH")
    request_binding_root = turn_record_root
    require(checked["contract"]["request_root"] == request_binding_root,
            "PIPPI_CMBA_COMPOSITE_OPERATION_REQUEST_MISMATCH")
    proof = build_operation_proof_bundle(
        operation_id=item["operation_id"], events=item["events"],
        expected_issuer_public_key_hex=item["expected_issuer_public_key_hex"],
        expected_jurisdiction_root=item["expected_jurisdiction_root"],
        expected_revocation_registry_root=item["expected_revocation_registry_root"])
    state = checked["state"]
    terminal = bool(state["terminal"])
    require(not terminal or (state["g1_root"] and state["g2_root"] and state["g3_root"]
                             and proof["status"] == "PASS"),
            "PIPPI_CMBA_COMPOSITE_TERMINAL_RECEIPTS_INCOMPLETE")
    projection = {
        "mode": "EFFECT_BOUND", "operation_id": item["operation_id"],
        "contract_root": checked["contract"]["contract_root"],
        "request_binding_root": request_binding_root,
        "state_root": state["state_root"], "state": state["state"],
        "g1_root": state["g1_root"], "g2_root": state["g2_root"],
        "g3_root": state["g3_root"], "proof_root": proof["proof_root"],
        "status": "G1_G2_G3_COMPLETE" if terminal else "G1_BOUND_PRE_TERMINAL",
        "effect_authorized": False,
    }
    return projection, {
        "operation-events.json": canonical_bytes(item["events"]),
        "operation-proof.json": canonical_bytes(proof),
    }


def build_composite_assessment(*, opening: dict[str, Any], report: dict[str, Any],
                               turn_record: dict[str, Any],
                               cmba_assessment: dict[str, Any],
                               expected_wheel_sha256: str,
                               dkn_locality_binding: dict[str, Any],
                               chc_thr_correspondence: dict[str, Any],
                               ccp_transition_id: str,
                               ccp_evaluation: dict[str, Any] | None,
                               operation_history: dict[str, Any] | None) -> dict[str, Any]:
    turn = validate_turn_record(turn_record, opening=opening, report=report)
    cmba = validate_cmba_turn_assessment(cmba_assessment, opening=opening,
        report=report, turn_record=turn, expected_wheel_sha256=expected_wheel_sha256)
    dkn = validate_dkn_locality_binding(dkn_locality_binding)
    correspondence = validate_chc_thr_correspondence(chc_thr_correspondence)
    require(correspondence["thr_contract_root"] == THR_CONTRACT_ROOT,
            "PIPPI_CMBA_COMPOSITE_THR_CONTRACT_MISMATCH")
    ccp = build_ccp_transition_binding(transition_id=ccp_transition_id,
                                       ccp_evaluation=ccp_evaluation)
    require(ccp["subject_root"] in {None, turn["turn_record_root"]},
            "PIPPI_CMBA_COMPOSITE_CCP_SUBJECT_MISMATCH")
    operation, operation_payloads = _operation_projection(operation_history,
        turn_record_root=turn["turn_record_root"], ccp_binding=ccp)
    payloads = {
        "opening.json": canonical_bytes(opening),
        "report.json": canonical_bytes(report),
        "turn-record.json": canonical_bytes(turn),
        "cmba-assessment.json": canonical_bytes(cmba),
        "dkn-locality.json": canonical_bytes(dkn),
        "chc-thr-correspondence.json": canonical_bytes(correspondence),
        "ccp-transition-binding.json": canonical_bytes(ccp),
        **operation_payloads,
    }
    thr = build_thr_manifest(
        application_id="PIPPI.CMBA.COMPOSITE",
        payloads=payloads,
        meaning={"turn_record_root": turn["turn_record_root"],
                 "cmba_assessment_root": cmba["assessment_root"],
                 "cmba_binding_root": cmba["cmba_binding"]["binding_root"],
                 "cmba_profile_root": cmba["cmba_profile"]["contract_hash"]},
        admissibility={"ccp_transition_binding_root": ccp["ccp_transition_binding_root"],
                       "ccp_status": ccp["current_use_status"],
                       "chc_thr_correspondence_root": correspondence["correspondence_root"]},
        locality={"dkn_locality_binding_root": dkn["locality_binding_root"],
                  "chc_profile_root": correspondence["chc_profile_root"],
                  "namespace_authority_verified": dkn["namespace_authority_verified"]},
        receipts={"operation_id": operation["operation_id"],
                  "g1_root": operation["g1_root"], "g2_root": operation["g2_root"],
                  "g3_root": operation["g3_root"], "proof_root": operation["proof_root"]})
    verify_thr_manifest(thr, payloads=payloads)
    profile = composite_profile()
    roots = {
        "turn_record_root": turn["turn_record_root"],
        "cmba_assessment_root": cmba["assessment_root"],
        "dkn_locality_binding_root": dkn["locality_binding_root"],
        "chc_thr_correspondence_root": correspondence["correspondence_root"],
        "ccp_transition_binding_root": ccp["ccp_transition_binding_root"],
        "thr_body_root": thr["h_body"],
        "operation_proof_root": operation["proof_root"],
    }
    body = {
        "schema": SCHEMA, "profile_root": profile["profile_root"],
        "mode": operation["mode"], "co_projection_roots": roots,
        "cmba_outcome": cmba["outcome"], "ccp_status": ccp["current_use_status"],
        "operation": operation, "thr_manifest": thr,
        "identity_rule": "ROOTS_ARE_BOUND_BUT_NEVER_COLLAPSED",
        "claim_ceiling": profile["claim_ceiling"],
        "acceptance_case_closed": False, "effect_authorized": False,
        **BOUNDARY,
    }
    return {**body, "composite_assessment_root": root(body)}


def validate_composite_assessment(value: dict[str, Any], **inputs: Any) -> dict[str, Any]:
    expected = build_composite_assessment(**inputs)
    require(value == expected, "PIPPI_CMBA_COMPOSITE_ASSESSMENT_MISMATCH")
    return deepcopy(expected)


__all__ = ["THR_CONTRACT_ROOT", "composite_profile", "build_composite_assessment",
           "validate_composite_assessment"]

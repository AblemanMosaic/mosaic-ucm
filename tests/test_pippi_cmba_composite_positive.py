from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from uclop.canonical import canonical_bytes, root
from ucm.amcas import BOUNDARY
from ucm.ccp_admissibility import (build_chc_thr_correspondence,
    build_current_use_snapshot, build_enforcement_perimeter, build_evidence_snapshot,
    build_jurisdiction_profile, evaluate_current_admissibility)
from ucm.operation_gateway import (DISPATCH_SCHEMA, PERMIT_SCHEMA, REVOCATION_SCHEMA,
    TERMINAL_SCHEMA, OperationGateway, build_operation_contract)
from ucm.pippi_cmba import CMBA_WHEEL_SHA256, build_cmba_turn_assessment
from ucm.pippi_cmba_composite import (THR_CONTRACT_ROOT, build_composite_assessment,
    composite_profile, validate_composite_assessment)
from ucm.pippi_constitution import build_ccp_transition_binding
from ucm.process_governance import build_dkn_locality_binding
from ucm.capabilities import invoke

from test_pippi_cmba_positive import common_turn_fixture


ISSUER = Ed25519PrivateKey.from_private_bytes(b"\x31" * 32)
EXECUTOR = Ed25519PrivateKey.from_private_bytes(b"\x32" * 32)


def public(key):
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def signed(body, key, field):
    signature = key.sign(canonical_bytes(body)).hex()
    return {**body, "signature_hex": signature,
            field: root({**body, "signature_hex": signature})}


def ccp_fixture(subject_root: str, *, operation: str = "PROPOSE_PUBLICATION"):
    policy, schemas, trust, checkpoint = [root({"r036": name}) for name in
        ("policy", "schemas", "trust", "checkpoint")]
    jurisdiction_root = root({"r036": "jurisdiction"})
    profile = build_jurisdiction_profile(profile_id="PIPPI.CMBA.COMPOSITE.V1",
        application_id="PIPPI.CMBA.COMPOSITE", subject_root=subject_root,
        state_boundary_id="PIPPI_COMMON_TURN", state_root=subject_root,
        manifest_root=root({"turn": subject_root}), path_policy="EXACT_ARCHIVE_MEMBERS_V1",
        governance_jurisdiction_root=jurisdiction_root, bound_policy_root=policy,
        bound_schema_registry_root=schemas, bound_trust_root=trust,
        transition_rule_root=root({"transition": operation}),
        allowed_operations=[operation], evidence_modes=["LOCAL"])
    perimeter = build_enforcement_perimeter(perimeter_id="PIPPI.CMBA.LOCAL",
        jurisdiction_profile_root=profile["jurisdiction_profile_root"],
        adapter_root=root({"adapter": "r036"}), intercepted_operations=[operation],
        excluded_bypass_classes=["UNMEDIATED_EFFECT"],
        continuing_use_policy="CONTINUOUS_RECHECK",
        qualification_status="QUALIFIED_SCOPED")
    correspondence = build_chc_thr_correspondence(
        correspondence_id="PIPPI.CMBA.CHC.THR", correspondence_version="v0.1",
        chc_source_root=root({"chc": "source"}), chc_profile_root=root({"chc": "profile"}),
        thr_contract_root=THR_CONTRACT_ROOT)
    claims = {"checkpoint": "CURRENT", "policy": "CURRENT",
        "revocation": "CURRENT_CLEAR", "schema": "CURRENT",
        "semantic": "CURRENT", "state": "CURRENT"}
    ids = {name: "R036.STATUS." + name.upper() for name in claims}
    rows = [{"evidence_id": ids[name], "evidence_kind": "STATUS_" + name.upper(),
        "subject_root": subject_root, "evidence_root": root({"status": name}),
        "source_mode": "LOCAL", "verification_status": "PASS", "observed_epoch": 10,
        "valid_until_epoch": 20,
        "admissibility_status_claim": {"domain": name, "observed_status": status}}
        for name, status in ids.items()]
    # Correct the status values after using the deterministic id ordering.
    for row, name in zip(rows, ids):
        row["admissibility_status_claim"]["observed_status"] = claims[name]
    evidence = build_evidence_snapshot(snapshot_id="R036.CMBA.EVIDENCE",
        subject_root=subject_root, state_identity_root=subject_root,
        semantic_identity_root=root({"semantic": subject_root}),
        jurisdiction_profile_root=profile["jurisdiction_profile_root"],
        enforcement_perimeter_root=perimeter["enforcement_perimeter_root"],
        active_policy_root=policy, active_schema_registry_root=schemas,
        active_trust_root=trust, checkpoint_root=checkpoint, checkpoint_sequence=1,
        persistent_maximum_sequence=1, authenticated_epoch=10, evidence=rows,
        status_evidence_ids=ids, unresolved_requirements=[])
    use = build_current_use_snapshot(request_id="R036.CMBA.USE", operation=operation,
        subject_root=subject_root, target_root=subject_root,
        handler_root=root({"handler": "r036"}), runtime_root=root({"runtime": "r036"}),
        dependency_closure_root=root({"deps": "r036"}), state_identity_root=subject_root,
        semantic_identity_root=root({"semantic": subject_root}),
        jurisdiction_profile_root=profile["jurisdiction_profile_root"],
        enforcement_perimeter_root=perimeter["enforcement_perimeter_root"],
        correspondence_root=correspondence["correspondence_root"],
        evidence_snapshot_root=evidence["evidence_snapshot_root"], active_policy_root=policy,
        active_schema_registry_root=schemas, active_trust_root=trust,
        checkpoint_root=checkpoint, authenticated_epoch=10,
        requested_effect_classes=["WRITE_WORKSPACE"], max_steps=100, max_evidence_rows=8)
    anchors = {"expected_subject_root": subject_root,
        "expected_jurisdiction_profile_root": profile["jurisdiction_profile_root"],
        "expected_enforcement_perimeter_root": perimeter["enforcement_perimeter_root"],
        "expected_correspondence_root": correspondence["correspondence_root"],
        "expected_policy_root": policy, "expected_schema_registry_root": schemas,
        "expected_trust_root": trust, "expected_checkpoint_root": checkpoint}
    decision = evaluate_current_admissibility(current_use_snapshot=use,
        evidence_snapshot=evidence, jurisdiction_profile=profile,
        enforcement_perimeter=perimeter, correspondence=correspondence, **anchors)
    evaluation = {"decision": decision, "current_use_snapshot": use,
        "evidence_snapshot": evidence, "jurisdiction_profile": profile,
        "enforcement_perimeter": perimeter, "correspondence": correspondence,
        "expected_anchors": anchors}
    return evaluation, correspondence, jurisdiction_root


def operation_fixture(request_root: str, jurisdiction_root: str):
    revocation = signed({"schema": REVOCATION_SCHEMA,
        "issuer_public_key_hex": public(ISSUER), "jurisdiction_root": jurisdiction_root,
        "generation": 1, "sequence": 1, "valid_at": 10,
        "revoked_permit_roots": [], "predecessor_root": "0" * 64, **BOUNDARY},
        ISSUER, "revocation_registry_root")
    permit = signed({"schema": PERMIT_SCHEMA, "permit_id": "permit:r036:1",
        "issuer_public_key_hex": public(ISSUER), "subject_identity_root": root({"user": 1}),
        "session_root": root({"session": 1}), "jurisdiction_root": jurisdiction_root,
        "application_id": "PIPPI.CMBA.COMPOSITE", "action_id": "PROPOSE_PUBLICATION",
        "request_root": request_root, "executor_public_key_hex": public(EXECUTOR),
        "allowed_effect_classes": ["WRITE_WORKSPACE"],
        "budget": {"max_cases": 1, "max_duration_ms": 1000, "max_output_bytes": 4096},
        "rollback_root": root({"rollback": 1}), "generation": 1,
        "nonce": root({"nonce": 1}), "issued_at": 8, "not_before": 9,
        "expires_at": 20, "revocation_registry_root": revocation["revocation_registry_root"],
        **BOUNDARY}, ISSUER, "permit_root")
    contract = build_operation_contract(operation_id="op:r036:1", permit=permit,
        revocation_registry=revocation, expected_issuer_public_key_hex=public(ISSUER),
        expected_jurisdiction_root=jurisdiction_root,
        expected_revocation_registry_root=revocation["revocation_registry_root"],
        requested_effect_classes=["WRITE_WORKSPACE"], idempotency_key=root({"id": 1}),
        expected_result_root=root({"result": 1}), now=10)
    return revocation, contract


def dispatch(prepared, contract):
    return signed({"schema": DISPATCH_SCHEMA, "operation_id": contract["operation_id"],
        "contract_root": contract["contract_root"], "g1_root": prepared["g1"]["receipt_root"],
        "dispatch_authorization_root": prepared["dispatch_authorization"]["receipt_root"],
        "idempotency_key": contract["idempotency_key"],
        "dispatch_nonce": prepared["dispatch_authorization"]["dispatch_nonce"],
        "started_at": 11, "status": "DISPATCHED", **BOUNDARY}, EXECUTOR, "receipt_root")


def terminal(dispatched, contract):
    return signed({"schema": TERMINAL_SCHEMA, "operation_id": contract["operation_id"],
        "contract_root": contract["contract_root"],
        "dispatch_root": dispatched["dispatch_receipt"]["receipt_root"],
        "terminal_status": "COMPLETED", "result_root": contract["expected_result_root"],
        "output_bytes": 1, "completed_cases": 1,
        "observed_effect_classes": ["WRITE_WORKSPACE"], "ended_at": 12,
        "receipt_nonce": root({"receipt": 1}), **BOUNDARY}, EXECUTOR, "receipt_root")


class PippiCmbaCompositePositiveTests(unittest.TestCase):
    def inputs(self):
        opening, report, turn = common_turn_fixture()
        cmba = build_cmba_turn_assessment(opening=opening, report=report, turn_record=turn,
            expected_wheel_sha256=CMBA_WHEEL_SHA256)
        evaluation, correspondence, jurisdiction_root = ccp_fixture(turn["turn_record_root"])
        dkn = build_dkn_locality_binding(phase_code="CMBA_R036",
            authority_public_key_hex="41" * 32, semantic_namespace="mosaic.ucm.v0.1",
            universe_root=root({"universe": "r036"}), namespace_policy_root=root({"policy": "r036"}),
            passport=None, possession_receipt_root=None, local_admission_root=None)
        return opening, report, turn, cmba, evaluation, correspondence, jurisdiction_root, dkn

    def test_observational_composite_keeps_roots_distinct(self):
        opening, report, turn, cmba, evaluation, correspondence, _, dkn = self.inputs()
        inputs = dict(opening=opening, report=report, turn_record=turn,
            cmba_assessment=cmba, expected_wheel_sha256=CMBA_WHEEL_SHA256,
            dkn_locality_binding=dkn, chc_thr_correspondence=correspondence,
            ccp_transition_id="PROPOSE_PUBLICATION", ccp_evaluation=evaluation,
            operation_history=None)
        result = build_composite_assessment(**inputs)
        self.assertEqual(result["mode"], "OBSERVATIONAL")
        self.assertEqual(result["ccp_status"], "ADMIT")
        self.assertEqual(result["operation"]["status"], "NO_EFFECT_HISTORY_DECLARED")
        self.assertFalse(result["effect_authorized"])
        roots = [value for value in result["co_projection_roots"].values() if value]
        self.assertEqual(len(roots), len(set(roots)))
        self.assertEqual(validate_composite_assessment(result, **inputs), result)

    def test_effect_history_binds_ccp_and_complete_gates(self):
        opening, report, turn, cmba, evaluation, correspondence, jurisdiction_root, dkn = self.inputs()
        ccp = build_ccp_transition_binding(transition_id="PROPOSE_PUBLICATION",
                                           ccp_evaluation=evaluation)
        request_root = turn["turn_record_root"]
        revocation, contract = operation_fixture(request_root, jurisdiction_root)
        anchors = evaluation["expected_anchors"]
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as raw:
            gateway = OperationGateway(Path(raw))
            prepared = gateway.prepare_with_admissibility(contract, evaluation["decision"],
                current_use_snapshot=evaluation["current_use_snapshot"],
                evidence_snapshot=evaluation["evidence_snapshot"],
                jurisdiction_profile=evaluation["jurisdiction_profile"],
                enforcement_perimeter=evaluation["enforcement_perimeter"],
                correspondence=evaluation["correspondence"],
                expected_admissibility_decision_root=evaluation["decision"]["decision_root"],
                expected_current_use_snapshot_root=evaluation["current_use_snapshot"]["current_use_snapshot_root"],
                expected_issuer_public_key_hex=public(ISSUER),
                expected_jurisdiction_root=jurisdiction_root,
                expected_revocation_registry_root=revocation["revocation_registry_root"], **anchors)
            dispatched = gateway.record_dispatch(contract["operation_id"], dispatch(prepared, contract))
            gateway.record_terminal(contract["operation_id"], terminal(dispatched, contract))
            operation_history = {"operation_id": contract["operation_id"],
                "events": gateway.journal.verify(),
                "expected_issuer_public_key_hex": public(ISSUER),
                "expected_jurisdiction_root": jurisdiction_root,
                "expected_revocation_registry_root": revocation["revocation_registry_root"]}
            result = build_composite_assessment(opening=opening, report=report, turn_record=turn,
                cmba_assessment=cmba, expected_wheel_sha256=CMBA_WHEEL_SHA256,
                dkn_locality_binding=dkn, chc_thr_correspondence=correspondence,
                ccp_transition_id="PROPOSE_PUBLICATION", ccp_evaluation=evaluation,
                operation_history=operation_history)
        self.assertEqual(result["mode"], "EFFECT_BOUND")
        self.assertEqual(result["operation"]["status"], "G1_G2_G3_COMPLETE")
        self.assertTrue(all(result["operation"][name] for name in ("g1_root", "g2_root", "g3_root")))
        self.assertFalse(result["effect_authorized"])

    def test_public_abi_exposes_profile(self):
        response = invoke({"schema": "mosaic.ucm.request.v0.1", "request_id": "r036-profile",
            "surface": "DISCOVER_PIPPI_CMBA_COMPOSITE_PROFILE", "payload": {}})
        self.assertEqual(response["result"], composite_profile())

    def test_public_cli_exposes_profile_without_writing(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root.parent) as raw:
            start = Path(raw)
            before = list(start.iterdir())
            environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                           "PYTHONPATH": str(root / "src")}
            process = subprocess.run([sys.executable, "-B", "-m", "ucm.pippi_cli",
                "--data-root", str(start / "absent-hub"), "cmba-composite-profile"],
                cwd=start, capture_output=True, check=False, env=environment)
            self.assertEqual(process.returncode, 0, process.stderr.decode(errors="replace"))
            self.assertEqual(json.loads(process.stdout), composite_profile())
            self.assertEqual(list(start.iterdir()), before)


if __name__ == "__main__":
    unittest.main()

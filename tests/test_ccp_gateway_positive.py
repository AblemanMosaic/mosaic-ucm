from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from uclop.canonical import root
from ucm.ccp_admissibility import (
    build_chc_thr_correspondence,
    build_enforcement_perimeter,
    build_evidence_snapshot,
    build_current_use_snapshot,
    build_jurisdiction_profile,
    evaluate_current_admissibility,
)
from ucm.operation_gateway import (
    OperationGateway,
    validate_admissibility_bound_operation_history,
)
from ucm.capabilities import invoke
from ucm.system import capability_registry

from tests.test_stage4_c5_operational_positive import ISSUER, fixture, public


def h(label: str) -> str:
    return root({"ccp": label})


def status_evidence(subject: str) -> tuple[list[dict], dict[str, str]]:
    ids = {domain: f"LOCAL.STATUS.{domain.upper()}" for domain in (
        "checkpoint", "policy", "revocation", "schema", "semantic", "state")}
    observations = {
        "checkpoint": "CURRENT", "policy": "CURRENT",
        "revocation": "CURRENT_CLEAR", "schema": "CURRENT",
        "semantic": "CURRENT", "state": "CURRENT",
    }
    rows = [{
        "evidence_id": evidence_id,
        "evidence_kind": f"STATUS_{domain.upper()}",
        "subject_root": subject,
        "evidence_root": h(f"status-{domain}"),
        "source_mode": "LOCAL", "verification_status": "PASS",
        "observed_epoch": 100, "valid_until_epoch": 110,
        "admissibility_status_claim": {
            "domain": domain, "observed_status": observations[domain],
        },
    } for domain, evidence_id in ids.items()]
    return rows, ids


def admissibility_fixture(contract: dict) -> tuple[dict, ...]:
    subject = h("exact-artifact")
    policy = h("active-policy")
    schemas = h("active-schema-registry")
    trust = h("active-trust")
    checkpoint = h("checkpoint-7")
    jurisdiction = build_jurisdiction_profile(
        profile_id="CCP.UCM.V0_1",
        application_id=contract["application_id"],
        subject_root=subject,
        state_boundary_id="EXACT_ARCHIVE",
        state_root=subject,
        manifest_root=h("archive-manifest"),
        path_policy="EXACT_ARCHIVE_MEMBERS_V1",
        governance_jurisdiction_root=contract["jurisdiction_root"],
        bound_policy_root=policy,
        bound_schema_registry_root=schemas,
        bound_trust_root=trust,
        transition_rule_root=h("context-transition"),
        allowed_operations=[contract["action_id"]],
        evidence_modes=["LOCAL"])
    perimeter = build_enforcement_perimeter(
        perimeter_id="CCP.LOCAL.BROKER",
        jurisdiction_profile_root=jurisdiction["jurisdiction_profile_root"],
        adapter_root=h("adapter"),
        intercepted_operations=[contract["action_id"]],
        excluded_bypass_classes=["ALTERNATE_LOADER"],
        continuing_use_policy="LAUNCH_ONLY_RECHECK_REQUIRED",
        qualification_status="QUALIFIED_SCOPED")
    correspondence = build_chc_thr_correspondence(
        correspondence_id="CCP.CHC.THR.V1",
        correspondence_version="v0.1",
        chc_source_root=h("chc-source"),
        chc_profile_root=h("chc-profile"),
        thr_contract_root=h("thr-contract"))
    evidence_rows, status_ids = status_evidence(subject)
    evidence = build_evidence_snapshot(
        snapshot_id="CCP.EVIDENCE.7",
        subject_root=subject,
        state_identity_root=subject,
        semantic_identity_root=h("semantic-identity"),
        jurisdiction_profile_root=jurisdiction["jurisdiction_profile_root"],
        enforcement_perimeter_root=perimeter["enforcement_perimeter_root"],
        active_policy_root=policy,
        active_schema_registry_root=schemas,
        active_trust_root=trust,
        checkpoint_root=checkpoint,
        checkpoint_sequence=7,
        persistent_maximum_sequence=7,
        authenticated_epoch=100,
        evidence=evidence_rows,
        status_evidence_ids=status_ids,
        unresolved_requirements=[])
    use = build_current_use_snapshot(
        request_id="CCP.REQUEST.1",
        operation=contract["action_id"],
        subject_root=subject,
        target_root=contract["request_root"],
        handler_root=h("handler"),
        runtime_root=h("runtime"),
        dependency_closure_root=h("dependencies"),
        state_identity_root=subject,
        semantic_identity_root=h("semantic-identity"),
        jurisdiction_profile_root=jurisdiction["jurisdiction_profile_root"],
        enforcement_perimeter_root=perimeter["enforcement_perimeter_root"],
        correspondence_root=correspondence["correspondence_root"],
        evidence_snapshot_root=evidence["evidence_snapshot_root"],
        active_policy_root=policy,
        active_schema_registry_root=schemas,
        active_trust_root=trust,
        checkpoint_root=checkpoint,
        authenticated_epoch=100,
        requested_effect_classes=contract["requested_effect_classes"],
        max_steps=100,
        max_evidence_rows=8)
    anchors = {
        "expected_subject_root": subject,
        "expected_jurisdiction_profile_root":
            jurisdiction["jurisdiction_profile_root"],
        "expected_enforcement_perimeter_root":
            perimeter["enforcement_perimeter_root"],
        "expected_correspondence_root": correspondence["correspondence_root"],
        "expected_policy_root": policy,
        "expected_schema_registry_root": schemas,
        "expected_trust_root": trust,
        "expected_checkpoint_root": checkpoint,
    }
    decision = evaluate_current_admissibility(
        current_use_snapshot=use,
        evidence_snapshot=evidence,
        jurisdiction_profile=jurisdiction,
        enforcement_perimeter=perimeter,
        correspondence=correspondence,
        **anchors)
    return jurisdiction, perimeter, correspondence, evidence, use, decision, anchors


class CcpGatewayPositiveTests(unittest.TestCase):
    def test_ccp_native_binding_and_point_of_use_gateway_positive(self) -> None:
        revocation, _, contract = fixture()
        (jurisdiction, perimeter, correspondence, evidence, use,
         decision, anchors) = admissibility_fixture(contract)
        self.assertEqual("ADMIT", decision["decision"])
        self.assertFalse(decision["effect_authorized"])
        projection_response = invoke({
            "schema": "mosaic.ucm.request.v0.1",
            "surface": "EXPLAIN_CURRENT_ADMISSIBILITY",
            "payload": {
                "decision": decision,
                "current_use_snapshot": use,
                "evidence_snapshot": evidence,
                "jurisdiction_profile": jurisdiction,
                "enforcement_perimeter": perimeter,
                "correspondence": correspondence,
                **anchors,
            },
            "request_id": "ccp-explain-current-admissibility",
        })
        self.assertEqual(
            "YES_SUBJECT_TO_SEPARATE_GATEWAY_AUTHORIZATION",
            projection_response["result"]["answer"],
        )
        # Keep disposable journal custody inside the governed workspace.  Some
        # Windows sandbox profiles expose the process TEMP path read-only.
        with tempfile.TemporaryDirectory() as raw:
            gateway = OperationGateway(Path(raw))
            prepared = gateway.prepare_with_admissibility(
                contract, decision,
                current_use_snapshot=use,
                evidence_snapshot=evidence,
                jurisdiction_profile=jurisdiction,
                enforcement_perimeter=perimeter,
                correspondence=correspondence,
                expected_admissibility_decision_root=decision["decision_root"],
                expected_current_use_snapshot_root=
                    use["current_use_snapshot_root"],
                expected_issuer_public_key_hex=public(ISSUER),
                expected_jurisdiction_root=contract["jurisdiction_root"],
                expected_revocation_registry_root=
                    revocation["revocation_registry_root"],
                **anchors)
            self.assertEqual(
                decision["decision_root"],
                prepared["g1"]["admissibility_decision_root"])
            self.assertEqual(
                contract["application_id"],
                prepared["admissibility_bundle"]["binding"]["application_id"])
            self.assertEqual(
                contract["jurisdiction_root"],
                prepared["admissibility_bundle"]["binding"][
                    "gateway_jurisdiction_root"])
            self.assertTrue(prepared["dispatch_authorization"][
                "pre_effect_version_check_required"])
            checked = validate_admissibility_bound_operation_history(
                operation_id=contract["operation_id"],
                events=gateway.journal.verify(),
                expected_issuer_public_key_hex=public(ISSUER),
                expected_jurisdiction_root=contract["jurisdiction_root"],
                expected_revocation_registry_root=
                    revocation["revocation_registry_root"],
                expected_admissibility_decision_root=decision["decision_root"],
                expected_current_use_snapshot_root=
                    use["current_use_snapshot_root"],
                **anchors)
            self.assertEqual(
                prepared["admissibility_bundle"]["binding"]["binding_root"],
                checked["admissibility_binding_root"])

        surfaces = {
            row["name"]: row for row in capability_registry()["surfaces"]
        }
        for name in (
                "BUILD_ADMISSIBILITY_JURISDICTION",
                "BUILD_ADMISSIBILITY_ENFORCEMENT_PERIMETER",
                "BUILD_CHC_THR_CORRESPONDENCE",
                "BUILD_ADMISSIBILITY_EVIDENCE_SNAPSHOT",
                "BUILD_CURRENT_USE_SNAPSHOT",
                "EVALUATE_CURRENT_ADMISSIBILITY",
                "EXPLAIN_CURRENT_ADMISSIBILITY"):
            self.assertEqual("PURE_COMPUTATION", surfaces[name]["effect_scope"])
        self.assertEqual(
            "LOCAL_ARTIFACT_PREPARATION",
            surfaces["PREPARE_ADMISSIBILITY_BOUND_GATEWAY"]["effect_scope"])


if __name__ == "__main__":
    unittest.main()

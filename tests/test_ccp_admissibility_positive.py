from __future__ import annotations

import unittest

from uclop.canonical import root
from ucm.ccp_admissibility import (
    build_admissibility_projection,
    build_chc_thr_correspondence,
    build_current_use_snapshot,
    build_enforcement_perimeter,
    build_evidence_snapshot,
    build_jurisdiction_profile,
    evaluate_current_admissibility,
    validate_admissibility_decision,
    validate_admissibility_projection,
    validate_chc_thr_correspondence,
    validate_current_use_snapshot,
    validate_enforcement_perimeter,
    validate_evidence_snapshot,
    validate_jurisdiction_profile,
)


SUBJECT_ROOT = "9a38419d655b9306c7216554081a6c869e12c0dcab1e08b961b8d645115e985e"
STATE_ROOT = root({"exact_archive_sha256": SUBJECT_ROOT})
SEMANTIC_ROOT = root({"program": "CCP-JM", "version": "v0.1", "revision": "r001"})
POLICY_ROOT = root({"policy": "ccp-local-use", "revision": 1})
SCHEMA_ROOT = root({"schema_registry": "ccp-local", "revision": 1})
TRUST_ROOT = root({"trust": "local-custody-only", "revision": 1})
CHECKPOINT_ROOT = root({"checkpoint": 7})


def status_evidence(*, revocation_status: str = "CURRENT_CLEAR",
                    schema_status: str = "CURRENT") -> tuple[list[dict], dict[str, str]]:
    ids = {domain: f"ccp.status.{domain}" for domain in (
        "checkpoint", "policy", "revocation", "schema", "semantic", "state")}
    observations = {
        "checkpoint": "CURRENT", "policy": "CURRENT",
        "revocation": "REVOKED" if revocation_status == "REVOKED" else "CURRENT_CLEAR",
        "schema": "CURRENT", "semantic": "CURRENT", "state": "CURRENT",
    }
    rows = []
    for domain, evidence_id in ids.items():
        verification = "PASS"
        if domain == "revocation" and revocation_status == "UNAVAILABLE":
            verification = "UNAVAILABLE"
        if domain == "schema" and schema_status == "UNRESOLVED":
            verification = "UNRESOLVED"
        valid_until = 119 if ((domain == "schema" and schema_status == "STALE")
                              or (domain == "revocation" and revocation_status == "STALE")) else 140
        rows.append({
            "evidence_id": evidence_id,
            "evidence_kind": f"STATUS_{domain.upper()}",
            "subject_root": SUBJECT_ROOT,
            "evidence_root": root({"status-evidence": domain,
                                   "observation": observations[domain]}),
            "source_mode": "LOCAL", "verification_status": verification,
            "observed_epoch": 118, "valid_until_epoch": valid_until,
            "admissibility_status_claim": {
                "domain": domain, "observed_status": observations[domain],
            },
        })
    return rows, ids


def fixture(*, snapshot_id: str = "ccp.snapshot.current",
            revocation_status: str = "CURRENT_CLEAR",
            schema_status: str = "CURRENT",
            operation: str = "USE.EXACT.ARTIFACT",
            unresolved_requirements: list[str] | None = None) -> dict:
    profile = build_jurisdiction_profile(
        profile_id="ccp.local-information-only",
        application_id="MOSAIC.UCM.CCP_JM",
        subject_root=SUBJECT_ROOT,
        state_boundary_id="exact-ccp-jm-r001-archive",
        state_root=STATE_ROOT,
        manifest_root=root({"packet_manifest": SUBJECT_ROOT}),
        path_policy="EXACT_ARCHIVE_MEMBERS_V1",
        governance_jurisdiction_root=root({"jurisdiction": "local.ccp"}),
        bound_policy_root=POLICY_ROOT,
        bound_schema_registry_root=SCHEMA_ROOT,
        bound_trust_root=TRUST_ROOT,
        transition_rule_root=root({"transition": "explicit-successor-only"}),
        allowed_operations=[operation],
        evidence_modes=["LOCAL"],
    )
    perimeter = build_enforcement_perimeter(
        perimeter_id="ccp.local.launch-adapter",
        jurisdiction_profile_root=profile["jurisdiction_profile_root"],
        adapter_root=root({"adapter": "ccp-fixture-adapter"}),
        intercepted_operations=[operation],
        excluded_bypass_classes=["DIRECT_UNMEDIATED_EXECUTION"],
        continuing_use_policy="LAUNCH_ONLY_RECHECK_REQUIRED",
        qualification_status="QUALIFIED_SCOPED",
    )
    correspondence = build_chc_thr_correspondence(
        correspondence_id="ccp.chc-thr.local-v1",
        correspondence_version="v0.1",
        chc_source_root=root({"source": "CHC-paper-pinned"}),
        chc_profile_root=root({"profile": "CCP-JM-CHC-profile"}),
        thr_contract_root=root({"contract": "UCM-THR-v0.1"}),
    )
    evidence_rows, status_ids = status_evidence(
        revocation_status=revocation_status, schema_status=schema_status)
    evidence = build_evidence_snapshot(
        snapshot_id=snapshot_id,
        subject_root=SUBJECT_ROOT,
        state_identity_root=STATE_ROOT,
        semantic_identity_root=SEMANTIC_ROOT,
        jurisdiction_profile_root=profile["jurisdiction_profile_root"],
        enforcement_perimeter_root=perimeter["enforcement_perimeter_root"],
        active_policy_root=POLICY_ROOT,
        active_schema_registry_root=SCHEMA_ROOT,
        active_trust_root=TRUST_ROOT,
        checkpoint_root=CHECKPOINT_ROOT,
        checkpoint_sequence=7,
        persistent_maximum_sequence=7,
        authenticated_epoch=120,
        evidence=evidence_rows,
        status_evidence_ids=status_ids,
        unresolved_requirements=[] if unresolved_requirements is None
        else unresolved_requirements,
    )
    use = build_current_use_snapshot(
        request_id=f"use.{snapshot_id}",
        operation=operation,
        subject_root=SUBJECT_ROOT,
        target_root=SUBJECT_ROOT,
        handler_root=root({"handler": "read-only-inspector"}),
        runtime_root=root({"runtime": "python-stdlib"}),
        dependency_closure_root=root({"dependencies": ["python-stdlib"]}),
        state_identity_root=STATE_ROOT,
        semantic_identity_root=SEMANTIC_ROOT,
        jurisdiction_profile_root=profile["jurisdiction_profile_root"],
        enforcement_perimeter_root=perimeter["enforcement_perimeter_root"],
        correspondence_root=correspondence["correspondence_root"],
        evidence_snapshot_root=evidence["evidence_snapshot_root"],
        active_policy_root=POLICY_ROOT,
        active_schema_registry_root=SCHEMA_ROOT,
        active_trust_root=TRUST_ROOT,
        checkpoint_root=CHECKPOINT_ROOT,
        authenticated_epoch=120,
        requested_effect_classes=["READ_ONLY"],
        max_steps=1000,
        max_evidence_rows=8,
    )
    anchors = {
        "expected_subject_root": SUBJECT_ROOT,
        "expected_jurisdiction_profile_root": profile["jurisdiction_profile_root"],
        "expected_enforcement_perimeter_root": perimeter["enforcement_perimeter_root"],
        "expected_correspondence_root": correspondence["correspondence_root"],
        "expected_policy_root": POLICY_ROOT,
        "expected_schema_registry_root": SCHEMA_ROOT,
        "expected_trust_root": TRUST_ROOT,
        "expected_checkpoint_root": CHECKPOINT_ROOT,
    }
    decision = evaluate_current_admissibility(
        current_use_snapshot=use,
        evidence_snapshot=evidence,
        jurisdiction_profile=profile,
        enforcement_perimeter=perimeter,
        correspondence=correspondence,
        **anchors,
    )
    projection = build_admissibility_projection(
        decision=decision,
        current_use_snapshot=use,
        evidence_snapshot=evidence,
        jurisdiction_profile=profile,
        enforcement_perimeter=perimeter,
        correspondence=correspondence,
        **anchors,
    )
    return {
        "profile": profile,
        "perimeter": perimeter,
        "correspondence": correspondence,
        "evidence": evidence,
        "use": use,
        "anchors": anchors,
        "decision": decision,
        "projection": projection,
    }


class CCPAdmissibilityPositiveTests(unittest.TestCase):
    def test_ccp_native_binding_and_point_of_use_gateway_positive(self) -> None:
        records = fixture()
        self.assertEqual(records["profile"],
                         validate_jurisdiction_profile(records["profile"]))
        self.assertEqual(records["perimeter"],
                         validate_enforcement_perimeter(records["perimeter"]))
        self.assertEqual(records["correspondence"],
                         validate_chc_thr_correspondence(records["correspondence"]))
        self.assertEqual("DIGESTS_ARE_NOT_EQUIVALENT",
                         records["correspondence"]["digest_equivalence"])
        self.assertEqual(records["evidence"],
                         validate_evidence_snapshot(records["evidence"]))
        self.assertEqual(records["use"],
                         validate_current_use_snapshot(records["use"]))
        self.assertEqual(records["decision"], validate_admissibility_decision(
            records["decision"],
            current_use_snapshot=records["use"],
            evidence_snapshot=records["evidence"],
            jurisdiction_profile=records["profile"],
            enforcement_perimeter=records["perimeter"],
            correspondence=records["correspondence"],
            **records["anchors"],
        ))
        self.assertEqual("ADMIT", records["decision"]["decision"])
        self.assertFalse(records["decision"]["effect_authorized"])
        self.assertEqual("SEPARATE_GATEWAY_AUTHORIZATION_REQUIRED",
                         records["decision"]["gateway_disposition"])
        self.assertEqual(records["projection"],
                         validate_admissibility_projection(
                             records["projection"],
                             decision=records["decision"],
                             current_use_snapshot=records["use"],
                             evidence_snapshot=records["evidence"],
                             jurisdiction_profile=records["profile"],
                             enforcement_perimeter=records["perimeter"],
                             correspondence=records["correspondence"],
                             **records["anchors"]))
        self.assertEqual("Can I use this now?",
                         records["projection"]["question"])
        self.assertEqual("YES_SUBJECT_TO_SEPARATE_GATEWAY_AUTHORIZATION",
                         records["projection"]["answer"])
        self.assertFalse(records["projection"]["projection_is_authority"])

    def test_same_identities_can_receive_a_new_present_decision(self) -> None:
        admitted = fixture()
        revoked = fixture(snapshot_id="ccp.snapshot.revoked",
                          revocation_status="REVOKED")
        self.assertEqual(admitted["use"]["state_identity_root"],
                         revoked["use"]["state_identity_root"])
        self.assertEqual(admitted["use"]["semantic_identity_root"],
                         revoked["use"]["semantic_identity_root"])
        self.assertEqual("ADMIT", admitted["decision"]["decision"])
        self.assertEqual("REFUSE", revoked["decision"]["decision"])
        self.assertIn("AUTHENTICATED_REVOCATION",
                      revoked["decision"]["reason_codes"])
        self.assertTrue(revoked["decision"]["historical_identities_unchanged"])
        self.assertEqual("NO_REFUSED", revoked["projection"]["answer"])

    def test_complete_records_express_defer_and_unresolved_without_effect(self) -> None:
        deferred = fixture(snapshot_id="ccp.snapshot.deferred",
                           revocation_status="UNAVAILABLE")
        unresolved = fixture(snapshot_id="ccp.snapshot.unresolved",
                             unresolved_requirements=["CHC_NATIVE_PROFILE_BINDING"])
        self.assertEqual("DEFER", deferred["decision"]["decision"])
        self.assertEqual("UNRESOLVED", unresolved["decision"]["decision"])
        self.assertFalse(deferred["decision"]["effect_authorized"])
        self.assertFalse(unresolved["decision"]["effect_authorized"])
        self.assertEqual("NOT_YET_CURRENT_EVIDENCE_REQUIRED",
                         deferred["projection"]["answer"])
        self.assertEqual("NOT_DETERMINED_UNRESOLVED_RULES",
                         unresolved["projection"]["answer"])

    def test_statuses_are_derived_from_bound_evidence_rows(self) -> None:
        stale = fixture(snapshot_id="ccp.snapshot.schema-stale",
                        schema_status="STALE")
        self.assertEqual("STALE", stale["evidence"]["statuses"]["schema"])
        schema_id = stale["evidence"]["status_evidence_ids"]["schema"]
        schema_row = next(row for row in stale["evidence"]["evidence"]
                          if row["evidence_id"] == schema_id)
        self.assertLess(schema_row["valid_until_epoch"],
                        stale["evidence"]["authenticated_epoch"])
        self.assertEqual("DEFER", stale["decision"]["decision"])
        self.assertIn("SCHEMA_STATE_STALE", stale["decision"]["reason_codes"])


if __name__ == "__main__":
    unittest.main()

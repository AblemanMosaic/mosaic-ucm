"""Positive construction tests only; adversarial cases live in the operator kit."""
from __future__ import annotations

import base64
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uclop.canonical import root
from ucm.amcas import BOUNDARY
from ucm.artifacts import deterministic_zip
from ucm.capabilities import invoke
from ucm.stage3 import instruction, plan_template
from ucm.stage4 import (AUTHORITY_SCHEMA, G1_SCHEMA, G2_SCHEMA, G3_SCHEMA,
    OBSERVATION_SCHEMA, REVIEW_ARCHIVE_ROLE, REVIEW_ARCHIVE_SCHEMA,
    REVIEW_POLICY_ID, REVIEW_SCHEMA, build_run_contract, derive_eligibility,
    validate_observation)


class StageI4C2PositiveTests(unittest.TestCase):
    def setUp(self):
        self.instruction = instruction(application={"id": "APP.ONE", "thread_id": "thread-one"},
            pipeline_release_sha256="1" * 64, predecessor_portfolio_sha256="2" * 64,
            portfolio_status_root="3" * 64, preflight_root="4" * 64,
            court_root="5" * 64, court_evidence_sha256="6" * 64,
            stage_i1_artifact_sha256="7" * 64, stage_i2_artifact_sha256="8" * 64,
            stage_i1_status="READY_FOR_REVIEW", matched_relations=[])
        self.plan = plan_template(self.instruction)
        self.plan["capability_projections"] = [{"capability_id": "CAP.ONE",
            "native_route": "native.one", "ucm_projection": "shadow.one",
            "effect_class": "READ_ONLY", "input_schema_root": "a" * 64,
            "output_schema_root": "b" * 64, "control_plane_disposition": "RETAIN",
            "case_ids": ["CASE.ONE"]}]
        self.plan["correspondence_cases"] = [{"id": "CASE.ONE",
            "capability_id": "CAP.ONE", "input_root": "c" * 64,
            "expected_native_decision": "PASS", "expected_ucm_decision": "PASS",
            "expected_native_result_root": "d" * 64,
            "expected_ucm_result_root": "d" * 64, "expected_equivalence": True,
            "evidence_requirements": ["NATIVE_RESULT", "UCM_RESULT"]}]
        self.plan["plan_root"] = root({k: v for k, v in self.plan.items() if k != "plan_root"})
        review_body = {"schema": REVIEW_SCHEMA, "review_class": "INDEPENDENT_REVIEW",
            "reviewer_policy_id": REVIEW_POLICY_ID, "reviewer_identity_root": "e" * 64,
            "reviewed_subject_root": "f" * 64, "reviewed_qualification_root": "1" * 64,
            "reviewed_source_root": "2" * 64,
            "applications": [{"application_id": "APP.ONE",
                "instruction_root": self.instruction["instruction_root"],
                "plan_root": self.plan["plan_root"]}],
            "verdict": "QUALIFIED_RECOMMENDATION_ONLY", "findings": [],
            "limitations": [], **BOUNDARY}
        disposition = {**review_body, "disposition_root": root(review_body)}
        self.review = deterministic_zip({"REVIEW-DISPOSITION.json":
            __import__("uclop.canonical", fromlist=["canonical_bytes"]).canonical_bytes(disposition)},
            schema=REVIEW_ARCHIVE_SCHEMA, artifact_role=REVIEW_ARCHIVE_ROLE)

    def _contracts(self):
        eligibility = derive_eligibility(instruction=self.instruction, plan=self.plan,
                                         review_archive=self.review)
        contract = build_run_contract(eligibility=eligibility, plan=self.plan,
            instruction=self.instruction, review_archive=self.review)
        return eligibility, contract

    def test_exact_review_derives_eligibility_and_run_contract(self):
        eligibility, contract = self._contracts()
        self.assertTrue(eligibility["eligible_for_shadow_execution"])
        self.assertEqual(contract["case_schedule"][0]["effect_class"], "READ_ONLY")
        self.assertFalse(contract["execution_authorized"])

    def test_complete_expected_observation_validates(self):
        eligibility, contract = self._contracts()
        g1_body = {"schema": G1_SCHEMA, "run_contract_root": contract["run_contract_root"],
            "application_id": "APP.ONE", "case_ids": ["CASE.ONE"],
            "capability_ids": ["CAP.ONE"], "effect_classes": ["READ_ONLY"],
            "policy_id": "UCM.INTEGRATION.G1.v1", "generation": 1,
            "decision": "ALLOW", "reason_codes": ["BOUNDED_REHEARSAL"],
            "rollback_root": "3" * 64, "budget_root": "4" * 64, **BOUNDARY}
        g1 = {**g1_body, "g1_root": root(g1_body)}
        case_result = {"case_id": "CASE.ONE", "native_decision": "PASS",
            "ucm_decision": "PASS", "native_result_root": "d" * 64,
            "ucm_result_root": "d" * 64}
        g2_body = {"schema": G2_SCHEMA, "run_contract_root": contract["run_contract_root"],
            "g1_root": g1["g1_root"], "application_id": "APP.ONE",
            "case_results": [case_result], "observed_effect_classes": ["READ_ONLY"],
            "output_roots": ["d" * 64], "recovery_status": "NOT_REQUIRED",
            "completion_status": "COMPLETE", **BOUNDARY}
        g2 = {**g2_body, "g2_root": root(g2_body)}
        g3_body = {"schema": G3_SCHEMA, "run_contract_root": contract["run_contract_root"],
            "g2_root": g2["g2_root"], "application_id": "APP.ONE",
            "classification": "PASS", "finding_codes": [], "next_action": "PRESERVE_EVIDENCE",
            **BOUNDARY}
        g3 = {**g3_body, "g3_root": root(g3_body)}
        authority_body = {"schema": AUTHORITY_SCHEMA,
            "run_contract_root": contract["run_contract_root"],
            "issuer_policy_id": "UCM.AUTHORITY.CEILING.v1", "scope": "SHADOW_REHEARSAL",
            "generation": 1, "authorized": False, "reason_code": "AUTHORITY_CEILING_NONE",
            **BOUNDARY}
        authority = {**authority_body, "authority_root": root(authority_body)}
        observation_body = {"schema": OBSERVATION_SCHEMA, "application_id": "APP.ONE",
            "run_contract_root": contract["run_contract_root"],
            "case_observations": [{**case_result, "pairwise_equivalent": True,
                "native_expected_conformant": True, "ucm_expected_conformant": True}],
            "g1_sentinel": g1, "g2_witness": g2, "g3_diagnostic": g3,
            "observed_effect_classes": ["READ_ONLY"], "pairwise_status": "EQUIVALENT",
            "expected_conformance_status": "CONFORMANT", "comparison_status": "PASS",
            "execution_authority": authority, **BOUNDARY}
        observation = {**observation_body, "observation_root": root(observation_body)}
        checked = validate_observation(observation, expected_run_contract=contract,
            expected_eligibility=eligibility, expected_plan=self.plan,
            expected_instruction=self.instruction, expected_review_archive=self.review)
        self.assertEqual(checked["comparison_status"], "PASS")

    def test_agent_surfaces_match_direct_interfaces(self):
        direct, contract = self._contracts()
        encoded = base64.b64encode(self.review).decode("ascii")
        stage3 = invoke({"schema": "mosaic.ucm.request.v0.1",
            "surface": "VALIDATE_STAGE_I3_PLAN",
            "payload": {"instruction": self.instruction, "plan": self.plan},
            "request_id": "stage3-positive"})
        derived = invoke({"schema": "mosaic.ucm.request.v0.1",
            "surface": "DERIVE_STAGE_I4_ELIGIBILITY",
            "payload": {"instruction": self.instruction, "plan": self.plan,
                        "review_archive_base64": encoded},
            "request_id": "stage4-positive"})
        validated = invoke({"schema": "mosaic.ucm.request.v0.1",
            "surface": "VALIDATE_STAGE_I4_RUN_CONTRACT",
            "payload": {"instruction": self.instruction, "plan": self.plan,
                "eligibility": direct, "run_contract": contract,
                "review_archive_base64": encoded}, "request_id": "run-positive"})
        self.assertEqual(stage3["result"]["plan_root"], self.plan["plan_root"])
        self.assertEqual(derived["result"], direct)
        self.assertEqual(validated["result"], contract)


if __name__ == "__main__":
    unittest.main()

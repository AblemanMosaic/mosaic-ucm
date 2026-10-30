from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uclop.canonical import root
from ucm.amcas import BOUNDARY
from ucm.stage3 import instruction, plan_template, validate_plan


class StageI3Tests(unittest.TestCase):
    def setUp(self):
        self.instruction = instruction(
            application={"id": "APP.ONE", "thread_id": "thread-one"},
            pipeline_release_sha256="1" * 64,
            predecessor_portfolio_sha256="2" * 64,
            portfolio_status_root="3" * 64, preflight_root="4" * 64,
            court_root="5" * 64, court_evidence_sha256="6" * 64,
            stage_i1_artifact_sha256="7" * 64,
            stage_i2_artifact_sha256="8" * 64,
            stage_i1_status="READY_FOR_REVIEW",
            matched_relations=[{"provider_application_id": "APP.TWO",
                "consumer_application_id": "APP.ONE", "interface_id": "IFACE.V1",
                "schema_root": "9" * 64, "required": False, "status": "MATCHED"}])
        self.plan = plan_template(self.instruction)
        self.plan["relation_dispositions"][0].update(
            {"disposition": "HOLD", "reason": "PAYLOAD_CONTRACT_REQUIRED"})
        self.plan["capability_projections"] = [{
            "capability_id": "CAP.ONE", "native_route": "native.one",
            "ucm_projection": "shadow.one", "effect_class": "READ_ONLY",
            "input_schema_root": "a" * 64, "output_schema_root": "b" * 64,
            "control_plane_disposition": "RETAIN", "case_ids": ["CASE.ONE"]}]
        self.plan["correspondence_cases"] = [{
            "id": "CASE.ONE", "capability_id": "CAP.ONE", "input_root": "c" * 64,
            "expected_native_decision": "PASS", "expected_ucm_decision": "PASS",
            "expected_native_result_root": "d" * 64,
            "expected_ucm_result_root": "d" * 64, "expected_equivalence": True,
            "evidence_requirements": ["NATIVE_RESULT", "UCM_RESULT"]}]
        self._reroot()

    def _reroot(self):
        self.plan["plan_root"] = root({key: value for key, value in self.plan.items()
                                       if key != "plan_root"})

    def test_valid_plan_is_planning_only(self):
        checked = validate_plan(self.plan, expected_instruction=self.instruction)
        self.assertFalse(checked["shadow_execution_requested"])
        self.assertEqual({key: checked[key] for key in BOUNDARY}, BOUNDARY)

    def test_result_root_divergence_refuses(self):
        self.plan["correspondence_cases"][0]["expected_ucm_result_root"] = "e" * 64
        self._reroot()
        with self.assertRaisesRegex(ValueError, "STAGE_I3_EXPECTED_RESULT_DIVERGENCE"):
            validate_plan(self.plan, expected_instruction=self.instruction)

    def test_missing_instruction_evidence_refuses(self):
        self.plan["required_evidence_roots"].remove(
            self.instruction["pipeline_release_sha256"])
        self._reroot()
        with self.assertRaisesRegex(ValueError, "STAGE_I3_REQUIRED_EVIDENCE_MISSING"):
            validate_plan(self.plan, expected_instruction=self.instruction)

    def test_missing_relation_refuses(self):
        self.plan["relation_dispositions"] = []
        self._reroot()
        with self.assertRaisesRegex(ValueError, "STAGE_I3_RELATION_COVERAGE_INVALID"):
            validate_plan(self.plan, expected_instruction=self.instruction)

    def test_uncovered_case_refuses(self):
        extra = deepcopy(self.plan["correspondence_cases"][0])
        extra["id"] = "CASE.TWO"
        extra["input_root"] = "e" * 64
        self.plan["correspondence_cases"].append(extra)
        self._reroot()
        with self.assertRaisesRegex(ValueError, "STAGE_I3_CAPABILITY_CASE_COVERAGE_INVALID"):
            validate_plan(self.plan, expected_instruction=self.instruction)

    def test_case_owned_by_wrong_projection_refuses(self):
        duplicate = deepcopy(self.plan["capability_projections"][0])
        duplicate["capability_id"] = "CAP.TWO"
        duplicate["case_ids"] = ["CASE.TWO"]
        self.plan["capability_projections"].append(duplicate)
        extra = deepcopy(self.plan["correspondence_cases"][0])
        extra["id"] = "CASE.TWO"
        extra["input_root"] = "e" * 64
        self.plan["correspondence_cases"].append(extra)
        self._reroot()
        with self.assertRaisesRegex(ValueError, "STAGE_I3_CAPABILITY_CASE_OWNERSHIP_INVALID"):
            validate_plan(self.plan, expected_instruction=self.instruction)

    def test_duplicate_relation_disposition_refuses(self):
        self.plan["relation_dispositions"].append(
            deepcopy(self.plan["relation_dispositions"][0]))
        self._reroot()
        with self.assertRaisesRegex(ValueError, "STAGE_I3_RELATION_DISPOSITION_DUPLICATE"):
            validate_plan(self.plan, expected_instruction=self.instruction)

    def test_execution_request_refuses(self):
        self.plan["shadow_execution_requested"] = True
        self._reroot()
        with self.assertRaisesRegex(ValueError, "STAGE_I3_PLAN_AUTHORITY_INVALID"):
            validate_plan(self.plan, expected_instruction=self.instruction)

    def test_inherited_hold_cannot_be_cleared(self):
        held_instruction = instruction(
            application={"id": "APP.HELD", "thread_id": "thread-held"},
            pipeline_release_sha256="1" * 64,
            predecessor_portfolio_sha256="2" * 64,
            portfolio_status_root="3" * 64, preflight_root="4" * 64,
            court_root="5" * 64, court_evidence_sha256="6" * 64,
            stage_i1_artifact_sha256="7" * 64,
            stage_i2_artifact_sha256="8" * 64,
            stage_i1_status="HOLD_FOR_REPAIR", matched_relations=[])
        held = plan_template(held_instruction)
        held["plan_status"] = "NO_APPLICABLE_SHADOW_ROUTE"
        held["holds"] = []
        held["plan_root"] = root({key: value for key, value in held.items()
                                  if key != "plan_root"})
        with self.assertRaisesRegex(ValueError, "STAGE_I3_INHERITED_HOLD_LOST"):
            validate_plan(held, expected_instruction=held_instruction)


if __name__ == "__main__":
    unittest.main()

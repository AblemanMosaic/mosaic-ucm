from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import Refusal
from ucm.realization import project_to_ucl_tessera, select_configuration, trace_preservation, validate_configuration, validate_contract


class RealizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads((ROOT / "examples/realization/portable-agent-environment.json").read_text(encoding="utf-8"))
        cls.configuration = json.loads((ROOT / "examples/realization/portable-agent-environment.configuration.json").read_text(encoding="utf-8"))

    def test_contract_and_configuration_validate(self):
        contract = validate_contract(self.contract)
        result = validate_configuration(contract, self.configuration)
        self.assertEqual(result["status"], "PASS_ADMISSIBLE")
        self.assertTrue(all(row["status"] == "PASS" for row in result["constraint_checks"]))
        self.assertEqual(result["authority_effect"], "NONE")

    def test_selection_is_deterministic(self):
        other = {**self.configuration, "TARGET_ISA": "ARM64"}
        one = select_configuration(self.contract, [self.configuration, other])
        two = select_configuration(self.contract, [other, self.configuration])
        self.assertEqual(one, two)
        self.assertEqual(one["policy"], "EXACT_DEFAULTS")
        self.assertEqual(one["selected_configuration"], self.configuration)
        self.assertEqual(len(one["candidate_set_root"]), 64)

    def test_hard_constraint_is_evaluated_before_admissible(self):
        invalid = {**self.configuration, "NETWORK_BOOTSTRAP": "ETHERNET_LOCAL_ONLY", "SELF_HOSTED_AGENT": True}
        result = validate_configuration(self.contract, invalid)
        self.assertEqual(result["status"], "REFUSED_INADMISSIBLE")
        failed = [row for row in result["constraint_checks"] if row["status"] == "FAIL"]
        self.assertEqual([row["constraint_id"] for row in failed], ["ETHERNET_PRECEDES_SELF_HOSTING"])

    def test_objective_policy_uses_declared_metric_and_commits_candidate_set(self):
        contract = json.loads(json.dumps(self.contract))
        contract["selection"] = {
            "default_policy": "OBJECTIVE_PRIORITY",
            "policies": ["OBJECTIVE_PRIORITY"],
            "seed_required_for_non_unique": False,
            "fallback_policy": "REFUSE",
        }
        other = {**self.configuration, "TARGET_ISA": "ARM64"}
        result = select_configuration(contract, [
            {"configuration": self.configuration, "metrics": {"ARTIFACT_BYTES": 20}},
            {"configuration": other, "metrics": {"ARTIFACT_BYTES": 10}},
        ])
        self.assertEqual(result["selected_configuration"], other)
        self.assertEqual(result["objective_order"], ["ARTIFACT_BYTES"])

    def test_out_of_domain_and_authority_broadening_refuse(self):
        with self.assertRaises(Refusal):
            validate_configuration(self.contract, {**self.configuration, "MEMORY_MIB": 1})
        bad = json.loads(json.dumps(self.contract))
        bad["authority"]["authority_effect"] = "DEPLOY"
        with self.assertRaises(Refusal):
            validate_contract(bad)

    def test_unsupported_axis_semantics_refuse(self):
        bad = json.loads(json.dumps(self.contract))
        bad["axes"][0]["value_type"] = "VECTOR"
        with self.assertRaises(Refusal) as caught:
            validate_contract(bad)
        self.assertEqual(caught.exception.code, "RSC_AXIS_TYPE_UNSUPPORTED")

    def test_optional_schema_fields_are_typed(self):
        mutations = [
            (("description",), 1),
            (("subject", "coordinate_frame"), "frame"),
            (("axes", 0, "ui_hint"), []),
            (("objectives", 0, "unit"), []),
            (("lowering", "targets", 0, "runtime_family"), "lowercase"),
            (("revision", "predecessor_root"), "not-a-root"),
            (("authority", "claim_boundary"), []),
        ]
        for path, value in mutations:
            with self.subTest(path=path):
                item = json.loads(json.dumps(self.contract))
                if path[0] == "revision":
                    item["revision"] = {}
                target = item
                for part in path[:-1]:
                    target = target[part]
                target[path[-1]] = value
                with self.assertRaises(Refusal):
                    validate_contract(item)

    def test_projection_and_trace_state_their_nonclaims(self):
        projection = project_to_ucl_tessera(self.contract)
        self.assertIn("NOT_A_COMPILATION", projection["non_claims"])
        trace = trace_preservation(self.contract, self.configuration, self.configuration)
        self.assertIn("NOT_A_COMPILER_PROOF", trace["non_claims"])


if __name__ == "__main__":
    unittest.main()


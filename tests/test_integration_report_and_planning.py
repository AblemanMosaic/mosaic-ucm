from __future__ import annotations

import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uclop.canonical import root
from ucm.integration import IntegrationCampaign
from ucm.planning import prepare_plan

from _amcas_helpers import contract


class ReportAndPlanningTests(unittest.TestCase):
    def test_import_bound_session_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            campaign = IntegrationCampaign.create(Path(temporary) / "campaign", contract())
            compiled = campaign.compiled()
            rows = [{"obligation_id": item["id"], "status": "PASS",
                     "evidence_roots": ["a" * 64]} for item in compiled["obligations"]]
            body = {"schema": "mosaic.ucm.session-integration-report.v0.1",
                    "contract_root": campaign.contract()["contract_root"],
                    "ir_root": compiled["ir_root"], "session_mosaic_id": "b" * 64,
                    "source_root_observed": campaign.contract()["subject"]["source_root"],
                    "requirement_dispositions": rows, "operation_summaries": [],
                    "findings": [], "artifacts": [], "limitations": [],
                    "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
                    "real_a5": False, "g0": "CLOSED"}
            result = campaign.import_session_report({**body, "report_root": root(body)},
                                                    event_id_prefix="session-a")
            self.assertEqual(result["status"], "PASS_IMPORTED")
            self.assertTrue(campaign.status()["ready_for_review"])

    def test_planner_exposes_unresolved_and_disables_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            campaign = IntegrationCampaign.create(Path(temporary) / "campaign", contract())
            plan = prepare_plan(campaign, changed_paths=["src/new_runtime.py"],
                                objective="Integrate exact application bytes")
            self.assertFalse(plan["execution_authorized"])
            self.assertEqual(plan["impact"]["lane"], "QUALIFICATION")
            self.assertTrue(any(row["kind"] == "OBLIGATION" for row in plan["tasks"]))


if __name__ == "__main__":
    unittest.main()

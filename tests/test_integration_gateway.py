import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uclop.canonical import Refusal
from ucm.integration import IntegrationCampaign
from _amcas_helpers import contract, operation


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.campaign = IntegrationCampaign.create(Path(self.temp.name) / "campaign", contract(effect=True))

    def tearDown(self):
        self.temp.cleanup()

    def test_three_gate_sequence_and_thr_dimensions(self):
        planned = self.campaign.plan_operation(operation(), event_id="plan")
        self.assertFalse(planned["sentinel"]["execution_authorized"])
        for field in ("H_s", "H_c", "H_m", "H_j", "H_r", "h_body"):
            self.assertEqual(len(planned["sentinel"][field]), 64)
        witness = {"operation_id": "OP-1", "outcome": "PASS",
            "observed_effects": ["LOCAL_ARTIFACT_PREPARATION"],
            "outputs": [{"path": "output.json", "sha256": "4" * 64}],
            "terminal_capture": {"stdout_sha256": hashlib.sha256(b"ok").hexdigest(),
                                 "stderr_sha256": hashlib.sha256(b"").hexdigest(), "exit_code": 0},
            "recovery_required": False}
        self.campaign.record_witness(witness, event_id="witness")
        result = self.campaign.record_diagnostic({"operation_id": "OP-1",
            "classification": "SUCCESS", "finding_ids": [], "acceptance": "READY_FOR_REVIEW",
            "next_action": "Review the exact output."}, event_id="diagnostic")
        self.assertEqual(result["diagnostic"]["constitutional_acceptance"], "NOT_GRANTED")
        self.assertEqual(self.campaign.status()["open_operations"], [])

    def test_undeclared_observed_effect_refuses(self):
        self.campaign.plan_operation(operation(), event_id="plan")
        witness = {"operation_id": "OP-1", "outcome": "PASS", "observed_effects": ["NETWORK"],
            "outputs": [], "terminal_capture": {"stdout_sha256": "0" * 64,
            "stderr_sha256": "0" * 64, "exit_code": 0}, "recovery_required": False}
        with self.assertRaises(Refusal):
            self.campaign.record_witness(witness, event_id="witness")


if __name__ == "__main__":
    unittest.main()

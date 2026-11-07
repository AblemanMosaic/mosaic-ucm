from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, strict_loads
from ucm.ecosystem_returns import build_return_index, receive_session_return


class EcosystemSessionReturnTests(unittest.TestCase):
    def test_exact_return_is_received_without_trusting_inner_claims(self):
        dispatch = strict_loads((ROOT / "integration" /
            "ECOSYSTEM-SESSION-DISPATCH.json").read_bytes())
        result = receive_session_return(
            dispatch, application_id="MOSAIC.AAC",
            artifact_raw=b'{"status":"HOLD_FOR_REPAIR"}',
            artifact_filename="AAC-RETURN.json", claimed_status="HOLD_FOR_REPAIR")
        self.assertEqual(result["integration_status"], "RECEIVED_UNVERIFIED")
        self.assertEqual(result["content_review_status"], "PENDING")
        self.assertEqual(result["prior_plan_status"], "HOLD_FOR_REPAIR")
        self.assertEqual(result["hold_clearance"], "NOT_ESTABLISHED")
        self.assertEqual(result["authority_effect"], "NONE")

    def test_incomplete_return_is_recorded_without_becoming_completion(self):
        dispatch = strict_loads((ROOT / "integration" /
            "ECOSYSTEM-SESSION-DISPATCH.json").read_bytes())
        result = receive_session_return(
            dispatch, application_id="MOSAIC.MESSENGER_CRYSTAL",
            artifact_raw=b'{"status":"INCOMPLETE_RETURN"}',
            artifact_filename="INCOMPLETE_RETURN.json",
            claimed_status="INCOMPLETE_RETURN")
        self.assertEqual(result["claimed_status"], "INCOMPLETE_RETURN")
        self.assertEqual(result["integration_status"], "RECEIVED_UNVERIFIED")
        self.assertEqual(result["content_review_status"], "PENDING")
        self.assertEqual(result["hold_clearance"], "NOT_ESTABLISHED")
        self.assertEqual(result["application_execution_observed"],
                         "NOT_ESTABLISHED")

    def test_received_return_index_rebuilds_with_fixed_denominator(self):
        dispatch = strict_loads((ROOT / "integration" /
            "ECOSYSTEM-SESSION-DISPATCH.json").read_bytes())
        returns_dir = ROOT / "integration" / "session-returns"
        packages = {path.name: path.read_bytes() for path in returns_dir.glob("*.zip")}
        result = build_return_index(dispatch, packages)
        frozen = (ROOT / "integration" /
                  "ECOSYSTEM-SESSION-RETURN-INDEX.json").read_bytes()
        self.assertEqual(canonical_bytes(result), frozen)
        self.assertEqual(result["fixed_denominator"], 7)
        self.assertEqual(result["received_count"], len(packages))
        self.assertEqual(result["pending_count"], 7 - len(packages))
        aac = next(row for row in result["applications"]
                   if row["application_id"] == "MOSAIC.AAC")
        self.assertEqual(aac["return_status"], "RECEIVED_UNVERIFIED")
        self.assertEqual(aac["claimed_status"], "HOLD_FOR_REPAIR")
        self.assertEqual(aac["content_review_status"], "PENDING")
        memory = next(row for row in result["applications"]
                      if row["application_id"] == "MOSAIC.MEMORY_VAULT")
        self.assertEqual(memory["return_status"], "RECEIVED_UNVERIFIED")
        self.assertEqual(memory["claimed_status"], "READY_FOR_REVIEW")
        self.assertEqual(memory["content_review_status"], "PENDING")
        messenger = next(row for row in result["applications"]
                         if row["application_id"] == "MOSAIC.MESSENGER_CRYSTAL")
        self.assertEqual(messenger["claimed_status"], "INCOMPLETE_RETURN")
        self.assertEqual(messenger["return_status"], "RECEIVED_UNVERIFIED")
        modeler = next(row for row in result["applications"]
                       if row["application_id"] == "MOSAIC.2D_3D")
        self.assertEqual(modeler["claimed_status"], "DRIFT_RECORDED")
        media = next(row for row in result["applications"]
                     if row["application_id"] == "MOSAIC.MEDIA_CENTER")
        self.assertEqual(media["claimed_status"], "READY_FOR_REVIEW")
        reader = next(row for row in result["applications"]
                      if row["application_id"] == "MOSAIC.READER")
        self.assertEqual(reader["claimed_status"], "HOLD_FOR_REPAIR")
        self.assertEqual(reader["return_status"], "RECEIVED_UNVERIFIED")
        self.assertEqual(result["received_count"], 7)
        self.assertEqual(result["pending_count"], 0)


if __name__ == "__main__":
    unittest.main()

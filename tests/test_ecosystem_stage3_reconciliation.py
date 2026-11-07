import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, strict_loads
from ucm.ecosystem_reconciliation import reconcile_stage_i3


class EcosystemStageI3ReconciliationTests(unittest.TestCase):
    def test_frozen_reconciliation_rebuilds_exactly(self):
        roster = strict_loads((ROOT / "examples" / "portfolio" /
                               "MOSAIC-APPLICATIONS.json").read_bytes())
        application_ids = [row["id"] for row in roster["applications"]]
        baseline_raw = (ROOT / "integration" /
                        "ECOSYSTEM-INTEGRATION-BASELINE.json").read_bytes()
        result = reconcile_stage_i3(
            ROOT / "integration" / "stage-i3" / "authoring",
            ROOT / "integration" / "stage-i3" / "pipeline-bound",
            application_ids,
            strict_loads(baseline_raw),
            hashlib.sha256(baseline_raw).hexdigest(),
        )
        frozen = (ROOT / "integration" / "stage-i3" /
                  "STAGE-I3-REBIND-RECONCILIATION.json").read_bytes()
        self.assertEqual(canonical_bytes(result), frozen)
        self.assertEqual(result["fixed_denominator"], 7)
        self.assertEqual(result["semantic_changes"], 0)
        self.assertEqual(result["binding_only_changes"], 7)
        self.assertEqual(result["capability_projection_count"], 35)
        self.assertEqual(result["correspondence_case_count"], 96)
        self.assertEqual(result["relation_disposition_count"], 13)
        self.assertEqual(result["plan_status_counts"], {
            "READY_FOR_SHADOW_REVIEW": 4,
            "HOLD_FOR_REPAIR": 3,
        })
        self.assertTrue(all(row["holds_preserved"] for row in result["applications"]))
        self.assertFalse(result["stage_i3_shadow_authorized"])
        self.assertFalse(result["application_execution_observed"])

    def test_session_dispatch_is_exactly_pending_and_non_authorizing(self):
        reconciliation = strict_loads((ROOT / "integration" / "stage-i3" /
            "STAGE-I3-REBIND-RECONCILIATION.json").read_bytes())
        dispatch = strict_loads((ROOT / "integration" /
            "ECOSYSTEM-SESSION-DISPATCH.json").read_bytes())
        provenance = strict_loads((ROOT / "integration" / "stage-i3" /
            "PIPELINE-BOUND-REBIND-PROVENANCE.json").read_bytes())
        body = {key: value for key, value in dispatch.items() if key != "dispatch_root"}
        from uclop.canonical import root
        self.assertEqual(dispatch["dispatch_root"], root(body))
        # The dispatch is immutable historical custody.  Its seven returns bind
        # this predecessor root; the repaired v0.2 reconciliation is a
        # successor record and must not rewrite those already-received bytes.
        self.assertEqual(dispatch["reconciliation_root"],
                         provenance["predecessor_reconciliation_root"])
        self.assertEqual(provenance["successor_reconciliation_root"],
                         reconciliation["reconciliation_root"])
        self.assertEqual(dispatch["fixed_denominator"], 7)
        self.assertEqual({row["return_status"] for row in dispatch["applications"]},
                         {"PENDING"})
        self.assertEqual(sum(row["work_class"] == "READ_ONLY_STAGE_I4_PREPARATION"
                             for row in dispatch["applications"]), 4)
        self.assertEqual(sum(row["work_class"] == "STAGE_I3_REPAIR_ONLY"
                             for row in dispatch["applications"]), 3)
        self.assertFalse(dispatch["application_execution_authorized"])

    def test_pipeline_bound_generator_is_carried_exactly(self):
        archive = (ROOT / "review" / "unified-maturity" / "track-b" /
                   "HISTORICAL-STAGE-I3-PIPELINE-RELEASE-3c549fbc.zip")
        provenance = json.loads((ROOT / "integration" / "stage-i3" /
            "PIPELINE-BOUND-REBIND-PROVENANCE.json").read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),
                         provenance["historical_pipeline_release_sha256"])
        self.assertEqual(provenance["historical_release_custody"],
                         "CARRIED_EXACT_IN_QUALIFICATION_AND_REVIEW_HANDOFF")
        self.assertEqual(provenance["status"],
                         "PASS_HISTORICAL_GENERATOR_CUSTODY_CLOSED")


if __name__ == "__main__":
    unittest.main()

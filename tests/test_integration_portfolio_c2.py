from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uclop.canonical import root
from uclop.canonical import canonical_bytes
from ucm.amcas import BOUNDARY
from ucm.composition import declaration_template
from ucm.artifacts import deterministic_zip
from ucm.portfolio import PortfolioCampaign
from ucm.stage3 import validate_plan
from _integration_c2_helpers import stage1_bundle


class PortfolioTests(unittest.TestCase):
    @staticmethod
    def roster():
        body = {"schema": "mosaic.ucm.integration-portfolio.v0.1",
                "portfolio_id": "MOSAIC.APPLICATIONS",
                "applications": [{"id": "EXAMPLE.PORTABLE_AGENT", "name": "One",
                                  "thread_id": "thread-1", "kit": "ONE"}],
                **BOUNDARY}
        return {**body, "roster_root": root(body)}

    def test_fixed_denominator_intake_and_instruction(self):
        with tempfile.TemporaryDirectory() as directory:
            body = {"schema": "mosaic.ucm.integration-portfolio.v0.1",
                    "portfolio_id": "MOSAIC.APPLICATIONS",
                    "applications": [{"id": "APP.ONE", "name": "One",
                                      "thread_id": "thread-1", "kit": "ONE"}],
                    **BOUNDARY}
            roster = {**body, "roster_root": root(body)}
            campaign = PortfolioCampaign.create(Path(directory) / "portfolio", roster)
            campaign.record_intake({"schema": "mosaic.ucm.portfolio-intake.v0.1",
                "application_id": "APP.ONE", "thread_id": "thread-1",
                "response_sha256": "1" * 64, "subject_status": "SOURCE_BOUNDARY_REQUIRED",
                "subject_root": None}, event_id_prefix="app-one-intake")
            campaign.record_instruction({"schema": "mosaic.ucm.portfolio-instruction.v0.1",
                "application_id": "APP.ONE", "thread_id": "thread-1",
                "instruction_sha256": "2" * 64}, event_id_prefix="app-one-instruction")
            status = campaign.status()
            self.assertEqual(status["fixed_workflow_denominator"], 1)
            self.assertEqual(status["applications"][0]["intake"], "BOUND")
            self.assertEqual(status["applications"][0]["instruction"], "DELIVERED")
            self.assertFalse(status["ready_for_composition"])

    def test_stage1_import_stores_exact_cas_object_and_requires_thr(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            campaign = PortfolioCampaign.create(base / "portfolio", self.roster())
            bundle_workspace = base / "bundle"
            bundle_workspace.mkdir()
            raw, _ = stage1_bundle(bundle_workspace)
            imported = campaign.import_stage1(raw, event_id_prefix="stage-i1")
            self.assertEqual(imported["cas"]["status"], "STORED_VERIFIED")
            stored = campaign.workspace / imported["cas"]["path"]
            self.assertEqual(stored.read_bytes(), raw)
            status = campaign.status()
            self.assertTrue(status["ready_for_composition"])
            self.assertEqual(status["applications"][0]["thr"], "PASS_SEPARATED")

    def test_stage2_import_is_exact_cas_journaled_and_revisioned(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            campaign = PortfolioCampaign.create(base / "portfolio", self.roster())
            bundle_workspace = base / "bundle"; bundle_workspace.mkdir()
            raw, _ = stage1_bundle(bundle_workspace)
            campaign.import_stage1(raw, event_id_prefix="stage-i1")
            declaration = declaration_template(raw)
            declaration["declared_relations_status"] = "DECLARED_INFORMATION_ONLY"
            declaration["declaration_root"] = root({key: value for key, value in declaration.items()
                                                     if key != "declaration_root"})
            declaration_raw = canonical_bytes(declaration)
            first = campaign.import_stage2(declaration_raw, event_id_prefix="stage-i2-r1")
            self.assertEqual(first["revision"], 1)
            self.assertEqual((campaign.workspace / first["cas"]["path"]).read_bytes(), declaration_raw)
            second = campaign.import_stage2(declaration_raw, event_id_prefix="stage-i2-r2")
            self.assertEqual(second["revision"], 2)
            status = campaign.status()
            self.assertEqual(status["applications"][0]["stage_i2_revision"], 2)
            self.assertEqual(status["composition_preflight_status"],
                             "READY_FOR_CORRESPONDENCE_COURT")
            self.assertFalse(status["composition_authorized"])

    def test_stage2_preserves_noncanonical_source_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            campaign = PortfolioCampaign.create(base / "portfolio", self.roster())
            bundle_workspace = base / "bundle"; bundle_workspace.mkdir()
            raw, _ = stage1_bundle(bundle_workspace)
            campaign.import_stage1(raw, event_id_prefix="stage-i1")
            declaration = declaration_template(raw)
            source = (__import__("json").dumps(declaration, indent=2) + "\n").encode()
            imported = campaign.import_stage2(source, event_id_prefix="stage-i2")
            self.assertEqual((campaign.workspace / imported["cas"]["path"]).read_bytes(), source)

    def test_operator_court_is_bound_stored_and_never_authorizes_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            campaign = PortfolioCampaign.create(base / "portfolio", self.roster())
            bundle_workspace = base / "bundle"; bundle_workspace.mkdir()
            raw, _ = stage1_bundle(bundle_workspace)
            campaign.import_stage1(raw, event_id_prefix="stage-i1")
            declaration = declaration_template(raw)
            declaration["declared_relations_status"] = "DECLARED_INFORMATION_ONLY"
            declaration["declaration_root"] = root({key: value for key, value in declaration.items()
                                                     if key != "declaration_root"})
            campaign.import_stage2(canonical_bytes(declaration), event_id_prefix="stage-i2")
            preflight = campaign.composition_preflight()
            row = {"id": "baseline", "expected": "READY_UNAUTHORIZED",
                   "observed": "READY_FOR_CORRESPONDENCE_COURT", "status": "PASS"}
            body = {"schema": "mosaic.ucm.amcas-correspondence-court-result.v0.1",
                    "handoff_sha256": "a" * 64, "portfolio_sha256": "b" * 64,
                    "baseline": {"applications": 1, "matched_edges": 0,
                        "preflight_root": preflight["preflight_root"],
                        "preflight_status": preflight["status"],
                        "composition_authorized": False},
                    "rows": [row], "counts": {"PASS": 1, "FAIL": 0},
                    "status": "PASS", **BOUNDARY}
            result = {**body, "court_root": root(body)}
            evidence = deterministic_zip({
                "CORRESPONDENCE-COURT-RESULT.json": canonical_bytes(result),
                "REPORT.md": b"operator court\n",
                "RUN-CORRESPONDENCE-COURT.py": b"# fixed runner\n",
            }, schema="mosaic.ucm.amcas-correspondence-court-evidence.v0.1",
               artifact_role="UCM_AMCAS_CORRESPONDENCE_COURT_EVIDENCE")
            imported = campaign.import_correspondence_court(evidence,
                event_id_prefix="court-c1", expected_handoff_sha256="a" * 64,
                expected_portfolio_sha256="b" * 64)
            self.assertEqual(imported["court"]["claim"],
                             "OPERATOR_REPRODUCED_ADVERSARIAL_EVIDENCE")
            self.assertFalse(imported["court"]["independent_reviewer_authored"])
            status = campaign.status()
            self.assertEqual(status["correspondence_court"], "IMPORTED")
            self.assertTrue(status["ready_for_stage_i3_shadow_planning"])
            self.assertFalse(status["stage_i3_shadow_authorized"])
            self.assertFalse(status["composition_authorized"])

    def test_stage3_planning_is_fixed_denominator_bound_and_non_authorizing(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            campaign = PortfolioCampaign.create(base / "portfolio", self.roster())
            bundle_workspace = base / "bundle"; bundle_workspace.mkdir()
            raw, _ = stage1_bundle(bundle_workspace)
            campaign.import_stage1(raw, event_id_prefix="stage-i1")
            declaration = declaration_template(raw)
            declaration["declared_relations_status"] = "DECLARED_INFORMATION_ONLY"
            declaration["declaration_root"] = root({key: value for key, value in declaration.items()
                                                     if key != "declaration_root"})
            campaign.import_stage2(canonical_bytes(declaration), event_id_prefix="stage-i2")
            preflight = campaign.composition_preflight()
            court_body = {"schema": "mosaic.ucm.amcas-correspondence-court-result.v0.1",
                "handoff_sha256": "a" * 64, "portfolio_sha256": "b" * 64,
                "baseline": {"applications": 1, "matched_edges": 0,
                    "preflight_root": preflight["preflight_root"],
                    "preflight_status": preflight["status"],
                    "composition_authorized": False},
                "rows": [{"id": "bound", "expected": "PASS", "observed": "PASS",
                          "status": "PASS"}],
                "counts": {"PASS": 1, "FAIL": 0}, "status": "PASS", **BOUNDARY}
            court = {**court_body, "court_root": root(court_body)}
            evidence = deterministic_zip({
                "CORRESPONDENCE-COURT-RESULT.json": canonical_bytes(court),
                "REPORT.md": b"operator court\n", "RUN-CORRESPONDENCE-COURT.py": b"# runner\n"},
                schema="mosaic.ucm.amcas-correspondence-court-evidence.v0.1",
                artifact_role="UCM_AMCAS_CORRESPONDENCE_COURT_EVIDENCE")
            campaign.import_correspondence_court(evidence, event_id_prefix="court",
                expected_handoff_sha256="a" * 64, expected_portfolio_sha256="b" * 64)
            predecessor_status = campaign.status()
            snapshot = deterministic_zip({"PORTFOLIO-STATUS.json":
                canonical_bytes(predecessor_status)},
                schema="mosaic.ucm.amcas-integration-portfolio-snapshot.v0.4",
                artifact_role="PORTABLE_CANONICAL_INTEGRATION_PORTFOLIO")
            issued = campaign.issue_stage3_instructions(
                pipeline_release_sha256="c" * 64,
                predecessor_portfolio_raw=snapshot,
                predecessor_portfolio_sha256=__import__("hashlib").sha256(snapshot).hexdigest(),
                expected_status_root=predecessor_status["status_root"],
                event_id_prefix="stage-i3-issue")
            self.assertEqual(len(issued), 1)
            plan = issued[0]["template"]
            case_id = "EXAMPLE.SHADOW.CASE.1"
            plan["capability_projections"] = [{
                "capability_id": "EXAMPLE.CAPABILITY", "native_route": "native.route",
                "ucm_projection": "ucm.shadow.route", "effect_class": "PURE_COMPUTATION",
                "input_schema_root": "d" * 64, "output_schema_root": "e" * 64,
                "control_plane_disposition": "RETAIN", "case_ids": [case_id]}]
            plan["correspondence_cases"] = [{
                "id": case_id, "capability_id": "EXAMPLE.CAPABILITY",
                "input_root": "f" * 64, "expected_native_decision": "PASS",
                "expected_ucm_decision": "PASS", "expected_equivalence": True,
                "expected_native_result_root": "1" * 64,
                "expected_ucm_result_root": "1" * 64,
                "evidence_requirements": ["NATIVE_RESULT_ROOT", "UCM_RESULT_ROOT"]}]
            plan["next_action"] = "RETURN_FOR_STAGE_I3_SHADOW_REVIEW"
            plan["plan_root"] = root({key: value for key, value in plan.items()
                                      if key != "plan_root"})
            validate_plan(plan, expected_instruction=issued[0]["instruction"])
            imported = campaign.import_stage3_plan(canonical_bytes(plan),
                event_id_prefix="stage-i3-plan")
            self.assertEqual(imported["stage_i3"]["plan_status"],
                             "READY_FOR_SHADOW_REVIEW")
            status = campaign.status()
            self.assertTrue(status["stage_i3_instruction_denominator_complete"])
            self.assertTrue(status["stage_i3_plan_denominator_complete"])
            self.assertTrue(status["ready_for_stage_i3_shadow_review"])
            self.assertFalse(status["stage_i3_shadow_authorized"])
            self.assertFalse(status["composition_authorized"])


if __name__ == "__main__":
    unittest.main()

"""Positive common-turn workflow and real CLI/ABI construction exercises."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from uclop.canonical import canonical_bytes
from ucm.capabilities import invoke
from ucm.pippi_adaptive import build_turn_report, interface_conformance
from ucm.pippi_cmba import CMBA_WHEEL_SHA256, build_cmba_turn_assessment
from ucm.pippi_global import PippiHub, build_onboarding, build_project
from ucm.pippi_turn_record import build_turn_record
from ucm.pippi_turn_workflow import (build_turn_bundle, build_turn_submission, validate_turn_bundle,
    build_assessment_attachment, reconcile_common_turn, project_turn_history, turn_continuation_context)
from ucm.system import capability_registry
from test_pippi_turn_record_positive import common_turn_fixture


ROOT = Path(__file__).resolve().parents[1]


def invoke_surface(surface, payload):
    return invoke({"schema":"mosaic.ucm.request.v0.2","request_id":"positive:r034",
        "surface":surface,"payload":payload,"profile_selection":{
            "schema":"mosaic.ucm.product-profile-selection.v0.1","profile_id":"AUTHORING",
            "capability_registry_root":capability_registry()["root"]}})["result"]


class PippiTurnWorkflowPositiveTests(unittest.TestCase):
    def fixture(self):
        opening, report, details = common_turn_fixture()
        record = build_turn_record(opening=opening, report=report, **details)
        return opening, report, details, record

    def test_common_bundle_preserves_native_records_and_reporting_links(self):
        opening, report, details, record = self.fixture()
        request = {"opening":opening, **{key:report[key] for key in (
            "summary","changed_paths","artifact_roots","evidence_roots","unresolved_items","next_action","claim_class")},
            "turn_details":details}
        bundle = build_turn_submission(request)
        self.assertEqual(bundle["report"], report)
        self.assertEqual(bundle["turn_record"], record)
        self.assertEqual(validate_turn_bundle(bundle), bundle)

    def test_legacy_reporting_projects_unknown_information_without_rewriting(self):
        opening, report, _, _ = self.fixture()
        request = {"opening":opening, **{key:report[key] for key in (
            "summary","changed_paths","artifact_roots","evidence_roots","unresolved_items","next_action","claim_class")}}
        bundle = build_turn_submission(request)
        self.assertEqual(bundle["report"],report)
        self.assertEqual(bundle["turn_record"]["status"],"NEEDS_INFORMATION")
        self.assertFalse(bundle["turn_record"]["acceptance_case_closed"])

    def test_all_new_surfaces_are_registered_and_publicly_invocable(self):
        opening, report, details, record = self.fixture()
        self.assertEqual(invoke_surface("BUILD_PIPPI_TURN_RECORD",{"opening":opening,"report":report,**details}),record)
        projection = invoke_surface("PROJECT_PIPPI_TURN_RECORD",{"value":record,"opening":opening,"report":report,"view":"HUMAN"})
        self.assertEqual(projection["turn_record_root"],record["turn_record_root"])
        requirement=invoke_surface("DISCOVER_PIPPI_TURN_REQUIREMENTS",{"scenario":opening["scenario"]})
        self.assertFalse(requirement["per_tool_interception_required"])
        assessment=invoke_surface("ASSESS_PIPPI_CMBA_TURN",{"opening":opening,"report":report,
            "turn_record":record,"expected_wheel_sha256":CMBA_WHEEL_SHA256})
        verified=invoke_surface("VERIFY_PIPPI_CMBA_TURN",{"value":assessment,"opening":opening,
            "report":report,"turn_record":record,"expected_wheel_sha256":CMBA_WHEEL_SHA256})
        self.assertEqual(assessment,verified)
        self.assertEqual(interface_conformance()["status"],"PASS")

    def test_hub_history_and_continuation_share_existing_journal(self):
        opening, report, _, record = self.fixture()
        with tempfile.TemporaryDirectory(prefix="ucm-r034-hub-positive-", dir=ROOT.parent) as tmp:
            hub=PippiHub(Path(tmp));hub.initialize(build_onboarding(governor_label="positive-construction",
                mosaic_id=None,dkn_public_key=None,github_account=None,github_credential_reference=None))
            # The project supplied by the fixture is exactly reproducible.
            project=build_project(project_id=opening["project_id"],title="P/PPI",
                workspace=str(ROOT),github_url=None,application_command=["pippi","dashboard"],
                verification_command=["pippi","interface-doctor"],revision="r034")
            self.assertEqual(project["project_root"],opening["project_root"])
            hub.add_project(project)
            hub.store_project_record(project_id=project["project_id"],record_kind="opening",record=opening,
                root_field="turn_opening_root",event_type="TURN_OPENED")
            bundle=build_turn_bundle(opening=opening,report=report,turn_record=record)
            saved=hub.store_project_record(project_id=project["project_id"],record_kind="turn-record",record=bundle,
                root_field="turn_bundle_root",event_type="TURN_RECORD_SUBMITTED")
            again=hub.store_project_record(project_id=project["project_id"],record_kind="turn-record",record=bundle,
                root_field="turn_bundle_root",event_type="TURN_RECORD_SUBMITTED")
            self.assertTrue(again["idempotent_replay"])
            self.assertEqual(saved["hub_event_root"],again["hub_event_root"])
            self.assertEqual(turn_continuation_context(hub,project["project_id"])["status"],"PREVIOUS_TURN_CLOSE_REQUIRED")
            history=project_turn_history(hub,project["project_id"])
            self.assertEqual(history["record_count"],1)
            self.assertTrue(history["records"][0]["journal_committed"])
            result=reconcile_common_turn(opening=opening,report=report,turn_record=record,
                current_project_root=project["project_root"],current_journal_head=opening["journal_head"])
            hub.store_project_record(project_id=project["project_id"],record_kind="reconciliation",record=result,
                root_field="reconciliation_root",event_type="TURN_RECONCILED")
            self.assertEqual(turn_continuation_context(hub,project["project_id"])["status"],"READY")
            self.assertEqual(hub.verify()["status"],"PASS")

    def test_actual_cmba_assessment_is_verified_before_journal_attachment(self):
        opening,report,_,record=self.fixture()
        assessment=build_cmba_turn_assessment(opening=opening,report=report,turn_record=record,
            expected_wheel_sha256=CMBA_WHEEL_SHA256)
        attachment=build_assessment_attachment(opening=opening,report=report,turn_record=record,
            assessment=assessment,expected_wheel_sha256=CMBA_WHEEL_SHA256)
        self.assertEqual(attachment["assessment"],assessment)
        self.assertFalse(attachment["acceptance_case_closed"])

    def test_cli_read_only_surface_uses_carried_source_without_initializing_hub(self):
        opening,report,details,_=self.fixture()
        with tempfile.TemporaryDirectory(prefix="ucm-r034-cli-positive-", dir=ROOT.parent) as tmp:
            base=Path(tmp);request=base/"request.json"
            request.write_bytes(canonical_bytes({"opening":opening,"report":report,**details})+b"\n")
            script="import sys,runpy;sys.path.insert(0,sys.argv.pop(1));runpy.run_module('ucm.pippi_cli',run_name='__main__')"
            run=subprocess.run([sys.executable,"-I","-B","-X","utf8","-c",script,str(ROOT/"src"),
                "--data-root",str(base/"hub"),"turn-record-build",str(request)],capture_output=True,check=True)
            value=json.loads(run.stdout)
            self.assertEqual(value["turn_opening_root"],opening["turn_opening_root"])
            self.assertFalse((base/"hub").exists())


if __name__ == "__main__":
    unittest.main()

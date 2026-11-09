from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from ucm.pippi import build_pippi_context
from ucm.pippi_global import HubRefusal, PippiHub, build_onboarding, build_project
from ucm.pippi_portfolio import (
    PortfolioStore,
    build_preferences,
    build_project_brief,
    build_project_profile,
    build_timeline,
    discover_campaigns,
)
from ucm.pippi_runtime import PippiCampaign
from ucm.pippi_service import dispatch_read


ROOT = Path(__file__).resolve().parents[1]
R = "1" * 64


class PippiPortfolioTests(unittest.TestCase):
    @staticmethod
    def temporary():
        return tempfile.TemporaryDirectory()

    @staticmethod
    def onboarding():
        return build_onboarding(
            governor_label="local-governor",
            mosaic_id=None,
            dkn_public_key=None,
            github_account=None,
            github_credential_reference=None,
        )

    @staticmethod
    def project(workspace: Path):
        return build_project(
            project_id="sample",
            title="Sample",
            workspace=str(workspace),
            github_url=None,
            application_command=None,
            verification_command=None,
            revision="r002",
        )

    def test_dark_mode_is_default_and_preferences_round_trip(self):
        value = build_preferences()
        self.assertEqual(value["theme"], "signature-dark")
        self.assertEqual(value["session_navigation"], "LEFT")
        with self.temporary() as td:
            hub = PippiHub(Path(td) / "hub")
            hub.initialize(self.onboarding())
            store = PortfolioStore(hub)
            saved = store.save_preferences(build_preferences(session_navigation="TOP", density="compact"))
            self.assertEqual(store.preferences(), saved)

    def test_workspace_and_canonical_revision_are_separate(self):
        with self.temporary() as td:
            base = Path(td)
            project = self.project(base / "working")
            profile = build_project_profile(
                project=project,
                workspaces=[{"workspace_id": "working", "path": str(base / "working"),
                             "role": "WORKING", "status": "ACTIVE"}],
                canonical_store={"kind": "FILESYSTEM", "path": str(base / "canonical"),
                                 "active_revision": "r002", "revision_root": R},
                current_subject_root=R,
                last_material_activity_ns=10,
                last_verified_ns=11,
                verified_subject_root=R,
                proof_level="TARGETED",
                operational_maturity="CONSTRUCTION",
                execution_holds=[],
                release_blockers=[],
                qualification_gaps=[],
                archive_status="CUSTODY_CONFIRMED",
                courthouse_status="NO_WORK_PENDING",
            )
            self.assertNotEqual(profile["workspaces"][0]["path"], profile["canonical_store"]["path"])
            self.assertEqual(profile["adherence_status"], "PASS")
            with self.assertRaisesRegex(HubRefusal,"PIPPI_CANONICAL_STORE_COLLIDES_WITH_WORKSPACE"):
                build_project_profile(
                    project=project, workspaces=profile["workspaces"],
                    canonical_store={"kind":"FILESYSTEM","path":profile["workspaces"][0]["path"],
                                     "active_revision":"r002","revision_root":R},
                    current_subject_root=R,last_material_activity_ns=10,last_verified_ns=11,
                    verified_subject_root=R,proof_level="TARGETED",operational_maturity="CONSTRUCTION",
                    execution_holds=[],release_blockers=[],qualification_gaps=[],archive_status="PASS",
                    courthouse_status="NO_WORK_PENDING")

    def test_freshness_and_holds_are_derived(self):
        with self.temporary() as td:
            project = self.project(Path(td))
            common = dict(
                project=project,
                workspaces=[],
                canonical_store={"kind": "UNBOUND", "path": None,
                                 "active_revision": "r002", "revision_root": None},
                last_material_activity_ns=10,
                last_verified_ns=11,
                proof_level="TARGETED",
                operational_maturity="CONSTRUCTION",
                release_blockers=[],
                qualification_gaps=[],
                archive_status="UNVERIFIED",
                courthouse_status="NO_WORK_PENDING",
            )
            stale = build_project_profile(current_subject_root=R, verified_subject_root="2" * 64,
                                          execution_holds=[], **common)
            held = build_project_profile(current_subject_root=R, verified_subject_root=R,
                                         execution_holds=["EXPLICIT_HOLD"], **common)
            self.assertEqual(stale["adherence_status"], "STALE")
            self.assertEqual(held["adherence_status"], "HELD")

    def test_project_brief_names_one_safe_current_action(self):
        with self.temporary() as td:
            project = self.project(Path(td))
            profile = build_project_profile(
                project=project, workspaces=[],
                canonical_store={"kind":"UNBOUND","path":None,"active_revision":"r002","revision_root":None},
                current_subject_root=R,last_material_activity_ns=10,last_verified_ns=11,
                verified_subject_root=R,proof_level="TARGETED",operational_maturity="CONSTRUCTION",
                execution_holds=["EXACT_ACCEPTANCE_CASE_OPEN"],release_blockers=[],qualification_gaps=[],
                archive_status="UNVERIFIED",courthouse_status="NO_WORK_PENDING")
            brief = build_project_brief(project=project, profile=profile, sessions=[], reviews=[],
                                          gateway_status="DECLARED_UNBOUND")
            self.assertEqual(brief["state"], "HELD")
            self.assertEqual(brief["reason"], "EXACT_ACCEPTANCE_CASE_OPEN")
            self.assertEqual(brief["recommended_action"]["workspace_tab"], "EVIDENCE")
            self.assertFalse(brief["recommended_action"]["dispatch_authorized"])
            self.assertEqual(len(brief["project_brief_root"]), 64)

    def test_cli_project_brief_matches_the_shared_projection(self):
        with self.temporary() as td:
            base=Path(td);hub=PippiHub(base/"hub");hub.initialize(self.onboarding())
            project=hub.add_project(self.project(base/"working"));store=PortfolioStore(hub)
            expected=build_project_brief(project=project,profile=store.profile(project),sessions=[],reviews=[],
                                         gateway_status=hub.integration("UCM_OPERATIONAL_GATEWAY")["status"])
            environment=dict(os.environ);environment["PYTHONPATH"]=str(ROOT / "src")
            completed=subprocess.run([sys.executable,"-m","ucm.pippi_cli","--data-root",str(base/"hub"),
                                      "project-brief","sample"],cwd=ROOT,env=environment,
                                     text=True,capture_output=True,check=True)
            self.assertEqual(json.loads(completed.stdout),expected)

    def test_discovery_imports_verified_reference_without_rewriting_source(self):
        with self.temporary() as td:
            base = Path(td)
            campaign_path = base / "external" / "campaign"
            context = build_pippi_context(
                session_root="1" * 64,
                subject_root="2" * 64,
                policy_roots=[],
                capability_registry_root="3" * 64,
                profile_root="4" * 64,
                jurisdiction_root="5" * 64,
                retained_context_roots=[],
                mediated_channels=["JOURNAL_WRITE"],
            )
            PippiCampaign.create(campaign_path, context)
            before = {p.relative_to(campaign_path).as_posix(): p.read_bytes()
                      for p in campaign_path.rglob("*") if p.is_file()}
            found = discover_campaigns([base / "external"])
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["discovery_status"], "VERIFIED")
            hub = PippiHub(base / "hub")
            hub.initialize(self.onboarding())
            project = hub.add_project(self.project(base / "working"))
            imported = PortfolioStore(hub).import_session(found[0], project_id=project["project_id"])
            self.assertEqual(imported["migration_mode"], "REFERENCE_ONLY_NO_REWRITE")
            after = {p.relative_to(campaign_path).as_posix(): p.read_bytes()
                     for p in campaign_path.rglob("*") if p.is_file()}
            self.assertEqual(before, after)

    def test_timeline_separates_archive_courthouse_operation_and_session_lanes(self):
        session = {
            "project_id": "sample", "last_activity_ns": 4,
            "session_reference_root": "6" * 64,
        }
        events = [
            {"sequence": 1, "observed_unix_ns": 1, "event_type": "ARCHIVE_PREPARED",
             "event_root": "1" * 64, "payload": {"project_id": "sample"}},
            {"sequence": 2, "observed_unix_ns": 2, "event_type": "COURTHOUSE_SUBMITTED",
             "event_root": "2" * 64, "payload": {"project_id": "sample"}},
            {"sequence": 3, "observed_unix_ns": 3, "event_type": "USER_LAUNCH_COMPLETED",
             "event_root": "3" * 64, "payload": {"project_id": "sample"}},
        ]
        timeline = build_timeline(project_id="sample", hub_events=events, sessions=[session])
        self.assertEqual([row["lane"] for row in timeline["events"]],
                         ["ARCHIVE", "COURTHOUSE", "OPERATION", "SESSION"])

    def test_loopback_dispatch_exposes_profiles_sessions_preferences_and_timeline(self):
        with self.temporary() as td:
            base=Path(td);hub=PippiHub(base/"hub");hub.initialize(self.onboarding())
            project=hub.add_project(self.project(base/"working"));store=PortfolioStore(hub)
            self.assertEqual(dispatch_read(hub,{"command":"profile","project_id":"sample"})["project_id"],"sample")
            brief=dispatch_read(hub,{"command":"project-brief","project_id":"sample"})
            self.assertEqual(brief["project_id"],"sample")
            self.assertEqual(brief["recommended_action"]["effect"],"READ_ONLY_NAVIGATION")
            self.assertEqual(dispatch_read(hub,{"command":"sessions","project_id":"sample"}),[])
            self.assertEqual(dispatch_read(hub,{"command":"preferences"})["theme"],"signature-dark")
            self.assertEqual(dispatch_read(hub,{"command":"timeline","project_id":"sample"})["project_id"],"sample")
            self.assertEqual(dispatch_read(hub,{"command":"unknown"})["code"],"PIPPI_IPC_COMMAND_REFUSED")

    def test_installer_targets_r033_and_preserves_global_data_by_default(self):
        source=(ROOT / "install/INSTALL-PIPPI.ps1").read_text(encoding="utf-8")
        uninstall=(ROOT / "install/UNINSTALL-PIPPI.ps1").read_text(encoding="utf-8")
        self.assertIn(r"Pippi\v0.1\r033",source)
        self.assertIn("ExpectedRuntimeRoot",source)
        self.assertIn("PIPPI_RUNTIME_EXTERNAL_ROOT_MISMATCH",source)
        self.assertIn(r"Pippi\data",source)
        self.assertIn("if($RemoveUserData -and",uninstall)

    def test_native_dashboard_uses_portfolio_and_dark_preference(self):
        source=(ROOT / "src/ucm/pippi_dashboard.py").read_text(encoding="utf-8")
        self.assertIn("PortfolioStore",source)
        self.assertIn('self.preferences["theme"]',source)
        self.assertIn('("Canonical store",',source)
        self.assertIn('self.window.image("brand_logo", self.logo',source)
        self.assertIn('name="About P/PPI", command=self.show_about',source)
        self.assertIn('def _build_about_window(self)',source)
        self.assertIn('def show_about(self)',source)
        self.assertIn('Mosaic Project / Process Pipeline Interface',source)
        self.assertIn('authority effect NONE',source)
        self.assertIn('self.window.set_enabled(key, bool(self.projects))',source)
        self.assertIn('("Authority","None inferred",False)',source)
        self.assertIn('self.window.layout_handler = self._relayout',source)
        self.assertIn('def _relayout(self, width: int, height: int)',source)
        self.assertIn('self.window.browse_file("Select the exact returned review archive"',source)
        self.assertIn('def show_review_substance(self)',source)
        self.assertIn('Create held proposal',source)
        self.assertIn('Non-evidentiary live status',source)
        self.assertIn('self.window.badge("focus_state"',source)
        self.assertIn('def open_recommended_context(self)',source)
        self.assertIn('build_project_brief',source)
        native=(ROOT / "src/mosaic_ui/win32.py").read_text(encoding="utf-8")
        self.assertIn('def browse_file(self, title: str, initial: str = "")',native)
        self.assertIn('def set_table_column_widths(self, key: str, widths)',native)


if __name__ == "__main__":
    unittest.main()


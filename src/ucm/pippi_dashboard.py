"""Native Mosaic UI dashboard for the sovereign local P/PPI hub."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import threading
import time
from typing import Any, Callable

from .pippi_global import PippiHub, HubRefusal
from .pippi_host import (HostLaunchAdapter, RefusingHostLaunchAdapter,
                         build_host_launch_proposal,
                         validate_host_adapter_policy,
                         validate_host_launch_result,
                         validate_host_mediation_attestation)
from .pippi_portfolio import (PortfolioStore, build_preferences, build_project_brief,
                              build_timeline)
from .pippi_reviews import ReviewStore, verify_review_envelope


WORKSPACE_TABS = ("OVERVIEW", "SESSIONS", "TIMELINE", "EVIDENCE", "REVIEWS", "CONSTITUTION")


def _load_native() -> tuple[Any, Any, Any, Any]:
    source_root = Path(__file__).resolve().parents[2]
    vendor = source_root / "vendor" / "mosaic-native"
    if vendor.is_dir() and str(vendor) not in sys.path:
        sys.path.insert(0, str(vendor))
    from mosaic_ui import win32
    from mosaic_ui.win32_image import NativeImage
    from mosaic_ui.branding import verified_logo_path
    from mosaic_ui_std.signature import resolve_signature_theme
    return win32, NativeImage, verified_logo_path, resolve_signature_theme


class PippiSplash:
    def __init__(self) -> None:
        win32, NativeImage, verified_logo_path, resolve = _load_native()
        self.win32 = win32
        self.logo = NativeImage(verified_logo_path())
        tokens = resolve("signature-dark", "comfortable")["tokens"]
        self.window = win32.NativeWindow("P/PPI", tokens=tokens, width=650, height=360,
                                         presentation="splash")
        self.window.set_icon(self.logo)
        self.window.image("logo", self.logo, (34, 36, 158, 158), name="Mosaic")
        self.window.label("title", "P/PPI", (220, 54, 380, 48), style="title")
        self.window.label("subtitle", "Mosaic Project / Process Pipeline Interface",
                          (220, 108, 380, 52), style="heading")
        self.window.label("status", "Verifying local constitutional state…", (38, 232, 570, 28))
        self.window.progress("progress", (38, 272, 570, 9))
        self.window.label("posture", "Sovereign local hub · remote work routes through the courthouse",
                          (38, 300, 570, 24), style="quiet")
        self.started = time.monotonic(); self.done = False; self.error: BaseException | None = None
        self.pending_status = "Verifying local constitutional state…"
        self.window.set_progress("progress", 8)
        self.window.set_timer(40, self.poll)

    def poll(self) -> None:
        self.window.set_text("status",self.pending_status)
        if self.done and self.error is None:self.window.set_progress("progress",100)
        if self.done and time.monotonic() - self.started >= 2.0:
            self.window.close()

    def run(self, probe: Callable[[], Any]) -> Any:
        result: list[Any] = []
        def work() -> None:
            try:
                self.pending_status = "Checking journals, projects, and identity references…"
                result.append(probe())
                self.pending_status = "Local hub ready"
            except BaseException as exc:
                self.error = exc
            finally:
                self.done = True
        thread = threading.Thread(target=work, name="pippi-startup", daemon=True)
        thread.start(); self.window.run(); thread.join(); self.logo.close()
        if self.error: raise self.error
        return result[0]


class Dashboard:
    def __init__(self, hub: PippiHub,
                 host_adapter: HostLaunchAdapter | None = None) -> None:
        win32, NativeImage, verified_logo_path, resolve = _load_native()
        self.win32 = win32
        self.resolve_theme = resolve
        self.logo = NativeImage(verified_logo_path())
        self.hub = hub; self.portfolio = PortfolioStore(hub); self.review_store = ReviewStore(hub)
        self.host_adapter = host_adapter or RefusingHostLaunchAdapter()
        self.preferences = self.portfolio.preferences()
        self.projects = hub.list_projects(); self.selected = 0; self.selected_tab = self.preferences["default_tab"]
        self.current_brief: dict[str, Any] | None = None
        self.advanced_visible = False
        self.selected_review_id: str | None = None
        self.review_display_ids: dict[str, str] = {}
        self.review_run_updates: list[dict[str, Any]] = []
        self.review_run_active = False
        self.review_run_started_ns: int | None = None
        self.review_run_phase = "IDLE"
        self.review_run_evidence: str | None = None
        self.window = win32.NativeWindow("P/PPI — Mosaic Projects", tokens=resolve(
            self.preferences["theme"], self.preferences["density"])["tokens"], width=1440, height=900)
        self.window.set_minimum_client_size(1180, 760)
        self.window.set_icon(self.logo)
        self.window.image("brand_logo", self.logo, (28, 14, 66, 66),
                          name="About P/PPI", command=self.show_about)
        self.window.label("brand", "P/PPI", (108, 20, 90, 42), style="title")
        self.window.label("heading", "Constitutional project operations", (210, 24, 600, 34), style="heading")
        self.window.label("boundary", "Local coordination · governed effects · courthouse for remote correspondence",
                          (210, 60, 790, 24), style="quiet")
        self.window.label("summary", "", (1030, 24, 370, 56), style="accent")
        self.window.badge("hub_state", (1030, 80, 210, 28))
        self.window.button("refresh", "Refresh", (1260, 80, 140, 28), self.refresh)
        self.window.label("project_heading", "Projects", (28, 104, 440, 28), style="heading")
        self.window.table("projects", ["Project", "Version · current state"], (28, 138, 440, 250),
                          command=self.select_project)
        self.window.label("session_heading", "Concurrent sessions", (28, 410, 440, 28), style="heading")
        self.window.table("sessions", ["Session", "State · updated"], (28, 444, 440, 250),
                          command=self.select_session)
        self.window.workspace_tabs("workspace_tabs", WORKSPACE_TABS,
                                   (500, 112, 870, 38), selected=self.selected_tab, command=self.select_tab)
        self.window.label("detail_title", "No project selected", (500, 164, 870, 42), style="title")
        self.window.label("focus_heading", "NOW", (500, 216, 70, 22), style="quiet")
        self.window.badge("focus_state", (580, 210, 150, 30))
        self.window.label("focus_headline", "Select a project", (500, 246, 610, 30), style="heading")
        self.window.label("focus_reason", "P/PPI will project the most important current fact here.",
                          (500, 278, 650, 24), style="quiet")
        self.window.button("focus_action", "Open", (1180, 246, 190, 42), self.open_recommended_context)
        self.window.flat_key_value("activity", "Project details", (500, 316, 870, 310), columns=2)
        # Reviews use an operator-oriented master/detail surface.  It is kept
        # separate from the generic project projection so custody and decision
        # states remain legible rather than becoming another raw key/value dump.
        self.window.label("review_queue_heading", "REVIEW QUEUE", (500, 216, 320, 24), style="quiet")
        self.window.table("review_queue", ["Review"], (500, 246, 320, 360), command=self.select_review)
        self.window.label("review_detail_heading", "SELECTED REVIEW", (842, 216, 330, 24), style="quiet")
        self.window.badge("review_state", (1190, 210, 180, 30))
        self.window.flat_key_value("review_detail", "Custody and decision state", (842, 246, 528, 360), columns=1)
        # Actions are grouped by human intent. The grouping is presentational only:
        # every command retains its original key, callback, and constitutional path.
        self.window.label("run_group", "RUN", (500, 638, 490, 24), style="quiet")
        self.window.button("both", "Verify, then launch", (500, 666, 182, 40), self.verify_then_launch)
        self.window.button("launch", "Launch application", (694, 666, 158, 40), self.launch_application)
        self.window.button("verify", "Verify only", (864, 666, 138, 40), self.launch_verification)
        self.window.style_button("both", primary=True)

        self.window.label("inspect_group", "INSPECT", (1024, 638, 376, 24), style="quiet")
        self.window.button("readme", "README", (1024, 666, 84, 40), self.open_readme)
        self.window.button("docs", "Docs", (1120, 666, 84, 40), self.open_docs)
        self.window.button("tree", "Files", (1216, 666, 84, 40), self.open_tree)
        self.window.button("github", "GitHub", (1312, 666, 84, 40), self.open_github)

        self.window.label("govern_group", "GOVERN", (500, 720, 870, 24), style="quiet")
        self.window.button("constitution", "Context / constitution", (500, 748, 214, 40), self.show_constitution)
        self.window.button("advanced_toggle", "Advanced…", (726, 748, 144, 40), self.toggle_advanced)
        self.project_action_keys = ("launch", "verify", "both", "github", "tree",
                                    "readme", "docs", "constitution", "focus_action")
        self.regular_action_keys = ("run_group", "both", "launch", "verify", "inspect_group",
                                    "readme", "docs", "tree", "github", "govern_group",
                                    "constitution", "advanced_toggle")
        self.review_view_keys = ("review_queue_heading", "review_queue", "review_detail_heading",
                                 "review_state", "review_detail")
        self.window.label("review_group", "REVIEW", (500, 638, 320, 24), style="quiet")
        self.window.button("review_verify", "Verify", (500, 666, 98, 40), self.verify_selected_review)
        self.window.button("review_run", "Run local", (610, 666, 98, 40), self.run_selected_review)
        self.window.button("review_substance", "Substance…", (720, 666, 100, 40), self.show_review_substance)
        self.window.label("correspond_group", "CORRESPOND", (842, 638, 320, 24), style="quiet")
        self.window.button("review_prepare", "Prepare courthouse", (842, 666, 166, 40), self.prepare_selected_review)
        self.window.button("review_import", "Import return…", (1020, 666, 142, 40), self.explain_review_import)
        self.window.label("decide_group", "DECIDE", (1184, 638, 186, 24), style="quiet")
        self.window.button("review_compare", "Compare", (1184, 666, 92, 40), self.compare_selected_review)
        self.window.button("review_publish", "Publication…", (1288, 666, 108, 40), self.explain_publication_proposal)
        self.window.label("review_boundary",
                          "Application owns its courts · P/PPI owns exact custody · publication requires human authorization",
                          (500, 728, 870, 28), style="accent")
        self.window.label("review_progress_heading", "RUN PROGRESS", (500, 766, 120, 22), style="quiet")
        self.window.flat_key_value("review_progress", "Non-evidentiary live status", (500, 792, 870, 48), columns=3)
        self.review_action_keys = ("review_group", "review_verify", "review_run", "review_substance", "correspond_group",
                                   "review_prepare", "review_import", "decide_group", "review_compare",
                                   "review_publish", "review_boundary", "review_progress_heading", "review_progress")
        for key in self.review_view_keys + self.review_action_keys:
            self.window.show(key, False)
        self.window.label("advanced_title", "Advanced controls", (500, 798, 200, 24), style="heading")
        self.window.label("advanced", "", (706, 798, 664, 24), style="quiet")
        self.window.button("layout_nav", "Sessions: left/top", (500, 826, 170, 32), self.toggle_navigation)
        self.window.button("hash_mode", "Hash display", (682, 826, 150, 32), self.toggle_hash_display)
        self.window.button("theme_mode", "Theme", (844, 826, 120, 32), self.toggle_theme)
        for key in ("advanced_title", "advanced", "layout_nav", "hash_mode", "theme_mode"):
            self.window.show(key, False)
        self.window.label("status", "Ready", (28, 716, 440, 72), style="quiet")
        self.window.set_timer(150, self.poll_review_run)
        self.window.layout_handler = self._relayout
        self.apply_navigation_layout()
        self.refresh()

    def _build_about_window(self):
        """Build the explanatory modal separately so native witnesses can inspect it."""
        about = self.win32.NativeWindow(
            "About P/PPI",
            tokens=self.resolve_theme(self.preferences["theme"], self.preferences["density"])["tokens"],
            width=760,
            height=620,
            owner=self.window,
        )
        about.set_icon(self.logo)
        about.image("logo", self.logo, (34, 28, 136, 136), name="Mosaic rainbow sun")
        about.label("title", "P/PPI", (196, 38, 500, 44), style="title")
        about.label("subtitle", "Mosaic Project / Process Pipeline Interface",
                    (196, 88, 500, 36), style="heading")
        about.label("identity", "v0.1 r016 · Ableman Mosaic 2026 · Apache 2.0",
                    (196, 128, 500, 24), style="quiet")
        about.label(
            "purpose",
            "P/PPI gives people and agents one governed view of projects, sessions, "
            "verification, journals, holds, and effect proposals. It keeps exact state "
            "visible while work moves between local tools, UCM, and the courthouse.",
            (34, 184, 678, 72),
        )
        about.label("does_heading", "What it does", (34, 274, 300, 30), style="heading")
        about.label(
            "does",
            "• Pins project, policy, profile, identity, jurisdiction, and journal roots.\n"
            "• Mediates observable agent drafts, tool proposals, results, and projections.\n"
            "• Routes permitted local effects to the UCM Gateway and remote correspondence "
            "to the courthouse.\n"
            "• Preserves portable, verifiable project and session history.",
            (48, 312, 650, 116),
        )
        about.label("boundary_heading", "Constitutional boundary", (34, 438, 330, 30), style="heading")
        about.label(
            "boundary_text",
            "P/PPI does not grant authority, replace an application's native validator, or "
            "turn progress into evidence. Unmediated channels remain explicitly partial.",
            (48, 476, 650, 58),
        )
        about.label(
            "posture",
            "INFORMATION_ONLY  ·  authority effect NONE  ·  real A5 false  ·  G0 closed",
            (34, 548, 520, 28),
            style="accent",
        )
        about.button("close", "Close", (586, 538, 126, 40), about.close)
        return about

    def show_about(self) -> None:
        """Show a bounded native explanation of P/PPI and its authority posture."""
        about = self._build_about_window()
        about.run_modal("close")

    def current(self) -> dict[str, Any]:
        if not self.projects: raise HubRefusal("PIPPI_PROJECT_UNKNOWN")
        return self.projects[min(self.selected, len(self.projects)-1)]

    def select_project(self, value: str) -> None:
        for index, project in enumerate(self.projects):
            if project["project_id"] == value or project["title"] == value:
                self.selected=index; break
        self.show()

    def select_session(self, value: str) -> None:
        sessions=self.portfolio.list_sessions(self.current()["project_id"]) if self.projects else []
        selected=next((row for row in sessions if row["session_id"]==value),None)
        if selected:
            self.selected_tab="SESSIONS";self.window.set_workspace_tabs("workspace_tabs",WORKSPACE_TABS,self.selected_tab)
            self.window.set_key_value("activity",self._session_rows(selected))

    def select_tab(self, value: str) -> None:
        self.selected_tab=value;self.show()

    def select_review(self, value: str) -> None:
        reviews = self.review_store.list(self.current()["project_id"]) if self.projects else []
        review_id = self.review_display_ids.get(value, value)
        if any(row["review_id"] == review_id for row in reviews):
            self.selected_review_id = review_id
        self._show_reviews()

    def refresh(self) -> None:
        self.projects=self.hub.list_projects(); self.selected=min(self.selected,max(0,len(self.projects)-1))
        for key in self.project_action_keys:
            self.window.set_enabled(key, bool(self.projects))
        gateway = self.hub.integration("UCM_OPERATIONAL_GATEWAY")
        gateway_bound = gateway["status"] == "BOUND_EXTERNAL"
        self.window.set_badge("hub_state", "GATEWAY BOUND" if gateway_bound else "GATEWAY NOT BOUND",
                              "accent" if gateway_bound else "pending")
        self.window.set_text("run_group","RUN" if gateway_bound else "RUN · GATEWAY REQUIRED")
        effect_ready = bool(self.projects) and gateway["status"] == "BOUND_EXTERNAL"
        for key in ("both", "launch", "verify", "github", "tree", "readme", "docs"):
            self.window.set_enabled(key, effect_ready)
        rows=[]
        for project in self.projects:
            profile=self.portfolio.profile(project)
            brief=self._brief(project,profile)
            rows.append((project["project_id"],
                         f"{project['public_version']} {project['revision']} · {brief['state']}"))
        self.window.set_rows("projects",rows)
        if self.projects:self.window.set_table_selection("projects",self.current()["project_id"])
        sessions=self.portfolio.list_sessions(self.current()["project_id"]) if self.projects else []
        session_rows=[(s["session_id"],f"{s['status']} · {self._time(s['last_activity_ns'])}") for s in sessions]
        self.window.set_rows("sessions",session_rows or [("No active sessions","Import a verified reference")])
        project_briefs=[self._brief(p,self.portfolio.profile(p)) for p in self.projects]
        held=sum(row["state"] in {"HELD","BLOCKED"} for row in project_briefs)
        project_attention=sum(row["state"] not in {"READY","REVIEW_RETURNED"} for row in project_briefs)
        attention=sum(s["status"]=="NEEDS_ATTENTION" for s in self.portfolio.list_sessions())
        reviews=self.review_store.list()
        returned=sum(row["status"] in {"RETURNED","PUBLICATION_PROPOSED"} for row in reviews)
        self.window.set_text("summary",f"{len(self.projects)} projects · {len(self.portfolio.list_sessions())} sessions · {len(reviews)} reviews\n"
                                       f"{held} held · {project_attention + attention} need attention · {returned} returned")
        self.show()

    def show(self) -> None:
        if not self.projects:
            self.current_brief=None
            self.window.set_text("detail_title","No projects registered")
            self.window.set_badge("focus_state","GET STARTED","info")
            self.window.set_text("focus_headline","Register or discover a governed project")
            self.window.set_text("focus_reason","Project state remains empty until an exact project record is added.")
            self.window.set_text("focus_action","No project")
            self.window.set_enabled("focus_action",False)
            self.window.set_key_value("activity",[("Next step",
                "Installer or pippi project-add",False),
                ("Existing sessions","pippi migrate-discover",False),
                ("Authority","None inferred",False)])
            self.window.set_text("status","Ready · no projects registered")
            return
        p=self.current();profile=self.portfolio.profile(p);sessions=self.portfolio.list_sessions(p["project_id"])
        self.current_brief=self._brief(p,profile)
        brief=self.current_brief
        self.window.set_badge("focus_state",brief["state"].replace("_"," "),brief["tone"])
        self.window.set_text("focus_headline",brief["headline"])
        self.window.set_text("focus_reason",brief["reason_display"])
        self.window.set_text("focus_action",brief["recommended_action"]["label"])
        self.window.set_enabled("focus_action",True)
        views={"OVERVIEW":lambda:self._overview_rows(p,profile,sessions),"SESSIONS":lambda:self._sessions_rows(sessions),
               "TIMELINE":lambda:self._timeline_rows(p),"EVIDENCE":lambda:self._evidence_rows(p,profile),
               "CONSTITUTION":lambda:self._constitution_rows(p)}
        self.window.set_text("detail_title",f"{p['title']}  ·  {p['public_version']} {p['revision']}")
        if self.selected_tab == "REVIEWS":
            self._show_reviews()
        else:
            self._set_review_mode(False)
            self.window.set_key_value("activity",views.get(self.selected_tab,views["OVERVIEW"])())
        self.window.set_text("advanced",f"Theme {self.preferences['theme']} · sessions {self.preferences['session_navigation'].lower()} · "
                                         f"hashes {self.preferences['hash_display'].lower()}")
        self.window.set_text("status",f"Projection current · {brief['state'].lower().replace('_',' ')}\n"
                                      f"Read-only navigation · no effect inferred")

    def _brief(self,p:dict[str,Any],profile:dict[str,Any])->dict[str,Any]:
        return build_project_brief(project=p,profile=profile,
            sessions=self.portfolio.list_sessions(p["project_id"]),
            reviews=self.review_store.list(p["project_id"]),
            gateway_status=self.hub.integration("UCM_OPERATIONAL_GATEWAY")["status"])

    def open_recommended_context(self)->None:
        if self.current_brief is None:return
        tab=self.current_brief["recommended_action"]["workspace_tab"]
        self.selected_tab=tab;self.window.set_workspace_tabs("workspace_tabs",WORKSPACE_TABS,tab)
        self.show();self.window.set_text("status",f"Opened {tab.lower()} · recommendation is navigation only")

    def _set_review_mode(self, enabled: bool) -> None:
        self.window.show("activity", not enabled)
        for key in self.regular_action_keys:
            self.window.show(key, not enabled)
        for key in self.review_view_keys + self.review_action_keys:
            self.window.show(key, enabled)
        for key in ("advanced_title", "advanced", "layout_nav", "hash_mode", "theme_mode"):
            self.window.show(key, (not enabled) and self.advanced_visible)

    @staticmethod
    def _human(value: str | None, fallback: str = "Not returned") -> str:
        if not value:
            return fallback
        return value.replace("_", " ").strip().capitalize()

    @staticmethod
    def _review_label(value: str, project_id: str | None = None) -> str:
        display = value
        if project_id and display.startswith(project_id + "-"):
            display = display[len(project_id) + 1:]
        return display.replace("-", " ").replace("_", " ").strip().title()

    def _review_detail_rows(self, review: dict[str, Any]) -> list[tuple[str, str, bool]]:
        publication = ("Proposal held for human authorization" if review["publication_plan_root"]
                       else "No publication proposal")
        authority = "No authority effect (reported outcome only)"
        return [
            ("Review", review["review_id"], False),
            ("Class", self._human(review["review_class"]), False),
            ("Subject", review["subject_role"], False),
            ("Authority", authority, False),
            ("Publication", publication, False),
            ("Reported outcome", self._human(review["reported_outcome"]), False),
            ("Subject root", self._hash(review["subject_manifest_root"]), True),
            ("Envelope", self._hash(review["envelope_sha256"]), True),
            ("Courthouse", self._hash(review["courthouse_work_order_root"]), True),
            ("Return", self._hash(review["return_root"]), True),
        ]

    def _show_reviews(self) -> None:
        self._set_review_mode(True)
        project_id = self.current()["project_id"]
        reviews = self.review_store.list(project_id)
        self.review_display_ids = {self._review_label(row["review_id"], project_id): row["review_id"] for row in reviews}
        self.window.set_rows("review_queue", [(label,) for label in self.review_display_ids])
        if not reviews:
            self.selected_review_id = None
            self.window.set_badge("review_state", "NO REVIEWS", "info")
            self.window.set_key_value("review_detail", [
                ("Next step", "Build and register an exact review envelope", False),
                ("Remote review", "Correspondence routes through the courthouse", False),
                ("Publication", "Separate human-authorized proposal", False),
            ])
            for key in ("review_verify", "review_run", "review_substance", "review_prepare", "review_import",
                        "review_compare", "review_publish"):
                self.window.set_enabled(key, False)
            self._update_review_progress()
            return
        ids = {row["review_id"] for row in reviews}
        if self.selected_review_id not in ids:
            self.selected_review_id = reviews[0]["review_id"]
        review = next(row for row in reviews if row["review_id"] == self.selected_review_id)
        self.window.set_table_selection("review_queue", self._review_label(self.selected_review_id, project_id))
        tone = {"PACKAGED": "info", "DISPATCH_PREPARED": "pending", "RETURNED": "accent",
                "PUBLICATION_PROPOSED": "accent"}.get(review["status"], "info")
        self.window.set_badge("review_state", self._human(review["status"]).upper(), tone)
        self.window.set_key_value("review_detail", self._review_detail_rows(review))
        self.window.set_enabled("review_verify", True)
        gateway_bound = self.hub.integration("UCM_OPERATIONAL_GATEWAY")["status"] == "BOUND_EXTERNAL"
        self.window.set_enabled("review_run", not self.review_run_active and gateway_bound)
        self.window.set_enabled("review_substance", True)
        self.window.set_enabled("review_prepare", review["status"] == "PACKAGED")
        self.window.set_enabled("review_import", review["status"] == "DISPATCH_PREPARED")
        self.window.set_enabled("review_compare", len(reviews) >= 2)
        self.window.set_enabled("review_publish", review["status"] == "RETURNED")
        self._update_review_progress()

    def _update_review_progress(self) -> None:
        elapsed = "not running"
        if self.review_run_started_ns is not None:
            seconds = max(0, (time.time_ns() - self.review_run_started_ns) // 1_000_000_000)
            elapsed = f"{seconds // 60:02d}:{seconds % 60:02d}"
        destination = self.review_run_evidence or "not created"
        if len(destination) > 62:
            destination = "…" + destination[-61:]
        self.window.set_key_value("review_progress", [
            ("Phase", self.review_run_phase, False),
            ("Elapsed", elapsed, True),
            ("Evidence", destination, True),
        ])

    @staticmethod
    def _time(value: int | None) -> str:
        if value is None:return "never"
        return time.strftime("%Y-%m-%d %H:%M",time.localtime(value/1_000_000_000))

    def _hash(self,value:str|None)->str:
        if value is None:return "unbound"
        return value if self.preferences["hash_display"]=="FULL" else value[:12]+"…"

    def _overview_rows(self,p,profile,sessions):
        workspace="; ".join(f"{row['role']} {row['path']} [{row['status']}]" for row in profile["workspaces"]) or "none"
        canonical=profile["canonical_store"]
        return [("Adherence",profile["adherence_status"],False),("Proof",profile["proof_level"],False),
                ("Maturity",profile["operational_maturity"],False),("Last activity",self._time(profile["last_material_activity_ns"]),False),
                ("Last verified",self._time(profile["last_verified_ns"]),False),("Current subject",self._hash(profile["current_subject_root"]),True),
                ("Verified subject",self._hash(profile["verified_subject_root"]),True),("Working spaces",workspace,False),
                ("Canonical store",f"{canonical['kind']} {canonical['path'] or 'unbound'}",False),
                ("Canonical revision",f"{canonical['active_revision']} · {self._hash(canonical['revision_root'])}",True),
                ("Sessions",str(len(sessions)),False),("Archive",profile["archive_status"],False),
                ("Courthouse",profile["courthouse_status"],False),("GitHub",p["github_url"] or "unbound",False)]

    def _session_rows(self,s):
        return [("Session",s["session_id"],True),("Status",s["status"],False),("Integration",s["integration_mode"],False),
                ("Last activity",self._time(s["last_activity_ns"]),False),("Events",str(s["event_count"]),False),
                ("Source",s["source_path"],False),("Context",self._hash(s["context_root"]),True),
                ("Subject",self._hash(s["subject_root"]),True),("Journal head",self._hash(s["journal_head"]),True),
                ("Migration","REFERENCE ONLY · ORIGINAL UNCHANGED",False)]

    def _sessions_rows(self,sessions):
        if not sessions:return [("Sessions","No verified P/PPI session references imported",False)]
        rows=[]
        for s in sessions:
            rows.extend([("Session",s["session_id"],True),("State",f"{s['status']} · {s['integration_mode']}",False),
                         ("Last activity",self._time(s["last_activity_ns"]),False),("Journal",self._hash(s["journal_head"]),True)])
        return rows

    def _timeline_rows(self,p):
        timeline=build_timeline(project_id=p["project_id"],hub_events=self.hub._events(),
                                sessions=self.portfolio.list_sessions(p["project_id"]))
        if not timeline["events"]:return [("Timeline","No governed transitions recorded",False)]
        return [(f"{row['lane']} · {row['kind']}",f"{self._time(row['observed_unix_ns'])} · {self._hash(row['receipt_root'])}",True)
                for row in timeline["events"]]

    def _evidence_rows(self,p,profile):
        rows=[("Project root",self._hash(p["project_root"]),True),("Profile root",self._hash(profile["profile_root"]),True)]
        for title,key in (("Execution hold","execution_holds"),("Release blocker","release_blockers"),("Qualification gap","qualification_gaps")):
            values=profile[key] or ["none"];rows.extend((title,value,False) for value in values)
        return rows

    def _reviews_rows(self,p):
        reviews=self.review_store.list(p["project_id"])
        if not reviews:
            return [("Reviews","No exact reviewer envelopes registered",False),
                    ("Create","pippi review-envelope-build",False),
                    ("Remote review","Courthouse owns transport; P/PPI imports the bound return",False),
                    ("Publication","Always a separate human-authorized effect",False)]
        rows=[]
        for review in reviews:
            rows.extend([
                ("Review",f"{review['review_id']} · {review['review_class']}",False),
                ("State",review["status"],False),
                ("Subject",self._hash(review["subject_manifest_root"]),True),
                ("Envelope",self._hash(review["envelope_sha256"]),True),
                ("Reported outcome",review["reported_outcome"] or "not returned",False),
                ("Courthouse",self._hash(review["courthouse_work_order_root"]),True),
                ("Publication",self._hash(review["publication_plan_root"]),True),
            ])
        return rows

    def _selected_review(self) -> dict[str, Any]:
        if not self.selected_review_id:
            raise HubRefusal("PIPPI_REVIEW_UNKNOWN")
        return self.review_store.get(self.current()["project_id"], self.selected_review_id)

    def verify_selected_review(self) -> None:
        try:
            review = self._selected_review()
            result = verify_review_envelope(Path(review["envelope_path"]),
                                            expected_sha256=review["envelope_sha256"])
            self.window.set_text("status", f"Envelope verified\n{self._hash(result['archive_sha256'])}")
        except BaseException as exc:
            self.window.set_text("status", f"Review verification refused\n{type(exc).__name__}: {exc}")

    def run_selected_review(self) -> None:
        if self.review_run_active:
            return
        try:
            review = self._selected_review()
        except BaseException as exc:
            self.window.set_text("status", f"Review run refused\n{type(exc).__name__}: {exc}")
            return
        evidence = self.hub.root / "review-runs" / review["review_id"] / "LOCAL-EVIDENCE.zip"
        self.review_run_updates.clear(); self.review_run_active = True
        self.review_run_started_ns = time.time_ns(); self.review_run_phase = "VERIFY · START"
        self.review_run_evidence = str(evidence)
        self.window.set_enabled("review_run", False)
        self.window.set_text("status", "Local review replay\nVERIFY: starting")
        self._update_review_progress()

        def progress(row: dict[str, Any]) -> None:
            self.review_run_updates.append({"kind": "PROGRESS", **row})

        def work() -> None:
            try:
                launch = self._dispatch_host("REVIEW_LOCAL", {
                    "envelope_path": review["envelope_path"],
                    "expected_sha256": review["envelope_sha256"],
                    "evidence_path": str(evidence)}, progress=progress)
                self.review_run_updates.append({"kind": "DONE",
                                                "result": launch["result_projection"]})
            except BaseException as exc:
                self.review_run_updates.append({"kind": "ERROR", "error": type(exc).__name__,
                                                "detail": str(exc)})
        threading.Thread(target=work, name="pippi-review-run", daemon=True).start()

    def poll_review_run(self) -> None:
        if not self.review_run_updates:
            if self.review_run_active and self.selected_tab == "REVIEWS":
                self._update_review_progress()
            return
        rows = self.review_run_updates[:]
        self.review_run_updates.clear()
        for row in rows:
            if row["kind"] == "PROGRESS":
                self.review_run_phase = f"{row['phase']} · {row['status']}"
                self.window.set_text("status", f"Local review replay\n{row['phase']}: {row['status']}")
                self._update_review_progress()
            elif row["kind"] == "DONE":
                self.review_run_active = False
                result = row["result"]
                self.review_run_phase = f"COMPLETE · {result['status']}"
                self.review_run_evidence = result["evidence_path"]
                self.window.set_text("status", f"Local review replay: {result['status']}\n"
                                               f"Evidence {self._hash(result['evidence_sha256'])}")
                self._show_reviews()
            else:
                self.review_run_active = False
                self.review_run_phase = f"REFUSED · {row['error']}"
                self.window.set_text("status", f"Local review replay refused\n{row['error']}: {row['detail']}")
                self._show_reviews()
        if self.review_run_active:
            self._update_review_progress()

    def prepare_selected_review(self) -> None:
        try:
            review = self._selected_review()
            result = self.review_store.prepare_courthouse(project_id=review["project_id"],
                                                           review_id=review["review_id"],
                                                           destination_jurisdiction="aok:courthouse")
            self.window.set_text("status", "Courthouse work order prepared\n" +
                                 self._hash(result["work_order"]["work_order_root"]))
            self.refresh()
        except BaseException as exc:
            self.window.set_text("status", f"Courthouse preparation refused\n{type(exc).__name__}: {exc}")

    def explain_review_import(self) -> None:
        review = self._selected_review()
        selected = self.window.browse_file("Select the exact returned review archive",
                                           self.current()["workspace"])
        if not selected:
            self.window.set_text("status", "Return import cancelled\nNo custody state changed")
            return
        try:
            updated = self.review_store.import_return(project_id=review["project_id"],
                                                       review_id=review["review_id"],
                                                       return_path=Path(selected))
            self.window.set_text("status", "Exact review return imported\n" + self._hash(updated["return_root"]))
            self.refresh()
        except BaseException as exc:
            self.window.message("Review return refused", f"{type(exc).__name__}: {exc}", error=True)
            self.window.set_text("status", f"Review return refused\n{type(exc).__name__}: {exc}")

    def _build_review_substance_window(self):
        review = self._selected_review()
        substance = self.review_store.substance(project_id=review["project_id"],
                                                 review_id=review["review_id"])
        severity = ", ".join(f"{key} {value}" for key, value in sorted(substance["severity_counts"].items())) or "none"
        sections = [
            f"Review: {substance['review_id']}",
            f"Class: {self._human(substance['review_class'])}",
            f"Reviewer identity: {substance['reviewer_identity_root'] or 'not returned'}",
            f"Reported outcome: {self._human(substance['reported_outcome'])}",
            f"Severity counts: {severity}",
            f"Independent review required: {str(substance['independent_review_required']).lower()}",
            "",
            "ENVELOPE LIMITATIONS",
            *(f"• {row}" for row in substance["envelope_limitations"]),
            "",
            "RETURN LIMITATIONS",
            *(f"• {row}" for row in substance["return_limitations"]),
            "",
            "FINDINGS",
            json.dumps(substance["findings"], ensure_ascii=False, sort_keys=True, indent=2),
            "",
            "EVIDENCE FILES",
            *(f"• {row['path']}  {row['sha256']}" for row in substance["evidence_files"]),
            "",
            f"Substance root: {substance['substance_root']}",
            "Exact projection only; no alternate authority was created.",
        ]
        modal = self.win32.NativeWindow(
            "Review substance",
            tokens=self.resolve_theme(self.preferences["theme"], self.preferences["density"])["tokens"],
            width=860, height=680, owner=self.window,
        )
        modal.label("title", "Review substance", (28, 22, 610, 38), style="title")
        modal.label("boundary", "Findings, limitations, evidence, and reviewer identity from exact archives",
                    (28, 62, 770, 24), style="quiet")
        document = "\n".join(sections)
        modal.rich_document("document", document, (28, 104, 804, 458))
        modal.set_rich_document("document", document, ())
        modal.button("close", "Close", (696, 578, 136, 38), modal.close)
        return modal

    def show_review_substance(self) -> None:
        try:
            modal = self._build_review_substance_window()
        except BaseException as exc:
            self.window.message("Review substance refused", f"{type(exc).__name__}: {exc}", error=True)
            return
        modal.run_modal("close")

    def compare_selected_review(self) -> None:
        review = self._selected_review()
        others = [row for row in self.review_store.list(review["project_id"])
                  if row["review_id"] != review["review_id"]]
        if not others:
            self.window.set_text("status", "Comparison unavailable\nA second exact review is required")
            return
        result = self.review_store.compare(project_id=review["project_id"],
                                           left_review_id=review["review_id"],
                                           right_review_id=others[-1]["review_id"])
        self.window.message("Review comparison",
                            f"Compared with {others[-1]['review_id']}.\n"
                            f"Changed custody fields: {len(result['changes'])}.\n"
                            f"Comparison root: {result['comparison_root']}\n\n"
                            "Semantic interpretation was not inferred.")

    def _build_publication_window(self):
        review = self._selected_review()
        profile = self.portfolio.profile(self.current())
        default_artifact = profile.get("current_subject_root") or ""
        modal = self.win32.NativeWindow(
            "Publication proposal",
            tokens=self.resolve_theme(self.preferences["theme"], self.preferences["density"])["tokens"],
            width=760, height=590, owner=self.window,
        )
        modal.label("title", "Prepare publication proposal", (28, 24, 650, 38), style="title")
        modal.label("boundary", "Creates a held plan only · Crystal Network remains publication owner",
                    (28, 66, 680, 24), style="accent")
        modal.label("artifact_path_label", "Exact local artifact path", (28, 116, 280, 24), style="heading")
        modal.edit("artifact_path", "", (28, 146, 700, 34))
        modal.label("artifact_label", "Expected artifact SHA-256", (28, 202, 280, 24), style="heading")
        modal.edit("artifact", default_artifact, (28, 232, 700, 34))
        modal.label("targets_label", "Targets (comma-separated)", (28, 288, 280, 24), style="heading")
        modal.edit("targets", "GITHUB", (28, 318, 700, 34))
        modal.label("dkn_label", "Optional public DKN namespace", (28, 374, 320, 24), style="heading")
        modal.edit("dkn", "", (28, 404, 700, 34))
        modal.label("notice",
                    f"Review outcome: {self._human(review['reported_outcome'])}. This does not authorize publication.",
                    (28, 460, 700, 36), style="quiet")

        def submit() -> None:
            artifact = modal.text("artifact").strip().lower()
            artifact_path = Path(modal.text("artifact_path").strip())
            targets = sorted(set(row.strip().upper() for row in modal.text("targets").split(",") if row.strip()))
            dkn = modal.text("dkn").strip() or None
            if len(artifact) != 64 or any(ch not in "0123456789abcdef" for ch in artifact):
                modal.message("Proposal refused", "Artifact SHA-256 must be exactly 64 lowercase hexadecimal characters.",
                              error=True)
                return
            try:
                result = self.review_store.propose_publication(
                    project_id=review["project_id"], review_id=review["review_id"],
                    artifact_path=artifact_path, artifact_sha256=artifact,
                    targets=targets, dkn_public_namespace=dkn,
                )
            except BaseException as exc:
                modal.message("Proposal refused", f"{type(exc).__name__}: {exc}", error=True)
                return
            self.window.set_text("status", "Publication proposal held for authorization\n" +
                                 self._hash(result["publication_plan"]["publication_plan_root"]))
            modal.close()
            self.refresh()

        modal.button("cancel", "Cancel", (430, 510, 128, 40), modal.close)
        modal.button("submit", "Create held proposal", (570, 510, 158, 40), submit)
        modal.style_button("submit", primary=True)
        return modal

    def explain_publication_proposal(self) -> None:
        modal = self._build_publication_window()
        modal.run_modal("artifact_path")

    def _constitution_rows(self,p):
        rows = [("Version","v0.1; revision advances are preferred and public-version changes require explicit user authorization",False),("Secrets","Raw credentials and private identity material refused",False),
                ("Local effects","UCM Gateway",False),("Remote work","AOK courthouse",False),
                ("Archive","Memory Vault preferred; P/PPI keeps causal roots",False),
                ("Mediation","Seven observable channels remain the denominator",False),
                ("Progress","Visible and never evidence",False),("Storage","Working and canonical locations stay distinct",False),
                ("Project root",self._hash(p["project_root"]),True)]
        rows.extend((f"Integration · {item['integration_id']}", item["status"], False)
                    for item in self.hub.integration_availability()["entries"])
        return rows

    def _dispatch_host(self, kind: str, payload: dict[str, Any],
                       progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
        p = self.current(); policy, attestation, now_ns = self.host_adapter.binding()
        policy = validate_host_adapter_policy(policy)
        attestation = validate_host_mediation_attestation(attestation, policy=policy,
            expected_session_root=attestation["session_root"],
            expected_subject_root=p["project_root"], now_ns=now_ns)
        gateway = self.hub.integration("UCM_OPERATIONAL_GATEWAY")
        if (gateway["status"] != "BOUND_EXTERNAL"
                or gateway["binding_root"] != policy["host_policy_root"]):
            raise HubRefusal("PIPPI_HOST_POLICY_UNBOUND")
        head = self.hub.verify()["journal_head"]
        proposal = build_host_launch_proposal(project_root=p["project_root"],
            session_root=attestation["session_root"],
            host_policy_root=policy["host_policy_root"],
            host_attestation_root=attestation["host_attestation_root"], kind=kind,
            payload=payload, expected_hub_head=head)
        proposed = self.hub.append("USER_LAUNCH_PROPOSED", {
            "project_id": p["project_id"], "kind": kind,
            "proposal_root": proposal["proposal_root"]}, expected_head=head)
        try:
            raw = self.host_adapter.dispatch(proposal, progress=progress)
            result = validate_host_launch_result(raw, proposal=proposal, policy=policy,
                attestation=attestation, now_ns=now_ns)
        except BaseException as exc:
            self.hub.append("USER_LAUNCH_REFUSED", {
                "proposal_event_root": proposed["event_root"],
                "proposal_root": proposal["proposal_root"],
                "code": getattr(exc, "code", type(exc).__name__)})
            raise
        self.hub.append("USER_LAUNCH_COMPLETED", {
            "proposal_event_root": proposed["event_root"],
            "proposal_root": proposal["proposal_root"],
            "launch_result_root": result["launch_result_root"], "status": "PASS"})
        return result

    def _recorded(self, kind: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        self.window.set_text("status",f"{kind}: running…")
        try:
            result=self._dispatch_host(kind,payload); status="PASS"
        except BaseException as exc:
            result={"error":type(exc).__name__,"detail":str(exc)};status="REFUSED"
        self.window.set_text("status",f"{kind}: {status}")
        return result if status == "PASS" else None

    def _command_payload(self, key: str) -> dict[str, Any]:
        command=self.current().get(key)
        if not command: raise HubRefusal("PIPPI_ENTRYPOINT_UNBOUND",key)
        return {"command": list(command), "workspace": self.current()["workspace"]}

    def launch_application(self) -> None:
        self._recorded("APPLICATION", self._command_payload("application_command"))
    def launch_verification(self) -> None:
        self._recorded("VERIFICATION", self._command_payload("verification_command"))
    def verify_then_launch(self) -> None:
        verified = self._recorded("VERIFICATION", self._command_payload("verification_command"))
        if verified is not None:
            self._recorded("APPLICATION", self._command_payload("application_command"))

    def open_github(self) -> None:
        value=self.current().get("github_url")
        if not value or not value.startswith("https://github.com/"): raise HubRefusal("PIPPI_GITHUB_URL_REFUSED")
        self._recorded("GITHUB", {"url": value})

    def open_tree(self) -> None:
        self._recorded("FILE_TREE", {"path": self.current()["workspace"]})

    def _reader_payload(self, path: str | None, role: str) -> dict[str, Any]:
        if not path: raise HubRefusal("PIPPI_DOCUMENT_UNBOUND")
        target=Path(self.current()["workspace"])/path
        if not target.resolve().is_relative_to(Path(self.current()["workspace"]).resolve()):
            raise HubRefusal("PIPPI_DOCUMENT_OUTSIDE_PROJECT")
        return {"path":str(target.resolve()),"document_role":role,
                "reader":"MOSAIC_READER_WIN32"}

    def open_readme(self) -> None:
        self._recorded("README",self._reader_payload(self.current().get("readme"),"README"))
    def open_docs(self) -> None:
        docs=self.current().get("docs",[])
        self._recorded("DOCUMENT",self._reader_payload(docs[0] if docs else None,"DOCUMENT"))
    def show_constitution(self) -> None:
        self.selected_tab="CONSTITUTION";self.window.set_workspace_tabs("workspace_tabs",WORKSPACE_TABS,self.selected_tab)
        self.show();self.window.set_text("status","Constitution projected from exact project state")

    def toggle_advanced(self)->None:
        self.advanced_visible=not self.advanced_visible
        for key in ("advanced_title","advanced","layout_nav","hash_mode","theme_mode"):
            self.window.show(key,self.advanced_visible)
        self.window.set_text("status","Advanced controls shown" if self.advanced_visible else "Advanced controls hidden")

    def _save_preferences(self,**changes)->None:
        values={key:self.preferences[key] for key in ("session_navigation","theme","density","default_tab","hash_display",
                                                       "pinned_projects","pinned_sessions","visible_project_fields")}
        values.update(changes);self.preferences=self.portfolio.save_preferences(build_preferences(**values));self.show()

    def toggle_navigation(self)->None:
        self._save_preferences(session_navigation="TOP" if self.preferences["session_navigation"]=="LEFT" else "LEFT")
        self.apply_navigation_layout();self.window.set_text("status","Session navigation layout saved")

    def toggle_hash_display(self)->None:
        self._save_preferences(hash_display="FULL" if self.preferences["hash_display"]=="ABBREVIATED" else "ABBREVIATED")
        self.window.set_text("status","Hash display preference saved")

    def toggle_theme(self)->None:
        theme="high-contrast-dark" if self.preferences["theme"]=="signature-dark" else "signature-dark"
        self._save_preferences(theme=theme);self.window.set_text("status",f"Theme {theme} saved; applies on next launch")

    def apply_navigation_layout(self)->None:
        self.window.relayout()

    def _relayout(self, width: int, height: int) -> None:
        """Fit the native dashboard at its declared minimum and at scaled DPIs."""
        wide = width >= 1400
        side_x = 28
        side_w = 440 if wide else 380
        main_x = side_x + side_w + 32
        main_w = max(1, width - main_x - 28)
        action_y = max(510, height - 250)
        button_y = action_y + 28
        body_bottom = action_y - 32
        advanced_x = main_x + (390 if wide else 376)
        layout_w, hash_w, theme_w = ((150, 130, max(80, main_w - 690)) if wide
                                     else (120, 100, max(58, main_w - 626)))
        self.window.move_many({
            "heading": (210, 24, max(300, width - 620), 34),
            "boundary": (210, 60, max(360, width - 620), 24),
            "summary": (width - 370, 24, 342, 56),
            "hub_state": (width - 370, 80, 202, 28),
            "refresh": (width - 164, 80, 136, 28),
            "project_heading": (side_x, 104, side_w, 28),
            "projects": (side_x, 138, side_w, 250),
            "status": (side_x, min(height - 126, 716), side_w, 92),
        })

        top_requested = self.preferences["session_navigation"] == "TOP"
        top_mode = top_requested and height >= 860
        if top_mode:
            detail_y = 330
            self.window.move_many({
                "projects": (side_x, 138, side_w, max(250, height - 194)),
                "session_heading": (main_x, 104, main_w, 26),
                "sessions": (main_x, 134, main_w, 84),
                "workspace_tabs": (main_x, 232, main_w, 38),
                "detail_title": (main_x, 282, main_w, 40),
            })
        else:
            detail_y = 216
            self.window.move_many({
                "session_heading": (side_x, 410, side_w, 28),
                "sessions": (side_x, 444, side_w, max(150, min(250, height - 610))),
                "workspace_tabs": (main_x, 112, main_w, 38),
                "detail_title": (main_x, 164, main_w, 42),
            })
        self.window.set_text("session_heading", "Concurrent sessions")
        focus_y = detail_y
        activity_y = focus_y + 100
        body_h = max(80, body_bottom - activity_y)
        queue_w = min(320, max(224, int(main_w * 0.36)))
        detail_x = main_x + queue_w + 22
        detail_w = max(300, main_x + main_w - detail_x)
        self.window.move_many({
            "focus_heading": (main_x, focus_y, 70, 22),
            "focus_state": (main_x + 80, focus_y - 6, 170, 30),
            "focus_headline": (main_x, focus_y + 32, max(260, main_w - 230), 30),
            "focus_reason": (main_x, focus_y + 64, max(260, main_w - 230), 24),
            "focus_action": (main_x + main_w - 210, focus_y + 34, 210, 42),
            "activity": (main_x, activity_y, main_w, body_h),
            "review_queue_heading": (main_x, activity_y, queue_w, 24),
            "review_queue": (main_x, activity_y + 30, queue_w, max(80, body_h - 30)),
            "review_detail_heading": (detail_x, activity_y, max(120, detail_w - 190), 24),
            "review_state": (detail_x + max(120, detail_w - 180), activity_y - 6, min(180, detail_w), 30),
            "review_detail": (detail_x, activity_y + 30, detail_w, max(80, body_h - 30)),
        })
        self.window.set_table_column_widths("projects", (max(104, int(side_w * 0.34)),
                                                          max(120, int(side_w * 0.66) - 8)))
        self.window.set_table_column_widths("sessions", (max(104, int(side_w * 0.34)),
                                                          max(120, int(side_w * 0.66) - 8)))
        self.window.set_table_column_widths("review_queue", (max(120, queue_w - 8),))

        if wide:
            run_x, inspect_x = main_x, main_x + 524
            regular = {
                "run_group": (run_x, action_y, 490, 24),
                "both": (run_x, button_y, 182, 40), "launch": (run_x + 194, button_y, 158, 40),
                "verify": (run_x + 364, button_y, 138, 40),
                "inspect_group": (inspect_x, action_y, max(1, width - inspect_x - 28), 24),
                "readme": (inspect_x, button_y, 84, 40), "docs": (inspect_x + 96, button_y, 84, 40),
                "tree": (inspect_x + 192, button_y, 84, 40), "github": (inspect_x + 288, button_y, 84, 40),
            }
            review_positions = {
                "review_group": (main_x, action_y, 320, 24),
                "review_verify": (main_x, button_y, 98, 40), "review_run": (main_x + 110, button_y, 98, 40),
                "review_substance": (main_x + 220, button_y, 100, 40),
                "correspond_group": (main_x + 342, action_y, 320, 24),
                "review_prepare": (main_x + 342, button_y, 166, 40),
                "review_import": (main_x + 520, button_y, 142, 40),
                "decide_group": (main_x + 684, action_y, max(1, main_w - 684), 24),
                "review_compare": (main_x + 684, button_y, 92, 40),
                "review_publish": (main_x + 788, button_y, 108, 40),
            }
        else:
            inspect_x = main_x + 432
            regular = {
                "run_group": (main_x, action_y, 410, 24),
                "both": (main_x, button_y, 146, 40), "launch": (main_x + 154, button_y, 130, 40),
                "verify": (main_x + 292, button_y, 112, 40),
                "inspect_group": (inspect_x, action_y, max(1, main_w - 432), 24),
                "readme": (inspect_x, button_y, 66, 40), "docs": (inspect_x + 72, button_y, 60, 40),
                "tree": (inspect_x + 138, button_y, 60, 40), "github": (inspect_x + 204, button_y, 70, 40),
            }
            correspond_x = main_x + 260
            decide_x = main_x + 526
            review_positions = {
                "review_group": (main_x, action_y, 244, 24),
                "review_verify": (main_x, button_y, 68, 40), "review_run": (main_x + 76, button_y, 76, 40),
                "review_substance": (main_x + 160, button_y, 92, 40),
                "correspond_group": (correspond_x, action_y, 250, 24),
                "review_prepare": (correspond_x, button_y, 128, 40),
                "review_import": (correspond_x + 136, button_y, 112, 40),
                "decide_group": (decide_x, action_y, max(1, main_w - 526), 24),
                "review_compare": (decide_x, button_y, 76, 40),
                "review_publish": (decide_x + 84, button_y, 94, 40),
            }
        self.window.move_many({**regular, **review_positions})
        govern_y = action_y + 82
        self.window.move_many({
            "govern_group": (main_x, govern_y, main_w, 24),
            "constitution": (main_x, govern_y + 28, 214, 40),
            "advanced_toggle": (main_x + 226, govern_y + 28, 144, 40),
            "review_boundary": (main_x, govern_y + 4, main_w, 28),
            "review_progress_heading": (main_x, govern_y + 42, 120, 22),
            "review_progress": (main_x, govern_y + 66, main_w, max(42, height - (govern_y + 76))),
            "advanced_title": (advanced_x, govern_y, 150, 24),
            "advanced": (advanced_x + 154, govern_y, max(1, main_x + main_w - advanced_x - 154), 24),
            "layout_nav": (advanced_x, govern_y + 28, layout_w, 32),
            "hash_mode": (advanced_x + layout_w + 8, govern_y + 28, hash_w, 32),
            "theme_mode": (advanced_x + layout_w + hash_w + 16, govern_y + 28, theme_w, 32),
        })
        if top_requested and not top_mode:
            self.window.set_text("status", "Compact-height layout\nSessions remain in the left rail until the window is taller")
    def run(self) -> int:
        try:
            return self.window.run()
        finally:
            self.logo.close()


def launch_dashboard(data_root: Path | None = None,
                     host_adapter: HostLaunchAdapter | None = None) -> int:
    hub=PippiHub(data_root); PippiSplash().run(hub.verify)
    return Dashboard(hub, host_adapter=host_adapter).run()


def probe_dashboard(data_root: Path | None = None) -> dict[str, Any]:
    """Construct the native dashboard without showing it or dispatching effects."""
    hub = PippiHub(data_root)
    verified = hub.verify()
    dashboard = Dashboard(hub)
    try:
        gateway = hub.integration("UCM_OPERATIONAL_GATEWAY")
        return {
            "schema": "mosaic.ucm.pippi-dashboard-positive-probe.v0.1",
            "status": "PASS",
            "native_ui": "MOSAIC_WIN32",
            "project_count": len(dashboard.projects),
            "journal_head": verified["journal_head"],
            "integration_registry_root": verified["integration_registry_root"],
            "operational_gateway_status": gateway["status"],
            "host_effect_dispatch": "DISABLED_UNLESS_BOUND_EXTERNAL",
            **__import__("ucm.amcas", fromlist=["BOUNDARY"]).BOUNDARY,
        }
    finally:
        dashboard.window.close()
        dashboard.logo.close()



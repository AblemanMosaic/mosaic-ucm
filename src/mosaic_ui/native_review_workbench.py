"""Ontology-driven Mosaic UI review workbench for an owned Win32 window."""
from __future__ import annotations

import copy
import hashlib
import platform
import sys
from pathlib import Path
from typing import Any, Callable

from mosaic_ui_std.signature import resolve_signature_theme

from .branding import APPLICATION_ID, verified_logo_path
from .canonical import atomic_write, canonical_bytes, commitment
from .model import UIRefusal
from .review_ontology import build_review_ontology, validate_review_ontology
from .review_session import REVIEW_MODES, ReviewSession


SNAPSHOT_NAME = "mosaic-ui-native-review-snapshot.json"
REBUILD_CONDITIONS = {"theme", "density", "direction"}
NATIVE_REVIEW_MINIMUM_VIEWPORT = (800, 720)
NATIVE_REVIEW_RESIZE_VIEWPORTS = ((1440, 900), (1120, 760), (840, 720), (1440, 900))


class NativeReviewModel(ReviewSession):
    """Closed interaction state shared by the native shell and its tests."""

    def __init__(self, ontology: dict[str, Any] | None = None, *, subject_id: str | None = None,
                 theme_id: str = "signature-dark", density_id: str = "comfortable") -> None:
        super().__init__(
            ontology, realizer="WIN32", subject_id=subject_id,
            theme_id=theme_id, density_id=density_id,
        )
        self.groups = {item["group_id"]: item for item in self.ontology["groups"]}
        self.snapshot_path: str | None = None

    def exercise_state(self) -> None:
        """Advance only the explicit specimen-state exercise control."""
        states = self.applicable_states()
        if len(states) < 2:
            raise UIRefusal("REVIEW_SESSION_ACTION_NOT_APPLICABLE", "EXERCISE_STATE")
        current = self.conditions["state"]
        self.conditions["state"] = states[(states.index(current) + 1) % len(states)] if current in states else states[0]
        self._record("EXERCISE_STATE", "state", self.conditions["state"])

    def snapshot(self) -> dict[str, Any]:
        value = {
            "schema": "mosaic.ui.native-review-snapshot.v0.1",
            "ontology_commitment": self.ontology["commitment"],
            "subject": copy.deepcopy(self.subject),
            "conditions": copy.deepcopy(self.conditions),
            "inspection_view": self.view_id,
            "events": copy.deepcopy(self.events),
            "review_session": self.state(),
            "host_realizer": "WIN32",
            "standing": "LOCAL_CANDIDATE_EVIDENCE",
            "authority_effect": "NONE",
            "claim_boundary": "NATIVE_REVIEW_SNAPSHOT_RECORDS_LOCAL_SELECTIONS_AND_DOES_NOT_ESTABLISH_RELEASE_ADMISSION",
        }
        value["commitment"] = commitment("MOSAIC.UI.NATIVE_REVIEW_SNAPSHOT.v0.1", value)
        return value

    def export_snapshot(self, root: Path) -> dict[str, Any]:
        root = root.resolve()
        root.mkdir(parents=True, exist_ok=True)
        target = root / SNAPSHOT_NAME
        snapshot = self.snapshot()
        data = canonical_bytes(snapshot) + b"\n"
        atomic_write(target, data)
        self.snapshot_path = str(target)
        self._record("EXPORT_SNAPSHOT", "local", target.name)
        receipt = {
            "schema": "mosaic.ui.native-review-export.v0.1",
            "path": str(target), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "snapshot_commitment": snapshot["commitment"],
            "disposition": "COMPLETE", "authority_effect": "NONE",
        }
        receipt["commitment"] = commitment("MOSAIC.UI.NATIVE_REVIEW_EXPORT.v0.1", receipt)
        return receipt


def _inspection_rows(model: NativeReviewModel) -> list[tuple[str, str, bool]]:
    subject = model.subject
    metadata = subject.get("metadata", {})
    review_contract = subject["review"]
    current_review = model.reviews[model.subject_id]
    progress = model.progress()
    kind = metadata.get("kind", "Composite")
    role = metadata.get("semantic_role", subject["subject_type"].lower())
    realized = set(metadata.get("realized_by", ()))
    scope = model.action_scope()
    state_row = (("Interaction state", model.conditions["state"], False)
                 if scope["state_control_visible"]
                 else ("Review lens", scope["state_control_context"].replace("_", " ").title(), False))
    rows = {
        "anatomy": [
            ("Review", current_review["disposition"].replace("_", " ").title(), False),
            ("Progress", f"{progress['reviewed']} of {progress['total']} subjects", False),
            ("Subject", subject["label"], False), ("Kind", kind, True),
            ("Role", role, False), state_row,
            ("Value", repr(model.specimen_values[model.subject_id]), False),
        ],
        "accessibility": [
            ("Name", subject["label"], False), ("Role", role, False),
            ("Keyboard", " / ".join(metadata.get("keyboard", ())) or "Not interactive", False),
            ("Direction", model.conditions["direction"], False),
            ("Preference", model.conditions["preference"], False),
        ],
        "tokens": [
            ("Profile", f"{model.ontology['profile_id']} {model.ontology['profile_version']}", False),
            ("Theme", model.conditions["theme"], False),
            ("Density", model.conditions["density"], False),
            ("Locale", model.conditions["locale"], False),
        ],
        "parity": [(name, "Catalog realized" if name in realized else "No item claim", False)
                   for name in ("HEADLESS", "BROWSER", "WIN32")],
        "evidence": [
            (f"Evidence {index + 1}", value, True)
            for index, value in enumerate(metadata.get("evidence", ())[:3])
        ] + [
            ("Automated", ", ".join(review_contract["automated_checks"]), False),
            ("Assisted", ", ".join(review_contract["assisted_checks"]), False),
            ("Human", ", ".join(review_contract["human_checks"]), False),
            ("Ontology", model.ontology["commitment"][:20] + "...", True),
        ],
        "delivery": [
            ("Module", metadata.get("delivery", {}).get("component_module", "Composite/profile closure"), True),
            ("Pathways", ", ".join(metadata.get("delivery", {}).get("shared_pathways", ())
                                     or metadata.get("realizer_pathways", ())) or "Subject dependent", False),
            ("Kinds", ", ".join(subject["component_kinds"]) or "None", False),
        ],
        "lifecycle": [
            ("Version", model.ontology["profile_version"], False),
            ("Standing", subject["standing"], False),
            ("Authority", "NONE", False),
            ("Compatibility", "Pre-1.0 additive catalog", False),
        ],
    }
    return rows[model.view_id]


class _NativeReviewShellV1:
    SHELL_VERSION = "LEGACY_V1"

    def __init__(self, model: NativeReviewModel, *, width: int, height: int, export_root: Path) -> None:
        from . import win32
        from .win32_image import NativeImage

        self.win32 = win32
        self.model = model
        self.export_root = export_root
        self.rebuild_requested = False
        if win32.shell32.SetCurrentProcessExplicitAppUserModelID(APPLICATION_ID) < 0:
            raise OSError("Could not establish Mosaic UI Review taskbar identity")
        self.logo = NativeImage(verified_logo_path())
        tokens = resolve_signature_theme(model.conditions["theme"], model.conditions["density"])["tokens"]
        if self.SHELL_VERSION == "SIGNATURE_V3":
            tokens = copy.deepcopy(tokens)
            for role, size in {"body": 12, "heading": 15, "metric": 22, "mono": 11, "title": 20}.items():
                tokens["typography"]["roles"][role]["size"] = size
        self.window = win32.NativeWindow(
            "Mosaic UI Review Workbench", tokens=tokens, width=width, height=height,
            rtl=model.conditions["direction"] == "RTL", error_status=("status", "Native review callback refused"),
        )
        if self.SHELL_VERSION == "SIGNATURE_V3":
            self.window.set_client_size(width, height)
        self.window.set_icon(self.logo)
        self.width, self.height = width, height
        self.group_labels = {item["label"]: item["group_id"] for item in model.ontology["groups"]}
        self.subject_labels: dict[str, str] = {}
        self.view_labels = {item["label"]: item["view_id"] for item in model.ontology["inspection_views"]}
        self.mode_labels = {"Explore": "EXPLORE", "Guided": "GUIDED_REVIEW", "Changes": "CHANGES"}
        self.specimen_keys: dict[str, str] = {}
        self.specimen_extras: dict[str, tuple[str, ...]] = {}
        self.condition_rects: dict[str, tuple[tuple[int, int, int, int], tuple[int, int, int, int]]] = {}
        self.action_rects: dict[str, tuple[int, int, int, int]] = {}
        self.static_action_rects: dict[str, tuple[int, int, int, int]] = {}
        self.tree_expanded = True
        self._build()
        self.refresh("Ready for native review")

    def close(self) -> None:
        self.logo.close()

    def _build(self) -> None:
        w, h, window = self.width, self.height, self.window
        left_w, right_w, gap = 226, 350, 14
        center_x = 20 + left_w + gap
        right_x = w - 20 - right_w
        center_w = right_x - gap - center_x
        content_top, content_bottom = 210, h - 88

        window.image("brand.logo", self.logo, (20, 16, 34, 34), name="Mosaic UI")
        window.label("title", "Mosaic UI", (64, 10, 310, 32), style="title")
        window.label("subtitle", "Signature Review Workbench / governed visual evidence", (66, 43, 330, 22), style="quiet")
        window.label("mode.label", "WORKSPACE", (402, 10, 390, 18), style="quiet")
        selected_mode = next(label for label, value in self.mode_labels.items() if value == self.model.mode)
        window.segmented("review.mode", tuple(self.mode_labels), (400, 30, 390, 34),
                         selected=selected_mode, command=self._set_mode)
        window.label("progress.label", "", (810, 10, 198, 20), style="quiet")
        window.progress("review.progress", (810, 37, 198, 18))
        window.badge("standing", (w - 250, 20, 220, 28))
        window.set_badge("standing", "LOCAL CANDIDATE", "accent")

        conditions = list(self.model.ontology["conditions"])
        rows = (conditions[:5], conditions[5:])
        for row_index, row in enumerate(rows):
            y = 80 + row_index * 58
            cell_w = (w - 40 - (len(row) - 1) * 8) // len(row)
            for index, spec in enumerate(row):
                x = 20 + index * (cell_w + 8)
                condition_id = spec["condition_id"]
                self.condition_rects[condition_id] = ((x, y, cell_w, 18), (x, y + 19, cell_w, 32))
                label = "STATE - SIMULATED" if condition_id == "state" else spec["label"].upper()
                window.label(f"condition.{condition_id}.label", label, (x, y, cell_w, 18), style="quiet")
                options = list(self.model.applicable_states()) if condition_id == "state" else spec["options"]
                selected = options.index(self.model.conditions[condition_id])
                window.combo(
                    f"condition.{condition_id}", options, (x, y + 19, cell_w, 32), selected=selected,
                    command=lambda value, key=condition_id: self._set_condition(key, value),
                )

        window.label("catalog.label", "CATALOG", (20, content_top, left_w, 20), style="quiet")
        group_values = list(self.group_labels)
        selected_group = next(label for label, value in self.group_labels.items() if value == self.model.group_id)
        window.combo("catalog.group", group_values, (20, content_top + 22, left_w, 34),
                     selected=group_values.index(selected_group), command=self._select_group)
        subject_values = self._refresh_subject_labels()
        selected_subject = next(label for label, value in self.subject_labels.items() if value == self.model.subject_id)
        window.listbox("catalog.subject", subject_values, (20, content_top + 66, left_w, content_bottom - content_top - 66),
                       selected=subject_values.index(selected_subject), command=self._select_subject)

        window.label("subject.title", "", (center_x, content_top, center_w - 110, 30), style="heading")
        window.badge("subject.type", (center_x + center_w - 106, content_top, 106, 26))
        window.label("review.question", "", (center_x, content_top + 32, center_w, 48), style="body")
        window.segmented(
            "state.matrix", self.model.applicable_states(),
            (center_x, content_top + 82, center_w, 34), selected=self.model.conditions["state"],
            command=lambda value: self._set_condition("state", value),
        )
        window.label("state.context", "", (center_x, content_top + 82, center_w, 34), style="quiet")
        specimen_box = (center_x, content_top + 122, center_w, 220)
        sx, sy, sw, _ = specimen_box
        window.label("specimen.heading", "Native specimen - live interaction", (sx, sy, sw, 26), style="heading")
        self._build_specimens(sx + 24, sy + 32, sw - 48, 182)
        if set(self.specimen_keys) != set(self.model.subjects):
            raise UIRefusal("NATIVE_REVIEW_SPECIMEN_COVERAGE_REFUSED", "")
        window.label("subject.summary", "", (center_x, content_top + 346, center_w, 34), style="body")
        window.label("review.note.label", "REVIEW NOTE", (center_x, content_top + 382, center_w, 18), style="quiet")
        window.edit("review.note", "", (center_x, content_top + 400, center_w, 28), command=self._set_note)
        decision_y = content_top + 434
        decision_w = max(96, (center_w - 16) // 3)
        window.button("approve", "Approve", (center_x, decision_y, decision_w, 30),
                      lambda: self._set_disposition("APPROVED"))
        window.style_button("approve", primary=True)
        window.button("issue", "Flag issue", (center_x + decision_w + 8, decision_y, decision_w, 30),
                      lambda: self._set_disposition("ISSUE"))
        window.button("defer", "Defer", (center_x + (decision_w + 8) * 2, decision_y, decision_w, 30),
                      lambda: self._set_disposition("DEFERRED"))
        action_y = decision_y + 36
        action_w = max(82, (center_w - 24) // 4)
        window.button("previous", "Previous", (center_x, action_y, action_w, 30), self._previous)
        window.button("interact", "Exercise state", (center_x + action_w + 8, action_y, action_w, 30), self._exercise_state)
        window.button("next", "Next", (center_x + (action_w + 8) * 2, action_y, action_w, 30), self._next)
        window.button("snapshot", "Export evidence", (center_x + (action_w + 8) * 3, action_y, action_w, 30), self._snapshot)
        self.action_rects = {
            "previous": (center_x, action_y, action_w, 30),
            "interact": (center_x + action_w + 8, action_y, action_w, 30),
            "next": (center_x + (action_w + 8) * 2, action_y, action_w, 30),
            "snapshot": (center_x + (action_w + 8) * 3, action_y, action_w, 30),
        }
        static_action_w = max(96, (center_w - 16) // 3)
        self.static_action_rects = {
            "previous": (center_x, action_y, static_action_w, 30),
            "next": (center_x + static_action_w + 8, action_y, static_action_w, 30),
            "snapshot": (center_x + (static_action_w + 8) * 2, action_y, static_action_w, 30),
        }

        window.label("inspector.label", "INSPECTOR", (right_x, content_top, right_w, 20), style="quiet")
        view_values = list(self.view_labels)
        selected_view = next(label for label, value in self.view_labels.items() if value == self.model.view_id)
        window.combo("inspector.view", view_values, (right_x, content_top + 22, right_w, 34),
                     selected=view_values.index(selected_view), command=self._select_view)
        window.key_value("inspector.detail", "", (right_x, content_top + 66, right_w, content_bottom - content_top - 66), columns=1)
        window.label("status", "", (20, h - 62, w - 40, 30), style="quiet")

        for key in ("review.mode", "catalog.group", "catalog.subject", "state.matrix", "review.note", "approve", "issue",
                    "defer", "previous", "interact", "next", "snapshot", "inspector.view"):
            window.set_accessibility(key, name=key.replace(".", " ").title(), description="Mosaic UI native review control")

    def _build_specimens(self, x: int, y: int, width: int, height: int) -> None:
        window = self.window
        add = lambda kind, key: self.specimen_keys.__setitem__(f"component.{kind.lower().replace('_', '-')}", key)
        window.panel("spec.WINDOW", "Owned Win32 window surface", (x, y, width, height)); add("WINDOW", "spec.WINDOW")
        window.panel("spec.PANEL", "Panel / grouped content", (x, y, width, height)); add("PANEL", "spec.PANEL")
        button_gap = 10
        button_width = max(96, (width - button_gap * 2) // 3)
        window.button("spec.BUTTON", "Create project", (x, y + 45, button_width, 42),
                      lambda: self._record_interaction("Create project"))
        window.style_button("spec.BUTTON", primary=True)
        window.button("spec.BUTTON.cancel", "Cancel", (x + button_width + button_gap, y + 45, button_width, 42),
                      lambda: self._record_interaction("Cancel"))
        window.button("spec.BUTTON.delete", "Delete", (x + (button_width + button_gap) * 2, y + 45, button_width, 42),
                      lambda: self._record_interaction("Delete"))
        window.style_button("spec.BUTTON.delete", danger=True)
        self.specimen_extras["component.button"] = ("spec.BUTTON.cancel", "spec.BUTTON.delete")
        add("BUTTON", "spec.BUTTON")
        window.edit("spec.TEXT_FIELD", "Review subject name", (x, y + 42, width, 42), command=self._record_interaction); add("TEXT_FIELD", "spec.TEXT_FIELD")
        window.combo("spec.SELECT", ["Balanced", "Compact", "Evidence first"], (x, y + 42, width, 40), command=self._record_interaction); add("SELECT", "spec.SELECT")
        window.combo("spec.COMBOBOX", ["Button", "Data grid", "Dialog"], (x, y + 42, width, 40), command=self._record_interaction, editable=True); add("COMBOBOX", "spec.COMBOBOX")
        window.checkbox("spec.CHECKBOX", "Include native witness", (x, y + 48, width, 32), checked=True, command=self._record_interaction); add("CHECKBOX", "spec.CHECKBOX")
        window.radio_group("spec.RADIO_GROUP", ("Semantic", "Visual", "Evidence"), (x, y + 42, width, 44), selected="Semantic", command=self._record_interaction); add("RADIO_GROUP", "spec.RADIO_GROUP")
        window.segmented("spec.SEGMENTED", ("Overview", "States", "Receipts"), (x, y + 42, width, 44), selected="Overview", command=self._record_interaction); add("SEGMENTED", "spec.SEGMENTED")
        window.stepper("spec.STEPPER", ("Build", "Probe", "Review"), (x, y + 42, width, 52), selected=1, command=self._record_interaction); add("STEPPER", "spec.STEPPER")
        window.navigation("spec.NAVIGATION", ("Catalog", "Specimen", "Evidence"), (x, y + 42, width, 44), selected="Catalog", command=self._record_interaction); add("NAVIGATION", "spec.NAVIGATION")
        window.popup_menu("spec.MENU", "Open application menu", ("Open", "Export", "Inspect"), (x, y + 42, width, 44), self._record_interaction); add("MENU", "spec.MENU")
        window.tab_bar("spec.TAB_BAR", ("Anatomy", "Accessibility", "Tokens"), (x, y + 42, width, 44), selected="Anatomy", command=self._record_interaction); add("TAB_BAR", "spec.TAB_BAR")
        window.listbox("spec.TREE", ["[-] Mosaic UI", "  [-] Components", "      Button", "      Data grid"], (x, y, width, height), kind="tree", command=self._record_tree_interaction); add("TREE", "spec.TREE")
        window.label("spec.LABEL", "Semantic label specimen", (x, y + 46, width, 36), style="heading"); add("LABEL", "spec.LABEL")
        window.badge("spec.BADGE", (x, y + 46, 190, 32)); window.set_badge("spec.BADGE", "PASS LOCAL", "accent"); add("BADGE", "spec.BADGE")
        window.label("spec.STATUS", "Review ready / no unresolved refusals", (x, y + 46, width, 34), style="quiet"); add("STATUS", "spec.STATUS")
        window.progress("spec.PROGRESS", (x, y + 54, width, 20)); window.set_progress("spec.PROGRESS", 68); add("PROGRESS", "spec.PROGRESS")
        window.key_value("spec.KEY_VALUE", "Receipt binding", (x, y, width, height), columns=2); window.set_key_value("spec.KEY_VALUE", [("Standing", "LOCAL_CANDIDATE", False), ("Authority", "NONE", False), ("Kinds", "25", False), ("Host", "WIN32", False)]); add("KEY_VALUE", "spec.KEY_VALUE")
        window.table("spec.TABLE", ["Subject", "State", "Evidence"], (x, y, width, height)); window.set_rows("spec.TABLE", [("Button", "Idle", "Catalog"), ("Dialog", "Focused", "HWND"), ("Grid", "Pending", "Receipt")]); add("TABLE", "spec.TABLE")
        window.table("spec.DATA_GRID", ["ID", "Status", "Result"], (x, y, width, height), kind="data_grid", command=self._record_interaction); window.set_rows("spec.DATA_GRID", [("UI-025", "Ready", "Pass"), ("UI-024", "Review", "Local"), ("UI-023", "Refused", "Bounded")]); add("DATA_GRID", "spec.DATA_GRID")
        for table_key in ("spec.TABLE", "spec.DATA_GRID"):
            for index in range(3):
                self.win32.user32.SendMessageW(window.controls[table_key].hwnd, 0x101E, index, max(80, (width - 8) // 3))
        window.listbox("spec.LIST", ["Signature dark", "Signature light", "High contrast"], (x, y, width, height), command=self._record_interaction); add("LIST", "spec.LIST")
        window.notification("spec.NOTIFICATION", "The review completed and its receipt is available.", (x, y + 36, width, 58), tone="accent"); add("NOTIFICATION", "spec.NOTIFICATION")
        window.tooltip_anchor("spec.TOOLTIP", "Review evidence", "Opens exact witness references", (x, y + 44, width, 44), lambda: self._record_interaction("anchor activated")); add("TOOLTIP", "spec.TOOLTIP")
        window.button("spec.DIALOG", "Open confirmation dialog", (x, y + 44, width, 44), self._show_specimen_dialog); add("DIALOG", "spec.DIALOG")

        def details(subject_id: str, title: str, rows: list[tuple[str, str, bool]]) -> None:
            key = "spec." + subject_id
            window.key_value(key, title, (x, y, width, height), columns=2)
            window.set_key_value(key, rows)
            self.specimen_keys[subject_id] = key

        window.swatch_grid("spec.foundation.color", [
            ("Canvas", "canvas"), ("Surface", "surface"), ("Field", "field"),
            ("Text", "text"), ("Quiet", "text_quiet"), ("Accent", "accent"),
            ("Focus", "focus"), ("Pending", "pending"), ("Refused", "refused"),
        ], (x, y, width, height))
        self.specimen_keys["foundation.color"] = "spec.foundation.color"
        window.type_scale("spec.foundation.typography", [
            ("title", "Release evidence console"), ("metric", "42 checks"),
            ("heading", "Review outcome"), ("body", "Readable supporting copy"),
            ("mono", "mosaic.ui.receipt"),
        ], (x, y, width, height))
        self.specimen_keys["foundation.typography"] = "spec.foundation.typography"
        window.token_scale("spec.foundation.spacing", "Spacing scale in context", [
            ("xs", 4), ("sm", 8), ("md", 12), ("lg", 20), ("xl", 28),
        ], (x, y, width, height))
        self.specimen_keys["foundation.spacing"] = "spec.foundation.spacing"
        window.token_scale("spec.foundation.sizing", "Control and target sizes", [
            ("compact", 32), ("comfortable", 40), ("touch", 44), ("tile", 80),
        ], (x, y, width, height))
        self.specimen_keys["foundation.sizing"] = "spec.foundation.sizing"
        window.token_scale("spec.foundation.radii", "Radius roles", [
            ("none", 0), ("field", 4), ("control", 6), ("dialog", 6),
        ], (x, y, width, height))
        self.specimen_keys["foundation.radii"] = "spec.foundation.radii"
        details("foundation.icons", "Icon vocabulary and fallback", [
            ("Commands", "add edit search filter save export", False),
            ("History", "undo redo", False), ("Status", "close warning", False),
            ("Missing", "named question-mark fallback", False),
        ])
        window.button("spec.foundation.motion", "Play bounded 160 ms transition", (x, y + 52, width, 40), self._record_interaction)
        self.specimen_keys["foundation.motion"] = "spec.foundation.motion"
        window.listbox("spec.foundation.localization", [
            "English / Review evidence", "Arabic / مراجعة الأدلة", "RTL / mirrored order",
            "Fallback / [message unavailable]",
        ], (x, y, width, height), command=self._record_interaction)
        self.specimen_keys["foundation.localization"] = "spec.foundation.localization"

        patterns = {
            "pattern.command-bar": ("Enter command", "Open actions", "Run", "Receipt"),
            "pattern.filter-search": ("Enter query", "Choose scope", "Apply", "Results"),
            "pattern.selection-inspector": ("Select row", "Load details", "Compare", "Retain"),
            "pattern.confirmation": ("Request", "Review", "Confirm", "Outcome"),
            "pattern.progress-cancel": ("Start", "Observe", "Cancel", "Terminal"),
            "pattern.settings": ("Change", "Validate", "Apply", "Persist"),
            "pattern.receipt-review": ("Choose run", "Checks", "Evidence", "Export"),
        }
        for subject_id, steps in patterns.items():
            key = "spec." + subject_id
            window.stepper(key, steps, (x, y + 30, width, 80), selected=0, command=self._record_interaction)
            self.specimen_keys[subject_id] = key

        surfaces = {
            "surface.data-workspace": ("Search and filter", "Result grid", "Selection inspector", "Evidence status"),
            "surface.operational-dashboard": ("Navigation", "Metrics", "Active operations", "Evidence feed"),
            "surface.settings-workflow": ("Settings menu", "Configuration form", "Validation status", "Confirmation dialog"),
        }
        for subject_id, regions in surfaces.items():
            key = "spec." + subject_id
            window.stepper(key, regions, (x, y + 30, width, 100), selected=0, command=self._record_interaction)
            self.specimen_keys[subject_id] = key

        key = "spec.profile.mosaic-signature"
        window.table(key, ["Theme", "Comfortable", "Compact"], (x, y, width, height), kind="data_grid", command=self._record_interaction)
        window.set_rows(key, [
            ("Signature dark", "Ready", "Ready"), ("Signature light", "Ready", "Ready"),
            ("High contrast dark", "Ready", "Ready"),
        ])
        self.specimen_keys["profile.mosaic-signature"] = key
        key = "spec.delivery.ablation"
        plan = self.model.subjects["delivery.ablation"]["metadata"]["specimen"]["visual"]["plan"]
        window.table(key, ["Slice", "Selection", "Closure"], (x, y, width, height), kind="data_grid", command=self._record_interaction)
        window.set_rows(key, [
            ("Components", ", ".join(plan["selected_components"]), "Exact"),
            ("Realizer", plan["realizer"], f"{plan['retained_module_count']} modules"),
            ("Unused", str(len(plan["removed_component_modules"])), "Removed"),
        ])
        self.specimen_keys["delivery.ablation"] = key

    @staticmethod
    def _condition_layouts(
        specs: list[dict[str, Any]], mode: str, region: tuple[int, int, int, int],
    ) -> dict[str, tuple[tuple[int, int, int, int], tuple[int, int, int, int]]]:
        x0, y0, width, _height = region
        gap = 8
        weights = (1.0, 1.15, 1.0, 1.1, 1.0, 0.85, 1.0, 1.25, 1.15)
        rows = (specs,) if mode == "WIDE" else (specs[:5], specs[5:])
        result = {}
        offset = 0
        for row_index, row in enumerate(rows):
            row_weights = weights[offset:offset + len(row)]
            available = width - 24 - gap * (len(row) - 1)
            unit = available / sum(row_weights)
            x = x0 + 12
            y = y0 + 8 + row_index * 58
            for index, (spec, weight) in enumerate(zip(row, row_weights)):
                cell_width = x0 + width - 12 - x if index + 1 == len(row) else int(unit * weight)
                result[spec["condition_id"]] = ((x, y, cell_width, 16), (x, y + 19, cell_width, 32))
                x += cell_width + gap
            offset += len(row)
        return result

    def _set_narrow_view(self, value: str) -> None:
        if value not in {"Catalog", "Review", "Inspect"}:
            raise UIRefusal("NATIVE_REVIEW_NARROW_VIEW_REFUSED", value)
        self.narrow_view = value
        self.window.set_segmented("narrow.view", ("Catalog", "Review", "Inspect"), value)
        self._relayout(self.width, self.height)
        self.window.set_text("status", f"Narrow {value.lower()} surface / state and selection retained")

    def _relayout(self, width: int, height: int) -> None:
        adaptive = native_review_shell_v3_adaptive_layout(width, height)
        self.width, self.height = width, height
        self.adaptive_mode = adaptive["mode"]
        regions = adaptive["regions"]
        top, conditions, catalog = regions["top"], regions["conditions"], regions["catalog"]
        local, guide, specimen = regions["local"], regions["guide"], regions["specimen"]
        inspector, footer = regions["inspector"], regions["footer"]
        rects: dict[str, tuple[int, int, int, int]] = {
            "chrome.top": top, "chrome.conditions": conditions, "chrome.catalog": catalog,
            "chrome.local": local, "chrome.guide": guide, "chrome.inspector": inspector,
            "chrome.footer": footer,
        }

        if self.adaptive_mode == "NARROW":
            rects.update({
                "brand.logo": (12, 12, 32, 32), "title": (52, 8, 210, 24),
                "subtitle": (52, 31, 220, 18), "snapshot": (width - 144, 10, 132, 36),
                "review.mode": (12, 55, 300, 32), "narrow.view": (320, 55, width - 332, 32),
                "session": (-400, -400, 10, 10), "workspace": (-400, -400, 10, 10),
            })
        else:
            compact = self.adaptive_mode == "COMPACT"
            rects.update({
                "brand.logo": (16, 14, 32, 32), "title": (56, 8, 210, 24),
                "subtitle": (56, 31, 220, 18),
                "review.mode": (276 if not compact else 260, 14, 276 if not compact else 252, 34),
                "session": (566 if not compact else 526, 19, 260 if not compact else 190, 24),
                "workspace": (width - 292, 19, 138, 24), "snapshot": (width - 144, 13, 132, 36),
                "narrow.view": (-400, -400, 10, 10),
            })

        condition_layouts = self._condition_layouts(
            list(self.model.ontology["conditions"]), self.adaptive_mode, conditions,
        )
        self.condition_rects = condition_layouts
        scope = self.model.action_scope()
        condition_ids = [item["condition_id"] for item in self.model.ontology["conditions"]]
        state_index = condition_ids.index("state")
        for index, condition_id in enumerate(condition_ids):
            source_id = condition_ids[index - 1] if not scope["state_control_visible"] and index > state_index else condition_id
            label_rect, combo_rect = condition_layouts[source_id]
            rects[f"condition.{condition_id}.label"] = label_rect
            rects[f"condition.{condition_id}"] = combo_rect

        cx, cy, cw, ch = catalog
        rects.update({
            "catalog.search": (cx + 10, cy + 12, cw - 20, 34),
            "catalog.subject": (cx + 6, cy + 56, cw - 12, ch - 62),
        })

        mx, my, mw, _ = local
        if self.adaptive_mode == "WIDE":
            state_x = mx + max(408, mw - 428)
            rects.update({
                "subject.title": (mx + 16, my + 8, 250, 23), "subject.summary": (mx + 16, my + 31, 285, 20),
                "review.progress": (mx + 306, my + 42, 96, 4), "progress.label": (mx + 406, my + 32, 92, 22),
                "state.matrix": (state_x, my + 14, mx + mw - state_x - 12, 34),
                "state.context": (state_x, my + 15, mx + mw - state_x - 12, 32),
            })
        else:
            state_x = mx + min(232, max(196, mw // 3))
            rects.update({
                "subject.title": (mx + 14, my + 6, state_x - mx - 22, 23),
                "subject.summary": (mx + 14, my + 29, state_x - mx - 22, 20),
                "review.progress": (mx + 14, my + local[3] - 8, max(70, state_x - mx - 30), 4),
                "progress.label": (state_x - 86, my + 28, 78, 20),
                "state.matrix": (state_x, my + 12, mx + mw - state_x - 12, 34),
                "state.context": (state_x, my + 13, mx + mw - state_x - 12, 32),
            })

        gx, gy, gw, _ = guide
        if self.adaptive_mode == "WIDE":
            rects.update({
                "guide.title": (gx + 16, gy + 11, 220, 17),
                "review.question": (gx + 16, gy + 30, max(300, gw - 405), 50),
                "review.note": (gx + 16, gy + 92, min(456, gw - 32), 30),
            })
            widths = (68, 76, 82, 62, 56)
            action_x, action_y = gx + gw - 16 - sum(widths) - 24, gy + 53
        else:
            rects.update({
                "guide.title": (gx + 14, gy + 8, gw - 28, 17),
                "review.question": (gx + 14, gy + 27, gw - 28, 43),
                "review.note": (gx + 14, gy + 76, gw - 28, 29),
            })
            button_width = max(56, (gw - 52) // 5)
            widths = (button_width,) * 5
            action_x, action_y = gx + 14, gy + 111
        action_positions = {}
        cursor = action_x
        for key, button_width in zip(("previous", "approve", "issue", "defer", "next"), widths):
            action_positions[key] = (cursor, action_y, button_width, 30 if self.adaptive_mode != "WIDE" else 32)
            rects[key] = action_positions[key]
            cursor += button_width + 6
        rects["interact"] = (-400, -400, 10, 10)
        self.action_rects = {
            "previous": action_positions["previous"], "interact": rects["interact"],
            "next": action_positions["next"], "snapshot": rects["snapshot"],
        }
        self.static_action_rects = {
            "previous": action_positions["previous"], "next": action_positions["next"],
            "snapshot": rects["snapshot"],
        }

        sx, sy, sw, sh = specimen
        frame_width = min(720, sw - 48)
        frame_height = min(430, max(220, sh - 48))
        frame_x = sx + (sw - frame_width) // 2
        frame_y = sy + 22
        content_y = frame_y + 47
        specimen_rect = (frame_x + 56, content_y, frame_width - 112, max(80, frame_height - 102))
        rects.update({
            "specimen.frame": (frame_x, frame_y, frame_width, frame_height),
            "specimen.heading": (frame_x + 16, frame_y + 10, frame_width - 168, 24),
            "specimen.host": (frame_x + frame_width - 148, frame_y + 10, 132, 22),
            "specimen.meta": (frame_x + 16, frame_y + frame_height - 32, frame_width - 32, 22),
        })
        for key in set(self.specimen_keys.values()):
            rects[key] = specimen_rect
        for values in self.specimen_extras.values():
            for key in values:
                rects[key] = specimen_rect
        rects.update({
            "spec.BUTTON": (frame_x + 56, content_y + 35, 136, 42),
            "spec.BUTTON.cancel": (frame_x + 202, content_y + 35, 96, 42),
            "spec.BUTTON.delete": (frame_x + 308, content_y + 35, 96, 42),
        })

        ix, iy, iw, ih = inspector
        rects.update({
            "inspector.tabs.primary": (ix, iy, iw, 34), "inspector.tabs.secondary": (ix, iy + 34, iw, 34),
            "inspector.detail": (ix + 4, iy + 76, iw - 8, ih - 80),
            "standing": (14, footer[1] + 9, 104, 20), "catalog.count": (126, footer[1] + 9, 226, 20),
            "status": (366, footer[1] + 9, max(40, width - 380), 20),
        })
        window = self.window
        window.move_many({key: rect for key, rect in rects.items() if key in window.controls})
        self._apply_adaptive_visibility()
        window.invalidate()

    def _apply_adaptive_visibility(self) -> None:
        window = self.window
        narrow = self.adaptive_mode == "NARROW"
        catalog_visible = not narrow or self.narrow_view == "Catalog"
        review_visible = not narrow or self.narrow_view == "Review"
        inspector_visible = not narrow or self.narrow_view == "Inspect"
        scope = self.model.action_scope()
        active = self.specimen_keys.get(self.model.subject_id)
        active_specimens = {active, *self.specimen_extras.get(self.model.subject_id, ())} if active else set()
        all_specimens = set(self.specimen_keys.values())
        for values in self.specimen_extras.values():
            all_specimens.update(values)
        visibility = {key: catalog_visible for key in {"chrome.catalog", "catalog.search", "catalog.subject"}}
        visibility.update({key: review_visible for key in {
            "chrome.local", "chrome.guide", "specimen.frame", "subject.title", "subject.summary",
            "review.progress", "progress.label", "guide.title", "review.question", "review.note",
            "previous", "approve", "issue", "defer", "next", "specimen.heading", "specimen.host", "specimen.meta",
        }})
        visibility.update({key: inspector_visible for key in {
            "chrome.inspector", "inspector.tabs.primary", "inspector.tabs.secondary", "inspector.detail",
        }})
        visibility.update({key: review_visible and key in active_specimens for key in all_specimens})
        visibility.update({
            "narrow.view": narrow, "session": not narrow, "workspace": self.adaptive_mode == "WIDE",
            "state.matrix": review_visible and scope["state_control_visible"],
            "state.context": review_visible and not scope["state_control_visible"],
            "interact": False, "subject.type": False, "catalog.group": False, "inspector.view": False,
            "condition.state.label": scope["state_control_visible"],
            "condition.state": scope["state_control_visible"],
        })
        window.set_visibility({key: visible for key, visible in visibility.items() if key in window.controls})

    def _refresh_subject_labels(self) -> list[str]:
        marks = {"NEEDS_REVIEW": "[ ]", "APPROVED": "[OK]", "ISSUE": "[!]", "DEFERRED": "[-]"}
        subject_ids = self.model.groups[self.model.group_id]["subject_ids"]
        self.subject_labels = {
            f"{marks[self.model.reviews[subject_id]['disposition']]} {self.model.subjects[subject_id]['label']}": subject_id
            for subject_id in subject_ids
        }
        return list(self.subject_labels)

    def _set_mode(self, label: str) -> None:
        self.model.set_mode(self.mode_labels[label])
        self.refresh(f"Workspace set to {label}")

    def _select_group(self, label: str) -> None:
        self.model.select_group(self.group_labels[label])
        self.refresh("Catalog group selected")

    def _select_subject(self, label: str) -> None:
        self.model.select_subject(self.subject_labels[label])
        self.refresh("Review subject selected")

    def _select_view(self, label: str) -> None:
        self.model.select_view(self.view_labels[label])
        self.refresh("Inspector changed")

    def _set_disposition(self, disposition: str) -> None:
        self.model.set_disposition(disposition)
        self.refresh(f"{self.model.subject['label']} marked {disposition.replace('_', ' ').lower()}")

    def _set_note(self, value: str) -> None:
        self.model.set_note(value)
        self.refresh("Review note retained in the local session")

    def _previous(self) -> None:
        self.model.move(-1, changed_only=self.model.mode == "CHANGES")
        self.refresh("Previous review subject")

    def _next(self) -> None:
        self.model.move(1, unresolved_only=self.model.mode == "GUIDED_REVIEW",
                        changed_only=self.model.mode == "CHANGES")
        self.refresh("Next review subject")

    def _set_condition(self, condition_id: str, value: str) -> None:
        changed = self.model.conditions[condition_id] != value
        self.model.set_condition(condition_id, value)
        if changed and condition_id in REBUILD_CONDITIONS:
            self.rebuild_requested = True
            self.win32.user32.PostMessageW(self.window.hwnd, self.win32.WM_CLOSE, 0, 0)
            return
        self.refresh(f"{self.model.condition_specs[condition_id]['label']} set to {value}")

    def _exercise_state(self) -> None:
        self.model.exercise_state()
        self.refresh(f"State exercise advanced to {self.model.conditions['state']}")

    def _record_interaction(self, value: Any = "ACTIVATE") -> None:
        self.model.set_specimen_value(value)
        self.refresh(f"Specimen value changed: {value}")

    def _record_tree_interaction(self, value: str) -> None:
        if "Mosaic UI" in value or "Components" in value:
            self.tree_expanded = not self.tree_expanded
            items = (["[-] Mosaic UI", "  [-] Components", "      Button", "      Data grid"]
                     if self.tree_expanded else ["[+] Mosaic UI"])
            self.window.set_list_items("spec.TREE", items, items[0])
            self._record_interaction("expanded" if self.tree_expanded else "collapsed")
            return
        self._record_interaction(value.strip())

    def _show_specimen_dialog(self) -> None:
        confirmed = self.window.confirm(
            "Publish component profile?",
            "This records the selected conditions and creates a local receipt.",
        )
        self._record_interaction("published" if confirmed else "cancelled")

    def _reset_state(self) -> None:
        self.model.set_condition("state", self.model.condition_specs["state"]["default"])
        self.refresh("Component state reset")

    def _snapshot(self) -> None:
        receipt = self.model.export_snapshot(self.export_root)
        self.refresh(f"Snapshot saved: {Path(receipt['path']).name} / {receipt['sha256'][:12]}")

    def refresh(self, status: str) -> None:
        window, subject = self.window, self.model.subject
        metadata = subject.get("metadata", {})
        selected_group = next(label for label, value in self.group_labels.items() if value == self.model.group_id)
        subject_values = self._refresh_subject_labels()
        selected_subject = next(label for label, value in self.subject_labels.items() if value == self.model.subject_id)
        selected_view = next(label for label, value in self.view_labels.items() if value == self.model.view_id)
        selected_mode = next(label for label, value in self.mode_labels.items() if value == self.model.mode)
        window.set_combo_value("catalog.group", selected_group)
        window.set_list_items("catalog.subject", subject_values, selected_subject)
        window.set_combo_value("inspector.view", selected_view)
        window.set_segmented("review.mode", tuple(self.mode_labels), selected_mode)
        window.set_text("subject.title", subject["label"])
        window.set_badge("subject.type", subject["subject_type"], "accent")
        window.set_text("subject.summary", subject["summary"])
        review = self.model.reviews[self.model.subject_id]
        progress = self.model.progress()
        if self.model.mode == "EXPLORE":
            question = "Purpose: " + subject["review"]["purpose"]
        elif self.model.mode == "CHANGES":
            question = f"Baseline comparison: {review['disposition'].replace('_', ' ').title()} / {len(self.model.changed_subject_ids())} changed subjects"
        else:
            question = "Review question: " + subject["review"]["question"]
        window.set_text("review.question", question)
        window.set_text("review.note", review["note"])
        window.set_text("progress.label", f"GUIDED PROGRESS  {progress['reviewed']} / {progress['total']}")
        window.set_progress("review.progress", progress["percent"])
        states = self.model.applicable_states()
        window.set_combo_items("condition.state", states, self.model.conditions["state"])
        window.set_segmented("state.matrix", states, self.model.conditions["state"])
        window.set_key_value("inspector.detail", _inspection_rows(self.model))
        kind = metadata.get("kind")
        active = self.specimen_keys.get(self.model.subject_id)
        if active is None:
            raise UIRefusal("REVIEW_SPECIMEN_ABSENT", self.model.subject_id)
        active_controls = {active, *self.specimen_extras.get(self.model.subject_id, ())}
        all_specimen_controls = set(self.specimen_keys.values())
        for values in self.specimen_extras.values():
            all_specimen_controls.update(values)
        window.set_visibility({key: key in active_controls for key in all_specimen_controls})
        state = self.model.conditions["state"]
        scope = self.model.action_scope()
        state_controls_visible = scope["state_control_visible"]
        window.set_visibility({
            "condition.state.label": state_controls_visible,
            "condition.state": state_controls_visible,
            "state.matrix": state_controls_visible,
            "state.context": not state_controls_visible,
            "interact": state_controls_visible,
        })
        window.set_text("state.context", scope["state_control_context"])
        state_label_rect, state_combo_rect = self.condition_rects["state"]
        viewport_label_rect, viewport_combo_rect = self.condition_rects["viewport"]
        window.move("condition.viewport.label", viewport_label_rect if state_controls_visible else state_label_rect)
        window.move("condition.viewport", viewport_combo_rect if state_controls_visible else state_combo_rect)
        action_rects = self.action_rects if state_controls_visible else self.static_action_rects
        for key, rect in action_rects.items():
            window.move(key, rect)
        window.set_text("specimen.heading", "Native specimen - " +
                        ("live interaction" if scope["specimen_interaction_enabled"] else "inspection only"))
        for key in active_controls:
            window.set_enabled(key, scope["specimen_interaction_enabled"] if metadata.get("interactive") else True)
        window.set_enabled("review.note", scope["review_note_enabled"])
        for key in ("approve", "issue", "defer"):
            window.set_enabled(key, scope["disposition_enabled"])
        window.set_enabled("condition.state", scope["state_exercise_enabled"])
        window.set_enabled("state.matrix", scope["state_exercise_enabled"])
        window.set_enabled("interact", scope["state_exercise_enabled"])
        window.set_enabled("previous", scope["previous_enabled"])
        window.set_enabled("next", scope["next_enabled"])
        if kind == "PROGRESS":
            mode = "indeterminate" if state == "PENDING" else "failed" if state == "REFUSED" \
                else "paused" if state == "DISABLED" else "determinate"
            window.set_progress_state(active, mode, 68 if state != "IDLE" else 32)
        if kind == "NOTIFICATION":
            window.set_notification(active, "Review refused within the declared boundary." if state == "REFUSED" else "The review completed and its receipt is available.", "refused" if state == "REFUSED" else "accent")
        for key in active_controls:
            window.set_accessibility(key, name=window.text(key) or subject["label"], description=subject["summary"],
                                     value=repr(self.model.specimen_values[self.model.subject_id]),
                                     default_action="Interact" if metadata.get("interactive") else "")
        state_status = (f"SIMULATED: {state} ({len(states)} applicable)" if state_controls_visible
                        else f"LENS: {scope['state_control_context']}")
        window.set_text("status", f"{status} | {state_status} | VALUE: {self.model.specimen_values[self.model.subject_id]!r} | APPLIED: WIN32/{self.model.conditions['theme']}/{self.model.conditions['density']} | {self.model.ontology['commitment'][:12]}")


def native_review_shell_v2_layout(width: int, height: int) -> dict[str, tuple[int, int, int, int]]:
    """Return the stable browser-inspired V2 regions without creating native controls."""
    minimum_width, minimum_height = NATIVE_REVIEW_MINIMUM_VIEWPORT
    if width < minimum_width or height < minimum_height:
        raise UIRefusal("NATIVE_REVIEW_VIEWPORT_REFUSED", f"{width}x{height}")
    margin, gap = 12, 12
    top_h, conditions_y, conditions_h = 60, 68, 62
    workspace_y, footer_h = 140, 34
    workspace_bottom = height - footer_h - 8
    left_w = 220 if width >= 1240 else 202
    right_w = 310 if width >= 1240 else 284
    center_x = margin + left_w + gap
    right_x = width - margin - right_w
    center_w = right_x - gap - center_x
    local_h, guide_h = 96, 132
    guide_y = workspace_y + local_h
    specimen_y = guide_y + guide_h + 10
    return {
        "top": (0, 0, width, top_h),
        "conditions": (0, conditions_y, width, conditions_h),
        "catalog": (margin, workspace_y, left_w, workspace_bottom - workspace_y),
        "local": (center_x, workspace_y, center_w, local_h),
        "guide": (center_x, guide_y, center_w, guide_h),
        "specimen": (center_x, specimen_y, center_w, workspace_bottom - specimen_y),
        "inspector": (right_x, workspace_y, right_w, workspace_bottom - workspace_y),
        "footer": (0, height - footer_h, width, footer_h),
    }


class _NativeReviewShellV2(_NativeReviewShellV1):
    """Signature V2 shell: new composition, unchanged governed review behavior."""

    SHELL_VERSION = "SIGNATURE_V2"

    def _build(self) -> None:
        w, h, window = self.width, self.height, self.window
        regions = native_review_shell_v2_layout(w, h)
        top = regions["top"]
        conditions = regions["conditions"]
        catalog = regions["catalog"]
        local = regions["local"]
        guide = regions["guide"]
        specimen = regions["specimen"]
        inspector = regions["inspector"]
        footer = regions["footer"]

        # Structural bands are created first so native controls remain above them in z-order.
        for key, rect in (
            ("chrome.top", top), ("chrome.conditions", conditions),
            ("chrome.catalog", catalog), ("chrome.local", local),
            ("chrome.guide", guide), ("chrome.specimen", specimen),
            ("chrome.inspector", inspector), ("chrome.footer", footer),
        ):
            window.panel(key, "", rect)

        window.image("brand.logo", self.logo, (16, 13, 34, 34), name="Mosaic UI")
        window.label("title", "Mosaic UI", (60, 8, 222, 25), style="heading")
        window.label("subtitle", "Signature Review Workbench", (60, 31, 222, 20), style="quiet")
        selected_mode = next(label for label, value in self.mode_labels.items() if value == self.model.mode)
        window.segmented("review.mode", tuple(self.mode_labels), (300, 14, 284, 34),
                         selected=selected_mode, command=self._set_mode)
        window.label("progress.label", "", (600, 8, 178, 20), style="quiet")
        window.progress("review.progress", (600, 33, 178, 12))
        window.badge("standing", (w - 330, 16, 160, 28))
        window.set_badge("standing", "LOCAL CANDIDATE", "accent")
        window.button("snapshot", "Export evidence", (w - 158, 13, 142, 36), self._snapshot)
        window.style_button("snapshot", primary=True)

        condition_specs = list(self.model.ontology["conditions"])
        condition_gap = 8
        condition_weights = (1.0, 1.15, 1.1, 1.2, 1.05, 0.8, 1.0, 1.35, 1.15)
        condition_available = w - 24 - condition_gap * (len(condition_specs) - 1)
        condition_unit = condition_available / sum(condition_weights)
        x = 12
        for index, spec in enumerate(condition_specs):
            condition_w = (w - 12 - x if index + 1 == len(condition_specs)
                           else int(condition_unit * condition_weights[index]))
            condition_id = spec["condition_id"]
            label_rect = (x, conditions[1] + 7, condition_w, 17)
            combo_rect = (x, conditions[1] + 25, condition_w, 30)
            self.condition_rects[condition_id] = (label_rect, combo_rect)
            label = "STATE - SIMULATED" if condition_id == "state" else spec["label"].upper()
            window.label(f"condition.{condition_id}.label", label, label_rect, style="quiet")
            options = list(self.model.applicable_states()) if condition_id == "state" else spec["options"]
            selected = options.index(self.model.conditions[condition_id])
            window.combo(
                f"condition.{condition_id}", options, combo_rect, selected=selected,
                command=lambda value, key=condition_id: self._set_condition(key, value),
            )
            x += condition_w + condition_gap

        cx, cy, cw, ch = catalog
        window.label("catalog.label", "REVIEW CATALOG", (cx + 12, cy + 10, cw - 24, 20), style="quiet")
        group_values = list(self.group_labels)
        selected_group = next(label for label, value in self.group_labels.items() if value == self.model.group_id)
        window.combo("catalog.group", group_values, (cx + 12, cy + 32, cw - 24, 32),
                     selected=group_values.index(selected_group), command=self._select_group)
        window.label("catalog.count", "", (cx + 12, cy + 68, cw - 24, 18), style="quiet")
        subject_values = self._refresh_subject_labels()
        selected_subject = next(label for label, value in self.subject_labels.items()
                                if value == self.model.subject_id)
        window.listbox("catalog.subject", subject_values, (cx + 8, cy + 88, cw - 16, ch - 98),
                       selected=subject_values.index(selected_subject), command=self._select_subject)

        mx, my, mw, _ = local
        window.label("subject.title", "", (mx + 14, my + 8, mw - 132, 27), style="heading")
        window.badge("subject.type", (mx + mw - 112, my + 9, 98, 24))
        window.label("subject.summary", "", (mx + 14, my + 37, mw - 28, 21), style="quiet")
        state_rect = (mx + 14, my + 62, mw - 132, 27)
        context_rect = (mx + 14, my + 62, mw - 28, 27)
        interact_rect = (mx + mw - 110, my + 62, 96, 27)
        window.segmented("state.matrix", self.model.applicable_states(), state_rect,
                         selected=self.model.conditions["state"],
                         command=lambda value: self._set_condition("state", value))
        window.label("state.context", "", context_rect, style="quiet")
        window.button("interact", "Next state", interact_rect, self._exercise_state)

        gx, gy, gw, _ = guide
        window.label("guide.title", "REVIEW QUESTION", (gx + 14, gy + 8, gw - 28, 18), style="quiet")
        window.label("review.question", "", (gx + 14, gy + 27, gw - 28, 38), style="body")
        window.edit("review.note", "", (gx + 14, gy + 68, gw - 28, 28), command=self._set_note)
        window.set_edit_placeholder("review.note", "Add a reason or observation")
        action_gap = 6
        action_w = (gw - 28 - action_gap * 4) // 5
        action_y = gy + 101
        action_defs = (
            ("previous", "Previous", self._previous),
            ("approve", "Approve", lambda: self._set_disposition("APPROVED")),
            ("issue", "Flag issue", lambda: self._set_disposition("ISSUE")),
            ("defer", "Defer", lambda: self._set_disposition("DEFERRED")),
            ("next", "Next", self._next),
        )
        action_positions: dict[str, tuple[int, int, int, int]] = {}
        for index, (key, label, command) in enumerate(action_defs):
            rect = (gx + 14 + index * (action_w + action_gap), action_y, action_w, 27)
            action_positions[key] = rect
            window.button(key, label, rect, command)
        window.style_button("approve", primary=True)
        window.style_button("issue", danger=True)
        self.action_rects = {
            "previous": action_positions["previous"], "interact": interact_rect,
            "next": action_positions["next"], "snapshot": (w - 158, 13, 142, 36),
        }
        self.static_action_rects = {
            "previous": action_positions["previous"], "next": action_positions["next"],
            "snapshot": (w - 158, 13, 142, 36),
        }

        sx, sy, sw, sh = specimen
        window.label("specimen.heading", "Native specimen - live interaction",
                     (sx + 16, sy + 10, sw - 32, 24), style="heading")
        specimen_content_height = max(150, sh - 82)
        self._build_specimens(sx + 24, sy + 42, sw - 48, specimen_content_height)
        if set(self.specimen_keys) != set(self.model.subjects):
            raise UIRefusal("NATIVE_REVIEW_SPECIMEN_COVERAGE_REFUSED", "")
        window.label("specimen.meta", "", (sx + 16, sy + sh - 31, sw - 32, 21), style="quiet")

        ix, iy, iw, ih = inspector
        window.label("inspector.label", "EVIDENCE INSPECTOR", (ix + 12, iy + 10, iw - 24, 20), style="quiet")
        view_values = list(self.view_labels)
        selected_view = next(label for label, value in self.view_labels.items() if value == self.model.view_id)
        window.combo("inspector.view", view_values, (ix + 12, iy + 33, iw - 24, 32),
                     selected=view_values.index(selected_view), command=self._select_view)
        window.key_value("inspector.detail", "", (ix + 8, iy + 73, iw - 16, ih - 83), columns=1)

        window.label("status", "", (footer[0] + 14, footer[1] + 6, footer[2] - 28, 22), style="quiet")
        for key in (
            "review.mode", "catalog.group", "catalog.subject", "state.matrix", "review.note",
            "approve", "issue", "defer", "previous", "interact", "next", "snapshot",
            "inspector.view",
        ):
            window.set_accessibility(key, name=key.replace(".", " ").title(),
                                     description="Mosaic UI Signature V2 native review control")
        surface_labels = {
            "title", "subtitle", "progress.label", "catalog.label", "catalog.count",
            "subject.title", "subject.summary", "state.context", "guide.title",
            "review.question", "specimen.heading", "specimen.meta", "inspector.label", "status",
            *(f"condition.{spec['condition_id']}.label" for spec in condition_specs),
        }
        for key in surface_labels:
            window.set_control_background(key, "surface")
        for key in (
            "chrome.top", "chrome.conditions", "chrome.catalog", "chrome.local",
            "chrome.guide", "chrome.specimen", "chrome.inspector", "chrome.footer",
        ):
            window.send_to_back(key)

    def _refresh_subject_labels(self) -> list[str]:
        marks = {"NEEDS_REVIEW": "[ ]", "APPROVED": "[OK]", "ISSUE": "[!]", "DEFERRED": "[-]"}
        self.subject_labels = {}
        values: list[str] = []
        for group in self.model.ontology["groups"]:
            values.append(group["label"].upper())
            for subject_id in group["subject_ids"]:
                subject = self.model.subjects[subject_id]
                label = f"  {marks[self.model.reviews[subject_id]['disposition']]} {subject['label']}"
                values.append(label)
                self.subject_labels[label] = subject_id
        return values

    def _select_subject(self, label: str) -> None:
        subject_id = self.subject_labels.get(label)
        if subject_id is None:
            self.refresh("Catalog section heading")
            return
        self.model.select_subject(subject_id)
        self.refresh("Review subject selected")

    def refresh(self, status: str) -> None:
        super().refresh(status)
        subject = self.model.subject
        scope = self.model.action_scope()
        progress = self.model.progress()
        window = self.window
        window.set_text("catalog.count", f"{len(self.model.subjects)} subjects / {progress['reviewed']} reviewed")
        window.set_text("guide.title", "WHAT CHANGED?" if self.model.mode == "CHANGES"
                        else "WHAT AM I LOOKING AT?" if self.model.mode == "EXPLORE"
                        else "REVIEW QUESTION")
        condition_ids = [item["condition_id"] for item in self.model.ontology["conditions"]]
        state_index = condition_ids.index("state")
        for index in range(state_index + 1, len(condition_ids)):
            condition_id = condition_ids[index]
            source_id = condition_ids[index if scope["state_control_visible"] else index - 1]
            label_rect, combo_rect = self.condition_rects[source_id]
            window.move(f"condition.{condition_id}.label", label_rect)
            window.move(f"condition.{condition_id}", combo_rect)
        state_text = (f"SIMULATED {self.model.conditions['state']} / {len(self.model.applicable_states())} applicable"
                      if scope["state_control_visible"] else scope["state_control_context"].replace("_", " "))
        window.set_text(
            "specimen.meta",
            f"{state_text}  |  {self.model.specimen_values[self.model.subject_id]!r}  |  "
            f"WIN32  |  {subject['standing']}",
        )


def native_review_shell_v3_adaptive_layout(width: int, height: int) -> dict[str, Any]:
    """Return the governed responsive mode and V3 regions in client-area DIPs."""
    minimum_width, minimum_height = NATIVE_REVIEW_MINIMUM_VIEWPORT
    if width < minimum_width or height < minimum_height:
        raise UIRefusal("NATIVE_REVIEW_VIEWPORT_REFUSED", f"{width}x{height}")
    mode = "WIDE" if width >= 1240 else "COMPACT" if width >= 960 else "NARROW"
    top_h = 96 if mode == "NARROW" else 60
    conditions_h = 70 if mode == "WIDE" else 126
    footer_h = 38
    workspace_y = top_h + conditions_h
    workspace_h = height - workspace_y - footer_h
    if mode == "NARROW":
        left_w = right_w = 0
        center_x, center_w = 0, width
        local_h, guide_h = 56, 132
        catalog = inspector = (0, workspace_y, width, workspace_h)
    else:
        left_w = 212 if mode == "WIDE" else 184
        right_w = 300 if mode == "WIDE" else 236
        center_x = left_w
        center_w = width - left_w - right_w
        local_h, guide_h = (64, 140) if mode == "WIDE" else (60, 148)
        catalog = (0, workspace_y, left_w, workspace_h)
        inspector = (width - right_w, workspace_y, right_w, workspace_h)
    regions = {
        "top": (0, 0, width, top_h),
        "conditions": (0, top_h, width, conditions_h),
        "catalog": catalog,
        "local": (center_x, workspace_y, center_w, local_h),
        "guide": (center_x, workspace_y + local_h, center_w, guide_h),
        "specimen": (center_x, workspace_y + local_h + guide_h, center_w,
                     workspace_h - local_h - guide_h),
        "inspector": inspector,
        "footer": (0, height - footer_h, width, footer_h),
    }
    return {
        "schema": "mosaic.ui.native-review-adaptive-layout.v0.1",
        "mode": mode,
        "viewport": {"width": width, "height": height},
        "minimum_viewport": {"width": minimum_width, "height": minimum_height},
        "condition_rows": 1 if mode == "WIDE" else 2,
        "regions": regions,
        "authority_effect": "NONE",
    }


def native_review_shell_v3_layout(width: int, height: int) -> dict[str, tuple[int, int, int, int]]:
    """Return V3 regions while preserving the original layout helper contract."""
    return native_review_shell_v3_adaptive_layout(width, height)["regions"]


def native_review_resize_plan_witness(
    viewports: tuple[tuple[int, int], ...] = NATIVE_REVIEW_RESIZE_VIEWPORTS,
) -> dict[str, Any]:
    """Bind deterministic topology evidence for a resize and restore sequence."""
    if not viewports:
        raise UIRefusal("NATIVE_REVIEW_RESIZE_SEQUENCE_REFUSED", "EMPTY")
    layouts = [native_review_shell_v3_adaptive_layout(width, height) for width, height in viewports]
    failures: list[dict[str, str]] = []
    for index, layout in enumerate(layouts):
        width = layout["viewport"]["width"]
        height = layout["viewport"]["height"]
        for region_id, (x, y, region_width, region_height) in layout["regions"].items():
            if min(x, y, region_width, region_height) < 0 or x + region_width > width or y + region_height > height:
                failures.append({"case_id": f"{index}:{region_id}", "detail": "OUT_OF_BOUNDS"})
        regions = layout["regions"]
        if regions["top"][3] + regions["conditions"][3] + regions["catalog"][3] + regions["footer"][3] != height:
            failures.append({"case_id": f"{index}:VERTICAL_PARTITION", "detail": "HEIGHT_MISMATCH"})
    if len(layouts) > 1 and layouts[0]["viewport"] == layouts[-1]["viewport"] \
            and layouts[0]["regions"] != layouts[-1]["regions"]:
        failures.append({"case_id": "RESTORE", "detail": "NON_DETERMINISTIC"})
    value = {
        "schema": "mosaic.ui.native-review-resize-plan-witness.v0.1",
        "viewports": [layout["viewport"] for layout in layouts],
        "modes": [layout["mode"] for layout in layouts],
        "layouts": layouts,
        "failure_count": len(failures),
        "failures": failures,
        "disposition": "PASS_LOCAL_CANDIDATE" if not failures else "REFUSE",
        "standing": "DETERMINISTIC_LAYOUT_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": "PLAN_EVIDENCE_DOES_NOT_ESTABLISH_REAL_HWND_RESIZE_OR_HUMAN_USABILITY",
    }
    value["commitment"] = commitment("MOSAIC.UI.NATIVE_REVIEW_RESIZE_PLAN.v0.1", value)
    return value


class _NativeReviewShellV3(_NativeReviewShellV2):
    """Signature V3 shell: native visual parity with the browser review workbench."""

    SHELL_VERSION = "SIGNATURE_V3"

    def _build(self) -> None:
        w, h, window = self.width, self.height, self.window
        adaptive = native_review_shell_v3_adaptive_layout(w, h)
        self.adaptive_mode = adaptive["mode"]
        self.narrow_view = "Review"
        regions = adaptive["regions"]
        top, conditions, catalog = regions["top"], regions["conditions"], regions["catalog"]
        local, guide, specimen = regions["local"], regions["guide"], regions["specimen"]
        inspector, footer = regions["inspector"], regions["footer"]
        self.catalog_query = ""
        self.mode_labels = {"Explore": "EXPLORE", "Guided review": "GUIDED_REVIEW", "Changes": "CHANGES"}

        surfaces = (
            ("chrome.top", top, "surface", "bottom"),
            ("chrome.conditions", conditions, "canvas", "bottom"),
            ("chrome.catalog", catalog, "canvas", "right"),
            ("chrome.local", local, "canvas", "bottom"),
            ("chrome.guide", guide, "canvas", "bottom"),
            ("chrome.inspector", inspector, "canvas", "left"),
            ("chrome.footer", footer, "surface", "top"),
        )
        for key, rect, fill, edges in surfaces:
            window.surface(key, rect, fill=fill, edges=edges)

        window.image("brand.logo", self.logo, (16, 14, 32, 32), name="Mosaic UI")
        window.label("title", "Mosaic UI", (56, 8, 210, 24), style="heading")
        window.label("subtitle", "Signature Review Workbench", (56, 31, 220, 18), style="quiet")
        selected_mode = next(label for label, value in self.mode_labels.items() if value == self.model.mode)
        window.segmented("review.mode", tuple(self.mode_labels), (276, 14, 276, 34),
                         selected=selected_mode, command=self._set_mode)
        window.segmented("narrow.view", ("Catalog", "Review", "Inspect"), (-400, -400, 10, 10),
                         selected=self.narrow_view, command=self._set_narrow_view)
        window.show("narrow.view", False)
        window.label("session", "Session governed / 25 components", (566, 19, 260, 24), style="accent")
        window.label("workspace", "Application authoring", (w - 292, 19, 138, 24), style="quiet")
        window.button("snapshot", "Export evidence", (w - 144, 13, 132, 36), self._snapshot)
        window.style_button("snapshot", primary=True)

        condition_specs = list(self.model.ontology["conditions"])
        condition_gap = 8
        condition_weights = (1.0, 1.15, 1.0, 1.1, 1.0, 0.85, 1.0, 1.25, 1.15)
        available = w - 24 - condition_gap * (len(condition_specs) - 1)
        unit = available / sum(condition_weights)
        x = 12
        for index, spec in enumerate(condition_specs):
            cell_w = w - 12 - x if index + 1 == len(condition_specs) else int(unit * condition_weights[index])
            condition_id = spec["condition_id"]
            label_rect = (x, conditions[1] + 8, cell_w, 16)
            combo_rect = (x, conditions[1] + 27, cell_w, 32)
            self.condition_rects[condition_id] = (label_rect, combo_rect)
            label = "STATE - SIMULATED" if condition_id == "state" else spec["label"].upper()
            window.label(f"condition.{condition_id}.label", label, label_rect, style="quiet")
            options = list(self.model.applicable_states()) if condition_id == "state" else spec["options"]
            window.combo(
                f"condition.{condition_id}", options, combo_rect,
                selected=options.index(self.model.conditions[condition_id]),
                command=lambda value, key=condition_id: self._set_condition(key, value),
            )
            x += cell_w + condition_gap

        cx, cy, cw, ch = catalog
        window.edit("catalog.search", "", (10, cy + 12, cw - 20, 34), command=self._set_catalog_search)
        window.set_edit_placeholder("catalog.search", "Find review subjects")
        group_values = list(self.group_labels)
        selected_group = next(label for label, value in self.group_labels.items() if value == self.model.group_id)
        window.combo("catalog.group", group_values, (-400, -400, 10, 10),
                     selected=group_values.index(selected_group), command=self._select_group)
        window.show("catalog.group", False)
        subject_values = self._refresh_subject_labels()
        selected_subject = next(label for label, value in self.subject_labels.items()
                                if value == self.model.subject_id)
        window.catalog_list(
            "catalog.subject", subject_values, (6, cy + 56, cw - 12, ch - 62),
            selected=subject_values.index(selected_subject), command=self._select_subject,
        )

        mx, my, mw, _ = local
        window.label("subject.title", "", (mx + 16, my + 8, 250, 23), style="heading")
        window.label("subject.summary", "", (mx + 16, my + 31, 285, 20), style="quiet")
        window.badge("subject.type", (-400, -400, 10, 10))
        window.show("subject.type", False)
        window.progress("review.progress", (mx + 306, my + 42, 96, 4))
        window.label("progress.label", "", (mx + 406, my + 32, 92, 22), style="quiet")
        state_x = mx + max(408, mw - 428)
        state_w = mx + mw - state_x - 12
        window.segmented(
            "state.matrix", self.model.applicable_states(), (state_x, my + 14, state_w, 34),
            selected=self.model.conditions["state"], command=lambda value: self._set_condition("state", value),
        )
        window.label("state.context", "", (state_x, my + 15, state_w, 32), style="quiet")
        window.button("interact", "Next state", (-400, -400, 10, 10), self._exercise_state)
        window.show("interact", False)

        gx, gy, gw, _ = guide
        window.label("guide.title", "REVIEW QUESTION", (gx + 16, gy + 11, 220, 17), style="quiet")
        window.label("review.question", "", (gx + 16, gy + 30, max(300, gw - 405), 50), style="body")
        window.edit("review.note", "", (gx + 16, gy + 92, min(456, gw - 32), 30), command=self._set_note)
        window.set_edit_placeholder("review.note", "Add a reason or observation")
        action_gap = 6
        action_widths = (68, 76, 82, 62, 56)
        action_total = sum(action_widths) + action_gap * 4
        action_x, action_y = gx + gw - 16 - action_total, gy + 53
        action_defs = (
            ("previous", "Previous", self._previous),
            ("approve", "Approve", lambda: self._set_disposition("APPROVED")),
            ("issue", "Flag issue", lambda: self._set_disposition("ISSUE")),
            ("defer", "Defer", lambda: self._set_disposition("DEFERRED")),
            ("next", "Next", self._next),
        )
        action_positions: dict[str, tuple[int, int, int, int]] = {}
        cursor = action_x
        for (key, label, command), button_w in zip(action_defs, action_widths):
            rect = (cursor, action_y, button_w, 32)
            action_positions[key] = rect
            window.button(key, label, rect, command)
            cursor += button_w + action_gap
        window.style_button("approve", primary=True)
        window.style_button("issue", danger=True)
        interact_rect = (-400, -400, 10, 10)
        self.action_rects = {
            "previous": action_positions["previous"], "interact": interact_rect,
            "next": action_positions["next"], "snapshot": (w - 144, 13, 132, 36),
        }
        self.static_action_rects = {
            "previous": action_positions["previous"], "next": action_positions["next"],
            "snapshot": (w - 144, 13, 132, 36),
        }

        sx, sy, sw, sh = specimen
        frame_w = min(720, sw - 48)
        frame_h = min(430, max(300, sh - 54))
        frame_x = sx + (sw - frame_w) // 2
        frame_y = sy + 24
        window.surface("specimen.frame", (frame_x, frame_y, frame_w, frame_h), fill="surface", edges="all")
        window.label("specimen.heading", "", (frame_x + 16, frame_y + 10, frame_w - 182, 24), style="heading")
        window.badge("specimen.host", (frame_x + frame_w - 160, frame_y + 10, 144, 22))
        window.set_badge("specimen.host", "WIN32 / WIN32", "accent")
        content_y = frame_y + 47
        content_h = frame_h - 102
        self._build_specimens(frame_x + 56, content_y, frame_w - 112, content_h)
        window.move("spec.BUTTON", (frame_x + 56, content_y + 45, 136, 42))
        window.move("spec.BUTTON.cancel", (frame_x + 202, content_y + 45, 96, 42))
        window.move("spec.BUTTON.delete", (frame_x + 308, content_y + 45, 96, 42))
        if set(self.specimen_keys) != set(self.model.subjects):
            raise UIRefusal("NATIVE_REVIEW_SPECIMEN_COVERAGE_REFUSED", "")
        window.label("specimen.meta", "", (frame_x + 16, frame_y + frame_h - 32, frame_w - 32, 22), style="quiet")

        ix, iy, iw, ih = inspector
        view_values = list(self.view_labels)
        selected_view = next(label for label, value in self.view_labels.items() if value == self.model.view_id)
        window.combo("inspector.view", view_values, (-400, -400, 10, 10),
                     selected=view_values.index(selected_view), command=self._select_view)
        window.show("inspector.view", False)
        primary_views, secondary_views = tuple(view_values[:4]), tuple(view_values[4:])
        window.workspace_tabs("inspector.tabs.primary", primary_views, (ix, iy, iw, 34),
                              selected=selected_view, command=self._select_view)
        window.workspace_tabs("inspector.tabs.secondary", secondary_views, (ix, iy + 34, iw, 34),
                              selected=selected_view, command=self._select_view)
        window.flat_key_value("inspector.detail", selected_view, (ix + 4, iy + 76, iw - 8, ih - 80), columns=1)

        window.label("standing", "LOCAL CANDIDATE", (14, footer[1] + 9, 104, 20), style="accent")
        window.label("catalog.count", "", (126, footer[1] + 9, 226, 20), style="body")
        window.label("status", "", (366, footer[1] + 9, w - 380, 20), style="quiet")

        interactive_keys = (
            "review.mode", "narrow.view", "catalog.search", "catalog.subject", "state.matrix", "review.note",
            "approve", "issue", "defer", "previous", "interact", "next", "snapshot",
            "inspector.tabs.primary", "inspector.tabs.secondary",
        )
        for key in interactive_keys:
            window.set_accessibility(key, name=key.replace(".", " ").title(),
                                     description="Mosaic UI Signature V3 native review control")

        backgrounds = {
            "title": "surface", "subtitle": "surface", "session": "surface", "workspace": "surface",
            "snapshot": "surface", "standing": "surface", "catalog.count": "surface", "status": "surface",
            "specimen.heading": "surface", "specimen.host": "surface", "specimen.meta": "surface",
        }
        for spec in condition_specs:
            backgrounds[f"condition.{spec['condition_id']}.label"] = "canvas"
        for key, role in backgrounds.items():
            window.set_control_background(key, role)
        for key, _, _, _ in surfaces:
            window.send_to_back(key)
        window.send_to_back("specimen.frame")
        window.set_minimum_client_size(*NATIVE_REVIEW_MINIMUM_VIEWPORT)
        window.layout_handler = self._relayout
        self._relayout(w, h)

    def _refresh_subject_labels(self) -> list[str]:
        marks = {"NEEDS_REVIEW": "[ ]", "APPROVED": "[OK]", "ISSUE": "[!]", "DEFERRED": "[-]"}
        query = getattr(self, "catalog_query", "").strip().casefold()
        self.subject_labels = {}
        values: list[str] = []
        for group in self.model.ontology["groups"]:
            matches = []
            for subject_id in group["subject_ids"]:
                subject = self.model.subjects[subject_id]
                if query and query not in subject["label"].casefold() and query not in subject_id.casefold() \
                        and subject_id != self.model.subject_id:
                    continue
                label = (
                    f"{marks[self.model.reviews[subject_id]['disposition']]} {subject['label']}"
                    f"\t{subject['subject_type']}"
                )
                matches.append((label, subject_id))
            if matches:
                values.append(f"{group['label'].upper()}::heading")
                for label, subject_id in matches:
                    values.append(label)
                    self.subject_labels[label] = subject_id
        return values

    def _set_catalog_search(self, value: str) -> None:
        self.catalog_query = value
        self.refresh("Catalog filter applied" if value.strip() else "Catalog filter cleared")

    def refresh(self, status: str) -> None:
        super().refresh(status)
        selected_view = next(label for label, value in self.view_labels.items() if value == self.model.view_id)
        view_values = list(self.view_labels)
        self.window.set_workspace_tabs("inspector.tabs.primary", tuple(view_values[:4]), selected_view)
        self.window.set_workspace_tabs("inspector.tabs.secondary", tuple(view_values[4:]), selected_view)
        self.window._components["inspector.detail"]["title"] = selected_view
        self.window.set_key_value("inspector.detail", _inspection_rows(self.model))
        progress = self.model.progress()
        self.window.set_text("session", f"Session governed / 25 components")
        self.window.set_text("progress.label", f"{progress['reviewed']} / {progress['total']} reviewed")
        group = self.model.groups[self.model.group_id]
        self.window.set_text("subject.summary", f"{group['label']} / {self.model.subject['subject_type']}")
        self.window.show("subject.type", False)
        self.window.show("interact", False)
        state_text = (f"SIMULATED {self.model.conditions['state']} / {len(self.model.applicable_states())} applicable"
                      if self.model.action_scope()["state_control_visible"]
                      else self.model.action_scope()["state_control_context"].replace("_", " "))
        self.window.set_text(
            "specimen.meta",
            f"{state_text}  |  {self.model.specimen_values[self.model.subject_id]!r}  |  "
            f"WIN32 / {self.adaptive_mode}  |  {self.model.subject['standing']}",
        )
        self.window.set_text(
            "status",
            f"{status} | {self.adaptive_mode} | {self.model.conditions['theme']}/"
            f"{self.model.conditions['density']} | {self.model.ontology['commitment'][:12]}",
        )
        self._apply_adaptive_visibility()


# Keep earlier shells available for bounded comparison while making visual-parity V3 the default.
_NativeReviewShell = _NativeReviewShellV3


def run_native_review_workbench(*, width: int = 1280, height: int = 800,
                                theme_id: str = "signature-dark", density_id: str = "comfortable",
                                subject_id: str | None = None, capture: Path | None = None,
                                export_root: Path | None = None, record: Path | None = None,
                                model_factory: Callable[..., NativeReviewModel] = NativeReviewModel) -> dict[str, Any]:
    """Open or capture the ontology-driven native review workbench."""
    if sys.platform != "win32":
        raise UIRefusal("NATIVE_REVIEW_REALIZER_REFUSED", sys.platform)
    minimum_width, minimum_height = NATIVE_REVIEW_MINIMUM_VIEWPORT
    if width < minimum_width or height < minimum_height:
        raise UIRefusal("NATIVE_REVIEW_VIEWPORT_REFUSED", f"{width}x{height}")
    ontology = build_review_ontology()
    model = model_factory(ontology, subject_id=subject_id, theme_id=theme_id, density_id=density_id)
    export_root = (export_root or (Path.cwd() / "mosaic-ui-review-snapshots")).resolve()
    captured: dict[str, Any] | None = None
    failures: list[str] = []
    native_evidence: dict[str, Any] = {}
    exit_code = 0
    while True:
        shell = _NativeReviewShell(model, width=width, height=height, export_root=export_root)
        window = shell.window
        native_evidence = {
            "hwnd": int(window.hwnd), "control_count": len(window.controls),
            "window_icon_count": len(window._icons),
            "shell_version": shell.SHELL_VERSION,
            "adaptive_mode": shell.adaptive_mode,
            "minimum_viewport": {"width": minimum_width, "height": minimum_height},
            "resize_handler": window.layout_handler is not None,
            "specimen_kind_count": 25,
            "specimen_subject_count": len(shell.specimen_keys),
            "generic_fallback_count": 0,
            "annotated_control_count": len(window._accessibility_values),
            "tab_order": window.tab_order(),
        }
        if capture is not None:
            capture = capture.resolve()
            capture.parent.mkdir(parents=True, exist_ok=True)

            def capture_and_close() -> None:
                nonlocal captured
                from .native_capture import capture_client

                try:
                    captured = capture_client(window, capture)
                    captured["sha256"] = hashlib.sha256(capture.read_bytes()).hexdigest()
                finally:
                    shell.win32.user32.PostMessageW(window.hwnd, shell.win32.WM_CLOSE, 0, 0)

            window.set_timer(350, capture_and_close)
        exit_code = window.run()
        callback_errors = list(window.callback_errors)
        window.close()
        shell.close()
        if callback_errors:
            failures.append("CALLBACK_ERRORS")
        if exit_code != 0:
            failures.append(f"EXIT_CODE:{exit_code}")
        if capture is not None and captured is None:
            failures.append("CAPTURE_MISSING")
        if not shell.rebuild_requested or capture is not None or failures:
            break

    value = {
        "schema": "mosaic.ui.native-review-workbench-witness.v0.1",
        "profile_id": ontology["profile_id"], "profile_version": ontology["profile_version"],
        "ontology_commitment": ontology["commitment"],
        "group_count": len(ontology["groups"]), "subject_count": len(ontology["subjects"]),
        "component_count": len([item for item in ontology["subjects"] if item["subject_type"] == "COMPONENT"]),
        "selection": {"subject_id": model.subject_id, "group_id": model.group_id,
                      "inspection_view": model.view_id, "conditions": copy.deepcopy(model.conditions),
                      "mode": model.mode, "review": copy.deepcopy(model.reviews[model.subject_id])},
        "review_progress": model.progress(),
        "review_session_commitment": model.state()["commitment"],
        "realizer": "WIN32", "review_mode": "FUNCTIONAL",
        "mode": "CAPTURE" if capture is not None else "INTERACTIVE",
        "viewport": {"width": width, "height": height},
        "native_evidence": native_evidence, "capture": captured,
        "snapshot_path": model.snapshot_path, "event_count": len(model.events),
        "exit_code": exit_code, "failures": failures,
        "platform": platform.platform(), "python": platform.python_version(),
        "disposition": "PASS_LOCAL_CANDIDATE" if not failures else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
        "claim_boundary": "REAL_HWND_REVIEW_EVIDENCE_APPLIES_TO_THIS_LOCAL_HOST_RUN_ONLY; RELEASE_AND_BROAD_ASSISTIVE_TECHNOLOGY_ACCEPTANCE_ARE_NOT_ESTABLISHED",
    }
    value["commitment"] = commitment("MOSAIC.UI.NATIVE_REVIEW_WORKBENCH_WITNESS.v0.1", value)
    if record is not None:
        atomic_write(record.resolve(), canonical_bytes(value) + b"\n")
    return value


def run_native_review_resize_witness(
    output_root: Path,
    *,
    viewports: tuple[tuple[int, int], ...] = NATIVE_REVIEW_RESIZE_VIEWPORTS,
    subject_id: str = "component.button",
    theme_id: str = "signature-dark",
    density_id: str = "comfortable",
) -> dict[str, Any]:
    """Exercise one real HWND through resize, narrow-surface, and restore transitions."""
    if sys.platform != "win32":
        raise UIRefusal("NATIVE_REVIEW_REALIZER_REFUSED", sys.platform)
    plan_witness = native_review_resize_plan_witness(viewports)
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    ontology = build_review_ontology()
    model = NativeReviewModel(
        ontology, subject_id=subject_id, theme_id=theme_id, density_id=density_id,
    )
    first_width, first_height = viewports[0]
    first_mode = native_review_shell_v3_adaptive_layout(first_width, first_height)["mode"]
    warmup_width = 1120 if first_mode == "WIDE" else 1240 if first_mode == "COMPACT" else 960
    shell = _NativeReviewShell(
        model, width=warmup_width, height=max(first_height, 760), export_root=output_root,
    )
    window = shell.window
    identity_before = {key: int(control.hwnd) for key, control in sorted(window.controls.items())}
    identity_root_before = commitment("MOSAIC.UI.NATIVE_CONTROL_IDENTITIES.v0.1", identity_before)
    state_before = model.state()["commitment"]
    steps: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    pending: list[tuple[int, int, str | None]] = []
    prepared: tuple[int, int, str | None] | None = None
    for width, height in viewports:
        mode = native_review_shell_v3_adaptive_layout(width, height)["mode"]
        views = ("Review", "Catalog", "Inspect") if mode == "NARROW" else (None,)
        pending.extend((width, height, view) for view in views)

    def advance() -> None:
        nonlocal prepared
        try:
            if prepared is None:
                if not pending:
                    shell.win32.user32.PostMessageW(window.hwnd, shell.win32.WM_CLOSE, 0, 0)
                    return
                width, height, narrow_view = pending.pop(0)
                window.set_client_size(width, height)
                if narrow_view is not None:
                    if narrow_view == "Review":
                        shell._set_narrow_view("Catalog")
                    shell._set_narrow_view(narrow_view)
                window.relayout()
                shell.refresh(f"Resize witness {width}x{height}")
                window.redraw()
                prepared = (width, height, narrow_view)
                return
            width, height, narrow_view = prepared
            window.redraw()
            mode = shell.adaptive_mode
            suffix = f"-{narrow_view.lower()}" if narrow_view else ""
            capture_path = output_root / f"{len(steps) + 1:02d}-{mode.lower()}-{width}x{height}{suffix}.png"
            from .native_capture import capture_client

            visible_keys = [
                key for key, control in window.controls.items()
                if shell.win32.user32.GetWindowLongW(control.hwnd, -16) & shell.win32.WS_VISIBLE
            ]
            window.set_visibility({key: False for key in visible_keys})
            window.set_visibility({key: True for key in visible_keys})
            window.redraw()
            warmup_path = output_root / ".native-review-resize-warmup.png"
            capture_client(window, warmup_path)
            capture = capture_client(window, capture_path)
            warmup_path.unlink(missing_ok=True)
            visible_rects = {
                key: rect for key, rect in window._rects.items()
                if shell.win32.user32.GetWindowLongW(window.controls[key].hwnd, -16) & shell.win32.WS_VISIBLE
            }
            out_of_bounds = sorted(
                key for key, (x, y, control_width, control_height) in visible_rects.items()
                if x < 0 or y < 0 or control_width < 1 or control_height < 1
                or x + control_width > width or y + control_height > height
            )
            if out_of_bounds:
                failures.append({"case_id": f"{width}x{height}:{narrow_view or mode}",
                                 "detail": "OUT_OF_BOUNDS:" + ",".join(out_of_bounds)})
            steps.append({
                "sequence": len(steps) + 1,
                "viewport": {"width": width, "height": height},
                "mode": mode,
                "narrow_surface": narrow_view,
                "visible_control_count": len(visible_rects),
                "out_of_bounds": out_of_bounds,
                "capture": {**capture, "sha256": hashlib.sha256(capture_path.read_bytes()).hexdigest()},
                "state_commitment": model.state()["commitment"],
                "control_identity_root": commitment(
                    "MOSAIC.UI.NATIVE_CONTROL_IDENTITIES.v0.1",
                    {key: int(control.hwnd) for key, control in sorted(window.controls.items())},
                ),
            })
            prepared = None
        except Exception as exc:
            failures.append({"case_id": "EXECUTION", "detail": f"{type(exc).__name__}:{exc}"})
            shell.win32.user32.PostMessageW(window.hwnd, shell.win32.WM_CLOSE, 0, 0)

    window.set_timer(250, advance)
    exit_code = window.run()
    callback_errors = list(window.callback_errors)
    identity_after = {key: int(control.hwnd) for key, control in sorted(window.controls.items())}
    identity_root_after = commitment("MOSAIC.UI.NATIVE_CONTROL_IDENTITIES.v0.1", identity_after)
    state_after = model.state()["commitment"]
    window.close()
    shell.close()
    if callback_errors:
        failures.append({"case_id": "CALLBACK_ERRORS", "detail": str(len(callback_errors))})
    if exit_code != 0:
        failures.append({"case_id": "EXIT_CODE", "detail": str(exit_code)})
    if identity_root_before != identity_root_after:
        failures.append({"case_id": "CONTROL_IDENTITY", "detail": "HWND_SET_CHANGED"})
    if state_before != state_after:
        failures.append({"case_id": "STATE_CONTINUITY", "detail": "SESSION_CHANGED"})
    expected_step_count = sum(3 if mode == "NARROW" else 1 for mode in plan_witness["modes"])
    if len(steps) != expected_step_count:
        failures.append({"case_id": "CAPTURE_COUNT", "detail": f"{len(steps)}!={expected_step_count}"})
    value = {
        "schema": "mosaic.ui.native-review-resize-witness.v0.1",
        "profile_id": ontology["profile_id"],
        "ontology_commitment": ontology["commitment"],
        "subject_id": subject_id,
        "plan_witness_commitment": plan_witness["commitment"],
        "steps": steps,
        "continuity": {
            "control_identity": "PASS" if identity_root_before == identity_root_after else "REFUSE",
            "review_session": "PASS" if state_before == state_after else "REFUSE",
            "restored_viewport": steps[-1]["viewport"] == steps[0]["viewport"] if steps else False,
        },
        "failure_count": len(failures),
        "failures": failures,
        "disposition": "PASS_LOCAL_CANDIDATE" if not failures else "REFUSE",
        "standing": "LOCAL_HOST_REAL_HWND_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": "REAL_HWND_RESIZE_EVIDENCE APPLIES TO THIS LOCAL HOST, VIEWPORT SEQUENCE, AND SUBJECT ONLY",
    }
    value["commitment"] = commitment("MOSAIC.UI.NATIVE_REVIEW_RESIZE_WITNESS.v0.1", value)
    atomic_write(output_root / "native-review-resize-witness.json", canonical_bytes(value) + b"\n")
    return value


__all__ = [
    "NATIVE_REVIEW_MINIMUM_VIEWPORT", "NATIVE_REVIEW_RESIZE_VIEWPORTS", "NativeReviewModel",
    "native_review_resize_plan_witness", "native_review_shell_v2_layout",
    "native_review_shell_v3_adaptive_layout", "native_review_shell_v3_layout",
    "run_native_review_resize_witness", "run_native_review_workbench",
]

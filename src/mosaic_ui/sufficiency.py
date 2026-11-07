"""Pre-1.0 standard-component sufficiency application."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .canonical import commitment, read_json


def _node(kind: str, key: str, name: Any, role: str, **props: Any) -> dict[str, Any]:
    return {
        "kind": kind,
        "node_id": key,
        "semantics": {
            "role": role,
            "name": name,
            "description": str(props.pop("description", "")),
            "focusable": kind != "NOTIFICATION",
            "actions": [] if kind == "NOTIFICATION" else ["select"],
        },
        "props": {"realization_key": key, "view": "main", **props},
        "children": [],
    }


def sufficiency_application() -> dict[str, Any]:
    def ref(message_id: str) -> dict[str, str]:
        return {"message_id": message_id}

    def choices(prefix: str, values: list[str]) -> list[dict[str, Any]]:
        return [{"value": value, "label": ref(f"{prefix}.{index}")} for index, value in enumerate(values)]

    controls = [
        _node("MENU", "suff.menu", ref("menu.name"), "menu",
              options=choices("menu.option", ["File", "Edit", "View"]), default="File", display_text=ref("menu.name")),
        _node("COMBOBOX", "suff.combo", ref("region.name"), "combobox",
              options=choices("region.option", ["US West", "US East", "Europe"]), default="US West", display_text=ref("region.name")),
        _node("NAVIGATION", "suff.navigation", ref("navigation.name"), "navigation",
              options=choices("navigation.option", ["Overview", "Evidence", "Release"]), default="Overview", display_text=ref("navigation.name")),
        _node("RADIO_GROUP", "suff.radio", ref("channel.name"), "radiogroup",
              options=choices("channel.option", ["Stable", "Beta"]), default="Stable", display_text=ref("channel.name")),
        _node("LIST", "suff.list", ref("records.name"), "listbox",
              items=choices("records.option", ["Jobs", "Receipts", "Policies"]), default="Jobs", display_text=ref("records.name")),
        _node("TREE", "suff.tree", ref("tree.name"), "tree",
              items=choices("tree.option", ["Workspace", "Applications", "Releases"]), default="Workspace", display_text=ref("tree.name")),
        _node("DATA_GRID", "suff.grid", ref("inventory.name"), "grid",
              columns=[ref("inventory.column.name"), ref("inventory.column.state")],
              rows=[["core", "ready"], ["browser", "ready"]],
              options=["core", "browser"], default="core", display_text=ref("inventory.name")),
        _node("NOTIFICATION", "suff.notice", ref("notice.name"), "status",
              display_text=ref("notice.ready")),
    ]
    tree = {
        "kind": "WINDOW", "node_id": "suff.window",
        "semantics": {"role": "window", "name": {"message_id": "app.title"}, "description": "", "focusable": False, "actions": []},
        "props": {"layout": {"type": "COLUMN", "padding": 20, "gap": 12}, "theme": "operations-dark"},
        "children": [
            {
                "kind": "LABEL", "node_id": "suff.title",
                "semantics": {"role": "heading", "name": {"message_id": "screen.title"}, "description": "", "focusable": False, "actions": []},
                "props": {"realization_key": "suff.title", "view": "main", "display_text": {"message_id": "screen.title"}, "layout_item": {"height": 44}},
                "children": [],
            },
            {
                "kind": "PANEL", "node_id": "suff.entry",
                "semantics": {"role": "group", "name": "Main", "description": "", "focusable": False, "actions": []},
                "props": {"target_view": "main", "layout_item": {"height": 1}},
                "operation_ref": "ENTER_MAIN", "children": [],
            },
            {
                "kind": "PANEL", "node_id": "suff.controls",
                "semantics": {"role": "group", "name": "Controls", "description": "", "focusable": False, "actions": []},
                "props": {"layout": {"type": "GRID", "columns": ["1fr", "1fr"], "gap": 12, "row_height": 108}, "layout_item": {"grow": 1}},
                "children": controls,
            },
        ],
    }
    return {
        "application_id": "MOSAIC-UI-1.0-SUFFICIENCY",
        "declared_operation_ids": ["ENTER_MAIN"],
        "localization": {
            "schema": "mosaic.ui.localization.v0.1",
            "default_locale": "en-US",
            "supported_locales": ["en-US", "ar"],
            "directions": {"en-US": "LTR", "ar": "RTL"},
            "messages": {
                "en-US": {
                    "app.title": "Mosaic UI sufficiency review",
                    "screen.title": "Standard UI sufficiency",
                    "menu.name": "Application menu",
                    "menu.option.0": "File", "menu.option.1": "Edit", "menu.option.2": "View",
                    "region.name": "Region",
                    "region.option.0": "US West", "region.option.1": "US East", "region.option.2": "Europe",
                    "navigation.name": "Workspace navigation",
                    "navigation.option.0": "Overview", "navigation.option.1": "Evidence", "navigation.option.2": "Release",
                    "channel.name": "Release channel",
                    "channel.option.0": "Stable", "channel.option.1": "Beta",
                    "records.name": "Recent records",
                    "records.option.0": "Jobs", "records.option.1": "Receipts", "records.option.2": "Policies",
                    "tree.name": "Project tree",
                    "tree.option.0": "Workspace", "tree.option.1": "Applications", "tree.option.2": "Releases",
                    "inventory.name": "Release inventory",
                    "inventory.column.name": "Name", "inventory.column.state": "State",
                    "notice.name": "Readiness notice",
                    "notice.ready": "All local readiness gates passed",
                },
                "ar": {
                    "app.title": "\u0645\u0631\u0627\u062c\u0639\u0629 \u0643\u0641\u0627\u064a\u0629 \u0648\u0627\u062c\u0647\u0629 Mosaic",
                    "screen.title": "\u0643\u0641\u0627\u064a\u0629 \u0648\u0627\u062c\u0647\u0629 \u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645",
                    "menu.name": "\u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u062a\u0637\u0628\u064a\u0642",
                    "menu.option.0": "\u0645\u0644\u0641", "menu.option.1": "\u062a\u062d\u0631\u064a\u0631", "menu.option.2": "\u0639\u0631\u0636",
                    "region.name": "\u0627\u0644\u0645\u0646\u0637\u0642\u0629",
                    "region.option.0": "\u063a\u0631\u0628 \u0627\u0644\u0648\u0644\u0627\u064a\u0627\u062a \u0627\u0644\u0645\u062a\u062d\u062f\u0629", "region.option.1": "\u0634\u0631\u0642 \u0627\u0644\u0648\u0644\u0627\u064a\u0627\u062a \u0627\u0644\u0645\u062a\u062d\u062f\u0629", "region.option.2": "\u0623\u0648\u0631\u0648\u0628\u0627",
                    "navigation.name": "\u062a\u0646\u0642\u0644 \u0645\u0633\u0627\u062d\u0629 \u0627\u0644\u0639\u0645\u0644",
                    "navigation.option.0": "\u0646\u0638\u0631\u0629 \u0639\u0627\u0645\u0629", "navigation.option.1": "\u0627\u0644\u0623\u062f\u0644\u0629", "navigation.option.2": "\u0627\u0644\u0625\u0635\u062f\u0627\u0631",
                    "channel.name": "\u0642\u0646\u0627\u0629 \u0627\u0644\u0625\u0635\u062f\u0627\u0631",
                    "channel.option.0": "\u0645\u0633\u062a\u0642\u0631", "channel.option.1": "\u062a\u062c\u0631\u064a\u0628\u064a",
                    "records.name": "\u0627\u0644\u0633\u062c\u0644\u0627\u062a \u0627\u0644\u0623\u062e\u064a\u0631\u0629",
                    "records.option.0": "\u0627\u0644\u0645\u0647\u0627\u0645", "records.option.1": "\u0627\u0644\u0625\u064a\u0635\u0627\u0644\u0627\u062a", "records.option.2": "\u0627\u0644\u0633\u064a\u0627\u0633\u0627\u062a",
                    "tree.name": "\u0634\u062c\u0631\u0629 \u0627\u0644\u0645\u0634\u0631\u0648\u0639",
                    "tree.option.0": "\u0645\u0633\u0627\u062d\u0629 \u0627\u0644\u0639\u0645\u0644", "tree.option.1": "\u0627\u0644\u062a\u0637\u0628\u064a\u0642\u0627\u062a", "tree.option.2": "\u0627\u0644\u0625\u0635\u062f\u0627\u0631\u0627\u062a",
                    "inventory.name": "\u0645\u062e\u0632\u0648\u0646 \u0627\u0644\u0625\u0635\u062f\u0627\u0631",
                    "inventory.column.name": "\u0627\u0644\u0627\u0633\u0645", "inventory.column.state": "\u0627\u0644\u062d\u0627\u0644\u0629",
                    "notice.name": "\u0625\u0634\u0639\u0627\u0631 \u0627\u0644\u062c\u0627\u0647\u0632\u064a\u0629",
                    "notice.ready": "\u0627\u062c\u062a\u0627\u0632\u062a \u0628\u0648\u0627\u0628\u0627\u062a \u0627\u0644\u062c\u0627\u0647\u0632\u064a\u0629 \u0627\u0644\u0645\u062d\u0644\u064a\u0629",
                },
            },
        },
        "lifecycle": {
            "schema": "mosaic.ui.std.lifecycle-binding.v0.1", "initial_view": "main",
            "operation_controls": {"cancel_key": None, "progress_key": None},
            "operation_classes": {"NAVIGATE": ["ENTER_MAIN"], "LONG_RUNNING": [], "CANCEL": [],
                                  "TOGGLE_DISCLOSURE": [], "HOST_WITHHELD": []},
            "status_templates": {"initial": "Ready", "queued": "{operation_phrase} queued",
                                 "progress": "{stage_phrase} {percent} {mm}:{ss}",
                                 "terminal": "{operation} {terminal} {message}",
                                 "cancelled": "{operation} cancelled"},
            "progress_default_stage": "working",
        },
        "tree": tree, "authority_effect": "NONE",
    }


def build_sufficiency_payload() -> dict[str, Any]:
    source = Path(__file__).resolve().parent / "source"
    library = read_json(source / "component-library.json")
    application = sufficiency_application()
    value = {"application": application, "library": library, "authority_effect": "NONE"}
    value["input_root"] = commitment("MOSAIC.UI.SUFFICIENCY_INPUT.v0.1", value)
    return value


__all__ = ["build_sufficiency_payload", "sufficiency_application"]

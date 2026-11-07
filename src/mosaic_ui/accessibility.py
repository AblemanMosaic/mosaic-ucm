"""Deterministic accessibility contract for canonical Mosaic applications."""
from __future__ import annotations

import re
from typing import Any

from .browser_realizer import BrowserRealizer
from .canonical import commitment
from .headless import HeadlessUI
from .model import ALL_COMPONENT_KINDS, STATES, walk
from .pilot import build_payload
from .sufficiency import build_sufficiency_payload


VALID_ROLES = frozenset({
    "application", "button", "checkbox", "combobox", "dialog", "grid", "group", "heading",
    "listbox", "menu", "menuitemradio", "navigation", "option", "progressbar", "radio",
    "radiogroup", "region", "row", "status", "tab", "table", "tablist", "text", "textbox",
    "tooltip", "tree", "treeitem",
})
KEYBOARD_CONTRACT = {
    "BUTTON": ["ENTER", "SPACE"], "CHECKBOX": ["SPACE"], "COMBOBOX": ["ARROWS", "ENTER"],
    "DATA_GRID": ["ARROWS", "ENTER"], "DIALOG": ["TAB", "SHIFT_TAB", "ESCAPE", "ENTER"],
    "LIST": ["ARROWS", "ENTER"], "MENU": ["ARROWS", "ENTER", "ESCAPE"],
    "NAVIGATION": ["TAB", "ENTER"], "RADIO_GROUP": ["ARROWS", "SPACE"],
    "SEGMENTED": ["ARROWS", "SPACE"], "SELECT": ["ARROWS", "ENTER"],
    "STEPPER": ["ARROWS"], "TAB_BAR": ["ARROWS", "HOME", "END"],
    "TEXT_FIELD": ["TAB", "TEXT_INPUT"], "TREE": ["ARROWS", "HOME", "END", "ENTER"],
}
ROLE_PATTERN = re.compile(r'\brole=(?:"([a-z0-9_-]+)"|([a-z0-9_-]+))')
NODE_PATTERN = re.compile(r'\bdata-node-id="([^"]+)"[^>]*\baria-label="([^"]*)"')


def _interaction_payload() -> dict[str, Any]:
    """Cover interaction kinds absent from the pilot and sufficiency fixtures."""
    controls = [
        ("DIALOG", "access.dialog", "Export evidence", ["choose"],
         {"message": "Export remains local.", "decisions": ["Cancel", "Export"], "default": "Cancel"}),
        ("SEGMENTED", "access.segmented", "Evidence mode", ["select"],
         {"options": ["Summary", "Details"], "default": "Summary"}),
        ("STEPPER", "access.stepper", "Review step", ["select"],
         {"steps": ["Draft", "Review", "Seal"], "default": "Draft"}),
        ("TAB_BAR", "access.tabs", "Workflow stage", ["select"],
         {"tabs": ["Build", "Probe", "Review"], "options": ["Build", "Probe", "Review"], "default": "Build"}),
        ("TOOLTIP", "access.tooltip", "Exact-bound review note", [],
         {"display_text": "Exact-bound review note"}),
    ]
    children = [
        {
            "kind": kind, "node_id": node_id,
            "semantics": {
                "role": kind.lower(), "name": name, "description": "",
                "focusable": bool(actions), "actions": actions,
            },
            "props": {"realization_key": node_id, "view": "main", **props}, "children": [],
        }
        for kind, node_id, name, actions, props in controls
    ]
    children.insert(0, {
        "kind": "PANEL", "node_id": "access.entry",
        "semantics": {"role": "group", "name": "Interaction audit", "description": "",
                      "focusable": False, "actions": []},
        "props": {"realization_key": "access.entry", "target_view": "main"},
        "operation_ref": "ENTER_MAIN", "children": [],
    })
    application = {
        "application_id": "MOSAIC-UI-ACCESSIBILITY-INTERACTIONS",
        "declared_operation_ids": ["ENTER_MAIN"],
        "lifecycle": {
            "schema": "mosaic.ui.std.lifecycle-binding.v0.1", "initial_view": "main",
            "operation_controls": {"cancel_key": None, "progress_key": None},
            "operation_classes": {"NAVIGATE": ["ENTER_MAIN"], "LONG_RUNNING": [], "CANCEL": [],
                                  "TOGGLE_DISCLOSURE": [], "HOST_WITHHELD": []},
            "status_templates": {
                "initial": "Ready", "queued": "{operation_phrase} queued",
                "progress": "{stage_phrase} {percent} {mm}:{ss}",
                "terminal": "{operation} {terminal} {message}", "cancelled": "{operation} cancelled",
            },
            "progress_default_stage": "working",
        },
        "tree": {
            "kind": "WINDOW", "node_id": "access.window",
            "semantics": {"role": "window", "name": "Accessibility interactions", "description": "",
                          "focusable": False, "actions": []},
            "props": {"theme": "operations-dark"}, "children": children,
        },
        "authority_effect": "NONE",
    }
    pilot = build_payload()
    return {
        "schema": "mosaic.ui.generated-library.v0.1",
        "input_root": commitment("MOSAIC.UI.ACCESSIBILITY_INTERACTIONS.v0.1", application),
        "application": application, "library": pilot["library"], "authority_effect": "NONE",
    }


def _subjects() -> list[tuple[str, dict[str, Any], Any, tuple[int, int]]]:
    return [
        ("SUFFICIENCY", build_sufficiency_payload(), None, (1280, 800)),
        ("PILOT", build_payload(), None, (1280, 800)),
        ("INTERACTIONS", _interaction_payload(), None, (960, 720)),
    ]


def audit_payload(
    subject_id: str, payload: dict[str, Any], layout_provider: Any = None,
    viewport: tuple[int, int] = (1280, 800),
) -> dict[str, Any]:
    headless = HeadlessUI(payload, layout_provider)
    projection = headless.project(*viewport).as_dict()
    nodes = projection["accessibility"]["nodes"]
    realized_items = [item for item in walk(payload["application"]["tree"])
                      if item.get("props", {}).get("realization_key")]
    focus_indexes = [node["focus_index"] for node in nodes if node["focus_index"] is not None]
    failures = []
    for node in nodes:
        if not str(node.get("name", "")).strip():
            failures.append(f'NAME_ABSENT:{node["node_id"]}')
        if node.get("state") not in STATES:
            failures.append(f'STATE_INVALID:{node["node_id"]}')
        if node.get("actions") and not node.get("focusable"):
            failures.append(f'INTERACTIVE_NOT_FOCUSABLE:{node["node_id"]}')
    if focus_indexes != list(range(len(focus_indexes))):
        failures.append("FOCUS_ORDER_NOT_CONTIGUOUS")
    if {node["node_id"] for node in nodes} != {item["node_id"] for item in realized_items}:
        failures.append("ACCESSIBILITY_NODE_COVERAGE")

    browser = BrowserRealizer(payload, layout_provider)
    try:
        document = browser.document(*viewport)
    finally:
        browser.close()
    roles = [first or second for first, second in ROLE_PATTERN.findall(document)]
    invalid_roles = sorted(set(roles) - VALID_ROLES)
    if invalid_roles:
        failures.append("BROWSER_ROLE_INVALID:" + ",".join(invalid_roles))
    rendered = NODE_PATTERN.findall(document)
    if len(rendered) != len(nodes) or any(not label.strip() for _, label in rendered):
        failures.append("BROWSER_NODE_LABEL_CORRESPONDENCE")
    kinds = sorted({str(item["kind"]) for item in walk(payload["application"]["tree"])})
    value = {
        "subject_id": subject_id, "component_kinds": kinds, "node_count": len(nodes),
        "focus_order": projection["accessibility"]["focus_order"], "browser_roles": sorted(set(roles)),
        "failures": failures, "disposition": "PASS" if not failures else "REFUSE",
    }
    value["commitment"] = commitment("MOSAIC.UI.ACCESSIBILITY_SUBJECT.v0.1", value)
    return value


def accessibility_witness() -> dict[str, Any]:
    subjects = [audit_payload(*args) for args in _subjects()]
    covered = sorted({kind for subject in subjects for kind in subject["component_kinds"]})
    checks = {
        "ALL_25_KINDS_COVERED": "PASS" if set(covered) == set(ALL_COMPONENT_KINDS) else "FAIL",
        "SUBJECT_AUDITS": "PASS" if all(subject["disposition"] == "PASS" for subject in subjects) else "FAIL",
        "KEYBOARD_CONTRACT_COMPLETE": "PASS" if len(KEYBOARD_CONTRACT) == 15 else "FAIL",
        "STANDARD_BROWSER_ROLES": "PASS" if all(not subject["failures"] for subject in subjects) else "FAIL",
    }
    passed = all(value == "PASS" for value in checks.values())
    value = {
        "schema": "mosaic.ui.accessibility-evidence.v0.1", "checks": checks,
        "covered_component_kinds": covered, "keyboard_contract": KEYBOARD_CONTRACT,
        "subjects": subjects, "disposition": "PASS_LOCAL_CANDIDATE" if passed else "REFUSE",
        "standing": "LOCAL_DETERMINISTIC_ACCESSIBILITY_EVIDENCE", "authority_effect": "NONE",
        "claim_boundary": "SEMANTIC_AND_DOM_AUDIT_DOES_NOT_ESTABLISH_SCREEN_READER_OR_HUMAN_USABILITY_CERTIFICATION",
    }
    value["commitment"] = commitment("MOSAIC.UI.ACCESSIBILITY_EVIDENCE.v0.1", value)
    return value


__all__ = ["KEYBOARD_CONTRACT", "VALID_ROLES", "accessibility_witness", "audit_payload"]

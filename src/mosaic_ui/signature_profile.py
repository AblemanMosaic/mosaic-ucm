"""Governed Mosaic Signature Profile reference compositions and witness."""
from __future__ import annotations

import copy
from typing import Any

from mosaic_ui_std.signature import load_signature_profile, resolve_signature_theme

from .canonical import commitment
from .headless import HeadlessUI
from .model import UIRefusal, walk
from .sufficiency import build_sufficiency_payload


REFERENCE_SCHEMA = "mosaic.ui.signature-reference.v0.1"


def _semantics(role: str, name: str, focusable: bool = False) -> dict[str, Any]:
    return {"role": role, "name": name, "description": "", "focusable": focusable,
            "actions": ["select"] if focusable else []}


def _control(kind: str, key: str, name: str, role: str, *, height: int | None = None,
             width: int | None = None, grow: int | None = None, span: int | None = None,
             operation: bool = False, **props: Any) -> dict[str, Any]:
    layout_item = {key: value for key, value in {
        "height": height, "width": width, "grow": grow, "span": span,
    }.items() if value is not None}
    value: dict[str, Any] = {
        "kind": kind, "node_id": key, "semantics": _semantics(role, name, kind not in {"BADGE", "NOTIFICATION", "PROGRESS", "STATUS"}),
        "props": {"realization_key": key, "view": "main", "display_text": name,
                  **({"layout_item": layout_item} if layout_item else {}), **props},
        "children": [],
    }
    if operation:
        value["operation_ref"] = "ENTER_MAIN"
        value["props"]["target_view"] = "main"
    return value


def _panel(key: str, children: list[dict[str, Any]], *, layout: dict[str, Any],
           height: int | None = None, grow: int | None = None) -> dict[str, Any]:
    layout_item = {name: value for name, value in {"height": height, "grow": grow}.items() if value is not None}
    return {
        "kind": "PANEL", "node_id": key, "semantics": _semantics("group", key.replace(".", " ").title()),
        "props": {"layout": layout, **({"layout_item": layout_item} if layout_item else {})},
        "children": children,
    }


def _choice(value: str, label: str) -> dict[str, str]:
    return {"value": value, "label": label}


def _entry() -> dict[str, Any]:
    return {
        "kind": "PANEL", "node_id": "signature.entry", "semantics": _semantics("group", "Main"),
        "props": {"target_view": "main", "layout_item": {"height": 1}},
        "operation_ref": "ENTER_MAIN", "children": [],
    }


def _lifecycle() -> dict[str, Any]:
    return {
        "schema": "mosaic.ui.std.lifecycle-binding.v0.1", "initial_view": "main",
        "operation_controls": {"cancel_key": None, "progress_key": None},
        "operation_classes": {"NAVIGATE": ["ENTER_MAIN"], "LONG_RUNNING": [], "CANCEL": [],
                              "TOGGLE_DISCLOSURE": [], "HOST_WITHHELD": []},
        "status_templates": {"initial": "Ready", "queued": "{operation_phrase} queued",
                             "progress": "{stage_phrase} {percent} {mm}:{ss}",
                             "terminal": "{operation} {terminal} {message}",
                             "cancelled": "{operation} cancelled"},
        "progress_default_stage": "working",
    }


def _operational_dashboard(gap: int, padding: int, control_height: int) -> dict[str, Any]:
    nav = _control("NAVIGATION", "ops.navigation", "Workspace", "navigation", height=control_height + 6,
                   options=[_choice("overview", "Overview"), _choice("evidence", "Evidence"), _choice("release", "Release")],
                   default="overview")
    metrics = _panel("ops.metrics", [
        _control("STATUS", "ops.health", "Runtime healthy", "status"),
        _control("BADGE", "ops.posture", "Local candidate", "status", tone="info"),
        _control("PROGRESS", "ops.coverage", "Evidence coverage", "progressbar", span=2, default=84),
    ], layout={"type": "GRID", "columns": ["1fr", "1fr"], "gap": gap, "row_height": 30}, height=30 * 2 + gap)
    body = _panel("ops.body", [
        _control("DATA_GRID", "ops.services", "Service health", "grid", grow=2,
                 columns=["Service", "State", "Evidence"],
                 rows=[["Browser", "Ready", "40 cases"], ["Win32", "Ready", "25 kinds"], ["Ablation", "Ready", "Exact closure"]],
                 options=["Browser", "Win32", "Ablation"], default="Browser"),
        _control("NOTIFICATION", "ops.notice", "No unresolved local refusals", "status", tone="info"),
    ], layout={"type": "ROW", "gap": gap}, grow=1)
    actions = _panel("ops.actions", [
        _control("BUTTON", "ops.refresh", "Refresh", "button", width=120, operation=True),
        _control("BUTTON", "ops.review", "Review evidence", "button", width=150, operation=True),
    ], layout={"type": "ROW", "gap": gap}, height=control_height)
    return _application("operational-dashboard", "Operations", [nav, metrics, body, actions], gap, padding)


def _data_workspace(gap: int, padding: int, control_height: int) -> dict[str, Any]:
    nav = _control("NAVIGATION", "data.navigation", "Data workspace", "navigation", height=control_height + 6,
                   options=[_choice("records", "Records"), _choice("schemas", "Schemas"), _choice("receipts", "Receipts")],
                   default="records")
    filters = _panel("data.filters", [
        _control("TEXT_FIELD", "data.search", "Search records", "searchbox", width=250,
                 default="release", required=False, readonly=False, multiline=False, max_length=80),
        _control("COMBOBOX", "data.scope", "Scope", "combobox", width=170,
                 options=[_choice("all", "All evidence"), _choice("pass", "Passing"), _choice("refused", "Refused")], default="all"),
        _control("BUTTON", "data.apply", "Apply", "button", width=110, operation=True),
    ], layout={"type": "ROW", "gap": gap}, height=control_height)
    body = _panel("data.body", [
        _control("LIST", "data.collections", "Collections", "listbox", width=220,
                 items=[_choice("runs", "Recent runs"), _choice("releases", "Releases"), _choice("policies", "Policies")], default="runs"),
        _control("DATA_GRID", "data.records", "Evidence records", "grid", grow=1,
                 columns=["Record", "Kind", "Status"],
                 rows=[["VIS-018", "Visual", "Pass"], ["ABL-031", "Slice", "Pass"], ["WIN-025", "Native", "Pass"]],
                 options=["VIS-018", "ABL-031", "WIN-025"], default="VIS-018"),
    ], layout={"type": "ROW", "gap": gap}, grow=1)
    footer = _panel("data.footer", [
        _control("STATUS", "data.status", "3 records selected", "status", grow=1),
        _control("BUTTON", "data.export", "Export slice", "button", width=140, operation=True),
    ], layout={"type": "ROW", "gap": gap}, height=control_height)
    return _application("data-workspace", "Evidence data", [nav, filters, body, footer], gap, padding)


def _settings_workflow(gap: int, padding: int, control_height: int) -> dict[str, Any]:
    menu = _control("MENU", "settings.menu", "Settings sections", "menu", height=control_height + 6,
                    options=[_choice("appearance", "Appearance"), _choice("evidence", "Evidence"), _choice("delivery", "Delivery")],
                    default="appearance")
    fields = _panel("settings.fields", [
        _control("TEXT_FIELD", "settings.name", "Application name", "textbox",
                 default="Mosaic Workbench", required=True, readonly=False, multiline=False, max_length=60),
        _control("COMBOBOX", "settings.theme", "Default theme", "combobox",
                 options=[_choice("dark", "Signature dark"), _choice("light", "Signature light"), _choice("contrast", "High contrast")],
                 default="dark"),
    ], layout={"type": "GRID", "columns": ["1fr", "1fr"], "gap": gap, "row_height": control_height + 14}, height=control_height + 14)
    dialog = _control("DIALOG", "settings.confirm", "Apply governed defaults", "dialog", grow=1,
                      message="Apply these presentation defaults to this application profile?",
                      decisions=[_choice("apply", "Apply"), _choice("cancel", "Cancel")], default="cancel")
    notice = _control("NOTIFICATION", "settings.notice", "Changes remain local until exported", "status", height=48, tone="info")
    actions = _panel("settings.actions", [
        _control("STATUS", "settings.status", "No pending changes", "status", grow=1),
        _control("BUTTON", "settings.save", "Save settings", "button", width=145, operation=True),
    ], layout={"type": "ROW", "gap": gap}, height=control_height)
    return _application("settings-workflow", "Application settings", [menu, fields, dialog, notice, actions], gap, padding)


def _application(composition_id: str, title: str, children: list[dict[str, Any]], gap: int, padding: int) -> dict[str, Any]:
    header = _panel(f"{composition_id}.header", [
        _control("LABEL", f"{composition_id}.title", title, "heading", grow=1, style="title"),
        _control("BADGE", f"{composition_id}.profile", "Mosaic Signature", "status", width=160, tone="info"),
    ], layout={"type": "ROW", "gap": gap}, height=40)
    tree = {
        "kind": "WINDOW", "node_id": f"signature.{composition_id}.window",
        "semantics": _semantics("application", title),
        "props": {"layout_provider": "mosaic.ui.layout.v0.1",
                  "layout": {"type": "COLUMN", "padding": padding, "gap": gap}},
        "children": [header, _entry(), *children],
    }
    return {
        "schema": REFERENCE_SCHEMA, "application_id": f"MOSAIC_SIGNATURE_{composition_id.upper().replace('-', '_')}",
        "composition_id": composition_id, "declared_operation_ids": ["ENTER_MAIN"],
        "lifecycle": _lifecycle(), "tree": tree, "standing": "LOCAL_CANDIDATE",
        "authority_effect": "NONE",
    }


def build_signature_payload(composition_id: str = "operational-dashboard", theme_id: str = "signature-dark",
                            density_id: str = "comfortable") -> dict[str, Any]:
    profile = load_signature_profile()
    composition_ids = {item["composition_id"] for item in profile["compositions"]}
    if composition_id not in composition_ids:
        raise UIRefusal("SIGNATURE_COMPOSITION_REFUSED", composition_id)
    resolved = resolve_signature_theme(theme_id, density_id)
    spacing, control_height = resolved["tokens"]["spacing"], resolved["control_height"]
    builders = {
        "operational-dashboard": _operational_dashboard,
        "data-workspace": _data_workspace,
        "settings-workflow": _settings_workflow,
    }
    application = builders[composition_id](spacing["sm"], spacing["lg"], control_height)
    required = next(item["required_kinds"] for item in profile["compositions"] if item["composition_id"] == composition_id)
    observed = {item["kind"] for item in walk(application["tree"])}
    if not set(required) <= observed:
        raise UIRefusal("SIGNATURE_COMPOSITION_REFUSED", "REQUIRED_KIND_CLOSURE")
    payload = build_sufficiency_payload()
    payload["application"] = application
    payload["library"] = copy.deepcopy(payload["library"])
    payload["library"]["tokens"] = copy.deepcopy(resolved["tokens"])
    payload["signature"] = {
        "schema": "mosaic.ui.signature-selection.v0.1", "profile_id": profile["profile_id"],
        "composition_id": composition_id, "theme_id": theme_id, "density_id": density_id,
        "resolution_commitment": resolved["commitment"], "authority_effect": "NONE",
    }
    payload["input_root"] = commitment("MOSAIC.UI.SIGNATURE.REFERENCE_INPUT.v0.1", {
        "application": payload["application"], "library": payload["library"], "signature": payload["signature"],
    })
    return payload


def signature_profile_witness() -> dict[str, Any]:
    from .browser_realizer import BrowserRealizer

    profile = load_signature_profile()
    cases = []
    for composition in profile["compositions"]:
        for theme_id in profile["themes"]:
            for density_id in profile["densities"]:
                payload = build_signature_payload(composition["composition_id"], theme_id, density_id)
                for width, height in ((640, 600), (1280, 800)):
                    for realizer_id, realizer in (("HEADLESS", HeadlessUI(payload)),
                                                   ("BROWSER", BrowserRealizer(payload))):
                        projection = realizer.project(width, height)
                        if hasattr(projection, "as_dict"):
                            projection = projection.as_dict()
                        gates = projection["gates"]
                        cases.append({
                            "case_id": f"{composition['composition_id']}:{theme_id}:{density_id}:{width}:{realizer_id}",
                            "composition_id": composition["composition_id"], "theme_id": theme_id,
                            "density_id": density_id, "realizer": realizer_id,
                            "viewport": {"width": width, "height": height},
                            "gate_commitment": gates["commitment"], "disposition": gates["disposition"],
                        })
    disposition = "PASS_LOCAL_CANDIDATE" if cases and all(case["disposition"] == "PASS" for case in cases) else "REFUSE"
    value = {
        "schema": "mosaic.ui.signature-profile-witness.v0.1", "profile_id": profile["profile_id"],
        "case_count": len(cases), "cases": cases, "disposition": disposition,
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
        "claim_boundary": "DETERMINISTIC_AND_BROWSER_PROTOCOL_CASES_DO_NOT_ESTABLISH_EXTERNAL_ACCEPTANCE",
    }
    value["commitment"] = commitment("MOSAIC.UI.SIGNATURE_PROFILE_WITNESS.v0.1", value)
    return value


__all__ = ["build_signature_payload", "signature_profile_witness"]

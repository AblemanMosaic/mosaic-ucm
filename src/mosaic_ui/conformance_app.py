"""Permanent semantic conformance application and real-HWND interaction witness."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
from typing import Iterable

from mosaic_ui_std import THEMES_DIR, load_theme

from .canonical import atomic_write, canonical_bytes, commitment
from .native_realizer import NativeSemanticUI


SIZE = (1120, 720)


def _node(kind: str, key: str, name: str, rect, *, actions: list[str] | None = None, **props):
    return {
        "kind": kind, "node_id": key,
        "semantics": {
            "role": kind.lower(), "name": name, "description": str(props.pop("description", "")),
            "focusable": True, "actions": actions or [],
        },
        "props": {"realization_key": key, "view": "main", **props}, "children": [],
    }, rect


def conformance_payload(theme_id: str = "high-contrast-dark") -> tuple[dict, dict]:
    theme = load_theme(THEMES_DIR / f"{theme_id}.json")
    controls = [
        _node("TEXT_FIELD", "conf.text", "Evidence label", (30, 154, 448, 38),
              actions=["set-value"], default="draft-01"),
        _node("SELECT", "conf.select", "Evidence profile", (30, 238, 448, 120),
              actions=["select"], options=["Balanced", "Strict"], default="Balanced"),
        _node("CHECKBOX", "conf.check", "Include native receipt", (30, 326, 448, 30),
              actions=["toggle"], default=False),
        _node("BUTTON", "conf.run", "Run bounded probe", (30, 398, 216, 44), actions=["activate"]),
        _node("SEGMENTED", "conf.segment", "Evidence mode", (540, 130, 532, 42),
              actions=["select"], options=["Summary", "Details", "Receipts"], default="Summary"),
        _node("TAB_BAR", "conf.tabs", "Workflow stage", (540, 208, 532, 42),
              actions=["select"], tabs=["Build", "Probe", "Review"], options=["Build", "Probe", "Review"],
              default="Build"),
        _node("STEPPER", "conf.steps", "Review step", (540, 286, 532, 50),
              actions=["select"], steps=["Draft", "Review", "Seal"], default="Draft"),
        _node("DIALOG", "conf.dialog", "Evidence export", (540, 378, 532, 174),
              actions=["choose"], message="Export remains local and effectless.",
              decisions=["Cancel", "Export"], default="Cancel"),
    ]
    nodes = [item for item, _ in controls]
    run = next(item for item in nodes if item["node_id"] == "conf.run")
    run["operation_ref"] = "RUN_LOCAL_PROBE"
    labels = [
        {
            "kind": "LABEL", "node_id": "conf.title",
            "semantics": {"role": "heading", "name": "Native interaction conformance", "description": "", "focusable": False, "actions": []},
            "props": {"realization_key": "conf.title", "view": "main", "display_text": "Native interaction conformance", "style": "title"},
            "children": [],
        },
        {
            "kind": "LABEL", "node_id": "conf.inputs-heading",
            "semantics": {"role": "heading", "name": "Input controls", "description": "", "focusable": False, "actions": []},
            "props": {"realization_key": "conf.inputs-heading", "view": "main", "display_text": "Input controls", "style": "heading"},
            "children": [],
        },
        {
            "kind": "LABEL", "node_id": "conf.choices-heading",
            "semantics": {"role": "heading", "name": "Choice controls", "description": "", "focusable": False, "actions": []},
            "props": {"realization_key": "conf.choices-heading", "view": "main", "display_text": "Choice controls", "style": "heading"},
            "children": [],
        },
        {
            "kind": "STATUS", "node_id": "conf.status",
            "semantics": {"role": "status", "name": "Conformance status", "description": "", "focusable": False, "actions": []},
            "props": {"realization_key": "conf.status", "view": "main", "display_text": "Ready for bounded synthetic interaction"},
            "children": [],
        },
    ]
    tree = {
        "kind": "WINDOW", "node_id": "conf.window",
        "semantics": {"role": "window", "name": "Mosaic UI conformance", "description": "", "focusable": False, "actions": []},
        "props": {"layout_provider": "mosaic.conformance-app.v0.1", "theme": theme_id},
        "children": [{
            "kind": "PANEL", "node_id": "conf.entry",
            "semantics": {"role": "group", "name": "Main", "description": "", "focusable": False, "actions": []},
            "props": {"target_view": "main"}, "operation_ref": "ENTER_MAIN", "children": [],
        }, labels[0], labels[1], labels[2], *nodes, labels[3]],
    }
    application = {
        "application_id": "MOSAIC-UI-NATIVE-CONFORMANCE",
        "declared_operation_ids": ["ENTER_MAIN", "RUN_LOCAL_PROBE"],
        "lifecycle": {
            "schema": "mosaic.ui.std.lifecycle-binding.v0.1", "initial_view": "main",
            "operation_controls": {"cancel_key": None, "progress_key": None},
            "operation_classes": {"NAVIGATE": ["ENTER_MAIN"], "LONG_RUNNING": [], "CANCEL": [],
                                  "TOGGLE_DISCLOSURE": [], "HOST_WITHHELD": ["RUN_LOCAL_PROBE"]},
            "status_templates": {
                "initial": "Ready", "queued": "{operation_phrase} queued",
                "progress": "{stage_phrase} {percent} {mm}:{ss}",
                "terminal": "{operation} {terminal} {message}", "cancelled": "{operation} cancelled",
            },
            "progress_default_stage": "working",
        },
        "tree": tree, "authority_effect": "NONE",
    }
    input_root = commitment("MOSAIC.UI.CONFORMANCE_INPUT.v0.1", {"application": application, "theme": theme})
    payload = {"input_root": input_root, "application": application,
               "library": {"tokens": theme["tokens"]}, "authority_effect": "NONE"}
    layout = {item["node_id"]: rect for item, rect in controls}
    layout.update({
        "conf.title": (30, 24, 760, 48), "conf.inputs-heading": (30, 100, 448, 30),
        "conf.choices-heading": (540, 82, 532, 30), "conf.status": (30, 626, 1042, 30),
    })
    return payload, layout


def run_witness(output: Path, screenshot: Path, *, theme_id: str = "high-contrast-dark",
                dpi: int = 96) -> tuple[dict, int]:
    from . import win32
    from .native_capture import capture_client

    payload, layout = conformance_payload(theme_id)
    native = NativeSemanticUI(payload, lambda width, height: dict(layout), width=SIZE[0], height=SIZE[1])
    native.window.set_review_dpi(dpi, SIZE)
    captured: dict = {}
    accessibility: dict = {}

    def command(key: str, notification: int) -> None:
        control = native.window.controls[key]
        wparam = int(control.command_id or 0) | (notification << 16)
        win32.user32.SendMessageW(native.window.hwnd, win32.WM_COMMAND, wparam, control.hwnd)

    def pointer_choice(key: str, index: int, count: int) -> None:
        hwnd = native.window.controls[key].hwnd
        width = native.window.physical_rect(key)[2]
        x = max(1, min(width - 2, width * (2 * index + 1) // (2 * count)))
        lparam = x | (native.window.px(18) << 16)
        win32.user32.SendMessageW(hwnd, win32.WM_LBUTTONDOWN, 1, lparam)
        win32.user32.SendMessageW(hwnd, win32.WM_LBUTTONUP, 0, lparam)

    def exercise() -> None:
        nonlocal captured, accessibility
        win32.user32.KillTimer(native.window.hwnd, 1)
        native.window.timer_handler = None
        native.window.set_text("conf.text", "sealed-01")
        command("conf.text", win32.EN_KILLFOCUS)
        win32.user32.SendMessageW(native.window.controls["conf.select"].hwnd, win32.CB_SETCURSEL, 1, 0)
        command("conf.select", win32.CBN_SELCHANGE)
        win32.user32.SendMessageW(native.window.controls["conf.check"].hwnd, 0x00F5, 0, 0)
        pointer_choice("conf.segment", 2, 3)
        win32.user32.SetFocus(native.window.controls["conf.tabs"].hwnd)
        win32.user32.SendMessageW(native.window.controls["conf.tabs"].hwnd, win32.WM_KEYDOWN, 39, 0)
        win32.user32.SetFocus(native.window.controls["conf.steps"].hwnd)
        win32.user32.SendMessageW(native.window.controls["conf.steps"].hwnd, win32.WM_KEYDOWN, 39, 0)
        pointer_choice("conf.dialog", 1, 2)
        win32.user32.SendMessageW(native.window.controls["conf.run"].hwnd, 0x00F5, 0, 0)
        native.window.set_text("conf.status", "Interaction and accessibility probes completed")
        accessibility = native.accessibility_witness()
        win32.user32.InvalidateRect(native.window.hwnd, None, True)
        win32.user32.UpdateWindow(native.window.hwnd)
        for control in native.window.controls.values():
            win32.user32.InvalidateRect(control.hwnd, None, True)
            win32.user32.UpdateWindow(control.hwnd)
        captured = capture_client(native.window, screenshot)
        win32.user32.PostMessageW(native.window.hwnd, win32.WM_CLOSE, 0, 0)

    native.window.set_timer(350, exercise)
    exit_code = native.run()
    expected = {
        "conf.text": "sealed-01", "conf.select": "Strict", "conf.check": True,
        "conf.segment": "Receipts", "conf.tabs": "Probe", "conf.steps": "Review",
        "conf.dialog": "Export",
    }
    observed = {key: native.runtime.state["values"].get(key) for key in expected}
    intents = native.runtime.state["emitted_intents"]
    passed = (observed == expected and len(intents) == 8 and accessibility.get("disposition") == "PASS_LOCAL_CANDIDATE"
              and not native.window.callback_errors and exit_code == 0 and screenshot.exists())
    result = {
        "schema": "mosaic.ui.native-conformance-witness.v0.1",
        "platform": platform.platform(), "python": platform.python_version(),
        "theme_id": theme_id, "dpi": dpi, "dpi_mode": "DETERMINISTIC_REVIEW_PROJECTION",
        "expected_values": expected, "observed_values": observed, "emitted_intents": intents,
        "accessibility": accessibility, "native_realization": native.witness_descriptor(),
        "capture": {**captured, "sha256": hashlib.sha256(screenshot.read_bytes()).hexdigest()},
        "callback_errors": list(native.window.callback_errors), "exit_code": exit_code,
        "disposition": "PASS_LOCAL_CANDIDATE" if passed else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
        "host_effect": "VISIBLE_LOCAL_WITNESS_ONLY",
        "claim_boundary": "SYNTHETIC_MESSAGES_AND_DIRECT_IACCESSIBLE_INSPECTION_DO_NOT_ESTABLISH_HUMAN_INPUT_SCREEN_READER_OR_BROAD_HOST_BEHAVIOR",
    }
    result["commitment"] = commitment("MOSAIC.UI.NATIVE_CONFORMANCE_WITNESS.v0.1", result)
    atomic_write(output, canonical_bytes(result) + b"\n")
    return result, 0 if passed else 32


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--screenshot", type=Path, required=True)
    parser.add_argument("--theme", choices=("operations-dark", "high-contrast-dark"), default="high-contrast-dark")
    parser.add_argument("--dpi", type=int, default=96)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result, code = run_witness(args.output.resolve(), args.screenshot.resolve(),
                               theme_id=args.theme, dpi=args.dpi)
    print(json.dumps(result, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

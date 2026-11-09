"""Small declarative native demo for the completed Mosaic UI catalog tier."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

from mosaic_ui_std import THEMES_DIR, load_theme

from .canonical import atomic_write, canonical_bytes, commitment
from .native_realizer import NativeSemanticUI


SIZE = (1120, 720)


def _node(kind: str, node_id: str, name: str, rect_key: str, **props) -> dict:
    return {
        "kind": kind,
        "node_id": node_id,
        "semantics": {
            "role": kind.lower(), "name": name, "description": str(props.pop("description", "")),
            "focusable": kind in {"SEGMENTED", "TAB_BAR"}, "actions": [],
        },
        "props": {"realization_key": rect_key, "view": "main", **props},
        "children": [],
    }


def demo_payload(theme_id: str = "operations-dark") -> tuple[dict, dict]:
    theme = load_theme(THEMES_DIR / f"{theme_id}.json")
    panel = _node("PANEL", "demo.panel", "Native completion", "demo.panel", display_text="Native completion")
    panel["props"]["target_view"] = "main"
    panel["operation_ref"] = "ENTER_MAIN"
    children = [
        _node("LABEL", "demo.title", "Declarative native catalog", "demo.title",
              display_text="Declarative native catalog", style="title"),
        _node("LABEL", "demo.subtitle", "One semantic tree, one lifecycle, two realizers", "demo.subtitle",
              display_text="One semantic tree, one lifecycle, two realizers", style="quiet"),
        _node("BADGE", "demo.badge", "17 / 17 WIN32", "demo.badge", display_text="17 / 17 WIN32", tone="accent"),
        _node("SEGMENTED", "demo.segmented", "Evidence mode", "demo.segmented",
              options=["Summary", "Details", "Receipts"], default="Details"),
        _node("TAB_BAR", "demo.tabs", "Workflow stage", "demo.tabs",
              tabs=["Build", "Probe", "Review"], default="Probe"),
        panel,
        _node("TOOLTIP", "demo.tooltip", "Exact-bound review note", "demo.tooltip",
              display_text="Tooltip: exact-bound review note"),
        _node("DIALOG", "demo.dialog", "Confirm evidence export", "demo.dialog",
              display_text="Confirm evidence export", message="The export remains local and effectless.",
              decisions=["Cancel", "Export"]),
        _node("KEY_VALUE", "demo.boundary", "Evidence boundary", "demo.boundary",
              title="Evidence boundary", columns=1,
              rows=[["Native drawing", "17 kinds", False], ["Choice input", "pointer + keyboard", False],
                    ["Authority effect", "NONE", False]]),
        _node("STATUS", "demo.status", "Ready for review", "demo.status",
              display_text="Ready for review", style="quiet"),
    ]
    tree = {
        "kind": "WINDOW", "node_id": "demo.window",
        "semantics": {"role": "window", "name": "Mosaic declarative native demo", "description": "", "focusable": False, "actions": []},
        "props": {"layout_provider": "mosaic.semantic-demo.v0.1", "theme": theme_id},
        "children": children,
    }
    application = {
        "application_id": "MOSAIC-UI-DECLARATIVE-NATIVE-DEMO",
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
        "tree": tree, "authority_effect": "NONE",
    }
    input_root = commitment("MOSAIC.UI.SEMANTIC_DEMO_INPUT.v0.1", {"application": application, "theme": theme})
    payload = {"input_root": input_root, "application": application, "library": {"tokens": theme["tokens"]},
               "authority_effect": "NONE"}
    layout = {
        "demo.title": (30, 24, 610, 44), "demo.subtitle": (32, 70, 580, 28),
        "demo.badge": (846, 30, 226, 28), "demo.segmented": (30, 140, 492, 42),
        "demo.tabs": (30, 218, 492, 42), "demo.panel": (30, 300, 492, 150),
        "demo.tooltip": (58, 480, 354, 40), "demo.dialog": (558, 140, 514, 260),
        "demo.boundary": (558, 430, 514, 140), "demo.status": (30, 626, 1042, 30),
    }
    return payload, layout


def run_demo(*, theme_id: str = "operations-dark", dpi: int = 96, capture: Path | None = None) -> tuple[dict, int]:
    from . import win32
    from .native_capture import capture_client

    payload, layout = demo_payload(theme_id)
    native = NativeSemanticUI(payload, lambda width, height: dict(layout), width=SIZE[0], height=SIZE[1])
    native.window.set_review_dpi(dpi, SIZE)
    capture_meta = None
    if capture is not None:
        def take_snapshot() -> None:
            nonlocal capture_meta
            try:
                capture_meta = capture_client(native.window, capture)
            finally:
                win32.user32.PostMessageW(native.window.hwnd, win32.WM_CLOSE, 0, 0)
        native.window.set_timer(300, take_snapshot)
    exit_code = native.run()
    descriptor = native.witness_descriptor()
    result = {
        "schema": "mosaic.ui.semantic-demo-witness.v0.1",
        "theme_id": theme_id, "dpi": dpi, "dpi_mode": "DETERMINISTIC_REVIEW_PROJECTION",
        "native_realization": descriptor, "capture": capture_meta,
        "exit_code": exit_code, "callback_errors": list(native.window.callback_errors),
        "disposition": "PASS_LOCAL_CANDIDATE" if exit_code == 0 and not native.window.callback_errors else "REFUSE",
        "authority_effect": "NONE",
    }
    if capture is not None and capture.exists():
        result["capture"]["sha256"] = hashlib.sha256(capture.read_bytes()).hexdigest()
    result["commitment"] = commitment("MOSAIC.UI.SEMANTIC_DEMO_WITNESS.v0.1", result)
    if capture is not None:
        atomic_write(capture.with_suffix(".witness.json"), canonical_bytes(result) + b"\n")
    return result, 0 if result["disposition"] == "PASS_LOCAL_CANDIDATE" else 32


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Mosaic declarative native catalog demo.")
    parser.add_argument("--theme", choices=("operations-dark", "high-contrast-dark"), default="operations-dark")
    parser.add_argument("--dpi", type=int, default=96)
    parser.add_argument("--capture", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result, code = run_demo(theme_id=args.theme, dpi=args.dpi,
                            capture=args.capture.resolve() if args.capture else None)
    print(json.dumps(result, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

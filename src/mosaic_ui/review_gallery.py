"""Native Mosaic UI review views and deterministic owned-window captures."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Callable, Iterable

from mosaic_ui.canonical import atomic_write, canonical_bytes, commitment
from mosaic_ui.native_capture import capture_client
from mosaic_ui import win32
from mosaic_ui_std.signature import resolve_signature_theme


VIEW_SIZE = (1120, 720)
VIEW_IDS = ("operations", "workflow", "evidence", "catalog")
THEME_IDS = ("signature-light", "signature-dark", "high-contrast-dark")
DENSITY_IDS = ("comfortable", "compact")
REVIEW_DPIS = (96, 144)


def _tokens(theme_id: str = "signature-dark", density_id: str = "comfortable") -> dict:
    if theme_id not in THEME_IDS:
        raise ValueError(f"unknown review theme: {theme_id}")
    if density_id not in DENSITY_IDS:
        raise ValueError(f"unknown review density: {density_id}")
    return resolve_signature_theme(theme_id, density_id)["tokens"]


def _operations_view(tokens: dict | None = None) -> win32.NativeWindow:
    window = win32.NativeWindow("Mosaic UI Review - Operations", tokens=tokens or _tokens(), width=VIEW_SIZE[0], height=VIEW_SIZE[1])
    window.label("title", "Release operations", (30, 24, 520, 44), style="title")
    window.label("subtitle", "Candidate health and deterministic evidence", (32, 70, 500, 28), style="quiet")
    window.badge("standing", (842, 30, 230, 28))
    window.set_badge("standing", "LOCAL CANDIDATE", "pending")

    window.label("summary.title", "Current run", (30, 122, 280, 30), style="heading")
    window.key_value("summary", "", (30, 158, 492, 164), columns=2)
    window.set_key_value("summary", [
        ("Probe scenarios", "7 / 7 passed", False),
        ("Catalog kinds", "25 declared", False),
        ("Native tier", "25 realized", False),
        ("Witness root", "75c9de0b1749...", True),
    ])
    window.label("progress.label", "Evidence completion", (30, 340, 250, 26))
    window.progress("progress", (30, 374, 492, 18))
    window.set_progress("progress", 86)
    window.stepper("release.steps", ("Build", "Probe", "Witness", "Review"), (30, 430, 492, 52))
    window.set_steps("release.steps", ("Build", "Probe", "Witness", "Review"), 2, "accent")

    window.label("activity.title", "Evidence activity", (558, 122, 280, 30), style="heading")
    window.table("activity", ["Instrument", "Result", "Evidence"], (558, 158, 514, 324))
    window.set_rows("activity", [
        ("Headless replay", "PASS", "14 roots"),
        ("State matrix", "PASS", "7 states"),
        ("Win32 runtime", "PASS", "HWND"),
        ("Interaction", "PASS", "pointer + keys"),
        ("Accessibility", "OBSERVED", "role/name/focus"),
    ])
    window.button("open.evidence", "Review evidence", (558, 520, 172, 42), lambda: window.set_text("status", "Evidence view selected"))
    window.style_button("open.evidence", primary=True)
    window.button("rerun", "Run probes", (744, 520, 148, 42), lambda: window.set_text("status", "Probe request emitted"))
    window.button("export", "Export", (906, 520, 166, 42), lambda: window.set_text("status", "Export request emitted"))
    window.label("status", "Ready for review", (30, 626, 1042, 30), style="quiet")
    return window


def _workflow_view(tokens: dict | None = None) -> win32.NativeWindow:
    window = win32.NativeWindow("Mosaic UI Review - Workflow", tokens=tokens or _tokens(), width=VIEW_SIZE[0], height=VIEW_SIZE[1])
    window.label("title", "Create probe docket", (30, 24, 520, 44), style="title")
    window.label("subtitle", "A compact input and decision workflow", (32, 70, 500, 28), style="quiet")
    window.badge("state", (886, 30, 186, 28))
    window.set_badge("state", "DRAFT", "info")

    window.label("name.label", "Docket name", (30, 126, 220, 26))
    window.edit("name", "library-review-r1", (30, 158, 476, 38))
    window.label("profile.label", "Evidence profile", (30, 220, 220, 26))
    window.combo("profile", ["Balanced", "Deterministic only", "Native interaction"], (30, 252, 476, 38), selected=0)
    window.label("notes.label", "Review note", (30, 314, 220, 26))
    window.edit("notes", "Confirm focus, refusal, pending, and compact-layout behavior.", (30, 346, 476, 94), multiline=True)
    window.checkbox("include.native", "Include native Windows witness", (30, 466, 340, 28), checked=True)
    window.checkbox("include.matrix", "Capture seven-state matrix", (30, 504, 340, 28), checked=True)

    window.label("scope.title", "Bound scope", (552, 126, 300, 30), style="heading")
    window.key_value("scope", "", (552, 164, 520, 204), columns=2)
    window.set_key_value("scope", [
        ("Subject", "mosaic-ui 0.2.0", False),
        ("Viewport", "1120 x 720", False),
        ("Host effects", "NONE", False),
        ("Standing", "LOCAL_CANDIDATE", False),
        ("Authority", "NONE", False),
    ])
    window.stepper("flow", ("Describe", "Bind", "Execute", "Review"), (552, 408, 520, 52))
    window.set_steps("flow", ("Describe", "Bind", "Execute", "Review"), 1, "accent")
    window.button("cancel", "Cancel", (760, 518, 132, 42), lambda: window.set_text("status", "Cancelled"))
    window.button("create", "Create docket", (906, 518, 166, 42), lambda: window.set_text("status", "Docket request emitted"))
    window.style_button("create", primary=True)
    window.label("status", "Inputs are local and effectless", (30, 626, 1042, 30), style="quiet")
    return window


def _evidence_view(tokens: dict | None = None) -> win32.NativeWindow:
    window = win32.NativeWindow("Mosaic UI Review - Evidence", tokens=tokens or _tokens(), width=VIEW_SIZE[0], height=VIEW_SIZE[1])
    window.label("title", "Evidence review", (30, 24, 480, 44), style="title")
    window.label("subtitle", "Receipts, boundaries, and attention points", (32, 70, 520, 28), style="quiet")
    window.badge("verdict", (874, 30, 198, 28))
    window.set_badge("verdict", "PASS LOCAL", "accent")

    window.label("receipt.title", "Receipt binding", (30, 122, 280, 30), style="heading")
    window.key_value("receipt", "", (30, 160, 1042, 150), columns=2)
    window.set_key_value("receipt", [
        ("Generated root", "c392df4fa7a95afe...", True),
        ("Witness commitment", "75c9de0b17496f27...", True),
        ("Probe receipt", "3cda8de5ff72d3ce...", True),
        ("Authority effect", "NONE", False),
    ])
    window.label("checks.title", "Checks", (30, 340, 240, 30), style="heading")
    window.table("checks", ["Surface", "Disposition", "Boundary"], (30, 378, 732, 220))
    window.set_rows("checks", [
        ("Semantic tree", "PASS", "closed schema"),
        ("Layout correspondence", "PASS", "exact keys"),
        ("Replay determinism", "PASS", "two-run match"),
        ("Native interaction", "PASS", "bounded Windows run"),
        ("EVS / COP", "WITNESSED", "consumer-side only"),
    ])
    window.label("attention.title", "Needs attention", (792, 340, 280, 30), style="heading")
    window.badge("attention", (792, 382, 280, 30))
    window.set_badge("attention", "CLAIM BOUNDARY", "pending")
    window.label("attention.copy", "Consumer witness is present. Native UGK EVS/COP remains explicitly unclaimed.", (792, 428, 280, 86))
    window.button("ack", "Mark reviewed", (792, 556, 168, 42), lambda: window.set_text("status", "Review acknowledgement requested"))
    window.style_button("ack", primary=True)
    window.label("status", "Evidence is reviewable; no admission effect", (30, 626, 1042, 30), style="quiet")
    return window


def _catalog_view(tokens: dict | None = None) -> win32.NativeWindow:
    window = win32.NativeWindow("Mosaic UI Review - Native Catalog", tokens=tokens or _tokens(), width=VIEW_SIZE[0], height=VIEW_SIZE[1])
    window.label("title", "Native catalog completion", (30, 24, 600, 44), style="title")
    window.label("subtitle", "The five former headless-only kinds", (32, 70, 500, 28), style="quiet")

    window.label("segmented.label", "Segmented control", (30, 126, 240, 28), style="heading")
    window.segmented("segmented", ("Overview", "Details", "Receipts"), (30, 164, 492, 42), selected="Details",
                     command=lambda value: window.set_text("status", f"Segment selected: {value}"))
    window.label("tabs.label", "Tab bar", (30, 240, 240, 28), style="heading")
    window.tab_bar("tabs", ("Build", "Probe", "Review"), (30, 278, 492, 42), selected="Probe",
                   command=lambda value: window.set_text("status", f"Tab selected: {value}"))
    window.panel("panel", "Panel / grouped surface", (30, 358, 492, 96))
    window.tooltip("tooltip", "Tooltip: bounded native explanation", (58, 478, 354, 40))

    window.label("dialog.label", "Dialog surface", (558, 126, 240, 28), style="heading")
    window.dialog("dialog", "Confirm evidence export", "The export is local and has no authority effect.",
                  ("Cancel", "Export"), (558, 164, 514, 244))
    window.key_value("coverage.detail", "Coverage boundary", (558, 438, 514, 132), columns=1)
    window.set_key_value("coverage.detail", [
        ("Drawing", "25 kinds", False),
        ("Interactive kinds", "16 governed", False),
        ("Accessibility", "IAccessible probe", False),
    ])
    window.badge("coverage", (846, 30, 226, 28))
    window.set_badge("coverage", "25 / 25 WIN32", "accent")
    window.label("status", "Native catalog ready for review", (30, 626, 1042, 30), style="quiet")
    return window


BUILDERS: dict[str, Callable[[dict | None], win32.NativeWindow]] = {
    "operations": _operations_view,
    "workflow": _workflow_view,
    "evidence": _evidence_view,
    "catalog": _catalog_view,
}


def capture_view(view_id: str, output: Path, *, theme_id: str = "signature-dark",
                 density_id: str = "comfortable", dpi: int = 96) -> dict:
    if view_id not in BUILDERS:
        raise ValueError(f"unknown review view: {view_id}")
    window = BUILDERS[view_id](_tokens(theme_id, density_id))
    window.set_review_dpi(dpi, VIEW_SIZE)
    captured: dict = {}

    def take_snapshot() -> None:
        try:
            captured.update(capture_client(window, output))
        finally:
            win32.user32.PostMessageW(window.hwnd, win32.WM_CLOSE, 0, 0)

    window.set_timer(300, take_snapshot)
    exit_code = window.run()
    if not captured:
        raise RuntimeError(f"capture did not complete for {view_id}")
    if window.callback_errors or exit_code != 0:
        raise RuntimeError(f"native review view failed: {view_id}")
    captured.update({
        "view_id": view_id,
        "theme_id": theme_id,
        "density_id": density_id,
        "dpi": dpi,
        "dpi_mode": "DETERMINISTIC_REVIEW_PROJECTION",
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "authority_effect": "NONE",
    })
    return captured


def capture_gallery(output_dir: Path, *, themes: tuple[str, ...] = THEME_IDS,
                    densities: tuple[str, ...] = DENSITY_IDS,
                    dpis: tuple[int, ...] = REVIEW_DPIS) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    captures = [
        capture_view(view_id, output_dir / f"mosaic-ui-{view_id}-{theme_id}-{density_id}-{dpi}.png",
                     theme_id=theme_id, density_id=density_id, dpi=dpi)
        for theme_id in themes
        for density_id in densities
        for dpi in dpis
        for view_id in VIEW_IDS
    ]
    manifest = {
        "schema": "mosaic.ui.review-gallery.v0.1",
        "views": captures,
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "themes": list(themes),
        "densities": list(densities),
        "dpis": list(dpis),
        "claim_boundary": "OWNED_WINDOW_CAPTURES_AND_SYNTHETIC_DPI_PROJECTIONS_SUPPORT_VISUAL_REVIEW_BUT_DO_NOT_ESTABLISH_PHYSICAL_MULTI_MONITOR_OR_BROAD_HOST_FIDELITY",
    }
    manifest["commitment"] = commitment("MOSAIC.UI.REVIEW_GALLERY.v0.1", manifest)
    atomic_write(output_dir / "review-gallery.json", canonical_bytes(manifest) + b"\n")
    return manifest


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Open or capture the Mosaic UI native review gallery.")
    parser.add_argument("--view", choices=VIEW_IDS, default="operations")
    parser.add_argument("--capture-all", type=Path)
    parser.add_argument("--theme", choices=THEME_IDS, default="signature-dark")
    parser.add_argument("--density", choices=DENSITY_IDS, default="comfortable")
    parser.add_argument("--themes", default=",".join(THEME_IDS))
    parser.add_argument("--densities", default=",".join(DENSITY_IDS))
    parser.add_argument("--dpis", default=",".join(str(value) for value in REVIEW_DPIS))
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.capture_all:
        themes = tuple(value.strip() for value in args.themes.split(",") if value.strip())
        densities = tuple(value.strip() for value in args.densities.split(",") if value.strip())
        dpis = tuple(int(value.strip()) for value in args.dpis.split(",") if value.strip())
        print(json.dumps(capture_gallery(args.capture_all.resolve(), themes=themes, densities=densities, dpis=dpis), indent=2, sort_keys=True))
        return 0
    return BUILDERS[args.view](_tokens(args.theme, args.density)).run()


if __name__ == "__main__":
    raise SystemExit(main())

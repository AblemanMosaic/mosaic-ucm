"""Interactive and receipted Win32 review for Mosaic Signature compositions."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any, Callable

from mosaic_ui_std.catalog import load_runtime_catalog
from mosaic_ui_std.signature import load_signature_profile

from .canonical import atomic_write, canonical_bytes, commitment
from .model import UIRefusal
from .signature_profile import build_signature_payload


def _selection(composition_id: str, theme_id: str, density_id: str) -> dict[str, str]:
    profile = load_signature_profile()
    compositions = {item["composition_id"] for item in profile["compositions"]}
    if composition_id not in compositions:
        raise UIRefusal("SIGNATURE_REVIEW_COMPOSITION_REFUSED", composition_id)
    if theme_id not in profile["themes"]:
        raise UIRefusal("SIGNATURE_REVIEW_THEME_REFUSED", theme_id)
    if density_id not in profile["densities"]:
        raise UIRefusal("SIGNATURE_REVIEW_DENSITY_REFUSED", density_id)
    return {"composition_id": composition_id, "theme_id": theme_id, "density_id": density_id}


def run_signature_review(composition_id: str = "operational-dashboard", *,
                         theme_id: str = "signature-dark", density_id: str = "comfortable",
                         width: int = 1280, height: int = 800, capture: Path | None = None,
                         native_factory: Callable[..., Any] | None = None,
                         native_workbench_runner: Callable[..., Any] | None = None,
                         review_mode: str = "conformance", realizer: str = "WIN32",
                         scenario: str | None = None, export_root: Path | None = None,
                         record: Path | None = None, subject_id: str | None = None) -> dict[str, Any]:
    """Open a Signature composition or capture and close it under the native message loop."""
    review_mode = review_mode.lower()
    realizer = realizer.upper()
    if review_mode not in {"conformance", "functional"}:
        raise UIRefusal("SIGNATURE_REVIEW_MODE_REFUSED", review_mode)
    if realizer not in {"WIN32", "HEADLESS"}:
        raise UIRefusal("SIGNATURE_REVIEW_REALIZER_REFUSED", realizer)
    if realizer == "HEADLESS" and review_mode != "functional":
        raise UIRefusal("SIGNATURE_REVIEW_MODE_REFUSED", "HEADLESS_REQUIRES_FUNCTIONAL")
    default_native = native_factory is None
    if realizer == "WIN32" and default_native:
        from .native_realizer import NativeSemanticUI

        native_factory = NativeSemanticUI
    if realizer == "WIN32" and default_native and sys.platform != "win32":
        raise UIRefusal("SIGNATURE_REVIEW_REALIZER_REFUSED", sys.platform)
    if width < 480 or height < 400:
        raise UIRefusal("SIGNATURE_REVIEW_VIEWPORT_REFUSED", f"{width}x{height}")
    selection = _selection(composition_id, theme_id, density_id)
    profile = load_signature_profile()
    composition = next(item for item in profile["compositions"] if item["composition_id"] == composition_id)
    if review_mode == "functional" and realizer == "WIN32" and scenario is None:
        if native_workbench_runner is None:
            from .native_review_workbench import run_native_review_workbench

            native_workbench_runner = run_native_review_workbench
        return native_workbench_runner(
            width=width, height=height, theme_id=theme_id, density_id=density_id,
            subject_id=subject_id or f"surface.{composition_id}", capture=capture,
            export_root=export_root, record=record,
        )
    session = None
    scenario_witness = None
    if review_mode == "functional":
        from .signature_review_host import SCENARIOS, SignatureReviewSession, run_scenario

        session = SignatureReviewSession(
            composition_id, theme_id=theme_id, density_id=density_id, export_root=export_root,
        )
        if realizer == "HEADLESS":
            selected_scenario = scenario or SCENARIOS[composition_id][0]
            scenario_witness = run_scenario(session, selected_scenario)
            if record is not None:
                session.record(record, selected_scenario)
            projection = session.runtime.ui.project(width, height).as_dict()
            failures = [] if projection["gates"]["disposition"] == "PASS" \
                and scenario_witness["disposition"] == "PASS_LOCAL_CANDIDATE" else ["HEADLESS_SCENARIO"]
            result = {
                "schema": "mosaic.ui.signature-native-review.v0.2",
                "profile_id": profile["profile_id"], "profile_version": profile["profile_version"],
                "selection": selection, "realizer": "HEADLESS", "viewport": {"width": width, "height": height},
                "mode": "HEADLESS", "review_mode": "FUNCTIONAL", "scenario": selected_scenario,
                "projection_commitment": projection["gates"]["commitment"],
                "descriptor_commitment": None, "capture": None, "accessibility_commitment": None,
                "session": session.witness(selected_scenario), "scenario_witness": scenario_witness,
                "record_path": str(record.resolve()) if record is not None else None,
                "exit_code": 0, "callback_error_count": 0, "failures": failures,
                "platform": platform.platform(), "python": platform.python_version(),
                "disposition": "PASS_LOCAL_CANDIDATE" if not failures else "REFUSE",
                "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
                "claim_boundary": "HEADLESS_FUNCTIONAL_REVIEW_ESTABLISHES_MODEL_AND_EFFECT EVIDENCE FOR THIS LOCAL RUN ONLY",
            }
            result["commitment"] = commitment("MOSAIC.UI.SIGNATURE_NATIVE_REVIEW.v0.2", result)
            return result
        payload = session.payload
        native = native_factory(
            payload, width=width, height=height, catalog=load_runtime_catalog(),
            title=f"Mosaic Signature Review - {composition['name']}",
            headless=session.runtime.ui, event_dispatch=session.dispatch,
        )
        confirm = getattr(native.window, "confirm", None)
        if callable(confirm):
            session.confirmation = confirm
    else:
        if scenario is not None:
            raise UIRefusal("SIGNATURE_REVIEW_SCENARIO_REFUSED", "CONFORMANCE_MODE")
        native = native_factory(
            build_signature_payload(**selection), width=width, height=height,
            catalog=load_runtime_catalog(), title=f"Mosaic Signature - {composition['name']}",
        )
    captured: dict[str, Any] | None = None
    accessibility: dict[str, Any] | None = None
    descriptor = native.witness_descriptor()
    try:
        if capture is not None:
            capture = capture.resolve()
            capture.parent.mkdir(parents=True, exist_ok=True)

            def capture_and_close() -> None:
                nonlocal captured, accessibility, scenario_witness
                from . import win32
                from .native_capture import capture_client

                try:
                    if session is not None and scenario is not None:
                        from .signature_review_host import run_scenario

                        scenario_witness = run_scenario(session, scenario)
                        native.sync()
                    native.window.relayout()
                    captured = capture_client(native.window, capture)
                    captured["sha256"] = hashlib.sha256(capture.read_bytes()).hexdigest()
                    accessibility = native.accessibility_witness()
                finally:
                    win32.user32.PostMessageW(native.window.hwnd, win32.WM_CLOSE, 0, 0)

            native.window.set_timer(300, capture_and_close)
        elif session is not None and scenario is not None:
            def drive_scenario() -> None:
                nonlocal scenario_witness
                from . import win32
                from .signature_review_host import run_scenario

                win32.user32.KillTimer(native.window.hwnd, 1)
                scenario_witness = run_scenario(session, scenario)
                native.sync()

            native.window.set_timer(300, drive_scenario)
        exit_code = native.run()
        callback_errors = [str(error) for error in getattr(native.window, "callback_errors", ())]
    finally:
        native.close()
    projection = native.project(width, height)
    if session is not None and scenario is not None and scenario_witness is None:
        from .signature_review_host import run_scenario

        scenario_witness = run_scenario(session, scenario)
    if session is not None and record is not None:
        session.record(record, scenario)
    failures = []
    if exit_code != 0:
        failures.append(f"EXIT_CODE:{exit_code}")
    if callback_errors:
        failures.append("CALLBACK_ERRORS")
    if projection["gates"]["disposition"] != "PASS":
        failures.append("PROJECTION_GATES")
    if capture is not None and captured is None:
        failures.append("CAPTURE_MISSING")
    if accessibility is not None and accessibility["disposition"] != "PASS_LOCAL_CANDIDATE":
        failures.append("ACCESSIBILITY")
    if scenario_witness is not None and scenario_witness["disposition"] != "PASS_LOCAL_CANDIDATE":
        failures.append("SCENARIO")
    result = {
        "schema": "mosaic.ui.signature-native-review.v0.2" if review_mode == "functional" else "mosaic.ui.signature-native-review.v0.1",
        "profile_id": profile["profile_id"], "profile_version": profile["profile_version"],
        "selection": selection, "realizer": "WIN32", "viewport": {"width": width, "height": height},
        "mode": "CAPTURE" if capture is not None else "INTERACTIVE",
        "review_mode": review_mode.upper(), "scenario": scenario,
        "projection_commitment": projection.get("commitment") or commitment(
            "MOSAIC.UI.SIGNATURE_NATIVE_REVIEW.PROJECTION.v0.1", projection,
        ),
        "descriptor_commitment": descriptor["commitment"],
        "capture": captured,
        "accessibility_commitment": accessibility["commitment"] if accessibility is not None else None,
        "session": session.witness(scenario) if session is not None else None,
        "scenario_witness": scenario_witness,
        "record_path": str(record.resolve()) if record is not None else None,
        "exit_code": exit_code, "callback_error_count": len(callback_errors), "failures": failures,
        "platform": platform.platform(), "python": platform.python_version(),
        "disposition": "PASS_LOCAL_CANDIDATE" if not failures else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
        "claim_boundary": "INTERACTIVE_OR_OWNED_WINDOW_REVIEW_ESTABLISHES_THIS_HOST_RUN_ONLY; BROAD_HOST_ACCEPTANCE_IS_NOT_ESTABLISHED",
    }
    domain = "MOSAIC.UI.SIGNATURE_NATIVE_REVIEW.v0.2" if review_mode == "functional" \
        else "MOSAIC.UI.SIGNATURE_NATIVE_REVIEW.v0.1"
    result["commitment"] = commitment(domain, result)
    return result


def main(argv: list[str] | None = None) -> int:
    profile = load_signature_profile()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--realizer", choices=("WIN32", "HEADLESS"), default="WIN32")
    parser.add_argument("--mode", choices=("functional", "conformance"), default="conformance")
    parser.add_argument("--composition", choices=tuple(item["composition_id"] for item in profile["compositions"]),
                        default="operational-dashboard")
    parser.add_argument("--theme", choices=tuple(profile["themes"]), default=profile["default_theme"])
    parser.add_argument("--density", choices=tuple(profile["densities"]), default=profile["default_density"])
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--scenario")
    parser.add_argument("--export-root", type=Path)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--subject")
    parser.add_argument("--list-scenarios", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.list_scenarios:
        from .signature_review_host import list_scenarios

        result = list_scenarios(args.composition)
    else:
        result = run_signature_review(
        args.composition, theme_id=args.theme, density_id=args.density,
        width=args.width, height=args.height, capture=args.capture,
        review_mode=args.mode, realizer=args.realizer, scenario=args.scenario,
        export_root=args.export_root, record=args.record, subject_id=args.subject,
        )
    if args.output:
        atomic_write(args.output.resolve(), canonical_bytes(result) + b"\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["disposition"] == "PASS_LOCAL_CANDIDATE" else 32


if __name__ == "__main__":
    raise SystemExit(main())

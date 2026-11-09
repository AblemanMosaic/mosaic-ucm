"""Bounded native witness for the Mosaic Release Console pilot."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any

from .canonical import commitment
from .native_capture import capture_client
from .native_realizer import NativeSemanticUI
from .pilot import build_runtime


def run_native_pilot(screenshot: Path, *, width: int = 1100, height: int = 760) -> dict[str, Any]:
    governed = build_runtime()
    for node_id in ("release.refresh", "release.verify", "release.model"):
        governed.dispatch({"intent": "ACTIVATE", "node_id": node_id})
        governed.run_next()
    native = NativeSemanticUI(governed.ui.payload, None, width=width, height=height,
                              title="Mosaic Release Console")
    native.runtime.state = copy.deepcopy(governed.ui.state)
    native.sync()
    observed: dict[str, Any] = {}

    def exercise() -> None:
        try:
            native.window.set_text("release.status", "Pilot evidence ready")
            native.window.relayout()
            observed["accessibility"] = native.accessibility_witness()
            observed["capture"] = capture_client(native.window, screenshot)
        finally:
            native.close()

    native.window.set_timer(350, exercise)
    exit_code = native.run()
    capture = observed.get("capture", {})
    if screenshot.is_file():
        capture["sha256"] = hashlib.sha256(screenshot.read_bytes()).hexdigest()
    accessibility = observed.get("accessibility", {})
    passed = exit_code == 0 and screenshot.is_file() and accessibility.get("disposition") == "PASS_LOCAL_CANDIDATE"
    value = {
        "schema": "mosaic.ui.pilot-native-witness.v0.1",
        "application_id": "MOSAIC_RELEASE_CONSOLE",
        "runtime_ledger_head": governed.snapshot()["ledger_head"],
        "native_realization": native.witness_descriptor(),
        "accessibility": accessibility,
        "capture": capture,
        "exit_code": exit_code,
        "disposition": "PASS_LOCAL_CANDIDATE" if passed else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "host_effect": "VISIBLE_LOCAL_WITNESS_ONLY",
        "claim_boundary": "OWNED_WINDOW_CAPTURE_AND_DIRECT_MSAA_INSPECTION_DO_NOT_ESTABLISH_HUMAN_INPUT_SCREEN_READER_OR_BROAD_HOST_BEHAVIOR",
    }
    value["commitment"] = commitment("MOSAIC.UI.PILOT_NATIVE_WITNESS.v0.1", value)
    return value


__all__ = ["run_native_pilot"]

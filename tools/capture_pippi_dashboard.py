"""Capture the P/PPI dashboard and About modal without desktop input."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
for candidate in (ROOT / "vendor" / "mosaic-native", ROOT / "src"):
    if str(candidate) not in sys.path:sys.path.insert(0,str(candidate))

from ucm.pippi_dashboard import Dashboard, _load_native
from ucm.pippi_global import PippiHub


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--width", type=int, default=1424)
    parser.add_argument("--height", type=int, default=860)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    dashboard = Dashboard(PippiHub(args.data_root))
    dashboard.window.set_client_size(args.width, args.height)
    win32, _image, _logo, _resolve = _load_native()
    from mosaic_ui.native_capture import capture_client

    dashboard_path = output / "PIPPI-r016-DASHBOARD.png"
    about_path = output / "PIPPI-r016-ABOUT.png"
    substance_path = output / "PIPPI-r016-REVIEW-SUBSTANCE.png"
    publication_path = output / "PIPPI-r016-PUBLICATION-PROPOSAL.png"
    about = substance = publication = None
    captures = []
    try:
        win32.user32.ShowWindow(dashboard.window.hwnd, 5)
        win32.user32.UpdateWindow(dashboard.window.hwnd)
        dashboard_capture = capture_client(dashboard.window, dashboard_path)
        captures.append({**dashboard_capture, "sha256": sha256(dashboard_path)})

        about = dashboard._build_about_window()
        about.show_modal("close")
        win32.user32.UpdateWindow(about.hwnd)
        about_capture = capture_client(about, about_path)
        captures.append({**about_capture, "sha256": sha256(about_path)})
        about.close(); about = None

        if dashboard.review_store.list(dashboard.current()["project_id"]):
            dashboard.selected_review_id = dashboard.review_store.list(dashboard.current()["project_id"])[0]["review_id"]
            substance = dashboard._build_review_substance_window()
            substance.show_modal("close")
            win32.user32.UpdateWindow(substance.hwnd)
            substance_capture = capture_client(substance, substance_path)
            captures.append({**substance_capture, "sha256": sha256(substance_path)})
            substance.close(); substance = None

            publication = dashboard._build_publication_window()
            publication.show_modal("artifact_path")
            win32.user32.UpdateWindow(publication.hwnd)
            publication_capture = capture_client(publication, publication_path)
            captures.append({**publication_capture, "sha256": sha256(publication_path)})
    finally:
        if about is not None:
            about.close()
        if substance is not None:
            substance.close()
        if publication is not None:
            publication.close()
        dashboard.window.close()
        dashboard.logo.close()

    result = {
        "schema": "mosaic.pippi.native-dashboard-capture.v0.1",
        "status": "PASS",
        "desktop_input": False,
        "revision": "r016",
        "captures": captures,
        "authority_effect": "NONE",
    }
    (output / "PIPPI-r016-UI-CAPTURE.json").write_text(
        json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

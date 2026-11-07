"""Windowless launcher and governed startup splash for Mosaic UI Review."""
from __future__ import annotations

import argparse
import queue
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Callable, TypeVar

from mosaic_ui_std.signature import resolve_signature_theme

from .branding import APPLICATION_ID, APPLICATION_TITLE, LOGO_SHA256, verified_logo_path
from .model import UIRefusal


T = TypeVar("T")
Reporter = Callable[[str, float], None]
MINIMUM_SPLASH_SECONDS = 2.0


class StartupSplash:
    """Keep startup responsive while local runtime probes run on a worker thread."""

    def __init__(self, *, capture: Path | None = None) -> None:
        from . import win32
        from .win32_image import NativeImage

        if win32.shell32.SetCurrentProcessExplicitAppUserModelID(APPLICATION_ID) < 0:
            raise OSError("Could not establish Mosaic UI Review taskbar identity")
        logo_path = verified_logo_path()
        tokens = resolve_signature_theme("signature-dark", "comfortable")["tokens"]
        self.win32 = win32
        self.logo = NativeImage(logo_path)
        self.window = win32.NativeWindow(
            APPLICATION_TITLE, tokens=tokens, width=620, height=350, presentation="splash",
        )
        self.window.set_icon(self.logo)
        self.window.image("brand.logo", self.logo, (34, 38, 158, 158), name="Mosaic")
        self.window.label("title", APPLICATION_TITLE, (218, 56, 360, 44), style="title")
        self.window.label("subtitle", "Governed component library review", (220, 108, 354, 52),
                          style="heading")
        self.window.label("status", "Starting local runtime...", (36, 228, 548, 28))
        self.window.progress("progress", (36, 267, 548, 9))
        self.window.label("posture", "Local native runtime / evidence remains local",
                          (36, 298, 548, 24), style="quiet")
        self.window.set_progress("progress", 4)
        self.messages: queue.Queue[tuple[str, object, float | None]] = queue.Queue()
        self.result: T | None = None
        self.error: BaseException | None = None
        self.capture = capture.resolve() if capture is not None else None
        self.capture_result: dict | None = None
        self.visible_since: float | None = None
        self.finished = False
        self.window.set_timer(40, self._poll)

    def report(self, message: str, percent: float) -> None:
        self.messages.put(("status", message, percent))

    def _work(self, task: Callable[[Reporter], T]) -> None:
        try:
            self.messages.put(("result", task(self.report), None))
        except BaseException as exc:
            self.messages.put(("error", exc, None))

    def _poll(self) -> None:
        if self.capture is not None and self.capture_result is None:
            from .native_capture import capture_client

            self.capture.parent.mkdir(parents=True, exist_ok=True)
            self.capture_result = capture_client(self.window, self.capture)
        while True:
            try:
                kind, value, percent = self.messages.get_nowait()
            except queue.Empty:
                break
            if kind == "status":
                self.window.set_text("status", str(value))
                self.window.set_progress("progress", float(percent or 0))
            elif kind == "result":
                self.result = value  # type: ignore[assignment]
                self.finished = True
            else:
                self.error = value if isinstance(value, BaseException) else RuntimeError(str(value))
                self.finished = True
        if self.finished and self._minimum_time_elapsed():
            self.window.close()

    def _minimum_time_elapsed(self, now: float | None = None) -> bool:
        if self.visible_since is None:
            return False
        observed = time.monotonic() if now is None else now
        return observed - self.visible_since >= MINIMUM_SPLASH_SECONDS

    def run(self, task: Callable[[Reporter], T]) -> T:
        worker = threading.Thread(target=self._work, args=(task,), name="mosaic-ui-startup", daemon=True)
        worker.start()
        self.visible_since = time.monotonic()
        try:
            self.window.run()
            worker.join()
        finally:
            self.logo.close()
        if self.error is not None:
            raise self.error
        return self.result  # type: ignore[return-value]


def _startup_probe(root: Path, report: Reporter) -> dict:
    from .review_experience_audit import review_experience_audit

    output = root / "mosaic-review-output" / "review-experience-audit.json"
    result = review_experience_audit(output, reporter=report)
    if result["disposition"] != "PASS_LOCAL_CANDIDATE":
        raise UIRefusal("REVIEW_STARTUP_AUDIT_REFUSED", str(result["failure_count"]))
    return result


def launch(*, splash: bool = True) -> dict:
    from .native_review_workbench import run_native_review_workbench

    root = Path(__file__).resolve().parents[1]
    output = root / "mosaic-review-output"
    output.mkdir(parents=True, exist_ok=True)
    if splash:
        StartupSplash().run(lambda report: _startup_probe(root, report))
    else:
        _startup_probe(root, lambda message, percent: print(f"[{percent:3.0f}%] {message}", flush=True))
    return run_native_review_workbench(
        width=1440, height=900,
        theme_id="signature-dark", density_id="comfortable", subject_id="component.button",
        export_root=output, record=output / "native-review-run.json",
    )


def _show_failure(message: str) -> None:
    try:
        from .win32 import user32

        user32.MessageBoxW(None, message, APPLICATION_TITLE, 0x00000010)
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mosaic-ui-review")
    parser.add_argument("--console", action="store_true", help="Run startup checks without the splash")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    output = root / "mosaic-review-output"
    output.mkdir(parents=True, exist_ok=True)
    log_path = output / "startup.log"
    stream = None
    if not args.console:
        stream = log_path.open("a", encoding="utf-8")
        sys.stdout = stream
        sys.stderr = stream
    try:
        result = launch(splash=not args.console)
        return 0 if result["disposition"] == "PASS_LOCAL_CANDIDATE" else 32
    except BaseException:
        traceback.print_exc()
        _show_failure(f"Mosaic UI Review could not start.\n\nDetails were written to:\n{log_path}")
        return 32
    finally:
        if stream is not None:
            stream.flush()
            stream.close()


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["MINIMUM_SPLASH_SECONDS", "StartupSplash", "launch", "main"]

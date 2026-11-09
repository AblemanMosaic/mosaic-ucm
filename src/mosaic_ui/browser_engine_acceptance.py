"""Governed local acceptance across explicitly supplied headless browser engines."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

from .browser_realizer import create_browser_server
from .canonical import atomic_write, canonical_bytes, commitment
from .model import UIRefusal
from .sufficiency import build_sufficiency_payload
from .visual_gate import VisualGateRefusal, _png_rgb, compare_pngs


SCHEMA = "mosaic.ui.browser-engine-acceptance.v0.1"
_ENGINE_ID = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
_CLIENT_SECRETS = re.compile(r'const mosaicSession="[^"]+",mosaicToken="[^"]+"')
EXPECTED_CHOICES = {
    "File": "\u0645\u0644\u0641", "Edit": "\u062a\u062d\u0631\u064a\u0631", "View": "\u0639\u0631\u0636",
    "US West": "\u063a\u0631\u0628 \u0627\u0644\u0648\u0644\u0627\u064a\u0627\u062a \u0627\u0644\u0645\u062a\u062d\u062f\u0629",
    "US East": "\u0634\u0631\u0642 \u0627\u0644\u0648\u0644\u0627\u064a\u0627\u062a \u0627\u0644\u0645\u062a\u062d\u062f\u0629",
    "Europe": "\u0623\u0648\u0631\u0648\u0628\u0627",
    "Overview": "\u0646\u0638\u0631\u0629 \u0639\u0627\u0645\u0629", "Evidence": "\u0627\u0644\u0623\u062f\u0644\u0629",
    "Release": "\u0627\u0644\u0625\u0635\u062f\u0627\u0631", "Stable": "\u0645\u0633\u062a\u0642\u0631", "Beta": "\u062a\u062c\u0631\u064a\u0628\u064a",
    "Jobs": "\u0627\u0644\u0645\u0647\u0627\u0645", "Receipts": "\u0627\u0644\u0625\u064a\u0635\u0627\u0644\u0627\u062a",
    "Policies": "\u0627\u0644\u0633\u064a\u0627\u0633\u0627\u062a", "Workspace": "\u0645\u0633\u0627\u062d\u0629 \u0627\u0644\u0639\u0645\u0644",
    "Applications": "\u0627\u0644\u062a\u0637\u0628\u064a\u0642\u0627\u062a", "Releases": "\u0627\u0644\u0625\u0635\u062f\u0627\u0631\u0627\u062a",
}


class _DOMProbe(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang = ""
        self.direction = ""
        self.choices: dict[str, str] = {}
        self._choice: tuple[str, str, list[str]] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html":
            self.lang, self.direction = values.get("lang", ""), values.get("dir", "")
        stable = values.get("data-choice") if tag == "button" else values.get("value") if tag == "option" else None
        if stable is not None:
            self._choice = (tag, stable, [])

    def handle_data(self, data: str) -> None:
        if self._choice is not None:
            self._choice[2].append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._choice is not None and tag == self._choice[0]:
            _tag, stable, pieces = self._choice
            self.choices[stable] = "".join(pieces).strip()
            self._choice = None


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sanitize_dom(document: str) -> str:
    return _CLIENT_SECRETS.sub('const mosaicSession="[REDACTED]",mosaicToken="[REDACTED]"', document)


def audit_dom(document: str) -> dict[str, Any]:
    probe = _DOMProbe()
    probe.feed(document)
    choice_checks = {stable: probe.choices.get(stable) == label for stable, label in EXPECTED_CHOICES.items()}
    checks = {
        "LANG_AR": probe.lang == "ar",
        "DIRECTION_RTL": probe.direction == "rtl",
        "STABLE_TRANSLATED_CHOICES": all(choice_checks.values()),
        "LOGICAL_CSS": "text-align:start" in document and "border-inline-start" in document,
        "NO_UNRESOLVED_MESSAGE_REFS": "message_id" not in document,
        "LOCALIZED_GRID_AND_STATUS": all(value in document for value in (
            "\u0627\u0644\u0627\u0633\u0645", "\u0627\u0644\u062d\u0627\u0644\u0629",
            "\u0627\u062c\u062a\u0627\u0632\u062a \u0628\u0648\u0627\u0628\u0627\u062a \u0627\u0644\u062c\u0627\u0647\u0632\u064a\u0629 \u0627\u0644\u0645\u062d\u0644\u064a\u0629",
        )),
    }
    return {"checks": checks, "choice_checks": choice_checks,
            "choice_count": len(probe.choices), "disposition": "PASS" if all(checks.values()) else "REFUSE"}


def _engine_specs(values: Iterable[str]) -> list[tuple[str, Path]]:
    result = []
    for value in values:
        engine_id, separator, raw_path = value.partition("=")
        path = Path(raw_path).resolve() if separator else Path()
        if not separator or not _ENGINE_ID.fullmatch(engine_id) or not path.is_file():
            raise UIRefusal("BROWSER_ENGINE_SPEC_REFUSED", value)
        result.append((engine_id, path))
    if len(result) < 2 or len({item[0] for item in result}) != len(result):
        raise UIRefusal("BROWSER_ENGINE_SET_REFUSED", "AT_LEAST_TWO_UNIQUE_EXPLICIT_ENGINES_REQUIRED")
    return result


def _invoke(executable: Path, arguments: list[str], stdout: Path, stderr: Path) -> int:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    with stdout.open("wb") as output_handle, stderr.open("wb") as error_handle:
        run = subprocess.run([str(executable), *arguments], stdout=output_handle, stderr=error_handle,
                             timeout=90, creationflags=flags)
    return run.returncode


def _capture_engine(engine_id: str, executable: Path, url: str, output: Path, profile_root: Path,
                    width: int, height: int) -> dict[str, Any]:
    dom_raw, dom_error = output / f"{engine_id}-raw.html", output / f"{engine_id}-dom.stderr"
    screenshot = output / f"{engine_id}.png"
    shot_output, shot_error = output / f"{engine_id}-screenshot.stdout", output / f"{engine_id}-screenshot.stderr"
    common = ["--headless", "--disable-gpu", "--disable-background-networking", "--disable-component-update",
              "--disable-default-apps", "--disable-sync", "--no-first-run", "--no-default-browser-check"]
    dom_code = _invoke(executable, [*common, f"--user-data-dir={profile_root / (engine_id + '-dom')}",
                                    "--dump-dom", url], dom_raw, dom_error)
    shot_code = _invoke(executable, [*common, f"--window-size={width},{height}",
                                     f"--user-data-dir={profile_root / (engine_id + '-shot')}",
                                     f"--screenshot={screenshot}", url], shot_output, shot_error)
    raw_document = dom_raw.read_text(encoding="utf-8") if dom_raw.is_file() else ""
    sanitized = sanitize_dom(raw_document)
    dom = output / f"{engine_id}.html"
    dom.write_text(sanitized, encoding="utf-8", newline="\n")
    dom_raw.unlink(missing_ok=True)
    dom_audit = audit_dom(sanitized)
    image = {"width": 0, "height": 0, "distinct_color_count": 0, "rendered_pixel_ratio": 0.0}
    image_ok = False
    if screenshot.is_file():
        try:
            image_width, image_height, pixels = _png_rgb(screenshot)
            colors = {pixels[index:index + 3] for index in range(0, len(pixels), 3)}
            background = pixels[:3]
            rendered = sum(pixels[index:index + 3] != background for index in range(0, len(pixels), 3))
            image = {"width": image_width, "height": image_height, "distinct_color_count": len(colors),
                     "rendered_pixel_ratio": round(rendered / max(1, image_width * image_height), 9)}
            image_ok = (image_width, image_height) == (width, height) and len(colors) >= 16 \
                and image["rendered_pixel_ratio"] >= 0.05
        except (OSError, ValueError, VisualGateRefusal):
            pass
    checks = {"DOM_PROCESS": dom_code == 0, "SCREENSHOT_PROCESS": shot_code == 0,
              "DOM_SEMANTICS": dom_audit["disposition"] == "PASS", "SCREENSHOT_CONTENT": image_ok,
              "CLIENT_SECRETS_REDACTED": "[REDACTED]" in sanitized and "mosaicToken=\"[REDACTED]\"" in sanitized}
    return {
        "engine_id": engine_id, "engine_family": "CHROMIUM_CLI", "executable_sha256": _sha(executable),
        "executable_bytes": executable.stat().st_size, "dom_artifact": dom.name, "dom_sha256": _sha(dom),
        "screenshot_artifact": screenshot.name, "screenshot_sha256": _sha(screenshot) if screenshot.is_file() else None,
        "stderr_bytes": dom_error.stat().st_size + shot_error.stat().st_size,
        "dom": dom_audit, "image": image, "checks": checks,
        "disposition": "PASS" if all(checks.values()) else "REFUSE",
    }


def run_browser_engine_acceptance(engine_specs: Iterable[str], output: Path, *, width: int = 676,
                                  height: int = 600, max_mismatch_ratio: float = 0.005,
                                  max_mean_channel_delta: float = 0.001) -> dict[str, Any]:
    engines = _engine_specs(engine_specs)
    output = output.resolve()
    if output.exists() or not 320 <= width <= 4096 or not 240 <= height <= 2160:
        raise UIRefusal("BROWSER_ENGINE_OUTPUT_REFUSED", str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    server, manager = create_browser_server(build_sufficiency_payload(), port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/?locale=ar&width=640&height=600"
        profile_root = Path(tempfile.mkdtemp(prefix="mosaic-ui-browser-engines-", dir=output.parent))
        try:
            rows = [_capture_engine(engine_id, executable, url, output, profile_root, width, height)
                    for engine_id, executable in engines]
        finally:
            shutil.rmtree(profile_root, ignore_errors=True)
    finally:
        server.shutdown()
        server.server_close()
        manager.close()
        thread.join(5)
    comparisons = []
    for index, left in enumerate(rows):
        for right in rows[index + 1:]:
            if left["screenshot_sha256"] and right["screenshot_sha256"]:
                diff = compare_pngs(output / left["screenshot_artifact"], output / right["screenshot_artifact"])
                passed = diff["dimensions_match"] and diff["mismatch_ratio"] <= max_mismatch_ratio \
                    and diff["mean_channel_delta"] <= max_mean_channel_delta
                comparisons.append({"left": left["engine_id"], "right": right["engine_id"], "diff": diff,
                                    "disposition": "PASS" if passed else "REFUSE"})
    passed = all(row["disposition"] == "PASS" for row in rows) and comparisons \
        and all(row["disposition"] == "PASS" for row in comparisons)
    value = {
        "schema": SCHEMA, "engine_count": len(rows), "engines": rows, "comparisons": comparisons,
        "thresholds": {"max_mismatch_ratio": max_mismatch_ratio,
                       "max_mean_channel_delta": max_mean_channel_delta},
        "disposition": "PASS_LOCAL_CANDIDATE" if passed else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
        "claim_boundary": "EXPLICIT_INSTALLED_CHROMIUM_FAMILY_ENGINES_ON_ONE_HOST; FIREFOX_WEBKIT_MOBILE_AT_AND_BROAD_BROWSER_CERTIFICATION_NOT_ESTABLISHED",
    }
    value["commitment"] = commitment("MOSAIC.UI.BROWSER_ENGINE_ACCEPTANCE.v0.1", value)
    atomic_write(output / "browser-engine-acceptance.json", canonical_bytes(value) + b"\n")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", action="append", required=True, help="Explicit ID=executable path; repeat twice or more")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=676)
    parser.add_argument("--height", type=int, default=600)
    args = parser.parse_args(argv)
    try:
        value = run_browser_engine_acceptance(args.engine, args.output, width=args.width, height=args.height)
        print(json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2))
        return 0 if value["disposition"] == "PASS_LOCAL_CANDIDATE" else 32
    except (UIRefusal, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"schema": "mosaic.ui.browser-engine-acceptance-refusal.v0.1", "disposition": "REFUSE",
                          "refusal_code": getattr(exc, "code", "BROWSER_ENGINE_ACCEPTANCE_REFUSED"),
                          "detail": getattr(exc, "detail", str(exc)), "authority_effect": "NONE"}, indent=2))
        return 32


if __name__ == "__main__":
    raise SystemExit(main())

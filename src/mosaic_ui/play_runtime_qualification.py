"""Host-specific qualification of an explicit installed Chromium Play runtime."""
from __future__ import annotations

import copy
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .adapter_sdk import AdapterManifest, GovernedAdapterSession, adapter_lifecycle_witness
from .canonical import atomic_write, canonical_bytes, commitment, read_json
from .domain_protocol import DomainRefusal, require_exact_mapping
from .play import PLAY_ACTION_TYPES, PLAY_EVENT_SCHEMA, PlayHeadlessRunner, reference_play_scene
from .play_adapters import (
    build_canvas_document, play_artifact_result, play_semantic_observation,
)
from .visual_gate import VisualGateRefusal, _png_rgb


POLICY_PATH = Path(__file__).resolve().parent / "source" / "play-runtime-policy.json"
POLICY_SCHEMA = "mosaic.play.external-runtime-policy.v0.1"
RUNTIME_FAMILY = "CHROMIUM_CANVAS_2D"
_VERSION = re.compile(r"(?:HeadlessChrome|Chrome|Edg)/(?P<version>\d+(?:\.\d+){1,3})")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def play_runtime_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    value = read_json(path)
    require_exact_mapping(value, {
        "schema", "runtime_family", "minimum_major_version", "process_timeout_seconds",
        "process_runs", "viewport", "maximum_artifact_bytes", "maximum_scene_assets",
        "maximum_scene_asset_bytes", "allowed_asset_media_kinds", "allowed_action_types",
        "asset_mode", "input_mode", "network_mode", "standing", "authority_effect",
    }, "PLAY_RUNTIME_POLICY_SCHEMA_REFUSED")
    limits = value["maximum_artifact_bytes"]
    if value["schema"] != POLICY_SCHEMA or value["runtime_family"] != RUNTIME_FAMILY \
            or value["authority_effect"] != "NONE" or value["process_runs"] != 2 \
            or not isinstance(value["minimum_major_version"], int) \
            or value["minimum_major_version"] < 1 \
            or not isinstance(value["process_timeout_seconds"], int) \
            or not 1 <= value["process_timeout_seconds"] <= 120 \
            or value["viewport"] != [640, 360] \
            or set(limits) != {"HTML", "DOM", "PNG"} \
            or not all(isinstance(item, int) and item > 0 for item in limits.values()) \
            or not isinstance(value["maximum_scene_assets"], int) \
            or not isinstance(value["maximum_scene_asset_bytes"], int) \
            or value["maximum_scene_assets"] < 0 or value["maximum_scene_asset_bytes"] < 0 \
            or value["allowed_action_types"] != sorted(PLAY_ACTION_TYPES) \
            or value["allowed_asset_media_kinds"] != sorted(set(value["allowed_asset_media_kinds"])) \
            or value["asset_mode"] != "DECLARED_HASH_REFERENCES_ONLY_NO_RUNTIME_FETCH" \
            or value["input_mode"] != "UPSTREAM_HEADLESS_TRANSITIONS_PROJECTION_ONLY" \
            or value["network_mode"] != "FILE_ARTIFACT_WITH_EXTERNAL_NAME_RESOLUTION_DISABLED":
        raise DomainRefusal("PLAY_RUNTIME_POLICY_REFUSED")
    result = copy.deepcopy(value)
    result["commitment"] = commitment("MOSAIC.PLAY.EXTERNAL_RUNTIME_POLICY.v0.1", value)
    return result


def discover_chromium_runtimes() -> list[dict[str, Any]]:
    candidates = (
        ("chrome", Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")),
        ("chrome-x86", Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")),
        ("edge", Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")),
        ("edge-x64", Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")),
    ) if sys.platform == "win32" else tuple(
        (name, Path(path)) for name, path in (
            ("chromium", "/usr/bin/chromium"), ("chromium-browser", "/usr/bin/chromium-browser"),
            ("chrome", "/usr/bin/google-chrome"), ("chrome-macos", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        )
    )
    rows = []
    for runtime_id, path in candidates:
        if path.is_file():
            rows.append({
                "runtime_id": runtime_id, "executable": str(path.resolve()),
                "executable_bytes": path.stat().st_size, "executable_sha256": _sha(path),
            })
    return rows


def _validate_executable(executable: Path) -> Path:
    if not isinstance(executable, Path):
        raise DomainRefusal("PLAY_RUNTIME_EXECUTABLE_REFUSED", type(executable).__name__)
    resolved = executable.resolve()
    if not resolved.is_file() or resolved.is_symlink() or resolved.stat().st_size <= 0:
        raise DomainRefusal("PLAY_RUNTIME_EXECUTABLE_REFUSED", str(resolved))
    return resolved


def _validate_scene_bounds(scene: dict[str, Any], policy: dict[str, Any]) -> None:
    assets = scene["assets"]
    total_asset_bytes = sum(item["bytes"] for item in assets)
    if len(assets) > policy["maximum_scene_assets"] \
            or total_asset_bytes > policy["maximum_scene_asset_bytes"] \
            or not all(item["media_kind"] in policy["allowed_asset_media_kinds"] for item in assets):
        raise DomainRefusal("PLAY_RUNTIME_ASSET_POLICY_REFUSED")
    if not all(item["type"] in policy["allowed_action_types"] for item in scene["actions"]):
        raise DomainRefusal("PLAY_RUNTIME_INPUT_POLICY_REFUSED")


class _RuntimeDOMProbe(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.attributes: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "html" and not self.attributes:
            self.attributes = {key: value or "" for key, value in attrs}


def _inspect_runtime_dom(data: bytes, expected_root: str) -> dict[str, Any]:
    if len(data) == 0:
        raise DomainRefusal("PLAY_RUNTIME_DOM_REFUSED", "EMPTY")
    try:
        document = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DomainRefusal("PLAY_RUNTIME_DOM_REFUSED", "ENCODING") from exc
    probe = _RuntimeDOMProbe()
    probe.feed(document)
    runtime = probe.attributes.get("data-mosaic-runtime", "")
    version_match = _VERSION.search(runtime)
    value = {
        "ready": probe.attributes.get("data-mosaic-ready") == "true",
        "semantic_state_root": probe.attributes.get("data-mosaic-semantic-root"),
        "canvas_fnv": probe.attributes.get("data-mosaic-canvas-fnv"),
        "runtime_user_agent": runtime,
        "runtime_version": version_match.group("version") if version_match else None,
        "runtime_major_version": int(version_match.group("version").split(".")[0]) if version_match else None,
        "semantic_root_matches": probe.attributes.get("data-mosaic-semantic-root") == expected_root,
    }
    if not value["ready"] or not value["semantic_root_matches"] \
            or not re.fullmatch(r"[0-9a-f]{8}", value["canvas_fnv"] or "") \
            or value["runtime_version"] is None:
        raise DomainRefusal("PLAY_RUNTIME_DOM_REFUSED", "EXECUTED_MARKERS")
    return value


def _invoke(
    executable: Path, arguments: list[str], stdout_path: Path, stderr_path: Path, timeout: int,
) -> dict[str, Any]:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    started = time.perf_counter_ns()
    try:
        with stdout_path.open("wb") as output_handle, stderr_path.open("wb") as error_handle:
            run = subprocess.run(
                [str(executable), *arguments], stdout=output_handle, stderr=error_handle,
                timeout=timeout, creationflags=flags, check=False,
            )
    except subprocess.TimeoutExpired as exc:
        raise DomainRefusal("PLAY_RUNTIME_TIMEOUT_REFUSED", str(timeout)) from exc
    duration_ms = (time.perf_counter_ns() - started) // 1_000_000
    return {
        "exit_code": run.returncode, "duration_ms": duration_ms,
        "stdout_bytes": stdout_path.stat().st_size, "stderr_bytes": stderr_path.stat().st_size,
    }


def _common_runtime_flags(profile: Path) -> list[str]:
    return [
        "--headless", "--disable-gpu", "--disable-background-networking",
        "--disable-component-update", "--disable-default-apps", "--disable-domain-reliability",
        "--disable-sync", "--metrics-recording-only", "--no-first-run",
        "--no-default-browser-check", "--hide-scrollbars", "--force-device-scale-factor=1",
        "--host-resolver-rules=MAP * 0.0.0.0", f"--user-data-dir={profile}",
    ]


class InstalledChromiumPlayAdapter(GovernedAdapterSession):
    manifest = AdapterManifest(
        "INSTALLED_CHROMIUM_CANVAS_2D", "PLAY_2D", "EXPLICIT_CHROMIUM_EXECUTABLE_HEADLESS",
        ("HTML", "EXECUTED_DOM", "PNG_SCREENSHOT"),
        ("PLAY_SCENE", "SEMANTIC_STATE", "CANVAS_2D", "INSTALLED_RUNTIME_IDENTITY", "BOUNDED_ARTIFACT"),
        ("EXPLICIT_INSTALLED_CHROMIUM_RUNTIME",),
        ("WRITE_BOUNDED_ARTIFACTS", "EXECUTE_EXPLICIT_LOCAL_RUNTIME"),
    )

    def __init__(self, executable: Path, policy: dict[str, Any], artifact_prefix: str) -> None:
        self.executable = _validate_executable(executable)
        canonical_policy = play_runtime_policy()
        self.policy = canonical_policy if policy is None else copy.deepcopy(policy)
        if self.policy != canonical_policy:
            raise DomainRefusal("PLAY_RUNTIME_POLICY_REFUSED")
        if not re.fullmatch(r"run-[12]", artifact_prefix):
            raise DomainRefusal("PLAY_RUNTIME_ARTIFACT_PREFIX_REFUSED", artifact_prefix)
        self.artifact_prefix = artifact_prefix
        super().__init__()

    def open(self, scene: dict[str, Any]) -> dict[str, Any]:
        opened = super().open(scene)
        _validate_scene_bounds(self.scene, self.policy)
        return opened

    def _project(self, snapshot: dict[str, Any], output_root: Path) -> dict[str, Any]:
        width, height = self.policy["viewport"]
        output_root.mkdir(parents=True, exist_ok=False)
        document = build_canvas_document(self.scene, snapshot)
        if len(document) > self.policy["maximum_artifact_bytes"]["HTML"] \
                or b"http://" in document or b"https://" in document:
            raise DomainRefusal("PLAY_RUNTIME_HTML_POLICY_REFUSED")
        document_path = output_root / "play-runtime.html"
        dom_path = output_root / "play-runtime-dom.html"
        screenshot_path = output_root / "play-runtime.png"
        atomic_write(document_path, document)
        profile_root = Path(tempfile.mkdtemp(prefix=".chromium-profile-", dir=output_root))
        try:
            dom_stdout, dom_stderr = output_root / ".dom.stdout", output_root / ".dom.stderr"
            dom_process = _invoke(
                self.executable,
                [*_common_runtime_flags(profile_root / "dom"), "--virtual-time-budget=1000",
                 "--dump-dom", document_path.as_uri()],
                dom_stdout, dom_stderr, self.policy["process_timeout_seconds"],
            )
            shot_stdout, shot_stderr = output_root / ".shot.stdout", output_root / ".shot.stderr"
            screenshot_process = _invoke(
                self.executable,
                [*_common_runtime_flags(profile_root / "shot"), "--virtual-time-budget=1000",
                 f"--window-size={width},{height}", f"--screenshot={screenshot_path}",
                 document_path.as_uri()],
                shot_stdout, shot_stderr, self.policy["process_timeout_seconds"],
            )
            if dom_process["exit_code"] != 0 or screenshot_process["exit_code"] != 0:
                raise DomainRefusal(
                    "PLAY_RUNTIME_PROCESS_REFUSED",
                    f"DOM={dom_process['exit_code']}:SCREENSHOT={screenshot_process['exit_code']}",
                )
            dom_data = dom_stdout.read_bytes()
            atomic_write(dom_path, dom_data)
            if not screenshot_path.is_file():
                raise DomainRefusal("PLAY_RUNTIME_SCREENSHOT_REFUSED", "ABSENT")
            screenshot = screenshot_path.read_bytes()
            if len(dom_data) > self.policy["maximum_artifact_bytes"]["DOM"] \
                    or len(screenshot) > self.policy["maximum_artifact_bytes"]["PNG"]:
                raise DomainRefusal("PLAY_RUNTIME_ARTIFACT_BUDGET_REFUSED")
            dom = _inspect_runtime_dom(dom_data, snapshot["semantic_state_root"])
            try:
                image_width, image_height, pixels = _png_rgb(screenshot_path)
            except (OSError, ValueError, VisualGateRefusal) as exc:
                raise DomainRefusal("PLAY_RUNTIME_SCREENSHOT_REFUSED", "PNG") from exc
            colors = {pixels[index:index + 3] for index in range(0, len(pixels), 3)}
            if (image_width, image_height) != (width, height) or len(colors) < 4:
                raise DomainRefusal("PLAY_RUNTIME_SCREENSHOT_REFUSED", "CONTENT")
            if dom["runtime_major_version"] < self.policy["minimum_major_version"]:
                raise DomainRefusal("PLAY_RUNTIME_VERSION_REFUSED", str(dom["runtime_version"]))
            observation = play_semantic_observation(self.scene, snapshot)
            result = play_artifact_result(
                self.manifest.adapter_id, "play-runtime.png", screenshot,
                snapshot, observation, "INSTALLED_CHROMIUM_PNG_SCREENSHOT",
            )
            result.update({
                "source_artifact": "play-runtime.html",
                "source_artifact_sha256": hashlib.sha256(document).hexdigest(),
                "executed_dom_artifact": "play-runtime-dom.html",
                "executed_dom_sha256": hashlib.sha256(dom_data).hexdigest(),
                "artifacts": {
                    "screenshot": {"name": "play-runtime.png", "bytes": len(screenshot),
                                   "sha256": hashlib.sha256(screenshot).hexdigest()},
                    "source": {"name": "play-runtime.html", "bytes": len(document),
                               "sha256": hashlib.sha256(document).hexdigest()},
                    "executed_dom": {"name": "play-runtime-dom.html", "bytes": len(dom_data),
                                     "sha256": hashlib.sha256(dom_data).hexdigest()},
                },
                "runtime_identity": {
                    "family": RUNTIME_FAMILY, "executable": str(self.executable),
                    "executable_bytes": self.executable.stat().st_size,
                    "executable_sha256": _sha(self.executable),
                    "observed_user_agent": dom["runtime_user_agent"],
                    "observed_version": dom["runtime_version"],
                },
                "runtime_observation": dom,
                "image": {
                    "width": image_width, "height": image_height,
                    "distinct_color_count": len(colors),
                    "pixel_sha256": hashlib.sha256(pixels).hexdigest(),
                },
                "processes": {"dom": dom_process, "screenshot": screenshot_process},
                "policy_commitment": self.policy["commitment"],
            })
            result["commitment"] = commitment("MOSAIC.PLAY.ADAPTER_ARTIFACT.v0.1", {
                key: value for key, value in result.items() if key != "commitment"
            })
            return result
        finally:
            shutil.rmtree(profile_root, ignore_errors=True)
            for transient in (output_root / ".dom.stdout", output_root / ".dom.stderr",
                              output_root / ".shot.stdout", output_root / ".shot.stderr"):
                transient.unlink(missing_ok=True)


def _negative_controls(policy: dict[str, Any], output_root: Path) -> dict[str, bool]:
    checks = {"UNDECLARED_ACTION_REFUSED": False, "POLICY_DRIFT_REFUSED": False,
              "MISSING_EXECUTABLE_REFUSED": False}
    runner = PlayHeadlessRunner(reference_play_scene())
    try:
        runner.apply({"schema": PLAY_EVENT_SCHEMA, "sequence": 1, "action_id": "undeclared"})
    except DomainRefusal as exc:
        checks["UNDECLARED_ACTION_REFUSED"] = exc.code == "PLAY_ACTION_NOT_DECLARED"
    drift = copy.deepcopy(policy)
    drift["allowed_action_types"] = [*drift["allowed_action_types"], "EXECUTE_HOST"]
    temporary = output_root / ".negative-policy.json"
    atomic_write(temporary, canonical_bytes({key: value for key, value in drift.items() if key != "commitment"}) + b"\n")
    try:
        play_runtime_policy(temporary)
    except DomainRefusal as exc:
        checks["POLICY_DRIFT_REFUSED"] = exc.code == "PLAY_RUNTIME_POLICY_REFUSED"
    finally:
        temporary.unlink(missing_ok=True)
    try:
        _validate_executable(output_root / "absent-runtime")
    except DomainRefusal as exc:
        checks["MISSING_EXECUTABLE_REFUSED"] = exc.code == "PLAY_RUNTIME_EXECUTABLE_REFUSED"
    return checks


def _review_document(witness: dict[str, Any]) -> bytes:
    first = witness["runtime_lifecycles"][0]["projection"]
    inspectors = {
        "Runtime Identity": first["runtime_identity"], "Policy": witness["policy"],
        "Scene": {"scene_commitment": witness["scene_commitment"],
                  "semantic_state_root": witness["semantic_state_root"]},
        "Inputs": witness["events"], "Assets": witness["asset_bounds"],
        "Performance": [item["projection"]["processes"] for item in witness["runtime_lifecycles"]],
        "Evidence": {"checks": witness["checks"], "negative_controls": witness["negative_controls"]},
    }
    details = "".join(
        f"<details{' open' if name == 'Runtime Identity' else ''}><summary>{html.escape(name)}</summary>"
        f"<pre>{html.escape(json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2))}</pre></details>"
        for name, value in inspectors.items()
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Mosaic Play installed runtime qualification</title>
<style>body{{margin:24px;background:#0f141b;color:#e8edf2;font:14px Segoe UI,sans-serif}}main{{max-width:1000px;margin:auto}}img,iframe{{width:100%;aspect-ratio:16/9;border:1px solid #425064;background:#121820}}section{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}details{{border-top:1px solid #303b49;padding:10px 0}}summary{{cursor:pointer;font-weight:600}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;color:#b9c7d5}}code{{font-size:11px}}</style></head>
<body><main><h1>Installed Chromium Play qualification</h1><p>Observed runtime: <code>{html.escape(first['runtime_identity']['observed_version'])}</code></p>
<p>Semantic root: <code>{html.escape(witness['semantic_state_root'])}</code></p><section><article><h2>Executed pixels</h2><img src="run-1/play-runtime.png" alt="Installed Chromium rendering"></article>
<article><h2>Bound source</h2><iframe src="run-1/play-runtime.html" title="Bound Play Canvas source"></iframe></article></section>
<h2>Inspectors</h2>{details}<p>One explicit executable on one host. This is not engine admission, release approval, or broad-host certification.</p></main></body></html>""".encode("utf-8")


def play_runtime_qualification_witness(executable: Path, output_root: Path) -> dict[str, Any]:
    executable = _validate_executable(executable)
    policy = play_runtime_policy()
    output = output_root.resolve()
    if output.exists():
        raise DomainRefusal("PLAY_RUNTIME_OUTPUT_REFUSED", str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    atomic_write(output / "play-runtime-policy.json", canonical_bytes(policy) + b"\n")
    scene = reference_play_scene()
    runner = PlayHeadlessRunner(scene)
    events = [
        {"schema": PLAY_EVENT_SCHEMA, "sequence": 1, "action_id": "move.right"},
        {"schema": PLAY_EVENT_SCHEMA, "sequence": 2, "action_id": "select.player"},
        {"schema": PLAY_EVENT_SCHEMA, "sequence": 3, "action_id": "save"},
    ]
    transitions = [runner.apply(event) for event in events]
    snapshot = runner.snapshot()
    before_sha = _sha(executable)
    lifecycles = [
        adapter_lifecycle_witness(
            InstalledChromiumPlayAdapter(executable, policy, f"run-{index}"),
            runner.scene, snapshot, output / f"run-{index}",
        )
        for index in range(1, policy["process_runs"] + 1)
    ]
    after_sha = _sha(executable)
    projections = [item["projection"] for item in lifecycles]
    negative = _negative_controls(policy, output)
    identities = [item["runtime_identity"] for item in projections]
    checks = {
        "EXPLICIT_EXECUTABLE_STABLE": before_sha == after_sha == identities[0]["executable_sha256"],
        "TWO_ISOLATED_RUNTIME_RUNS": len(lifecycles) == 2 and all(
            item["disposition"] == "PASS_LOCAL_CANDIDATE" for item in lifecycles),
        "RUNTIME_IDENTITY_STABLE": identities[0] == identities[1],
        "SEMANTIC_STATE_BOUND": all(
            item["semantic_state_root"] == snapshot["semantic_state_root"] for item in projections),
        "EXECUTED_DOM_REPEATABLE": projections[0]["executed_dom_sha256"] == projections[1]["executed_dom_sha256"],
        "SCREENSHOT_PIXELS_REPEATABLE": projections[0]["image"]["pixel_sha256"] == projections[1]["image"]["pixel_sha256"],
        "SCREENSHOT_BYTES_REPEATABLE": projections[0]["artifact_sha256"] == projections[1]["artifact_sha256"],
        "RUNTIME_VERSION_SUPPORTED": all(
            item["runtime_observation"]["runtime_major_version"] >= policy["minimum_major_version"]
            for item in projections),
        "FILE_ONLY_NO_DECLARED_NETWORK_RESOURCES": all(
            item["source_artifact_sha256"] == projections[0]["source_artifact_sha256"] for item in projections),
        "ARTIFACTS_WITHIN_BUDGET": all(
            item["artifact_bytes"] <= policy["maximum_artifact_bytes"]["PNG"] for item in projections),
        "NEGATIVE_CONTROLS_PASS": all(negative.values()),
        "AUTHORITY_NONE": all(item["authority_effect"] == "NONE" for item in lifecycles),
    }
    value = {
        "schema": "mosaic.play.external-runtime-qualification.v0.1",
        "policy": policy, "scene_commitment": runner.scene["scene_commitment"],
        "semantic_state_root": snapshot["semantic_state_root"], "events": events,
        "transitions": transitions, "runtime_lifecycles": lifecycles,
        "asset_bounds": {
            "asset_mode": policy["asset_mode"], "declared_assets": len(runner.scene["assets"]),
            "declared_asset_bytes": sum(item["bytes"] for item in runner.scene["assets"]),
            "runtime_fetches": 0,
        },
        "negative_controls": negative, "checks": checks,
        "disposition": "PASS_LOCAL_CANDIDATE" if all(checks.values()) else "REFUSE",
        "standing": "HOST_SPECIFIC_LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
        "claim_boundary": "ONE_EXPLICIT_INSTALLED_CHROMIUM_EXECUTABLE_ON_ONE_HOST; NO_GAME_ENGINE_ADMISSION_RELEASE_APPROVAL_OR_BROAD_HOST_CERTIFICATION",
    }
    value["commitment"] = commitment("MOSAIC.PLAY.EXTERNAL_RUNTIME_QUALIFICATION.v0.1", value)
    review = _review_document(value)
    atomic_write(output / "play-runtime-review.html", review)
    value["review_surface"] = {
        "artifact": "play-runtime-review.html", "sha256": hashlib.sha256(review).hexdigest(),
    }
    value["commitment"] = commitment("MOSAIC.PLAY.EXTERNAL_RUNTIME_QUALIFICATION.v0.1", {
        key: item for key, item in value.items() if key != "commitment"
    })
    atomic_write(output / "play-runtime-witness.json", canonical_bytes(value) + b"\n")
    return value


__all__ = [
    "InstalledChromiumPlayAdapter", "POLICY_PATH", "POLICY_SCHEMA", "RUNTIME_FAMILY",
    "discover_chromium_runtimes", "play_runtime_policy", "play_runtime_qualification_witness",
]

"""Selected Mosaic Play adapters, candidate matrix, and cross-adapter evidence."""
from __future__ import annotations

import hashlib
import html
import json
import struct
import zlib
from pathlib import Path
from typing import Any

from .adapter_sdk import AdapterManifest, GovernedAdapterSession, adapter_lifecycle_witness
from .canonical import atomic_write, canonical_bytes, commitment, read_json
from .domain_protocol import DomainRefusal, require_exact_mapping
from .play import PLAY_EVENT_SCHEMA, PlayHeadlessRunner, reference_play_scene


CANDIDATE_MATRIX_PATH = Path(__file__).resolve().parent / "source" / "play-adapter-candidates.json"
SCORE_KEYS = {"accessibility", "determinism", "evidence", "isolation", "packaging", "portability"}


def adapter_candidate_matrix(path: Path = CANDIDATE_MATRIX_PATH) -> dict[str, Any]:
    value = read_json(path)
    require_exact_mapping(
        value, {"schema", "hard_requirements", "weights", "score_range", "candidates", "standing",
                "authority_effect"}, "PLAY_ADAPTER_MATRIX_SCHEMA_REFUSED",
    )
    if value["schema"] != "mosaic.play.adapter-candidate-matrix.v0.1" \
            or value["authority_effect"] != "NONE" or set(value["weights"]) != SCORE_KEYS \
            or value["score_range"] != [0, 5]:
        raise DomainRefusal("PLAY_ADAPTER_MATRIX_REFUSED")
    if not isinstance(value["candidates"], list) or len(value["candidates"]) < 2:
        raise DomainRefusal("PLAY_ADAPTER_CANDIDATES_REFUSED")
    rows = []
    identifiers: set[str] = set()
    candidate_keys = {"adapter_id", "available_in_candidate", "canonical_dependency", "dependencies",
                      "scores", "selection_class", "tested_scope"}
    for candidate in value["candidates"]:
        require_exact_mapping(candidate, candidate_keys, "PLAY_ADAPTER_CANDIDATE_SCHEMA_REFUSED")
        adapter_id = candidate["adapter_id"]
        if not isinstance(adapter_id, str) or not adapter_id or adapter_id in identifiers \
                or not isinstance(candidate["available_in_candidate"], bool) \
                or candidate["canonical_dependency"] is not False \
                or not isinstance(candidate["dependencies"], list) \
                or set(candidate["scores"]) != SCORE_KEYS \
                or not all(isinstance(score, int) and 0 <= score <= 5 for score in candidate["scores"].values()):
            raise DomainRefusal("PLAY_ADAPTER_CANDIDATE_REFUSED", str(adapter_id))
        score = sum(candidate["scores"][key] * value["weights"][key] for key in SCORE_KEYS)
        eligible = candidate["available_in_candidate"] and candidate["selection_class"] == "IMPLEMENT_NOW"
        rows.append({**candidate, "weighted_score": score, "eligible": eligible})
        identifiers.add(adapter_id)
    rows.sort(key=lambda item: (-item["weighted_score"], item["adapter_id"]))
    selected = [row["adapter_id"] for row in rows if row["eligible"]][:2]
    if len(selected) != 2:
        raise DomainRefusal("PLAY_ADAPTER_SELECTION_REFUSED", repr(selected))
    result = {
        "schema": "mosaic.play.adapter-selection.v0.1",
        "source_schema": value["schema"], "hard_requirements": value["hard_requirements"],
        "weights": value["weights"], "candidates": rows, "selected": selected,
        "selection_basis": "TOP_TWO_AVAILABLE_IMPLEMENT_NOW_WEIGHTED_CANDIDATES",
        "selection_effect": "BOUNDED_EXPERIMENT_ONLY",
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
        "claim_boundary": "SELECTION_DOES_NOT_ADMIT_OR_ENDORSE_A_PRODUCTION_ENGINE",
    }
    result["commitment"] = commitment("MOSAIC.PLAY.ADAPTER_SELECTION.v0.1", result)
    return result


def play_semantic_observation(scene: dict[str, Any], snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    definitions = {item["entity_id"]: item for item in scene["entities"]}
    return [
        {
            "entity_id": entity_id, "kind": definitions[entity_id]["kind"],
            "position": state["position"], "size": definitions[entity_id]["size"],
            "visible": state["visible"],
            "selected": snapshot["state"]["selected_entity_id"] == entity_id,
            "accessible_name": definitions[entity_id]["accessibility"]["name"],
        }
        for entity_id, state in sorted(snapshot["state"]["entities"].items())
    ]


def play_artifact_result(
    adapter_id: str, artifact_name: str, data: bytes, snapshot: dict[str, Any],
    observation: list[dict[str, Any]], artifact_kind: str,
) -> dict[str, Any]:
    value = {
        "schema": "mosaic.play.adapter-artifact.v0.1", "adapter_id": adapter_id,
        "artifact": artifact_name, "artifact_kind": artifact_kind,
        "artifact_sha256": hashlib.sha256(data).hexdigest(), "artifact_bytes": len(data),
        "semantic_state_root": snapshot["semantic_state_root"],
        "semantic_observation": observation, "disposition": "PASS_LOCAL_CANDIDATE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
    }
    value["commitment"] = commitment("MOSAIC.PLAY.ADAPTER_ARTIFACT.v0.1", value)
    return value


def build_canvas_document(scene: dict[str, Any], snapshot: dict[str, Any]) -> bytes:
    """Build the standalone Canvas artifact shared by local and installed-runtime adapters."""
    observation = play_semantic_observation(scene, snapshot)
    payload = json.dumps({
        "bounds": scene["bounds"], "entities": observation,
        "semantic_state_root": snapshot["semantic_state_root"],
    }, ensure_ascii=True, sort_keys=True, separators=(",", ":")).replace("<", "\\u003c")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Mosaic Play Canvas Adapter</title>
<style>html,body{{margin:0;background:#121820;color:#e8edf2;font:14px sans-serif}}canvas{{display:block;width:640px;height:360px}}#a11y{{position:absolute;left:-10000px}}</style></head>
<body><canvas id="scene" width="320" height="180" aria-label="Mosaic Play reference scene"></canvas><ul id="a11y"></ul>
<script>const model={payload};const c=document.getElementById('scene'),x=c.getContext('2d');
x.fillStyle='#121820';x.fillRect(0,0,c.width,c.height);const sx=c.width/model.bounds[0],sy=c.height/model.bounds[1];
for(const e of model.entities){{if(!e.visible)continue;x.fillStyle=e.kind==='HUD'?'#374151':'#2f81f7';x.fillRect(Math.floor(e.position[0]*sx),Math.floor(e.position[1]*sy),Math.max(1,Math.floor(e.size[0]*sx)),Math.max(1,Math.floor(e.size[1]*sy)));if(e.selected){{x.strokeStyle='#f0c75e';x.lineWidth=2;x.strokeRect(Math.floor(e.position[0]*sx),Math.floor(e.position[1]*sy),Math.max(1,Math.floor(e.size[0]*sx)),Math.max(1,Math.floor(e.size[1]*sy)));}}const li=document.createElement('li');li.textContent=e.accessible_name;document.getElementById('a11y').appendChild(li);}}
const pixels=x.getImageData(0,0,c.width,c.height).data;let pixelRoot=2166136261;for(const value of pixels){{pixelRoot=Math.imul((pixelRoot^value)>>>0,16777619)>>>0;}}
document.documentElement.dataset.mosaicReady='true';document.documentElement.dataset.mosaicSemanticRoot=model.semantic_state_root;document.documentElement.dataset.mosaicCanvasFnv=pixelRoot.toString(16).padStart(8,'0');document.documentElement.dataset.mosaicRuntime=navigator.userAgent;
window.__mosaicObservation=model;</script></body></html>
""".encode("utf-8")


class BrowserCanvasPlayAdapter(GovernedAdapterSession):
    manifest = AdapterManifest(
        "BROWSER_CANVAS_2D", "PLAY_2D", "HTML_CANVAS_2D_STANDARD",
        ("HTML", "CANVAS_2D"),
        ("PLAY_SCENE", "SEMANTIC_STATE", "ACCESSIBILITY", "DRAW_COMMANDS", "BOUNDED_ARTIFACT"),
    )

    def _project(self, snapshot: dict[str, Any], output_root: Path) -> dict[str, Any]:
        observation = play_semantic_observation(self.scene, snapshot)
        document = build_canvas_document(self.scene, snapshot)
        output_root.mkdir(parents=True, exist_ok=True)
        atomic_write(output_root / "play-canvas.html", document)
        return play_artifact_result(
            self.manifest.adapter_id, "play-canvas.html", document, snapshot, observation, "HTML_CANVAS_2D",
        )


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def _encode_png(width: int, height: int, rgb: bytes) -> bytes:
    if len(rgb) != width * height * 3:
        raise DomainRefusal("PLAY_RASTER_BUFFER_REFUSED")
    rows = b"".join(b"\x00" + rgb[y * width * 3:(y + 1) * width * 3] for y in range(height))
    return (b"\x89PNG\r\n\x1a\n"
            + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + _png_chunk(b"IDAT", zlib.compress(rows, 9)) + _png_chunk(b"IEND", b""))


def inspect_adapter_png(data: bytes) -> dict[str, Any]:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise DomainRefusal("PLAY_ADAPTER_PNG_REFUSED", "SIGNATURE")
    offset, width, height, compressed = 8, 0, 0, bytearray()
    while offset + 12 <= len(data):
        size = struct.unpack(">I", data[offset:offset + 4])[0]
        kind, body = data[offset + 4:offset + 8], data[offset + 8:offset + 8 + size]
        crc = struct.unpack(">I", data[offset + 8 + size:offset + 12 + size])[0]
        if zlib.crc32(kind + body) & 0xFFFFFFFF != crc:
            raise DomainRefusal("PLAY_ADAPTER_PNG_REFUSED", "CRC")
        if kind == b"IHDR":
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", body)
            if (depth, color, compression, filtering, interlace) != (8, 2, 0, 0, 0):
                raise DomainRefusal("PLAY_ADAPTER_PNG_REFUSED", "FORMAT")
        elif kind == b"IDAT":
            compressed.extend(body)
        elif kind == b"IEND":
            break
        offset += size + 12
    raw = zlib.decompress(bytes(compressed))
    if width <= 0 or height <= 0 or len(raw) != (width * 3 + 1) * height \
            or any(raw[y * (width * 3 + 1)] != 0 for y in range(height)):
        raise DomainRefusal("PLAY_ADAPTER_PNG_REFUSED", "PAYLOAD")
    pixels = b"".join(raw[y * (width * 3 + 1) + 1:(y + 1) * (width * 3 + 1)] for y in range(height))
    return {"width": width, "height": height, "pixel_sha256": hashlib.sha256(pixels).hexdigest()}


class SoftwareRasterPlayAdapter(GovernedAdapterSession):
    manifest = AdapterManifest(
        "SOFTWARE_RASTER_PNG", "PLAY_2D", "PYTHON_STDLIB_RGB_RASTER",
        ("RGB_BUFFER", "PNG"),
        ("PLAY_SCENE", "SEMANTIC_STATE", "DETERMINISTIC_PIXELS", "BOUNDED_ARTIFACT"),
    )

    def _project(self, snapshot: dict[str, Any], output_root: Path) -> dict[str, Any]:
        width, height = 320, 180
        pixels = bytearray((18, 24, 32) * (width * height))
        observation = play_semantic_observation(self.scene, snapshot)
        scene_width, scene_height = self.scene["bounds"]

        def rectangle(x: int, y: int, w: int, h: int, color: tuple[int, int, int]) -> None:
            for row in range(max(0, y), min(height, y + h)):
                for column in range(max(0, x), min(width, x + w)):
                    start = (row * width + column) * 3
                    pixels[start:start + 3] = bytes(color)

        for item in observation:
            if not item["visible"]:
                continue
            x = item["position"][0] * width // scene_width
            y = item["position"][1] * height // scene_height
            w = max(1, item["size"][0] * width // scene_width)
            h = max(1, item["size"][1] * height // scene_height)
            rectangle(x, y, w, h, (55, 65, 81) if item["kind"] == "HUD" else (47, 129, 247))
            if item["selected"]:
                rectangle(x, y, w, 1, (240, 199, 94))
                rectangle(x, y + h - 1, w, 1, (240, 199, 94))
                rectangle(x, y, 1, h, (240, 199, 94))
                rectangle(x + w - 1, y, 1, h, (240, 199, 94))
        data = _encode_png(width, height, bytes(pixels))
        inspected = inspect_adapter_png(data)
        output_root.mkdir(parents=True, exist_ok=True)
        atomic_write(output_root / "play-raster.png", data)
        result = play_artifact_result(
            self.manifest.adapter_id, "play-raster.png", data, snapshot, observation, "PNG_RGB",
        )
        result["raster"] = inspected
        result["commitment"] = commitment("MOSAIC.PLAY.ADAPTER_ARTIFACT.v0.1", {
            key: value for key, value in result.items() if key != "commitment"
        })
        return result


def _review_document(
    matrix: dict[str, Any], scene: dict[str, Any], snapshot: dict[str, Any],
    transitions: list[dict[str, Any]], projections: list[dict[str, Any]],
) -> bytes:
    selected = ", ".join(matrix["selected"])
    semantic_root = snapshot["semantic_state_root"]
    rows = "".join(
        f"<tr><td>{html.escape(item['adapter_id'])}</td><td>{html.escape(item['artifact_kind'])}</td>"
        f"<td><code>{item['artifact_sha256']}</code></td></tr>" for item in projections
    )
    inspectors = {
        "Scene": {"scene_id": scene["scene_id"], "units": scene["units"], "bounds": scene["bounds"]},
        "Entities": scene["entities"], "Inputs": scene["actions"], "Transitions": transitions,
        "Assets": scene["assets"], "Budgets": scene["budgets"],
        "Evidence": {"matrix_commitment": matrix["commitment"], "semantic_state_root": semantic_root,
                     "projections": projections},
    }
    inspector_html = "".join(
        f"<details{' open' if name == 'Scene' else ''}><summary>{name}</summary>"
        f"<pre>{html.escape(json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2))}</pre></details>"
        for name, payload in inspectors.items()
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Mosaic Play Adapter Review</title>
<style>body{{margin:24px;background:#0f141b;color:#e8edf2;font:14px Segoe UI,sans-serif}}main{{max-width:1100px;margin:auto}}section{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}iframe,img{{width:100%;aspect-ratio:16/9;border:1px solid #425064;background:#121820}}table{{width:100%;border-collapse:collapse}}td,th{{padding:8px;border-bottom:1px solid #303b49;text-align:left}}code{{font-size:11px}}details{{border-top:1px solid #303b49;padding:10px 0}}summary{{cursor:pointer;font-weight:600}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;color:#b9c7d5}}</style></head>
<body><main><h1>Mosaic Play adapter review</h1><p>Selected experiments: {html.escape(selected)}</p>
<p>Shared semantic state: <code>{semantic_root}</code></p><section><article><h2>Browser Canvas</h2><iframe src="play-canvas.html" title="Canvas realization"></iframe></article>
<article><h2>Software raster</h2><img src="play-raster.png" alt="Software raster realization"></article></section>
<h2>Evidence</h2><table><thead><tr><th>Adapter</th><th>Artifact</th><th>SHA-256</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Inspectors</h2>{inspector_html}
<p>Local candidate comparison only. No production engine, broad-host behavior, or visual equivalence is certified.</p></main></body></html>""".encode("utf-8")


def play_adapter_witness(output_root: Path) -> dict[str, Any]:
    matrix = adapter_candidate_matrix()
    scene = reference_play_scene()
    runner = PlayHeadlessRunner(scene)
    events = (
        {"schema": PLAY_EVENT_SCHEMA, "sequence": 1, "action_id": "move.right"},
        {"schema": PLAY_EVENT_SCHEMA, "sequence": 2, "action_id": "select.player"},
        {"schema": PLAY_EVENT_SCHEMA, "sequence": 3, "action_id": "save"},
    )
    transitions = [runner.apply(event) for event in events]
    snapshot = runner.snapshot()
    adapters = (BrowserCanvasPlayAdapter(), SoftwareRasterPlayAdapter())
    if set(matrix["selected"]) != {adapter.manifest.adapter_id for adapter in adapters}:
        raise DomainRefusal("PLAY_ADAPTER_IMPLEMENTATION_SELECTION_DRIFT")
    output = output_root.resolve()
    output.mkdir(parents=True, exist_ok=True)
    atomic_write(output / "play-adapter-matrix.json", canonical_bytes(matrix) + b"\n")
    lifecycles = [adapter_lifecycle_witness(adapter, runner.scene, snapshot, output) for adapter in adapters]
    projections = [item["projection"] for item in lifecycles]
    observations = [item["semantic_observation"] for item in projections]
    review = _review_document(matrix, runner.scene, snapshot, transitions, projections)
    atomic_write(output / "play-adapter-review.html", review)
    checks = {
        "MATRIX_SELECTED_TWO": len(matrix["selected"]) == 2,
        "TWO_RUNTIME_BINDINGS": len({item["adapter"]["runtime_binding"] for item in lifecycles}) == 2,
        "LIFECYCLES_PASS": all(item["disposition"] == "PASS_LOCAL_CANDIDATE" for item in lifecycles),
        "SEMANTIC_OBSERVATIONS_EQUAL": observations[0] == observations[1],
        "SEMANTIC_ROOTS_EQUAL": len({item["semantic_state_root"] for item in projections}) == 1,
        "ARTIFACT_KINDS_DIFFER": len({item["artifact_kind"] for item in projections}) == 2,
        "REVIEW_SURFACE_PRESENT": b"play-canvas.html" in review and b"play-raster.png" in review,
        "CANONICAL_DEPENDENCY_ABSENT": all(item["adapter"]["canonical_dependency"] is False for item in lifecycles),
    }
    value = {
        "schema": "mosaic.play.adapter-readiness-witness.v0.1", "matrix": matrix,
        "scene_commitment": runner.scene["scene_commitment"], "events": list(events),
        "transitions": transitions, "snapshot": snapshot, "adapter_lifecycles": lifecycles,
        "review_surface": {"artifact": "play-adapter-review.html", "sha256": hashlib.sha256(review).hexdigest()},
        "checks": checks, "disposition": "PASS_LOCAL_CANDIDATE" if all(checks.values()) else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
        "claim_boundary": "TWO_REAL_ARTIFACT_ADAPTERS_TESTED_LOCALLY_WITHOUT_ENGINE_ADMISSION_OR_BROAD_HOST_CERTIFICATION",
    }
    value["commitment"] = commitment("MOSAIC.PLAY.ADAPTER_READINESS_WITNESS.v0.1", value)
    atomic_write(output / "play-adapter-witness.json", canonical_bytes(value) + b"\n")
    return value


__all__ = [
    "BrowserCanvasPlayAdapter", "CANDIDATE_MATRIX_PATH", "SoftwareRasterPlayAdapter",
    "adapter_candidate_matrix", "build_canvas_document", "inspect_adapter_png",
    "play_adapter_witness", "play_artifact_result", "play_semantic_observation",
]

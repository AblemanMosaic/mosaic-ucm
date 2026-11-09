"""Governed semantic/DOM golden matrix for Mosaic UI visual certification."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .canonical import atomic_write, canonical_bytes, commitment, read_json
from .realizer import create_realizer
from .signature_profile import build_signature_payload
from .visual_gate import _png_rgb


MATRIX_SCHEMA = "mosaic.ui.visual-certification-matrix.v0.1"
BASELINE_PATH = Path(__file__).resolve().parent / "source" / "visual-baseline.json"
THEMES = ("signature-light", "signature-dark", "high-contrast-dark")
DENSITIES = ("comfortable", "compact")
COMPOSITIONS = ("operational-dashboard", "data-workspace", "settings-workflow")
VIEWPORTS = ((1280, 800), (640, 600))
STATES = ("IDLE", "FOCUSED", "SELECTED", "DISABLED", "REFUSED")
REALIZERS = ("HEADLESS", "BROWSER")


def _case_payload(composition_id: str, theme_id: str, density_id: str, state: str) -> tuple[dict[str, Any], str, str]:
    payload = build_signature_payload(composition_id, theme_id, density_id)
    targets = {
        "operational-dashboard": ("ops.services", "Win32"),
        "data-workspace": ("data.collections", "releases"),
        "settings-workflow": ("settings.theme", "light"),
    }
    node_id, selected = targets[composition_id]
    if state in {"DISABLED", "REFUSED"}:
        target = next(item for item in _walk(payload["application"]["tree"]) if item["node_id"] == node_id)
        target["props"]["default_state"] = state
    return payload, node_id, selected


def _walk(node: dict[str, Any]):
    yield node
    for child in node.get("children", []):
        yield from _walk(child)


def build_matrix(output: Path | None = None) -> dict[str, Any]:
    rows = []
    if output is not None:
        output.mkdir(parents=True, exist_ok=True)
    for realizer_id in REALIZERS:
        for composition_id in COMPOSITIONS:
            for theme_id in THEMES:
                for density_id in DENSITIES:
                    for width, height in VIEWPORTS:
                        for state in STATES:
                            payload, target_id, selected = _case_payload(composition_id, theme_id, density_id, state)
                            realizer = create_realizer(realizer_id, payload)
                            try:
                                if state == "FOCUSED":
                                    realizer.apply({"intent": "FOCUS", "node_id": target_id})
                                elif state == "SELECTED":
                                    realizer.apply({"intent": "SELECT", "node_id": target_id, "value": selected})
                                projection = realizer.project(width, height)
                                if projection["gates"]["disposition"] != "PASS":
                                    raise ValueError(f"VISUAL_MATRIX_GATE_REFUSED:{realizer_id}:{composition_id}:{theme_id}:{density_id}:{width}x{height}:{state}")
                                data = canonical_bytes(projection) + b"\n"
                                artifact = f"{realizer_id.lower()}-{composition_id}-{theme_id}-{density_id}-{width}x{height}-{state.lower()}.json"
                                if output is not None:
                                    atomic_write(output / artifact, data)
                                    if realizer_id == "BROWSER":
                                        document = realizer.document(width, height)
                                        atomic_write(output / artifact.replace(".json", ".html"), document.encode("utf-8"))
                                rows.append({
                                    "realizer": realizer_id, "composition": composition_id, "theme": theme_id,
                                    "density": density_id, "viewport": {"width": width, "height": height},
                                    "state": state, "artifact": artifact, "sha256": hashlib.sha256(data).hexdigest(),
                                    "gate_commitment": projection["gates"]["commitment"],
                                })
                            finally:
                                realizer.close()
    value = {
        "schema": MATRIX_SCHEMA,
        "case_count": len(rows), "realizers": list(REALIZERS), "compositions": list(COMPOSITIONS),
        "themes": list(THEMES), "densities": list(DENSITIES),
        "viewports": [{"width": width, "height": height} for width, height in VIEWPORTS],
        "states": list(STATES), "cases": rows,
        "determinism_basis": "CANONICAL_PROJECTION_AND_SEMANTIC_DOM_NO_HOST_MEASUREMENT",
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
        "claim_boundary": "SEMANTIC_AND_DOM_GOLDENS_DO_NOT_ESTABLISH_BROWSER_PIXEL_OR_ASSISTIVE_TECHNOLOGY_EQUIVALENCE",
    }
    value["matrix_root"] = commitment("MOSAIC.UI.VISUAL_CERTIFICATION_MATRIX.v0.1", value)
    if output is not None:
        atomic_write(output / "visual-certification-matrix.json", canonical_bytes(value) + b"\n")
    return value


def record_baseline(path: Path = BASELINE_PATH) -> dict[str, Any]:
    matrix = build_matrix()
    baseline = {
        "schema": "mosaic.ui.visual-baseline.v0.1", "matrix_schema": MATRIX_SCHEMA,
        "matrix_root": matrix["matrix_root"], "case_count": matrix["case_count"],
        "cases": matrix["cases"], "standing": "LOCAL_CANDIDATE_BASELINE",
        "authority_effect": "NONE",
        "claim_boundary": "BASELINE_RECORDING_IS_NOT_RELEASE_APPROVAL_OR_CONSTITUTIONAL_ADMISSION",
    }
    baseline["commitment"] = commitment("MOSAIC.UI.VISUAL_BASELINE.v0.1", baseline)
    atomic_write(path, canonical_bytes(baseline) + b"\n")
    return baseline


def verify_baseline(path: Path = BASELINE_PATH) -> dict[str, Any]:
    expected = read_json(path)
    body = dict(expected)
    observed_commitment = body.pop("commitment", None)
    if observed_commitment != commitment("MOSAIC.UI.VISUAL_BASELINE.v0.1", body):
        raise ValueError("VISUAL_BASELINE_COMMITMENT_REFUSED")
    observed = build_matrix()
    passed = expected.get("matrix_root") == observed["matrix_root"] and expected.get("cases") == observed["cases"]
    value = {
        "schema": "mosaic.ui.visual-baseline-verification.v0.1",
        "expected_matrix_root": expected.get("matrix_root"), "observed_matrix_root": observed["matrix_root"],
        "case_count": observed["case_count"], "disposition": "PASS_LOCAL_CANDIDATE" if passed else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
    }
    value["commitment"] = commitment("MOSAIC.UI.VISUAL_BASELINE_VERIFICATION.v0.1", value)
    return value


def pixel_witness(captures: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for capture in captures:
        path = Path(str(capture["path"])).resolve()
        width, height, media_type = _image_dimensions(path)
        expected_width, expected_height = int(capture["width"]), int(capture["height"])
        if (width, height) != (expected_width, expected_height):
            raise ValueError(f"PIXEL_CAPTURE_DIMENSION_REFUSED:{path.name}:{width}x{height}")
        rows.append({
            "capture_id": str(capture["capture_id"]), "realizer": str(capture["realizer"]),
            "theme": str(capture["theme"]), "state": str(capture["state"]),
            "viewport": {"width": width, "height": height}, "file": path.name,
            "media_type": media_type,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size,
        })
    rows.sort(key=lambda item: item["capture_id"])
    value = {
        "schema": "mosaic.ui.visual-pixel-witness.v0.1", "captures": rows,
        "capture_count": len(rows), "disposition": "PASS_LOCAL_CANDIDATE" if rows else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
        "claim_boundary": "EXACT_RUN_PIXEL_CAPTURE_DOES_NOT_ESTABLISH CROSS_BROWSER_OR_CROSS_HOST_EQUIVALENCE",
    }
    value["commitment"] = commitment("MOSAIC.UI.VISUAL_PIXEL_WITNESS.v0.1", value)
    return value


def _image_dimensions(path: Path) -> tuple[int, int, str]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        width, height, _ = _png_rgb(path)
        return width, height, "image/png"
    if data.startswith(b"\xff\xd8"):
        offset = 2
        while offset + 9 < len(data):
            if data[offset] != 0xFF:
                offset += 1
                continue
            marker = data[offset + 1]
            offset += 2
            if marker in {0xD8, 0xD9}:
                continue
            if offset + 2 > len(data):
                break
            length = int.from_bytes(data[offset:offset + 2], "big")
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                          0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF} and length >= 7:
                height = int.from_bytes(data[offset + 3:offset + 5], "big")
                width = int.from_bytes(data[offset + 5:offset + 7], "big")
                return width, height, "image/jpeg"
            if length < 2:
                break
            offset += length
    raise ValueError(f"PIXEL_CAPTURE_FORMAT_REFUSED:{path.name}")


__all__ = ["BASELINE_PATH", "build_matrix", "pixel_witness", "record_baseline", "verify_baseline"]

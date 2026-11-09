from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from .canonical import atomic_write, canonical_bytes, commitment, read_json
from .foundry import COMPONENT_KINDS
from .model import STATES, UIRefusal


class BridgeRefusal(UIRefusal):
    pass


def _require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise BridgeRefusal(code, detail)


def _write(path: Path, value: Any) -> None:
    atomic_write(path, canonical_bytes(value) + b"\n")


def _file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _verify_commitment(value: dict[str, Any], field: str, domain: str) -> bool:
    observed = value.get(field)
    body = copy.deepcopy(value)
    body.pop(field, None)
    return isinstance(observed, str) and observed == commitment(domain, body)


def _document_body(document: dict[str, Any]) -> dict[str, Any]:
    body = copy.deepcopy(document)
    body.pop("document_commitment", None)
    body.pop("ephemeral", None)
    return body


def _slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", ".", value.lower()).strip(".")
    return result or "component"


def _component_geometry(document: dict[str, Any]) -> dict[str, int]:
    layers = [layer for layer in document["layers"] if layer.get("primitive") != "REFERENCE_IMAGE" and not layer.get("hidden")]
    root = next((layer for layer in layers if layer.get("semantic", {}).get("role") == "COMPONENT_ROOT"), None)
    if root is not None:
        return {key: int(root["geometry"][key]) for key in ("x", "y", "width", "height")}
    _require(bool(layers), "BUILDER_COMPONENT_GEOMETRY_ABSENT")
    left = min(int(layer["geometry"]["x"]) for layer in layers)
    top = min(int(layer["geometry"]["y"]) for layer in layers)
    right = max(int(layer["geometry"]["x"]) + int(layer["geometry"]["width"]) for layer in layers)
    bottom = max(int(layer["geometry"]["y"]) + int(layer["geometry"]["height"]) for layer in layers)
    return {"x": left, "y": top, "width": right - left, "height": bottom - top}


def _label(document: dict[str, Any], accessible_name: str) -> str:
    for layer in document["layers"]:
        if layer.get("primitive") == "TEXT" and layer.get("text"):
            return str(layer["text"])
    return accessible_name


def _builder_visual(document: dict[str, Any], component: dict[str, int]) -> dict[str, Any]:
    supported = {"RECT", "ROUNDED_RECT", "TEXT", "LINE", "ICON_SLOT"}
    layers = []
    for source in document["layers"]:
        if source.get("primitive") == "REFERENCE_IMAGE" or source.get("hidden"):
            continue
        primitive = str(source.get("primitive") or "")
        _require(primitive in supported, "BUILDER_VISUAL_PRIMITIVE_UNSUPPORTED", primitive)
        geometry = source.get("geometry")
        _require(isinstance(geometry, dict), "BUILDER_LAYER_GEOMETRY_INVALID", str(source.get("layer_id") or ""))
        normalized_geometry = {
            "x": int(geometry["x"]) - component["x"],
            "y": int(geometry["y"]) - component["y"],
            "width": int(geometry["width"]),
            "height": int(geometry["height"]),
        }
        _require(normalized_geometry["width"] >= 0 and normalized_geometry["height"] >= 0,
                 "BUILDER_LAYER_GEOMETRY_INVALID", str(source.get("layer_id") or ""))
        layers.append({
            "layer_id": str(source["layer_id"]),
            "primitive": primitive,
            "geometry": normalized_geometry,
            "style": copy.deepcopy(source.get("style", {})),
            "text": str(source.get("text") or ""),
            "semantic": copy.deepcopy(source.get("semantic", {})),
            "state_overrides": {
                state: copy.deepcopy(source.get("state_overrides", {}).get(state, {}))
                for state in STATES
            },
        })
    _require(bool(layers), "BUILDER_VISUAL_LAYERS_ABSENT")
    value = {
        "schema": "mosaic.ui.builder-vector-visual.v0.1",
        "source_coordinate_space": {
            "origin_x": component["x"], "origin_y": component["y"],
            "width": component["width"], "height": component["height"],
        },
        "states": list(STATES),
        "layers": layers,
        "authority_effect": "NONE",
    }
    value["commitment"] = commitment("MOSAIC.UI.BUILDER_VECTOR_VISUAL.v0.1", value)
    return value


def export_element(document_path: Path, ic_path: Path, output_dir: Path) -> dict[str, Any]:
    document = read_json(document_path)
    ic = read_json(ic_path)
    _require(isinstance(document, dict), "BUILDER_DOCUMENT_INVALID")
    _require(isinstance(ic, dict), "BUILDER_IC_INVALID")
    _require(document.get("schema") == "ui-substrate.element-document.v1", "BUILDER_DOCUMENT_SCHEMA_REFUSED")
    expected_document = commitment("CUIF.T8.ELEMENT_DOCUMENT.v1", _document_body(document))
    _require(document.get("document_commitment") == expected_document, "BUILDER_DOCUMENT_COMMITMENT_REFUSED")
    _require(document.get("states") == list(STATES), "BUILDER_STATE_MODEL_REFUSED")
    _require(document.get("standing") == "PROPOSED_ZERO_STANDING", "BUILDER_DOCUMENT_STANDING_REFUSED")
    _require(document.get("standing_effect") == "NONE" and document.get("authority_effect") == "NONE",
             "BUILDER_DOCUMENT_EFFECT_REFUSED")
    _require(document.get("effects_performed") == [], "BUILDER_DOCUMENT_EFFECT_HISTORY_REFUSED")

    _require(ic.get("schema") == "ableman-razor.instance-constitution.v1", "BUILDER_IC_SCHEMA_REFUSED")
    _require(_verify_commitment(ic, "ic_commitment", "AR.DESCENT.INSTANCE_CONSTITUTION.v1"),
             "BUILDER_IC_COMMITMENT_REFUSED")
    _require(ic.get("ic_level") == "PERSONAL_COMPONENT_LIBRARY", "BUILDER_IC_LEVEL_REFUSED")
    _require(ic.get("standing_effect") == "NONE" and ic.get("authority_effect") == "NONE", "BUILDER_IC_EFFECT_REFUSED")
    binding = ic.get("bindings", {}).get("element_document", {})
    expected_binding = {
        "document_id": document.get("document_id"),
        "document_commitment": document.get("document_commitment"),
        "file_sha256": _file_sha256(document_path),
        "component_type": document.get("component_type"),
    }
    _require(binding == expected_binding, "BUILDER_IC_DOCUMENT_BINDING_REFUSED")
    _require(ic.get("bindings", {}).get("effect_boundary", {}).get("performed_effects") == [],
             "BUILDER_IC_PERFORMED_EFFECT_REFUSED")

    kind = str(document["component_type"])
    _require(kind in COMPONENT_KINDS and kind == "BUTTON", "BUILDER_COMPONENT_KIND_UNSUPPORTED", kind)
    accessible_name = str(ic.get("bindings", {}).get("accessibility_obligations", {}).get("accessible_name") or "")
    _require(bool(accessible_name), "BUILDER_ACCESSIBLE_NAME_ABSENT")
    geometry = _component_geometry(document)
    builder_visual = _builder_visual(document, geometry)
    canvas = document["canvas"]
    width, height = int(canvas["width"]), int(canvas["height"])
    _require(geometry["width"] > 0 and geometry["height"] > 0, "BUILDER_COMPONENT_GEOMETRY_INVALID")
    _require(geometry["x"] >= 0 and geometry["y"] >= 0 and geometry["x"] + geometry["width"] <= width
             and geometry["y"] + geometry["height"] <= height, "BUILDER_COMPONENT_OUT_OF_BOUNDS")

    node_id = f"element.{_slug(document['document_id'])}"
    operation_id = "ELEMENT_ACTIVATE"
    enter_operation = "ENTER_PREVIEW"
    state_refs = {
        state: commitment(
            "MOSAIC.UI.BUILDER_STATE.v0.1",
            [{"layer_id": layer["layer_id"], "override": layer.get("state_overrides", {}).get(state, {})}
             for layer in document["layers"] if layer.get("primitive") != "REFERENCE_IMAGE"],
        )
        for state in STATES
    }
    application = {
        "application_id": f"MOSAIC_BUILDER_PREVIEW::{document['document_id']}",
        "declared_operation_ids": [enter_operation, operation_id],
        "lifecycle": {
            "schema": "mosaic.ui.std.lifecycle-binding.v0.1",
            "initial_view": "preview",
            "operation_controls": {"cancel_key": None, "progress_key": None},
            "operation_classes": {
                "NAVIGATE": [enter_operation],
                "LONG_RUNNING": [],
                "CANCEL": [],
                "TOGGLE_DISCLOSURE": [],
                "HOST_WITHHELD": [operation_id],
            },
            "status_templates": {
                "initial": "Ready",
                "queued": "{operation_phrase} queued",
                "progress": "{stage_phrase} | {percent} | {mm}:{ss}",
                "terminal": "{operation} {terminal} | {message}",
                "cancelled": "{operation} cancelled",
            },
            "progress_default_stage": "working",
        },
        "tree": {
            "kind": "WINDOW",
            "node_id": "preview.window",
            "semantics": {"role": "window", "name": document["title"], "description": "", "focusable": False, "actions": []},
            "props": {"layout_provider": "mosaic.ui.probe-layouts.v0.1", "theme": "dark"},
            "children": [
                {
                    "kind": "PANEL",
                    "node_id": "preview.entry",
                    "semantics": {"role": "group", "name": "Preview", "description": "", "focusable": False, "actions": []},
                    "props": {"target_view": "preview"},
                    "operation_ref": enter_operation,
                    "children": [],
                },
                {
                    "kind": kind,
                    "node_id": node_id,
                    "semantics": {
                        "role": kind.lower().replace("_", ""),
                        "name": accessible_name,
                        "description": "Constituted builder component preview",
                        "focusable": True,
                        "actions": ["activate"],
                    },
                    "props": {
                        "realization_key": node_id,
                        "view": "preview",
                        "display_text": _label(document, accessible_name),
                        "default_state": "IDLE",
                        "builder_document_ref": document["document_commitment"],
                        "builder_ic_ref": ic["ic_commitment"],
                        "builder_state_refs": state_refs,
                        "builder_visual": builder_visual,
                    },
                    "operation_ref": operation_id,
                    "children": [],
                },
            ],
        },
        "builder_bridge": {
            "schema": "mosaic.ui.builder-bridge-binding.v0.1",
            "document_ref": document["document_commitment"],
            "instance_constitution_ref": ic["ic_commitment"],
            "visual_transfer": "NORMALIZED_VECTOR_LAYER_PROJECTION",
            "builder_visual_ref": builder_visual["commitment"],
            "authority_effect": "NONE",
        },
        "authority_effect": "NONE",
    }
    docket = {
        "schema": "mosaic.ui.probe-docket.v0.1",
        "docket_id": f"BUILDER-BRIDGE::{document['document_id']}",
        "scenarios": [{
            "id": "focus_and_request_activation",
            "events": [{"intent": "FOCUS", "node_id": node_id}, {"intent": "ACTIVATE", "node_id": node_id}],
            "expected_refusals": [],
            "viewports": [{"width": width, "height": height}],
            "state_matrix": [{"node_id": node_id, "states": list(STATES)}],
        }],
    }
    layouts = {
        "schema": "mosaic.ui.probe-layouts.v0.1",
        "plans": [{
            "width": width,
            "height": height,
            "rects": {node_id: [geometry["x"], geometry["y"], geometry["width"], geometry["height"]]},
        }],
    }
    receipt = {
        "schema": "mosaic.ui.builder-bridge-receipt.v0.1",
        "document_ref": document["document_commitment"],
        "document_file_sha256": expected_binding["file_sha256"],
        "instance_constitution_ref": ic["ic_commitment"],
        "application_commitment": commitment("MOSAIC.UI.BUILDER_APPLICATION.v0.1", application),
        "docket_commitment": commitment("MOSAIC.UI.PROBE_DOCKET.v0.1", docket),
        "layout_commitment": commitment("MOSAIC.UI.PROBE_LAYOUTS.v0.1", layouts),
        "component_kind": kind,
        "visual_transfer": "NORMALIZED_VECTOR_LAYER_PROJECTION",
        "builder_visual_ref": builder_visual["commitment"],
        "nonclaims": [
            "BUILDER_VECTOR_LAYER_RASTER_PIXEL_IDENTITY_NOT_ESTABLISHED",
            "HOST_DESKTOP_BEHAVIOR_NOT_ESTABLISHED",
            "CONSTITUTIONAL_ADMISSION_NOT_CLAIMED",
        ],
        "standing": "LOCAL_CANDIDATE",
        "standing_effect": "NONE",
        "authority_effect": "NONE",
    }
    receipt["receipt_commitment"] = commitment("MOSAIC.UI.BUILDER_BRIDGE_RECEIPT.v0.1", receipt)
    _write(output_dir / "application.json", application)
    _write(output_dir / "probe-docket.json", docket)
    _write(output_dir / "probe-layouts.json", layouts)
    _write(output_dir / "bridge-receipt.json", receipt)
    return receipt


def export_minimal_runtime(
    document_path: Path,
    ic_path: Path,
    output_dir: Path,
    *,
    library_source: Path,
    realizers: tuple[str, ...] = ("HEADLESS",),
    themes: tuple[str, ...] = (),
    retain_kinds: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Export bridge inputs, compile them, and emit a reviewed minimal-runtime report."""
    from .ablate import build_slice
    from .equivalence import run_equivalence
    from .foundry import compile_library

    bridge_receipt = export_element(document_path, ic_path, output_dir)
    generated = output_dir / "generated"
    compile_library(library_source, generated, output_dir / "application.json")
    slice_result = build_slice(
        generated, output_dir / "minimal-runtime", realizers, themes, retain_kinds,
    )
    equivalence, code = run_equivalence(
        generated, output_dir / "probe-docket.json", output_dir / "probe-layouts.json",
        Path(slice_result["archive_path"]), output_dir / "minimal-runtime-equivalence",
    )
    if code != 0:
        raise BridgeRefusal("MINIMAL_RUNTIME_EQUIVALENCE_REFUSED")
    report = {
        "schema": "mosaic.ui.builder-minimal-runtime-report.v0.1",
        "builder_bridge_receipt": bridge_receipt["receipt_commitment"],
        "profile_root": slice_result["profile_root"],
        "retained_kinds": slice_result["retained_kinds"],
        "removed_kinds": slice_result["removed_kinds"],
        "requested_realizers": slice_result["requested_realizers"],
        "size": {
            "runtime_source_bytes": slice_result["runtime_source_bytes"],
            "installed_payload_bytes": slice_result["installed_payload_bytes"],
            "source_archive_bytes": slice_result["archive_bytes"],
            "wheel_bytes": slice_result["wheel_bytes"],
            "cold_import_source_bytes": slice_result["cold_import"]["source_bytes"],
        },
        "dependency_explanation": "See MOSAIC-UI-ABLATION-MANIFEST.json dependency_reasons",
        "equivalence_receipt": equivalence["receipt_commitment"],
        "disposition": "PASS_LOCAL_CANDIDATE",
        "standing": "LOCAL_CANDIDATE",
        "authority_effect": "NONE",
    }
    report["report_commitment"] = commitment("MOSAIC.UI.BUILDER_MINIMAL_RUNTIME_REPORT.v0.1", report)
    _write(output_dir / "minimal-runtime-report.json", report)
    return report


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export a constituted UI Element Composer document to Mosaic UI probe inputs.")
    parser.add_argument("--document", type=Path, required=True)
    parser.add_argument("--ic", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimal-runtime", action="store_true")
    parser.add_argument("--library-source", type=Path, default=Path(__file__).resolve().parent / "source")
    parser.add_argument("--realizer", action="append", choices=("HEADLESS", "WIN32"))
    parser.add_argument("--theme", action="append", default=[])
    parser.add_argument("--retain-kind", action="append", default=[])
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if args.minimal_runtime:
            result = export_minimal_runtime(
                args.document.resolve(), args.ic.resolve(), args.output.resolve(),
                library_source=args.library_source.resolve(),
                realizers=tuple(args.realizer or ["HEADLESS"]), themes=tuple(args.theme),
                retain_kinds=tuple(args.retain_kind),
            )
        else:
            result = export_element(args.document.resolve(), args.ic.resolve(), args.output.resolve())
        print(json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2))
        return 0
    except (BridgeRefusal, UIRefusal, OSError, ValueError, json.JSONDecodeError) as exc:
        value = {
            "schema": "mosaic.ui.builder-bridge-refusal.v0.1",
            "disposition": "REFUSE",
            "refusal_code": getattr(exc, "code", "BUILDER_BRIDGE_INPUT_OR_IO_REFUSED"),
            "detail": getattr(exc, "detail", str(exc)),
            "effects_performed": [],
            "standing_effect": "NONE",
            "authority_effect": "NONE",
        }
        print(json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2))
        return 32


if __name__ == "__main__":
    raise SystemExit(main())

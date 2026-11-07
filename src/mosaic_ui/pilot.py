"""Mosaic Release Console: an end-to-end pilot application for the UI toolchain."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .canonical import commitment, read_json
from .foundry import validate_component_library
from .model import node, validate_tree
from .runtime import GovernedRuntime, OperationContext, OperationResult, OperationSpec, RuntimePolicy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(__file__).resolve().parent / "source"


def _item(
    kind: str,
    node_id: str,
    name: str,
    *,
    operation: str | None = None,
    focusable: bool = False,
    props: dict[str, Any] | None = None,
    children: tuple[Any, ...] = (),
    role: str | None = None,
) -> Any:
    return node(
        kind, node_id, name, role=role, operation_ref=operation, focusable=focusable,
        props=props or {}, children=children,
    )


def pilot_application() -> dict[str, Any]:
    title = _item("LABEL", "release.title", "Mosaic Release Console", role="heading", props={
        "realization_key": "release.title", "display_text": "Mosaic Release Console",
        "layout_item": {"grow": 1},
    })
    posture = _item("BADGE", "release.posture", "Local candidate", role="status", props={
        "realization_key": "release.posture", "default": "LOCAL_CANDIDATE",
        "layout_item": {"width": 180},
    })
    header = _item("PANEL", "release.header", "Release header", role="group", props={
        "layout": {"type": "ROW", "gap": 12}, "layout_item": {"height": 38},
    }, children=(title, posture))

    channel = _item("SELECT", "release.channel", "Release channel", focusable=True, props={
        "realization_key": "release.channel", "options": ["candidate", "stable"], "default": "candidate",
        "layout_item": {"width": 170},
    })
    strict = _item("CHECKBOX", "release.strict", "Strict verification", focusable=True, props={
        "realization_key": "release.strict", "default": True, "layout_item": {"width": 190},
    })
    refresh = _item("BUTTON", "release.refresh", "Refresh inventory", operation="REFRESH_INVENTORY", focusable=True, props={
        "realization_key": "release.refresh", "layout_item": {"width": 170},
    })
    show = _item("BUTTON", "release.show", "Releases", operation="SHOW_RELEASES", focusable=True, props={
        "realization_key": "release.show", "target_view": "release", "layout_item": {"width": 120},
    })
    controls = _item("PANEL", "release.controls", "Inventory controls", role="group", props={
        "layout": {"type": "ROW", "gap": 10}, "layout_item": {"height": 38},
    }, children=(channel, strict, refresh, show))

    files = _item("KEY_VALUE", "release.files", "Source files", props={
        "realization_key": "release.files", "default": "Not scanned", "layout_item": {"grow": 1},
    })
    size = _item("KEY_VALUE", "release.bytes", "Source bytes", props={
        "realization_key": "release.bytes", "default": "Not scanned", "layout_item": {"grow": 1},
    })
    tests = _item("KEY_VALUE", "release.tests", "Test modules", props={
        "realization_key": "release.tests", "default": "Not scanned", "layout_item": {"grow": 1},
    })
    metrics = _item("PANEL", "release.metrics", "Release metrics", role="group", props={
        "layout": {"type": "ROW", "gap": 10}, "layout_item": {"height": 78},
    }, children=(files, size, tests))

    inventory = _item("TABLE", "release.inventory", "Package inventory", role="table", focusable=True, props={
        "realization_key": "release.inventory", "columns": ["Area", "Files", "Bytes"], "default": [],
        "layout_item": {"grow": 3, "min_height": 150},
    })
    evidence = _item("TEXT_FIELD", "release.evidence", "Verification evidence", role="log", focusable=True, props={
        "realization_key": "release.evidence", "readonly": True, "multiline": True,
        "default": "Run an inventory scan, verification, or profile model.",
        "layout_item": {"grow": 2, "min_height": 100},
    })
    progress = _item("PROGRESS", "release.progress", "Operation progress", role="progressbar", props={
        "realization_key": "release.progress", "default": 0.0, "layout_item": {"height": 18},
    })
    status = _item("STATUS", "release.status", "Ready", role="status", props={
        "realization_key": "release.status", "display_text": "Ready", "layout_item": {"height": 26},
    })
    verify = _item("BUTTON", "release.verify", "Verify source", operation="VERIFY_SOURCE", focusable=True, props={
        "realization_key": "release.verify", "layout_item": {"width": 150},
    })
    model = _item("BUTTON", "release.model", "Model minimal runtime", operation="MODEL_MINIMAL_RUNTIME", focusable=True, props={
        "realization_key": "release.model", "layout_item": {"width": 210},
    })
    cancel = _item("BUTTON", "release.cancel", "Cancel", operation="CANCEL_OPERATION", focusable=True, props={
        "realization_key": "release.cancel", "default_state": "DISABLED", "layout_item": {"width": 110},
    })
    actions = _item("PANEL", "release.actions", "Release actions", role="group", props={
        "layout": {"type": "ROW", "gap": 10}, "layout_item": {"height": 38},
    }, children=(verify, model, cancel))
    tree = _item("WINDOW", "release.window", "Mosaic Release Console", role="application", props={
        "layout_provider": "mosaic.ui.layout.v0.1",
        "layout": {"type": "COLUMN", "padding": 20, "gap": 10},
    }, children=(header, controls, metrics, inventory, evidence, progress, status, actions)).as_dict()
    operations = ["SHOW_RELEASES", "REFRESH_INVENTORY", "VERIFY_SOURCE", "MODEL_MINIMAL_RUNTIME", "CANCEL_OPERATION"]
    return {
        "schema": "mosaic.ui.pilot-application.v0.1",
        "application_id": "MOSAIC_RELEASE_CONSOLE",
        "declared_operation_ids": operations,
        "lifecycle": {
            "schema": "mosaic.ui.std.lifecycle-binding.v0.1",
            "initial_view": "release",
            "operation_controls": {"cancel_key": "release.cancel", "progress_key": "release.progress"},
            "operation_classes": {
                "NAVIGATE": ["SHOW_RELEASES"],
                "LONG_RUNNING": ["REFRESH_INVENTORY", "VERIFY_SOURCE", "MODEL_MINIMAL_RUNTIME"],
                "CANCEL": ["CANCEL_OPERATION"],
                "TOGGLE_DISCLOSURE": [],
                "HOST_WITHHELD": [],
            },
            "status_templates": {
                "initial": "Ready | release inspection | local candidate",
                "queued": "{operation_phrase} queued",
                "progress": "{stage_phrase} | {percent} | {mm}:{ss}",
                "terminal": "{operation} {terminal} | {message}",
                "cancelled": "{operation} cancelled | completed evidence retained",
            },
            "progress_default_stage": "working",
        },
        "tree": tree,
        "standing": "LOCAL_CANDIDATE",
        "authority_effect": "NONE",
    }


def build_payload() -> dict[str, Any]:
    specification = read_json(SOURCE / "specification.json")
    library = read_json(SOURCE / "component-library.json")
    application = pilot_application()
    library_validation = validate_component_library(library)
    tree_validation = validate_tree(application["tree"], set(application["declared_operation_ids"]))
    inputs = {"specification": specification, "library": library, "application": application}
    return {
        "schema": "mosaic.ui.generated-library.v0.1",
        "input_root": commitment("MOSAIC.UI.FOUNDRY.INPUT.v0.1", inputs),
        "specification": specification,
        "library": library,
        "application": application,
        "library_validation": library_validation,
        "tree_validation": tree_validation,
        "realization": {"target": "PORTABLE_REALIZER_PROTOCOL", "allowed_effects": ["SEMANTIC_INTENT"]},
        "standing": "LOCAL_CANDIDATE",
        "authority_effect": "NONE",
    }


def _inventory(context: OperationContext, source_root: Path = ROOT) -> OperationResult:
    root = context.require_path(source_root)
    groups: dict[str, list[Path]] = {"runtime": [], "stdlib": [], "tests": [], "tools": []}
    for name, folder in (("runtime", "mosaic_ui"), ("stdlib", "mosaic_ui_std"), ("tests", "tests"), ("tools", "tools")):
        groups[name] = sorted(
            (path for path in (root / folder).rglob("*")
             if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"),
            key=lambda path: path.relative_to(root / folder).as_posix())
    rows = [[name, len(paths), sum(path.stat().st_size for path in paths)] for name, paths in groups.items()]
    count = sum(row[1] for row in rows)
    size = sum(row[2] for row in rows)
    return OperationResult(
        f"indexed {count} source files",
        {"release.files": str(count), "release.bytes": str(size), "release.tests": str(len(groups["tests"])),
         "release.inventory": rows, "release.evidence": f"Inventory root: {root}\nFiles: {count}\nBytes: {size}"},
        {"root": str(root), "areas": len(rows)},
    )


def _verify(context: OperationContext, source_root: Path = ROOT) -> OperationResult:
    root = context.require_path(source_root)
    required = [root / "mosaic_ui" / "headless.py", root / "mosaic_ui_std" / "catalog.json"]
    missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
    py_files = sorted(
        (path for folder in (root / "mosaic_ui", root / "mosaic_ui_std")
         for path in folder.rglob("*.py")),
        key=lambda path: path.relative_to(root).as_posix())
    digests = {str(path.relative_to(root)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest() for path in py_files}
    if missing:
        raise ValueError("missing required files: " + ",".join(missing))
    digest_root = commitment("MOSAIC.UI.PILOT.SOURCE_INVENTORY.v0.1", digests)
    return OperationResult(
        f"verified {len(py_files)} Python sources",
        {"release.evidence": f"Required files: PASS\nPython sources: {len(py_files)}\nInventory root: {digest_root}"},
        {"python_sources": len(py_files), "inventory_root": digest_root, "test_execution": "NOT_PART_OF_IN_APP_CHECK"},
    )


def _model(context: OperationContext) -> OperationResult:
    payload = build_payload()
    kinds = sorted({item["kind"] for item in _walk(payload["application"]["tree"])})
    total = len(payload["library"]["components"])
    removed = total - len(kinds)
    return OperationResult(
        f"modeled {len(kinds)} retained component kinds",
        {"release.evidence": "Pilot runtime profile\nRetained: " + ", ".join(kinds) + f"\nAblatable kinds: {removed}"},
        {"retained_kinds": kinds, "removed_kind_count": removed, "physical_slice": "NOT_BUILT_BY_MODEL_OPERATION"},
    )


def _walk(tree: dict[str, Any]):
    yield tree
    for child in tree.get("children", []):
        yield from _walk(child)


def build_runtime(source_root: Path = ROOT) -> GovernedRuntime:
    # The source root is explicit policy evidence, even though the packaged pilot uses its own root.
    source_root = source_root.resolve()
    policy = RuntimePolicy(("PURE", "READ_LOCAL"), (source_root,))
    return GovernedRuntime(build_payload(), (
        OperationSpec("REFRESH_INVENTORY", "READ_LOCAL", lambda context: _inventory(context, source_root)),
        OperationSpec("VERIFY_SOURCE", "READ_LOCAL", lambda context: _verify(context, source_root)),
        OperationSpec("MODEL_MINIMAL_RUNTIME", "PURE", _model),
    ), policy=policy)


def pilot_witness(width: int = 1280, height: int = 800) -> dict[str, Any]:
    runtime = build_runtime()
    for node_id in ("release.refresh", "release.verify", "release.model"):
        runtime.dispatch({"intent": "ACTIVATE", "node_id": node_id})
        runtime.run_next()
    projection = runtime.ui.project(width, height).as_dict()
    runtime_pass = all(receipt["disposition"] == "COMPLETE" for receipt in runtime.receipts)
    value = {
        "schema": "mosaic.ui.pilot-witness.v0.1",
        "application_id": "MOSAIC_RELEASE_CONSOLE",
        "runtime": runtime.snapshot(),
        "projection": projection,
        "disposition": "PASS_LOCAL_CANDIDATE" if projection["gates"]["disposition"] == "PASS" and runtime_pass else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": "PILOT_EXECUTION_ESTABLISHES_LOCAL_CONTRACT_INTEGRATION_ONLY",
    }
    value["commitment"] = commitment("MOSAIC.UI.PILOT_WITNESS.v0.1", value)
    return value


__all__ = ["build_payload", "build_runtime", "pilot_application", "pilot_witness"]

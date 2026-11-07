"""Operation-lifecycle binding: the app-declared facts a realizer needs to run operations.

Replaces realizer hard-codes (initial view, cancel/progress control keys, operation IDs
dispatched by name, status wording) with a validated declaration in the application spec.
Status templates are filled by closed substitution (never str.format), so values are
inserted literally and cannot reach attributes or other placeholders.
"""
from __future__ import annotations

import re
from typing import Any

from mosaic_ui.model import UIRefusal, walk

LIFECYCLE_SCHEMA = "mosaic.ui.std.lifecycle-binding.v0.1"
BINDING_KEYS = {"schema", "initial_view", "operation_controls", "operation_classes",
                "status_templates", "progress_default_stage"}
CONTROL_KEYS = {"cancel_key", "progress_key"}
OPERATION_CLASSES = ("NAVIGATE", "LONG_RUNNING", "CANCEL", "TOGGLE_DISCLOSURE", "HOST_WITHHELD")
TEMPLATE_PLACEHOLDERS = {
    "initial": frozenset(),
    "queued": frozenset({"operation_phrase"}),
    "progress": frozenset({"stage_phrase", "percent", "mm", "ss"}),
    "terminal": frozenset({"operation", "terminal", "message"}),
    "cancelled": frozenset({"operation"}),
}
PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")


def _template_failures(name: str, template: Any) -> list[str]:
    if not isinstance(template, str):
        return [f"TEMPLATE_INVALID:{name}:NOT_STRING"]
    used = set(PLACEHOLDER.findall(template))
    failures = [f"TEMPLATE_INVALID:{name}:UNKNOWN_PLACEHOLDER:{p}" for p in sorted(used - TEMPLATE_PLACEHOLDERS[name])]
    residue = PLACEHOLDER.sub("", template)
    if "{" in residue or "}" in residue:
        failures.append(f"TEMPLATE_INVALID:{name}:STRAY_BRACE")
    return failures


def render(template: str, values: dict[str, str]) -> str:
    """Single-pass literal substitution over a validated template."""
    return PLACEHOLDER.sub(lambda match: values[match.group(1)], template)


def validate_lifecycle(application: dict[str, Any]) -> dict[str, Any]:
    """Validate application['lifecycle'] against the tree (R1-R6); return the resolved binding."""
    binding = application.get("lifecycle")
    failures: list[str] = []
    if not isinstance(binding, dict):
        raise UIRefusal("LIFECYCLE_REFUSED", "LIFECYCLE_BINDING_ABSENT")
    if set(binding) != BINDING_KEYS:
        raise UIRefusal("LIFECYCLE_REFUSED", "KEYS_MISMATCH:" + ",".join(sorted(set(binding) ^ BINDING_KEYS)))
    if binding["schema"] != LIFECYCLE_SCHEMA:
        failures.append("SCHEMA_MISMATCH")
    controls = binding["operation_controls"]
    classes = binding["operation_classes"]
    templates = binding["status_templates"]
    if not isinstance(controls, dict) or set(controls) != CONTROL_KEYS:
        failures.append("OPERATION_CONTROLS_SHAPE_INVALID")
    if not isinstance(classes, dict) or set(classes) != set(OPERATION_CLASSES) \
            or not all(isinstance(v, list) and all(isinstance(o, str) for o in v) for v in classes.values()):
        failures.append("OPERATION_CLASSES_SHAPE_INVALID")
    if not isinstance(templates, dict) or set(templates) != set(TEMPLATE_PLACEHOLDERS):
        failures.append("STATUS_TEMPLATES_SHAPE_INVALID")
    stage = binding["progress_default_stage"]
    if not isinstance(stage, str) or not stage:
        failures.append("PROGRESS_DEFAULT_STAGE_INVALID")
    if failures:
        raise UIRefusal("LIFECYCLE_REFUSED", ";".join(sorted(failures)))

    # R1: every declared operation classified exactly once; nothing undeclared.
    declared = set(application.get("declared_operation_ids", ()))
    operation_class: dict[str, str] = {}
    for class_name in OPERATION_CLASSES:
        for operation in classes[class_name]:
            if operation in operation_class:
                failures.append(f"OPERATION_MULTIPLY_CLASSIFIED:{operation}")
            operation_class[operation] = class_name
    failures += [f"OPERATION_UNCLASSIFIED:{o}" for o in sorted(declared - set(operation_class))]
    failures += [f"OPERATION_UNDECLARED:{o}" for o in sorted(set(operation_class) - declared)]

    # R2: target_view present iff the node's operation is NAVIGATE.
    keyed: dict[str, dict[str, Any]] = {}
    target_views: set[str] = set()
    for item in walk(application["tree"]):
        node_id = str(item.get("node_id"))
        props = item.get("props", {})
        if not isinstance(props, dict):
            failures.append(f"PROPS_NOT_OBJECT:{node_id}")
            continue
        if props.get("realization_key"):
            keyed[str(props["realization_key"])] = item
        target_view = props.get("target_view")
        if target_view is not None:
            if not isinstance(target_view, str) or not target_view:
                failures.append(f"TARGET_VIEW_INVALID:{node_id}")
            else:
                target_views.add(target_view)
        operation = item.get("operation_ref")
        if operation is None:
            if target_view is not None:
                failures.append(f"TARGET_VIEW_WITHOUT_OPERATION:{node_id}")
            continue
        navigate = operation_class.get(operation) == "NAVIGATE"
        if navigate and target_view is None:
            failures.append(f"NAVIGATION_WITHOUT_TARGET_VIEW:{node_id}")
        if not navigate and target_view is not None:
            failures.append(f"TARGET_VIEW_ON_NON_NAVIGATE:{node_id}")

    # R3: the initial view is reachable by navigation.
    if binding["initial_view"] not in target_views:
        failures.append(f"INITIAL_VIEW_UNREACHABLE:{binding['initial_view']}")

    # R4/R5: control keys point at real controls; null exactly when there are no long-running operations.
    long_running = bool(classes["LONG_RUNNING"])
    cancel_key, progress_key = controls["cancel_key"], controls["progress_key"]
    if long_running:
        cancel = keyed.get(cancel_key) if isinstance(cancel_key, str) else None
        if cancel is None or operation_class.get(cancel.get("operation_ref")) != "CANCEL":
            failures.append(f"CANCEL_KEY_INVALID:{cancel_key}")
        progress = keyed.get(progress_key) if isinstance(progress_key, str) else None
        if progress is None or progress.get("kind") != "PROGRESS":
            failures.append(f"PROGRESS_KEY_INVALID:{progress_key}")
    else:
        if cancel_key is not None:
            failures.append("CANCEL_KEY_WITHOUT_LONG_RUNNING")
        if progress_key is not None:
            failures.append("PROGRESS_KEY_WITHOUT_LONG_RUNNING")

    # R6: closed templates.
    for name in sorted(TEMPLATE_PLACEHOLDERS):
        failures += _template_failures(name, templates[name])

    if failures:
        raise UIRefusal("LIFECYCLE_REFUSED", ";".join(sorted(failures)))
    return {
        "initial_view": binding["initial_view"],
        "cancel_key": cancel_key,
        "progress_key": progress_key,
        "operation_class": operation_class,
        "templates": dict(templates),
        "progress_default_stage": stage,
    }

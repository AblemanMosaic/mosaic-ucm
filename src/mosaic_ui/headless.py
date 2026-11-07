from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .canonical import commitment
from .components import load_handlers
from .localization import mirror_layout, resolve_payload
from .model import STATES, UIRefusal, validate_tree, walk
from mosaic_ui_std.catalog import check_realizable, load_runtime_catalog, validate_catalog
from mosaic_ui_std.lifecycle import render, validate_lifecycle


Rect = tuple[int, int, int, int]
LayoutProvider = Callable[[int, int], dict[str, Rect]]
TERMINAL_OPERATION_STATES = {"COMPLETE", "CANCELLED", "REFUSED"}
class HeadlessRefusal(UIRefusal):
    pass


def _index(tree: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["node_id"]): item for item in walk(tree)}


def _realization_nodes(tree: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in walk(tree) if item.get("props", {}).get("realization_key")]


def validate_realization_correspondence(
    payload: dict[str, Any], actual_control_keys: Iterable[str], layout_keys: Iterable[str]
) -> dict[str, Any]:
    declared = {str(item["props"]["realization_key"]) for item in _realization_nodes(payload["application"]["tree"])}
    actual = set(actual_control_keys)
    layout = set(layout_keys)
    failures = {
        "missing_native_controls": sorted(declared - actual),
        "undeclared_native_controls": sorted(actual - declared),
        "missing_layout_entries": sorted(declared - layout),
        "undeclared_layout_entries": sorted(layout - declared),
    }
    if any(failures.values()):
        raise HeadlessRefusal("REALIZATION_CORRESPONDENCE_REFUSED", json_safe(failures))
    value = {
        "schema": "mosaic.ui.realization-correspondence.v0.1",
        "declared_control_count": len(declared), "native_control_count": len(actual),
        "layout_entry_count": len(layout), "disposition": "PASS_LOCAL_CANDIDATE",
        "authority_effect": "NONE",
    }
    value["commitment"] = commitment("MOSAIC.UI.REALIZATION_CORRESPONDENCE.v0.1", value)
    return value


def json_safe(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _is_visible(item: dict[str, Any], active_view: str, evidence_open: dict[str, bool]) -> bool:
    props = item.get("props", {})
    view = props.get("view")
    if view is not None and view != active_view:
        return False
    if props.get("evidence_only"):
        return evidence_open.get(view, False)
    if props.get("summary_only"):
        return not evidence_open.get(view, False)
    return True


def _color_channels(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    return tuple(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels)


def _luminance(value: str) -> float:
    red, green, blue = _color_channels(value)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast(first: str, second: str) -> float:
    high, low = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _intersection(first: Rect, second: Rect) -> tuple[int, int] | None:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[0] + first[2], second[0] + second[2])
    bottom = min(first[1] + first[3], second[1] + second[3])
    return (right - left, bottom - top) if right > left and bottom > top else None


def _overlap_failures(items: list[tuple[str, Rect | None, dict[str, Any]]]) -> list[dict[str, Any]]:
    """Find overlaps with a deterministic sweep over the broader layout axis."""
    candidates = [(index, node_id, rect, item) for index, (node_id, rect, item) in enumerate(items)
                  if rect is not None]
    if len(candidates) < 2:
        return []
    x_span = max(row[2][0] + row[2][2] for row in candidates) - min(row[2][0] for row in candidates)
    y_span = max(row[2][1] + row[2][3] for row in candidates) - min(row[2][1] for row in candidates)
    axis = 0 if x_span >= y_span else 1
    extent = 2 if axis == 0 else 3
    ordered = sorted(candidates, key=lambda row: (row[2][axis], row[0]))
    active: list[tuple[int, str, Rect, dict[str, Any]]] = []
    failures: list[tuple[int, int, dict[str, Any]]] = []
    for current in ordered:
        current_start = current[2][axis]
        active = [row for row in active if row[2][axis] + row[2][extent] > current_start]
        for prior in active:
            overlap = _intersection(prior[2], current[2])
            if overlap and prior[3]["kind"] != "PROGRESS" and current[3]["kind"] != "PROGRESS":
                first, second = sorted((prior, current), key=lambda row: row[0])
                failures.append((first[0], second[0], {
                    "gate": "OVERLAP", "nodes": [first[1], second[1]], "pixels": list(overlap),
                }))
        active.append(current)
    return [row[2] for row in sorted(failures, key=lambda row: (row[0], row[1]))]


def _visual_rect(item: dict[str, Any], rect: Rect) -> Rect:
    # Win32 combo allocation includes popup extent; the closed control is one field high.
    if item.get("kind") == "SELECT":
        return (rect[0], rect[1], rect[2], min(29, rect[3]))
    return rect


def _overlay(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(base)
    for key, item in override.items():
        if isinstance(value.get(key), dict) and isinstance(item, dict):
            value[key] = _overlay(value[key], item)
        else:
            value[key] = copy.deepcopy(item)
    return value


@dataclass(frozen=True)
class Projection:
    semantics: dict[str, Any]
    geometry: dict[str, Any]
    accessibility: dict[str, Any]
    draw_stream: dict[str, Any]
    gates: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "semantics": self.semantics,
            "geometry": self.geometry,
            "accessibility": self.accessibility,
            "draw_stream": self.draw_stream,
            "gates": self.gates,
        }


class HeadlessUI:
    """Deterministic semantic realization; creates no HWND and performs no host input."""

    def __init__(
        self,
        payload: dict[str, Any],
        layout_provider: LayoutProvider | None = None,
        *,
        catalog: dict[str, Any] | None = None,
        locale: str | None = None,
        accept_language: str | None = None,
    ) -> None:
        self.source_payload = copy.deepcopy(payload)
        self.localization_explicit = "localization" in self.source_payload.get("application", {})
        self.payload, self.localization = resolve_payload(self.source_payload, locale, accept_language)
        self.application = self.payload["application"]
        self.tree = self.application["tree"]
        self.nodes = _index(self.tree)
        self.layout_provider = layout_provider
        validate_tree(self.tree, set(self.application["declared_operation_ids"]))
        if "theme_v02" in self.payload.get("library", {}):
            from .foundry import validate_library_theme_v02

            validate_library_theme_v02(self.payload["library"])
        self.lifecycle = validate_lifecycle(self.application)
        self.catalog = copy.deepcopy(catalog) if catalog is not None else load_runtime_catalog()
        validate_catalog(self.catalog)
        check_realizable(self.catalog, self.tree, "HEADLESS")
        self.handlers = load_handlers(self.catalog)
        self.state = self._initial_state()

    def layout_plan(self, width: int, height: int) -> dict[str, Rect]:
        if self.layout_provider is not None:
            plan = self.layout_provider(width, height)
        else:
            from .layout import layout_tree

            plan = layout_tree(self.tree, width, height, active_view=self.state["active_view"])
        return mirror_layout(plan, width) if self.localization.direction == "RTL" else plan

    def _initial_state(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        states: dict[str, str] = {}
        for item in _realization_nodes(self.tree):
            props = item.get("props", {})
            key = props["realization_key"]
            if "default" in props:
                values[key] = props["default"]
            states[key] = str(props.get("default_state", "IDLE"))
        value = {
            "active_view": self.lifecycle["initial_view"],
            "evidence_open": {},
            "focused_node_id": None,
            "values": values,
            "states": states,
            "active_operation": None,
            "operation_node_id": None,
            "progress": 0.0,
            "status": render(self.lifecycle["templates"]["initial"], {}),
            "emitted_intents": [],
            "event_count": 0,
        }
        if self.localization_explicit:
            value = {"locale": self.localization.locale, "direction": self.localization.direction, **value}
        return value

    def clone(self) -> "HeadlessUI":
        value = HeadlessUI(
            self.source_payload, self.layout_provider, catalog=self.catalog, locale=self.localization.locale,
        )
        value.state = copy.deepcopy(self.state)
        return value

    def visible_nodes(self) -> list[dict[str, Any]]:
        return [item for item in _realization_nodes(self.tree) if _is_visible(item, self.state["active_view"], self.state["evidence_open"])]

    def focus_order(self) -> list[str]:
        return [
            str(item["node_id"])
            for item in self.visible_nodes()
            if item.get("semantics", {}).get("focusable")
            and self.state["states"].get(item["props"]["realization_key"]) != "DISABLED"
        ]

    def apply(self, event: dict[str, Any]) -> dict[str, Any]:
        kind = str(event.get("intent") or "").upper()
        self.state["event_count"] += 1
        if kind == "ACTIVATE":
            self._activate(str(event.get("node_id") or ""))
        elif kind in {"SELECT", "TEXT_COMMIT", "TOGGLE", "STEP", "DIALOG_DECISION"}:
            self._component_event(kind, event)
        elif kind == "FOCUS":
            self._focus(str(event.get("node_id") or ""))
        elif kind == "FOCUS_NEXT":
            self._focus_next()
        elif kind == "PROGRESS":
            self._progress(event)
        elif kind == "COMPLETE":
            self._terminal("COMPLETE", event)
        elif kind == "REFUSE":
            self._terminal("REFUSED", event)
        elif kind == "CANCEL":
            self._cancel()
        else:
            raise HeadlessRefusal("UNKNOWN_SEMANTIC_INTENT", kind)
        return self.snapshot()

    def _require_interactive(self, node_id: str) -> dict[str, Any]:
        item = self.nodes.get(node_id)
        if item is None:
            raise HeadlessRefusal("UNKNOWN_NODE", node_id)
        if not _is_visible(item, self.state["active_view"], self.state["evidence_open"]):
            raise HeadlessRefusal("HIDDEN_NODE_INTERACTION_REFUSED", node_id)
        key = item.get("props", {}).get("realization_key")
        if key and self.state["states"].get(key) == "DISABLED":
            raise HeadlessRefusal("DISABLED_NODE_INTERACTION_REFUSED", node_id)
        return item

    @staticmethod
    def _component_refusal(code: str, detail: str) -> None:
        raise HeadlessRefusal(code, detail)

    def _component_event(self, intent: str, event: dict[str, Any]) -> None:
        node_id = str(event.get("node_id") or "")
        item = self._require_interactive(node_id)
        handler = self.handlers[item["kind"]]
        if handler.interaction_intent != intent or handler.interact is None:
            code = {
                "TEXT_COMMIT": "TEXT_COMMIT_REFUSED", "TOGGLE": "TOGGLE_REFUSED",
                "STEP": "STEP_REFUSED", "DIALOG_DECISION": "DIALOG_DECISION_REFUSED",
            }.get(intent, "INVALID_SELECTION")
            raise HeadlessRefusal(code, node_id)
        handler.interact(self, item, event)

    def _activate(self, node_id: str) -> None:
        item = self._require_interactive(node_id)
        operation = item.get("operation_ref")
        if not operation:
            raise HeadlessRefusal("NODE_HAS_NO_ACTIVATION_OPERATION", node_id)
        intent = {
            "intent": "REQUEST_ACTIVATION", "node_id": node_id,
            "operation_ref": operation, "authority_effect": "NONE",
        }
        # B2: an intent is recorded only once its branch has succeeded; refusals leave no intent.
        target_view = item.get("props", {}).get("target_view")
        if target_view:
            self.state["active_view"] = target_view
            self.state["focused_node_id"] = node_id
            self.state["emitted_intents"].append(intent)
            return
        operation_class = self.lifecycle["operation_class"][operation]
        if operation_class == "TOGGLE_DISCLOSURE":
            view = self.state["active_view"]
            self.state["evidence_open"][view] = not self.state["evidence_open"].get(view, False)
            self.state["emitted_intents"].append(intent)
            return
        if operation_class == "CANCEL":
            self._cancel()
            self.state["emitted_intents"].append(intent)
            return
        if operation_class == "HOST_WITHHELD":
            intent["host_effect"] = "WITHHELD_IN_HEADLESS_REALIZATION"
            self.state["emitted_intents"].append(intent)
            return
        if self.state["active_operation"]:
            raise HeadlessRefusal("OPERATION_ALREADY_ACTIVE", str(self.state["active_operation"]))
        key = item["props"]["realization_key"]
        self.state["active_operation"] = operation
        self.state["operation_node_id"] = node_id
        self.state["states"][key] = "PENDING"
        self.state["states"][self.lifecycle["cancel_key"]] = "IDLE"
        self.state["progress"] = 1.0
        self.state["values"][self.lifecycle["progress_key"]] = 1.0
        self.state["status"] = render(self.lifecycle["templates"]["queued"],
                                      {"operation_phrase": operation.lower().replace("_", " ")})
        self.state["emitted_intents"].append(intent)

    def _focus(self, node_id: str) -> None:
        item = self._require_interactive(node_id)
        if not item.get("semantics", {}).get("focusable"):
            raise HeadlessRefusal("NON_FOCUSABLE_NODE", node_id)
        prior = self.state.get("focused_node_id")
        if prior and prior in self.nodes:
            prior_key = self.nodes[prior].get("props", {}).get("realization_key")
            if prior_key and self.state["states"].get(prior_key) == "FOCUSED":
                self.state["states"][prior_key] = "IDLE"
        key = item["props"]["realization_key"]
        if self.state["states"].get(key) == "IDLE":
            self.state["states"][key] = "FOCUSED"
        self.state["focused_node_id"] = node_id

    def _focus_next(self) -> None:
        order = self.focus_order()
        if not order:
            raise HeadlessRefusal("NO_FOCUSABLE_NODE", self.state["active_view"])
        current = self.state.get("focused_node_id")
        next_node = order[0] if current not in order else order[(order.index(current) + 1) % len(order)]
        self._focus(next_node)

    def _progress(self, event: dict[str, Any]) -> None:
        if not self.state["active_operation"]:
            raise HeadlessRefusal("PROGRESS_WITHOUT_ACTIVE_OPERATION", "")
        percent = float(event.get("percent", 0))
        if not math.isfinite(percent) or percent < 0 or percent > 100:
            raise HeadlessRefusal("INVALID_PROGRESS", str(percent))
        self.state["progress"] = percent
        self.state["values"][self.lifecycle["progress_key"]] = percent
        stage = str(event.get("stage") or self.lifecycle["progress_default_stage"]).replace("_", " ")
        elapsed = int(event.get("elapsed_seconds") or 0)
        self.state["status"] = render(self.lifecycle["templates"]["progress"], {
            "stage_phrase": stage, "percent": f"{percent:.1f}%",
            "mm": f"{elapsed // 60:02d}", "ss": f"{elapsed % 60:02d}"})

    def _terminal(self, terminal: str, event: dict[str, Any]) -> None:
        if not self.state["active_operation"]:
            raise HeadlessRefusal("TERMINAL_WITHOUT_ACTIVE_OPERATION", terminal)
        node_id = str(self.state["operation_node_id"])
        key = self.nodes[node_id]["props"]["realization_key"]
        self.state["states"][key] = "REFUSED" if terminal == "REFUSED" else "IDLE"
        self.state["states"][self.lifecycle["cancel_key"]] = "DISABLED"
        if terminal == "COMPLETE":
            self.state["progress"] = 100.0
            self.state["values"][self.lifecycle["progress_key"]] = 100.0
        message = str(event.get("message") or terminal.lower())
        self.state["status"] = render(self.lifecycle["templates"]["terminal"], {
            "operation": str(self.state["active_operation"]), "terminal": terminal.lower(), "message": message})
        self.state["active_operation"] = None
        self.state["operation_node_id"] = None

    def _cancel(self) -> None:
        if not self.state["active_operation"]:
            raise HeadlessRefusal("CANCEL_WITHOUT_ACTIVE_OPERATION", "")
        node_id = str(self.state["operation_node_id"])
        key = self.nodes[node_id]["props"]["realization_key"]
        self.state["states"][key] = "IDLE"
        self.state["states"][self.lifecycle["cancel_key"]] = "DISABLED"
        self.state["status"] = render(self.lifecycle["templates"]["cancelled"],
                                      {"operation": str(self.state["active_operation"])})
        self.state["active_operation"] = None
        self.state["operation_node_id"] = None

    def snapshot(self) -> dict[str, Any]:
        value = {
            "schema": "mosaic.ui.headless-state.v0.1",
            **copy.deepcopy(self.state),
            "standing": "LOCAL_CANDIDATE_EVIDENCE",
            "authority_effect": "NONE",
            "host_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.HEADLESS_STATE.v0.1", value)
        return value

    def load_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Restore a committed state snapshot after validating its closed runtime shape."""
        expected_keys = {
            "schema", *self._initial_state().keys(), "standing", "authority_effect", "host_effect", "commitment",
        }
        if not isinstance(snapshot, dict) or set(snapshot) != expected_keys \
                or snapshot.get("schema") != "mosaic.ui.headless-state.v0.1":
            raise HeadlessRefusal("HEADLESS_STATE_RESTORE_REFUSED", "SCHEMA")
        body = copy.deepcopy(snapshot)
        observed = body.pop("commitment", None)
        if observed != commitment("MOSAIC.UI.HEADLESS_STATE.v0.1", body):
            raise HeadlessRefusal("HEADLESS_STATE_RESTORE_REFUSED", "COMMITMENT")
        if snapshot.get("standing") != "LOCAL_CANDIDATE_EVIDENCE" \
                or snapshot.get("authority_effect") != "NONE" or snapshot.get("host_effect") != "NONE":
            raise HeadlessRefusal("HEADLESS_STATE_RESTORE_REFUSED", "BOUNDARY")
        realization_keys = {
            str(item["props"]["realization_key"]) for item in _realization_nodes(self.tree)
        }
        values, states = snapshot.get("values"), snapshot.get("states")
        if not isinstance(values, dict) or not set(values) <= realization_keys \
                or not isinstance(states, dict) or set(states) != realization_keys \
                or any(value not in STATES for value in states.values()):
            raise HeadlessRefusal("HEADLESS_STATE_RESTORE_REFUSED", "COMPONENT_STATE")
        views = {self.lifecycle["initial_view"]}
        views.update(
            str(item.get("props", {}).get("target_view"))
            for item in walk(self.tree) if item.get("props", {}).get("target_view") is not None
        )
        focused = snapshot.get("focused_node_id")
        if snapshot.get("active_view") not in views \
                or self.localization_explicit and snapshot.get("locale") != self.localization.locale \
                or self.localization_explicit and snapshot.get("direction") != self.localization.direction \
                or focused is not None and focused not in self.nodes \
                or not isinstance(snapshot.get("evidence_open"), dict) \
                or not isinstance(snapshot.get("emitted_intents"), list) \
                or isinstance(snapshot.get("event_count"), bool) \
                or not isinstance(snapshot.get("event_count"), int) or snapshot["event_count"] < 0 \
                or not isinstance(snapshot.get("status"), str) \
                or isinstance(snapshot.get("progress"), bool) \
                or not isinstance(snapshot.get("progress"), (int, float)) \
                or not 0 <= float(snapshot["progress"]) <= 100:
            raise HeadlessRefusal("HEADLESS_STATE_RESTORE_REFUSED", "STATE_VALUE")
        self.state = {
            key: copy.deepcopy(snapshot[key]) for key in self._initial_state()
        }

    def project(self, width: int, height: int) -> Projection:
        semantics = self._semantic_projection()
        geometry = self._geometry_projection(width, height)
        accessibility = self._accessibility_projection()
        draw = self._draw_projection(geometry)
        gates = self._gates(width, height, geometry, accessibility)
        return Projection(semantics, geometry, accessibility, draw, gates)

    def _semantic_projection(self) -> dict[str, Any]:
        nodes = []
        for item in self.visible_nodes():
            key = item["props"]["realization_key"]
            nodes.append({
                "node_id": item["node_id"], "realization_key": key, "kind": item["kind"],
                "semantics": item["semantics"], "operation_ref": item.get("operation_ref"),
                "state": self.state["states"].get(key, "IDLE"),
                "value": self.state["values"].get(key),
            })
        value = {
            "schema": "mosaic.ui.headless-semantic-projection.v0.1",
            "active_view": self.state["active_view"], "locale": self.localization.locale,
            "direction": self.localization.direction, "nodes": nodes,
            "generated_root": self.payload["input_root"], "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.HEADLESS_SEMANTICS.v0.1", value)
        return value

    def _geometry_projection(self, width: int, height: int) -> dict[str, Any]:
        plan = self.layout_plan(width, height)
        rows = []
        missing = []
        for item in self.visible_nodes():
            key = item["props"]["realization_key"]
            rect = plan.get(key)
            if rect is None:
                missing.append(key)
                continue
            visual = _visual_rect(item, rect)
            rows.append({
                "node_id": item["node_id"], "realization_key": key,
                "rect": {"x": visual[0], "y": visual[1], "width": visual[2], "height": visual[3]},
                "native_allocation": {"x": rect[0], "y": rect[1], "width": rect[2], "height": rect[3]},
            })
        value = {
            "schema": "mosaic.ui.headless-geometry.v0.1", "viewport": {"width": width, "height": height},
            "direction": self.localization.direction,
            "nodes": rows, "missing_realization_keys": sorted(missing),
            "layout_provider": self.tree.get("props", {}).get("layout_provider", "mosaic.ui.layout.v0.1"),
            "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.HEADLESS_GEOMETRY.v0.1", value)
        return value

    def _accessibility_projection(self) -> dict[str, Any]:
        rows = []
        order = self.focus_order()
        for item in self.visible_nodes():
            key = item["props"]["realization_key"]
            semantics = item["semantics"]
            props = item.get("props", {})
            raw_value = self.state["values"].get(key, props.get("default"))
            rows.append({
                "node_id": item["node_id"], "role": semantics["role"], "name": semantics["name"],
                "description": semantics.get("description", ""), "actions": semantics.get("actions", []),
                "focusable": bool(semantics.get("focusable")),
                "focus_index": order.index(item["node_id"]) if item["node_id"] in order else None,
                "state": self.state["states"].get(key, "IDLE"),
                "value": (
                    self.handlers[item["kind"]].accessible_value(raw_value, props)
                    if item["kind"] == "RICH_DOCUMENT" else raw_value
                ),
            })
        value = {
            "schema": "mosaic.ui.headless-accessibility.v0.1", "active_view": self.state["active_view"],
            "locale": self.localization.locale, "direction": self.localization.direction,
            "nodes": rows, "focus_order": order, "focused_node_id": self.state["focused_node_id"],
            "platform_bridge": "NOT_CLAIMED_BY_HEADLESS_REALIZATION", "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.HEADLESS_ACCESSIBILITY.v0.1", value)
        return value

    def _draw_projection(self, geometry: dict[str, Any]) -> dict[str, Any]:
        colors = self.payload["library"]["tokens"]["colors"]
        geometry_index = {row["node_id"]: row["rect"] for row in geometry["nodes"]}
        commands = [{"op": "FILL", "target": "window", "color": colors["canvas"]}]
        for item in self.visible_nodes():
            rect = geometry_index.get(item["node_id"])
            if rect is None:
                continue
            key = item["props"]["realization_key"]
            state = self.state["states"].get(key, "IDLE")
            kind = item["kind"]
            handler = self.handlers[kind]
            builder_visual = item.get("props", {}).get("builder_visual")
            if builder_visual:
                self._project_builder_visual(commands, item, rect, state, builder_visual)
                continue
            if item.get("props", {}).get("image_asset"):
                commands.append({"op": "IMAGE_ASSET", "node_id": item["node_id"], "rect": rect,
                                 "asset": item["props"]["image_asset"]})
                continue
            fill = colors[handler.draw_fill]
            if state == "PENDING":
                fill = colors["pending"]
            elif state == "REFUSED":
                fill = colors["refused"]
            commands.append({"op": "BOX", "node_id": item["node_id"], "rect": rect, "fill": fill, "border": colors["border"],
                             "corner_radius": self.payload["library"]["tokens"]["radii"][handler.corner_radius] if handler.corner_radius else 0})
            commands.append({
                "op": "TEXT", "node_id": item["node_id"], "rect": rect,
                "text": str(
                    item.get("props", {}).get("display_text")
                    or (handler.projection_text(
                        self.state["values"].get(key, item.get("props", {}).get("default")),
                        item.get("props", {}),
                    ) if kind == "RICH_DOCUMENT" else item["semantics"]["name"])
                ),
                "color": colors["text"],
            })
        value = {
            "schema": "mosaic.ui.headless-draw-stream.v0.1", "active_view": self.state["active_view"],
            "commands": commands, "palette": colors, "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.HEADLESS_DRAW.v0.1", value)
        return value

    def _project_builder_visual(self, commands: list[dict[str, Any]], item: dict[str, Any], rect: dict[str, int],
                                state: str, visual: dict[str, Any]) -> None:
        if visual.get("schema") != "mosaic.ui.builder-vector-visual.v0.1" or visual.get("states") != list(STATES):
            raise HeadlessRefusal("BUILDER_VISUAL_SCHEMA_REFUSED", str(item["node_id"]))
        body = copy.deepcopy(visual)
        observed = body.pop("commitment", None)
        if observed != commitment("MOSAIC.UI.BUILDER_VECTOR_VISUAL.v0.1", body):
            raise HeadlessRefusal("BUILDER_VISUAL_COMMITMENT_REFUSED", str(item["node_id"]))
        coordinate_space = visual.get("source_coordinate_space", {})
        source_width = int(coordinate_space.get("width", 0))
        source_height = int(coordinate_space.get("height", 0))
        if source_width <= 0 or source_height <= 0:
            raise HeadlessRefusal("BUILDER_VISUAL_COORDINATE_SPACE_REFUSED", str(item["node_id"]))
        scale_x, scale_y = rect["width"] / source_width, rect["height"] / source_height
        for source in visual.get("layers", []):
            layer = _overlay(source, source.get("state_overrides", {}).get(state, {}))
            geometry = layer["geometry"]
            layer_rect = {
                "x": rect["x"] + round(int(geometry["x"]) * scale_x),
                "y": rect["y"] + round(int(geometry["y"]) * scale_y),
                "width": round(int(geometry["width"]) * scale_x),
                "height": round(int(geometry["height"]) * scale_y),
            }
            commands.append({
                "op": f"BUILDER_{layer['primitive']}", "node_id": item["node_id"],
                "layer_id": layer["layer_id"], "state": state, "rect": layer_rect,
                "style": layer.get("style", {}), "text": layer.get("text", ""),
                "semantic": layer.get("semantic", {}),
                "source_visual_ref": visual["commitment"],
            })

    def _gates(self, width: int, height: int, geometry: dict[str, Any], accessibility: dict[str, Any]) -> dict[str, Any]:
        failures: list[dict[str, Any]] = []
        rects: dict[str, Rect] = {}
        for row in geometry["nodes"]:
            rect_data = row["rect"]
            rect = (rect_data["x"], rect_data["y"], rect_data["width"], rect_data["height"])
            rects[row["node_id"]] = rect
            if rect[0] < 0 or rect[1] < 0 or rect[2] <= 0 or rect[3] <= 0 or rect[0] + rect[2] > width or rect[1] + rect[3] > height:
                failures.append({"gate": "BOUNDS", "node_id": row["node_id"], "rect": rect_data})
        if geometry["missing_realization_keys"]:
            failures.append({"gate": "REALIZATION_CORRESPONDENCE", "missing": geometry["missing_realization_keys"]})
        items = [(item["node_id"], rects.get(item["node_id"]), item) for item in self.visible_nodes()]
        failures.extend(_overlap_failures(items))
        for item in self.visible_nodes():
            if item["kind"] not in {"LABEL", "BUTTON", "STATUS"}:
                continue
            if item.get("props", {}).get("image_asset"):
                continue
            rect = rects.get(item["node_id"])
            if rect is None:
                continue
            display = str(item.get("props", {}).get("display_text") or item["semantics"]["name"])
            character_width = 6 if item["kind"] in {"LABEL", "STATUS"} else 7
            estimated_width = len(display) * character_width + 8
            if estimated_width > rect[2]:
                failures.append({"gate": "TEXT_FIT", "node_id": item["node_id"], "estimated_width": estimated_width, "available_width": rect[2]})
        for row in accessibility["nodes"]:
            if not row["role"] or not row["name"]:
                failures.append({"gate": "ACCESSIBILITY", "node_id": row["node_id"]})
        colors = self.payload["library"]["tokens"]["colors"]
        color_scheme = "DARK" if _luminance(colors["canvas"]) < 0.5 else "LIGHT"
        if len({colors["canvas"], colors["surface"], colors["field"]}) < 2:
            failures.append({"gate": "PALETTE_SURFACE_SEPARATION", "detail": "canvas, surface, and field are identical"})
        contrast = _contrast(colors["text"], colors["canvas"])
        if contrast < 4.5:
            failures.append({"gate": "CONTRAST", "ratio": round(contrast, 3)})
        value = {
            "schema": "mosaic.ui.headless-gate-result.v0.1", "active_view": self.state["active_view"],
            "viewport": {"width": width, "height": height}, "failure_count": len(failures),
            "failures": failures, "contrast_ratio": round(contrast, 3), "color_scheme": color_scheme,
            "disposition": "PASS" if not failures else "REFUSE", "authority_effect": "NONE",
            "claim_boundary": "HEADLESS_SEMANTICS_DO_NOT_ESTABLISH_HOST_DESKTOP_BEHAVIOR",
        }
        value["commitment"] = commitment("MOSAIC.UI.HEADLESS_GATES.v0.1", value)
        return value


def replay(payload: dict[str, Any], layout_provider: LayoutProvider, events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    runtime = HeadlessUI(payload, layout_provider)
    snapshots = [runtime.snapshot()]
    refusals = []
    for sequence, event in enumerate(events, 1):
        try:
            snapshots.append(runtime.apply(dict(event)))
        except HeadlessRefusal as exc:
            refusals.append({"sequence": sequence, "code": exc.code, "detail": exc.detail})
            snapshots.append(runtime.snapshot())
    value = {
        "schema": "mosaic.ui.headless-replay.v0.1", "event_count": len(snapshots) - 1,
        "events": list(events) if isinstance(events, list) else [], "snapshots": snapshots,
        "emitted_intents": runtime.state["emitted_intents"], "refusals": refusals,
        "final_state": runtime.snapshot(), "authority_effect": "NONE", "host_effect": "NONE",
    }
    value["commitment"] = commitment("MOSAIC.UI.HEADLESS_REPLAY.v0.1", value)
    return value

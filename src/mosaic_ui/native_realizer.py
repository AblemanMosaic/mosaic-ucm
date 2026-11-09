"""Declarative semantic-tree realization through the stdlib-only Win32 toolkit."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Callable

from mosaic_ui_std.catalog import check_realizable, load_runtime_catalog, validate_catalog

from .canonical import commitment
from .components import load_handlers
from .headless import HeadlessUI, LayoutProvider, validate_realization_correspondence
from .model import UIRefusal, walk


class NativeRealizerRefusal(UIRefusal):
    pass


class NativeSemanticUI:
    """Validated semantic payload projected into one native window.

    HeadlessUI remains the state machine. Native controls emit only its closed intent
    vocabulary and are synchronized from its resulting state.
    """

    def __init__(
        self,
        payload: dict[str, Any],
        layout_provider: LayoutProvider | None = None,
        *,
        width: int,
        height: int,
        title: str | None = None,
        window_factory: Callable[..., Any] | None = None,
        catalog: dict[str, Any] | None = None,
        locale: str | None = None,
        headless: HeadlessUI | None = None,
        event_dispatch: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        self.payload = copy.deepcopy(payload)
        self.layout_provider = layout_provider
        self.width, self.height = width, height
        selected_catalog = copy.deepcopy(catalog) if catalog is not None else load_runtime_catalog()
        validate_catalog(selected_catalog)
        if headless is not None and headless.source_payload != self.payload:
            raise NativeRealizerRefusal("NATIVE_SHARED_RUNTIME_REFUSED", "PAYLOAD_MISMATCH")
        self.runtime = headless or HeadlessUI(
            self.payload, self.layout_provider, catalog=selected_catalog, locale=locale,
        )
        self.event_dispatch = event_dispatch
        check_realizable(selected_catalog, self.runtime.tree, "WIN32")
        self.handlers = load_handlers(selected_catalog)
        if window_factory is None:
            from .win32 import NativeWindow
            window_factory = NativeWindow
        self.window = window_factory(
            title or self.runtime.tree["semantics"]["name"],
            tokens=self.payload["library"]["tokens"], width=width, height=height,
            rtl=self.runtime.localization.direction == "RTL",
        )
        self.items = {
            str(item["props"]["realization_key"]): item
            for item in walk(self.runtime.tree)
            if item.get("props", {}).get("realization_key")
        }
        self.layout = self.runtime.layout_plan(width, height)
        self._build()
        self.correspondence = validate_realization_correspondence(
            self.payload, self.items, self.layout,
        )
        self.window.layout_handler = self._relayout
        self.sync()

    def _apply(self, event: dict[str, Any]) -> None:
        try:
            if self.event_dispatch is None:
                self.runtime.apply(event)
            else:
                self.event_dispatch(copy.deepcopy(event))
        except UIRefusal as exc:
            self.runtime.state["status"] = f"{exc.code}: {exc.detail}".rstrip(": ")
        self.sync()

    @property
    def descriptor(self):
        from .realizer import PROTOCOL_SCHEMA, RealizerDescriptor

        return RealizerDescriptor(
            "WIN32", PROTOCOL_SCHEMA,
            ("SEMANTICS", "GEOMETRY", "ACCESSIBILITY", "DRAW_STREAM", "GATES", "NATIVE_CONTROLS"),
            ("VISIBLE_LOCAL_WINDOW", "LOCAL_INPUT"),
            tuple(sorted({item["kind"] for item in self.runtime.nodes.values()})),
        )

    def apply(self, event: dict[str, Any]) -> dict[str, Any]:
        if self.event_dispatch is None:
            state = self.runtime.apply(copy.deepcopy(event))
        else:
            self.event_dispatch(copy.deepcopy(event))
            state = self.runtime.snapshot()
        self.sync()
        return state

    def snapshot(self) -> dict[str, Any]:
        return self.runtime.snapshot()

    def project(self, width: int, height: int) -> dict[str, Any]:
        return self.runtime.project(width, height).as_dict()

    def close(self) -> None:
        close = getattr(self.window, "close", None)
        if callable(close):
            close()

    @staticmethod
    def _component_refusal(code: str, detail: str) -> None:
        raise NativeRealizerRefusal(code, detail)

    def _build(self) -> None:
        missing = sorted(set(self.items) - set(self.layout))
        if missing:
            raise NativeRealizerRefusal("NATIVE_LAYOUT_MISSING", ",".join(missing))
        for key, item in self.items.items():
            kind = item["kind"]
            if kind == "WINDOW":
                continue
            rect, props, node_id = self.layout[key], item.get("props", {}), str(item["node_id"])
            value = self.runtime.state["values"].get(key, props.get("default"))
            handler = self.handlers.get(kind)
            if handler is None or handler.build is None:
                raise NativeRealizerRefusal("NATIVE_KIND_REFUSED", f"{kind}:{node_id}")
            handler.build(self, item, key, rect, value)
            focusable = bool(item.get("semantics", {}).get("focusable"))
            self.window.set_focusable(key, focusable)
            if focusable:
                self.window.bind_focus(
                    key, lambda node_id=node_id: self._apply({"intent": "FOCUS", "node_id": node_id}),
                )
            semantics = item["semantics"]
            self.window.set_accessibility(
                key, name=str(semantics["name"]), description=str(semantics.get("description", "")),
                value=handler.accessible_value(value, props), default_action=handler.default_action,
            )

    def _relayout(self, width: int, height: int) -> None:
        plan = self.runtime.layout_plan(width, height)
        missing = sorted(set(self.items) - set(plan))
        if missing:
            raise NativeRealizerRefusal("NATIVE_LAYOUT_MISSING", ",".join(missing))
        self.layout = plan
        for key, item in self.items.items():
            if item["kind"] != "WINDOW":
                self.window.move(key, plan[key])

    def sync(self) -> None:
        visible = {item["props"]["realization_key"] for item in self.runtime.visible_nodes()}
        visibility = {key: key in visible for key, item in self.items.items() if item["kind"] != "WINDOW"}
        if visibility:
            self.window.set_visibility(visibility)
        for key, item in self.items.items():
            if item["kind"] == "WINDOW" or key not in visible:
                continue
            kind, props = item["kind"], item.get("props", {})
            value = self.runtime.state["values"].get(key, props.get("default"))
            state = self.runtime.state["states"].get(key, "IDLE")
            handler = self.handlers[kind]
            if handler.sync is not None:
                handler.sync(self, item, key, value)
            self.window.set_enabled(key, state != "DISABLED")
            semantics = item["semantics"]
            self.window.set_accessibility(
                key, name=str(semantics["name"]), description=str(semantics.get("description", "")),
                value=handler.accessible_value(value, props), default_action=handler.default_action,
            )
        focused = self.runtime.state.get("focused_node_id")
        if focused and focused in self.runtime.nodes:
            focused_key = self.runtime.nodes[focused].get("props", {}).get("realization_key")
            if focused_key in visible:
                self.window.focus(str(focused_key))

    def accessibility_witness(self) -> dict[str, Any]:
        """Compare direct HWND IAccessible observations with the semantic contract."""
        from .win32_accessibility import inspect

        visible = {item["props"]["realization_key"] for item in self.runtime.visible_nodes()}
        rows = []
        failures = []
        for key, item in self.items.items():
            if item["kind"] == "WINDOW" or key not in visible:
                continue
            observed = inspect(self.window.controls[key].hwnd)
            semantics = item["semantics"]
            expected_focusable = bool(semantics.get("focusable"))
            checks = {
                "name": observed["name"] == str(semantics["name"]),
                "description": observed["description"] == str(semantics.get("description", "")),
                "focusable": observed["tab_stop"] == expected_focusable,
                "enabled": observed["enabled"] == (self.runtime.state["states"].get(key, "IDLE") != "DISABLED"),
                "visible": observed["visible"],
                "role_present": observed["role"] != "unknown",
            }
            if not all(checks.values()):
                failures.append({"realization_key": key, "failed_checks": sorted(name for name, passed in checks.items() if not passed)})
            rows.append({
                "node_id": item["node_id"], "realization_key": key, "kind": item["kind"],
                "semantic_role": semantics["role"], "semantic_name": semantics["name"],
                "expected_focusable": expected_focusable, "observed": observed, "checks": checks,
            })
        semantic_order = [self.runtime.nodes[node_id]["props"]["realization_key"] for node_id in self.runtime.focus_order()]
        native_order = [key for key in self.window.tab_order() if key in visible]
        if native_order != semantic_order:
            failures.append({"gate": "TAB_ORDER", "expected": semantic_order, "observed": native_order})
        value = {
            "schema": "mosaic.ui.win32-accessibility-witness.v0.1",
            "bridge": "WINDOWS_IACCESSIBLE_STANDARD_HWND_PROXY",
            "rows": rows, "semantic_focus_order": semantic_order, "native_tab_order": native_order,
            "failure_count": len(failures), "failures": failures,
            "disposition": "PASS_LOCAL_CANDIDATE" if not failures else "REFUSE",
            "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
            "claim_boundary": "DIRECT_MSAA_PROXY_INSPECTION_DOES_NOT_ESTABLISH_SCREEN_READER_OR_COMPLETE_UI_AUTOMATION_BEHAVIOR",
        }
        value["commitment"] = commitment("MOSAIC.UI.WIN32_ACCESSIBILITY_WITNESS.v0.1", value)
        return value

    def witness_descriptor(self) -> dict[str, Any]:
        value = {
            "schema": "mosaic.ui.native-semantic-realization.v0.1",
            "generated_root": self.payload.get("input_root"),
            "realized_keys": sorted(self.items),
            "correspondence_commitment": self.correspondence["commitment"],
            "state_commitment": self.runtime.snapshot()["commitment"],
            "locale": self.runtime.localization.locale,
            "direction": self.runtime.localization.direction,
            "standing": "LOCAL_CANDIDATE_EVIDENCE",
            "authority_effect": "NONE",
            "claim_boundary": "DECLARATIVE_WIN32_REALIZATION_DOES_NOT_ESTABLISH_BROAD_HOST_OR_ASSISTIVE_TECHNOLOGY_BEHAVIOR",
        }
        value["commitment"] = commitment("MOSAIC.UI.NATIVE_SEMANTIC_REALIZATION.v0.1", value)
        return value

    def run(self) -> int:
        return self.window.run()


__all__ = ["NativeRealizerRefusal", "NativeSemanticUI"]

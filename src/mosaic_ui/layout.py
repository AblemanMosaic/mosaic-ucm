"""Deterministic, integer-only layout for semantic Mosaic UI trees."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .canonical import commitment
from .model import UIRefusal


Rect = tuple[int, int, int, int]
LAYOUT_SCHEMA = "mosaic.ui.layout.v0.1"
_CONTAINER_KEYS = {"type", "padding", "gap", "columns", "row_height", "align"}
_ITEM_KEYS = {"width", "height", "basis", "grow", "min_width", "min_height", "max_width", "max_height", "span"}


class LayoutRefusal(UIRefusal):
    pass


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise LayoutRefusal("LAYOUT_VALUE_REFUSED", f"{name}:{value!r}")
    return value


def _inset(rect: Rect, padding: int) -> Rect:
    x, y, width, height = rect
    if width < padding * 2 or height < padding * 2:
        raise LayoutRefusal("LAYOUT_VIEWPORT_TOO_SMALL", f"{rect}:{padding}")
    return x + padding, y + padding, width - padding * 2, height - padding * 2


def _visible_children(node: dict[str, Any], active_view: str | None) -> list[dict[str, Any]]:
    children = []
    for child in node.get("children", []):
        view = child.get("props", {}).get("view")
        if active_view is None or view is None or view == active_view:
            children.append(child)
    return children


def _closed_layout(value: Any, allowed: set[str], where: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise LayoutRefusal("LAYOUT_SPEC_REFUSED", f"{where}:not-object")
    extra = sorted(set(value) - allowed)
    if extra:
        raise LayoutRefusal("LAYOUT_SPEC_REFUSED", f"{where}:unknown:{','.join(extra)}")
    return value


def _split(total: int, specs: list[dict[str, Any]], axis: str, gap: int) -> list[int]:
    available = total - gap * max(0, len(specs) - 1)
    if available < len(specs):
        raise LayoutRefusal("LAYOUT_VIEWPORT_TOO_SMALL", f"{axis}:{total}")
    fixed: list[int | None] = []
    weight = 0
    for spec in specs:
        explicit = spec.get(axis)
        basis = spec.get("basis")
        if explicit is not None:
            fixed.append(_integer(explicit, axis, 1))
        elif basis is not None:
            fixed.append(_integer(basis, "basis", 1))
        else:
            fixed.append(None)
            weight += _integer(spec.get("grow", 1), "grow", 1)
    remainder = available - sum(item or 0 for item in fixed)
    if remainder < sum(1 for item in fixed if item is None):
        raise LayoutRefusal("LAYOUT_VIEWPORT_TOO_SMALL", f"{axis}:fixed-overflow")
    cursor = 0
    result: list[int] = []
    for index, (item, spec) in enumerate(zip(fixed, specs)):
        if item is None:
            share = remainder * _integer(spec.get("grow", 1), "grow", 1) // weight
            cursor += share
            # Give deterministic integer remainders to the final flexible item.
            if index == max(i for i, value in enumerate(fixed) if value is None):
                share += remainder - cursor
            item = share
        minimum = _integer(spec.get("min_width" if axis == "width" else "min_height", 1), "minimum", 1)
        maximum = spec.get("max_width" if axis == "width" else "max_height")
        item = max(item, minimum)
        if maximum is not None:
            item = min(item, _integer(maximum, "maximum", 1))
        result.append(item)
    if sum(result) > available:
        raise LayoutRefusal("LAYOUT_CONSTRAINTS_UNSATISFIED", f"{axis}:{sum(result)}>{available}")
    return result


def _track_sizes(total: int, columns: list[Any], gap: int) -> list[int]:
    if not columns:
        raise LayoutRefusal("LAYOUT_SPEC_REFUSED", "grid:columns-empty")
    fixed = 0
    flexible = 0
    parsed: list[tuple[str, int]] = []
    for value in columns:
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            parsed.append(("fixed", value))
            fixed += value
        elif isinstance(value, str) and value.endswith("fr") and value[:-2].isdigit() and int(value[:-2]) > 0:
            weight = int(value[:-2])
            parsed.append(("flex", weight))
            flexible += weight
        else:
            raise LayoutRefusal("LAYOUT_SPEC_REFUSED", f"grid:column:{value!r}")
    available = total - gap * (len(columns) - 1) - fixed
    if available < flexible:
        raise LayoutRefusal("LAYOUT_VIEWPORT_TOO_SMALL", "grid:columns")
    result: list[int] = []
    used = 0
    last_flex = max((i for i, item in enumerate(parsed) if item[0] == "flex"), default=-1)
    for index, (kind, amount) in enumerate(parsed):
        if kind == "fixed":
            result.append(amount)
        else:
            share = available * amount // flexible
            used += share
            if index == last_flex:
                share += available - used
            result.append(share)
    return result


def _place(node: dict[str, Any], rect: Rect, output: dict[str, Rect], active_view: str | None) -> None:
    props = node.get("props", {})
    key = props.get("realization_key")
    if key:
        if key in output:
            raise LayoutRefusal("LAYOUT_DUPLICATE_KEY", str(key))
        output[str(key)] = rect
    children = _visible_children(node, active_view)
    if not children:
        return
    spec = _closed_layout(props.get("layout"), _CONTAINER_KEYS, str(node.get("node_id")))
    kind = str(spec.get("type", "COLUMN")).upper()
    padding = _integer(spec.get("padding", 0), "padding")
    gap = _integer(spec.get("gap", 0), "gap")
    inner = _inset(rect, padding)
    item_specs = [_closed_layout(child.get("props", {}).get("layout_item"), _ITEM_KEYS, str(child.get("node_id"))) for child in children]
    if kind in {"ROW", "COLUMN"}:
        axis = "width" if kind == "ROW" else "height"
        total = inner[2] if kind == "ROW" else inner[3]
        sizes = _split(total, item_specs, axis, gap)
        cursor = inner[0] if kind == "ROW" else inner[1]
        for child, item, size in zip(children, item_specs, sizes):
            if kind == "ROW":
                height = min(inner[3], _integer(item.get("height", inner[3]), "height", 1))
                child_rect = (cursor, inner[1], size, height)
            else:
                width = min(inner[2], _integer(item.get("width", inner[2]), "width", 1))
                child_rect = (inner[0], cursor, width, size)
            _place(child, child_rect, output, active_view)
            cursor += size + gap
        return
    if kind == "GRID":
        columns = spec.get("columns", ["1fr"])
        if not isinstance(columns, list):
            raise LayoutRefusal("LAYOUT_SPEC_REFUSED", "grid:columns-not-list")
        widths = _track_sizes(inner[2], columns, gap)
        row_height = _integer(spec.get("row_height", 40), "row_height", 1)
        x_offsets = [inner[0]]
        for width in widths[:-1]:
            x_offsets.append(x_offsets[-1] + width + gap)
        column = row = 0
        for child, item in zip(children, item_specs):
            span = _integer(item.get("span", 1), "span", 1)
            if span > len(widths):
                raise LayoutRefusal("LAYOUT_SPEC_REFUSED", "grid:span")
            if column + span > len(widths):
                row += 1
                column = 0
            width = sum(widths[column:column + span]) + gap * (span - 1)
            child_rect = (x_offsets[column], inner[1] + row * (row_height + gap), width, row_height)
            if child_rect[1] + child_rect[3] > inner[1] + inner[3]:
                raise LayoutRefusal("LAYOUT_VIEWPORT_TOO_SMALL", "grid:rows")
            _place(child, child_rect, output, active_view)
            column += span
            if column == len(widths):
                row += 1
                column = 0
        return
    raise LayoutRefusal("LAYOUT_TYPE_REFUSED", kind)


def layout_tree(tree: dict[str, Any], width: int, height: int, *, active_view: str | None = None) -> dict[str, Rect]:
    """Compile a tree into stable integer rectangles without host measurement APIs."""
    width = _integer(width, "viewport.width", 1)
    height = _integer(height, "viewport.height", 1)
    output: dict[str, Rect] = {}
    _place(tree, (0, 0, width, height), output, active_view)
    return output


@dataclass(frozen=True)
class LayoutWitness:
    viewport: dict[str, int]
    nodes: tuple[dict[str, Any], ...]
    active_view: str | None

    def as_dict(self) -> dict[str, Any]:
        value = {
            "schema": "mosaic.ui.layout-witness.v0.1",
            "layout_schema": LAYOUT_SCHEMA,
            "viewport": self.viewport,
            "active_view": self.active_view,
            "nodes": list(self.nodes),
            "determinism_basis": "INTEGER_CONSTRAINTS_NO_HOST_MEASUREMENT",
            "standing": "LOCAL_CANDIDATE_EVIDENCE",
            "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.LAYOUT_WITNESS.v0.1", value)
        return value


def witness(tree: dict[str, Any], width: int, height: int, *, active_view: str | None = None) -> dict[str, Any]:
    plan = layout_tree(tree, width, height, active_view=active_view)
    rows = tuple({"realization_key": key, "rect": list(plan[key])} for key in sorted(plan))
    return LayoutWitness({"width": width, "height": height}, rows, active_view).as_dict()


def make_layout_provider(tree: dict[str, Any], *, active_view: str | None = None):
    return lambda width, height: layout_tree(tree, width, height, active_view=active_view)


__all__ = ["LAYOUT_SCHEMA", "LayoutRefusal", "LayoutWitness", "layout_tree", "make_layout_provider", "witness"]

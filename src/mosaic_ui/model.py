from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator


STATES = ("IDLE", "HOVER", "FOCUSED", "PRESSED", "DISABLED", "PENDING", "REFUSED")
FORBIDDEN_KEYS = {"callback", "code", "script", "url", "uri", "network", "package", "command_line"}
COMPONENT_KINDS = frozenset({
    "WINDOW", "LABEL", "BUTTON", "TEXT_FIELD", "SELECT", "CHECKBOX", "SEGMENTED",
    "TAB_BAR", "PROGRESS", "STATUS", "TABLE", "PANEL", "DIALOG", "TOOLTIP",
    "BADGE", "KEY_VALUE", "STEPPER",
})
SUFFICIENCY_COMPONENT_KINDS = frozenset({
    "COMBOBOX", "DATA_GRID", "LIST", "MENU", "NAVIGATION", "NOTIFICATION",
    "RADIO_GROUP", "TREE",
})
ALL_COMPONENT_KINDS = COMPONENT_KINDS | SUFFICIENCY_COMPONENT_KINDS
RICH_DOCUMENT_COMPONENT_KINDS = frozenset({"RICH_DOCUMENT"})
SUCCESSOR_COMPONENT_KINDS = ALL_COMPONENT_KINDS | RICH_DOCUMENT_COMPONENT_KINDS


class UIRefusal(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}:{detail}")


@dataclass(frozen=True)
class Node:
    kind: str
    node_id: str
    name: str
    role: str
    children: tuple["Node", ...] = ()
    operation_ref: str | None = None
    focusable: bool = False
    props: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "kind": self.kind,
            "node_id": self.node_id,
            "semantics": {
                "role": self.role,
                "name": self.name,
                "description": str(self.props.get("description", "")),
                "focusable": self.focusable,
                "actions": ["activate"] if self.operation_ref else [],
            },
            "props": dict(self.props),
            "children": [child.as_dict() for child in self.children],
        }
        if self.operation_ref:
            value["operation_ref"] = self.operation_ref
        return value


def node(
    kind: str,
    node_id: str,
    name: str,
    *,
    role: str | None = None,
    children: Iterable[Node] = (),
    operation_ref: str | None = None,
    focusable: bool = False,
    props: dict[str, Any] | None = None,
) -> Node:
    return Node(kind, node_id, name, role or kind.lower(), tuple(children), operation_ref, focusable, props or {})


def walk(tree: dict[str, Any]) -> Iterator[dict[str, Any]]:
    yield tree
    for child in tree.get("children", []):
        yield from walk(child)


def _recursive_keys(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key).lower()
            yield from _recursive_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _recursive_keys(item)


def _semantic_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value) or (
        isinstance(value, dict) and set(value) == {"message_id"}
        and isinstance(value.get("message_id"), str) and bool(value["message_id"])
    )


def validate_tree(tree: dict[str, Any], operation_ids: set[str]) -> dict[str, Any]:
    ids: set[str] = set()
    failures: list[str] = []
    operations: set[str] = set()
    forbidden = sorted(set(_recursive_keys(tree)) & FORBIDDEN_KEYS)
    if forbidden:
        failures.append("FORBIDDEN_KEYS:" + ",".join(forbidden))
    for item in walk(tree):
        node_id = item.get("node_id")
        if not isinstance(node_id, str) or not node_id:
            failures.append("MISSING_STABLE_NODE_ID")
            continue
        if node_id in ids:
            failures.append(f"DUPLICATE_NODE_ID:{node_id}")
        ids.add(node_id)
        semantics = item.get("semantics")
        if not isinstance(semantics, dict) or not semantics.get("role") \
                or not _semantic_text(semantics.get("name")):
            failures.append(f"ACCESSIBILITY_SEMANTICS_INCOMPLETE:{node_id}")
        if not isinstance(item.get("props", {}), dict):
            failures.append(f"PROPS_NOT_OBJECT:{node_id}")
        elif item.get("kind") == "TEXT_FIELD":
            props = item.get("props", {})
            for key in ("required", "readonly", "multiline"):
                if key in props and not isinstance(props[key], bool):
                    failures.append(f"TEXT_FIELD_BOOLEAN_INVALID:{node_id}:{key}")
            minimum, maximum = props.get("min_length", 0), props.get("max_length")
            minimum_valid = not isinstance(minimum, bool) and isinstance(minimum, int) and minimum >= 0
            if not minimum_valid:
                failures.append(f"TEXT_FIELD_MIN_LENGTH_INVALID:{node_id}")
            if maximum is not None and (isinstance(maximum, bool) or not isinstance(maximum, int)
                                        or (minimum_valid and maximum < minimum)):
                failures.append(f"TEXT_FIELD_MAX_LENGTH_INVALID:{node_id}")
            default = props.get("default")
            if default is not None and not isinstance(default, str):
                failures.append(f"TEXT_FIELD_DEFAULT_INVALID:{node_id}")
        elif item.get("kind") == "RICH_DOCUMENT":
            props = item.get("props", {})
            source = props.get("default")
            if not isinstance(source, str):
                failures.append(f"RICH_DOCUMENT_SOURCE_INVALID:{node_id}")
            elif len(source.encode("utf-8")) > 2_000_000:
                failures.append(f"RICH_DOCUMENT_SOURCE_TOO_LARGE:{node_id}")
            if props.get("format", "HTML_SUBSET") not in {
                "HTML_SUBSET", "MARKDOWN", "PLAIN_TEXT",
            }:
                failures.append(f"RICH_DOCUMENT_FORMAT_INVALID:{node_id}")
            if props.get("unsupported_policy", "REPORT") != "REPORT":
                failures.append(f"RICH_DOCUMENT_UNSUPPORTED_POLICY_INVALID:{node_id}")
            if props.get("source_status", "UNKNOWN") not in {
                "EXACT_SOURCE", "LOCAL_PROPOSAL", "UNSAVED_PREVIEW", "UNKNOWN",
            }:
                failures.append(f"RICH_DOCUMENT_SOURCE_STATUS_INVALID:{node_id}")
            if item.get("operation_ref") is not None:
                failures.append(f"RICH_DOCUMENT_OPERATION_REFUSED:{node_id}")
        operation = item.get("operation_ref")
        if operation is not None:
            operations.add(str(operation))
            if operation not in operation_ids:
                failures.append(f"UNKNOWN_OPERATION_REFERENCE:{node_id}:{operation}")
    if failures:
        raise UIRefusal("SEMANTIC_TREE_VALIDATION_REFUSED", ";".join(sorted(failures)))
    return {
        "schema": "mosaic.ui.semantic-tree-validation.v0.1",
        "node_count": len(ids),
        "node_ids": sorted(ids),
        "operation_references": sorted(operations),
        "states": list(STATES),
        "disposition": "PASS_LOCAL_CANDIDATE",
        "authority_effect": "NONE",
    }

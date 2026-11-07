"""Governed semantic-tree authoring operations and deterministic node diagnostics."""
from __future__ import annotations

import copy
from typing import Any, Iterator

from .canonical import commitment
from .model import UIRefusal, walk


AUTHORING_SCHEMA = "mosaic.ui.authoring.v0.1"
ADDABLE_KINDS = ("PANEL", "LABEL", "BUTTON", "TEXT_FIELD", "STATUS", "NOTIFICATION")
MUTATIONS = ("ADD_CHILD", "DUPLICATE", "DELETE", "MOVE_UP", "MOVE_DOWN")
PROTECTED_NODE_IDS = frozenset({"signature.entry"})


def _node_ids(tree: dict[str, Any]) -> set[str]:
    return {str(node["node_id"]) for node in walk(tree)}


def _unique_id(ids: set[str], base: str) -> str:
    normalized = "".join(character if character.isalnum() or character in ".-_" else "-" for character in base)
    candidate = normalized
    index = 2
    while candidate in ids:
        candidate = f"{normalized}-{index}"
        index += 1
    ids.add(candidate)
    return candidate


def _locate(tree: dict[str, Any], node_id: str) -> tuple[dict[str, Any], dict[str, Any] | None, int]:
    def descend(node: dict[str, Any], parent: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any] | None, int] | None:
        if node.get("node_id") == node_id:
            return node, parent, -1 if parent is None else parent.get("children", []).index(node)
        for child in node.get("children", []):
            found = descend(child, node)
            if found is not None:
                return found
        return None

    located = descend(tree, None)
    if located is None:
        raise UIRefusal("AUTHORING_NODE_REFUSED", node_id)
    return located


def _default_node(kind: str, node_id: str, name: str) -> dict[str, Any]:
    if kind not in ADDABLE_KINDS:
        raise UIRefusal("AUTHORING_KIND_REFUSED", kind)
    focusable = kind in {"BUTTON", "TEXT_FIELD"}
    role = {
        "PANEL": "group", "LABEL": "heading", "BUTTON": "button", "TEXT_FIELD": "textbox",
        "STATUS": "status", "NOTIFICATION": "status",
    }[kind]
    props: dict[str, Any]
    if kind == "PANEL":
        props = {"layout": {"type": "COLUMN", "gap": 8}, "layout_item": {"height": 96}}
    else:
        props = {
            "realization_key": node_id, "view": "main", "display_text": name,
            "layout_item": {"height": 36},
        }
        if kind == "TEXT_FIELD":
            props.update({"default": "", "required": False, "readonly": False, "multiline": False})
        if kind == "NOTIFICATION":
            props["tone"] = "info"
    return {
        "kind": kind, "node_id": node_id,
        "semantics": {"role": role, "name": name, "description": "", "focusable": focusable,
                      "actions": ["select"] if focusable else []},
        "props": props, "children": [],
    }


def _clone_subtree(node: dict[str, Any], ids: set[str]) -> dict[str, Any]:
    clone = copy.deepcopy(node)

    def rewrite(item: dict[str, Any]) -> None:
        old_id = str(item["node_id"])
        new_id = _unique_id(ids, f"{old_id}.copy")
        item["node_id"] = new_id
        props = item.setdefault("props", {})
        if props.get("realization_key"):
            props["realization_key"] = new_id
        semantics = item.setdefault("semantics", {})
        semantics["name"] = f"{semantics.get('name', old_id)} copy"
        if props.get("display_text"):
            props["display_text"] = semantics["name"]
        for child in item.get("children", []):
            rewrite(child)

    rewrite(clone)
    return clone


def mutate_application(application: dict[str, Any], operation: str, node_id: str, *,
                       kind: str | None = None, name: str | None = None) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """Return a mutated application and a deterministic pre-validation operation receipt."""
    if operation not in MUTATIONS:
        raise UIRefusal("AUTHORING_OPERATION_REFUSED", operation)
    result = copy.deepcopy(application)
    tree = result.get("tree")
    if not isinstance(tree, dict):
        raise UIRefusal("AUTHORING_DOCUMENT_REFUSED", "tree")
    node, parent, index = _locate(tree, node_id)
    ids = _node_ids(tree)
    before = commitment("MOSAIC.UI.AUTHORING.APPLICATION.v0.1", application)
    selected_node_id = node_id

    if operation == "ADD_CHILD":
        container = node if node.get("kind") in {"WINDOW", "PANEL"} else parent
        if container is None:
            raise UIRefusal("AUTHORING_PARENT_REFUSED", node_id)
        selected_kind = kind or "LABEL"
        base = f"draft.{selected_kind.lower().replace('_', '-')}"
        selected_node_id = _unique_id(ids, base)
        label = (name or selected_kind.replace("_", " ").title()).strip()
        if not label:
            raise UIRefusal("AUTHORING_NAME_REFUSED", selected_node_id)
        container.setdefault("children", []).append(_default_node(selected_kind, selected_node_id, label))
    elif operation == "DUPLICATE":
        if parent is None or node_id in PROTECTED_NODE_IDS:
            raise UIRefusal("AUTHORING_PROTECTED_NODE_REFUSED", node_id)
        clone = _clone_subtree(node, ids)
        parent["children"].insert(index + 1, clone)
        selected_node_id = str(clone["node_id"])
    elif operation == "DELETE":
        if parent is None or node_id in PROTECTED_NODE_IDS:
            raise UIRefusal("AUTHORING_PROTECTED_NODE_REFUSED", node_id)
        parent["children"].pop(index)
        selected_node_id = str(parent["node_id"])
    elif operation == "MOVE_UP":
        if parent is None or node_id in PROTECTED_NODE_IDS or index <= 0:
            raise UIRefusal("AUTHORING_MOVE_REFUSED", f"{node_id}:UP")
        parent["children"][index - 1], parent["children"][index] = parent["children"][index], parent["children"][index - 1]
    elif operation == "MOVE_DOWN":
        siblings = [] if parent is None else parent.get("children", [])
        if parent is None or node_id in PROTECTED_NODE_IDS or index >= len(siblings) - 1:
            raise UIRefusal("AUTHORING_MOVE_REFUSED", f"{node_id}:DOWN")
        siblings[index + 1], siblings[index] = siblings[index], siblings[index + 1]

    receipt = {
        "schema": "mosaic.ui.authoring-operation.v0.1", "operation": operation,
        "subject_node_id": node_id, "selected_node_id": selected_node_id,
        "before_commitment": before,
        "after_commitment": commitment("MOSAIC.UI.AUTHORING.APPLICATION.v0.1", result),
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
    }
    receipt["commitment"] = commitment("MOSAIC.UI.AUTHORING_OPERATION.v0.1", receipt)
    return result, selected_node_id, receipt


def _hierarchy(tree: dict[str, Any]) -> Iterator[tuple[dict[str, Any], str | None, int, tuple[str, ...]]]:
    def descend(node: dict[str, Any], parent_id: str | None, depth: int,
                path: tuple[str, ...]) -> Iterator[tuple[dict[str, Any], str | None, int, tuple[str, ...]]]:
        node_id = str(node["node_id"])
        current = (*path, node_id)
        yield node, parent_id, depth, current
        for child in node.get("children", []):
            yield from descend(child, node_id, depth + 1, current)

    yield from descend(tree, None, 1, ())


def authoring_metadata(application: dict[str, Any], projection: dict[str, Any], *, undo_depth: int,
                       redo_depth: int, last_operation: dict[str, Any] | None = None,
                       selected_node_id: str | None = None) -> dict[str, Any]:
    geometry_ids = {str(item["node_id"]) for item in projection["geometry"]["nodes"]}
    rows = []
    for node, parent_id, depth, path in _hierarchy(application["tree"]):
        node_id = str(node["node_id"])
        props = node.get("props", {})
        realized = node_id in geometry_ids
        structural = node.get("kind") in {"WINDOW", "PANEL"} and not props.get("realization_key")
        diagnostics = ["STRUCTURAL"] if structural else (["REALIZED"] if realized else ["NOT_REALIZED"])
        if node.get("semantics", {}).get("focusable"):
            diagnostics.append("FOCUSABLE")
        if node.get("operation_ref"):
            diagnostics.append("OPERATION_BOUND")
        disposition = "STRUCTURAL" if structural else ("PASS" if realized else "ATTENTION")
        row = {
            "node_id": node_id, "parent_id": parent_id, "depth": depth, "path": list(path),
            "kind": node.get("kind"), "name": node.get("semantics", {}).get("name", node_id),
            "child_count": len(node.get("children", [])), "expanded_by_default": depth <= 2,
            "disposition": disposition, "diagnostics": diagnostics,
            "protected": parent_id is None or node_id in PROTECTED_NODE_IDS,
        }
        row["commitment"] = commitment("MOSAIC.UI.AUTHORING_NODE.v0.1", row)
        rows.append(row)
    value = {
        "schema": AUTHORING_SCHEMA, "nodes": rows, "node_count": len(rows),
        "selected_node_id": selected_node_id, "can_undo": undo_depth > 0, "can_redo": redo_depth > 0,
        "undo_depth": undo_depth, "redo_depth": redo_depth,
        "supported_mutations": list(MUTATIONS), "addable_kinds": list(ADDABLE_KINDS),
        "last_operation": copy.deepcopy(last_operation),
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
    }
    value["commitment"] = commitment("MOSAIC.UI.AUTHORING.v0.1", value)
    return value


__all__ = [
    "ADDABLE_KINDS", "AUTHORING_SCHEMA", "MUTATIONS", "authoring_metadata", "mutate_application",
]

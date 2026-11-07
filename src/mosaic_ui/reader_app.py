"""Minimal governed application shell for Mosaic Reader.

This layer accepts already-supplied source text. It does not discover files, open
links, load referenced assets, or grant document content any execution authority.
"""
from __future__ import annotations

import copy
from typing import Any, Callable

from mosaic_ui_std import THEMES_DIR, load_theme
from mosaic_ui_std.catalog import load_rich_document_catalog

from .browser_realizer import BrowserRealizer
from .canonical import commitment
from .document_model import DocumentIR, import_document
from .headless import HeadlessUI
from .model import UIRefusal
from .native_realizer import NativeSemanticUI


DEFAULT_SIZE = (960, 720)


def _semantics(role: str, name: str, *, focusable: bool = False) -> dict[str, Any]:
    return {
        "role": role,
        "name": name,
        "description": "",
        "focusable": focusable,
        "actions": [],
    }


def reader_layout(width: int, height: int) -> dict[str, tuple[int, int, int, int]]:
    """Return a deterministic, bounded flow layout for the source-supplied reader."""
    if width < 480 or height < 320:
        raise UIRefusal("READER_VIEWPORT_REFUSED", f"{width}x{height}")
    margin = 24
    status_height = 30
    header_height = 68
    content_top = margin + header_height
    content_height = height - content_top - status_height - (margin * 2)
    return {
        "reader.title": (margin, margin, max(200, width - 320), 34),
        "reader.format": (width - 260, margin + 2, 236, 28),
        "reader.document": (margin, content_top, width - (margin * 2), content_height),
        "reader.status": (margin, height - margin - status_height, width - (margin * 2), status_height),
    }


def reader_payload(
    source: str | None,
    source_format: str,
    *,
    title: str = "Mosaic Reader",
    theme_id: str = "operations-dark",
) -> tuple[dict[str, Any], DocumentIR]:
    """Build a validated semantic payload while retaining exact source text."""
    document = import_document(source, source_format)
    theme = load_theme(THEMES_DIR / f"{theme_id}.json")
    tree = {
        "kind": "WINDOW",
        "node_id": "reader.window",
        "semantics": _semantics("window", title),
        "props": {
            "layout_provider": "mosaic.reader.flow.v0.1",
            "theme": theme_id,
        },
        "children": [
            {
                "kind": "PANEL",
                "node_id": "reader.entry",
                "semantics": _semantics("group", "Reader main view"),
                "props": {"target_view": "main"},
                "operation_ref": "ENTER_MAIN",
                "children": [],
            },
            {
                "kind": "LABEL",
                "node_id": "reader.title",
                "semantics": _semantics("heading", title),
                "props": {
                    "realization_key": "reader.title",
                    "view": "main",
                    "display_text": title,
                    "style": "title",
                },
                "children": [],
            },
            {
                "kind": "BADGE",
                "node_id": "reader.format",
                "semantics": _semantics("status", f"{source_format} source"),
                "props": {
                    "realization_key": "reader.format",
                    "view": "main",
                    "display_text": source_format,
                    "tone": "accent",
                },
                "children": [],
            },
            {
                "kind": "RICH_DOCUMENT",
                "node_id": "reader.document",
                "semantics": _semantics("document", title, focusable=True),
                "props": {
                    "realization_key": "reader.document",
                    "view": "main",
                    "default": document.source,
                    "format": document.source_format,
                    "source_status": "EXACT_SOURCE",
                    "unsupported_policy": "REPORT",
                },
                "children": [],
            },
            {
                "kind": "STATUS",
                "node_id": "reader.status",
                "semantics": _semantics("status", "Inert local projection"),
                "props": {
                    "realization_key": "reader.status",
                    "view": "main",
                    "display_text": "Inert projection · links require separate host admission",
                    "style": "quiet",
                },
                "children": [],
            },
        ],
    }
    application = {
        "application_id": "MOSAIC-READER-SOURCE-SUPPLIED",
        "declared_operation_ids": ["ENTER_MAIN"],
        "lifecycle": {
            "schema": "mosaic.ui.std.lifecycle-binding.v0.1",
            "initial_view": "main",
            "operation_controls": {"cancel_key": None, "progress_key": None},
            "operation_classes": {
                "NAVIGATE": ["ENTER_MAIN"], "LONG_RUNNING": [], "CANCEL": [],
                "TOGGLE_DISCLOSURE": [], "HOST_WITHHELD": [],
            },
            "status_templates": {
                "initial": "Ready",
                "queued": "{operation_phrase} queued",
                "progress": "{stage_phrase} {percent} {mm}:{ss}",
                "terminal": "{operation} {terminal} {message}",
                "cancelled": "{operation} cancelled",
            },
            "progress_default_stage": "working",
        },
        "tree": tree,
        "authority_effect": "NONE",
    }
    input_root = commitment("MOSAIC.READER.SOURCE_SUPPLIED.v0.1", {
        "application": application,
        "document_root": document.document_root,
        "theme": theme,
    })
    payload = {
        "input_root": input_root,
        "application": application,
        "library": {"tokens": theme["tokens"]},
        "reader": {
            "source_root": document.source_root,
            "document_root": document.document_root,
            "source_format": document.source_format,
            "authority_effect": "NONE",
            "execution_authority": False,
            "network_requests": [],
        },
        "authority_effect": "NONE",
    }
    return payload, document


def create_headless_reader(
    source: str | None,
    source_format: str,
    *,
    title: str = "Mosaic Reader",
) -> HeadlessUI:
    payload, _ = reader_payload(source, source_format, title=title)
    return HeadlessUI(
        payload,
        reader_layout,
        catalog=load_rich_document_catalog(),
    )


def create_native_reader(
    source: str | None,
    source_format: str,
    *,
    title: str = "Mosaic Reader",
    width: int = DEFAULT_SIZE[0],
    height: int = DEFAULT_SIZE[1],
    window_factory: Callable[..., Any] | None = None,
) -> NativeSemanticUI:
    payload, _ = reader_payload(source, source_format, title=title)
    return NativeSemanticUI(
        payload,
        reader_layout,
        width=width,
        height=height,
        title=title,
        window_factory=window_factory,
        catalog=load_rich_document_catalog(),
    )


def create_browser_reader(*args, **kwargs) -> BrowserRealizer:
    """Refuse the browser pathway until it has its own bounded qualification."""
    del args, kwargs
    raise UIRefusal(
        "READER_BROWSER_REALIZER_REFUSED",
        "RICH_DOCUMENT_BROWSER_REALIZATION_NOT_QUALIFIED",
    )


def headless_reader_witness(
    source: str | None,
    source_format: str,
    *,
    title: str = "Mosaic Reader",
    width: int = DEFAULT_SIZE[0],
    height: int = DEFAULT_SIZE[1],
) -> dict[str, Any]:
    runtime = create_headless_reader(source, source_format, title=title)
    projection = runtime.project(width, height).as_dict()
    value = {
        "schema": "mosaic.reader.headless-witness.v0.1",
        "input_root": runtime.source_payload["input_root"],
        "reader": copy.deepcopy(runtime.source_payload["reader"]),
        "viewport": {"width": width, "height": height},
        "projection": projection,
        "authority_effect": "NONE",
    }
    value["witness_root"] = commitment("MOSAIC.READER.HEADLESS_WITNESS.v0.1", value)
    return value


__all__ = [
    "DEFAULT_SIZE", "create_browser_reader", "create_headless_reader",
    "create_native_reader", "headless_reader_witness", "reader_layout",
    "reader_payload",
]

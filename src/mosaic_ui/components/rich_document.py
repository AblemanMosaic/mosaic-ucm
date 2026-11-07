from __future__ import annotations

from .base import ComponentHandler
from mosaic_ui.rich_document import project_rich_document


def _project(value, props):
    return project_rich_document(str(value or ""), str(props.get("format", "HTML_SUBSET")))


def text(value, props):
    return _project(value, props).plain_text


def build(owner, item, key, rect, value):
    projection = _project(value, item.get("props", {}))
    owner.window.rich_document(key, projection.plain_text, rect)
    owner.window.set_rich_document(key, projection.plain_text, projection.spans)


def sync(owner, item, key, value):
    projection = _project(value, item.get("props", {}))
    owner.window.set_rich_document(key, projection.plain_text, projection.spans)


HANDLER = ComponentHandler(
    "RICH_DOCUMENT",
    draw_fill="field",
    default_action="",
    interaction_intent=None,
    build=build,
    sync=sync,
    accessible_value=text,
    projection_text=text,
)

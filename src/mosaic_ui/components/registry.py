from __future__ import annotations

import importlib
from typing import Any

from mosaic_ui.model import UIRefusal

from .base import ComponentHandler


def module_name(kind: str) -> str:
    return kind.lower()


def load_handlers(catalog: dict[str, Any]) -> dict[str, ComponentHandler]:
    handlers: dict[str, ComponentHandler] = {}
    for component in catalog["components"]:
        kind = str(component["kind"])
        try:
            module = importlib.import_module(f"{__package__}.{module_name(kind)}")
        except ModuleNotFoundError as exc:
            if exc.name == f"{__package__}.{module_name(kind)}":
                raise UIRefusal("COMPONENT_HANDLER_ABSENT", kind) from exc
            raise
        handler = getattr(module, "HANDLER", None)
        if not isinstance(handler, ComponentHandler) or handler.kind != kind:
            raise UIRefusal("COMPONENT_HANDLER_INVALID", kind)
        handlers[kind] = handler
    return handlers

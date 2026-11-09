"""Attach a v0.2 theme to an application payload (library L2b, ruling L2b-R1)."""
from __future__ import annotations

import copy
from typing import Any

from .foundry import validate_library_theme_v02


def attach_theme_v02(payload: dict[str, Any], theme_id: str) -> dict[str, Any]:
    """Copy of the payload whose library carries the v0.2 theme and, as `tokens`, its exact v0.1 projection."""
    from mosaic_ui_std.theme_v02 import THEMES_V02_DIR, load_theme_v02, project_to_v01
    theme = load_theme_v02(THEMES_V02_DIR / f"{theme_id}.json")
    value = copy.deepcopy(payload)
    value["library"]["tokens"] = project_to_v01(theme)["tokens"]
    value["library"]["theme_v02"] = theme
    validate_library_theme_v02(value["library"])
    return value

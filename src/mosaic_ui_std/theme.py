"""Injectable theme files and composition into a foundry component library.

The theme schema is closed over exactly the token keys declared in r012
(component-library.json). Realizers read some keys dynamically (win32.py:1318,
badge tones), so no smaller required subset is provably safe: a theme may change
values, never the key set.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from mosaic_ui.canonical import commitment, read_json
from mosaic_ui.model import UIRefusal

THEME_SCHEMA = "mosaic.ui.std.theme.v0.1"
THEME_KEYS = {"schema", "theme_id", "tokens", "standing", "authority_effect"}
TOKEN_GROUPS = {"colors", "radii", "spacing", "typography"}
COLOR_KEYS = {
    "accent", "accent_hover", "border", "canvas", "field", "focus", "info", "pending", "refused",
    "selection", "surface", "surface_hover", "surface_raised", "text", "text_quiet",
}
RADII_KEYS = {"none", "sm", "md"}
SPACING_KEYS = {"xs", "sm", "md", "lg", "xl"}
TYPOGRAPHY_KEYS = {"roles", "unit"}
TYPOGRAPHY_UNIT = "logical_px_character_height"
ROLE_KEYS = {"body", "heading", "metric", "mono", "title"}
ROLE_FIELDS = {"family", "size", "weight"}
HEX = re.compile(r"#[0-9a-f]{6}")
THEMES_DIR = Path(__file__).resolve().parent / "themes"


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _closed(failures: list[str], where: str, value: Any, keys: set[str]) -> bool:
    if not isinstance(value, dict):
        failures.append(f"NOT_OBJECT:{where}")
        return False
    if set(value) != keys:
        failures.append(f"KEYS_MISMATCH:{where}:" + ",".join(sorted(set(value) ^ keys)))
        return False
    return True


def validate_theme(theme: Any) -> dict[str, Any]:
    failures: list[str] = []
    if _closed(failures, "theme", theme, THEME_KEYS):
        if theme["schema"] != THEME_SCHEMA:
            failures.append("SCHEMA_MISMATCH")
        if not isinstance(theme["theme_id"], str) or not theme["theme_id"]:
            failures.append("THEME_ID_INVALID")
        if theme["authority_effect"] != "NONE":
            failures.append("AUTHORITY_EFFECT_NOT_NONE")
        tokens = theme["tokens"]
        if _closed(failures, "tokens", tokens, TOKEN_GROUPS):
            if _closed(failures, "colors", tokens["colors"], COLOR_KEYS):
                for key in sorted(COLOR_KEYS):
                    value = tokens["colors"][key]
                    if not isinstance(value, str) or not HEX.fullmatch(value):
                        failures.append(f"COLOR_INVALID:{key}")
            for group, keys in (("radii", RADII_KEYS), ("spacing", SPACING_KEYS)):
                if _closed(failures, group, tokens[group], keys):
                    for key in sorted(keys):
                        if not _is_int(tokens[group][key]) or tokens[group][key] < 0:
                            failures.append(f"SIZE_INVALID:{group}.{key}")
            typography = tokens["typography"]
            if _closed(failures, "typography", typography, TYPOGRAPHY_KEYS):
                if typography["unit"] != TYPOGRAPHY_UNIT:
                    failures.append("TYPOGRAPHY_UNIT_MISMATCH")
                if _closed(failures, "typography.roles", typography["roles"], ROLE_KEYS):
                    for role in sorted(ROLE_KEYS):
                        spec = typography["roles"][role]
                        if not _closed(failures, f"role.{role}", spec, ROLE_FIELDS):
                            continue
                        if not isinstance(spec["family"], str) or not spec["family"]:
                            failures.append(f"ROLE_FAMILY_INVALID:{role}")
                        if not _is_int(spec["size"]) or spec["size"] <= 0:
                            failures.append(f"ROLE_SIZE_INVALID:{role}")
                        if not _is_int(spec["weight"]) or not 1 <= spec["weight"] <= 1000:
                            failures.append(f"ROLE_WEIGHT_INVALID:{role}")
    if failures:
        raise UIRefusal("THEME_REFUSED", ";".join(sorted(failures)))
    return {
        "schema": "mosaic.ui.std.theme-validation.v0.1",
        "theme_id": theme["theme_id"],
        "theme_root": commitment("MOSAIC.UI.STD.THEME.v0.1", theme),
        "disposition": "PASS_LOCAL_CANDIDATE",
        "authority_effect": "NONE",
    }


def validate_tokens(tokens: Any) -> None:
    """Validate a bare token set (as carried in a generated library payload) under the theme schema."""
    validate_theme({"schema": THEME_SCHEMA, "theme_id": "TOKENS", "tokens": tokens,
                    "standing": "LOCAL_CANDIDATE", "authority_effect": "NONE"})


def load_theme(path: Path) -> dict[str, Any]:
    theme = read_json(path)
    validate_theme(theme)
    return theme


def compose_component_library(catalog: dict[str, Any], theme: dict[str, Any], library_id: str) -> dict[str, Any]:
    """Compose a foundry component-library document (mosaic.ui.component-library.v0.1).

    Tier data and evidence stay in the catalog; they are not emitted into the library,
    so composition cannot perturb generated_root.
    """
    from mosaic_ui.foundry import validate_component_library
    from .catalog import validate_catalog

    validate_catalog(catalog)
    validate_theme(theme)
    if not isinstance(library_id, str) or not library_id:
        raise UIRefusal("LIBRARY_ID_INVALID", repr(library_id))
    library = {
        "authority_effect": "NONE",
        "components": [{"component_id": c["component_id"], "kind": c["kind"]} for c in catalog["components"]],
        "library_id": library_id,
        "schema": "mosaic.ui.component-library.v0.1",
        "standing": "LOCAL_CANDIDATE",
        "states": list(catalog["states"]),
        "tokens": theme["tokens"],
    }
    validate_component_library(library)
    return library

"""Governed Mosaic Signature Profile, theme, and density composition."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from mosaic_ui.canonical import commitment, read_json
from mosaic_ui.model import ALL_COMPONENT_KINDS, UIRefusal

from .theme import THEMES_DIR, load_theme, validate_theme


PROFILE_SCHEMA = "mosaic.ui.signature-profile.v0.1"
DENSITY_SCHEMA = "mosaic.ui.density.v0.1"
PROFILES_DIR = Path(__file__).resolve().parent / "profiles"
DENSITIES_DIR = Path(__file__).resolve().parent / "densities"
PROFILE_KEYS = {
    "schema", "profile_id", "profile_version", "component_kinds", "themes", "densities",
    "default_theme", "default_density", "compositions", "quality_contract", "standing", "authority_effect",
}
DENSITY_KEYS = {
    "schema", "density_id", "spacing", "typography_sizes", "control_height",
    "standing", "authority_effect",
}
SPACING_KEYS = {"xs", "sm", "md", "lg", "xl"}
ROLE_KEYS = {"body", "heading", "metric", "mono", "title"}


def _closed(value: Any, keys: set[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise UIRefusal(code, "KEYS_MISMATCH")
    return value


def validate_density(value: Any) -> dict[str, Any]:
    density = _closed(value, DENSITY_KEYS, "DENSITY_REFUSED")
    if density["schema"] != DENSITY_SCHEMA or density["authority_effect"] != "NONE" \
            or not isinstance(density["density_id"], str) or not density["density_id"]:
        raise UIRefusal("DENSITY_REFUSED", "IDENTITY_OR_AUTHORITY")
    spacing = _closed(density["spacing"], SPACING_KEYS, "DENSITY_REFUSED")
    sizes = _closed(density["typography_sizes"], ROLE_KEYS, "DENSITY_REFUSED")
    if not all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in spacing.values()) \
            or not all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in sizes.values()) \
            or not isinstance(density["control_height"], int) or isinstance(density["control_height"], bool) \
            or not 24 <= density["control_height"] <= 64:
        raise UIRefusal("DENSITY_REFUSED", "VALUE")
    result = {
        "schema": "mosaic.ui.density-validation.v0.1", "density_id": density["density_id"],
        "density_root": commitment("MOSAIC.UI.DENSITY.v0.1", density),
        "disposition": "PASS_LOCAL_CANDIDATE", "authority_effect": "NONE",
    }
    return result


def load_density(density_id: str) -> dict[str, Any]:
    if not isinstance(density_id, str) or not density_id or Path(density_id).name != density_id:
        raise UIRefusal("DENSITY_REFUSED", "IDENTIFIER")
    value = read_json(DENSITIES_DIR / f"{density_id}.json")
    validate_density(value)
    return value


def validate_signature_profile(value: Any) -> dict[str, Any]:
    profile = _closed(value, PROFILE_KEYS, "SIGNATURE_PROFILE_REFUSED")
    if profile["schema"] != PROFILE_SCHEMA or profile["authority_effect"] != "NONE" \
            or not isinstance(profile["profile_id"], str) or not profile["profile_id"] \
            or not isinstance(profile["profile_version"], str) or not profile["profile_version"]:
        raise UIRefusal("SIGNATURE_PROFILE_REFUSED", "IDENTITY_OR_AUTHORITY")
    kinds, themes, densities = profile["component_kinds"], profile["themes"], profile["densities"]
    if not isinstance(kinds, list) or kinds != sorted(set(kinds)) or not set(kinds) <= set(ALL_COMPONENT_KINDS) \
            or not isinstance(themes, list) or themes != sorted(set(themes)) or not themes \
            or not isinstance(densities, list) or densities != sorted(set(densities)) or not densities \
            or profile["default_theme"] not in themes or profile["default_density"] not in densities:
        raise UIRefusal("SIGNATURE_PROFILE_REFUSED", "SCOPE")
    compositions = profile["compositions"]
    composition_keys = {"composition_id", "name", "purpose", "required_kinds"}
    if not isinstance(compositions, list) or not compositions:
        raise UIRefusal("SIGNATURE_PROFILE_REFUSED", "COMPOSITIONS")
    identifiers: list[str] = []
    for composition in compositions:
        _closed(composition, composition_keys, "SIGNATURE_PROFILE_REFUSED")
        required = composition["required_kinds"]
        if not isinstance(composition["composition_id"], str) or not composition["composition_id"] \
                or not isinstance(composition["name"], str) or not composition["name"] \
                or not isinstance(composition["purpose"], str) or not composition["purpose"] \
                or not isinstance(required, list) or required != sorted(set(required)) or not set(required) <= set(kinds):
            raise UIRefusal("SIGNATURE_PROFILE_REFUSED", "COMPOSITION_SCOPE")
        identifiers.append(composition["composition_id"])
    quality = profile["quality_contract"]
    quality_keys = {"max_radius", "letter_spacing", "minimum_text_contrast", "nested_cards", "responsive_viewports"}
    _closed(quality, quality_keys, "SIGNATURE_PROFILE_REFUSED")
    if len(set(identifiers)) != len(identifiers) or quality != {
        "letter_spacing": 0, "max_radius": 8, "minimum_text_contrast": 4.5,
        "nested_cards": False, "responsive_viewports": [640, 1280],
    }:
        raise UIRefusal("SIGNATURE_PROFILE_REFUSED", "QUALITY_CONTRACT")
    for theme_id in themes:
        load_theme(THEMES_DIR / f"{theme_id}.json")
    for density_id in densities:
        load_density(density_id)
    result = {
        "schema": "mosaic.ui.signature-profile-validation.v0.1",
        "profile_id": profile["profile_id"], "component_count": len(kinds),
        "composition_count": len(compositions),
        "profile_root": commitment("MOSAIC.UI.SIGNATURE_PROFILE.v0.1", profile),
        "disposition": "PASS_LOCAL_CANDIDATE", "authority_effect": "NONE",
    }
    return result


def load_signature_profile() -> dict[str, Any]:
    value = read_json(PROFILES_DIR / "mosaic-signature.json")
    validate_signature_profile(value)
    return value


def resolve_signature_theme(theme_id: str, density_id: str) -> dict[str, Any]:
    profile = load_signature_profile()
    if theme_id not in profile["themes"] or density_id not in profile["densities"]:
        raise UIRefusal("SIGNATURE_SELECTION_REFUSED", f"{theme_id}:{density_id}")
    theme, density = load_theme(THEMES_DIR / f"{theme_id}.json"), load_density(density_id)
    resolved = copy.deepcopy(theme)
    resolved["theme_id"] = f"{theme['theme_id']}@{density['density_id'].upper()}"
    resolved["tokens"]["spacing"] = copy.deepcopy(density["spacing"])
    for role, size in density["typography_sizes"].items():
        resolved["tokens"]["typography"]["roles"][role]["size"] = size
    validate_theme(resolved)
    value = {
        "schema": "mosaic.ui.signature-theme-resolution.v0.1",
        "profile_id": profile["profile_id"], "theme_id": theme_id, "density_id": density_id,
        "control_height": density["control_height"], "tokens": resolved["tokens"],
        "theme_root": commitment("MOSAIC.UI.STD.THEME.v0.1", resolved),
        "density_root": commitment("MOSAIC.UI.DENSITY.v0.1", density),
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
    }
    value["commitment"] = commitment("MOSAIC.UI.SIGNATURE_THEME_RESOLUTION.v0.1", value)
    return value


__all__ = [
    "DENSITIES_DIR", "PROFILES_DIR", "load_density", "load_signature_profile",
    "resolve_signature_theme", "validate_density", "validate_signature_profile",
]

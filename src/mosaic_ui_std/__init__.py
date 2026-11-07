"""Mosaic UI standard library: catalog, themes, lifecycle, and realization tiers."""
from .catalog import (
    DECLARED_ONLY, DEFAULT_CATALOG, REALIZERS, RUNTIME_REALIZERS, check_realizable, load_catalog,
    load_runtime_catalog, require_realized, tiers, validate_catalog,
)
from .lifecycle import LIFECYCLE_SCHEMA, render, validate_lifecycle
from .theme import THEMES_DIR, compose_component_library, load_theme, validate_theme, validate_tokens
from .signature import (
    DENSITIES_DIR, PROFILES_DIR, load_density, load_signature_profile, resolve_signature_theme,
    validate_density, validate_signature_profile,
)
from .visual_profile import (
    VISUAL_PROFILE_PATH, load_signature_visual_profile, signature_visual_witness,
    validate_signature_visual_profile,
)
from .theme_v02 import (
    FONTS_DIR, THEMES_V02_DIR, list_themes_v02, load_font_registry, load_theme_v02,
    project_to_v01, theme_v02_commitment, validate_theme_v02, verify_font_assets,
)

__all__ = [
    "DECLARED_ONLY", "DEFAULT_CATALOG", "LIFECYCLE_SCHEMA", "REALIZERS", "THEMES_DIR", "check_realizable",
    "RUNTIME_REALIZERS", "DENSITIES_DIR", "PROFILES_DIR", "compose_component_library", "load_catalog",
    "load_density", "load_runtime_catalog", "load_signature_profile", "load_theme", "render",
    "require_realized", "resolve_signature_theme", "tiers", "validate_catalog", "validate_density",
    "validate_lifecycle", "validate_signature_profile", "validate_theme", "validate_tokens",
    "VISUAL_PROFILE_PATH", "load_signature_visual_profile", "signature_visual_witness",
    "validate_signature_visual_profile",
    "FONTS_DIR", "THEMES_V02_DIR", "list_themes_v02", "load_font_registry", "load_theme_v02",
    "project_to_v01", "theme_v02_commitment", "validate_theme_v02", "verify_font_assets",
]
__version__ = "0.1.0"

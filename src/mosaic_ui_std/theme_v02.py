"""Theme schema v0.2 (library L1): owned typography, explicit roles, and enforced contrast guardrails.

v0.2 lives alongside the frozen v0.1 schema (ruling RL-3). v0.1 files, validator, and commitments are untouched.
`project_to_v01` returns a v0.1-shaped theme that passes the unchanged v0.1 validator, so every existing
realizer renders a v0.2 theme without code change (ruling L1-R1: native consumption of fonts, elevation and
motion arrives with the L2 pack format).
"""
from __future__ import annotations

import colorsys
import hashlib
import re
from pathlib import Path
from typing import Any

from mosaic_ui.canonical import commitment, read_json
from mosaic_ui.model import UIRefusal

from .theme import validate_theme

THEME_V02_SCHEMA = "mosaic.ui.std.theme.v0.2"
THEMES_V02_DIR = Path(__file__).resolve().parent / "themes_v02"
FONTS_DIR = Path(__file__).resolve().parent / "fonts"
PROFILE_PATH = Path(__file__).resolve().parent / "profiles" / "mosaic-signature.json"

THEME_KEYS = {"schema", "theme_id", "label", "scheme", "provenance", "tokens", "standing", "authority_effect"}
TOKEN_GROUPS = {"colors", "radii", "spacing", "elevation", "motion", "typography", "guardrails"}
SURFACES = ("canvas", "surface", "surface_raised", "surface_hover", "field", "selection")
TEXT_ROLES = ("text", "text_quiet", "accent", "success", "info", "pending", "refused")
COLOR_KEYS = set(SURFACES) | set(TEXT_ROLES) | {"border", "border_strong", "accent_hover", "on_accent", "on_refused", "focus"}
RADII_KEYS = {"none", "sm", "md", "lg"}
SPACING_KEYS = {"xs", "sm", "md", "lg", "xl"}
ELEVATION_KEYS = {"flat", "raised", "overlay"}
SHADOW_KEYS = {"y", "blur", "alpha"}
MOTION_KEYS = {"short_ms", "medium_ms", "easing", "reduced_motion"}
TYPOGRAPHY_KEYS = {"roles", "unit"}
ROLE_KEYS = {"body", "heading", "metric", "mono", "title"}
ROLE_FIELDS = {"font", "size", "weight"}
GUARDRAIL_KEYS = {"minimum_text_contrast", "extra_pairs"}
HEX = re.compile(r"^#[0-9a-f]{6}$")
STATUS_ROLES = ("success", "info", "pending", "refused")
STATUS_MIN_SATURATION, STATUS_LIGHTNESS = 0.2, (0.08, 0.92)

# Mandatory guardrails (rulings L1-R2, L1-R5). A theme may add pairs; it can never remove or weaken these.
MANDATORY_TEXT_PAIRS = tuple((fg, bg) for fg in TEXT_ROLES for bg in SURFACES)
MANDATORY_FILL_PAIRS = (("on_accent", "accent"), ("on_refused", "refused"))
FOCUS_PAIRS = (("focus", "canvas"), ("focus", "surface"))
MIN_TEXT_CONTRAST = 4.5
MIN_FOCUS_CONTRAST = 3.0


def _luminance(value: str) -> float:
    channels = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


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


def load_font_registry() -> dict[str, Any]:
    return read_json(FONTS_DIR / "registry.json")


def _max_radius() -> int:
    return int(read_json(PROFILE_PATH)["quality_contract"]["max_radius"])


def validate_theme_v02(theme: Any, *, fonts: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate a v0.2 theme. Refuses with every failing rule listed, never only the first."""
    failures: list[str] = []
    registry = (fonts or load_font_registry())["fonts"]
    if _closed(failures, "theme", theme, THEME_KEYS):
        if theme["schema"] != THEME_V02_SCHEMA:
            failures.append("SCHEMA_MISMATCH")
        for key in ("theme_id", "label", "provenance"):
            if not isinstance(theme[key], str) or not theme[key]:
                failures.append(f"FIELD_INVALID:{key}")
        if theme["scheme"] not in ("dark", "light"):
            failures.append("SCHEME_INVALID")
        if theme["authority_effect"] != "NONE":
            failures.append("AUTHORITY_EFFECT_NOT_NONE")
        tokens = theme["tokens"]
        if _closed(failures, "tokens", tokens, TOKEN_GROUPS):
            colors = tokens["colors"]
            colors_ok = _closed(failures, "colors", colors, COLOR_KEYS)
            if colors_ok:
                for key in sorted(COLOR_KEYS):
                    if not isinstance(colors[key], str) or not HEX.match(colors[key]):
                        failures.append(f"COLOR_INVALID:{key}")
                        colors_ok = False
            if _closed(failures, "radii", tokens["radii"], RADII_KEYS):
                limit = _max_radius()
                for key in sorted(RADII_KEYS):
                    value = tokens["radii"][key]
                    if not _is_int(value) or value < 0:
                        failures.append(f"RADIUS_INVALID:{key}")
                    elif value > limit:
                        failures.append(f"RADIUS_ABOVE_PROFILE_MAX:{key}:{value}>{limit}")
            if _closed(failures, "spacing", tokens["spacing"], SPACING_KEYS):
                for key in sorted(SPACING_KEYS):
                    if not _is_int(tokens["spacing"][key]) or tokens["spacing"][key] < 0:
                        failures.append(f"SPACING_INVALID:{key}")
            if _closed(failures, "elevation", tokens["elevation"], ELEVATION_KEYS):
                for level in sorted(ELEVATION_KEYS):
                    shadow = tokens["elevation"][level]
                    if _closed(failures, f"elevation.{level}", shadow, SHADOW_KEYS):
                        if not (_is_int(shadow["y"]) and _is_int(shadow["blur"]) and shadow["y"] >= 0 and shadow["blur"] >= 0):
                            failures.append(f"ELEVATION_INVALID:{level}")
                        if not isinstance(shadow["alpha"], (int, float)) or isinstance(shadow["alpha"], bool) or not 0 <= shadow["alpha"] <= 1:
                            failures.append(f"ELEVATION_ALPHA_INVALID:{level}")
            motion = tokens["motion"]
            if _closed(failures, "motion", motion, MOTION_KEYS):
                if not (_is_int(motion["short_ms"]) and _is_int(motion["medium_ms"]) and 0 <= motion["short_ms"] <= motion["medium_ms"] <= 1000):
                    failures.append("MOTION_DURATION_INVALID")
                if not isinstance(motion["easing"], str) or not motion["easing"]:
                    failures.append("MOTION_EASING_INVALID")
                if motion["reduced_motion"] != "none":
                    failures.append("REDUCED_MOTION_MUST_BE_NONE")
            typography = tokens["typography"]
            if _closed(failures, "typography", typography, TYPOGRAPHY_KEYS):
                if typography["unit"] != "logical_px_character_height":
                    failures.append("TYPOGRAPHY_UNIT_INVALID")
                if _closed(failures, "typography.roles", typography["roles"], ROLE_KEYS):
                    for role in sorted(ROLE_KEYS):
                        spec = typography["roles"][role]
                        if not _closed(failures, f"typography.roles.{role}", spec, ROLE_FIELDS):
                            continue
                        if spec["font"] not in registry:
                            failures.append(f"FONT_ASSET_UNKNOWN:{role}:{spec['font']}")
                        elif not (FONTS_DIR / registry[spec["font"]]["license_file"]).is_file():
                            failures.append(f"FONT_LICENSE_MISSING:{spec['font']}")
                        if not _is_int(spec["size"]) or spec["size"] <= 0:
                            failures.append(f"TYPOGRAPHY_SIZE_INVALID:{role}")
                        if not _is_int(spec["weight"]) or not 1 <= spec["weight"] <= 1000:
                            failures.append(f"TYPOGRAPHY_WEIGHT_INVALID:{role}")
            guardrails = tokens["guardrails"]
            extra: list[tuple[str, str]] = []
            if _closed(failures, "guardrails", guardrails, GUARDRAIL_KEYS):
                minimum = guardrails["minimum_text_contrast"]
                if not isinstance(minimum, (int, float)) or isinstance(minimum, bool) or minimum < MIN_TEXT_CONTRAST:
                    failures.append("GUARDRAIL_MINIMUM_WEAKENED")
                pairs = guardrails["extra_pairs"]
                if not isinstance(pairs, list) or not all(
                        isinstance(p, list) and len(p) == 2 and all(k in COLOR_KEYS for k in p) for p in pairs):
                    failures.append("GUARDRAIL_EXTRA_PAIRS_INVALID")
                else:
                    extra = [(p[0], p[1]) for p in pairs]
            if colors_ok:
                for fg, bg in (*MANDATORY_TEXT_PAIRS, *MANDATORY_FILL_PAIRS, *extra):
                    ratio = contrast_ratio(colors[fg], colors[bg])
                    if ratio < MIN_TEXT_CONTRAST:
                        failures.append(f"CONTRAST:{fg}/{bg}:{ratio:.2f}")
                for role in STATUS_ROLES:  # LIB-18: contrast alone let a white "success" through
                    r, g, b = (int(colors[role][i:i + 2], 16) / 255 for i in (1, 3, 5))
                    _, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
                    if saturation < STATUS_MIN_SATURATION or not STATUS_LIGHTNESS[0] <= lightness <= STATUS_LIGHTNESS[1]:
                        failures.append(f"STATUS_NOT_CHROMATIC:{role}:l={lightness:.2f},s={saturation:.2f}")
                for fg, bg in FOCUS_PAIRS:
                    ratio = contrast_ratio(colors[fg], colors[bg])
                    if ratio < MIN_FOCUS_CONTRAST:
                        failures.append(f"FOCUS_CONTRAST:{fg}/{bg}:{ratio:.2f}")
    if failures:
        raise UIRefusal("THEME_V02_REFUSED", ";".join(sorted(failures)))
    return theme


def theme_v02_commitment(theme: dict[str, Any]) -> str:
    validate_theme_v02(theme)
    return commitment("MOSAIC.UI.STD.THEME.v0.2", theme)


def load_theme_v02(path: Path) -> dict[str, Any]:
    return validate_theme_v02(read_json(path))


def list_themes_v02() -> list[str]:
    return sorted(path.stem for path in THEMES_V02_DIR.glob("*.json"))


def project_to_v01(theme: dict[str, Any]) -> dict[str, Any]:
    """v0.1-shaped view of a v0.2 theme; passes the unchanged v0.1 validator."""
    validate_theme_v02(theme)
    tokens, families = theme["tokens"], load_font_registry()["fonts"]
    v01_colors = ("accent", "accent_hover", "border", "canvas", "field", "focus", "info", "pending", "refused",
                  "selection", "surface", "surface_hover", "surface_raised", "text", "text_quiet")
    projected = {
        "schema": "mosaic.ui.std.theme.v0.1", "theme_id": theme["theme_id"],
        "standing": theme["standing"], "authority_effect": "NONE",
        "tokens": {
            "colors": {key: tokens["colors"][key] for key in v01_colors},
            "radii": {key: tokens["radii"][key] for key in ("none", "sm", "md")},
            "spacing": dict(tokens["spacing"]),
            "typography": {"unit": tokens["typography"]["unit"], "roles": {
                role: {"family": families[spec["font"]]["family"], "size": spec["size"], "weight": spec["weight"]}
                for role, spec in tokens["typography"]["roles"].items()}},
        },
    }
    validate_theme(projected)
    return projected


def verify_font_assets() -> list[str]:
    """Hash-check every registered font file and license; returns mismatches (empty when intact)."""
    problems = []
    for font_id, entry in load_font_registry()["fonts"].items():
        for item in entry["files"]:
            path = FONTS_DIR / item["file"]
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                problems.append(f"{font_id}:{item['file']}")
        license_path = FONTS_DIR / entry["license_file"]
        if not license_path.is_file() or hashlib.sha256(license_path.read_bytes()).hexdigest() != entry["license_sha256"]:
            problems.append(f"{font_id}:{entry['license_file']}")
    return problems


def font_face_css(font_ids: list[str]) -> str:
    """@font-face rules for registered OFL fonts, embedded as data URIs (no network)."""
    import base64
    registry = load_font_registry()["fonts"]
    rules = []
    for font_id in dict.fromkeys(font_ids):
        entry = registry[font_id]
        rules.append(f"/* {entry['family']}: SIL Open Font License 1.1; license text in mosaic_ui_std/fonts/ */")
        for item in entry["files"]:
            data = base64.b64encode((FONTS_DIR / item["file"]).read_bytes()).decode()
            rules.append(f"@font-face{{font-family:'{entry['family']}';font-style:normal;font-display:block;"
                         f"font-weight:{item['weight']};src:url(data:font/woff2;base64,{data}) format('woff2')}}")
    return "\n".join(rules)

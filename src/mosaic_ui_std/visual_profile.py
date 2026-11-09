"""Closed professional presentation contract for the Mosaic Signature profile."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from mosaic_ui.canonical import commitment, read_json
from mosaic_ui.model import ALL_COMPONENT_KINDS, UIRefusal

from .theme import THEMES_DIR, load_theme


VISUAL_PROFILE_SCHEMA = "mosaic.ui.signature-visual-profile.v0.1"
VISUAL_PROFILE_PATH = Path(__file__).resolve().parent / "profiles" / "mosaic-signature-visual.json"
PROFILE_KEYS = {
    "schema", "visual_profile_id", "visual_profile_version", "profile_id", "foundations",
    "component_families", "reference_compositions", "evidence_contract", "standing",
    "authority_effect", "claim_boundary",
}
FOUNDATION_KEYS = {"color", "geometry", "hierarchy", "iconography", "motion", "typography"}
FAMILY_KEYS = {"family_id", "kinds", "principles", "state_treatments"}
COMPOSITION_KEYS = {"composition_id", "name", "required_families", "quality_bar"}
EVIDENCE_KEYS = {"quality_gates", "required_captures", "required_themes"}
REQUIRED_GATES = {
    "TOKEN_PROVENANCE", "COMPONENT_FAMILY_COVERAGE", "STATE_RECIPE_COVERAGE",
    "TEXT_CONTRAST", "FOCUS_VISIBILITY", "STABLE_GEOMETRY", "ICON_LABELING",
    "REDUCED_MOTION", "VISUAL_BASELINE", "HUMAN_VISUAL_REVIEW",
}


def _closed(value: Any, keys: set[str], detail: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise UIRefusal("SIGNATURE_VISUAL_PROFILE_REFUSED", detail + ":KEYS")
    return value


def _string_list(value: Any, detail: str) -> list[str]:
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item for item in value):
        raise UIRefusal("SIGNATURE_VISUAL_PROFILE_REFUSED", detail)
    return value


def validate_signature_visual_profile(value: Any) -> dict[str, Any]:
    profile = _closed(value, PROFILE_KEYS, "PROFILE")
    if profile["schema"] != VISUAL_PROFILE_SCHEMA or profile["authority_effect"] != "NONE" \
            or profile["profile_id"] != "mosaic-signature":
        raise UIRefusal("SIGNATURE_VISUAL_PROFILE_REFUSED", "IDENTITY_OR_AUTHORITY")
    for key in ("visual_profile_id", "visual_profile_version", "standing", "claim_boundary"):
        if not isinstance(profile[key], str) or not profile[key]:
            raise UIRefusal("SIGNATURE_VISUAL_PROFILE_REFUSED", "IDENTITY")

    foundations = _closed(profile["foundations"], FOUNDATION_KEYS, "FOUNDATIONS")
    if foundations["geometry"].get("maximum_radius") != 8 \
            or foundations["hierarchy"].get("levels") != ["application", "workspace", "task", "specimen", "evidence"] \
            or foundations["iconography"].get("policy") != "OWNED_SEMANTIC_VOCABULARY" \
            or 0 not in foundations["motion"].get("durations_ms", []):
        raise UIRefusal("SIGNATURE_VISUAL_PROFILE_REFUSED", "FOUNDATION_CONTRACT")

    families = profile["component_families"]
    if not isinstance(families, list) or not families:
        raise UIRefusal("SIGNATURE_VISUAL_PROFILE_REFUSED", "COMPONENT_FAMILIES")
    family_ids: list[str] = []
    kinds: list[str] = []
    for family in families:
        item = _closed(family, FAMILY_KEYS, "COMPONENT_FAMILY")
        family_ids.append(str(item["family_id"]))
        kinds.extend(_string_list(item["kinds"], "COMPONENT_KINDS"))
        _string_list(item["principles"], "COMPONENT_PRINCIPLES")
        _string_list(item["state_treatments"], "COMPONENT_STATES")
    if family_ids != sorted(set(family_ids)) or len(kinds) != len(set(kinds)) \
            or set(kinds) != set(ALL_COMPONENT_KINDS):
        raise UIRefusal("SIGNATURE_VISUAL_PROFILE_REFUSED", "COMPONENT_COVERAGE")

    compositions = profile["reference_compositions"]
    composition_ids: list[str] = []
    if not isinstance(compositions, list) or len(compositions) != 5:
        raise UIRefusal("SIGNATURE_VISUAL_PROFILE_REFUSED", "REFERENCE_COMPOSITIONS")
    for composition in compositions:
        item = _closed(composition, COMPOSITION_KEYS, "REFERENCE_COMPOSITION")
        composition_ids.append(str(item["composition_id"]))
        required = _string_list(item["required_families"], "REQUIRED_FAMILIES")
        if not set(required) <= set(family_ids) or not item["name"] or not item["quality_bar"]:
            raise UIRefusal("SIGNATURE_VISUAL_PROFILE_REFUSED", "REFERENCE_COMPOSITION_SCOPE")
    if composition_ids != sorted(set(composition_ids)):
        raise UIRefusal("SIGNATURE_VISUAL_PROFILE_REFUSED", "REFERENCE_COMPOSITION_ORDER")

    evidence = _closed(profile["evidence_contract"], EVIDENCE_KEYS, "EVIDENCE")
    if set(_string_list(evidence["quality_gates"], "QUALITY_GATES")) != REQUIRED_GATES \
            or set(_string_list(evidence["required_themes"], "REQUIRED_THEMES")) != {
                "high-contrast-dark", "signature-dark", "signature-light"
            } or set(_string_list(evidence["required_captures"], "REQUIRED_CAPTURES")) != {
                "BROWSER_DESKTOP", "BROWSER_MOBILE", "WIN32_DESKTOP"
            }:
        raise UIRefusal("SIGNATURE_VISUAL_PROFILE_REFUSED", "EVIDENCE_CONTRACT")
    return {
        "schema": "mosaic.ui.signature-visual-profile-validation.v0.1",
        "visual_profile_id": profile["visual_profile_id"],
        "component_count": len(kinds), "family_count": len(families),
        "composition_count": len(compositions), "quality_gate_count": len(REQUIRED_GATES),
        "visual_profile_root": commitment("MOSAIC.UI.SIGNATURE_VISUAL_PROFILE.v0.1", profile),
        "disposition": "PASS_LOCAL_CANDIDATE", "authority_effect": "NONE",
    }


def load_signature_visual_profile() -> dict[str, Any]:
    value = read_json(VISUAL_PROFILE_PATH)
    validate_signature_visual_profile(value)
    return value


def _linear(channel: int) -> float:
    value = channel / 255
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _contrast(first: str, second: str) -> float:
    def luminance(value: str) -> float:
        channels = [int(value[index:index + 2], 16) for index in (1, 3, 5)]
        return 0.2126 * _linear(channels[0]) + 0.7152 * _linear(channels[1]) + 0.0722 * _linear(channels[2])
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return round((high + 0.05) / (low + 0.05), 2)


def signature_visual_witness() -> dict[str, Any]:
    profile = load_signature_visual_profile()
    validation = validate_signature_visual_profile(profile)
    contrast_cases = []
    for theme_id in profile["evidence_contract"]["required_themes"]:
        colors = load_theme(THEMES_DIR / f"{theme_id}.json")["tokens"]["colors"]
        for surface in ("canvas", "surface", "field"):
            ratio = _contrast(colors["text"], colors[surface])
            contrast_cases.append({
                "case_id": f"{theme_id}:text/{surface}", "ratio": ratio,
                "minimum": 4.5, "disposition": "PASS" if ratio >= 4.5 else "FAIL",
            })
    failures = [case for case in contrast_cases if case["disposition"] != "PASS"]
    value = {
        "schema": "mosaic.ui.signature-visual-witness.v0.1",
        "visual_profile_root": validation["visual_profile_root"],
        "component_count": validation["component_count"],
        "family_count": validation["family_count"],
        "composition_count": validation["composition_count"],
        "quality_gate_count": validation["quality_gate_count"],
        "contrast_cases": contrast_cases,
        "failure_count": len(failures),
        "disposition": "PASS_LOCAL_CANDIDATE" if not failures else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
        "claim_boundary": profile["claim_boundary"],
    }
    value["commitment"] = commitment("MOSAIC.UI.SIGNATURE_VISUAL_WITNESS.v0.1", value)
    return value


__all__ = [
    "VISUAL_PROFILE_PATH", "VISUAL_PROFILE_SCHEMA", "load_signature_visual_profile",
    "signature_visual_witness", "validate_signature_visual_profile",
]

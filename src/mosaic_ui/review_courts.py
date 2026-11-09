"""Governed, browser-free review-pack courts over Mosaic HeadlessUI evidence."""
from __future__ import annotations

import hashlib
from typing import Any

from .canonical import canonical_bytes, commitment
from .headless import HeadlessUI
from .model import UIRefusal
from .review_ontology import build_review_ontology
from .review_shell import assemble, list_packs, load_pack, validate_pack
from .review_specimens import build_specimen_definitions
from .sampling import build_plan
from .signature_profile import build_signature_payload
from .theme_payload import attach_theme_v02

VIEWPORTS = {"wide": (1440, 900), "compact": (1120, 760), "narrow": (840, 720)}
CLAIM_BOUNDARY = (
    "STATIC_PACK_CONTRACT_AND_HEADLESS_SEMANTIC_PROJECTION_ONLY; "
    "NO_BROWSER_PIXEL_DOM_GEOMETRY_OR_ASSISTIVE_TECHNOLOGY_CLAIM"
)


def run_review_headless_court(
    pack_id: str = "g2-stage", themes: list[str] | None = None, mode: str = "auto",
) -> dict[str, Any]:
    """Probe a review pack with canonical HeadlessUI, without launching a browser engine."""
    from mosaic_ui_std.theme_v02 import list_themes_v02

    if pack_id not in list_packs():
        raise UIRefusal("REVIEW_PACK_UNKNOWN", pack_id)
    known_themes = list_themes_v02()
    selected = known_themes if themes == ["all"] else list(themes or ["signature-dark"])
    if not selected or len(set(selected)) != len(selected):
        raise UIRefusal("REVIEW_COURT_THEME_SCOPE_REFUSED", "EMPTY_OR_DUPLICATE")
    unknown = sorted(set(selected) - set(known_themes))
    if unknown:
        raise UIRefusal("REVIEW_COURT_THEME_UNKNOWN", ",".join(unknown))

    pack = load_pack(pack_id)
    static_failures = validate_pack(pack_id)
    subjects = list(pack["manifest"].get("court_states", ()))
    ontology = build_review_ontology()
    known_subjects = {item["subject_id"] for item in ontology["subjects"]}
    definitions = build_specimen_definitions()
    invalid_subjects = sorted(set(subjects) - known_subjects)
    missing_definitions = sorted(set(subjects) - set(definitions))
    if not subjects or invalid_subjects or missing_definitions:
        raise UIRefusal(
            "REVIEW_COURT_SUBJECT_SCOPE_REFUSED",
            f"invalid={','.join(invalid_subjects)};missing={','.join(missing_definitions)}",
        )

    plan = build_plan(
        {"theme": selected, "viewport": list(VIEWPORTS), "subject": subjects}, mode,
    )
    shells = {theme: assemble(pack_id, theme) for theme in selected}
    projections: dict[tuple[str, str], dict[str, Any]] = {}
    cases = []
    for case in plan["cases"]:
        projection_key = (case["theme"], case["viewport"])
        if projection_key not in projections:
            payload = attach_theme_v02(
                build_signature_payload("operational-dashboard", "signature-dark", "comfortable"),
                case["theme"],
            )
            width, height = VIEWPORTS[case["viewport"]]
            projections[projection_key] = HeadlessUI(payload).project(width, height).as_dict()
        projection = projections[projection_key]
        failures = list(static_failures)
        if projection["gates"]["disposition"] != "PASS":
            failures.append("HEADLESS_PROJECTION_REFUSED")
        definition = definitions[case["subject"]]
        if definition.get("authority_effect") != "NONE":
            failures.append("SPECIMEN_AUTHORITY_EFFECT")
        result = {
            **case,
            "shell_sha256": hashlib.sha256(shells[case["theme"]].encode("utf-8")).hexdigest(),
            "projection_sha256": hashlib.sha256(canonical_bytes(projection)).hexdigest(),
            "specimen_commitment": definition["commitment"],
            "failures": failures,
            "disposition": "PASS" if not failures else "REFUSE",
        }
        cases.append(result)

    failures = [
        f"{case['theme']}:{case['viewport']}:{case['subject']}:{failure}"
        for case in cases for failure in case["failures"]
    ]
    value = {
        "schema": "mosaic.ui.review-headless-court.v0.1",
        "runner": "MOSAIC_HEADLESS_UI",
        "pack_id": pack_id,
        "pack_version": pack["manifest"]["version"],
        "themes": selected,
        "plan_commitment": plan["commitment"],
        "sampling_mode": plan["mode"],
        "sampling_strength": plan["strength"],
        "full_product": plan["full_product"],
        "case_count": len(cases),
        "cases": cases,
        "failures": failures,
        "disposition": "PASS_LOCAL_CANDIDATE" if cases and not failures else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": CLAIM_BOUNDARY,
    }
    value["commitment"] = commitment("MOSAIC.UI.REVIEW_HEADLESS_COURT.v0.1", value)
    return value


__all__ = ["CLAIM_BOUNDARY", "VIEWPORTS", "run_review_headless_court"]

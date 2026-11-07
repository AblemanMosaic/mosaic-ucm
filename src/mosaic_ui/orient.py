"""Deterministic cold-boot orientation and environment diagnostics."""
from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

from mosaic_ui_std.catalog import load_runtime_catalog, validate_catalog
from mosaic_ui_std.signature import load_signature_profile, validate_signature_profile
from mosaic_ui_std.visual_profile import (
    load_signature_visual_profile,
    signature_visual_witness,
    validate_signature_visual_profile,
)

from . import __version__
from .canonical import atomic_write, canonical_bytes, commitment
from .framework_bindings import binding_manifest
from .domain_protocol import domain_schema_registry
from .play_adapters import adapter_candidate_matrix
from .play_runtime_qualification import discover_chromium_runtimes, play_runtime_policy
from .public_contract import public_contract_witness
from .web_distribution import web_manifest


REQUIRED_SOURCE_GUIDES = (
    "START-HERE.md", "AGENTS.md", "SYSTEM-MAP.json", "README.md",
    "MOSAIC-UI-0.1.0-CANDIDATE-RELEASE.md", "MOSAIC-UI-SUBSYSTEMS.md",
    "MOSAIC-UI-REVIEW-WORKBENCH-ROADMAP.md",
    "MOSAIC-SIGNATURE-VISUAL-SYSTEM.md", "MOSAIC-UI-FUTURE-DIRECTIONS.md",
    "MOSAIC-PLAY-ADAPTER-READINESS.md",
    "MOSAIC-UI-1.0-PROGRAM.md", "MOSAIC-UI-1.0-MIGRATION-AND-COMPATIBILITY.md",
    "MOSAIC-UI-PARALLEL-029-INTEGRATION.md",
)


def orientation_witness(source_root: Path | None = None) -> dict[str, Any]:
    catalog = load_runtime_catalog()
    web = web_manifest()
    adapters = binding_manifest()
    signature = load_signature_profile()
    visual_profile = load_signature_visual_profile()
    visual_validation = validate_signature_visual_profile(visual_profile)
    visual = signature_visual_witness()
    from .review_ontology import review_ontology_witness

    review_ontology = review_ontology_witness()
    from .play import play_evidence_witness
    from .spatial import spatial_evidence_witness

    play = play_evidence_witness()
    spatial = spatial_evidence_witness()
    domain_schemas = domain_schema_registry()
    adapter_matrix = adapter_candidate_matrix()
    runtime_policy = play_runtime_policy()
    public_contract = public_contract_witness()
    from mosaic_ui_std.theme_v02 import (
        THEMES_V02_DIR, list_themes_v02, load_theme_v02, theme_v02_commitment, verify_font_assets,
    )
    from .evidence_gates import load_registry
    from .review_shell import list_packs, load_binding, validate_pack

    themes_v02 = [
        {"theme_id": theme_id,
         "commitment": theme_v02_commitment(load_theme_v02(THEMES_V02_DIR / f"{theme_id}.json"))}
        for theme_id in list_themes_v02()
    ]
    font_failures = verify_font_assets()
    pack_failures = {pack_id: validate_pack(pack_id) for pack_id in list_packs()}
    gate_registry = load_registry()
    source = source_root.resolve() if source_root is not None else None
    guides = {
        name: bool(source is not None and (source / name).is_file())
        for name in REQUIRED_SOURCE_GUIDES
    }
    checks = {
        "RUNTIME_CATALOG": validate_catalog(catalog)["disposition"],
        "PUBLIC_CONTRACT_25_KIND_FREEZE": public_contract["disposition"],
        "TRACK_A_OPTIONAL_DOMAIN_INDEPENDENCE": "PASS_LOCAL_CANDIDATE"
        if public_contract["checks"]["OPTIONAL_DOMAINS_EXCLUDED"]
        and public_contract["checks"]["TRACKS_NOT_MUTUALLY_GATING"] else "FAIL",
        "SOVEREIGN_WEB_NO_DEPENDENCIES": "PASS" if not web["runtime_dependencies"] and not web["framework_dependencies"] else "FAIL",
        "OPTIONAL_ADAPTER_BOUNDARY": "PASS" if adapters["canonical_runtime"] is False else "FAIL",
        "SIGNATURE_PROFILE": validate_signature_profile(signature)["disposition"],
        "SIGNATURE_VISUAL_PROFILE": visual["disposition"],
        "REVIEW_ONTOLOGY": review_ontology["disposition"],
        "PLAY_2D_PROTOTYPE": play["disposition"],
        "SPATIAL_3D_PROTOTYPE": spatial["disposition"],
        "DOMAIN_SCHEMA_REGISTRY": domain_schemas["disposition"],
        "PLAY_ADAPTER_SELECTION": "PASS_LOCAL_CANDIDATE" if len(adapter_matrix["selected"]) == 2 else "FAIL",
        "PLAY_EXTERNAL_RUNTIME_POLICY": "PASS_LOCAL_CANDIDATE"
        if runtime_policy["authority_effect"] == "NONE" else "FAIL",
        "THEME_V02_LIBRARY": "PASS" if themes_v02 else "FAIL",
        "OWNED_FONT_ASSETS": "PASS" if not font_failures else "FAIL",
        "REVIEW_PACKS": "PASS" if pack_failures and not any(pack_failures.values()) else "FAIL",
        "EVIDENCE_GATE_REGISTRY": "PASS" if gate_registry.get("authority_effect") == "NONE" else "FAIL",
        "SOURCE_GUIDES": "PASS" if source is None or all(guides.values()) else "FAIL",
    }
    passed = all(value in {"PASS", "PASS_LOCAL_CANDIDATE"} for value in checks.values())
    value = {
        "schema": "mosaic.ui.orientation.v0.1",
        "version": __version__,
        "identity": "SOVEREIGN_EVIDENCE_NATIVE_SEMANTIC_UI_SUBSTRATE",
        "canonical_realizers": ["BROWSER", "HEADLESS", "WIN32"],
        "canonical_web_interface": "WEB_COMPONENT_AND_STANDARD_ES_MODULE",
        "component_count": len(catalog["components"]),
        "framework_runtime_required": False,
        "optional_compatibility_adapters": adapters["frameworks"],
        "signature_profile": {
            "profile_id": signature["profile_id"], "profile_version": signature["profile_version"],
            "default_theme": signature["default_theme"], "default_density": signature["default_density"],
            "themes": signature["themes"], "densities": signature["densities"],
            "compositions": [item["composition_id"] for item in signature["compositions"]],
            "visual_profile_id": visual_profile["visual_profile_id"],
            "visual_profile_version": visual_profile["visual_profile_version"],
            "visual_profile_commitment": visual["commitment"],
        },
        "signature_visual_profile": {
            "profile_id": visual_profile["visual_profile_id"],
            "profile_version": visual_profile["visual_profile_version"],
            "family_count": visual_validation["family_count"],
            "component_count": visual_validation["component_count"],
            "composition_count": visual_validation["composition_count"],
            "quality_gate_count": visual_validation["quality_gate_count"],
            "visual_profile_root": visual_validation["visual_profile_root"],
            "witness_commitment": visual["commitment"],
        },
        "web_distribution_commitment": web["commitment"],
        "adapter_bundle_commitment": adapters["commitment"],
        "review_ontology": {
            "group_count": review_ontology["group_count"],
            "subject_count": review_ontology["subject_count"],
            "component_count": review_ontology["component_count"],
            "condition_count": review_ontology["condition_count"],
            "ontology_commitment": review_ontology["ontology_commitment"],
            "witness_commitment": review_ontology["commitment"],
        },
        "optional_domain_prototypes": {
            "play_2d": {
                "schema": play["schema"], "commitment": play["commitment"],
                "experiment_count": len(play["projections"]), "engine_binding": "NONE_EXPERIMENTAL",
            },
            "spatial_3d": {
                "schema": spatial["schema"], "commitment": spatial["commitment"],
                "experiment_count": len(spatial["projections"]), "engine_binding": "NONE_EXPERIMENTAL",
                "exact_pixel_equality_required": False,
            },
        },
        "adapter_readiness": {
            "domain_schema_registry_commitment": domain_schemas["commitment"],
            "play_adapter_matrix_commitment": adapter_matrix["commitment"],
            "selected_play_adapters": adapter_matrix["selected"],
            "selection_effect": adapter_matrix["selection_effect"],
            "external_runtime_policy_commitment": runtime_policy["commitment"],
            "external_runtime_family": runtime_policy["runtime_family"],
            "external_runtime_effect": "EXPLICIT_EXECUTABLE_QUALIFICATION_ONLY",
        },
        "public_contract": {
            "contract_id": public_contract["contract_id"],
            "contract_commitment": public_contract["contract_commitment"],
            "component_count": public_contract["component_count"],
            "release_pathway": public_contract["release_pathway"],
            "release_closure_pathways": public_contract["release_closure_pathways"],
            "excluded_optional_pathways": public_contract["excluded_optional_pathways"],
            "track_a_requires_track_b": False,
            "witness_commitment": public_contract["commitment"],
        },
        "visual_library_v02": {
            "theme_count": len(themes_v02), "themes": themes_v02,
            "font_failures": font_failures, "review_packs": sorted(pack_failures),
            "review_binding_commitment": load_binding()["commitment"],
            "evidence_gate_command_count": len(gate_registry["commands"]),
            "default_workbench_route": "CANONICAL_ADAPTIVE_SIGNATURE_V3",
            "optional_library_route": "/library",
        },
        "source_guides": guides,
        "checks": checks,
        "verification_ladder": [
            "python verify_dist.py",
            "python -m unittest discover -s tests -v",
            "mosaic-ui protocol --realizer HEADLESS",
            "mosaic-ui public-contract",
            "mosaic-ui protocol --realizer BROWSER",
            "mosaic-ui accessibility",
            "mosaic-ui review-ontology --witness",
            "mosaic-ui signature-visual --witness",
            "mosaic-ui theme-v02 --theme all",
            "mosaic-ui visual-certify-v02",
            "mosaic-ui review-court --pack g2-stage --themes all",
            "mosaic-ui play-evidence",
            "mosaic-ui spatial-evidence",
            "mosaic-ui play-adapter-matrix",
            "mosaic-ui play-adapters <output>",
            "mosaic-ui play-runtime <output> --chromium-executable <path>",
            "mosaic-ui workbench --port 8765",
            "mosaic-ui review --realizer WIN32 --mode functional --subject component.button --theme signature-dark --density comfortable",
            "mosaic-ui review --realizer HEADLESS --mode functional --composition data-workspace --scenario filter-and-export",
            "mosaic-ui session-backup <database> <backup>",
            "mosaic-ui session-verify <backup>",
            "mosaic-ui consumer-lifecycle <baseline-wheel> <candidate-wheel> <output>",
            "mosaic-ui human-review-template <request> <receipt>",
            "mosaic-ui verify-human-review <request> <receipt>",
            "mosaic-ui browser-engines <output> --engine <id=path> --engine <id=path>",
            "mosaic-ui release . <output> --upgrade-from-wheel <prior-wheel> --native --browser-engine <id=path> --browser-engine <id=path>",
        ],
        "reading_order": [
            "START-HERE.md", "AGENTS.md", "SYSTEM-MAP.json", "README.md",
            "MOSAIC-UI-0.1.0-CANDIDATE-RELEASE.md", "MOSAIC-UI-SUBSYSTEMS.md",
            "MOSAIC-UI-REVIEW-WORKBENCH-ROADMAP.md",
            "MOSAIC-SIGNATURE-VISUAL-SYSTEM.md", "MOSAIC-UI-FUTURE-DIRECTIONS.md",
            "MOSAIC-PLAY-ADAPTER-READINESS.md",
            "MOSAIC-UI-PARALLEL-029-INTEGRATION.md",
            "MOSAIC-UI-1.0-PROGRAM.md", "MOSAIC-UI-1.0-MIGRATION-AND-COMPATIBILITY.md",
            "MOSAIC-UI-1.0-READINESS.md",
        ],
        "disposition": "PASS_LOCAL_CANDIDATE" if passed else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": "ORIENTATION_DOES_NOT_ESTABLISH HOST_ACCEPTANCE_EXTERNAL_SIGNATURE_OR_CONSTITUTIONAL_ADMISSION",
    }
    value["commitment"] = commitment("MOSAIC.UI.ORIENTATION.v0.1", value)
    return value


def doctor_witness() -> dict[str, Any]:
    implementation = platform.python_implementation()
    python_supported = sys.version_info >= (3, 12) and implementation == "CPython"
    installed_play_runtimes = discover_chromium_runtimes()
    value = {
        "schema": "mosaic.ui.doctor.v0.1",
        "version": __version__,
        "python": {"implementation": implementation, "version": platform.python_version(), "supported": python_supported},
        "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "capabilities": {
            "HEADLESS": True,
            "BROWSER": True,
            "WIN32": sys.platform == "win32",
            "SOVEREIGN_WEB": web_manifest()["framework_dependencies"] == [],
            "PLAY_2D_HEADLESS_PROTOTYPE": True,
            "SPATIAL_3D_HEADLESS_PROTOTYPE": True,
            "PLAY_2D_ARTIFACT_ADAPTERS": True,
            "PLAY_EXTERNAL_RUNTIME_QUALIFICATION": bool(installed_play_runtimes),
            "THEME_V02_LIBRARY": True,
            "REVIEW_PACK_LIBRARY": True,
            "HEADLESS_REVIEW_COURT": True,
        },
        "installed_play_runtimes": installed_play_runtimes,
        "disposition": "PASS_LOCAL_CANDIDATE" if python_supported else "REFUSE",
        "standing": "LOCAL_ENVIRONMENT_EVIDENCE",
        "authority_effect": "NONE",
    }
    value["commitment"] = commitment("MOSAIC.UI.DOCTOR.v0.1", value)
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("orient", "doctor"), nargs="?", default="orient")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = orientation_witness(args.source) if args.command == "orient" else doctor_witness()
    data = canonical_bytes(result) + b"\n"
    if args.output is not None:
        atomic_write(args.output.resolve(), data)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2))
    return 0 if result["disposition"] != "REFUSE" else 32


__all__ = ["doctor_witness", "orientation_witness"]


if __name__ == "__main__":
    raise SystemExit(main())

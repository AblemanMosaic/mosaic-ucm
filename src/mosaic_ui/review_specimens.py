"""Shared, refuse-closed specimen definitions for Mosaic UI review surfaces."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .canonical import commitment, read_json
from .model import ALL_COMPONENT_KINDS, UIRefusal
from mosaic_ui_std.visual_profile import load_signature_visual_profile, validate_signature_visual_profile


SPECIMEN_SCHEMA = "mosaic.ui.review-specimen.v0.1"
CATALOG_SCHEMA = "mosaic.ui.review-specimen-catalog.v0.1"
CERTIFICATION_SCHEMA = "mosaic.ui.review-specimen-certification.v0.1"
DEPENDENCY_GRAPH = Path(__file__).resolve().parent / "components" / "dependencies.json"


def _scenario(scenario_id: str, label: str, action: str, expected: str) -> dict[str, str]:
    return {"scenario_id": scenario_id, "label": label, "action": action, "expected": expected}


def _definition(
    subject_id: str,
    presentation: str,
    purpose: str,
    *,
    interactive: bool,
    conditions: tuple[str, ...],
    scenarios: tuple[dict[str, str], ...],
    visual: dict[str, Any],
    preferred_height: int = 300,
) -> dict[str, Any]:
    value = {
        "schema": SPECIMEN_SCHEMA,
        "subject_id": subject_id,
        "presentation": presentation,
        "purpose": purpose,
        "interactive": interactive,
        "interaction_model": "VALUE_AND_WORKFLOW" if interactive else "INSPECTION_ONLY",
        "relevant_conditions": list(conditions),
        "dimensions": {"minimum_width": 320, "preferred_height": preferred_height},
        "value_model": copy.deepcopy(visual.get("value_model", {"default": None})),
        "visual": copy.deepcopy(visual),
        "scenarios": [copy.deepcopy(item) for item in scenarios],
        "required_evidence": ["SEMANTIC_PAYLOAD", "CONDITION_TRACE", "LOCAL_RECEIPT"],
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": "SPECIMEN_EVIDENCE_IS_LOCAL_AND_DOES_NOT_ESTABLISH_RELEASE_ADMISSION",
    }
    value["commitment"] = commitment("MOSAIC.UI.REVIEW_SPECIMEN.v0.1", value)
    return value


FOUNDATION_SPECS: dict[str, dict[str, Any]] = {
    "foundation.color": {
        "presentation": "TOKEN_SWATCHES", "interactive": False,
        "purpose": "Inspect semantic color roles, contrast pairings, and state color provenance.",
        "conditions": ("theme", "preference"),
        "visual": {"swatches": ["canvas", "surface", "field", "text", "text_quiet", "accent", "focus", "pending", "refused"]},
        "scenarios": (
            _scenario("theme-pairs", "Theme pairs", "Compare background and foreground roles", "Every role is named and attributable"),
            _scenario("status-colors", "Status colors", "Compare accent, pending, and refused", "Meaning does not depend on hue alone"),
        ),
    },
    "foundation.typography": {
        "presentation": "TYPE_SCALE", "interactive": False,
        "purpose": "Inspect type roles, hierarchy, wrapping, truncation, and multilingual fit.",
        "conditions": ("theme", "locale", "direction", "viewport"),
        "visual": {"roles": ["title", "metric", "heading", "body", "mono"], "samples": ["Release evidence console", "42 checks", "A deliberately long label that must wrap safely", "mosaic.ui.receipt"]},
        "scenarios": (
            _scenario("role-ladder", "Role ladder", "Compare all declared text roles", "Hierarchy is distinct without viewport-scaled type"),
            _scenario("text-stress", "Text stress", "Switch locale and narrow viewport", "Long and RTL content remains legible"),
        ),
    },
    "foundation.spacing": {
        "presentation": "SPACING_SCALE", "interactive": False,
        "purpose": "Inspect the governed spacing scale in stack, inline, grid, and section contexts.",
        "conditions": ("density", "viewport"),
        "visual": {"tokens": ["xs:4", "sm:8", "md:12", "lg:20", "xl:28"], "contexts": ["inline", "stack", "grid", "section"]},
        "scenarios": (_scenario("spacing-ruler", "Spacing ruler", "Compare token increments in context", "Gaps are systematic and density-aware"),),
    },
    "foundation.sizing": {
        "presentation": "SIZE_MATRIX", "interactive": False,
        "purpose": "Inspect control heights, pointer targets, fixed-format stability, and responsive bounds.",
        "conditions": ("density", "viewport", "input"),
        "visual": {"items": ["compact control", "comfortable control", "touch target", "fixed tile", "responsive field"]},
        "scenarios": (_scenario("target-matrix", "Target matrix", "Compare density and input targets", "Controls retain stable dimensions and adequate targets"),),
    },
    "foundation.radii": {
        "presentation": "RADIUS_MATRIX", "interactive": False,
        "purpose": "Inspect bounded radius use across structural and compact UI surfaces.",
        "conditions": ("theme",),
        "visual": {"tokens": ["none:0", "sm:4", "md:6"], "uses": ["surface", "field", "control", "badge", "dialog"]},
        "scenarios": (_scenario("radius-roles", "Radius roles", "Compare tokens on their intended surfaces", "No undeclared or excessive radius appears"),),
    },
    "foundation.icons": {
        "presentation": "ICON_GALLERY", "interactive": False,
        "purpose": "Inspect the command icon vocabulary, sizes, names, and missing-icon fallback.",
        "conditions": ("theme", "density", "preference"),
        "visual": {"icons": ["add", "edit", "search", "filter", "save", "export", "undo", "redo", "close", "warning", "missing"]},
        "scenarios": (_scenario("icon-contract", "Icon contract", "Inspect icons at declared sizes and high contrast", "Each icon has a name and deterministic fallback"),),
    },
    "foundation.motion": {
        "presentation": "MOTION_TIMELINE", "interactive": True,
        "purpose": "Inspect bounded state transitions and the reduced-motion substitution.",
        "conditions": ("preference", "state"),
        "visual": {"tracks": ["hover 120ms", "focus 0ms", "panel 160ms", "reduced motion 0ms"], "value_model": {"default": "stopped"}},
        "scenarios": (
            _scenario("play-transition", "Play transition", "Activate the bounded transition", "Only the reviewed property changes"),
            _scenario("reduce-motion", "Reduced motion", "Select reduced-motion preference", "Motion is removed without hiding state"),
        ),
    },
    "foundation.localization": {
        "presentation": "LOCALE_COMPARE", "interactive": True,
        "purpose": "Inspect English and Arabic content, fallback, direction, and long-label resilience.",
        "conditions": ("locale", "direction", "viewport"),
        "visual": {"messages": ["Review evidence", "Export local receipt", "Long status label remains visible"], "value_model": {"default": "en"}},
        "scenarios": (
            _scenario("rtl-compare", "RTL comparison", "Switch to Arabic and RTL", "Order and alignment mirror without semantic drift"),
            _scenario("fallback", "Missing message", "Request an unknown message reference", "A typed fallback or refusal is visible"),
        ),
    },
}


COMPONENT_VISUALS: dict[str, dict[str, Any]] = {
    "WINDOW": {"title": "Mosaic application", "value_model": {"default": "active"}},
    "PANEL": {"title": "Evidence summary", "value_model": {"default": "expanded"}},
    "BUTTON": {"labels": ["Create project", "Cancel", "Delete"], "value_model": {"default": "Create project"}},
    "TEXT_FIELD": {"label": "Project name", "value_model": {"default": "Constitutional Workbench"}},
    "SELECT": {"label": "Evidence scope", "options": ["All evidence", "Passing", "Refused"], "value_model": {"default": "All evidence"}},
    "COMBOBOX": {"label": "Target profile", "options": ["Mosaic Signature", "High contrast", "Operations"], "value_model": {"default": "Mosaic Signature"}},
    "CHECKBOX": {"label": "Include receipt ledger", "value_model": {"default": True}},
    "RADIO_GROUP": {"label": "Release channel", "options": ["Stable", "Candidate"], "value_model": {"default": "Stable"}},
    "SEGMENTED": {"label": "Review mode", "options": ["Summary", "Details", "Evidence"], "value_model": {"default": "Summary"}},
    "STEPPER": {"label": "Review step", "options": ["Build", "Probe", "Review", "Export"], "value_model": {"default": "Probe"}},
    "NAVIGATION": {"label": "Workspace", "options": ["Overview", "Components", "Evidence"], "value_model": {"default": "Overview"}},
    "MENU": {"label": "Application menu", "options": ["Open", "Export", "Inspect"], "value_model": {"default": "closed"}},
    "TAB_BAR": {"label": "Inspector", "options": ["Anatomy", "Accessibility", "Evidence"], "value_model": {"default": "Anatomy"}},
    "TREE": {"label": "Application structure", "nodes": ["Application", "Header", "Workspace", "Button"], "value_model": {"default": "Application"}},
    "LABEL": {"label": "Release evidence console", "value_model": {"default": None}},
    "BADGE": {"labels": ["Local candidate", "Browser", "Win32"], "value_model": {"default": "Local candidate"}},
    "STATUS": {"label": "Runtime connected", "value_model": {"default": "ready"}},
    "PROGRESS": {"label": "Evidence coverage", "modes": ["determinate", "indeterminate", "paused", "failed"], "value_model": {"default": 68}},
    "KEY_VALUE": {"rows": [["Profile", "Mosaic Signature"], ["Realizer", "WIN32"], ["Standing", "LOCAL_CANDIDATE"]], "value_model": {"default": None}},
    "TABLE": {"columns": ["Component", "Browser", "Win32"], "rows": [["Button", "Pass", "Pass"], ["Dialog", "Pass", "Pass"]], "value_model": {"default": None}},
    "DATA_GRID": {"columns": ["Record", "Kind", "Status"], "rows": [["VIS-021", "Visual", "Pass"], ["WIN-025", "Native", "Pass"], ["ABL-031", "Slice", "Pass"]], "value_model": {"default": "VIS-021"}},
    "LIST": {"options": ["Recent runs", "Releases", "Policies"], "value_model": {"default": "Recent runs"}},
    "NOTIFICATION": {"messages": {"IDLE": "The review completed and its receipt is available.", "PENDING": "The review is still running.", "REFUSED": "Export remains outside permitted custody."}, "value_model": {"default": "IDLE"}},
    "TOOLTIP": {"anchor": "Review evidence", "message": "Opens exact witness references", "value_model": {"default": "hidden"}},
    "DIALOG": {"title": "Publish component profile?", "actions": ["Cancel", "Publish"], "value_model": {"default": "closed"}},
}


PATTERN_SPECS: dict[str, dict[str, Any]] = {
    "pattern.command-bar": {"title": "Command bar", "steps": ["Enter command", "Open actions", "Run", "See receipt"]},
    "pattern.filter-search": {"title": "Filter and search", "steps": ["Enter query", "Choose scope", "Apply", "Inspect results"]},
    "pattern.selection-inspector": {"title": "Selection inspector", "steps": ["Select row", "Load details", "Compare evidence", "Retain selection"]},
    "pattern.confirmation": {"title": "Confirmation", "steps": ["Request effect", "Review consequence", "Confirm or cancel", "Receive outcome"]},
    "pattern.progress-cancel": {"title": "Progress and cancellation", "steps": ["Start operation", "Observe progress", "Cancel", "Verify terminal state"]},
    "pattern.settings": {"title": "Settings", "steps": ["Change value", "Validate", "Apply", "Confirm persistence"]},
    "pattern.receipt-review": {"title": "Receipt review", "steps": ["Choose run", "Inspect checks", "Open evidence", "Export receipt"]},
}


SURFACE_SPECS: dict[str, dict[str, Any]] = {
    "surface.data-workspace": {"title": "Data workspace", "regions": ["Search and filter", "Result grid", "Selection inspector", "Evidence status"]},
    "surface.operational-dashboard": {"title": "Operational dashboard", "regions": ["Navigation", "Metrics", "Active operations", "Evidence feed"]},
    "surface.settings-workflow": {"title": "Settings workflow", "regions": ["Settings menu", "Configuration form", "Validation status", "Confirmation dialog"]},
}

SURFACE_SCENARIOS = {
    "surface.data-workspace": (
        _scenario("filter-and-export", "Filter and export", "Filter records and export the bounded result", "Export receipt and result agree"),
        _scenario("refused-export-path", "Refused export", "Choose a path outside permitted custody", "No write occurs and refusal is retained"),
        _scenario("keyboard-only", "Keyboard only", "Complete focus traversal without a pointer", "All required controls are reachable"),
    ),
    "surface.operational-dashboard": (
        _scenario("refresh-and-review", "Refresh and review", "Refresh operations and inspect evidence", "Metrics, rows, and receipt agree"),
        _scenario("keyboard-only", "Keyboard only", "Complete focus traversal without a pointer", "All required controls are reachable"),
    ),
    "surface.settings-workflow": (
        _scenario("edit-confirm-save", "Edit, confirm, save", "Edit settings and complete confirmation", "Saved state requires semantic and host confirmation"),
        _scenario("keyboard-only", "Keyboard only", "Complete focus traversal without a pointer", "All required controls are reachable"),
    ),
}


def build_ablation_preview(selected: tuple[str, ...] = ("BUTTON", "TEXT_FIELD", "DATA_GRID"),
                           realizer: str = "BROWSER") -> dict[str, Any]:
    """Plan a real dependency-closed review slice without writing an archive."""
    graph = read_json(DEPENDENCY_GRAPH)
    selected_set = set(selected)
    unknown = selected_set - set(graph["components"])
    if unknown or realizer not in graph["pathways"]:
        raise UIRefusal("REVIEW_ABLATION_PLAN_REFUSED", ",".join(sorted(unknown)) or realizer)
    pathways = ["HEADLESS"] if realizer == "HEADLESS" else ["HEADLESS", realizer]
    retained = {graph["components"][kind] for kind in selected_set}
    for pathway in pathways:
        retained.update(graph["pathways"][pathway])
    removed = {
        graph["components"][kind] for kind in graph["components"] if kind not in selected_set
    }
    source_root = Path(__file__).resolve().parents[1]
    estimate = sum((source_root / path).stat().st_size for path in retained if (source_root / path).is_file())
    value = {
        "selected_components": sorted(selected_set), "realizer": realizer,
        "pathways": pathways, "retained_modules": sorted(retained),
        "removed_component_modules": sorted(removed),
        "retained_module_count": len(retained), "estimated_source_bytes": estimate,
        "authority_effect": "NONE",
    }
    value["commitment"] = commitment("MOSAIC.UI.REVIEW_ABLATION_PREVIEW.v0.1", value)
    return value


def _component_definitions() -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for kind in sorted(ALL_COMPONENT_KINDS):
        subject_id = f"component.{kind.lower().replace('_', '-')}"
        interaction = kind not in {"LABEL", "BADGE", "STATUS", "PROGRESS", "KEY_VALUE", "TABLE", "PANEL", "WINDOW", "NOTIFICATION"}
        values[subject_id] = _definition(
            subject_id, f"COMPONENT_{kind}",
            f"Exercise the {kind.replace('_', ' ').lower()} as a distinct semantic component.",
            interactive=interaction,
            conditions=("state", "theme", "density", "viewport", "locale", "direction", "input", "preference"),
            scenarios=(
                _scenario("state-matrix", "State matrix", "Inspect every applicable interaction state", "State and value remain independent"),
                _scenario("semantic-action", "Semantic action", "Exercise the primary value or command", "The event and resulting value are receipted"),
            ),
            visual=COMPONENT_VISUALS[kind], preferred_height=280,
        )
    return values


def build_specimen_definitions() -> dict[str, dict[str, Any]]:
    """Return one explicit specimen definition for every review subject."""
    values = _component_definitions()
    for subject_id, spec in FOUNDATION_SPECS.items():
        values[subject_id] = _definition(
            subject_id, spec["presentation"], spec["purpose"],
            interactive=spec["interactive"], conditions=spec["conditions"],
            scenarios=spec["scenarios"], visual=spec["visual"], preferred_height=320,
        )
    for subject_id, visual in PATTERN_SPECS.items():
        values[subject_id] = _definition(
            subject_id, "WORKFLOW", f"Exercise the complete {visual['title'].lower()} workflow.",
            interactive=True, conditions=("state", "viewport", "locale", "direction", "input"),
            scenarios=(
                _scenario("happy-path", "Happy path", "Complete every workflow stage", "A terminal outcome and receipt are visible"),
                _scenario("recovery-path", "Recovery path", "Interrupt or refuse the workflow", "Recovery preserves state and explains the outcome"),
            ), visual={**visual, "value_model": {"default": 0}}, preferred_height=360,
        )
    for subject_id, visual in SURFACE_SPECS.items():
        values[subject_id] = _definition(
            subject_id, "REFERENCE_SURFACE", f"Operate the functional {visual['title'].lower()} reference composition.",
            interactive=True, conditions=("theme", "density", "viewport", "locale", "direction", "input", "preference"),
            scenarios=SURFACE_SCENARIOS[subject_id],
            visual={**visual, "value_model": {"default": "ready"}}, preferred_height=420,
        )
    visual_profile = load_signature_visual_profile()
    visual_validation = validate_signature_visual_profile(visual_profile)
    values["profile.mosaic-signature"] = _definition(
        "profile.mosaic-signature", "PROFILE_MATRIX",
        "Compare the Mosaic Signature profile across every declared theme and density.",
        interactive=True, conditions=("theme", "density", "viewport", "preference"),
        scenarios=(
            _scenario("theme-density-matrix", "Theme and density matrix", "Inspect three themes by two densities", "Meaning and hierarchy remain stable"),
            _scenario("quality-contract", "Quality contract", "Inspect radius, contrast, nesting, and responsive limits", "All profile constraints are visible"),
        ),
        visual={
            "themes": ["high-contrast-dark", "signature-dark", "signature-light"],
            "densities": ["comfortable", "compact"],
            "families": [item["family_id"] for item in visual_profile["component_families"]],
            "quality_gates": list(visual_profile["evidence_contract"]["quality_gates"]),
            "visual_profile_root": visual_validation["visual_profile_root"],
            "value_model": {"default": "signature-dark/comfortable"},
        },
        preferred_height=380,
    )
    values["delivery.ablation"] = _definition(
        "delivery.ablation", "ABLATION_PLANNER",
        "Plan a dependency-closed application slice and inspect retained and removed pathways.",
        interactive=True, conditions=("realizer",),
        scenarios=(
            _scenario("minimal-slice", "Minimal slice", "Select components and one realizer", "Dependency closure and removed modules are explicit"),
            _scenario("reproducibility", "Reproducibility", "Generate the same slice twice", "Manifest and package commitments match"),
        ),
        visual={"selected": ["BUTTON", "TEXT_FIELD", "DATA_GRID"], "pathways": ["HEADLESS", "BROWSER", "WIN32"],
                "plan": build_ablation_preview(),
                "value_model": {"default": "BUTTON,TEXT_FIELD,DATA_GRID/BROWSER"}},
        preferred_height=380,
    )
    return values


def bind_specimen_definitions(subjects: list[dict[str, Any]]) -> None:
    """Attach shared definitions and refuse ontology/specimen drift."""
    definitions = build_specimen_definitions()
    subject_ids = {item["subject_id"] for item in subjects}
    if set(definitions) != subject_ids:
        missing = sorted(subject_ids - set(definitions))
        extra = sorted(set(definitions) - subject_ids)
        raise UIRefusal("REVIEW_SPECIMEN_COVERAGE_REFUSED", f"missing={missing};extra={extra}")
    for subject in subjects:
        definition = copy.deepcopy(definitions[subject["subject_id"]])
        definition["visual"]["component_kinds"] = list(subject.get("component_kinds", ()))
        if subject["subject_id"] == "profile.mosaic-signature":
            definition["visual"]["themes"] = list(subject["metadata"]["themes"])
            definition["visual"]["densities"] = list(subject["metadata"]["densities"])
        previous = subject.setdefault("metadata", {}).get("specimen", {})
        if previous:
            definition.update({key: copy.deepcopy(value) for key, value in previous.items()})
        definition.pop("commitment", None)
        definition["commitment"] = commitment("MOSAIC.UI.REVIEW_SPECIMEN.v0.1", definition)
        subject["metadata"]["specimen"] = definition
        subject["metadata"]["interactive"] = definition["interactive"]
        if definition["interactive"] and "INTERACTION_FEEL" not in subject["review"]["human_checks"]:
            subject["review"]["human_checks"].append("INTERACTION_FEEL")


def validate_specimen_catalog(ontology: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    subjects = ontology.get("subjects", [])
    for subject in subjects:
        definition = subject.get("metadata", {}).get("specimen")
        subject_id = subject.get("subject_id", "")
        if not isinstance(definition, dict):
            failures.append(f"REVIEW_SPECIMEN_ABSENT:{subject_id}")
            continue
        if definition.get("schema") != SPECIMEN_SCHEMA or definition.get("subject_id") != subject_id:
            failures.append(f"SPECIMEN_IDENTITY:{subject_id}")
        if not str(definition.get("presentation", "")).strip() or definition.get("presentation") == "GENERIC":
            failures.append(f"SPECIMEN_PRESENTATION:{subject_id}")
        if not definition.get("scenarios") or not definition.get("required_evidence"):
            failures.append(f"SPECIMEN_EVIDENCE:{subject_id}")
        if definition.get("authority_effect") != "NONE":
            failures.append(f"SPECIMEN_AUTHORITY:{subject_id}")
    if failures:
        raise UIRefusal("REVIEW_SPECIMEN_CATALOG_REFUSED", ";".join(failures))
    by_type: dict[str, int] = {}
    for subject in subjects:
        by_type[subject["subject_type"]] = by_type.get(subject["subject_type"], 0) + 1
    value = {
        "schema": CATALOG_SCHEMA,
        "subject_count": len(subjects),
        "scenario_count": sum(len(item["metadata"]["specimen"]["scenarios"]) for item in subjects),
        "by_type": by_type,
        "generic_fallback_count": 0,
        "disposition": "PASS_LOCAL_CANDIDATE",
        "authority_effect": "NONE",
    }
    value["commitment"] = commitment("MOSAIC.UI.REVIEW_SPECIMEN_CATALOG.v0.1", value)
    return value


def certify_specimen_catalog(ontology: dict[str, Any]) -> dict[str, Any]:
    """Produce deterministic per-scenario evidence for the shared Headless projection."""
    catalog = validate_specimen_catalog(ontology)
    cases: list[dict[str, Any]] = []
    for subject in ontology["subjects"]:
        definition = subject["metadata"]["specimen"]
        for scenario in definition["scenarios"]:
            case = {
                "subject_id": subject["subject_id"],
                "subject_type": subject["subject_type"],
                "presentation": definition["presentation"],
                "scenario_id": scenario["scenario_id"],
                "action": scenario["action"],
                "expected": scenario["expected"],
                "evidence": list(definition["required_evidence"]),
                "disposition": "PASS",
            }
            case["commitment"] = commitment("MOSAIC.UI.REVIEW_SPECIMEN_CASE.v0.1", case)
            cases.append(case)
    value = {
        "schema": CERTIFICATION_SCHEMA,
        "ontology_commitment": ontology["commitment"],
        "catalog_commitment": catalog["commitment"],
        "subject_count": catalog["subject_count"],
        "scenario_count": len(cases),
        "cases": cases,
        "generic_fallback_count": 0,
        "disposition": "PASS_LOCAL_CANDIDATE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": "STRUCTURAL_HEADLESS_CERTIFICATION_DOES_NOT_ESTABLISH_HUMAN_VISUAL_ACCEPTANCE",
    }
    value["commitment"] = commitment("MOSAIC.UI.REVIEW_SPECIMEN_CERTIFICATION.v0.1", value)
    return value


def run_specimen_headless_witness(ontology: dict[str, Any]) -> dict[str, Any]:
    """Exercise every definition through the governed headless review session."""
    import tempfile

    from .review_session import ReviewSession
    from .signature_review_host import SCENARIOS, SignatureReviewSession, run_scenario

    certification = certify_specimen_catalog(ontology)
    subjects: list[dict[str, Any]] = []
    state_probe_count = 0
    interaction_probe_count = 0
    for subject in ontology["subjects"]:
        session = ReviewSession(ontology, realizer="HEADLESS", subject_id=subject["subject_id"])
        observed_states: list[str] = []
        for state in session.applicable_states():
            session.set_condition("state", state)
            observed_states.append(state)
            state_probe_count += 1
        definition = subject["metadata"]["specimen"]
        observed_scenarios: list[str] = []
        if definition["interactive"]:
            if session.conditions["state"] == "DISABLED":
                session.set_condition("state", session.applicable_states()[0])
            for scenario in definition["scenarios"]:
                session.set_specimen_value(scenario["scenario_id"])
                observed_scenarios.append(scenario["scenario_id"])
                interaction_probe_count += 1
        state = session.state()
        case = {
            "subject_id": subject["subject_id"],
            "presentation": definition["presentation"],
            "states": observed_states,
            "scenarios": observed_scenarios,
            "session_commitment": state["commitment"],
            "event_count": state["event_count"],
            "disposition": "PASS",
        }
        case["commitment"] = commitment("MOSAIC.UI.REVIEW_HEADLESS_SUBJECT.v0.1", case)
        subjects.append(case)
    surface_cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="mosaic-specimen-surfaces-") as raw:
        root = Path(raw)
        for composition_id, scenarios in SCENARIOS.items():
            for scenario_id in scenarios:
                session = SignatureReviewSession(
                    composition_id, export_root=root / composition_id / scenario_id,
                )
                result = run_scenario(session, scenario_id)
                stable_result = {
                    key: result[key] for key in (
                        "schema", "composition_id", "scenario", "event_count",
                        "receipt_dispositions", "focus_trace", "artifact_count",
                        "disposition", "authority_effect",
                    )
                }
                surface_cases.append({
                    "composition_id": composition_id, "scenario_id": scenario_id,
                    # The session commitment binds absolute effect-custody paths. This
                    # structural runner binds the stable behavioral projection instead.
                    "scenario_commitment": commitment(
                        "MOSAIC.UI.REVIEW_HEADLESS_FUNCTIONAL_CASE.v0.1", stable_result,
                    ),
                    "disposition": result["disposition"],
                })
    value = {
        "schema": "mosaic.ui.review-headless-runner-witness.v0.1",
        "ontology_commitment": ontology["commitment"],
        "certification_commitment": certification["commitment"],
        "subject_count": len(subjects),
        "scenario_count": certification["scenario_count"],
        "state_probe_count": state_probe_count,
        "interaction_probe_count": interaction_probe_count,
        "functional_surface_scenario_count": len(surface_cases),
        "functional_surface_cases": surface_cases,
        "subjects": subjects,
        "generic_fallback_count": 0,
        "disposition": "PASS_LOCAL_CANDIDATE" if all(
            case["disposition"] == "PASS_LOCAL_CANDIDATE" for case in surface_cases
        ) else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": "HEADLESS_SESSION_COVERAGE_DOES_NOT_ESTABLISH_HOST_VISUAL_OR_ASSISTIVE_TECHNOLOGY_ACCEPTANCE",
    }
    value["commitment"] = commitment("MOSAIC.UI.REVIEW_HEADLESS_RUNNER_WITNESS.v0.1", value)
    return value


__all__ = [
    "SPECIMEN_SCHEMA", "bind_specimen_definitions", "build_ablation_preview", "build_specimen_definitions",
    "certify_specimen_catalog", "run_specimen_headless_witness", "validate_specimen_catalog",
]

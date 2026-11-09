"""Deterministic ontology for human and agent review of Mosaic UI itself."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from mosaic_ui_std.catalog import RUNTIME_REALIZERS, load_runtime_catalog
from mosaic_ui_std.signature import load_signature_profile
from mosaic_ui_std.visual_profile import load_signature_visual_profile, validate_signature_visual_profile

from .accessibility import KEYBOARD_CONTRACT
from .canonical import commitment, read_json
from .model import ALL_COMPONENT_KINDS, STATES, UIRefusal
from .review_specimens import bind_specimen_definitions, validate_specimen_catalog


ONTOLOGY_SCHEMA = "mosaic.ui.review-ontology.v0.1"
WITNESS_SCHEMA = "mosaic.ui.review-ontology-witness.v0.1"
DEPENDENCY_GRAPH = Path(__file__).resolve().parent / "components" / "dependencies.json"

GROUPS = (
    ("foundations", "Foundations", "FOUNDATION"),
    ("layout", "Layout", "COMPONENT"),
    ("actions-inputs", "Actions and inputs", "COMPONENT"),
    ("navigation", "Navigation", "COMPONENT"),
    ("data-display", "Data and display", "COMPONENT"),
    ("feedback-overlays", "Feedback and overlays", "COMPONENT"),
    ("patterns", "Patterns", "PATTERN"),
    ("surfaces", "Application surfaces", "SURFACE"),
    ("profiles-delivery", "Profiles and delivery", "PROFILE_OR_DELIVERY"),
)

COMPONENT_GROUPS = {
    "layout": ("WINDOW", "PANEL"),
    "actions-inputs": (
        "BUTTON", "TEXT_FIELD", "SELECT", "COMBOBOX", "CHECKBOX", "RADIO_GROUP",
        "SEGMENTED", "STEPPER",
    ),
    "navigation": ("NAVIGATION", "MENU", "TAB_BAR", "TREE"),
    "data-display": ("LABEL", "BADGE", "STATUS", "PROGRESS", "KEY_VALUE", "TABLE", "DATA_GRID", "LIST"),
    "feedback-overlays": ("NOTIFICATION", "TOOLTIP", "DIALOG"),
}

SEMANTIC_ROLES = {
    "WINDOW": "application", "PANEL": "group", "BUTTON": "button", "TEXT_FIELD": "textbox",
    "SELECT": "listbox", "COMBOBOX": "combobox", "CHECKBOX": "checkbox",
    "RADIO_GROUP": "radiogroup", "SEGMENTED": "radiogroup", "STEPPER": "group",
    "NAVIGATION": "navigation", "MENU": "menu", "TAB_BAR": "tablist", "TREE": "tree",
    "LABEL": "text", "BADGE": "status", "STATUS": "status", "PROGRESS": "progressbar",
    "KEY_VALUE": "group", "TABLE": "table", "DATA_GRID": "grid", "LIST": "listbox",
    "NOTIFICATION": "status", "TOOLTIP": "tooltip", "DIALOG": "dialog",
}

# Review-state applicability describes useful specimen states, not every state the
# underlying runtime can store. Passive content is not presented as pressable, and
# status surfaces expose lifecycle states without pretending to take focus.
REVIEW_STATES = {
    "WINDOW": ("IDLE", "FOCUSED", "DISABLED"),
    "PANEL": ("IDLE", "DISABLED"),
    "BUTTON": STATES,
    "TEXT_FIELD": ("IDLE", "HOVER", "FOCUSED", "DISABLED", "REFUSED"),
    "SELECT": ("IDLE", "HOVER", "FOCUSED", "PRESSED", "DISABLED", "REFUSED"),
    "COMBOBOX": ("IDLE", "HOVER", "FOCUSED", "PRESSED", "DISABLED", "REFUSED"),
    "CHECKBOX": ("IDLE", "HOVER", "FOCUSED", "PRESSED", "DISABLED"),
    "RADIO_GROUP": ("IDLE", "HOVER", "FOCUSED", "PRESSED", "DISABLED"),
    "SEGMENTED": ("IDLE", "HOVER", "FOCUSED", "PRESSED", "DISABLED"),
    "STEPPER": ("IDLE", "HOVER", "FOCUSED", "PRESSED", "DISABLED"),
    "NAVIGATION": ("IDLE", "HOVER", "FOCUSED", "PRESSED", "DISABLED"),
    "MENU": ("IDLE", "HOVER", "FOCUSED", "PRESSED", "DISABLED"),
    "TAB_BAR": ("IDLE", "HOVER", "FOCUSED", "PRESSED", "DISABLED"),
    "TREE": ("IDLE", "HOVER", "FOCUSED", "PRESSED", "DISABLED"),
    "LABEL": ("IDLE",),
    "BADGE": ("IDLE", "PENDING", "REFUSED"),
    "STATUS": ("IDLE", "PENDING", "REFUSED"),
    "PROGRESS": ("IDLE", "PENDING", "REFUSED"),
    "KEY_VALUE": ("IDLE",),
    "TABLE": ("IDLE",),
    "DATA_GRID": ("IDLE", "HOVER", "FOCUSED", "PRESSED", "DISABLED", "PENDING", "REFUSED"),
    "LIST": ("IDLE", "HOVER", "FOCUSED", "PRESSED", "DISABLED"),
    "NOTIFICATION": ("IDLE", "PENDING", "REFUSED"),
    "TOOLTIP": ("IDLE", "HOVER", "FOCUSED"),
    "DIALOG": ("IDLE", "FOCUSED", "PRESSED", "DISABLED", "PENDING", "REFUSED"),
}

FOUNDATIONS = (
    ("foundation.color", "Color", "Theme tokens, contrast pairs, and semantic status color."),
    ("foundation.typography", "Typography", "Type roles, families, weights, measures, and scaling."),
    ("foundation.spacing", "Spacing", "Governed spacing scale and layout gaps."),
    ("foundation.sizing", "Sizing", "Control heights, targets, viewport bounds, and density."),
    ("foundation.radii", "Radii", "Surface and control radius constraints."),
    ("foundation.icons", "Icons", "Icon meaning, sizing, labels, and fallback behavior."),
    ("foundation.motion", "Motion", "State transitions and reduced-motion behavior."),
    ("foundation.localization", "Localization", "Message references, fallback, locale, and direction."),
)

PATTERNS = (
    ("pattern.command-bar", "Command bar", ("BUTTON", "TEXT_FIELD", "MENU")),
    ("pattern.filter-search", "Filter and search", ("TEXT_FIELD", "SELECT", "BUTTON", "DATA_GRID")),
    ("pattern.selection-inspector", "Selection inspector", ("LIST", "DATA_GRID", "KEY_VALUE")),
    ("pattern.confirmation", "Confirmation", ("DIALOG", "BUTTON", "NOTIFICATION")),
    ("pattern.progress-cancel", "Progress and cancellation", ("PROGRESS", "STATUS", "BUTTON")),
    ("pattern.settings", "Settings", ("MENU", "TEXT_FIELD", "COMBOBOX", "CHECKBOX", "BUTTON")),
    ("pattern.receipt-review", "Receipt review", ("NAVIGATION", "DATA_GRID", "KEY_VALUE", "STATUS")),
)

INSPECTION_VIEWS = (
    ("anatomy", "Anatomy", "Semantic role, state, actions, properties, and tree position."),
    ("accessibility", "Accessibility", "Name, focus order, keyboard contract, target, and contrast."),
    ("tokens", "Tokens", "Resolved token values and provenance."),
    ("parity", "Parity", "Evidence-bounded HEADLESS, BROWSER, and WIN32 realization claims."),
    ("evidence", "Evidence", "Witness references, commitments, receipts, and claim boundary."),
    ("delivery", "Delivery", "Component module, shared pathways, optional pathways, and ablation impact."),
    ("lifecycle", "Lifecycle", "Version, standing, compatibility, and migration status."),
)

REVIEW_QUESTIONS = {
    "FOUNDATION": "Does this foundation remain coherent, legible, and reusable across the declared themes and conditions?",
    "COMPONENT": "Does this component communicate its purpose and state, behave predictably, and retain its semantic contract?",
    "PATTERN": "Does this composition make the intended task efficient without hiding state, evidence, or recovery?",
    "SURFACE": "Can a user complete the reference workflow and understand its status, evidence, and consequences?",
    "PROFILE": "Does this profile form a visually coherent, high-quality subset without changing component meaning?",
    "DELIVERY": "Does the selected slice retain exactly the required dependency-closed components and pathways?",
}


def _review_contract(subject_type: str, summary: str, *, interactive: bool = False) -> dict[str, Any]:
    question = REVIEW_QUESTIONS.get(subject_type, REVIEW_QUESTIONS["FOUNDATION"])
    return {
        "purpose": summary,
        "question": question,
        "use_when": "Reviewing this subject's declared visual, semantic, interaction, and delivery behavior.",
        "do_not_use_when": "A broader host, release, or production claim is required without corresponding evidence.",
        "automated_checks": ["ONTOLOGY", "SEMANTICS", "DELIVERY_CLOSURE"],
        "assisted_checks": ["VISUAL_STATES", "REALIZER_PARITY", "EVIDENCE_BINDING"],
        "human_checks": ["PURPOSE_CLARITY", "VISUAL_QUALITY", "WORKFLOW_CONFIDENCE"]
        + (["INTERACTION_FEEL"] if interactive else []),
        "completion_requires": ["DISPOSITION", "LOCAL_EVIDENCE", "CLAIM_BOUNDARY"],
    }


def _label(kind: str) -> str:
    return kind.replace("_", " ").title()


def _subject(
    subject_id: str, label: str, group_id: str, subject_type: str, summary: str,
    *, component_kinds: tuple[str, ...] = (), metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    copied_metadata = copy.deepcopy(metadata or {})
    return {
        "subject_id": subject_id,
        "label": label,
        "group_id": group_id,
        "subject_type": subject_type,
        "summary": summary,
        "component_kinds": list(component_kinds),
        "metadata": copied_metadata,
        "review": _review_contract(
            subject_type, summary, interactive=bool(copied_metadata.get("interactive")),
        ),
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
    }


def _component_subjects() -> list[dict[str, Any]]:
    catalog = load_runtime_catalog()
    graph = read_json(DEPENDENCY_GRAPH)
    by_kind = {component["kind"]: component for component in catalog["components"]}
    subjects: list[dict[str, Any]] = []
    for group_id, kinds in COMPONENT_GROUPS.items():
        for kind in kinds:
            component = by_kind[kind]
            keyboard = list(KEYBOARD_CONTRACT.get(kind, ()))
            subjects.append(_subject(
                f"component.{kind.lower().replace('_', '-')}", _label(kind), group_id, "COMPONENT",
                f"Review the {_label(kind).lower()} semantic contract, states, realizations, and delivery closure.",
                component_kinds=(kind,),
                metadata={
                    "kind": kind,
                    "component_id": component["component_id"],
                    "semantic_role": SEMANTIC_ROLES[kind],
                    "interactive": bool(keyboard),
                    "keyboard": keyboard,
                    "states": list(REVIEW_STATES[kind]),
                    "realized_by": list(component["realized_by"]),
                    "evidence": list(component["evidence"]),
                    "delivery": {
                        "component_module": graph["components"][kind],
                        "shared_pathways": list(component["realized_by"]),
                    },
                    "specimen": {
                        "default_state": "IDLE",
                        "state_matrix": list(REVIEW_STATES[kind]),
                        "review_actions": ["INTERACT", "INSPECT", "COMPARE", "SNAPSHOT"],
                    },
                },
            ))
    return subjects


def build_review_ontology() -> dict[str, Any]:
    """Build the shared, claim-bounded review ontology used by humans and agents."""
    profile = load_signature_profile()
    visual_profile = load_signature_visual_profile()
    visual_validation = validate_signature_visual_profile(visual_profile)
    graph = read_json(DEPENDENCY_GRAPH)
    subjects = [
        _subject(subject_id, label, "foundations", "FOUNDATION", summary)
        for subject_id, label, summary in FOUNDATIONS
    ]
    subjects.extend(_component_subjects())
    subjects.extend(
        _subject(subject_id, label, "patterns", "PATTERN", f"Review the {label.lower()} composition pattern.",
                 component_kinds=kinds)
        for subject_id, label, kinds in PATTERNS
    )
    subjects.extend(
        _subject(
            f"surface.{item['composition_id']}", item["name"], "surfaces", "SURFACE",
            "Review the complete Signature reference composition across its supported conditions.",
            component_kinds=tuple(item["required_kinds"]),
            metadata={"composition_id": item["composition_id"]},
        )
        for item in profile["compositions"]
    )
    subjects.extend([
        _subject("profile.mosaic-signature", "Mosaic Signature", "profiles-delivery", "PROFILE",
                 "Review the governed Signature profile, themes, densities, and quality contract.",
                 component_kinds=tuple(profile["component_kinds"]),
                 metadata={"profile_id": profile["profile_id"], "profile_version": profile["profile_version"],
                           "themes": list(profile["themes"]), "densities": list(profile["densities"]),
                           "visual_profile_id": visual_profile["visual_profile_id"],
                           "visual_profile_version": visual_profile["visual_profile_version"],
                           "visual_profile_root": visual_validation["visual_profile_root"]}),
        _subject("delivery.ablation", "Ablatable delivery", "profiles-delivery", "DELIVERY",
                 "Review exact component retention, realizer pathways, optional pathways, and package budgets.",
                 component_kinds=tuple(sorted(ALL_COMPONENT_KINDS)),
                 metadata={"realizer_pathways": sorted(graph["pathways"]),
                           "optional_pathways": sorted(graph["optional_pathways"])}),
    ])
    bind_specimen_definitions(subjects)
    groups = [
        {"group_id": group_id, "label": label, "subject_type": subject_type,
         "subject_ids": [item["subject_id"] for item in subjects if item["group_id"] == group_id]}
        for group_id, label, subject_type in GROUPS
    ]
    conditions = [
        {"condition_id": "realizer", "label": "Realizer", "default": "BROWSER",
         "options": list(RUNTIME_REALIZERS)},
        {"condition_id": "theme", "label": "Theme", "default": profile["default_theme"],
         "options": list(profile["themes"])},
        {"condition_id": "density", "label": "Density", "default": profile["default_density"],
         "options": list(profile["densities"])},
        {"condition_id": "state", "label": "State", "default": "IDLE", "options": list(STATES)},
        {"condition_id": "viewport", "label": "Viewport", "default": "DESKTOP",
         "options": ["DESKTOP", "TABLET", "MOBILE"]},
        {"condition_id": "locale", "label": "Locale", "default": "en",
         "options": ["en", "ar"]},
        {"condition_id": "direction", "label": "Direction", "default": "LTR",
         "options": ["LTR", "RTL"]},
        {"condition_id": "input", "label": "Input", "default": "KEYBOARD_POINTER",
         "options": ["KEYBOARD_POINTER", "KEYBOARD_ONLY", "POINTER_ONLY", "TOUCH"]},
        {"condition_id": "preference", "label": "Preference", "default": "STANDARD",
         "options": ["STANDARD", "REDUCED_MOTION", "HIGH_CONTRAST"]},
    ]
    value = {
        "schema": ONTOLOGY_SCHEMA,
        "ontology_id": "mosaic-ui-review-ontology",
        "groups": groups,
        "subjects": subjects,
        "conditions": conditions,
        "inspection_views": [
            {"view_id": view_id, "label": label, "summary": summary}
            for view_id, label, summary in INSPECTION_VIEWS
        ],
        "catalog_root": commitment("MOSAIC.UI.STD.RUNTIME_CATALOG.v0.1", load_runtime_catalog()),
        "profile_id": profile["profile_id"],
        "profile_version": profile["profile_version"],
        "visual_profile_root": visual_validation["visual_profile_root"],
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": (
            "ONTOLOGY_COVERAGE_AND_LOCAL_REVIEW_METADATA_DO_NOT_ESTABLISH_BROAD_HOST_VISUAL_"
            "ASSISTIVE_TECHNOLOGY_OR_PRODUCTION_ACCEPTANCE"
        ),
    }
    validate_review_ontology(value)
    value["commitment"] = commitment("MOSAIC.UI.REVIEW_ONTOLOGY.v0.1", value)
    return value


def validate_review_ontology(value: Any) -> dict[str, Any]:
    failures: list[str] = []
    if not isinstance(value, dict) or value.get("schema") != ONTOLOGY_SCHEMA:
        raise UIRefusal("REVIEW_ONTOLOGY_REFUSED", "SCHEMA")
    if value.get("authority_effect") != "NONE":
        failures.append("AUTHORITY_EFFECT")
    groups, subjects, conditions = value.get("groups"), value.get("subjects"), value.get("conditions")
    if not isinstance(groups, list) or not isinstance(subjects, list) or not isinstance(conditions, list):
        raise UIRefusal("REVIEW_ONTOLOGY_REFUSED", "COLLECTION_SHAPE")
    group_ids = [item.get("group_id") for item in groups if isinstance(item, dict)]
    if group_ids != [item[0] for item in GROUPS] or len(set(group_ids)) != len(group_ids):
        failures.append("GROUP_SET_OR_ORDER")
    subject_ids = [item.get("subject_id") for item in subjects if isinstance(item, dict)]
    if len(subject_ids) != len(subjects) or len(set(subject_ids)) != len(subject_ids):
        failures.append("SUBJECT_IDS")
    grouped_ids = [subject_id for group in groups for subject_id in group.get("subject_ids", [])]
    if grouped_ids != [item["subject_id"] for group_id in group_ids for item in subjects
                       if item.get("group_id") == group_id]:
        failures.append("GROUP_MEMBERSHIP_OR_ORDER")
    if set(grouped_ids) != set(subject_ids):
        failures.append("GROUP_COVERAGE")
    component_subjects = [item for item in subjects if item.get("subject_type") == "COMPONENT"]
    component_kinds = [item.get("metadata", {}).get("kind") for item in component_subjects]
    if len(component_kinds) != 25 or set(component_kinds) != set(ALL_COMPONENT_KINDS):
        failures.append("COMPONENT_KIND_COVERAGE")
    catalog_by_kind = {item["kind"]: item for item in load_runtime_catalog()["components"]}
    for subject in component_subjects:
        metadata = subject.get("metadata", {})
        kind = metadata.get("kind")
        source = catalog_by_kind.get(kind)
        if source is None or metadata.get("realized_by") != source["realized_by"] \
                or metadata.get("evidence") != source["evidence"]:
            failures.append(f"COMPONENT_CLAIM_DRIFT:{kind}")
        expected_states = list(REVIEW_STATES.get(kind, ()))
        specimen = metadata.get("specimen", {})
        if not expected_states or metadata.get("states") != expected_states \
                or specimen.get("state_matrix") != expected_states \
                or specimen.get("default_state") not in expected_states:
            failures.append(f"COMPONENT_REVIEW_STATES:{kind}")
    for subject in subjects:
        review = subject.get("review")
        required = {"purpose", "question", "use_when", "do_not_use_when", "automated_checks",
                    "assisted_checks", "human_checks", "completion_requires"}
        if not isinstance(review, dict) or set(review) != required:
            failures.append(f"REVIEW_CONTRACT:{subject.get('subject_id')}")
    condition_ids = [item.get("condition_id") for item in conditions if isinstance(item, dict)]
    expected_conditions = ["realizer", "theme", "density", "state", "viewport", "locale",
                           "direction", "input", "preference"]
    if condition_ids != expected_conditions or len(set(condition_ids)) != len(condition_ids):
        failures.append("CONDITION_SET_OR_ORDER")
    for condition in conditions:
        options = condition.get("options")
        if not isinstance(options, list) or len(options) != len(set(options)) \
                or condition.get("default") not in options:
            failures.append(f"CONDITION_OPTIONS:{condition.get('condition_id')}")
    if failures:
        raise UIRefusal("REVIEW_ONTOLOGY_REFUSED", ";".join(sorted(failures)))
    specimen_validation = validate_specimen_catalog(value)
    return {
        "schema": "mosaic.ui.review-ontology-validation.v0.1",
        "group_count": len(groups), "subject_count": len(subjects),
        "component_count": len(component_subjects), "condition_count": len(conditions),
        "specimen_count": specimen_validation["subject_count"],
        "specimen_scenario_count": specimen_validation["scenario_count"],
        "disposition": "PASS_LOCAL_CANDIDATE", "authority_effect": "NONE",
    }


def review_ontology_witness() -> dict[str, Any]:
    ontology = build_review_ontology()
    validation = validate_review_ontology(ontology)
    value = {
        "schema": WITNESS_SCHEMA,
        "ontology_commitment": ontology["commitment"],
        "catalog_root": ontology["catalog_root"],
        "group_count": validation["group_count"],
        "subject_count": validation["subject_count"],
        "component_count": validation["component_count"],
        "condition_count": validation["condition_count"],
        "disposition": "PASS_LOCAL_CANDIDATE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": ontology["claim_boundary"],
    }
    value["commitment"] = commitment("MOSAIC.UI.REVIEW_ONTOLOGY_WITNESS.v0.1", value)
    return value


__all__ = ["REVIEW_STATES", "build_review_ontology", "review_ontology_witness", "validate_review_ontology"]

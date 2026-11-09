"""Deterministic C-change preflight and exact quick-check evaluation.

This module is a pure policy surface.  It classifies a proposed C change,
derives the complete check denominator, and validates externally produced
check evidence.  It never edits source, launches a compiler, or grants tool
dispatch authority.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import PurePosixPath
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .amcas import BOUNDARY


STANDARD_SCHEMA = "mosaic.ucm.c-coding-standard.v0.1"
PROPOSAL_SCHEMA = "mosaic.ucm.c-change-proposal.v0.1"
PREFLIGHT_SCHEMA = "mosaic.ucm.c-change-preflight.v0.1"
RESULT_SCHEMA = "mosaic.ucm.c-check-result.v0.1"
EVALUATION_SCHEMA = "mosaic.ucm.c-check-evaluation.v0.1"

CHANNELS = {
    "MODEL_INPUT", "MODEL_DRAFT", "VISIBLE_OUTPUT", "TOOL_PROPOSAL",
    "TOOL_DISPATCH", "TOOL_RESULT", "JOURNAL_WRITE",
}
INTEGRATION_MODES = {"SIDECAR_PARTIAL", "ENFORCED_HOST"}
ALLOWED_EFFECT_CLASSES = {"READ_SOURCE", "WRITE_WORKSPACE", "LOCAL_PROCESS"}
FORBIDDEN_EFFECT_CLASSES = {
    "NETWORK", "INSTALL", "DEPLOY", "AUTHORITY_CHANGE", "WRITE_PROTECTED",
}
CHANGE_CLASSES = {
    "BUILD_SYSTEM", "C_RUNTIME", "DOCUMENTATION", "PERSISTENCE", "PLATFORM",
    "PUBLIC_ABI", "PYTHON_TOOLING", "RENDER", "RNG", "SIMULATION", "TESTS",
    "WORLD_INDEXING",
}

BASE_CHECKS = {
    "ARCHITECTURE_BOUNDARY", "C17_WARNING_CLEAN", "NO_UNDECLARED_EFFECTS",
    "SOURCE_BOUND", "TOOLCHAIN_PIN",
}
CHECKS_BY_CLASS = {
    "BUILD_SYSTEM": {"C17_WARNING_CLEAN", "TOOLCHAIN_PIN"},
    "C_RUNTIME": {"CHECKED_ARITHMETIC", "OWNERSHIP_LIFETIME", "UNIT_TESTS"},
    "DOCUMENTATION": set(),
    "PERSISTENCE": {"CRASH_RECOVERY", "FUZZ_WORLD_FILES", "SANITIZER",
                    "SAVE_CODEC"},
    "PLATFORM": {"PORTABILITY_MATRIX", "UNIT_TESTS"},
    "PUBLIC_ABI": {"ABI_COMPATIBILITY", "OWNERSHIP_LIFETIME"},
    "PYTHON_TOOLING": {"FIXTURE_VALIDATION", "PYTHON_NONAUTHORITATIVE"},
    "RENDER": {"RENDER_SIMULATION_SEPARATION", "UNIT_TESTS"},
    "RNG": {"DETERMINISM_REPLAY", "RNG_GOLDEN_VECTORS"},
    "SIMULATION": {"DETERMINISM_REPLAY", "FIXED_STEP", "UNIT_TESTS"},
    "TESTS": {"TEST_IDENTITY"},
    "WORLD_INDEXING": {"CHECKED_ARITHMETIC", "CHUNK_INDEX_PROPERTIES",
                       "SANITIZER"},
}
CHECK_ROLES = {
    "ABI_COMPATIBILITY": "STATIC",
    "ARCHITECTURE_BOUNDARY": "STATIC",
    "C17_WARNING_CLEAN": "COMPILER",
    "CHECKED_ARITHMETIC": "STATIC",
    "CHUNK_INDEX_PROPERTIES": "PROPERTY",
    "CRASH_RECOVERY": "RECOVERY",
    "DETERMINISM_REPLAY": "COURT",
    "FIXED_STEP": "PROPERTY",
    "FIXTURE_VALIDATION": "INTEGRATION",
    "FUZZ_WORLD_FILES": "FUZZ",
    "NO_UNDECLARED_EFFECTS": "STATIC",
    "OWNERSHIP_LIFETIME": "STATIC",
    "PORTABILITY_MATRIX": "PORTABILITY",
    "PYTHON_NONAUTHORITATIVE": "STATIC",
    "RENDER_SIMULATION_SEPARATION": "ARCHITECTURE",
    "RNG_GOLDEN_VECTORS": "PROPERTY",
    "SANITIZER": "SANITIZER",
    "SAVE_CODEC": "PROPERTY",
    "SOURCE_BOUND": "CUSTODY",
    "TEST_IDENTITY": "STATIC",
    "TOOLCHAIN_PIN": "CUSTODY",
    "UNIT_TESTS": "TARGETED",
}


def _identifier(value: Any, code: str) -> str:
    require(type(value) is str and value == value.strip() and 0 < len(value) <= 192
            and all(ch.isalnum() or ch in "._:-" for ch in value), code)
    return value


def _identifiers(value: Any, allowed: set[str], code: str,
                 *, allow_empty: bool = False) -> list[str]:
    require(type(value) is list and value == sorted(set(value))
            and (allow_empty or bool(value)), code)
    require(set(value) <= allowed, code)
    return list(value)


def _paths(value: Any, code: str) -> list[str]:
    require(type(value) is list and bool(value) and value == sorted(set(value)), code)
    normalized: list[str] = []
    for raw in value:
        require(type(raw) is str and raw == raw.strip() and raw == raw.replace("\\", "/")
                and 0 < len(raw) <= 512, code)
        path = PurePosixPath(raw)
        require(not path.is_absolute() and ":" not in raw and ".." not in path.parts
                and "." not in path.parts and str(path) == raw, code)
        normalized.append(raw)
    return normalized


def _infer_change_classes(paths: list[str]) -> set[str]:
    inferred: set[str] = set()
    for path in paths:
        lower = path.lower()
        suffix = PurePosixPath(lower).suffix
        if lower.startswith("include/") and suffix == ".h":
            inferred.add("PUBLIC_ABI")
        if lower.startswith("src/persistence/"):
            inferred.add("PERSISTENCE")
        elif lower.startswith("src/render/"):
            inferred.add("RENDER")
        elif lower.startswith("src/platform/"):
            inferred.add("PLATFORM")
        elif lower.startswith("src/world/"):
            inferred.add("C_RUNTIME")
        elif lower.startswith("src/core/"):
            inferred.update({"C_RUNTIME", "SIMULATION"})
        elif suffix in {".c", ".h"}:
            inferred.add("C_RUNTIME")
        if "chunk" in lower or "coordinate" in lower or "index" in lower:
            inferred.add("WORLD_INDEXING")
        if "rng" in lower or "random" in lower or "seed" in lower:
            inferred.add("RNG")
        if suffix == ".py" or lower.startswith("tools/"):
            inferred.add("PYTHON_TOOLING")
        if lower.startswith("tests/") or PurePosixPath(lower).name.startswith("test_"):
            inferred.add("TESTS")
        if (PurePosixPath(lower).name in {"cmakelists.txt", "makefile", "meson.build"}
                or lower.startswith("build/") or lower.startswith("cmake/")):
            inferred.add("BUILD_SYSTEM")
        if suffix in {".md", ".rst"} or lower.startswith("docs/"):
            inferred.add("DOCUMENTATION")
    return inferred


def c_coding_standard() -> dict[str, Any]:
    obligations = [
        "EXACT_SOURCE_AND_TOOLCHAIN_CUSTODY",
        "C17_OR_EXPLICITLY_PINNED_SUCCESSOR_DIALECT",
        "WARNING_CLEAN_SUPPORTED_BUILDS",
        "CHECKED_INTEGER_SIZE_AND_OFFSET_ARITHMETIC",
        "EXPLICIT_POINTER_OWNERSHIP_AND_LIFETIME",
        "BOUNDS_SAFE_CHUNK_AND_COORDINATE_INDEXING",
        "DETERMINISTIC_FIXED_STEP_AND_RNG",
        "VERSIONED_BOUNDED_BINARY_SAVE_FORMATS",
        "ATOMIC_CRASH_SAFE_SAVE_COMMIT_AND_RECOVERY",
        "NO_UNDEFINED_BEHAVIOR_DEPENDENCY",
        "RENDER_SIMULATION_PERSISTENCE_PLANE_SEPARATION",
        "PYTHON_AUTHORING_AND_VERIFICATION_ONLY",
        "NO_NETWORK_INSTALL_DEPLOY_OR_AUTHORITY_EFFECT",
    ]
    body = {"schema": STANDARD_SCHEMA, "standard_id": "UCM.PIPPI.C17.SAFE_V0_1",
            "language_standard": "C17", "obligations": obligations,
            "change_classes": sorted(CHANGE_CLASSES),
            "allowed_effect_classes": sorted(ALLOWED_EFFECT_CLASSES),
            "forbidden_effect_classes": sorted(FORBIDDEN_EFFECT_CLASSES),
            "checks": [{"check_id": key, "role": CHECK_ROLES[key]}
                       for key in sorted(CHECK_ROLES)],
            "native_semantic_authority": "NATIVE_C",
            "python_role": "AUTHORING_VERIFICATION_ONLY", **BOUNDARY}
    return {**body, "standard_root": root(body)}


def build_c_change_preflight(*, proposal_id: str, subject_root: str,
                             source_manifest_root: str, language_standard: str,
                             compiler_profile_root: str,
                             architecture_contract_root: str,
                             change_classes: list[str], changed_paths: list[str],
                             declared_write_paths: list[str],
                             declared_check_ids: list[str],
                             requested_effect_classes: list[str],
                             integration_mode: str,
                             mediated_channels: list[str],
                             native_semantic_authority: str,
                             python_role: str) -> dict[str, Any]:
    proposal_id = _identifier(proposal_id, "C_PREFLIGHT_PROPOSAL_ID_INVALID")
    for value in (subject_root, source_manifest_root, compiler_profile_root,
                  architecture_contract_root):
        require_root(value)
    declared_classes = _identifiers(change_classes, CHANGE_CLASSES,
                                    "C_PREFLIGHT_CHANGE_CLASSES_INVALID")
    changed = _paths(changed_paths, "C_PREFLIGHT_CHANGED_PATHS_INVALID")
    write_paths = _paths(declared_write_paths, "C_PREFLIGHT_WRITE_PATHS_INVALID")
    checks = _identifiers(declared_check_ids, set(CHECK_ROLES),
                          "C_PREFLIGHT_CHECK_IDS_INVALID", allow_empty=True)
    effects = _identifiers(requested_effect_classes,
                           ALLOWED_EFFECT_CLASSES | FORBIDDEN_EFFECT_CLASSES,
                           "C_PREFLIGHT_EFFECT_CLASSES_INVALID", allow_empty=True)
    channels = _identifiers(mediated_channels, CHANNELS,
                            "C_PREFLIGHT_CHANNELS_INVALID", allow_empty=True)
    require(integration_mode in INTEGRATION_MODES, "C_PREFLIGHT_MODE_INVALID")
    require(type(language_standard) is str, "C_PREFLIGHT_DIALECT_INVALID")
    require(type(native_semantic_authority) is str and type(python_role) is str,
            "C_PREFLIGHT_AUTHORITY_FIELDS_INVALID")

    inferred = _infer_change_classes(changed)
    required_checks = set(BASE_CHECKS)
    for change_class in set(declared_classes) | inferred:
        required_checks.update(CHECKS_BY_CLASS[change_class])

    violations: list[dict[str, str]] = []
    def violation(code: str, obligation_id: str, detail: str) -> None:
        violations.append({"code": code, "obligation_id": obligation_id,
                           "detail": detail})

    if language_standard != "C17":
        violation("C_PREFLIGHT_DIALECT_REFUSED", "C_DIALECT_PINNED",
                  f"expected C17, received {language_standard}")
    if not set(changed) <= set(write_paths):
        violation("C_PREFLIGHT_WRITE_SET_INCOMPLETE", "DECLARED_WRITE_SET",
                  ",".join(sorted(set(changed) - set(write_paths))))
    undeclared_classes = sorted(inferred - set(declared_classes))
    if undeclared_classes:
        violation("C_PREFLIGHT_CHANGE_CLASS_INCOMPLETE", "CHANGE_CLASSIFICATION",
                  ",".join(undeclared_classes))
    forbidden = sorted(set(effects) & FORBIDDEN_EFFECT_CLASSES)
    if forbidden:
        violation("C_PREFLIGHT_FORBIDDEN_EFFECT", "NO_FORBIDDEN_EFFECTS",
                  ",".join(forbidden))
    if native_semantic_authority != "NATIVE_C":
        violation("C_PREFLIGHT_NATIVE_AUTHORITY_INVALID", "NATIVE_C_AUTHORITY",
                  native_semantic_authority)
    if python_role != "AUTHORING_VERIFICATION_ONLY":
        violation("C_PREFLIGHT_PYTHON_AUTHORITY_INVALID", "PYTHON_NONAUTHORITATIVE",
                  python_role)
    if integration_mode == "ENFORCED_HOST":
        violation("C_PREFLIGHT_HOST_ATTESTATION_REQUIRED", "PIPPI_HOST_COVERAGE",
                  "legacy preflight accepts channel declarations only; use an attested Pippi context")
    missing_checks = sorted(required_checks - set(checks))
    if missing_checks:
        violation("C_PREFLIGHT_REQUIRED_CHECKS_MISSING", "CHECK_DENOMINATOR",
                  ",".join(missing_checks))

    proposal_body = {"schema": PROPOSAL_SCHEMA, "proposal_id": proposal_id,
        "subject_root": subject_root, "source_manifest_root": source_manifest_root,
        "language_standard": language_standard,
        "compiler_profile_root": compiler_profile_root,
        "architecture_contract_root": architecture_contract_root,
        "change_classes": declared_classes, "changed_paths": changed,
        "declared_write_paths": write_paths, "declared_check_ids": checks,
        "requested_effect_classes": effects, "integration_mode": integration_mode,
        "mediated_channels": channels,
        "native_semantic_authority": native_semantic_authority,
        "python_role": python_role}
    proposal = {**proposal_body, "proposal_root": root(proposal_body)}
    decision = "REFUSED" if violations else "READY_FOR_QUICK_CHECKS"
    body = {"schema": PREFLIGHT_SCHEMA, "standard_root": c_coding_standard()["standard_root"],
            "proposal": proposal, "inferred_change_classes": sorted(inferred),
            "required_check_ids": sorted(required_checks),
            "missing_check_ids": missing_checks, "violations": violations,
            "decision": decision, "tool_dispatch_authorized": False, **BOUNDARY}
    return {**body, "preflight_root": root(body)}


def validate_c_change_preflight(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "standard_root", "proposal",
        "inferred_change_classes", "required_check_ids", "missing_check_ids",
        "violations", "decision", "tool_dispatch_authorized", "standing",
        "authority_effect", "real_a5", "g0", "preflight_root"})
    proposal = exact_keys(item["proposal"], {"schema", "proposal_id", "subject_root",
        "source_manifest_root", "language_standard", "compiler_profile_root",
        "architecture_contract_root", "change_classes", "changed_paths",
        "declared_write_paths", "declared_check_ids", "requested_effect_classes",
        "integration_mode", "mediated_channels", "native_semantic_authority",
        "python_role", "proposal_root"})
    expected = build_c_change_preflight(**{key: deepcopy(value)
        for key, value in proposal.items() if key not in {"schema", "proposal_root"}})
    require(item == expected, "C_PREFLIGHT_INVALID")
    return deepcopy(item)


def evaluate_c_check_results(*, preflight: dict[str, Any],
                             check_results: list[dict[str, Any]]) -> dict[str, Any]:
    preflight = validate_c_change_preflight(preflight)
    require(preflight["decision"] == "READY_FOR_QUICK_CHECKS",
            "C_CHECKS_PREFLIGHT_REFUSED")
    require(type(check_results) is list, "C_CHECK_RESULTS_INVALID")
    required = set(preflight["required_check_ids"])
    subject_root = preflight["proposal"]["subject_root"]
    by_id: dict[str, dict[str, Any]] = {}
    for raw in check_results:
        item = exact_keys(raw, {"schema", "check_id", "status", "subject_root",
                                "tool_root", "invocation_root", "evidence_root"})
        require(item["schema"] == RESULT_SCHEMA, "C_CHECK_RESULT_SCHEMA_INVALID")
        check_id = _identifier(item["check_id"], "C_CHECK_RESULT_ID_INVALID")
        require(check_id in required and check_id not in by_id,
                "C_CHECK_RESULT_UNKNOWN_OR_DUPLICATE")
        require(item["status"] in {"PASS", "FAIL", "NOT_RUN"},
                "C_CHECK_RESULT_STATUS_INVALID")
        require(item["subject_root"] == subject_root, "C_CHECK_RESULT_SUBJECT_MISMATCH")
        if item["status"] == "NOT_RUN":
            require(item["tool_root"] is None and item["invocation_root"] is None
                    and item["evidence_root"] is None,
                    "C_CHECK_NOT_RUN_ROOTS_INVALID")
        else:
            for field in ("tool_root", "invocation_root", "evidence_root"):
                require_root(item[field])
        by_id[check_id] = deepcopy(item)
    missing = sorted(required - set(by_id))
    failed = sorted(key for key, row in by_id.items() if row["status"] == "FAIL")
    not_run = sorted(key for key, row in by_id.items() if row["status"] == "NOT_RUN")
    decision = "PASS" if not missing and not failed and not not_run else "REFUSED"
    reason_codes = []
    if missing:
        reason_codes.append("C_CHECK_RESULTS_MISSING")
    if failed:
        reason_codes.append("C_CHECK_RESULTS_FAILED")
    if not_run:
        reason_codes.append("C_CHECK_RESULTS_NOT_RUN")
    body = {"schema": EVALUATION_SCHEMA, "preflight_root": preflight["preflight_root"],
            "subject_root": subject_root,
            "check_results": [by_id[key] for key in sorted(by_id)],
            "required_check_ids": sorted(required), "missing_check_ids": missing,
            "failed_check_ids": failed, "not_run_check_ids": not_run,
            "completed_denominator": len(required) - len(missing) - len(not_run),
            "fixed_denominator": len(required), "decision": decision,
            "reason_codes": reason_codes, "tool_dispatch_authorized": False,
            **BOUNDARY}
    return {**body, "evaluation_root": root(body)}

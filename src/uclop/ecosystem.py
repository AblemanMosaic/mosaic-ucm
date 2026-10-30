from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .canonical import exact_keys, require, require_root, root


APPLICATION_TYPES = {"AGENT", "ADAPTER", "SERVICE", "UI", "WORKFLOW"}
ADAPTER_KINDS = {"IN_PROCESS", "LOCAL_SERVICE", "REMOTE_SERVICE", "HARDWARE", "HUMAN_CEREMONY"}
EFFECT_CLASSES = ("NONE", "READ_EXTERNAL", "WRITE_LOCAL", "NETWORK", "HOST_SECURITY", "PRODUCTION")
STAGES = ("D2_INDEPENDENT_REVIEW", "D3_REAL_IDENTITY_SEATING", "D4_PROTECTED_INSTALLATION", "D5_PRODUCTION_ACTIVATION")
EFFECT_MINIMUM_STAGE = {
    "NONE": "D2_INDEPENDENT_REVIEW",
    "READ_EXTERNAL": "D3_REAL_IDENTITY_SEATING",
    "WRITE_LOCAL": "D4_PROTECTED_INSTALLATION",
    "NETWORK": "D4_PROTECTED_INSTALLATION",
    "HOST_SECURITY": "D4_PROTECTED_INSTALLATION",
    "PRODUCTION": "D5_PRODUCTION_ACTIVATION",
}
_ID = re.compile(r"^[a-z][a-z0-9_.-]{2,63}$")
_VERSION = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


def _identifier(value: Any, code: str, path: str) -> str:
    require(type(value) is str and bool(_ID.fullmatch(value)), code, path)
    return value


def _version(value: Any, path: str) -> str:
    require(type(value) is str and bool(_VERSION.fullmatch(value)), "SEMANTIC_VERSION_INVALID", path)
    return value


def _sorted_unique(values: Any, code: str, path: str, *, identifiers: bool = False) -> list[str]:
    require(type(values) is list and all(type(item) is str for item in values), code, path)
    checked = sorted(values)
    require(values == checked and len(values) == len(set(values)), code, path)
    if identifiers:
        for index, value in enumerate(values):
            _identifier(value, code, f"{path}[{index}]")
    return list(values)


def effect_rank(value: Any) -> int:
    require(value in EFFECT_CLASSES, "EFFECT_CLASS_INVALID")
    return EFFECT_CLASSES.index(value)


def stage_rank(value: Any) -> int:
    require(value in STAGES, "DEPLOYMENT_STAGE_INVALID")
    return STAGES.index(value)


def make_capability_descriptor(
    *,
    capability_id: str,
    version: str,
    input_schema_root: str,
    output_schema_root: str,
    implementation_root: str,
    dependencies: list[str],
    effect_class: str,
    adapter_kind: str,
    deterministic: bool,
    idempotent: bool,
) -> dict[str, Any]:
    capability_id = _identifier(capability_id, "CAPABILITY_ID_INVALID", "$.capability_id")
    version = _version(version, "$.version")
    dependencies = _sorted_unique(dependencies, "CAPABILITY_DEPENDENCY_SET_INVALID", "$.dependencies", identifiers=True)
    require(capability_id not in dependencies, "CAPABILITY_SELF_DEPENDENCY")
    require(effect_class in EFFECT_CLASSES, "EFFECT_CLASS_INVALID")
    require(adapter_kind in ADAPTER_KINDS, "CAPABILITY_ADAPTER_KIND_INVALID")
    require(type(deterministic) is bool and type(idempotent) is bool, "CAPABILITY_BEHAVIOR_FLAG_INVALID")
    minimum_stage = EFFECT_MINIMUM_STAGE[effect_class]
    body = {
        "schema": "ucl.ucm.capability_descriptor.v1",
        "capability_id": capability_id,
        "version": version,
        "input_schema_root": require_root(input_schema_root),
        "output_schema_root": require_root(output_schema_root),
        "implementation_root": require_root(implementation_root),
        "dependencies": dependencies,
        "effect_class": effect_class,
        "minimum_stage": minimum_stage,
        "adapter_kind": adapter_kind,
        "deterministic": deterministic,
        "idempotent": idempotent,
        "external_decision_required": effect_class != "NONE",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "descriptor_root": root(body)}


def verify_capability_descriptor(value: Any) -> dict[str, Any]:
    item = exact_keys(
        value,
        {
            "schema", "capability_id", "version", "input_schema_root", "output_schema_root",
            "implementation_root", "dependencies", "effect_class", "minimum_stage", "adapter_kind",
            "deterministic", "idempotent", "external_decision_required", "standing",
            "authority_effect", "descriptor_root",
        },
        "$.capability",
    )
    body = {key: item[key] for key in item if key != "descriptor_root"}
    require(item["schema"] == "ucl.ucm.capability_descriptor.v1" and item["descriptor_root"] == root(body), "CAPABILITY_DESCRIPTOR_ROOT_INVALID")
    _identifier(item["capability_id"], "CAPABILITY_ID_INVALID", "$.capability.capability_id")
    _version(item["version"], "$.capability.version")
    for name in ("input_schema_root", "output_schema_root", "implementation_root"):
        require_root(item[name], f"$.capability.{name}")
    _sorted_unique(item["dependencies"], "CAPABILITY_DEPENDENCY_SET_INVALID", "$.capability.dependencies", identifiers=True)
    require(item["capability_id"] not in item["dependencies"], "CAPABILITY_SELF_DEPENDENCY")
    require(item["effect_class"] in EFFECT_CLASSES and item["minimum_stage"] == EFFECT_MINIMUM_STAGE[item["effect_class"]], "CAPABILITY_STAGE_EFFECT_MISMATCH")
    require(item["adapter_kind"] in ADAPTER_KINDS and type(item["deterministic"]) is bool and type(item["idempotent"]) is bool, "CAPABILITY_BEHAVIOR_INVALID")
    require(item["external_decision_required"] is (item["effect_class"] != "NONE"), "CAPABILITY_DECISION_REQUIREMENT_INVALID")
    require(item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "CAPABILITY_EFFECT_INVALID")
    return deepcopy(body)


def compile_capability_registry(*, subject_root: str, descriptors: list[dict[str, Any]]) -> dict[str, Any]:
    require(type(descriptors) is list and descriptors, "CAPABILITY_REGISTRY_EMPTY")
    verified: dict[str, dict[str, Any]] = {}
    for descriptor in descriptors:
        verify_capability_descriptor(descriptor)
        capability_id = descriptor["capability_id"]
        require(capability_id not in verified, "CAPABILITY_DUPLICATE_ID", detail=capability_id)
        verified[capability_id] = deepcopy(descriptor)
    for capability_id, descriptor in verified.items():
        require(set(descriptor["dependencies"]).issubset(verified), "CAPABILITY_DEPENDENCY_UNKNOWN", detail=capability_id)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(capability_id: str) -> None:
        require(capability_id not in visiting, "CAPABILITY_DEPENDENCY_CYCLE", detail=capability_id)
        if capability_id in visited:
            return
        visiting.add(capability_id)
        for dependency in verified[capability_id]["dependencies"]:
            visit(dependency)
        visiting.remove(capability_id)
        visited.add(capability_id)

    for capability_id in sorted(verified):
        visit(capability_id)
    ordered = [verified[key] for key in sorted(verified)]
    body = {
        "schema": "ucl.ucm.capability_registry.v1",
        "subject_root": require_root(subject_root),
        "capabilities": ordered,
        "capability_count": len(ordered),
        "capability_roots": {item["capability_id"]: item["descriptor_root"] for item in ordered},
        "default_policy": "DENY",
        "executable_effect_classes": ["NONE"],
        "maximum_executable_stage": "D2_INDEPENDENT_REVIEW",
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "registry_root": root(body)}


def verify_capability_registry(value: Any, *, expected_subject_root: str | None = None) -> dict[str, Any]:
    item = exact_keys(
        value,
        {
            "schema", "subject_root", "capabilities", "capability_count", "capability_roots",
            "default_policy", "executable_effect_classes", "maximum_executable_stage",
            "standing", "authority_effect", "registry_root",
        },
        "$.registry",
    )
    body = {key: item[key] for key in item if key != "registry_root"}
    require(item["schema"] == "ucl.ucm.capability_registry.v1" and item["registry_root"] == root(body), "CAPABILITY_REGISTRY_ROOT_INVALID")
    if expected_subject_root is not None:
        require(item["subject_root"] == require_root(expected_subject_root), "CAPABILITY_REGISTRY_SUBJECT_MISMATCH")
    else:
        require_root(item["subject_root"])
    require(type(item["capabilities"]) is list and item["capability_count"] == len(item["capabilities"]) and item["capability_count"] > 0, "CAPABILITY_REGISTRY_COUNT_INVALID")
    ids: list[str] = []
    roots: dict[str, str] = {}
    for descriptor in item["capabilities"]:
        verify_capability_descriptor(descriptor)
        ids.append(descriptor["capability_id"])
        roots[descriptor["capability_id"]] = descriptor["descriptor_root"]
    require(ids == sorted(ids) and len(ids) == len(set(ids)) and item["capability_roots"] == roots, "CAPABILITY_REGISTRY_INDEX_INVALID")
    require(item["default_policy"] == "DENY" and item["executable_effect_classes"] == ["NONE"] and item["maximum_executable_stage"] == "D2_INDEPENDENT_REVIEW", "CAPABILITY_REGISTRY_CEILING_INVALID")
    require(item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "CAPABILITY_REGISTRY_EFFECT_INVALID")
    return deepcopy(body)


def make_application_manifest(
    *,
    application_id: str,
    version: str,
    application_type: str,
    implementation_root: str,
    input_schema_root: str,
    output_schema_root: str,
    data_domains: list[str],
    obligation_roots: list[str],
    requested_capabilities: list[str],
    supported_platforms: list[str],
    maximum_effect_class: str,
) -> dict[str, Any]:
    application_id = _identifier(application_id, "APPLICATION_ID_INVALID", "$.application_id")
    require(application_type in APPLICATION_TYPES, "APPLICATION_TYPE_INVALID")
    data_domains = _sorted_unique(data_domains, "APPLICATION_DATA_DOMAIN_SET_INVALID", "$.data_domains", identifiers=True)
    requested_capabilities = _sorted_unique(requested_capabilities, "APPLICATION_CAPABILITY_SET_INVALID", "$.requested_capabilities", identifiers=True)
    supported_platforms = _sorted_unique(supported_platforms, "APPLICATION_PLATFORM_SET_INVALID", "$.supported_platforms")
    require(supported_platforms and set(supported_platforms).issubset({"POSIX", "WINDOWS"}), "APPLICATION_PLATFORM_INVALID")
    require(type(obligation_roots) is list and obligation_roots == sorted(obligation_roots) and len(obligation_roots) == len(set(obligation_roots)) and obligation_roots, "APPLICATION_OBLIGATION_SET_INVALID")
    for index, value in enumerate(obligation_roots):
        require_root(value, f"$.obligation_roots[{index}]")
    require(maximum_effect_class in EFFECT_CLASSES, "EFFECT_CLASS_INVALID")
    body = {
        "schema": "ucl.ucm.application_manifest.v1",
        "application_id": application_id,
        "version": _version(version, "$.version"),
        "application_type": application_type,
        "implementation_root": require_root(implementation_root),
        "input_schema_root": require_root(input_schema_root),
        "output_schema_root": require_root(output_schema_root),
        "data_domains": data_domains,
        "obligation_roots": list(obligation_roots),
        "requested_capabilities": requested_capabilities,
        "supported_platforms": supported_platforms,
        "maximum_effect_class": maximum_effect_class,
        "automatic_authority": False,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "manifest_root": root(body)}


def verify_application_manifest(value: Any) -> dict[str, Any]:
    item = exact_keys(
        value,
        {
            "schema", "application_id", "version", "application_type", "implementation_root",
            "input_schema_root", "output_schema_root", "data_domains", "obligation_roots",
            "requested_capabilities", "supported_platforms", "maximum_effect_class",
            "automatic_authority", "standing", "authority_effect", "manifest_root",
        },
        "$.application",
    )
    body = {key: item[key] for key in item if key != "manifest_root"}
    require(item["schema"] == "ucl.ucm.application_manifest.v1" and item["manifest_root"] == root(body), "APPLICATION_MANIFEST_ROOT_INVALID")
    _identifier(item["application_id"], "APPLICATION_ID_INVALID", "$.application.application_id")
    _version(item["version"], "$.application.version")
    require(item["application_type"] in APPLICATION_TYPES, "APPLICATION_TYPE_INVALID")
    for name in ("implementation_root", "input_schema_root", "output_schema_root"):
        require_root(item[name], f"$.application.{name}")
    _sorted_unique(item["data_domains"], "APPLICATION_DATA_DOMAIN_SET_INVALID", "$.application.data_domains", identifiers=True)
    _sorted_unique(item["requested_capabilities"], "APPLICATION_CAPABILITY_SET_INVALID", "$.application.requested_capabilities", identifiers=True)
    _sorted_unique(item["supported_platforms"], "APPLICATION_PLATFORM_SET_INVALID", "$.application.supported_platforms")
    require(item["supported_platforms"] and set(item["supported_platforms"]).issubset({"POSIX", "WINDOWS"}), "APPLICATION_PLATFORM_INVALID")
    require(type(item["obligation_roots"]) is list and item["obligation_roots"] == sorted(item["obligation_roots"]) and len(item["obligation_roots"]) == len(set(item["obligation_roots"])) and item["obligation_roots"], "APPLICATION_OBLIGATION_SET_INVALID")
    for value in item["obligation_roots"]:
        require_root(value)
    require(item["maximum_effect_class"] in EFFECT_CLASSES and item["automatic_authority"] is False, "APPLICATION_AUTHORITY_INVALID")
    require(item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "APPLICATION_EFFECT_INVALID")
    return deepcopy(body)


def compile_policy_bundle(
    *,
    subject_root: str,
    policy_version: str,
    registry: dict[str, Any],
    applications: list[dict[str, Any]],
    grants: dict[str, list[str]],
) -> dict[str, Any]:
    verify_capability_registry(registry, expected_subject_root=subject_root)
    app_map: dict[str, dict[str, Any]] = {}
    for application in applications:
        verify_application_manifest(application)
        application_id = application["application_id"]
        require(application_id not in app_map, "APPLICATION_DUPLICATE_ID")
        app_map[application_id] = deepcopy(application)
    require(set(grants) == set(app_map), "POLICY_APPLICATION_SET_INVALID")
    capabilities = {item["capability_id"]: item for item in registry["capabilities"]}
    checked_grants: dict[str, list[str]] = {}
    for application_id in sorted(app_map):
        allowed = _sorted_unique(grants[application_id], "POLICY_GRANT_SET_INVALID", f"$.grants.{application_id}", identifiers=True)
        application = app_map[application_id]
        require(set(allowed).issubset(set(application["requested_capabilities"])), "POLICY_UNREQUESTED_CAPABILITY")
        require(set(allowed).issubset(capabilities), "POLICY_UNKNOWN_CAPABILITY")
        for capability_id in allowed:
            require(effect_rank(capabilities[capability_id]["effect_class"]) <= effect_rank(application["maximum_effect_class"]), "POLICY_EFFECT_EXCEEDS_APPLICATION_CEILING")
        checked_grants[application_id] = allowed
    ordered_apps = [app_map[key] for key in sorted(app_map)]
    body = {
        "schema": "ucl.ucm.application_policy_bundle.v1",
        "subject_root": require_root(subject_root),
        "policy_version": _version(policy_version, "$.policy_version"),
        "registry_root": registry["registry_root"],
        "applications": ordered_apps,
        "application_roots": {item["application_id"]: item["manifest_root"] for item in ordered_apps},
        "grants": checked_grants,
        "default_policy": "DENY",
        "effectful_requests_require_external_decision": True,
        "maximum_executable_stage": "D2_INDEPENDENT_REVIEW",
        "executable_effect_classes": ["NONE"],
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "policy_root": root(body)}


def verify_policy_bundle(value: Any, *, registry: dict[str, Any], expected_subject_root: str) -> dict[str, Any]:
    item = exact_keys(
        value,
        {
            "schema", "subject_root", "policy_version", "registry_root", "applications",
            "application_roots", "grants", "default_policy", "effectful_requests_require_external_decision",
            "maximum_executable_stage", "executable_effect_classes", "standing", "authority_effect", "policy_root",
        },
        "$.policy",
    )
    body = {key: item[key] for key in item if key != "policy_root"}
    require(item["schema"] == "ucl.ucm.application_policy_bundle.v1" and item["policy_root"] == root(body), "POLICY_ROOT_INVALID")
    verify_capability_registry(registry, expected_subject_root=expected_subject_root)
    require(item["subject_root"] == require_root(expected_subject_root) and item["registry_root"] == registry["registry_root"], "POLICY_CONTEXT_MISMATCH")
    _version(item["policy_version"], "$.policy.policy_version")
    applications: dict[str, dict[str, Any]] = {}
    for application in item["applications"]:
        verify_application_manifest(application)
        require(application["application_id"] not in applications, "APPLICATION_DUPLICATE_ID")
        applications[application["application_id"]] = application
    require([item["application_id"] for item in item["applications"]] == sorted(applications), "POLICY_APPLICATION_ORDER_INVALID")
    require(item["application_roots"] == {key: applications[key]["manifest_root"] for key in sorted(applications)}, "POLICY_APPLICATION_ROOTS_INVALID")
    require(set(item["grants"]) == set(applications), "POLICY_APPLICATION_SET_INVALID")
    capabilities = {entry["capability_id"]: entry for entry in registry["capabilities"]}
    for application_id in sorted(applications):
        allowed = _sorted_unique(item["grants"][application_id], "POLICY_GRANT_SET_INVALID", f"$.policy.grants.{application_id}", identifiers=True)
        require(set(allowed).issubset(set(applications[application_id]["requested_capabilities"])) and set(allowed).issubset(capabilities), "POLICY_GRANT_INVALID")
        for capability_id in allowed:
            require(effect_rank(capabilities[capability_id]["effect_class"]) <= effect_rank(applications[application_id]["maximum_effect_class"]), "POLICY_EFFECT_EXCEEDS_APPLICATION_CEILING")
    require(item["default_policy"] == "DENY" and item["effectful_requests_require_external_decision"] is True, "POLICY_DEFAULT_INVALID")
    require(item["maximum_executable_stage"] == "D2_INDEPENDENT_REVIEW" and item["executable_effect_classes"] == ["NONE"], "POLICY_EXECUTION_CEILING_INVALID")
    require(item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "POLICY_EFFECT_INVALID")
    return deepcopy(body)


def application_from_policy(policy: dict[str, Any], application_id: str) -> dict[str, Any]:
    _identifier(application_id, "APPLICATION_ID_INVALID", "$.application_id")
    matches = [item for item in policy["applications"] if item["application_id"] == application_id]
    require(len(matches) == 1, "APPLICATION_NOT_IN_POLICY")
    return deepcopy(matches[0])


def capability_from_registry(registry: dict[str, Any], capability_id: str) -> dict[str, Any]:
    _identifier(capability_id, "CAPABILITY_ID_INVALID", "$.capability_id")
    matches = [item for item in registry["capabilities"] if item["capability_id"] == capability_id]
    require(len(matches) == 1, "CAPABILITY_NOT_IN_REGISTRY")
    return deepcopy(matches[0])


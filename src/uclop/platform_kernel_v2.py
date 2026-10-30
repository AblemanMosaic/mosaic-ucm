from __future__ import annotations

from copy import deepcopy
from typing import Any

from .adapter_contracts import verify_adapter_registry
from .application_supervisor import DurableApplicationSupervisor
from .canonical import exact_keys, require, require_root, root
from .custody_maturity import CustodyLineage
from .incident_system import IncidentLedger
from .platform_kernel import PlatformKernel, verify_platform_snapshot
from .platform_observability import ObservationLedger
from .platform_profiles import verify_platform_profile


class PlatformKernelV2:
    """Integrated c2 reference kernel; all effectful provider routes remain proposals."""

    def __init__(
        self, *, subject_root: str, registry: dict[str, Any], policy: dict[str, Any],
        expected_registry_root: str, expected_policy_root: str,
        adapter_registry: dict[str, Any], platform_profiles: dict[str, dict[str, Any]],
        custody: CustodyLineage, incidents: IncidentLedger, observations: ObservationLedger,
        runtime_capsule: dict[str, Any] | None = None, runtime_pin: str | None = None,
        supervisor_capsule: dict[str, Any] | None = None, supervisor_pin: str | None = None,
    ) -> None:
        self.subject_root = require_root(subject_root)
        require(registry.get("registry_root") == require_root(expected_registry_root), "PLATFORM_V2_REGISTRY_EXTERNAL_PIN_MISMATCH")
        require(policy.get("policy_root") == require_root(expected_policy_root), "PLATFORM_V2_POLICY_EXTERNAL_PIN_MISMATCH")
        verify_adapter_registry(adapter_registry, expected_subject_root=self.subject_root)
        require(type(platform_profiles) is dict and set(platform_profiles) == {"POSIX", "WINDOWS"}, "PLATFORM_V2_PROFILE_SET_INVALID")
        for platform, profile in platform_profiles.items():
            verify_platform_profile(profile)
            require(profile["platform"] == platform, "PLATFORM_V2_PROFILE_CONTEXT_MISMATCH")
        require(observations.subject_root == self.subject_root, "PLATFORM_V2_OBSERVATION_CONTEXT_MISMATCH")
        self.registry, self.policy = deepcopy(registry), deepcopy(policy)
        self.adapter_registry, self.platform_profiles = deepcopy(adapter_registry), deepcopy(platform_profiles)
        self.observations = observations
        self.base = PlatformKernel(
            subject_root=self.subject_root, registry=registry, policy=policy, custody=custody,
            expected_registry_root=expected_registry_root, expected_policy_root=expected_policy_root,
            incidents=incidents, runtime_capsule=runtime_capsule, runtime_pin=runtime_pin,
        )
        self.supervisor = DurableApplicationSupervisor(
            subject_root=self.subject_root, policy_root=policy["policy_root"],
            initial_capsule=supervisor_capsule, expected_pin=supervisor_pin,
        )

    def snapshot(self) -> dict[str, Any]:
        base = self.base.snapshot()
        supervisor = self.supervisor.export_capsule()
        observations = self.observations.export_capsule()
        body = {
            "schema": "ucl.ucm.application_platform_snapshot.v2",
            "subject_root": self.subject_root,
            "registry_root": self.registry["registry_root"],
            "policy_root": self.policy["policy_root"],
            "adapter_registry_root": self.adapter_registry["registry_root"],
            "platform_profile_roots": {key: self.platform_profiles[key]["profile_root"] for key in sorted(self.platform_profiles)},
            "base_snapshot": base,
            "supervisor_capsule": supervisor,
            "observation_capsule": observations,
            "maximum_stage": "S2_INFORMATION_ONLY_FEDERATION",
            "effect_observed": "NONE",
            "host_processes_started": 0,
            "identity_seated": False,
            "installed": False,
            "released": False,
            "real_a5": False,
            "g0": "CLOSED",
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        return {**body, "snapshot_root": root(body)}


def verify_platform_snapshot_v2(
    value: Any, *, expected_subject_root: str, expected_registry_root: str,
    expected_policy_root: str, expected_capability_roots: dict[str, str],
    expected_adapter_registry_root: str, expected_profile_roots: dict[str, str],
) -> dict[str, Any]:
    item = exact_keys(value, {
        "schema", "subject_root", "registry_root", "policy_root", "adapter_registry_root",
        "platform_profile_roots", "base_snapshot", "supervisor_capsule", "observation_capsule",
        "maximum_stage", "effect_observed", "host_processes_started", "identity_seated",
        "installed", "released", "real_a5", "g0", "standing", "authority_effect", "snapshot_root",
    }, "$.platform_snapshot_v2")
    body = {key: item[key] for key in item if key != "snapshot_root"}
    require(item["schema"] == "ucl.ucm.application_platform_snapshot.v2" and item["snapshot_root"] == root(body), "PLATFORM_V2_SNAPSHOT_ROOT_INVALID")
    require(item["subject_root"] == require_root(expected_subject_root), "PLATFORM_V2_SNAPSHOT_SUBJECT_MISMATCH")
    require(item["registry_root"] == require_root(expected_registry_root) and item["policy_root"] == require_root(expected_policy_root), "PLATFORM_V2_SNAPSHOT_POLICY_MISMATCH")
    require(item["adapter_registry_root"] == require_root(expected_adapter_registry_root), "PLATFORM_V2_ADAPTER_REGISTRY_MISMATCH")
    require(item["platform_profile_roots"] == expected_profile_roots, "PLATFORM_V2_PROFILE_ROOTS_MISMATCH")
    verify_platform_snapshot(
        item["base_snapshot"], expected_subject_root=expected_subject_root,
        expected_registry_root=expected_registry_root, expected_policy_root=expected_policy_root,
        expected_capability_roots=expected_capability_roots,
    )
    for name, schema in (("supervisor_capsule", "ucl.ucm.application_supervisor_capsule.v1"), ("observation_capsule", "ucl.ucm.platform_observation_capsule.v1")):
        capsule = item[name]
        capsule_body = {key: capsule[key] for key in capsule if key != "capsule_root"}
        require(capsule.get("schema") == schema and capsule.get("capsule_root") == root(capsule_body), "PLATFORM_V2_CAPSULE_ROOT_INVALID", detail=name)
        require(capsule.get("subject_root") == expected_subject_root and capsule.get("effect_observed") == "NONE" and capsule.get("standing") == "INFORMATION_ONLY" and capsule.get("authority_effect") == "NONE", "PLATFORM_V2_CAPSULE_BOUNDARY_INVALID", detail=name)
    require(item["maximum_stage"] == "S2_INFORMATION_ONLY_FEDERATION" and item["effect_observed"] == "NONE" and item["host_processes_started"] == 0, "PLATFORM_V2_EFFECT_BOUNDARY_INVALID")
    require(item["identity_seated"] is False and item["installed"] is False and item["released"] is False and item["real_a5"] is False and item["g0"] == "CLOSED", "PLATFORM_V2_AUTHORITY_STATE_INVALID")
    require(item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "PLATFORM_V2_AUTHORITY_BOUNDARY_INVALID")
    return deepcopy(body)

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from .canonical import exact_keys, require, require_root, root
from .custody_maturity import CustodyLineage
from .incident_system import IncidentLedger
from .application_runtime import BoundApplicationRuntime
from .providers import ProviderRegistry, make_provider_descriptor, verify_provider_registry_snapshot


def _handler(capability_id: str) -> Callable[[Any], dict[str, Any]]:
    def execute(value: Any) -> dict[str, Any]:
        return {
            "capability_id": capability_id,
            "input_root": root(value),
            "result_root": root({"capability_id": capability_id, "input": value}),
            "effect_observed": "NONE",
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
    return execute


class PlatformKernel:
    """Integrated in-memory kernel for no-effect application workflows."""

    def __init__(
        self, *, subject_root: str, registry: dict[str, Any], policy: dict[str, Any],
        expected_registry_root: str, expected_policy_root: str,
        custody: CustodyLineage, incidents: IncidentLedger,
        runtime_capsule: dict[str, Any] | None = None, runtime_pin: str | None = None,
    ) -> None:
        self.subject_root = require_root(subject_root)
        require(custody.subject_root == self.subject_root and incidents.subject_root == self.subject_root, "PLATFORM_KERNEL_CONTEXT_MISMATCH")
        require(registry.get("registry_root") == require_root(expected_registry_root), "PLATFORM_REGISTRY_EXTERNAL_PIN_MISMATCH")
        require(policy.get("policy_root") == require_root(expected_policy_root), "PLATFORM_POLICY_EXTERNAL_PIN_MISMATCH")
        self.registry, self.policy = deepcopy(registry), deepcopy(policy)
        self.custody, self.incidents = custody, incidents
        self.runtime = BoundApplicationRuntime(
            subject_root=self.subject_root, registry=registry, policy=policy,
            expected_registry_root=expected_registry_root, expected_policy_root=expected_policy_root,
            initial_capsule=runtime_capsule, expected_pin=runtime_pin,
        )
        capabilities = {item["capability_id"]: item for item in registry["capabilities"]}
        handlers = {item["implementation_root"]: _handler(item["capability_id"]) for item in capabilities.values() if item["effect_class"] == "NONE"}
        schemas = {schema_root: (lambda value: type(value) is dict) for item in capabilities.values() for schema_root in (item["input_schema_root"], item["output_schema_root"])}
        self.providers = ProviderRegistry(
            subject_root=self.subject_root,
            capability_roots=registry["capability_roots"],
            capability_effects={key: item["effect_class"] for key, item in capabilities.items()},
            trusted_no_effect_handlers=handlers,
            trusted_schema_validators=schemas,
        )
        self._provider_ids: dict[str, str] = {}
        for capability_id in sorted(capabilities):
            capability = capabilities[capability_id]
            provider_id = "platform." + capability_id
            descriptor = make_provider_descriptor(
                provider_id=provider_id,
                capability_id=capability_id,
                implementation_root=capability["implementation_root"],
                input_schema_root=capability["input_schema_root"],
                output_schema_root=capability["output_schema_root"],
                effect_class=capability["effect_class"],
                deterministic=capability["deterministic"],
                portable=True,
            )
            self.providers.register(descriptor)
            self._provider_ids[capability_id] = provider_id

    def register_tenant(self, *, tenant_id: str, caller_principal_root: str, namespace_root: str, data_domain_allowlist: list[str], idempotency_key: str) -> dict[str, Any]:
        return self.runtime.register_tenant(tenant_id=tenant_id, caller_principal_root=caller_principal_root, namespace_root=namespace_root, data_domain_allowlist=data_domain_allowlist, idempotency_key=idempotency_key)

    def register_application(self, *, tenant_id: str, caller_principal_root: str, application_id: str, manifest_root: str, idempotency_key: str) -> dict[str, Any]:
        return self.runtime.register_application(tenant_id=tenant_id, caller_principal_root=caller_principal_root, application_id=application_id, manifest_root=manifest_root, idempotency_key=idempotency_key)

    def create_workflow(self, *, tenant_id: str, caller_principal_root: str, workflow_id: str, composition: dict[str, Any], input_root: str, idempotency_key: str) -> dict[str, Any]:
        return self.runtime.create_workflow(tenant_id=tenant_id, caller_principal_root=caller_principal_root, workflow_id=workflow_id, composition=composition, input_root=input_root, idempotency_key=idempotency_key)

    def advance(self, *, tenant_id: str, caller_principal_root: str, workflow_id: str, input_value: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        require(type(input_value) is dict, "PLATFORM_INPUT_INVALID")
        gate = self.incidents.gate(affected_roots=[self.subject_root])
        require(gate["status"] == "PASS", "PLATFORM_BLOCKED_BY_INCIDENT")
        event = self.runtime.begin_next(tenant_id=tenant_id, caller_principal_root=caller_principal_root, workflow_id=workflow_id, idempotency_key="begin:" + idempotency_key)
        capability_id = event["payload"]["capability_id"]
        provider_result = self.providers.invoke(
            provider_id=self._provider_ids[capability_id],
            capability_id=capability_id,
            input_value=input_value,
            request_root=root({"workflow_id": workflow_id, "event_root": event["event_root"], "input": input_value}),
        )
        if event["event_type"] == "NODE_PROPOSAL_PREPARED":
            require(provider_result["status"] == "UNBOUND_PROPOSAL" and provider_result["executed"] is False, "PLATFORM_EFFECT_ROUTE_INVALID")
            body = {
                "schema": "ucl.ucm.platform_step.v1",
                "workflow_id": workflow_id,
                "event_root": event["event_root"],
                "capability_id": capability_id,
                "status": "BLOCKED_EXTERNAL_AUTHORITY",
                "provider_result": provider_result,
                "effect_observed": "NONE",
                "standing": "INFORMATION_ONLY",
                "authority_effect": "NONE",
            }
            return {**body, "step_root": root(body)}
        require(provider_result["status"] == "PASS", "PLATFORM_PROVIDER_REFUSED", detail=provider_result.get("diagnostic", ""))
        completed = self.runtime.complete_no_effect_node(
            tenant_id=tenant_id, caller_principal_root=caller_principal_root,
            workflow_id=workflow_id,
            node_id=event["payload"]["node_id"],
            result=provider_result,
            idempotency_key="complete:" + idempotency_key,
        )
        body = {
            "schema": "ucl.ucm.platform_step.v1",
            "workflow_id": workflow_id,
            "event_root": completed["event_root"],
            "capability_id": capability_id,
            "status": "COMPLETED",
            "provider_result": provider_result,
            "effect_observed": "NONE",
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        return {**body, "step_root": root(body)}

    def snapshot(self) -> dict[str, Any]:
        runtime = self.runtime.export_capsule()
        custody = self.custody.export_capsule()
        incidents = self.incidents.export_capsule()
        providers = self.providers.snapshot()
        body = {
            "schema": "ucl.ucm.application_platform_snapshot.v1",
            "subject_root": self.subject_root,
            "registry_root": self.registry["registry_root"],
            "policy_root": self.policy["policy_root"],
            "runtime_capsule": runtime,
            "custody_capsule": custody,
            "incident_capsule": incidents,
            "provider_registry": providers,
            "maximum_stage": "S2_INFORMATION_ONLY_FEDERATION",
            "effect_observed": "NONE",
            "identity_seated": False,
            "real_a5": False,
            "g0": "CLOSED",
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        return {**body, "snapshot_root": root(body)}


def verify_platform_snapshot(value: Any, *, expected_subject_root: str, expected_registry_root: str, expected_policy_root: str, expected_capability_roots: dict[str, str]) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "subject_root", "registry_root", "policy_root", "runtime_capsule", "custody_capsule", "incident_capsule", "provider_registry", "maximum_stage", "effect_observed", "identity_seated", "real_a5", "g0", "standing", "authority_effect", "snapshot_root"}, "$.platform_snapshot")
    body = {key: item[key] for key in item if key != "snapshot_root"}
    require(item["schema"] == "ucl.ucm.application_platform_snapshot.v1" and item["snapshot_root"] == root(body), "PLATFORM_SNAPSHOT_ROOT_INVALID")
    require(item["subject_root"] == require_root(expected_subject_root) and item["registry_root"] == require_root(expected_registry_root) and item["policy_root"] == require_root(expected_policy_root), "PLATFORM_SNAPSHOT_CONTEXT_MISMATCH")
    for capsule_name in ("runtime_capsule", "custody_capsule", "incident_capsule"):
        capsule = item[capsule_name]
        require(type(capsule) is dict and capsule.get("capsule_root") == root({key: value for key, value in capsule.items() if key != "capsule_root"}), "PLATFORM_SNAPSHOT_CAPSULE_INVALID", detail=capsule_name)
        require(capsule.get("subject_root") == expected_subject_root and capsule.get("standing") == "INFORMATION_ONLY" and capsule.get("authority_effect") == "NONE", "PLATFORM_SNAPSHOT_CAPSULE_AUTHORITY_INVALID", detail=capsule_name)
        pending = [capsule]
        while pending:
            current = pending.pop()
            if type(current) is dict:
                for key, child in current.items():
                    if key in {"authority_effect", "effect_observed", "effects_observed"}: require(child == "NONE", "PLATFORM_SNAPSHOT_CAPSULE_AUTHORITY_INVALID", detail=key)
                    if key == "standing": require(child == "INFORMATION_ONLY", "PLATFORM_SNAPSHOT_CAPSULE_AUTHORITY_INVALID", detail=key)
                    if key == "real_a5": require(child is False, "PLATFORM_SNAPSHOT_CAPSULE_AUTHORITY_INVALID", detail=key)
                    if key == "g0": require(child == "CLOSED", "PLATFORM_SNAPSHOT_CAPSULE_AUTHORITY_INVALID", detail=key)
                    pending.append(child)
            elif type(current) is list:
                pending.extend(current)
    verify_provider_registry_snapshot(item["provider_registry"], expected_subject_root=expected_subject_root, expected_capability_roots=expected_capability_roots)
    require(item["maximum_stage"] == "S2_INFORMATION_ONLY_FEDERATION" and item["effect_observed"] == "NONE" and item["identity_seated"] is False and item["real_a5"] is False and item["g0"] == "CLOSED" and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "PLATFORM_SNAPSHOT_AUTHORITY_INVALID")
    return deepcopy(body)

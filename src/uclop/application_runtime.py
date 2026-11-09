from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import exact_keys, require, require_root, root
from .ecosystem import verify_capability_registry, verify_policy_bundle
from .operational_runtime_v2 import OperationalRuntime


class BoundApplicationRuntime:
    """Tenant-bound successor facade over the frozen operational runtime.

    Predecessor replay remains available through the frozen predecessor, not
    through a mutable escape hatch on this facade. New platform code must enter
    through this facade, which externally pins the registry and policy and
    requires an exact tenant principal on every mutating operation.
    """

    def __init__(
        self, *, subject_root: str, registry: dict[str, Any], policy: dict[str, Any],
        expected_registry_root: str, expected_policy_root: str,
        initial_capsule: dict[str, Any] | None = None, expected_pin: str | None = None,
    ) -> None:
        self.subject_root = require_root(subject_root)
        verify_capability_registry(registry, expected_subject_root=self.subject_root)
        verify_policy_bundle(policy, registry=registry, expected_subject_root=self.subject_root)
        require(registry["registry_root"] == require_root(expected_registry_root), "APPLICATION_RUNTIME_REGISTRY_PIN_MISMATCH")
        require(policy["policy_root"] == require_root(expected_policy_root), "APPLICATION_RUNTIME_POLICY_PIN_MISMATCH")
        self.registry_root = registry["registry_root"]
        self.policy_root = policy["policy_root"]
        self._tenant_principals: dict[str, str] = {}
        runtime_capsule = None
        if initial_capsule is not None:
            item = exact_keys(initial_capsule, {
                "schema", "subject_root", "registry_root", "policy_root", "tenant_principals",
                "runtime_capsule", "effect_observed", "standing", "authority_effect", "capsule_root",
            }, "$.application_runtime_capsule")
            body = {key: item[key] for key in item if key != "capsule_root"}
            require(item["schema"] == "ucl.ucm.bound_application_runtime_capsule.v1" and item["capsule_root"] == root(body) == require_root(expected_pin), "APPLICATION_RUNTIME_CAPSULE_PIN_MISMATCH")
            require(item["subject_root"] == self.subject_root and item["registry_root"] == self.registry_root and item["policy_root"] == self.policy_root, "APPLICATION_RUNTIME_CAPSULE_CONTEXT_MISMATCH")
            require(item["effect_observed"] == "NONE" and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "APPLICATION_RUNTIME_CAPSULE_AUTHORITY_INVALID")
            require(type(item["tenant_principals"]) is dict, "APPLICATION_RUNTIME_PRINCIPALS_INVALID")
            self._tenant_principals = {tenant: require_root(principal) for tenant, principal in sorted(item["tenant_principals"].items())}
            runtime_capsule = item["runtime_capsule"]
        else:
            require(expected_pin is None, "APPLICATION_RUNTIME_CAPSULE_REQUIRED")
        self._runtime = OperationalRuntime(
            subject_root=self.subject_root, registry=registry, policy=policy,
            initial_capsule=runtime_capsule,
            expected_pin=runtime_capsule["capsule_root"] if runtime_capsule is not None else None,
        )

    def _authorize(self, tenant_id: str, caller_principal_root: str) -> None:
        require(tenant_id in self._tenant_principals, "APPLICATION_RUNTIME_TENANT_UNKNOWN")
        require(self._tenant_principals[tenant_id] == require_root(caller_principal_root), "APPLICATION_RUNTIME_CALLER_MISMATCH")

    def register_tenant(self, *, tenant_id: str, caller_principal_root: str, namespace_root: str, data_domain_allowlist: list[str], idempotency_key: str) -> dict[str, Any]:
        principal = require_root(caller_principal_root)
        require(tenant_id not in self._tenant_principals, "APPLICATION_RUNTIME_TENANT_DUPLICATE")
        event = self._runtime.register_tenant(tenant_id=tenant_id, namespace_root=namespace_root, data_domain_allowlist=data_domain_allowlist, idempotency_key=idempotency_key)
        self._tenant_principals[tenant_id] = principal
        return event

    def register_application(self, *, tenant_id: str, caller_principal_root: str, application_id: str, manifest_root: str, idempotency_key: str) -> dict[str, Any]:
        self._authorize(tenant_id, caller_principal_root)
        return self._runtime.register_application(tenant_id=tenant_id, application_id=application_id, manifest_root=manifest_root, idempotency_key=idempotency_key)

    def create_workflow(self, *, tenant_id: str, caller_principal_root: str, workflow_id: str, composition: dict[str, Any], input_root: str, idempotency_key: str) -> dict[str, Any]:
        self._authorize(tenant_id, caller_principal_root)
        return self._runtime.create_workflow(tenant_id=tenant_id, workflow_id=workflow_id, composition=composition, input_root=input_root, idempotency_key=idempotency_key)

    def begin_next(self, *, tenant_id: str, caller_principal_root: str, workflow_id: str, idempotency_key: str) -> dict[str, Any]:
        self._authorize(tenant_id, caller_principal_root)
        status = self._runtime.workflow_status(workflow_id)
        require(status["tenant_id"] == tenant_id, "APPLICATION_RUNTIME_WORKFLOW_TENANT_MISMATCH")
        return self._runtime.begin_next(workflow_id=workflow_id, idempotency_key=idempotency_key)

    def complete_no_effect_node(self, *, tenant_id: str, caller_principal_root: str, workflow_id: str, node_id: str, result: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        self._authorize(tenant_id, caller_principal_root)
        status = self._runtime.workflow_status(workflow_id)
        require(status["tenant_id"] == tenant_id, "APPLICATION_RUNTIME_WORKFLOW_TENANT_MISMATCH")
        return self._runtime.complete_no_effect_node(workflow_id=workflow_id, node_id=node_id, result=result, idempotency_key=idempotency_key)

    def workflow_status(self, *, tenant_id: str, caller_principal_root: str, workflow_id: str) -> dict[str, Any]:
        self._authorize(tenant_id, caller_principal_root)
        status = self._runtime.workflow_status(workflow_id)
        require(status["tenant_id"] == tenant_id, "APPLICATION_RUNTIME_WORKFLOW_TENANT_MISMATCH")
        return status

    def export_capsule(self) -> dict[str, Any]:
        body = {
            "schema": "ucl.ucm.bound_application_runtime_capsule.v1",
            "subject_root": self.subject_root,
            "registry_root": self.registry_root,
            "policy_root": self.policy_root,
            "tenant_principals": {key: self._tenant_principals[key] for key in sorted(self._tenant_principals)},
            "runtime_capsule": self._runtime.export_capsule(),
            "effect_observed": "NONE",
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        return {**body, "capsule_root": root(body)}


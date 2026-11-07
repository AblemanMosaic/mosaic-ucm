from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .canonical import exact_keys, require, require_root, root
from .composition import verify_composition
from .ecosystem import verify_capability_registry, verify_policy_bundle


_ID = re.compile(r"^[a-z][a-z0-9_.-]{2,63}$")
EVENT_TYPES = {
    "TENANT_REGISTERED", "APPLICATION_REGISTERED", "WORKFLOW_CREATED", "NODE_STARTED",
    "NODE_COMPLETED", "NODE_PROPOSAL_PREPARED", "WORKFLOW_COMPLETED", "WORKFLOW_CANCELLED",
}


def _identifier(value: Any, code: str) -> str:
    require(type(value) is str and bool(_ID.fullmatch(value)), code)
    return value


def _event_body(*, event_type: str, tenant_id: str, workflow_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
    require(event_type in EVENT_TYPES, "OPERATION_EVENT_TYPE_INVALID")
    _identifier(tenant_id, "TENANT_ID_INVALID")
    require(workflow_id is None or (type(workflow_id) is str and bool(_ID.fullmatch(workflow_id))), "WORKFLOW_ID_INVALID")
    require(type(payload) is dict, "OPERATION_EVENT_PAYLOAD_INVALID")
    return {
        "schema": "ucl.ucm.operational_event.v1", "event_type": event_type,
        "tenant_id": tenant_id, "workflow_id": workflow_id, "payload": deepcopy(payload),
        "effect_observed": "NONE", "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    }


def _validate_event_payload(
    *, event_type: str, tenant_id: str, workflow_id: str | None, payload: Any,
    capabilities: dict[str, dict[str, Any]], applications: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Validate the semantic payload of every event before it enters or rebuilds state."""
    if event_type == "TENANT_REGISTERED":
        item = exact_keys(payload, {"namespace_root", "data_domain_allowlist"}, "$.event.payload")
        require(workflow_id is None, "OPERATION_EVENT_WORKFLOW_CONTEXT_INVALID")
        require_root(item["namespace_root"])
        domains = item["data_domain_allowlist"]
        require(type(domains) is list and domains == sorted(domains) and len(domains) == len(set(domains)) and all(type(value) is str and value for value in domains), "TENANT_DATA_DOMAIN_SET_INVALID")
    elif event_type == "APPLICATION_REGISTERED":
        item = exact_keys(payload, {"application_id", "manifest_root"}, "$.event.payload")
        require(workflow_id is None and item["application_id"] in applications, "APPLICATION_NOT_IN_POLICY")
        require(item["manifest_root"] == applications[item["application_id"]]["manifest_root"], "APPLICATION_MANIFEST_PIN_MISMATCH")
    elif event_type == "WORKFLOW_CREATED":
        item = exact_keys(payload, {"composition_root", "input_root", "node_order", "nodes"}, "$.event.payload")
        require(workflow_id is not None, "OPERATION_EVENT_WORKFLOW_CONTEXT_INVALID")
        require_root(item["composition_root"]); require_root(item["input_root"])
        require(type(item["node_order"]) is list and item["node_order"] and len(item["node_order"]) == len(set(item["node_order"])), "WORKFLOW_NODE_ORDER_INVALID")
        require(type(item["nodes"]) is list and item["nodes"], "WORKFLOW_NODE_SET_INVALID")
        node_ids: list[str] = []
        for index, candidate in enumerate(item["nodes"]):
            node = exact_keys(candidate, {"node_id", "capability_id", "effect_class"}, f"$.event.payload.nodes[{index}]")
            node_ids.append(_identifier(node["node_id"], "COMPOSITION_NODE_ID_INVALID"))
            require(node["capability_id"] in capabilities and node["effect_class"] == capabilities[node["capability_id"]]["effect_class"], "WORKFLOW_CAPABILITY_BINDING_INVALID")
        require(len(node_ids) == len(set(node_ids)) and set(item["node_order"]) == set(node_ids), "WORKFLOW_NODE_ORDER_INVALID")
    elif event_type in {"NODE_STARTED", "NODE_PROPOSAL_PREPARED"}:
        item = exact_keys(payload, {"node_id", "capability_id", "effect_class", "composition_root", "executed"}, "$.event.payload")
        require(workflow_id is not None and item["executed"] is False, "OPERATION_EVENT_WORKFLOW_CONTEXT_INVALID")
        _identifier(item["node_id"], "COMPOSITION_NODE_ID_INVALID"); require_root(item["composition_root"])
        require(item["capability_id"] in capabilities and item["effect_class"] == capabilities[item["capability_id"]]["effect_class"], "WORKFLOW_CAPABILITY_BINDING_INVALID")
        require((event_type == "NODE_STARTED") == (item["effect_class"] == "NONE"), "WORKFLOW_EFFECT_ROUTE_INVALID")
    elif event_type == "NODE_COMPLETED":
        item = exact_keys(payload, {"node_id", "capability_id", "result", "result_root"}, "$.event.payload")
        require(workflow_id is not None, "OPERATION_EVENT_WORKFLOW_CONTEXT_INVALID")
        _identifier(item["node_id"], "COMPOSITION_NODE_ID_INVALID"); require_root(item["result_root"])
        require(item["capability_id"] in capabilities and capabilities[item["capability_id"]]["effect_class"] == "NONE", "WORKFLOW_CAPABILITY_BINDING_INVALID")
        _validate_no_effect_result(item["result"])
        require(item["result_root"] == root(item["result"]), "WORKFLOW_RESULT_ROOT_MISMATCH")
    elif event_type == "WORKFLOW_COMPLETED":
        item = exact_keys(payload, {"composition_root", "result_roots"}, "$.event.payload")
        require(workflow_id is not None, "OPERATION_EVENT_WORKFLOW_CONTEXT_INVALID")
        require_root(item["composition_root"])
        require(type(item["result_roots"]) is list and item["result_roots"] and all(type(value) is str for value in item["result_roots"]), "WORKFLOW_RESULT_SET_INVALID")
        for value in item["result_roots"]: require_root(value)
    elif event_type == "WORKFLOW_CANCELLED":
        item = exact_keys(payload, {"composition_root", "reason_code"}, "$.event.payload")
        require(workflow_id is not None, "OPERATION_EVENT_WORKFLOW_CONTEXT_INVALID")
        require_root(item["composition_root"])
        require(type(item["reason_code"]) is str and bool(re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", item["reason_code"])), "WORKFLOW_CANCEL_REASON_INVALID")
    else:
        require(False, "OPERATION_EVENT_TYPE_INVALID")
    return deepcopy(item)


def _validate_no_effect_result(value: Any) -> None:
    require(type(value) is dict and value.get("effect_observed") == "NONE" and value.get("authority_effect") == "NONE", "NODE_RESULT_EFFECT_INVALID")
    pending = [(value, "$")]
    while pending:
        current, path = pending.pop()
        if type(current) is dict:
            for key, item in current.items():
                child = f"{path}.{key}"
                if key in {"effect_observed", "effects_observed", "authority_effect"}:
                    require(item == "NONE", "NODE_RESULT_EFFECT_INVALID", child)
                elif key == "standing":
                    require(item == "INFORMATION_ONLY", "NODE_RESULT_STANDING_INVALID", child)
                elif key == "real_a5":
                    require(item is False, "NODE_RESULT_AUTHORITY_INVALID", child)
                elif key == "g0":
                    require(item == "CLOSED", "NODE_RESULT_AUTHORITY_INVALID", child)
                elif key in {"installed", "released", "production_active", "admitted", "identity_seated"}:
                    require(item is False, "NODE_RESULT_AUTHORITY_INVALID", child)
                pending.append((item, child))
        elif type(current) is list:
            pending.extend((item, f"{path}[{index}]") for index, item in enumerate(current))


class OperationalRuntime:
    """Event-sourced multi-application runtime with an immutable NONE effect ceiling."""

    def __init__(
        self, *, subject_root: str, registry: dict[str, Any], policy: dict[str, Any],
        initial_capsule: dict[str, Any] | None = None, expected_pin: str | None = None,
    ) -> None:
        self.subject_root = require_root(subject_root)
        verify_capability_registry(registry, expected_subject_root=self.subject_root)
        verify_policy_bundle(policy, registry=registry, expected_subject_root=self.subject_root)
        self.registry, self.policy = deepcopy(registry), deepcopy(policy)
        self._capabilities = {item["capability_id"]: item for item in registry["capabilities"]}
        self._applications = {item["application_id"]: item for item in policy["applications"]}
        self._events: list[dict[str, Any]] = []
        self._tenants: dict[str, dict[str, Any]] = {}
        self._workflows: dict[str, dict[str, Any]] = {}
        self._idempotency: dict[str, tuple[str, str]] = {}
        self._sequence = 0
        self._head = root({"subject_root": self.subject_root, "policy_root": policy["policy_root"], "genesis": True})
        if initial_capsule is not None:
            require(expected_pin is not None, "OPERATIONAL_CAPSULE_PIN_REQUIRED")
            self.restore(initial_capsule, expected_pin=expected_pin)
        else:
            require(expected_pin is None, "OPERATIONAL_CAPSULE_REQUIRED")

    def _append(self, body: dict[str, Any]) -> dict[str, Any]:
        self._sequence += 1
        bound = {**body, "sequence": self._sequence, "previous_head": self._head}
        event = {**bound, "event_root": root(bound)}
        self._events.append(event)
        self._head = event["event_root"]
        return deepcopy(event)

    def _remember(self, key: str, request_root: str, event_root: str) -> None:
        require(type(key) is str and 8 <= len(key) <= 128, "IDEMPOTENCY_KEY_INVALID")
        prior = self._idempotency.get(key)
        if prior is not None:
            require(prior == (request_root, event_root), "IDEMPOTENCY_CONFLICT")
            return
        self._idempotency[key] = (request_root, event_root)

    def register_tenant(self, *, tenant_id: str, namespace_root: str, data_domain_allowlist: list[str], idempotency_key: str) -> dict[str, Any]:
        tenant_id = _identifier(tenant_id, "TENANT_ID_INVALID")
        require(type(data_domain_allowlist) is list and data_domain_allowlist == sorted(data_domain_allowlist) and len(data_domain_allowlist) == len(set(data_domain_allowlist)), "TENANT_DATA_DOMAIN_SET_INVALID")
        body = _event_body(event_type="TENANT_REGISTERED", tenant_id=tenant_id, workflow_id=None, payload={
            "namespace_root": require_root(namespace_root), "data_domain_allowlist": list(data_domain_allowlist),
        })
        request_root = root(body)
        if idempotency_key in self._idempotency:
            prior_request, prior_event = self._idempotency[idempotency_key]
            require(prior_request == request_root, "IDEMPOTENCY_CONFLICT")
            return deepcopy(next(item for item in self._events if item["event_root"] == prior_event))
        require(tenant_id not in self._tenants, "TENANT_DUPLICATE")
        event = self._append(body)
        self._tenants[tenant_id] = {"namespace_root": namespace_root, "data_domain_allowlist": list(data_domain_allowlist), "application_roots": {}}
        self._remember(idempotency_key, request_root, event["event_root"])
        return event

    def register_application(self, *, tenant_id: str, application_id: str, manifest_root: str, idempotency_key: str) -> dict[str, Any]:
        require(tenant_id in self._tenants, "TENANT_UNKNOWN")
        require(application_id in self._applications, "APPLICATION_NOT_IN_POLICY")
        require(self._applications[application_id]["manifest_root"] == require_root(manifest_root), "APPLICATION_MANIFEST_PIN_MISMATCH")
        domains = self._applications[application_id]["data_domains"]
        require(set(domains).issubset(set(self._tenants[tenant_id]["data_domain_allowlist"])), "TENANT_DATA_DOMAIN_NOT_ALLOWED")
        body = _event_body(event_type="APPLICATION_REGISTERED", tenant_id=tenant_id, workflow_id=None, payload={"application_id": application_id, "manifest_root": manifest_root})
        request_root = root(body)
        if idempotency_key in self._idempotency:
            prior_request, prior_event = self._idempotency[idempotency_key]
            require(prior_request == request_root, "IDEMPOTENCY_CONFLICT")
            return deepcopy(next(item for item in self._events if item["event_root"] == prior_event))
        require(application_id not in self._tenants[tenant_id]["application_roots"], "TENANT_APPLICATION_DUPLICATE")
        event = self._append(body)
        self._tenants[tenant_id]["application_roots"][application_id] = manifest_root
        self._remember(idempotency_key, request_root, event["event_root"])
        return event

    def create_workflow(self, *, tenant_id: str, workflow_id: str, composition: dict[str, Any], input_root: str, idempotency_key: str) -> dict[str, Any]:
        require(tenant_id in self._tenants, "TENANT_UNKNOWN")
        workflow_id = _identifier(workflow_id, "WORKFLOW_ID_INVALID")
        verify_composition(composition, registry=self.registry, policy=self.policy, expected_subject_root=self.subject_root)
        required_apps = {item["application_id"] for item in composition["nodes"]}
        require(required_apps.issubset(self._tenants[tenant_id]["application_roots"]), "WORKFLOW_APPLICATION_NOT_REGISTERED")
        require(set(composition["data_permissions"].keys()).issuperset(required_apps), "WORKFLOW_DATA_SCOPE_INVALID")
        for app_id in required_apps:
            require(set(composition["data_permissions"][app_id]).issubset(self._tenants[tenant_id]["data_domain_allowlist"]), "WORKFLOW_DATA_SCOPE_INVALID")
        body = _event_body(event_type="WORKFLOW_CREATED", tenant_id=tenant_id, workflow_id=workflow_id, payload={
            "composition_root": composition["composition_root"], "input_root": require_root(input_root),
            "node_order": list(composition["topological_order"]),
            "nodes": [{"node_id": item["node_id"], "capability_id": item["capability_id"], "effect_class": item["effect_class"]} for item in composition["nodes"]],
        })
        request_root = root(body)
        if idempotency_key in self._idempotency:
            prior_request, prior_event = self._idempotency[idempotency_key]
            require(prior_request == request_root, "IDEMPOTENCY_CONFLICT")
            return deepcopy(next(item for item in self._events if item["event_root"] == prior_event))
        require(workflow_id not in self._workflows, "WORKFLOW_DUPLICATE")
        event = self._append(body)
        self._workflows[workflow_id] = {
            "tenant_id": tenant_id, "composition_root": composition["composition_root"], "input_root": input_root,
            "node_order": list(composition["topological_order"]), "nodes": {item["node_id"]: {"capability_id": item["capability_id"], "effect_class": item["effect_class"], "status": "PENDING", "result_root": None} for item in composition["nodes"]},
            "status": "READY", "next_index": 0,
        }
        self._remember(idempotency_key, request_root, event["event_root"])
        return event

    def begin_next(self, *, workflow_id: str, idempotency_key: str) -> dict[str, Any]:
        require(workflow_id in self._workflows, "WORKFLOW_UNKNOWN")
        state = self._workflows[workflow_id]
        require(state["next_index"] < len(state["node_order"]), "WORKFLOW_ALREADY_COMPLETE")
        node_id = state["node_order"][state["next_index"]]
        node = state["nodes"][node_id]
        event_type = "NODE_STARTED" if node["effect_class"] == "NONE" else "NODE_PROPOSAL_PREPARED"
        body = _event_body(event_type=event_type, tenant_id=state["tenant_id"], workflow_id=workflow_id, payload={
            "node_id": node_id, "capability_id": node["capability_id"], "effect_class": node["effect_class"],
            "composition_root": state["composition_root"], "executed": False,
        })
        request_root = root(body)
        if idempotency_key in self._idempotency:
            prior_request, prior_event = self._idempotency[idempotency_key]
            require(prior_request == request_root, "IDEMPOTENCY_CONFLICT")
            return deepcopy(next(item for item in self._events if item["event_root"] == prior_event))
        require(state["status"] in {"READY", "RUNNING"}, "WORKFLOW_TRANSITION_INVALID")
        require(node["status"] == "PENDING", "WORKFLOW_NODE_TRANSITION_INVALID")
        event = self._append(body)
        node["status"] = "RUNNING" if event_type == "NODE_STARTED" else "EXTERNAL_REVIEW_PENDING"
        state["status"] = "RUNNING" if event_type == "NODE_STARTED" else "BLOCKED_EXTERNAL_AUTHORITY"
        self._remember(idempotency_key, request_root, event["event_root"])
        return event

    def complete_no_effect_node(self, *, workflow_id: str, node_id: str, result: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        require(workflow_id in self._workflows, "WORKFLOW_UNKNOWN")
        state = self._workflows[workflow_id]
        require(node_id in state["nodes"], "WORKFLOW_NODE_TRANSITION_INVALID")
        node = state["nodes"][node_id]
        require(node["effect_class"] == "NONE", "EFFECTFUL_RESULT_FORBIDDEN")
        _validate_no_effect_result(result)
        result_root = root(result)
        body = _event_body(event_type="NODE_COMPLETED", tenant_id=state["tenant_id"], workflow_id=workflow_id, payload={
            "node_id": node_id, "capability_id": node["capability_id"], "result": deepcopy(result), "result_root": result_root,
        })
        request_root = root(body)
        if idempotency_key in self._idempotency:
            prior_request, prior_event = self._idempotency[idempotency_key]
            require(prior_request == request_root, "IDEMPOTENCY_CONFLICT")
            return deepcopy(next(item for item in self._events if item["event_root"] == prior_event))
        require(node["status"] == "RUNNING", "WORKFLOW_NODE_TRANSITION_INVALID")
        event = self._append(body)
        node["status"], node["result_root"] = "COMPLETED", result_root
        state["next_index"] += 1
        if state["next_index"] == len(state["node_order"]):
            state["status"] = "COMPLETED"
            terminal = _event_body(event_type="WORKFLOW_COMPLETED", tenant_id=state["tenant_id"], workflow_id=workflow_id, payload={
                "composition_root": state["composition_root"], "result_roots": [state["nodes"][key]["result_root"] for key in state["node_order"]],
            })
            self._append(terminal)
        else:
            state["status"] = "READY"
        self._remember(idempotency_key, request_root, event["event_root"])
        return event

    def cancel_workflow(self, *, workflow_id: str, reason_code: str, idempotency_key: str) -> dict[str, Any]:
        require(workflow_id in self._workflows, "WORKFLOW_UNKNOWN")
        state = self._workflows[workflow_id]
        body = _event_body(event_type="WORKFLOW_CANCELLED", tenant_id=state["tenant_id"], workflow_id=workflow_id, payload={
            "composition_root": state["composition_root"], "reason_code": reason_code,
        })
        _validate_event_payload(event_type="WORKFLOW_CANCELLED", tenant_id=state["tenant_id"], workflow_id=workflow_id, payload=body["payload"], capabilities=self._capabilities, applications=self._applications)
        request_root = root(body)
        if idempotency_key in self._idempotency:
            prior_request, prior_event = self._idempotency[idempotency_key]
            require(prior_request == request_root, "IDEMPOTENCY_CONFLICT")
            return deepcopy(next(item for item in self._events if item["event_root"] == prior_event))
        require(state["status"] not in {"COMPLETED", "CANCELLED"}, "WORKFLOW_TRANSITION_INVALID")
        event = self._append(body)
        state["status"] = "CANCELLED"
        self._remember(idempotency_key, request_root, event["event_root"])
        return event

    def workflow_status(self, workflow_id: str) -> dict[str, Any]:
        require(workflow_id in self._workflows, "WORKFLOW_UNKNOWN")
        state = deepcopy(self._workflows[workflow_id])
        body = {
            "schema": "ucl.ucm.workflow_status.v1", "workflow_id": workflow_id, **state,
            "maximum_effect_class_executed": "NONE", "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        }
        return {**body, "status_root": root(body)}

    def export_capsule(self) -> dict[str, Any]:
        body = {
            "schema": "ucl.ucm.operational_runtime_capsule.v1", "subject_root": self.subject_root,
            "policy_root": self.policy["policy_root"], "sequence": self._sequence, "head": self._head,
            "events": deepcopy(self._events), "tenants": deepcopy({key: self._tenants[key] for key in sorted(self._tenants)}),
            "workflows": deepcopy({key: self._workflows[key] for key in sorted(self._workflows)}),
            "idempotency": {key: list(self._idempotency[key]) for key in sorted(self._idempotency)},
            "maximum_effect_class_executed": "NONE", "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        }
        return {**body, "capsule_root": root(body)}

    def restore(self, capsule: Any, *, expected_pin: str) -> None:
        item = exact_keys(capsule, {
            "schema", "subject_root", "policy_root", "sequence", "head", "events", "tenants", "workflows",
            "idempotency", "maximum_effect_class_executed", "standing", "authority_effect", "capsule_root",
        }, "$.capsule")
        body = {key: item[key] for key in item if key != "capsule_root"}
        require(item["schema"] == "ucl.ucm.operational_runtime_capsule.v1" and item["capsule_root"] == root(body) == require_root(expected_pin), "OPERATIONAL_CAPSULE_PIN_MISMATCH")
        require(item["subject_root"] == self.subject_root and item["policy_root"] == self.policy["policy_root"], "OPERATIONAL_CAPSULE_CONTEXT_MISMATCH")
        require(item["maximum_effect_class_executed"] == "NONE" and item["standing"] == "INFORMATION_ONLY" and item["authority_effect"] == "NONE", "OPERATIONAL_CAPSULE_AUTHORITY_INVALID")
        require(type(item["events"]) is list and type(item["sequence"]) is int and type(item["sequence"]) is not bool and item["sequence"] == len(item["events"]), "OPERATIONAL_EVENT_CHAIN_INVALID")
        expected_head = root({"subject_root": self.subject_root, "policy_root": self.policy["policy_root"], "genesis": True})
        for sequence, event in enumerate(item["events"], 1):
            event = exact_keys(event, {"schema", "event_type", "tenant_id", "workflow_id", "payload", "effect_observed", "standing", "authority_effect", "sequence", "previous_head", "event_root"}, f"$.events[{sequence - 1}]")
            event_body = {key: event[key] for key in event if key not in {"sequence", "previous_head", "event_root"}}
            require(event_body == _event_body(event_type=event["event_type"], tenant_id=event["tenant_id"], workflow_id=event["workflow_id"], payload=event["payload"]), "OPERATIONAL_EVENT_INVALID")
            _validate_event_payload(event_type=event["event_type"], tenant_id=event["tenant_id"], workflow_id=event["workflow_id"], payload=event["payload"], capabilities=self._capabilities, applications=self._applications)
            bound = {**event_body, "sequence": sequence, "previous_head": expected_head}
            require(event["sequence"] == sequence and event["previous_head"] == expected_head and event["event_root"] == root(bound), "OPERATIONAL_EVENT_CHAIN_INVALID")
            expected_head = event["event_root"]
        require(item["head"] == expected_head, "OPERATIONAL_EVENT_HEAD_INVALID")
        require(type(item["tenants"]) is dict and type(item["workflows"]) is dict and type(item["idempotency"]) is dict, "OPERATIONAL_STATE_INVALID")
        # Materialized state is covered by the capsule root; event roots prevent silent truncation.
        for tenant_id, tenant in item["tenants"].items():
            _identifier(tenant_id, "TENANT_ID_INVALID")
            require(type(tenant) is dict and set(tenant) == {"namespace_root", "data_domain_allowlist", "application_roots"}, "TENANT_STATE_INVALID")
            require_root(tenant["namespace_root"])
        for workflow_id, workflow in item["workflows"].items():
            _identifier(workflow_id, "WORKFLOW_ID_INVALID")
            require(type(workflow) is dict and workflow.get("tenant_id") in item["tenants"], "WORKFLOW_STATE_INVALID")
            require(workflow.get("status") in {"READY", "RUNNING", "BLOCKED_EXTERNAL_AUTHORITY", "COMPLETED", "CANCELLED"}, "WORKFLOW_STATE_INVALID")
        derived_tenants: dict[str, dict[str, Any]] = {}
        derived_workflows: dict[str, dict[str, Any]] = {}
        for event in item["events"]:
            event_type, tenant_id, workflow_id, payload = event["event_type"], event["tenant_id"], event["workflow_id"], event["payload"]
            if event_type == "TENANT_REGISTERED":
                require(tenant_id not in derived_tenants, "TENANT_DUPLICATE")
                derived_tenants[tenant_id] = {"namespace_root": payload["namespace_root"], "data_domain_allowlist": payload["data_domain_allowlist"], "application_roots": {}}
            elif event_type == "APPLICATION_REGISTERED":
                require(tenant_id in derived_tenants and payload["application_id"] not in derived_tenants[tenant_id]["application_roots"], "APPLICATION_EVENT_ORDER_INVALID")
                derived_tenants[tenant_id]["application_roots"][payload["application_id"]] = payload["manifest_root"]
            elif event_type == "WORKFLOW_CREATED":
                require(tenant_id in derived_tenants and workflow_id not in derived_workflows, "WORKFLOW_EVENT_ORDER_INVALID")
                derived_workflows[workflow_id] = {
                    "tenant_id": tenant_id, "composition_root": payload["composition_root"], "input_root": payload["input_root"],
                    "node_order": payload["node_order"],
                    "nodes": {node["node_id"]: {"capability_id": node["capability_id"], "effect_class": node["effect_class"], "status": "PENDING", "result_root": None} for node in payload["nodes"]},
                    "status": "READY", "next_index": 0,
                }
            elif event_type in {"NODE_STARTED", "NODE_PROPOSAL_PREPARED"}:
                require(workflow_id in derived_workflows, "WORKFLOW_EVENT_ORDER_INVALID")
                workflow = derived_workflows[workflow_id]
                require(payload["node_id"] in workflow["nodes"] and workflow["next_index"] < len(workflow["node_order"]), "WORKFLOW_EVENT_ORDER_INVALID")
                node = workflow["nodes"][payload["node_id"]]
                require(node["status"] == "PENDING" and workflow["node_order"][workflow["next_index"]] == payload["node_id"] and payload["capability_id"] == node["capability_id"] and payload["effect_class"] == node["effect_class"] and payload["composition_root"] == workflow["composition_root"], "WORKFLOW_EVENT_ORDER_INVALID")
                node["status"] = "RUNNING" if event_type == "NODE_STARTED" else "EXTERNAL_REVIEW_PENDING"
                workflow["status"] = "RUNNING" if event_type == "NODE_STARTED" else "BLOCKED_EXTERNAL_AUTHORITY"
            elif event_type == "NODE_COMPLETED":
                require(workflow_id in derived_workflows, "WORKFLOW_EVENT_ORDER_INVALID")
                workflow = derived_workflows[workflow_id]
                require(payload["node_id"] in workflow["nodes"], "WORKFLOW_EVENT_ORDER_INVALID")
                node = workflow["nodes"][payload["node_id"]]
                require(node["status"] == "RUNNING" and payload["capability_id"] == node["capability_id"], "WORKFLOW_EVENT_ORDER_INVALID")
                node["status"], node["result_root"] = "COMPLETED", payload["result_root"]
                workflow["next_index"] += 1; workflow["status"] = "READY"
            elif event_type == "WORKFLOW_COMPLETED":
                require(workflow_id in derived_workflows and derived_workflows[workflow_id]["next_index"] == len(derived_workflows[workflow_id]["node_order"]), "WORKFLOW_EVENT_ORDER_INVALID")
                workflow = derived_workflows[workflow_id]
                require(payload["composition_root"] == workflow["composition_root"] and payload["result_roots"] == [workflow["nodes"][key]["result_root"] for key in workflow["node_order"]], "WORKFLOW_EVENT_ORDER_INVALID")
                workflow["status"] = "COMPLETED"
            elif event_type == "WORKFLOW_CANCELLED":
                require(workflow_id in derived_workflows and derived_workflows[workflow_id]["status"] not in {"COMPLETED", "CANCELLED"} and payload["composition_root"] == derived_workflows[workflow_id]["composition_root"], "WORKFLOW_EVENT_ORDER_INVALID")
                derived_workflows[workflow_id]["status"] = "CANCELLED"
        require(derived_tenants == item["tenants"] and derived_workflows == item["workflows"], "OPERATIONAL_MATERIALIZED_STATE_MISMATCH")
        decoded_idempotency: dict[str, tuple[str, str]] = {}
        event_roots = {event["event_root"] for event in item["events"]}
        for key, pair in item["idempotency"].items():
            require(type(key) is str and type(pair) is list and len(pair) == 2, "IDEMPOTENCY_STATE_INVALID")
            require_root(pair[0]); require(pair[1] in event_roots, "IDEMPOTENCY_EVENT_UNKNOWN")
            decoded_idempotency[key] = (pair[0], pair[1])
        self._events, self._sequence, self._head = deepcopy(item["events"]), item["sequence"], item["head"]
        self._tenants, self._workflows, self._idempotency = deepcopy(item["tenants"]), deepcopy(item["workflows"]), decoded_idempotency


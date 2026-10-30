from __future__ import annotations

from copy import deepcopy
import pathlib
from typing import Any

from .adapter_contracts import (
    make_adapter_invocation,
    make_fixture_adapter_receipt,
    verify_adapter_registry,
)
from .aep_c2_control_plane import build_content_graph, plan_lane, verify_baseline_pin
from .application_lifecycle import (
    make_backup_receipt,
    make_lifecycle_rehearsal_receipt,
    make_upgrade_plan,
    verify_upgrade_plan,
)
from .application_supervisor import DurableApplicationSupervisor
from .composition_supervisor import DurableCompositionSupervisor
from .canonical import Refusal, exact_keys, require, require_root, root
from .foundation_agent import _scan_no_secrets
from .platform_profiles import verify_platform_profile
from .platform_workbench import PlatformWorkbench, SURFACES as LEGACY_SURFACES
from .protected_execution_v2 import (
    make_protected_execution_contract,
    verify_external_execution_receipt,
)


NEW_SURFACES = (
    "CLOSE_SUPERVISOR_INCIDENT",
    "DESCRIBE_ADAPTERS",
    "DESCRIBE_PROTECTED_PROFILE",
    "INSPECT_SUPERVISOR",
    "INSPECT_COMPOSITION",
    "OPEN_SUPERVISOR_INCIDENT",
    "PREPARE_ADAPTER_INVOCATION",
    "PREPARE_APPLICATION_BACKUP",
    "PREPARE_LIFECYCLE_REHEARSAL",
    "PREPARE_PROTECTED_EXECUTION_CONTRACT",
    "PREPARE_UPGRADE_PLAN",
    "RECORD_SUPERVISOR_HEALTH",
    "REGISTER_SUPERVISED_APPLICATION",
    "RECORD_COMPOSITION_NODE",
    "START_COMPOSITION",
    "TRANSITION_SUPERVISOR",
    "VALIDATE_EXTERNAL_EXECUTION",
    "VALIDATE_FIXTURE_ADAPTER_RECEIPT",
    "VALIDATE_UPGRADE_PLAN",
)
SURFACES_V2 = tuple(sorted(set(LEGACY_SURFACES) | set(NEW_SURFACES)))


class PlatformWorkbenchV2:
    """Unified c2 operator/agent surface; all calls remain no-effect reference operations."""

    def __init__(
        self, *, base: PlatformWorkbench, adapter_registry: dict[str, Any],
        supervisor: DurableApplicationSupervisor, platform_profiles: dict[str, dict[str, Any]],
        composition_supervisors: dict[str, DurableCompositionSupervisor] | None = None,
        court_workspace_root: str | None = None, court_baseline_pin: dict[str, Any] | None = None,
    ) -> None:
        self.base = base
        self.subject_root = base.subject_root
        verify_adapter_registry(adapter_registry, expected_subject_root=self.subject_root)
        require(supervisor.subject_root == self.subject_root, "WORKBENCH_V2_SUPERVISOR_CONTEXT_MISMATCH")
        require(type(platform_profiles) is dict and set(platform_profiles) == {"POSIX", "WINDOWS"}, "WORKBENCH_V2_PROFILE_SET_INVALID")
        for platform, profile in platform_profiles.items():
            verify_platform_profile(profile)
            require(profile["platform"] == platform, "WORKBENCH_V2_PROFILE_CONTEXT_MISMATCH")
        self.adapter_registry = deepcopy(adapter_registry)
        self.supervisor = supervisor
        self.platform_profiles = deepcopy(platform_profiles)
        self.composition_supervisors = dict(composition_supervisors or {})
        self.court_workspace_root = court_workspace_root
        self.court_baseline_pin = deepcopy(court_baseline_pin)
        require(all(type(key) is str and value.subject_root == self.subject_root and value.composition["composition_id"] == key for key, value in self.composition_supervisors.items()), "WORKBENCH_V2_COMPOSITION_SET_INVALID")
        self._results: dict[str, tuple[str, dict[str, Any]]] = {}

    def dispatch(self, value: Any) -> dict[str, Any]:
        request = exact_keys(value, {"schema", "surface", "idempotency_key", "effect_ceiling", "payload"}, "$.request")
        require(request["schema"] == "ucl.ucm.platform_workbench_request.v2" and request["surface"] in SURFACES_V2, "WORKBENCH_V2_SURFACE_INVALID")
        require(type(request["idempotency_key"]) is str and 8 <= len(request["idempotency_key"]) <= 128, "IDEMPOTENCY_KEY_INVALID")
        require(request["effect_ceiling"] == "NONE" and type(request["payload"]) is dict, "WORKBENCH_V2_EFFECT_CEILING_INVALID")
        request_root = root(request)
        prior = self._results.get(request["idempotency_key"])
        try:
            _scan_no_secrets(request["payload"], "$.request.payload")
            if prior is not None:
                require(prior[0] == request_root, "IDEMPOTENCY_CONFLICT")
                return deepcopy(prior[1])
            if request["surface"] == "DECIDE_COURT_LANE":
                payload = exact_keys(request["payload"], {"changed_paths", "circumstances", "frozen_candidate"}, "$.payload")
                require(type(payload["circumstances"]) is list and len(payload["circumstances"]) == 1 and type(payload["circumstances"][0]) is str, "AEP_C2_WORKBENCH_CIRCUMSTANCE_REQUIRED")
                require(type(payload["frozen_candidate"]) is bool, "AEP_C2_WORKBENCH_FROZEN_FLAG_INVALID")
                require(type(self.court_workspace_root) is str and self.court_workspace_root and self.court_baseline_pin is not None, "AEP_C2_WORKBENCH_COURT_CONTEXT_MISSING")
                graph = build_content_graph(pathlib.Path(self.court_workspace_root))
                verify_baseline_pin(self.court_baseline_pin, graph=graph)
                output = plan_lane(
                    changed_paths=payload["changed_paths"], circumstance=payload["circumstances"][0],
                    graph=graph, baseline_pin=self.court_baseline_pin,
                    frozen_candidate=payload["frozen_candidate"],
                )
            elif request["surface"] in LEGACY_SURFACES:
                legacy = self.base.dispatch({
                    "schema": "ucl.ucm.platform_workbench_request.v1",
                    "surface": request["surface"],
                    "idempotency_key": "v2:" + request["idempotency_key"],
                    "effect_ceiling": "NONE",
                    "payload": request["payload"],
                })
                if legacy["outcome"] == "REFUSED":
                    raise Refusal(legacy["diagnostic"], path=legacy["output"].get("path", "$"), detail=legacy["output"].get("detail"))
                output = legacy["output"]
            else:
                output = self._execute(request["surface"], request["payload"], request["idempotency_key"])
            outcome, diagnostic = "COMPLETED", "PASS"
        except Refusal as error:
            output = {"path": error.path, "detail": error.detail}
            outcome, diagnostic = "REFUSED", error.code
        except (KeyError, TypeError, IndexError) as error:
            output = {"path": "$.request.payload", "detail": type(error).__name__}
            outcome, diagnostic = "REFUSED", "WORKBENCH_V2_PAYLOAD_INVALID"
        body = {
            "schema": "ucl.ucm.platform_workbench_result.v2",
            "surface": request["surface"],
            "request_root": request_root,
            "outcome": outcome,
            "diagnostic": diagnostic,
            "output": output,
            "effect_observed": "NONE",
            "maximum_stage": "S2_INFORMATION_ONLY_FEDERATION",
            "standing": "INFORMATION_ONLY",
            "real_a5": False,
            "g0": "CLOSED",
            "authority_effect": "NONE",
        }
        result = {**body, "result_root": root(body)}
        if prior is None:
            self._results[request["idempotency_key"]] = (request_root, deepcopy(result))
        return result

    def _execute(self, surface: str, payload: dict[str, Any], key: str) -> dict[str, Any]:
        if surface == "DESCRIBE_ADAPTERS":
            exact_keys(payload, set(), "$.payload")
            return {
                "registry_root": self.adapter_registry["registry_root"],
                "adapters": [{
                    "adapter_id": item["adapter_id"], "adapter_root": item["adapter_root"],
                    "capability_id": item["capability_id"], "effect_class": item["effect_class"],
                } for item in self.adapter_registry["contracts"]],
            }
        if surface == "PREPARE_ADAPTER_INVOCATION":
            exact_keys(payload, {"adapter_id", "application_root", "tenant_id", "caller_principal_root", "input"}, "$.payload")
            return make_adapter_invocation(
                subject_root=self.subject_root, registry=self.adapter_registry, adapter_id=payload["adapter_id"],
                application_root=payload["application_root"], tenant_id=payload["tenant_id"],
                caller_principal_root=payload["caller_principal_root"], input_value=payload["input"],
                idempotency_key="adapter:" + key,
            )
        if surface == "VALIDATE_FIXTURE_ADAPTER_RECEIPT":
            exact_keys(payload, {"invocation", "output"}, "$.payload")
            contracts = {item["adapter_id"]: item for item in self.adapter_registry["contracts"]}
            require(payload["invocation"].get("adapter_id") in contracts, "ADAPTER_NOT_REGISTERED")
            return make_fixture_adapter_receipt(invocation=payload["invocation"], output_value=payload["output"], adapter_contract=contracts[payload["invocation"]["adapter_id"]])
        if surface == "REGISTER_SUPERVISED_APPLICATION":
            exact_keys(payload, {"application_id", "application_root", "tenant_id", "tenant_principal_root"}, "$.payload")
            return self.supervisor.register(**payload, idempotency_key="supervisor:" + key)
        if surface == "TRANSITION_SUPERVISOR":
            exact_keys(payload, {"application_id", "caller_principal_root", "target_state", "evidence_root"}, "$.payload")
            return self.supervisor.transition(**payload, idempotency_key="supervisor:" + key)
        if surface == "RECORD_SUPERVISOR_HEALTH":
            exact_keys(payload, {"application_id", "caller_principal_root", "health_root", "status"}, "$.payload")
            return self.supervisor.record_health(**payload, idempotency_key="supervisor:" + key)
        if surface == "OPEN_SUPERVISOR_INCIDENT":
            exact_keys(payload, {"application_id", "caller_principal_root", "incident_root"}, "$.payload")
            return self.supervisor.open_incident(**payload, idempotency_key="supervisor:" + key)
        if surface == "CLOSE_SUPERVISOR_INCIDENT":
            exact_keys(payload, {"application_id", "caller_principal_root", "resolution_root"}, "$.payload")
            return self.supervisor.close_incident(**payload, idempotency_key="supervisor:" + key)
        if surface == "INSPECT_SUPERVISOR":
            exact_keys(payload, set(), "$.payload")
            return self.supervisor.export_capsule()
        if surface == "START_COMPOSITION":
            exact_keys(payload, {"composition_id", "run_id", "tenant_id", "tenant_principal_root", "input_root"}, "$.payload")
            require(payload["composition_id"] in self.composition_supervisors, "COMPOSITION_NOT_REGISTERED")
            values = {name: payload[name] for name in payload if name != "composition_id"}
            return self.composition_supervisors[payload["composition_id"]].start(**values, idempotency_key="composition:" + key)
        if surface == "RECORD_COMPOSITION_NODE":
            exact_keys(payload, {"composition_id", "run_id", "tenant_principal_root", "node_id", "input_root", "output_root", "disposition"}, "$.payload")
            require(payload["composition_id"] in self.composition_supervisors, "COMPOSITION_NOT_REGISTERED")
            values = {name: payload[name] for name in payload if name != "composition_id"}
            return self.composition_supervisors[payload["composition_id"]].record_node(**values, idempotency_key="composition:" + key)
        if surface == "INSPECT_COMPOSITION":
            exact_keys(payload, {"composition_id"}, "$.payload")
            require(payload["composition_id"] in self.composition_supervisors, "COMPOSITION_NOT_REGISTERED")
            return self.composition_supervisors[payload["composition_id"]].export_capsule()
        if surface == "PREPARE_APPLICATION_BACKUP":
            exact_keys(payload, {"application_id", "generation", "state_capsule_root", "supervisor_capsule_root", "custody_capsule_root"}, "$.payload")
            return make_backup_receipt(subject_root=self.subject_root, **payload)
        if surface == "PREPARE_UPGRADE_PLAN":
            exact_keys(payload, {"installed_package", "candidate_package", "backup_receipt", "compatibility_root", "rollback_action_roots", "migration_step_roots"}, "$.payload")
            return make_upgrade_plan(subject_root=self.subject_root, **payload)
        if surface == "VALIDATE_UPGRADE_PLAN":
            exact_keys(payload, {"plan", "installed_package", "candidate_package", "backup_receipt"}, "$.payload")
            return verify_upgrade_plan(payload["plan"], expected_subject_root=self.subject_root, installed_package=payload["installed_package"], candidate_package=payload["candidate_package"], backup_receipt=payload["backup_receipt"])
        if surface == "PREPARE_LIFECYCLE_REHEARSAL":
            exact_keys(payload, {"upgrade_plan", "backup_receipt", "before_state_root", "mutated_state_root", "restored_state_root", "platform_profile_root"}, "$.payload")
            return make_lifecycle_rehearsal_receipt(**payload)
        if surface == "DESCRIBE_PROTECTED_PROFILE":
            exact_keys(payload, {"platform"}, "$.payload")
            require(payload["platform"] in self.platform_profiles, "PLATFORM_PROFILE_UNKNOWN")
            return deepcopy(self.platform_profiles[payload["platform"]])
        if surface == "PREPARE_PROTECTED_EXECUTION_CONTRACT":
            exact_keys(payload, {"platform", "candidate_root", "candidate_manifest_root", "entrypoint_root", "allowed_read_roots", "allowed_write_roots", "memory_bytes", "cpu_seconds", "process_limit"}, "$.payload")
            require(payload["platform"] in self.platform_profiles, "PLATFORM_PROFILE_UNKNOWN")
            values = {name: payload[name] for name in payload if name != "platform"}
            return make_protected_execution_contract(subject_root=self.subject_root, profile=self.platform_profiles[payload["platform"]], **values)
        if surface == "VALIDATE_EXTERNAL_EXECUTION":
            exact_keys(payload, {"receipt", "contract", "expected_executor_root", "expected_executor_attestation_root"}, "$.payload")
            platform = payload["contract"].get("platform")
            require(platform in self.platform_profiles, "PROTECTED_PROFILE_UNKNOWN")
            return verify_external_execution_receipt(payload["receipt"], contract=payload["contract"], expected_executor_root=payload["expected_executor_root"], expected_executor_attestation_root=payload["expected_executor_attestation_root"], expected_subject_root=self.subject_root, expected_profile=self.platform_profiles[platform])
        raise Refusal("WORKBENCH_V2_SURFACE_INVALID")

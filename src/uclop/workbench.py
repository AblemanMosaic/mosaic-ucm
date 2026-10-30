"""Supported agent/program boundary. Models supply data, never executable routes."""
from __future__ import annotations
from copy import deepcopy
from typing import Any
from .canonical import Refusal, exact_keys, require, root
from .workbench_contracts import reject_raw_secrets
from .workbench_orientation import verify_orientation
from .workbench_project import choose_lane

SURFACES = {
    "DISCOVER": ([], "READ_ONLY"),
    "ORIENT": ([], "READ_ONLY"),
    "INSPECT_PROJECT": ([], "READ_ONLY"),
    "INSPECT_PLAN": ([], "READ_ONLY"),
    "ASSESS_IMPACT": ([], "READ_ONLY"),
    "SELECT_LANE": ([], "READ_ONLY"),
    "STATUS": ([], "READ_ONLY"),
    "CURRENT_TASK_CONTEXT": ([], "READ_ONLY"),
    "COMPILE_PROOF_CONTRACT": ([], "PURE_COMPUTATION"),
    "PROVE_DEDUCTIVE_CONTRACT": ([], "PURE_COMPUTATION"),
    "VERIFY_DEDUCTIVE_PROOF": ([], "PURE_COMPUTATION"),
    "BEGIN_TASK": ([], "LOCAL_CUSTODY"),
    "RUN_TASK": ([], "LOCAL_BOUNDED_WORKER_AND_CUSTODY"),
    "COMPLETE_TASK": ([], "LOCAL_CUSTODY"),
    "MARK_UNCERTAIN": ([], "LOCAL_CUSTODY"),
    "RECONCILE_NOT_EXECUTED": ([], "LOCAL_CUSTODY"),
    "ATTEST_NOT_EXECUTED": ([], "READ_ONLY_SIGNED_OBSERVATION"),
    "PREPARE_RECOVERY_AUTHORIZATION": ([], "READ_ONLY"),
    "EXPORT_CAPSULE": ([], "READ_ONLY"),
    "COMPILE_INTENT": ([], "PURE_COMPUTATION"),
}

def capability_registry() -> dict:
    body = {"schema": "ucl.ucm.workbench.capability_registry.v1", "surfaces": [
        {"name": name, "effect_scope": effect, "readiness_required": name != "DISCOVER"} for name, (_, effect) in sorted(SURFACES.items())],
        "worker_operations": ["INSPECT_ARTIFACTS", "PREPARE_CANDIDATE", "RUN_TESTS"],
        "external_signer": "OPAQUE_PROVIDER_REQUIRED_FOR_NONFIXTURE_USE", "hostile_code_sandbox": "UNBOUND_EXTERNAL",
        "dkn_federation": "UNBOUND_EXTERNAL", "production_authority": False, "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
    return {**body, "registry_root": root(body)}


def supported_effect_scope(surface: str) -> str:
    """Truthful effect projection while retaining the pinned legacy response ABI."""
    require(type(surface) is str and surface in SURFACES, "WORKBENCH_SURFACE_UNKNOWN")
    return "LOCAL_CUSTODY" if surface == "ATTEST_NOT_EXECUTED" else SURFACES[surface][1]

class Workbench:
    def __init__(self, *, manager: Any, worker: Any, orientation: dict,
                 orientation_pins: dict, graph: dict, expected_graph_root: str,
                 expected_implementation_root: str, now: int,
                 baseline_graph: dict | None = None,
                 expected_baseline_graph_root: str | None = None):
        try:
            checked = verify_orientation(orientation, external_pins=orientation_pins, now=now, expected_head=orientation["current_head"])
        except Refusal:
            recovery = getattr(manager, "_recovery_body", None)
            require(type(recovery) is dict and recovery.get("orientation_root") == orientation.get("root")
                    and orientation.get("root") == root({key: value for key, value in orientation.items() if key != "root"})
                    and recovery.get("issued_at", now + 1) <= now <= recovery.get("expires_at", now - 1),
                    "WORKBENCH_RECOVERY_CONTEXT_INVALID")
            checked = deepcopy(orientation)
        require(checked["registry_root"] == capability_registry()["registry_root"], "WORKBENCH_REGISTRY_PIN_MISMATCH")
        require(checked["implementation_root"] == expected_implementation_root, "WORKBENCH_IMPLEMENTATION_PIN_MISMATCH")
        require(graph["graph_root"] == expected_graph_root == root({k: v for k, v in graph.items() if k != "graph_root"}), "WORKBENCH_GRAPH_PIN_MISMATCH")
        require(graph["source_root"] == checked["source_root"], "WORKBENCH_GRAPH_SOURCE_MISMATCH")
        require(manager.orientation["root"] == checked["root"] and manager.worker_root == worker.worker_root, "WORKBENCH_COMPOSITION_BINDING_MISMATCH")
        self.manager, self.worker = manager, worker
        self.orientation, self.pins = deepcopy(checked), deepcopy(orientation_pins)
        self.graph, self.graph_root = deepcopy(graph), expected_graph_root
        if baseline_graph is not None:
            require(baseline_graph.get("graph_root") == expected_baseline_graph_root
                    == root({key: value for key, value in baseline_graph.items() if key != "graph_root"}),
                    "WORKBENCH_BASELINE_GRAPH_PIN_MISMATCH")
        self.baseline_graph = deepcopy(baseline_graph)
        self.baseline_graph_root = expected_baseline_graph_root

    def dispatch(self, request: Any, *, now: int) -> dict:
        exact_keys(request, {"schema", "surface", "payload", "context_root", "request_id", "expected_head"})
        require(request["schema"] == "ucl.ucm.workbench.request.v1", "WORKBENCH_REQUEST_SCHEMA_INVALID")
        require(type(request["surface"]) is str and request["surface"] in SURFACES, "WORKBENCH_SURFACE_UNKNOWN")
        require(type(request["request_id"]) is str and 0 < len(request["request_id"]) <= 200, "WORKBENCH_REQUEST_ID_INVALID")
        require(type(request["payload"]) is dict, "WORKBENCH_PAYLOAD_INVALID")
        reject_raw_secrets(request["payload"])
        require(request["context_root"] == self.orientation["root"], "WORKBENCH_CONTEXT_STALE")
        surface, payload = request["surface"], request["payload"]
        try:
            verify_orientation(self.orientation, external_pins=self.pins, now=now, expected_head=self.orientation["current_head"])
        except Refusal:
            recovery_safe = {"STATUS", "CURRENT_TASK_CONTEXT", "COMPLETE_TASK", "MARK_UNCERTAIN", "RECONCILE_NOT_EXECUTED",
                             "ATTEST_NOT_EXECUTED", "PREPARE_RECOVERY_AUTHORIZATION", "EXPORT_CAPSULE"}
            require(surface in recovery_safe and (surface in {"ATTEST_NOT_EXECUTED", "PREPARE_RECOVERY_AUTHORIZATION"}
                    or getattr(self.manager, "recovery_authorization", None) is not None),
                    "WORKBENCH_RECOVERY_SURFACE_REFUSED")
        head = request["expected_head"]
        if surface == "DISCOVER":
            exact_keys(payload, set()); result = capability_registry()
        elif surface == "ORIENT":
            exact_keys(payload, set()); result = deepcopy(self.orientation)
        elif surface == "STATUS":
            exact_keys(payload, set()); result = self.manager.status(expected_head=head, now=now)
        elif surface == "CURRENT_TASK_CONTEXT":
            exact_keys(payload, {"task_id"})
            result = self.manager.current_task_context(payload["task_id"], expected_head=head, now=now)
        elif surface == "INSPECT_PLAN":
            exact_keys(payload, set()); self.manager.status(expected_head=head, now=now); result = deepcopy(self.manager.plan)
        elif surface == "INSPECT_PROJECT":
            exact_keys(payload, set()); self.manager.status(expected_head=head, now=now); result = deepcopy(self.manager.project)
        elif surface == "ASSESS_IMPACT":
            exact_keys(payload, {"changed_ids", "changed_paths"})
            from .project_intelligence import impact_analysis
            result = impact_analysis(self.manager.project, payload["changed_ids"], payload["changed_paths"])
        elif surface == "SELECT_LANE":
            exact_keys(payload, {"changed_paths", "circumstance", "frozen_source_root"})
            result = choose_lane(payload["changed_paths"], payload["circumstance"], graph=self.graph,
                externally_pinned_graph_root=self.graph_root, frozen_source_root=payload["frozen_source_root"],
                baseline_graph=self.baseline_graph,
                externally_pinned_baseline_graph_root=self.baseline_graph_root)
        elif surface == "COMPILE_PROOF_CONTRACT":
            exact_keys(payload, {"contract"})
            from .deductive_proofs import compile_contract
            result = compile_contract(payload["contract"])
        elif surface == "PROVE_DEDUCTIVE_CONTRACT":
            exact_keys(payload, {"contract"})
            from .deductive_proofs import prove_contract
            result = prove_contract(payload["contract"])
        elif surface == "VERIFY_DEDUCTIVE_PROOF":
            exact_keys(payload, {"contract", "proof_bundle"})
            from .deductive_proofs import verify_proof
            result = verify_proof(payload["contract"], payload["proof_bundle"])
        elif surface in {"BEGIN_TASK", "RUN_TASK"}:
            exact_keys(payload, {"task_id", "dispatcher_id"})
            args = (payload["task_id"], request["request_id"], payload["dispatcher_id"])
            result = self.manager.execute(*args, self.worker, expected_head=head, now=now) if surface == "RUN_TASK" else self.manager.begin_dispatch(*args, expected_head=head, now=now, worker=self.worker)
        elif surface == "COMPLETE_TASK":
            exact_keys(payload, {"ticket", "result"})
            result = self.manager.complete_dispatch(payload["ticket"], payload["result"], expected_head=head, now=now)
        elif surface == "MARK_UNCERTAIN":
            exact_keys(payload, {"ticket", "diagnostic"})
            result = self.manager.mark_uncertain(payload["ticket"], diagnostic=payload["diagnostic"], expected_head=head, now=now)
        elif surface == "RECONCILE_NOT_EXECUTED":
            exact_keys(payload, {"ticket", "attestation"})
            result = self.manager.reconcile_not_executed(payload["ticket"], payload["attestation"], expected_head=head, now=now)
        elif surface == "ATTEST_NOT_EXECUTED":
            exact_keys(payload, {"request"})
            self.manager.validate_cancellation_context(payload["request"], expected_head=head)
            result = self.worker.attest_not_executed(payload["request"])
        elif surface == "PREPARE_RECOVERY_AUTHORIZATION":
            exact_keys(payload, {"ticket", "actions", "issued_at", "expires_at"})
            result = self.manager.prepare_recovery_authorization(payload["ticket"], expected_head=head,
                actions=payload["actions"], issued_at=payload["issued_at"], expires_at=payload["expires_at"])
        elif surface == "EXPORT_CAPSULE":
            exact_keys(payload, set()); result = self.manager.export_capsule(expected_head=head, now=now)
        else:
            exact_keys(payload, {"intent"})
            from .constitutional import validate_intent, tessera_projection, build_cru, build_bcr
            from .pipeline import compile_contract
            intent = validate_intent(payload["intent"])
            require(intent["jurisdiction"] == self.orientation["jurisdiction"], "WORKBENCH_INTENT_JURISDICTION_MISMATCH")
            tessera = tessera_projection(intent); cru = build_cru(intent, tessera); bcr = build_bcr(intent, cru)
            result = {"tessera": tessera, "cru": cru, "bcr": bcr, "compilation": compile_contract(bcr["operation_contract"])}
        body = {"schema": "ucl.ucm.workbench.response.v1", "surface": surface, "request_root": root(request),
                "context_root": self.orientation["root"], "result": result,
                "effect_scope": SURFACES[surface][1], "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}
        return {**body, "response_root": root(body)}

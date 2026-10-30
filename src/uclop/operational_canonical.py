"""Canonical agent-facing facade over realization, proof and project systems."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any

from .canonical import canonical_bytes, exact_keys, require, require_root, root
from .maturity_semantics import BOUNDARY, seal
from .workbench_contracts import reject_raw_secrets
from . import autonomous_project_manager as apm
from . import project_intelligence as pi
from .operational_explanation import (
    make_explanation_graph,
    make_semantic_change_plan,
    make_tcb_ledger,
    verify_semantic_inventory_contract,
)
from .operational_evidence import accept_claim_evidence, verify_evidence_acceptance_contract
from .operational_ontology import make_correspondence
from .operational_realization import (check_admissibility, project_to_ucl_tessera, select_realization,
                                      trace_adaptation, verify_space_contract)
from .deductive_proofs import verify_proof
from .maturity_proof import evaluate_gate

SURFACES = {
    "ORIENT",
    "CHECK_ADMISSIBILITY", "COMPARE_REALIZATIONS", "DESCRIBE_REALIZATION_SPACE",
    "EXPLAIN_SELECTION", "MAKE_EXPLANATION_GRAPH", "MAKE_SEMANTIC_CHANGE_PLAN",
    "MAKE_TCB_LEDGER", "ONTOLOGY_CORRESPONDENCE", "PREPARE_AUTONOMOUS_PLAN",
    "PROJECT_DASHBOARD", "PROJECT_TO_UCL_TESSERA", "TRACE_ADAPTATION",
    "VERIFY_NATIVE_PROOF", "EVALUATE_PROOF_GATE",
    "ACCEPT_CLAIM_EVIDENCE",
}


def orientation() -> dict[str, Any]:
    """Return the compact human/agent map without reading or mutating a workspace."""
    return seal({"schema": "ucl.ucm.operational_orientation.v1",
        "subject": "MOSAIC-UCM-v0.1-COMPATIBILITY",
        "start_here": {"human": "README.md", "agent": "docs/AGENT-START.md",
                       "capabilities": "docs/CAPABILITY-SURFACES.md",
                       "realization": "docs/REALIZATION-SPACE.md",
                       "cold_boot": "docs/RELEASE-AND-REVIEW.md"},
        "conceptual_interface": ["DESCRIBE", "CONSTRAIN", "CHECK", "COMPARE", "SELECT", "PROJECT",
                                 "TRACE", "PROVE", "EXPLAIN", "PREPARE"],
        "direct_surfaces": sorted(SURFACES),
        "canonical_cli": "python -m ucm.cli", "canonical_portable": "tools/build_release.py",
        "evidence_rule": "CLAIM_MEANING_REQUIRES_A_MANIFEST_PINNED_EVIDENCE_ACCEPTANCE_CONTRACT",
        "effect_model": "PURE_COMPUTATION_OR_READ_ONLY; EFFECTFUL_EXECUTION_REQUIRES_A_SEPARATE_GOVERNED_STAGE",
        **BOUNDARY})


def capability_registry() -> dict[str, Any]:
    rows = [{"name": name, "effect_scope": "READ_ONLY" if name == "PROJECT_DASHBOARD" else "PURE_COMPUTATION",
             "readiness_required": True} for name in sorted(SURFACES)]
    return seal({"schema": "ucl.ucm.operational_capability_registry.v1",
        "subject": "MOSAIC-UCM-v0.1-COMPATIBILITY", "surfaces": rows,
        "composition": {"agent_workbench": "PINNED_PURE_COMPUTATION_AND_VERIFICATION_FACADE", "project_intelligence": "BOUND_LIBRARY",
                        "autonomous_project_management": "PLAN_ONLY_NO_EXECUTION", "native_proof": "CERTIFICATE_AND_GATE",
                        "mature_execution": "SEPARATE_COMPATIBILITY_INTERFACE_NOT_DISPATCHED",
                        "application_return": "SEPARATE_COMPATIBILITY_INTERFACE_NOT_DISPATCHED",
                        "ontology": "OPTIONAL_CORRESPONDENCE_ONLY"}, **BOUNDARY})


def make_system_manifest(*, source_root: str, maturity_registry_root: str,
                         realization_contract_roots: dict[str, str], project_root: str | None = None,
                         evidence_contract_roots: dict[str, str] | None = None,
                         semantic_inventory_roots: dict[str, str] | None = None) -> dict[str, Any]:
    require_root(source_root); require_root(maturity_registry_root)
    require(type(realization_contract_roots) is dict and bool(realization_contract_roots), "OPERATIONAL_REALIZATION_PINS_INVALID")
    for name, digest in realization_contract_roots.items():
        require(type(name) is str and name, "OPERATIONAL_REALIZATION_ID_INVALID"); require_root(digest)
    evidence_contract_roots = {} if evidence_contract_roots is None else evidence_contract_roots
    require(type(evidence_contract_roots) is dict, "OPERATIONAL_EVIDENCE_PINS_INVALID")
    for name, digest in evidence_contract_roots.items():
        require(type(name) is str and name, "OPERATIONAL_EVIDENCE_ID_INVALID"); require_root(digest)
    semantic_inventory_roots = {} if semantic_inventory_roots is None else semantic_inventory_roots
    require(type(semantic_inventory_roots) is dict, "OPERATIONAL_SEMANTIC_INVENTORY_PINS_INVALID")
    for name, digest in semantic_inventory_roots.items():
        require(type(name) is str and name, "OPERATIONAL_SEMANTIC_INVENTORY_ID_INVALID"); require_root(digest)
    if project_root is not None: require_root(project_root)
    return seal({"schema": "ucl.ucm.operational_system_manifest.v1", "source_root": source_root,
        "operational_registry_root": capability_registry()["root"], "maturity_registry_root": maturity_registry_root,
        "realization_contract_roots": deepcopy(realization_contract_roots), "project_root": project_root,
        "evidence_contract_roots": deepcopy(evidence_contract_roots),
        "semantic_inventory_roots": deepcopy(semantic_inventory_roots),
        "mosaicos_m1": {"identity_status": "UNBOUND", "binding_status": "PREPARED_INTERFACE_ONLY"},
        "application_integrations": "EXACT_REQUEST_AND_RETURN_KITS_ONLY", **BOUNDARY})


def verify_system_manifest(value: Any, *, expected_root: str, expected_maturity_registry_root: str) -> dict[str, Any]:
    require(type(value) is dict and value.get("schema") == "ucl.ucm.operational_system_manifest.v1",
            "OPERATIONAL_MANIFEST_INVALID")
    rebuilt = make_system_manifest(source_root=value.get("source_root"),
        maturity_registry_root=value.get("maturity_registry_root"),
        realization_contract_roots=value.get("realization_contract_roots"), project_root=value.get("project_root"),
        evidence_contract_roots=value.get("evidence_contract_roots"),
        semantic_inventory_roots=value.get("semantic_inventory_roots"))
    require(canonical_bytes(value) == canonical_bytes(rebuilt), "OPERATIONAL_MANIFEST_RECONSTRUCTION_MISMATCH")
    require(value["root"] == require_root(expected_root), "OPERATIONAL_MANIFEST_PIN_MISMATCH")
    require(value["maturity_registry_root"] == require_root(expected_maturity_registry_root),
            "OPERATIONAL_MATURITY_REGISTRY_PIN_MISMATCH")
    return rebuilt


class OperationalCanonicalWorkbench:
    def __init__(self, manifest: dict[str, Any], contracts: dict[str, dict[str, Any]], *,
                 expected_manifest_root: str, expected_maturity_registry_root: str,
                 project: dict[str, Any] | None = None, workspace: Path | None = None,
                 evidence_contracts: dict[str, dict[str, Any]] | None = None,
                 semantic_inventories: dict[str, dict[str, Any]] | None = None):
        manifest = verify_system_manifest(manifest, expected_root=expected_manifest_root,
            expected_maturity_registry_root=expected_maturity_registry_root)
        require(manifest.get("operational_registry_root") == capability_registry()["root"], "OPERATIONAL_REGISTRY_PIN_MISMATCH")
        require(type(contracts) is dict and set(contracts) == set(manifest.get("realization_contract_roots", {})),
                "OPERATIONAL_CONTRACT_SET_MISMATCH")
        self.contracts = {}
        for name, contract in contracts.items():
            self.contracts[name] = verify_space_contract(contract, expected_root=manifest["realization_contract_roots"][name])
        evidence_contracts = {} if evidence_contracts is None else evidence_contracts
        require(type(evidence_contracts) is dict and set(evidence_contracts) == set(manifest["evidence_contract_roots"]),
                "OPERATIONAL_EVIDENCE_CONTRACT_SET_MISMATCH")
        self.evidence_contracts = {}
        for name, contract in evidence_contracts.items():
            self.evidence_contracts[name] = verify_evidence_acceptance_contract(
                contract, expected_root=manifest["evidence_contract_roots"][name])
        semantic_inventories = {} if semantic_inventories is None else semantic_inventories
        require(type(semantic_inventories) is dict and set(semantic_inventories) == set(manifest["semantic_inventory_roots"]),
                "OPERATIONAL_SEMANTIC_INVENTORY_SET_MISMATCH")
        self.semantic_inventories = {}
        for name, inventory in semantic_inventories.items():
            self.semantic_inventories[name] = verify_semantic_inventory_contract(
                inventory, expected_root=manifest["semantic_inventory_roots"][name])
        self.manifest = deepcopy(manifest); self.project = deepcopy(project); self.workspace = workspace
        if project is not None:
            require(workspace is not None, "OPERATIONAL_PROJECT_WORKSPACE_REQUIRED")
            pi.validate_project(project, expected_source_root=manifest["source_root"])
            require(project["snapshot_root"] == manifest["project_root"], "OPERATIONAL_PROJECT_PIN_MISMATCH")

    def _contract(self, payload: dict[str, Any]) -> dict[str, Any]:
        require(type(payload.get("contract_id")) is str and payload["contract_id"] in self.contracts,
                "OPERATIONAL_CONTRACT_UNKNOWN")
        return self.contracts[payload["contract_id"]]

    def dispatch(self, request: Any) -> dict[str, Any]:
        item = exact_keys(request, {"schema", "surface", "payload", "request_id", "manifest_root"})
        canonical_bytes(item); reject_raw_secrets(item["payload"])
        require(item["schema"] == "ucl.ucm.operational_request.v1" and item["manifest_root"] == self.manifest["root"],
                "OPERATIONAL_REQUEST_CONTEXT_INVALID")
        require(type(item["request_id"]) is str and item["request_id"] and item["surface"] in SURFACES
                and type(item["payload"]) is dict, "OPERATIONAL_REQUEST_INVALID")
        surface, payload = item["surface"], item["payload"]
        if surface == "ORIENT":
            exact_keys(payload, set()); result = orientation()
        elif surface == "DESCRIBE_REALIZATION_SPACE":
            exact_keys(payload, {"contract_id"}); result = deepcopy(self._contract(payload))
        elif surface == "CHECK_ADMISSIBILITY":
            exact_keys(payload, {"contract_id", "configuration"}); result = check_admissibility(self._contract(payload), payload["configuration"])
        elif surface in {"COMPARE_REALIZATIONS", "EXPLAIN_SELECTION"}:
            exact_keys(payload, {"contract_id", "candidates"}); result = select_realization(self._contract(payload), payload["candidates"])
        elif surface == "PROJECT_TO_UCL_TESSERA":
            exact_keys(payload, {"contract_id"}); result = project_to_ucl_tessera(self._contract(payload))
        elif surface == "TRACE_ADAPTATION":
            exact_keys(payload, {"contract_id", "before", "after"}); result = trace_adaptation(self._contract(payload), payload["before"], payload["after"])
        elif surface == "ACCEPT_CLAIM_EVIDENCE":
            exact_keys(payload, {"evidence_contract_id", "evidence", "claim_id"})
            require(payload["evidence_contract_id"] in self.evidence_contracts, "OPERATIONAL_EVIDENCE_CONTRACT_UNKNOWN")
            contract=self.evidence_contracts[payload["evidence_contract_id"]]
            result=accept_claim_evidence(contract, payload["evidence"], expected_contract_root=contract["root"],
                                         claim_id=payload["claim_id"])
        elif surface == "MAKE_EXPLANATION_GRAPH":
            exact_keys(payload, {"assertions", "edges", "proof_roots"})
            result = make_explanation_graph(subject_root=self.manifest["source_root"],
                evidence_contracts=list(self.evidence_contracts.values()),
                accepted_contract_roots=sorted(self.manifest["evidence_contract_roots"].values()), **payload)
        elif surface == "MAKE_TCB_LEDGER":
            exact_keys(payload, {"components"}); result = make_tcb_ledger(subject_root=self.manifest["source_root"],
                evidence_contracts=list(self.evidence_contracts.values()),
                accepted_contract_roots=sorted(self.manifest["evidence_contract_roots"].values()), **payload)
        elif surface == "MAKE_SEMANTIC_CHANGE_PLAN":
            exact_keys(payload, {"inventory_id", "evidence_checks", "expected_evidence_roots", "method"})
            require(payload["inventory_id"] in self.semantic_inventories,
                    "OPERATIONAL_SEMANTIC_INVENTORY_UNKNOWN")
            inventory = self.semantic_inventories[payload["inventory_id"]]
            result = make_semantic_change_plan(
                inventory_contract=inventory,
                expected_inventory_contract_root=inventory["root"],
                evidence_checks=payload["evidence_checks"],
                expected_evidence_roots=payload["expected_evidence_roots"],
                method=payload["method"],
                evidence_contracts=list(self.evidence_contracts.values()),
                accepted_contract_roots=sorted(self.manifest["evidence_contract_roots"].values()))
        elif surface == "VERIFY_NATIVE_PROOF":
            exact_keys(payload, {"contract", "proof_bundle", "expected_contract_root", "expected_proof_bundle_root"})
            require(payload["contract"].get("contract_root") == require_root(payload["expected_contract_root"]),
                    "PROOF_CONTRACT_PIN_MISMATCH")
            require(payload["proof_bundle"].get("proof_bundle_root") == require_root(payload["expected_proof_bundle_root"]),
                    "PROOF_BUNDLE_PIN_MISMATCH")
            result = verify_proof(payload["contract"], payload["proof_bundle"])
        elif surface == "EVALUATE_PROOF_GATE":
            exact_keys(payload, {"plan", "proof_bundles", "expected_subject_root", "expected_plan_root",
                                 "expected_inventory_root", "expected_obligation_ids"})
            result = evaluate_gate(**payload)
        elif surface == "ONTOLOGY_CORRESPONDENCE":
            exact_keys(payload, {"ontology_root", "mappings", "adjudication"})
            result = make_correspondence(ucm_subject_root=self.manifest["source_root"], **payload)
        elif surface == "PROJECT_DASHBOARD":
            exact_keys(payload, set()); require(self.project is not None and self.workspace is not None, "OPERATIONAL_PROJECT_NOT_CONFIGURED")
            result = pi.project_dashboard(self.project, self.workspace)
        elif surface == "PREPARE_AUTONOMOUS_PLAN":
            exact_keys(payload, {"changed_ids", "changed_paths", "objective"}); require(self.project is not None, "OPERATIONAL_PROJECT_NOT_CONFIGURED")
            result = apm.make_plan(self.project, payload["changed_ids"], payload["changed_paths"], objective=payload["objective"])
        else:
            require(False, "OPERATIONAL_SURFACE_UNKNOWN")
        return seal({"schema": "ucl.ucm.operational_response.v1", "request_root": root(item),
            "surface": surface, "manifest_root": self.manifest["root"], "result": result,
            "effect_scope": "READ_ONLY" if surface == "PROJECT_DASHBOARD" else "PURE_COMPUTATION", **BOUNDARY})

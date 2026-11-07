"""Constitutional integration coordinator over the operational gateway.

This module does not execute effects and does not turn native control-plane
reports into authority.  It binds separately named native reports, explains
their contribution to the decision, and delegates custody to OperationGateway.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import os
from typing import Any

from uclop.canonical import canonical_bytes, exact_keys, require, require_root, root, strict_loads

from .amcas import BOUNDARY
from .application_capsule import validate_application_capsule
from .operation_gateway import OperationGateway, validate_operation_contract
from .progress import Progress


ADAPTER_SCHEMA = "mosaic.ucm.native-control-plane-result.v0.1"
GRAVITY_SCHEMA = "mosaic.ucm.semantic-gravity-explanation.v0.1"
PREPARATION_SCHEMA = "mosaic.ucm.constitutional-integration-preparation.v0.1"
COMPLETION_SCHEMA = "mosaic.ucm.constitutional-integration-completion.v0.1"

PROTOCOLS = {
    "UGK", "ESA", "SRSA", "COP", "EVS_EVENT_EVIDENCE_STREAM",
    "EVS_EVIDENCE_VERIFICATION_SUBSYSTEM", "HEADLESS_RUNNER",
    "TEST_CONTROL", "REPAIR_CONTROL",
}
DISPOSITIONS = {"RETAIN", "ADAPT", "REPLACE_AFTER_EQUIVALENCE", "NOT_APPLICABLE"}
DECISIONS = {"PASS", "REFUSED", "NOT_APPLICABLE"}


def _identifier(value: Any, code: str) -> str:
    require(type(value) is str and value == value.strip() and 0 < len(value) <= 192
            and all(ch.isalnum() or ch in "._:-" for ch in value), code)
    return value


def _identifiers(value: Any, code: str, *, allow_empty: bool = True) -> list[str]:
    require(type(value) is list and value == sorted(set(value))
            and (allow_empty or bool(value)), code)
    return [_identifier(item, code) for item in value]


def build_adapter_result(*, adapter_id: str, protocol_id: str,
                         provider_root: str, version: str, subject_root: str,
                         policy_root: str, input_root: str, decision: str,
                         reason_codes: list[str], evidence_roots: list[str],
                         disposition: str) -> dict[str, Any]:
    """Build a non-authorizing, content-addressed native-plane result."""
    _identifier(adapter_id, "ADAPTER_ID_INVALID")
    require(protocol_id in PROTOCOLS, "ADAPTER_PROTOCOL_INVALID")
    _identifier(version, "ADAPTER_VERSION_INVALID")
    for value in (provider_root, subject_root, policy_root, input_root):
        require_root(value)
    require(decision in DECISIONS, "ADAPTER_DECISION_INVALID")
    _identifiers(reason_codes, "ADAPTER_REASON_CODES_INVALID")
    require(type(evidence_roots) is list and evidence_roots == sorted(set(evidence_roots)),
            "ADAPTER_EVIDENCE_ROOTS_INVALID")
    for evidence_root in evidence_roots:
        require_root(evidence_root)
    require(disposition in DISPOSITIONS, "ADAPTER_DISPOSITION_INVALID")
    body = {
        "schema": ADAPTER_SCHEMA, "adapter_id": adapter_id,
        "protocol_id": protocol_id, "provider_root": provider_root,
        "version": version, "subject_root": subject_root,
        "policy_root": policy_root, "input_root": input_root,
        "decision": decision, "reason_codes": list(reason_codes),
        "evidence_roots": list(evidence_roots), "effect_claim": "NONE",
        "disposition": disposition, **BOUNDARY,
    }
    return {**body, "adapter_result_root": root(body)}


def validate_adapter_result(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "adapter_id", "protocol_id", "provider_root",
        "version", "subject_root", "policy_root", "input_root", "decision",
        "reason_codes", "evidence_roots", "effect_claim", "disposition",
        "standing", "authority_effect", "real_a5", "g0", "adapter_result_root"})
    expected = build_adapter_result(
        adapter_id=item["adapter_id"], protocol_id=item["protocol_id"],
        provider_root=item["provider_root"], version=item["version"],
        subject_root=item["subject_root"], policy_root=item["policy_root"],
        input_root=item["input_root"], decision=item["decision"],
        reason_codes=item["reason_codes"], evidence_roots=item["evidence_roots"],
        disposition=item["disposition"])
    require(item == expected and item["effect_claim"] == "NONE",
            "ADAPTER_RESULT_INVALID")
    return deepcopy(item)


def validate_integration_policy(value: Any, *, expected_root: str) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "policy_id", "required_protocols",
        "required_gates", "forbidden_adapter_effect_claims",
        "native_executor_selection", "progress_semantics", "uncertain_policy",
        "capability_grant_effect_class", "standing", "authority_effect",
        "real_a5", "g0", "policy_pack_root"})
    require(item["schema"] == "mosaic.ucm.integration-policy-pack.v0.1",
            "INTEGRATION_POLICY_SCHEMA_INVALID")
    _identifier(item["policy_id"], "INTEGRATION_POLICY_ID_INVALID")
    require(type(item["required_protocols"]) is list
            and item["required_protocols"] == sorted(set(item["required_protocols"]))
            and bool(item["required_protocols"])
            and set(item["required_protocols"]) <= PROTOCOLS,
            "INTEGRATION_POLICY_PROTOCOLS_INVALID")
    require(item["required_gates"] == ["G1_SENTINEL", "G2_WITNESS", "G3_DIAGNOSTIC"],
            "INTEGRATION_POLICY_GATES_INVALID")
    require(type(item["forbidden_adapter_effect_claims"]) is list
            and item["forbidden_adapter_effect_claims"] ==
                sorted(set(item["forbidden_adapter_effect_claims"])),
            "INTEGRATION_POLICY_EFFECTS_INVALID")
    require(item["native_executor_selection"] == "EXTERNAL_ONLY"
            and item["progress_semantics"] == "NONE"
            and item["uncertain_policy"] == "RECONCILE_WITHOUT_REDISPATCH"
            and item["capability_grant_effect_class"] == "AUTHORITY_CHANGE",
            "INTEGRATION_POLICY_SEMANTICS_INVALID")
    require({key: item[key] for key in BOUNDARY} == BOUNDARY,
            "INTEGRATION_POLICY_AUTHORITY_INVALID")
    body = {key: deepcopy(raw) for key, raw in item.items()
            if key != "policy_pack_root"}
    require(item["policy_pack_root"] == root(body)
            and item["policy_pack_root"] == require_root(expected_root),
            "INTEGRATION_POLICY_ROOT_INVALID")
    return deepcopy(item)

def build_semantic_gravity(*, gate: str, contract: dict[str, Any],
                           adapter_results: list[dict[str, Any]],
                           required_protocols: list[str],
                           integration_policy_root: str,
                           receipt_roots: list[str]) -> dict[str, Any]:
    """Explain a gate decision with separate THR/UGK commitments.

    These explanations are deterministic projections.  They never replace the
    signed permit, external receipts, or OperationGateway journal.
    """
    require(gate in {"G1_SENTINEL", "G2_WITNESS", "G3_DIAGNOSTIC"},
            "SEMANTIC_GRAVITY_GATE_INVALID")
    require(type(contract) is dict and "contract_root" in contract,
            "SEMANTIC_GRAVITY_CONTRACT_INVALID")
    contract_body = {key: deepcopy(value) for key, value in contract.items()
                     if key != "contract_root"}
    require(contract["contract_root"] == root(contract_body),
            "SEMANTIC_GRAVITY_CONTRACT_ROOT_INVALID")
    require({key: contract_body.get(key) for key in BOUNDARY} == BOUNDARY,
            "SEMANTIC_GRAVITY_AUTHORITY_CEILING_INVALID")
    require(type(adapter_results) is list, "ADAPTER_RESULTS_INVALID")
    adapters = sorted((validate_adapter_result(row) for row in adapter_results),
                      key=lambda row: (row["protocol_id"], row["adapter_id"]))
    require(len(adapters) == len({row["adapter_id"] for row in adapters}),
            "ADAPTER_ID_DUPLICATE")
    require(type(required_protocols) is list
            and required_protocols == sorted(set(required_protocols))
            and set(required_protocols) <= PROTOCOLS,
            "REQUIRED_PROTOCOLS_INVALID")
    require(type(receipt_roots) is list and receipt_roots == sorted(set(receipt_roots)),
            "SEMANTIC_GRAVITY_RECEIPTS_INVALID")
    for receipt_root in receipt_roots:
        require_root(receipt_root)
    by_protocol = {row["protocol_id"] for row in adapters
                   if row["decision"] == "PASS"}
    failed = [row["adapter_id"] for row in adapters if row["decision"] == "REFUSED"]
    missing = sorted(set(required_protocols) - by_protocol)
    rules = [
        {"rule_id": "THR_COMMITMENTS_SEPARATE", "status": "PASS"},
        {"rule_id": "NATIVE_AUTHORITY_REMAINS_EXTERNAL", "status": "PASS"},
        {"rule_id": "ADAPTERS_CLAIM_NO_EFFECT", "status":
         "PASS" if all(row["effect_claim"] == "NONE" for row in adapters) else "REFUSED"},
        {"rule_id": "REQUIRED_PROTOCOLS_PRESENT", "status":
         "PASS" if not missing else "REFUSED"},
        {"rule_id": "NO_NATIVE_PLANE_REFUSED", "status":
         "PASS" if not failed else "REFUSED"},
    ]
    decision = "ALLOW" if all(row["status"] == "PASS" for row in rules) else "REFUSE"
    body = {
        "schema": GRAVITY_SCHEMA, "gate": gate,
        "operation_id": contract["operation_id"],
        "contract_root": require_root(contract["contract_root"]),
        "commitments": {
            "state_root": root({"operation_id": contract["operation_id"],
                                "request_root": contract["request_root"]}),
            "admissibility_root": root({"permit_root": contract["permit"]["permit_root"],
                                         "requested_effect_classes": contract["requested_effect_classes"],
                                         "budget": contract["budget"]}),
            "meaning_root": root({"application_id": contract["application_id"],
                                   "action_id": contract["action_id"],
                                   "expected_result_root": contract["expected_result_root"]}),
            "locality_root": root({"jurisdiction_root": contract["jurisdiction_root"],
                                    "subject_identity_root": contract["subject_identity_root"],
                                    "session_root": contract["session_root"]}),
            "receipt_policy_root": root({"executor_public_key_hex":
                                           contract["executor_public_key_hex"],
                                           "receipt_roots": receipt_roots}),
        },
        "adapter_result_roots": [row["adapter_result_root"] for row in adapters],
        "required_protocols": list(required_protocols),
        "integration_policy_root": require_root(integration_policy_root),
        "missing_protocols": missing, "refused_adapters": failed,
        "rules": rules, "decision": decision,
        "explanation": ("All required native planes are separately bound; the external "
                        "executor remains the only effect source."
                        if decision == "ALLOW" else
                        "The gate is refused because a required native plane is missing or refused."),
        **BOUNDARY,
    }
    return {**body, "explanation_root": root(body)}


class ConstitutionalIntegrationRuntime:
    """Coordinate integration gates while OperationGateway owns authority custody."""

    def __init__(self, workspace: str | Path, *, progress: Progress | None = None) -> None:
        self.workspace = Path(workspace)
        self.gateway = OperationGateway(self.workspace, progress=progress or Progress())

    def _preparation_path(self, operation_id: str) -> Path:
        return self.workspace / "integration" / f"{root({'operation_id': operation_id})}.json"

    def _store_preparation(self, value: dict[str, Any]) -> None:
        target = self._preparation_path(value["operation_id"])
        raw = canonical_bytes(value)
        if target.exists():
            require(target.read_bytes() == raw, "INTEGRATION_PREPARATION_CONFLICT")
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(f".json.{os.getpid()}.tmp")
        try:
            with temporary.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _load_preparation(self, operation_id: str) -> dict[str, Any]:
        target = self._preparation_path(operation_id)
        require(target.is_file(), "INTEGRATION_PREPARATION_MISSING")
        item = exact_keys(strict_loads(target.read_bytes()), {
            "schema", "operation_id", "contract_root", "application_capsule_root",
            "semantic_gravity", "integration_policy_root", "gateway_g1_root",
            "dispatch_authorization_root", "dispatch_nonce",
            "native_executor_selected_by_ucm", "status", "standing",
            "authority_effect", "real_a5", "g0", "preparation_root"})
        require(item["schema"] == PREPARATION_SCHEMA
                and item["native_executor_selected_by_ucm"] is False
                and item["status"] == "READY_FOR_EXTERNAL_EXECUTOR"
                and {key: item[key] for key in BOUNDARY} == BOUNDARY,
                "INTEGRATION_PREPARATION_INVALID")
        for name in ("contract_root", "application_capsule_root",
                     "integration_policy_root", "gateway_g1_root",
                     "dispatch_authorization_root", "dispatch_nonce"):
            require_root(item[name])
        require(type(item["semantic_gravity"]) is dict
                and item["semantic_gravity"].get("gate") == "G1_SENTINEL"
                and item["semantic_gravity"].get("decision") == "ALLOW",
                "INTEGRATION_PREPARATION_GRAVITY_INVALID")
        body = {key: deepcopy(value) for key, value in item.items()
                if key != "preparation_root"}
        require(item["preparation_root"] == root(body),
                "INTEGRATION_PREPARATION_ROOT_INVALID")
        return item

    def prepare(self, contract: dict[str, Any], *, application_capsule: dict[str, Any],
                adapter_results: list[dict[str, Any]],
                integration_policy: dict[str, Any],
                expected_integration_policy_root: str,
                expected_issuer_public_key_hex: str,
                expected_jurisdiction_root: str,
                expected_revocation_registry_root: str) -> dict[str, Any]:
        integration_policy = validate_integration_policy(integration_policy,
            expected_root=expected_integration_policy_root)
        capsule = validate_application_capsule(application_capsule)
        contract = validate_operation_contract(contract,
            expected_issuer_public_key_hex=expected_issuer_public_key_hex,
            expected_jurisdiction_root=expected_jurisdiction_root,
            expected_revocation_registry_root=expected_revocation_registry_root)
        adapter_roots = sorted(validate_adapter_result(row)["adapter_result_root"]
                               for row in adapter_results)
        require(contract["application_id"] == capsule["application_id"]
                and contract["request_root"] == capsule["capsule_root"],
                "INTEGRATION_CAPSULE_OPERATION_BINDING_INVALID")
        require(integration_policy["policy_pack_root"] in capsule["policy_pack_roots"]
                and adapter_roots == capsule["adapter_result_roots"],
                "INTEGRATION_CAPSULE_POLICY_BINDING_INVALID")
        gravity = build_semantic_gravity(gate="G1_SENTINEL", contract=contract,
            adapter_results=adapter_results,
            required_protocols=integration_policy["required_protocols"],
            integration_policy_root=integration_policy["policy_pack_root"],
            receipt_roots=[])
        require(gravity["decision"] == "ALLOW", "INTEGRATION_G1_REFUSED")
        prepared = self.gateway.prepare(contract,
            expected_issuer_public_key_hex=expected_issuer_public_key_hex,
            expected_jurisdiction_root=expected_jurisdiction_root,
            expected_revocation_registry_root=expected_revocation_registry_root)
        body = {"schema": PREPARATION_SCHEMA,
                "operation_id": contract["operation_id"],
                "contract_root": contract["contract_root"],
                "application_capsule_root": capsule["capsule_root"],
                "semantic_gravity": gravity,
                "integration_policy_root": integration_policy["policy_pack_root"],
                "gateway_g1_root": prepared["g1"]["receipt_root"],
                "dispatch_authorization_root":
                    prepared["dispatch_authorization"]["receipt_root"],
                "dispatch_nonce": prepared["dispatch_authorization"]["dispatch_nonce"],
                "native_executor_selected_by_ucm": False,
                "status": "READY_FOR_EXTERNAL_EXECUTOR", **BOUNDARY}
        result = {**body, "preparation_root": root(body)}
        self._store_preparation(result)
        return result

    def record_dispatch(self, operation_id: str, receipt: dict[str, Any]) -> dict[str, Any]:
        preparation = self._load_preparation(operation_id)
        require(preparation["status"] == "READY_FOR_EXTERNAL_EXECUTOR",
                "INTEGRATION_DISPATCH_NOT_PREPARED")
        return self.gateway.record_dispatch(operation_id, receipt)

    def record_terminal(self, operation_id: str, receipt: dict[str, Any], *,
                        adapter_results: list[dict[str, Any]],
                        integration_policy: dict[str, Any],
                        expected_integration_policy_root: str) -> dict[str, Any]:
        integration_policy = validate_integration_policy(integration_policy,
            expected_root=expected_integration_policy_root)
        preparation = self._load_preparation(operation_id)
        terminal_adapter_roots = sorted(
            validate_adapter_result(row)["adapter_result_root"]
            for row in adapter_results)
        require(preparation["integration_policy_root"] ==
                integration_policy["policy_pack_root"],
                "INTEGRATION_TERMINAL_POLICY_MISMATCH")
        require(terminal_adapter_roots ==
                sorted(preparation["semantic_gravity"]["adapter_result_roots"]),
                "INTEGRATION_TERMINAL_ADAPTER_BINDING_MISMATCH")
        terminal = self.gateway.record_terminal(operation_id, receipt)
        contract = self.gateway.contract(operation_id)
        state = terminal["state"]
        roots = sorted({state[name] for name in
                        ("g1_root", "dispatch_root", "terminal_receipt_root",
                         "g2_root", "g3_root") if state[name]})
        g2 = build_semantic_gravity(gate="G2_WITNESS", contract=contract,
            adapter_results=adapter_results,
            required_protocols=integration_policy["required_protocols"],
            integration_policy_root=integration_policy["policy_pack_root"],
            receipt_roots=roots)
        g3 = build_semantic_gravity(gate="G3_DIAGNOSTIC", contract=contract,
            adapter_results=adapter_results,
            required_protocols=integration_policy["required_protocols"],
            integration_policy_root=integration_policy["policy_pack_root"],
            receipt_roots=roots)
        require(g2["decision"] == "ALLOW" and g3["decision"] == "ALLOW",
                "INTEGRATION_TERMINAL_DIAGNOSTIC_REFUSED")
        body = {"schema": COMPLETION_SCHEMA, "operation_id": operation_id,
                "contract_root": contract["contract_root"],
                "application_capsule_root": preparation["application_capsule_root"],
                "preparation_root": preparation["preparation_root"],
                "state_root": state["state_root"],
                "integration_policy_root": integration_policy["policy_pack_root"],
                "g2_semantic_gravity": g2, "g3_semantic_gravity": g3,
                "terminal_state": state["state"], "status": "PASS", **BOUNDARY}
        return {**body, "completion_root": root(body)}

    def state(self, operation_id: str) -> dict[str, Any]:
        return self.gateway.state(operation_id)
"""Public-only charter ceremony, external pin verification and coherent resume."""
from __future__ import annotations

import copy
from typing import Any

from .canonical import exact_keys, require, require_root, root
from .custody import CustodyProvider, OpaqueEd25519KeyStore, public_key_root, verify_asymmetric
from .workbench_contracts import reject_raw_secrets, typed_root, validate_root_ref

CHARTER_DOMAIN = "UCL_UCM_WORKBENCH_CHARTER_V1"
GRANT_DOMAIN = "UCL_UCM_WORKBENCH_GRANT_V1"
POSSESSION_DOMAIN = "UCL_UCM_WORKBENCH_POSSESSION_V1"
PIN_FIELDS = {"charter_root", "grant_root", "issuer_key_root", "issuer_public_key_hex", "project_root", "source_root", "implementation_root", "registry_root", "policy_root", "namespace_root", "schema_root", "namespace_adapter_root", "thr_adapter_root"}
KINDS = {"project": "PROJECT", "source": "SOURCE", "implementation": "IMPLEMENTATION", "registry": "REGISTRY", "policy": "POLICY", "namespace": "NAMESPACE", "schema": "SCHEMA"}
BUDGETS = {"max_actions", "max_attempts", "max_artifact_bytes"}


def _integer(value: Any, code: str, *, minimum: int = 0) -> int:
    require(type(value) is int and minimum <= value <= 2**63 - 1, code)
    return value


def _names(value: Any, code: str) -> list[str]:
    require(type(value) is list and bool(value) and all(type(v) is str and bool(v) and v.isascii() and v.strip() == v for v in value), code)
    require(len(value) == len(set(value)), code)
    return value


def _budgets(value: Any) -> dict[str, int]:
    item = exact_keys(value, BUDGETS)
    for field in BUDGETS:
        _integer(item[field], "WORKBENCH_BUDGET_INVALID", minimum=1)
    return item


def _signed(record: Any, domain: str, *, expected_key_root: str, public_key_hex: str) -> dict[str, Any]:
    item = exact_keys(record, {"body", "body_root", "signature", "key_root", "signature_algorithm"})
    require(type(item["body"]) is dict and type(item["signature"]) is str and len(item["signature"]) == 88, "WORKBENCH_SIGNED_RECORD_INVALID")
    return verify_asymmetric(item, domain, expected_key_root=expected_key_root, public_key_hex=public_key_hex)


def _adapter(value: Any, kind: str, expected_root: str) -> bool:
    item = exact_keys(value, {"schema", "kind", "status", "namespace_root", "source_contract_root", "authority_root", "semantic_mapping"})
    require(item["schema"] == "ucl.ucm.workbench.imported_adapter.v1" and item["kind"] == kind and root(item) == expected_root, "WORKBENCH_ADAPTER_PIN_MISMATCH")
    require(type(item["status"]) is str and item["status"] in {"UNBOUND", "BOUND"}, "WORKBENCH_ADAPTER_STATUS_INVALID")
    require_root(item["namespace_root"])
    if item["status"] == "BOUND":
        require_root(item["source_contract_root"])
        require_root(item["authority_root"])
    else:
        require(item["source_contract_root"] is None and item["authority_root"] is None, "WORKBENCH_UNBOUND_ADAPTER_INVALID")
    mapping = item["semantic_mapping"]
    if kind == "THR_UGK":
        require(mapping == {"H_s": "state", "H_c": "admissibility", "H_m": "meaning", "H_j": "locality", "H_r": "receipt_identity", "h_body": "whole_body_integrity"}, "WORKBENCH_THR_MAPPING_INVALID")
    else:
        require(type(mapping) is dict and mapping == {"jurisdiction": "imported_contract_only", "portability": "origin_and_receiving_authority_separate"}, "WORKBENCH_JURISDICTION_MAPPING_INVALID")
    return item["status"] == "BOUND"


def _verify_material(material: Any, *, external_pins: dict[str, Any], now: int, expected_head: str, requested_capabilities: list[str], requested_jurisdiction: str, consequential: bool) -> dict[str, Any]:
    reject_raw_secrets(material)
    pins = exact_keys(external_pins, PIN_FIELDS)
    for name in PIN_FIELDS - {"issuer_public_key_hex"}:
        require_root(pins[name])
    require(public_key_root(pins["issuer_public_key_hex"]) == pins["issuer_key_root"], "WORKBENCH_ISSUER_PIN_INVALID")
    _integer(now, "WORKBENCH_TIME_INVALID")
    require(type(consequential) is bool, "WORKBENCH_CONSEQUENTIAL_FLAG_INVALID")
    value = exact_keys(material, {"charter", "grant", "possession", "capsule"})
    require(root(value["charter"]) == pins["charter_root"] and root(value["grant"]) == pins["grant_root"], "WORKBENCH_AUTHORIZATION_PIN_MISMATCH")
    charter = _signed(value["charter"], CHARTER_DOMAIN, expected_key_root=pins["issuer_key_root"], public_key_hex=pins["issuer_public_key_hex"])
    exact_keys(charter, {"schema", "bindings", "roles", "capabilities", "jurisdictions", "budgets", "issued_at", "expires_at", "namespace_adapter", "thr_adapter", "authority_ceiling", "effect_ceiling", "effect_scope", "standing"})
    require(charter["schema"] == "ucl.ucm.workbench.charter.v1", "WORKBENCH_CHARTER_SCHEMA_INVALID")
    require(charter["authority_ceiling"] == "NONE" and charter["effect_ceiling"] == "NONE" and charter["standing"] == "INFORMATION_ONLY", "WORKBENCH_AUTHORITY_CEILING_EXCEEDED")
    require(charter["effect_scope"] == "LOCAL_WORKSPACE", "WORKBENCH_EFFECT_SCOPE_INVALID")
    bindings = exact_keys(charter["bindings"], set(KINDS))
    for field, kind in KINDS.items():
        ref = validate_root_ref(bindings[field], kind)
        require(ref["digest"] == pins[field + "_root"], "WORKBENCH_BINDING_PIN_MISMATCH", detail=field)
    namespace_bound = _adapter(charter["namespace_adapter"], "DKN_JURISDICTION", pins["namespace_adapter_root"])
    thr_bound = _adapter(charter["thr_adapter"], "THR_UGK", pins["thr_adapter_root"])
    require(charter["namespace_adapter"]["namespace_root"] == pins["namespace_root"] == charter["thr_adapter"]["namespace_root"], "WORKBENCH_ADAPTER_NAMESPACE_MISMATCH")
    require(type(charter["roles"]) is dict and bool(charter["roles"]), "WORKBENCH_ROLE_MAP_INVALID")
    role_roots: list[str] = []
    for role, identity in charter["roles"].items():
        require(type(role) is str and role and role.isascii(), "WORKBENCH_ROLE_INVALID")
        exact_keys(identity, {"key_root", "public_key_hex"})
        require(public_key_root(identity["public_key_hex"]) == identity["key_root"] != pins["issuer_key_root"], "WORKBENCH_ROLE_IDENTITY_INVALID")
        role_roots.append(identity["key_root"])
    require(len(role_roots) == len(set(role_roots)), "WORKBENCH_ROLE_INDEPENDENCE_REQUIRED")
    _names(charter["capabilities"], "WORKBENCH_CAPABILITIES_INVALID")
    _names(charter["jurisdictions"], "WORKBENCH_JURISDICTIONS_INVALID")
    _budgets(charter["budgets"])
    issued = _integer(charter["issued_at"], "WORKBENCH_TIME_INVALID")
    expiry = _integer(charter["expires_at"], "WORKBENCH_TIME_INVALID")
    require(issued <= now < expiry and expiry - issued <= 86400 * 31, "WORKBENCH_CHARTER_EXPIRED_OR_NOT_CURRENT")
    grant = _signed(value["grant"], GRANT_DOMAIN, expected_key_root=pins["issuer_key_root"], public_key_hex=pins["issuer_public_key_hex"])
    exact_keys(grant, {"schema", "charter_root", "role", "principal_key_root", "tenant_id", "capabilities", "jurisdictions", "budgets", "issued_at", "expires_at", "max_sessions", "authority_effect", "standing"})
    require(grant["schema"] == "ucl.ucm.workbench.grant.v1" and grant["charter_root"] == pins["charter_root"], "WORKBENCH_GRANT_CHARTER_MISMATCH")
    require(grant["authority_effect"] == "NONE" and grant["standing"] == "INFORMATION_ONLY", "WORKBENCH_AUTHORITY_CEILING_EXCEEDED")
    require(type(grant["role"]) is str and grant["role"] in charter["roles"], "WORKBENCH_GRANT_ROLE_UNKNOWN")
    principal = charter["roles"][grant["role"]]
    require(principal["key_root"] == grant["principal_key_root"], "WORKBENCH_GRANT_ROLE_KEY_MISMATCH")
    require(type(grant["tenant_id"]) is str and bool(grant["tenant_id"]) and grant["tenant_id"].isascii() and grant["tenant_id"].strip() == grant["tenant_id"], "WORKBENCH_TENANT_ID_INVALID")
    _names(grant["capabilities"], "WORKBENCH_CAPABILITIES_INVALID")
    _names(grant["jurisdictions"], "WORKBENCH_JURISDICTIONS_INVALID")
    require(set(grant["capabilities"]) <= set(charter["capabilities"]) and set(grant["jurisdictions"]) <= set(charter["jurisdictions"]), "WORKBENCH_GRANT_SCOPE_EXCEEDED")
    _budgets(grant["budgets"])
    require(all(grant["budgets"][k] <= charter["budgets"][k] for k in BUDGETS), "WORKBENCH_GRANT_BUDGET_EXCEEDED")
    grant_start = _integer(grant["issued_at"], "WORKBENCH_TIME_INVALID")
    grant_expiry = _integer(grant["expires_at"], "WORKBENCH_TIME_INVALID")
    require(issued <= grant_start <= now < grant_expiry <= expiry, "WORKBENCH_GRANT_EXPIRED_OR_NOT_CURRENT")
    _integer(grant["max_sessions"], "WORKBENCH_SESSION_BUDGET_INVALID", minimum=1)
    _names(requested_capabilities, "WORKBENCH_REQUESTED_CAPABILITIES_INVALID")
    require(set(requested_capabilities) <= set(grant["capabilities"]), "WORKBENCH_CAPABILITY_NOT_GRANTED")
    require(type(requested_jurisdiction) is str and requested_jurisdiction in grant["jurisdictions"], "WORKBENCH_JURISDICTION_SCOPE_ESCAPE")
    require(not consequential, "WORKBENCH_CONSEQUENTIAL_AUTHORITY_NOT_GRANTED")
    possession = _signed(value["possession"], POSSESSION_DOMAIN, expected_key_root=principal["key_root"], public_key_hex=principal["public_key_hex"])
    exact_keys(possession, {"schema", "charter_root", "grant_root", "nonce", "session_id", "current_head", "issued_at", "expires_at", "capabilities", "jurisdiction"})
    require(possession["schema"] == "ucl.ucm.workbench.possession.v1" and possession["charter_root"] == pins["charter_root"] and possession["grant_root"] == pins["grant_root"], "WORKBENCH_POSSESSION_BINDING_MISMATCH")
    session_id = root({"schema": "ucl.ucm.workbench.session_identity.v1", "principal_key_root": principal["key_root"], "nonce": require_root(possession["nonce"]), "charter_root": pins["charter_root"], "grant_root": pins["grant_root"]})
    require(possession["session_id"] == session_id, "WORKBENCH_SESSION_ID_INVALID")
    require(possession["capabilities"] == sorted(requested_capabilities) and possession["jurisdiction"] == requested_jurisdiction, "WORKBENCH_POSSESSION_SCOPE_MISMATCH")
    session_start = _integer(possession["issued_at"], "WORKBENCH_TIME_INVALID")
    session_expiry = _integer(possession["expires_at"], "WORKBENCH_TIME_INVALID")
    require(grant_start <= session_start <= now < session_expiry <= grant_expiry and session_expiry - session_start <= 3600, "WORKBENCH_SESSION_EXPIRED_OR_NOT_CURRENT")
    capsule = exact_keys(value["capsule"], {"schema", "project_root", "head", "sequence", "consumed_sessions", "root"})
    require(capsule["schema"] == "ucl.ucm.workbench.resume_capsule.v1" and capsule["project_root"] == pins["project_root"], "WORKBENCH_CAPSULE_PROJECT_MISMATCH")
    _integer(capsule["sequence"], "WORKBENCH_CAPSULE_SEQUENCE_INVALID")
    require(capsule["head"] == possession["current_head"] == require_root(expected_head), "WORKBENCH_CAPSULE_STALE")
    require(capsule["root"] == root({k: v for k, v in capsule.items() if k != "root"}), "WORKBENCH_CAPSULE_ROOT_INVALID")
    sessions = capsule["consumed_sessions"]
    require(type(sessions) is list and all(type(x) is str for x in sessions) and len(sessions) == len(set(sessions)), "WORKBENCH_CAPSULE_SESSIONS_INVALID")
    for session in sessions:
        require_root(session)
    # The external head must be the content head of the capsule's complete state.
    require(capsule["head"] == root({"project_root": capsule["project_root"], "sequence": capsule["sequence"], "consumed_sessions": sessions}), "WORKBENCH_CAPSULE_HEAD_BINDING_MISMATCH")
    require(session_id not in sessions, "WORKBENCH_SESSION_REPLAY")
    require(len(sessions) < grant["max_sessions"], "WORKBENCH_SESSION_BUDGET_EXHAUSTED")
    jurisdiction_root = root({"namespace_root": pins["namespace_root"], "jurisdiction": requested_jurisdiction, "tenant_id": grant["tenant_id"]})
    return {"schema": "ucl.ucm.workbench.orientation.v1", **{k + "_root": pins[k + "_root"] for k in KINDS}, "charter_root": pins["charter_root"], "grant_root": pins["grant_root"], "jurisdiction": requested_jurisdiction, "jurisdiction_root": jurisdiction_root, "tenant_id": grant["tenant_id"], "role": grant["role"], "principal_key_root": principal["key_root"], "session_id": session_id, "capabilities": sorted(requested_capabilities), "budgets": copy.deepcopy(grant["budgets"]), "expires_at": session_expiry, "current_head": capsule["head"], "readiness": "READY_INFORMATION_ONLY", "effect_scope": "LOCAL_WORKSPACE", "standing": "INFORMATION_ONLY", "authority_effect": "NONE", "namespace_authority_bound": namespace_bound, "thr_authority_bound": thr_bound, "material": copy.deepcopy(value)}


def verify_orientation(context: Any, *, external_pins: dict[str, Any], now: int, expected_head: str) -> dict[str, Any]:
    require(type(context) is dict and "material" in context and "capabilities" in context and "jurisdiction" in context, "WORKBENCH_ORIENTATION_INVALID")
    rebuilt = _verify_material(context["material"], external_pins=external_pins, now=now, expected_head=expected_head, requested_capabilities=context["capabilities"], requested_jurisdiction=context["jurisdiction"], consequential=False)
    rebuilt["root"] = root(rebuilt)
    require(context == rebuilt, "WORKBENCH_ORIENTATION_CONTEXT_FORGED")
    return copy.deepcopy(rebuilt)


class OrientationRegistry:
    """Local ceremony constructor; durable consumption requires committing capsule externally."""
    def __init__(self, *, external_pins: dict[str, Any], current_head: str) -> None:
        self.external_pins = copy.deepcopy(external_pins)
        self.current_head = require_root(current_head)
        self.consumed: set[str] = set()

    def orient(self, *, charter: Any, grant: Any, possession: Any, capsule: Any, now: int, requested_capabilities: list[str], requested_jurisdiction: str, consequential: bool = False) -> dict[str, Any]:
        body = _verify_material({"charter": charter, "grant": grant, "possession": possession, "capsule": capsule}, external_pins=self.external_pins, now=now, expected_head=self.current_head, requested_capabilities=requested_capabilities, requested_jurisdiction=requested_jurisdiction, consequential=consequential)
        require(body["session_id"] not in self.consumed, "WORKBENCH_SESSION_REPLAY")
        self.consumed.add(body["session_id"])
        return {**body, "root": root(body)}

    def capsule_after(self, context: Any) -> dict[str, Any]:
        checked = verify_orientation(context, external_pins=self.external_pins, now=context["material"]["possession"]["body"]["issued_at"], expected_head=self.current_head)
        old = checked["material"]["capsule"]
        sessions = sorted(set(old["consumed_sessions"]) | self.consumed)
        sequence = old["sequence"] + 1
        head = root({"project_root": checked["project_root"], "sequence": sequence, "consumed_sessions": sessions})
        body = {"schema": "ucl.ucm.workbench.resume_capsule.v1", "project_root": checked["project_root"], "head": head, "sequence": sequence, "consumed_sessions": sessions}
        return {**body, "root": root(body)}


def sign_public_record(provider: CustodyProvider, handle: str, domain: str, body: dict[str, Any]) -> dict[str, Any]:
    """External signer interface; no private material accepted in agent requests."""
    reject_raw_secrets(body)
    return provider.sign(handle, domain, copy.deepcopy(body))


def build_fixture_orientation(*, nonce_label: str = "session-1", now: int = 1000, roots: dict[str, str] | None = None, budgets: dict[str, int] | None = None, tenant_id: str = "fixture-tenant", jurisdiction: str = "fixture/project") -> dict[str, Any]:
    """Published deterministic test identities. This fixture seats no real identity."""
    store = OpaqueEd25519KeyStore()
    issuer = store.install_fixture_seed("GOVERNOR", bytes.fromhex("31" * 32))
    agent = store.install_fixture_seed("NODE", bytes.fromhex("32" * 32))
    issuer_identity, principal = store.identity(issuer), store.identity(agent)
    _integer(now, "WORKBENCH_TIME_INVALID")
    overrides = {} if roots is None else roots
    require(type(overrides) is dict and set(overrides) <= set(KINDS), "WORKBENCH_FIXTURE_ROOT_OVERRIDE_INVALID")
    bindings = {k: typed_root(v, overrides.get(k, root({"fixture_only": True, "field": k}))) for k, v in KINDS.items()}
    namespace = bindings["namespace"]["digest"]
    adapter_base = {"schema": "ucl.ucm.workbench.imported_adapter.v1", "status": "UNBOUND", "namespace_root": namespace, "source_contract_root": None, "authority_root": None}
    namespace_adapter = {**adapter_base, "kind": "DKN_JURISDICTION", "semantic_mapping": {"jurisdiction": "imported_contract_only", "portability": "origin_and_receiving_authority_separate"}}
    thr_adapter = {**adapter_base, "kind": "THR_UGK", "semantic_mapping": {"H_s": "state", "H_c": "admissibility", "H_m": "meaning", "H_j": "locality", "H_r": "receipt_identity", "h_body": "whole_body_integrity"}}
    budgets = copy.deepcopy(budgets or {"max_actions": 8, "max_attempts": 3, "max_artifact_bytes": 65536})
    _budgets(budgets)
    issued, expires = max(0, now - 100), now + 3000
    capabilities = ["INSPECT_ARTIFACTS", "PREPARE_CANDIDATE", "RUN_TESTS"]
    charter_body = {"schema": "ucl.ucm.workbench.charter.v1", "bindings": bindings, "roles": {"BUILDER": {"key_root": principal["key_root"], "public_key_hex": principal["public_key_hex"]}}, "capabilities": capabilities, "jurisdictions": [jurisdiction], "budgets": budgets, "issued_at": issued, "expires_at": expires, "namespace_adapter": namespace_adapter, "thr_adapter": thr_adapter, "authority_ceiling": "NONE", "effect_ceiling": "NONE", "effect_scope": "LOCAL_WORKSPACE", "standing": "INFORMATION_ONLY"}
    charter = sign_public_record(store, issuer, CHARTER_DOMAIN, charter_body)
    grant_body = {"schema": "ucl.ucm.workbench.grant.v1", "charter_root": root(charter), "role": "BUILDER", "principal_key_root": principal["key_root"], "tenant_id": tenant_id, "capabilities": capabilities, "jurisdictions": [jurisdiction], "budgets": budgets, "issued_at": issued, "expires_at": expires, "max_sessions": 8, "authority_effect": "NONE", "standing": "INFORMATION_ONLY"}
    grant = sign_public_record(store, issuer, GRANT_DOMAIN, grant_body)
    project = bindings["project"]["digest"]
    head = root({"project_root": project, "sequence": 0, "consumed_sessions": []})
    capsule_body = {"schema": "ucl.ucm.workbench.resume_capsule.v1", "project_root": project, "head": head, "sequence": 0, "consumed_sessions": []}
    capsule = {**capsule_body, "root": root(capsule_body)}
    nonce = root({"fixture_nonce": nonce_label})
    session_id = root({"schema": "ucl.ucm.workbench.session_identity.v1", "principal_key_root": principal["key_root"], "nonce": nonce, "charter_root": root(charter), "grant_root": root(grant)})
    possession_body = {"schema": "ucl.ucm.workbench.possession.v1", "charter_root": root(charter), "grant_root": root(grant), "nonce": nonce, "session_id": session_id, "current_head": head, "issued_at": now, "expires_at": now + 600, "capabilities": capabilities, "jurisdiction": jurisdiction}
    possession = store.sign(agent, POSSESSION_DOMAIN, possession_body)
    pins = {"charter_root": root(charter), "grant_root": root(grant), "issuer_key_root": issuer_identity["key_root"], "issuer_public_key_hex": issuer_identity["public_key_hex"], **{k + "_root": v["digest"] for k, v in bindings.items()}, "namespace_adapter_root": root(namespace_adapter), "thr_adapter_root": root(thr_adapter)}
    registry = OrientationRegistry(external_pins=pins, current_head=head)
    context = registry.orient(charter=charter, grant=grant, possession=possession, capsule=capsule, now=now, requested_capabilities=capabilities, requested_jurisdiction=jurisdiction)
    return {"context": context, "external_pins": pins, "current_head": head, "now": now, "provider": store, "issuer_handle": issuer, "agent_handle": agent, "registry": registry}

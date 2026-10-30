from __future__ import annotations

from copy import deepcopy
import base64
import binascii
import re
from typing import Any

from .canonical import Refusal, exact_keys, require, require_root, root
from .ecosystem import verify_application_manifest, verify_capability_registry, verify_policy_bundle
from .effect_mediator import EffectMediator, make_capability_request, prepare_effect_proposal
from .foundation_runtime import FoundationRuntime
from .court_planner import build_content_graph, plan_courts


SURFACES = (
    "ORIENT_FOUNDATION", "DISCOVER_CAPABILITIES", "VALIDATE_APPLICATION", "VALIDATE_POLICY",
    "EVALUATE_CAPABILITY_REQUEST", "PREPARE_EFFECT_PROPOSAL", "PREFLIGHT_DEPLOYMENT",
    "REHEARSE_DEPLOYMENT", "APPEND_OBSERVATION", "QUERY_OPERATIONS", "PREPARE_INCIDENT",
    "PREPARE_MIGRATION", "PREPARE_BACKUP", "PLAN_REQUALIFICATION", "PREPARE_REVIEW_HANDOFF", "SELECT_COURT_LANE",
)
_SECRET_FRAGMENTS = {
    "privatekey", "secret", "password", "passwd", "passphrase", "bearer", "token",
    "credential", "seed", "mnemonic", "signingkey", "apikey", "clientsecret", "jwt", "pem", "authorization",
}
_HEX_SECRET = re.compile(r"^(?:0[xX])?[0-9a-fA-F]{64,128}$")
_SPLIT_HEX_SECRET = re.compile(r"^(?:[0-9a-fA-F]{2}[-:_ ]){31,63}[0-9a-fA-F]{2}$")
_BASE64_MATERIAL = re.compile(r"^[A-Za-z0-9+/_-]{42,}={0,2}$")
_BASE32_MATERIAL = re.compile(r"^[A-Z2-7]{52,}={0,7}$", re.IGNORECASE)
_ESCAPED_BYTES = re.compile(r"^(?:\\x[0-9a-fA-F]{2}){32,64}$")


def _normalized_key(value: str) -> str:
    return "".join(ch for ch in value.casefold() if ch.isalnum())


def _secret_material_length(value: str) -> int:
    """Return a known secret-sized decoded length, or zero.

    This deliberately recognizes encodings rather than guessing entropy. Public
    hashes remain allowed only through typed root/hash fields in the caller's
    schema; unstructured strings and fragments are never treated as roots.
    """
    compact = "".join(value.split())
    if _ESCAPED_BYTES.fullmatch(compact):
        return len(compact) // 4
    if "%" in compact:
        try:
            decoded_percent = bytes(int(item, 16) for item in compact.split("%")[1:] if len(item) == 2)
            if not compact.startswith("%") or compact.count("%") != len(decoded_percent):
                decoded_percent = b""
        except (ValueError, TypeError):
            decoded_percent = b""
        if len(decoded_percent) in {32, 48, 64}:
            return len(decoded_percent)
    normalized_hex = compact
    if normalized_hex.startswith(("0x", "0X")):
        normalized_hex = normalized_hex[2:]
    normalized_hex = re.sub(r"[-:_,.]", "", normalized_hex)
    if len(normalized_hex) in {64, 96, 128} and re.fullmatch(r"[0-9a-fA-F]+", normalized_hex):
        return len(normalized_hex) // 2
    candidates = [compact]
    for _ in range(2):
        next_candidates: list[str] = []
        for candidate in candidates:
            if _BASE64_MATERIAL.fullmatch(candidate):
                try:
                    normalized = candidate.replace("-", "+").replace("_", "/")
                    normalized += "=" * ((4 - len(normalized) % 4) % 4)
                    decoded = base64.b64decode(normalized, validate=True)
                except (binascii.Error, ValueError):
                    decoded = b""
                if len(decoded) in {32, 48, 64}:
                    return len(decoded)
                try:
                    next_candidates.append(decoded.decode("ascii"))
                except UnicodeDecodeError:
                    pass
            if _BASE32_MATERIAL.fullmatch(candidate):
                try:
                    normalized32 = candidate.upper() + "=" * ((8 - len(candidate) % 8) % 8)
                    decoded32 = base64.b32decode(normalized32, casefold=True)
                except (binascii.Error, ValueError):
                    decoded32 = b""
                if len(decoded32) in {32, 48, 64}:
                    return len(decoded32)
        candidates = next_candidates
    for decoder in (base64.b85decode, base64.a85decode):
        try:
            decoded85 = decoder(compact.encode("ascii"))
        except (ValueError, TypeError, binascii.Error, UnicodeEncodeError):
            decoded85 = b""
        if len(decoded85) in {32, 48, 64}:
            return len(decoded85)
    return 0


def _public_material_key(key: str) -> bool:
    return key.endswith(("root", "roots", "hash", "hashes")) or key in {"sha256", "publickeyhex", "signature"}


def _untyped_string_fragments(value: Any, parent_key: str = "") -> list[str]:
    if type(value) is dict:
        fragments: list[str] = []
        for key, child in value.items():
            if type(key) is str and not _public_material_key(_normalized_key(key)):
                fragments.extend(_untyped_string_fragments(child, _normalized_key(key)))
        return fragments
    if type(value) is list:
        return [fragment for child in value for fragment in _untyped_string_fragments(child, parent_key)]
    if type(value) is str and not _public_material_key(parent_key):
        return [value]
    return []


def _scan_no_secrets(value: Any, path: str = "$") -> None:
    pending = [(value, path, "", False, False)]
    while pending:
        current, current_path, parent_key, root_collection, unstructured = pending.pop()
        if type(current) is dict:
            fragments = _untyped_string_fragments(current)
            if len(fragments) > 1:
                combined = "".join(fragments)
                normalized = re.sub(r"[-:_,.\s]", "", combined)
                require(not (len(normalized) in {64, 96, 128} and re.fullmatch(r"[0-9a-fA-F]+", normalized)), "AGENT_SECRET_VALUE_FORBIDDEN", current_path)
            collection = root_collection or parent_key.endswith(("roots", "hashes"))
            for key, child in current.items():
                require(type(key) is str, "AGENT_SECRET_SHAPE_FORBIDDEN", current_path)
                normalized = _normalized_key(key)
                require(not any(fragment in normalized for fragment in _SECRET_FRAGMENTS), "AGENT_SECRET_SHAPE_FORBIDDEN", f"{current_path}.{key}")
                pending.append((child, f"{current_path}.{key}", normalized, collection, unstructured or normalized in {"details", "metadata", "opaque"}))
        elif type(current) is list:
            collection = root_collection or parent_key.endswith(("roots", "hashes"))
            fragments = _untyped_string_fragments(current, parent_key)
            if not collection and fragments:
                require(_secret_material_length("".join(fragments)) == 0, "AGENT_SECRET_VALUE_FORBIDDEN", current_path)
            if not collection and 32 <= len(current) <= 64 and all(type(child) is int and type(child) is not bool and 0 <= child <= 255 for child in current):
                require(False, "AGENT_SECRET_VALUE_FORBIDDEN", current_path)
            pending.extend((child, f"{current_path}[{index}]", parent_key, collection, unstructured) for index, child in enumerate(current))
        elif type(current) is str:
            folded = current.casefold()
            require(not ("-----begin " in folded and "private key-----" in folded), "AGENT_SECRET_VALUE_FORBIDDEN", current_path)
            if _SPLIT_HEX_SECRET.fullmatch(current):
                require(False, "AGENT_SECRET_VALUE_FORBIDDEN", current_path)
            if _HEX_SECRET.fullmatch(current):
                permitted = not unstructured and (root_collection or parent_key.endswith(("root", "roots", "hash", "hashes")) or parent_key in {"sha256", "publickeyhex"})
                require(permitted, "AGENT_SECRET_VALUE_FORBIDDEN", current_path)
            elif parent_key not in {"publickeyhex", "signature"}:
                require(_secret_material_length(current) == 0, "AGENT_SECRET_VALUE_FORBIDDEN", current_path)


class FoundationAgent:
    """Strict no-effect SDK facade for application and review agents."""

    def __init__(self, *, subject_root: str, registry: dict[str, Any], policy: dict[str, Any], runtime: FoundationRuntime, expected_registry_root: str, expected_policy_root: str, workspace_root: str | None = None) -> None:
        self.subject_root = require_root(subject_root)
        verify_capability_registry(registry, expected_subject_root=self.subject_root)
        verify_policy_bundle(policy, registry=registry, expected_subject_root=self.subject_root)
        require(runtime.subject_root == self.subject_root and runtime.policy_root == policy["policy_root"], "FOUNDATION_RUNTIME_CONTEXT_MISMATCH")
        self.registry = deepcopy(registry)
        self.policy = deepcopy(policy)
        self.runtime = runtime
        self.workspace_root = workspace_root
        self.mediator = EffectMediator(subject_root=self.subject_root, registry=self.registry, policy=self.policy, expected_registry_root=expected_registry_root, expected_policy_root=expected_policy_root)
        self._outcomes: dict[str, tuple[str, dict[str, Any]]] = {}

    def dispatch(self, value: Any) -> dict[str, Any]:
        request = exact_keys(value, {"schema", "surface", "idempotency_key", "effect_ceiling", "payload"}, "$.request")
        require(request["schema"] == "ucl.ucm.foundation_agent_request.v1", "FOUNDATION_AGENT_SCHEMA_INVALID")
        require(request["surface"] in SURFACES, "FOUNDATION_AGENT_SURFACE_UNKNOWN")
        require(type(request["idempotency_key"]) is str and 8 <= len(request["idempotency_key"]) <= 128, "IDEMPOTENCY_KEY_INVALID")
        require(request["effect_ceiling"] == "NONE" and type(request["payload"]) is dict, "FOUNDATION_AGENT_BOUNDARY_INVALID")
        request_root = root(request)
        prior = self._outcomes.get(request["idempotency_key"])
        try:
            _scan_no_secrets(request["payload"], "$.request.payload")
            if prior is not None:
                require(prior[0] == request_root, "IDEMPOTENCY_CONFLICT")
                return deepcopy(prior[1])
            output = self._execute(request["surface"], request["payload"], request["idempotency_key"])
            outcome, diagnostic = "COMPLETED", "PASS"
        except Refusal as error:
            output = {"path": error.path, "detail": error.detail}
            outcome, diagnostic = "REFUSED", error.code
        except (KeyError, TypeError, IndexError) as error:
            output = {"path": "$.request.payload", "detail": type(error).__name__}
            outcome, diagnostic = "REFUSED", "FOUNDATION_AGENT_PAYLOAD_INVALID"
        body = {
            "schema": "ucl.ucm.foundation_agent_result.v1", "surface": request["surface"],
            "request_root": request_root, "outcome": outcome, "diagnostic": diagnostic,
            "output": output, "effect_observed": "NONE", "maximum_stage": "D2_INDEPENDENT_REVIEW",
            "standing": "INFORMATION_ONLY", "real_a5": False, "g0": "CLOSED", "authority_effect": "NONE",
        }
        result = {**body, "result_root": root(body)}
        if prior is None:
            self._outcomes[request["idempotency_key"]] = (request_root, deepcopy(result))
        return result

    def _execute(self, surface: str, payload: dict[str, Any], request_key: str) -> dict[str, Any]:
        if surface == "ORIENT_FOUNDATION":
            exact_keys(payload, set(), "$.payload")
            return {
                "system": "UCL-UCM Operational Ecosystem Foundation", "surface_count": len(SURFACES),
                "subject_root": self.subject_root, "policy_root": self.policy["policy_root"],
                "maximum_stage": "D2_INDEPENDENT_REVIEW", "executable_effect_classes": ["NONE"],
                "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            }
        if surface == "DISCOVER_CAPABILITIES":
            exact_keys(payload, set(), "$.payload")
            return {"registry": deepcopy(self.registry), "policy_root": self.policy["policy_root"], "surfaces": list(SURFACES)}
        if surface == "VALIDATE_APPLICATION":
            exact_keys(payload, {"application"}, "$.payload")
            verify_application_manifest(payload["application"])
            expected = {item["application_id"]: item["manifest_root"] for item in self.policy["applications"]}
            require(expected.get(payload["application"]["application_id"]) == payload["application"]["manifest_root"], "APPLICATION_NOT_IN_POLICY")
            return {"application_root": payload["application"]["manifest_root"], "status": "PASS"}
        if surface == "VALIDATE_POLICY":
            exact_keys(payload, {"policy"}, "$.payload")
            verify_policy_bundle(payload["policy"], registry=self.registry, expected_subject_root=self.subject_root)
            require(payload["policy"]["policy_root"] == self.policy["policy_root"], "POLICY_NOT_CURRENT")
            return {"policy_root": self.policy["policy_root"], "status": "PASS"}
        if surface in {"EVALUATE_CAPABILITY_REQUEST", "PREPARE_EFFECT_PROPOSAL"}:
            exact_keys(payload, {"application_id", "capability_id", "input"}, "$.payload")
            capability_request = make_capability_request(
                application_id=payload["application_id"], capability_id=payload["capability_id"],
                policy=self.policy, registry=self.registry, input_value=payload["input"],
                idempotency_key="capability:" + request_key,
            )
            evaluation = self.mediator.evaluate(capability_request, input_value=payload["input"])
            if surface == "PREPARE_EFFECT_PROPOSAL":
                return prepare_effect_proposal(evaluation)
            return {"request": capability_request, "evaluation": evaluation}
        if surface == "PREFLIGHT_DEPLOYMENT":
            exact_keys(payload, {"deployment_id", "application_root", "artifact_root", "target_profile_root", "rollback_root", "requested_stage", "checks"}, "$.payload")
            plan = self.runtime.plan_deployment(
                deployment_id=payload["deployment_id"], application_root=payload["application_root"], artifact_root=payload["artifact_root"],
                target_profile_root=payload["target_profile_root"], rollback_root=payload["rollback_root"], requested_stage=payload["requested_stage"],
                idempotency_key="deployment:" + request_key,
            )
            return {"plan": plan, "preflight": self.runtime.preflight_deployment(deployment_id=payload["deployment_id"], checks=payload["checks"])}
        if surface == "REHEARSE_DEPLOYMENT":
            exact_keys(payload, {"deployment_id", "rehearsal_root", "rollback_rehearsal_root"}, "$.payload")
            state = self.runtime.rehearse_deployment(deployment_id=payload["deployment_id"], rehearsal_root=payload["rehearsal_root"], rollback_rehearsal_root=payload["rollback_rehearsal_root"])
            return {"state": state, "readiness": self.runtime.readiness(payload["deployment_id"])}
        if surface == "APPEND_OBSERVATION":
            exact_keys(payload, {"kind", "subject_root", "evidence_roots", "status", "details"}, "$.payload")
            return self.runtime.append_observation(**payload)
        if surface == "QUERY_OPERATIONS":
            exact_keys(payload, set(), "$.payload")
            capsule = self.runtime.export_capsule()
            return {"capsule_root": capsule["capsule_root"], "sequence": capsule["sequence"], "observation_count": len(capsule["observations"]), "incident_count": len(capsule["incidents"]), "deployment_count": len(capsule["deployments"])}
        if surface == "SELECT_COURT_LANE":
            exact_keys(payload, {"changed_paths", "circumstance", "baseline_graph_root", "requested_lane"}, "$.payload")
            require(type(self.workspace_root) is str and self.workspace_root, "COURT_WORKSPACE_NOT_CONFIGURED")
            import pathlib
            graph = build_content_graph(pathlib.Path(self.workspace_root))
            return plan_courts(changed_paths=payload["changed_paths"], circumstance=payload["circumstance"], baseline_graph_root=payload["baseline_graph_root"], current_graph=graph, requested_lane=payload["requested_lane"])
        if surface == "PREPARE_INCIDENT":
            exact_keys(payload, {"incident_id", "severity", "subject_root", "evidence_roots", "summary"}, "$.payload")
            return self.runtime.open_incident(**payload)
        if surface in {"PREPARE_MIGRATION", "PREPARE_BACKUP", "PLAN_REQUALIFICATION", "PREPARE_REVIEW_HANDOFF"}:
            exact_keys(payload, {"subject_root", "target_root", "evidence_roots"}, "$.payload")
            require_root(payload["subject_root"]); require_root(payload["target_root"])
            require(type(payload["evidence_roots"]) is list and payload["evidence_roots"] == sorted(payload["evidence_roots"]), "FOUNDATION_EVIDENCE_SET_INVALID")
            for value in payload["evidence_roots"]:
                require_root(value)
            body = {
                "schema": "ucl.ucm.foundation_planning_record.v1", "operation": surface,
                "subject_root": payload["subject_root"], "target_root": payload["target_root"],
                "evidence_roots": payload["evidence_roots"], "status": "UNBOUND_PROPOSAL",
                "executable": False, "effect_observed": "NONE", "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            }
            return {**body, "planning_root": root(body)}
        raise Refusal("FOUNDATION_AGENT_SURFACE_UNKNOWN")


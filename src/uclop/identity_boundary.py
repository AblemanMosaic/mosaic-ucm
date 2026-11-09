from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import exact_keys, require, require_root, root
from .custody import CustodyProvider, verify_asymmetric


IDENTITY_BINDING_DOMAIN = "UCL_UCM_OPERATIONAL_IDENTITY_BINDING_V1"
ALLOWED_FIXTURE_EFFECTS = {
    "READ_WORKSPACE",
    "WRITE_DISPOSABLE_FIXTURE",
    "SIGN_INFORMATION_ONLY",
}


class FixtureOSIdentityProvider:
    """Deterministic, no-effect OS identity observations for rehearsal only.

    This adapter never queries or changes the host.  A real Windows, Linux,
    HSM, or service adapter must implement the same observation contract and
    receive separate qualification and authority.
    """

    def __init__(self, *, host_root: str, principals: dict[str, dict[str, Any]]) -> None:
        self.host_root = require_root(host_root)
        checked: dict[str, dict[str, Any]] = {}
        for principal_id, value in principals.items():
            require(type(principal_id) is str and principal_id, "OS_PRINCIPAL_ID_INVALID")
            item = exact_keys(value, {"account_type", "identity_token", "enabled"}, "$.fixture_principal")
            require(item["account_type"] in {"LOCAL_FIXTURE", "SERVICE_FIXTURE"}, "OS_ACCOUNT_TYPE_INVALID")
            require(type(item["identity_token"]) is str and item["identity_token"], "OS_IDENTITY_TOKEN_INVALID")
            require(type(item["enabled"]) is bool, "OS_IDENTITY_ENABLED_INVALID")
            checked[principal_id] = deepcopy(item)
        self._principals = checked

    def observe(self, principal_id: str, *, nonce: str) -> dict[str, Any]:
        require(principal_id in self._principals, "OS_PRINCIPAL_UNKNOWN")
        require(type(nonce) is str and nonce, "OS_IDENTITY_NONCE_INVALID")
        principal = self._principals[principal_id]
        require(principal["enabled"], "OS_PRINCIPAL_DISABLED")
        body = {
            "schema": "ucl.ucm.fixture_os_identity_observation.v1",
            "provider_kind": "FIXTURE_ONLY",
            "host_root": self.host_root,
            "principal_id": principal_id,
            "account_type": principal["account_type"],
            "identity_token_root": root({"identity_token": principal["identity_token"]}),
            "nonce": nonce,
            "persistent_host_observation": False,
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        return {**body, "observation_root": root(body)}


def provider_contract(provider_root: str, *, provider_kind: str = "FIXTURE_ONLY") -> dict[str, Any]:
    require(provider_kind == "FIXTURE_ONLY", "REAL_PROVIDER_NOT_AUTHORIZED")
    body = {
        "schema": "ucl.ucm.custody_provider_contract.v1",
        "provider_root": require_root(provider_root),
        "provider_kind": provider_kind,
        "private_material_exportable": False,
        "algorithms": ["Ed25519"],
        "permitted_standing": "INFORMATION_ONLY",
        "maximum_stage": "S2_INFORMATION_ONLY_FEDERATION",
        "persistent_host_effects": False,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    return {**body, "contract_root": root(body)}


def make_operational_identity_binding(
    provider: CustodyProvider,
    *,
    provider_root: str,
    handle: str,
    os_provider: FixtureOSIdentityProvider,
    principal_id: str,
    role_address: str,
    allowed_stages: list[str],
    allowed_effects: list[str],
    nonce: str,
) -> dict[str, Any]:
    identity = provider.identity(handle)
    require(type(role_address) is str and role_address, "IDENTITY_ROLE_ADDRESS_INVALID")
    require(role_address.rsplit("/", 1)[-1] == identity["role"], "IDENTITY_ROLE_ADDRESS_ROLE_MISMATCH")
    require(type(allowed_stages) is list and allowed_stages, "IDENTITY_STAGE_SET_INVALID")
    require(allowed_stages == sorted(set(allowed_stages)), "IDENTITY_STAGE_SET_INVALID")
    require(set(allowed_stages).issubset({
        "S0_NATIVE_REPLAY", "S1_PROTECTED_SHADOW_INSTALLATION",
        "S2_INFORMATION_ONLY_FEDERATION",
    }), "IDENTITY_STAGE_ABOVE_CEILING")
    require(type(allowed_effects) is list and allowed_effects == sorted(set(allowed_effects)) and set(allowed_effects).issubset(ALLOWED_FIXTURE_EFFECTS), "IDENTITY_EFFECT_ABOVE_CEILING")
    observation = os_provider.observe(principal_id, nonce=nonce)
    contract = provider_contract(provider_root)
    body = {
        "schema": "ucl.ucm.operational_identity_binding.v1",
        "provider_contract_root": contract["contract_root"],
        "provider_root": require_root(provider_root),
        "role": identity["role"],
        "role_address": role_address,
        "key_root": identity["key_root"],
        "public_key_hex": identity["public_key_hex"],
        "key_generation": identity["generation"],
        "os_identity_observation": observation,
        "os_identity_observation_root": observation["observation_root"],
        "allowed_stages": sorted(allowed_stages),
        "allowed_effects": sorted(allowed_effects),
        "maximum_stage": "S2_INFORMATION_ONLY_FEDERATION",
        "real_identity_seated": False,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
    }
    signed = provider.sign(handle, IDENTITY_BINDING_DOMAIN, body)
    return {**signed, "binding_root": root(signed)}


def verify_operational_identity_binding(
    value: Any,
    *,
    expected_provider_root: str,
    expected_key_root: str,
    expected_principal_id: str,
    expected_role_address: str,
    expected_host_root: str,
    expected_nonce: str,
    expected_allowed_stages: list[str],
    expected_allowed_effects: list[str],
) -> dict[str, Any]:
    item = exact_keys(value, {
        "body", "body_root", "signature", "key_root", "signature_algorithm", "binding_root",
    }, "$.identity_binding")
    signed = {key: item[key] for key in ("body", "body_root", "signature", "key_root", "signature_algorithm")}
    body = exact_keys(item["body"], {
        "schema", "provider_contract_root", "provider_root", "role", "role_address",
        "key_root", "public_key_hex", "key_generation", "os_identity_observation",
        "os_identity_observation_root", "allowed_stages", "allowed_effects", "maximum_stage",
        "real_identity_seated", "standing", "authority_effect",
    }, "$.identity_binding.body")
    require(body["schema"] == "ucl.ucm.operational_identity_binding.v1", "IDENTITY_BINDING_SCHEMA_INVALID")
    require(item["binding_root"] == root(signed), "IDENTITY_BINDING_ROOT_INVALID")
    require(body["provider_root"] == require_root(expected_provider_root), "IDENTITY_PROVIDER_MISMATCH")
    require(body["key_root"] == require_root(expected_key_root) == item["key_root"], "IDENTITY_KEY_MISMATCH")
    require(body["role_address"] == expected_role_address, "IDENTITY_ROLE_ADDRESS_MISMATCH")
    require(type(body["role"]) is str and body["role_address"].rsplit("/", 1)[-1] == body["role"], "IDENTITY_ROLE_ADDRESS_ROLE_MISMATCH")
    observation = exact_keys(body["os_identity_observation"], {
        "schema", "provider_kind", "host_root", "principal_id", "account_type",
        "identity_token_root", "nonce", "persistent_host_observation", "standing",
        "authority_effect", "observation_root",
    }, "$.identity_binding.body.os_identity_observation")
    require(body["os_identity_observation_root"] == root({key: observation[key] for key in observation if key != "observation_root"}) == observation["observation_root"], "OS_IDENTITY_OBSERVATION_ROOT_INVALID")
    require(observation["principal_id"] == expected_principal_id and observation["provider_kind"] == "FIXTURE_ONLY", "OS_IDENTITY_PRINCIPAL_MISMATCH")
    require(observation["host_root"] == require_root(expected_host_root), "OS_IDENTITY_HOST_MISMATCH")
    require(observation["nonce"] == expected_nonce, "OS_IDENTITY_NONCE_MISMATCH")
    require(observation["persistent_host_observation"] is False and observation["standing"] == "INFORMATION_ONLY" and observation["authority_effect"] == "NONE", "OS_IDENTITY_EFFECT_FORBIDDEN")
    require(body["maximum_stage"] == "S2_INFORMATION_ONLY_FEDERATION", "IDENTITY_STAGE_ABOVE_CEILING")
    require(type(expected_allowed_stages) is list and expected_allowed_stages == sorted(set(expected_allowed_stages)), "IDENTITY_STAGE_SET_INVALID")
    require(type(body["allowed_stages"]) is list and body["allowed_stages"] == expected_allowed_stages and set(body["allowed_stages"]).issubset({
        "S0_NATIVE_REPLAY", "S1_PROTECTED_SHADOW_INSTALLATION", "S2_INFORMATION_ONLY_FEDERATION",
    }), "IDENTITY_STAGE_SET_MISMATCH")
    require(type(expected_allowed_effects) is list and expected_allowed_effects == sorted(set(expected_allowed_effects)), "IDENTITY_EFFECT_SET_INVALID")
    require(type(body["allowed_effects"]) is list and body["allowed_effects"] == expected_allowed_effects and set(body["allowed_effects"]).issubset(ALLOWED_FIXTURE_EFFECTS), "IDENTITY_EFFECT_SET_MISMATCH")
    require(body["real_identity_seated"] is False and body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE", "IDENTITY_BINDING_EFFECT_FORBIDDEN")
    verify_asymmetric(signed, IDENTITY_BINDING_DOMAIN, expected_key_root=body["key_root"], public_key_hex=body["public_key_hex"])
    return deepcopy(body)

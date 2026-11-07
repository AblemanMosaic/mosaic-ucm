from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

from .canonical import Refusal, exact_keys, require, require_root, root


ROLE_SET = {"GOVERNOR", "H_M", "H_J", "RECOVERY", "WITNESS", "REVIEWER", "NODE", "REGISTRY_GOVERNOR"}
RETIREMENT_DOMAIN = "UCL_UCM_IDENTITY_RETIREMENT_LEDGER_V2"


class CustodyProvider(Protocol):
    """Minimum agent-independent signing surface. Private material is absent."""

    def identity(self, handle: str) -> dict[str, Any]: ...
    def sign(self, handle: str, domain: str, body: dict[str, Any]) -> dict[str, Any]: ...
    def retire(self, handle: str) -> dict[str, Any]: ...
    def inventory(self) -> dict[str, Any]: ...


class ExternalSignerProvider:
    """Adapter for an OS, HSM, service, or subprocess signer.

    The provider stores public identities and opaque callbacks only. It cannot
    import or export a seed. Real provider installation remains outside this
    experimental package.
    """

    def __init__(
        self, *, provider_root: str, identities: dict[str, dict[str, Any]],
        sign_callback: Callable[[str, str, str], str],
        retire_callback: Callable[[str], None],
    ) -> None:
        self.provider_root = require_root(provider_root)
        checked: dict[str, dict[str, Any]] = {}
        roots: set[str] = set()
        for handle, value in identities.items():
            require(type(handle) is str and handle, "CUSTODY_HANDLE_INVALID")
            identity = exact_keys(value, {"schema", "role", "key_root", "public_key_hex", "generation"}, "$.external_identity")
            require(identity["schema"] == "ucl.ucm.asymmetric_public_identity.v1" and identity["role"] in ROLE_SET, "EXTERNAL_IDENTITY_INVALID")
            require(identity["key_root"] == public_key_root(identity["public_key_hex"]), "EXTERNAL_IDENTITY_KEY_ROOT_MISMATCH")
            require(type(identity["generation"]) is int and type(identity["generation"]) is not bool and identity["generation"] > 0, "EXTERNAL_IDENTITY_GENERATION_INVALID")
            require(identity["key_root"] not in roots, "EXTERNAL_IDENTITY_KEY_COLLISION")
            roots.add(identity["key_root"]); checked[handle] = dict(identity)
        self._identities = checked
        self._sign_callback = sign_callback
        self._retire_callback = retire_callback

    def identity(self, handle: str) -> dict[str, Any]:
        require(handle in self._identities, "CUSTODY_HANDLE_UNKNOWN")
        return dict(self._identities[handle])

    def sign(self, handle: str, domain: str, body: dict[str, Any]) -> dict[str, Any]:
        identity = self.identity(handle)
        body_root = root(body)
        signature = self._sign_callback(handle, domain, body_root)
        require(type(signature) is str and signature, "EXTERNAL_SIGNATURE_INVALID")
        record = {"body": body, "body_root": body_root, "signature": signature, "key_root": identity["key_root"], "signature_algorithm": "Ed25519"}
        verify_asymmetric(record, domain, expected_key_root=identity["key_root"], public_key_hex=identity["public_key_hex"])
        return record

    def retire(self, handle: str) -> dict[str, Any]:
        identity = self.identity(handle)
        self._retire_callback(handle)
        self._identities.pop(handle)
        return {"role": identity["role"], "key_root": identity["key_root"], "status": "RETIRED"}

    def inventory(self) -> dict[str, Any]:
        return {
            "schema": "ucl.ucm.external_custody_inventory.v1",
            "provider_root": self.provider_root,
            "active_public_identities": [self._identities[key] for key in sorted(self._identities)],
            "private_material_exported": False,
            "custody_mode": "EXTERNAL_OPAQUE_PROVIDER",
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        }


def _public_bytes(key: Ed25519PublicKey) -> bytes:
    return key.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)


def public_key_root(public_key_hex: str) -> str:
    require(type(public_key_hex) is str and len(public_key_hex) == 64, "PUBLIC_KEY_INVALID")
    try:
        raw = bytes.fromhex(public_key_hex)
    except ValueError as error:
        raise Refusal("PUBLIC_KEY_INVALID") from error
    require(len(raw) == 32, "PUBLIC_KEY_INVALID")
    return hashlib.sha256(raw).hexdigest()


def _message(domain: str, body_root: str) -> bytes:
    require(type(domain) is str and domain and "\x00" not in domain, "SIGNATURE_DOMAIN_INVALID")
    return domain.encode("utf-8") + b"\x00" + require_root(body_root).encode("ascii")


@dataclass(frozen=True)
class PublicIdentity:
    role: str
    key_root: str
    public_key_hex: str
    generation: int

    def record(self) -> dict[str, Any]:
        return {
            "schema": "ucl.ucm.asymmetric_public_identity.v1",
            "role": self.role,
            "key_root": self.key_root,
            "public_key_hex": self.public_key_hex,
            "generation": self.generation,
        }


class OpaqueEd25519KeyStore:
    """Fixture-only in-process signer. Use ExternalSignerProvider for real custody."""

    def __init__(self) -> None:
        self._keys: dict[str, Ed25519PrivateKey] = {}
        self._identities: dict[str, PublicIdentity] = {}
        self._active_by_role: dict[str, str] = {}
        self._retired_roots: set[str] = set()
        self._counter = 0

    def _install(self, role: str, private: Ed25519PrivateKey, generation: int) -> str:
        require(role in ROLE_SET, "CUSTODY_ROLE_INVALID")
        require(type(generation) is int and type(generation) is not bool and generation > 0, "CUSTODY_GENERATION_INVALID")
        public_hex = _public_bytes(private.public_key()).hex()
        key_root = public_key_root(public_hex)
        require(key_root not in self._retired_roots, "CUSTODY_RETIRED_KEY_REUSE")
        require(all(identity.key_root != key_root for identity in self._identities.values()), "CUSTODY_KEY_DUPLICATE")
        prior = self._active_by_role.get(role)
        if prior is not None:
            require(self._identities[prior].generation < generation, "CUSTODY_GENERATION_NOT_ADVANCED")
        self._counter += 1
        handle = f"key:{role.lower()}:{self._counter:08d}"
        self._keys[handle] = private
        self._identities[handle] = PublicIdentity(role, key_root, public_hex, generation)
        self._active_by_role[role] = handle
        return handle

    def generate(self, role: str, *, generation: int = 1) -> str:
        return self._install(role, Ed25519PrivateKey.generate(), generation)

    def install_fixture_seed(self, role: str, seed: bytes, *, generation: int = 1) -> str:
        require(type(seed) is bytes and len(seed) == 32, "CUSTODY_FIXTURE_SEED_INVALID")
        return self._install(role, Ed25519PrivateKey.from_private_bytes(seed), generation)

    def identity(self, handle: str) -> dict[str, Any]:
        require(type(handle) is str and handle in self._identities, "CUSTODY_HANDLE_UNKNOWN")
        return self._identities[handle].record()

    def active_handle(self, role: str) -> str:
        require(role in self._active_by_role, "CUSTODY_ROLE_NOT_ACTIVE")
        return self._active_by_role[role]

    def sign(self, handle: str, domain: str, body: dict[str, Any]) -> dict[str, Any]:
        require(type(handle) is str and handle in self._keys, "CUSTODY_HANDLE_UNKNOWN")
        body_root = root(body)
        signature = self._keys[handle].sign(_message(domain, body_root))
        identity = self._identities[handle]
        return {
            "body": body,
            "body_root": body_root,
            "signature": base64.b64encode(signature).decode("ascii"),
            "key_root": identity.key_root,
            "signature_algorithm": "Ed25519",
        }

    def retire(self, handle: str) -> dict[str, Any]:
        require(type(handle) is str and handle in self._keys, "CUSTODY_HANDLE_UNKNOWN")
        identity = self._identities[handle]
        self._retired_roots.add(identity.key_root)
        self._keys.pop(handle)
        if self._active_by_role.get(identity.role) == handle:
            self._active_by_role.pop(identity.role)
        return {"role": identity.role, "key_root": identity.key_root, "status": "RETIRED"}

    def inventory(self) -> dict[str, Any]:
        active = [self._identities[handle].record() for handle in sorted(self._keys)]
        roots = [item["key_root"] for item in active]
        require(len(roots) == len(set(roots)), "CUSTODY_ACTIVE_KEY_COLLISION")
        return {
            "schema": "ucl.ucm.opaque_key_custody_inventory.v1",
            "active_public_identities": active,
            "retired_key_roots": sorted(self._retired_roots),
            "private_material_exported": False,
            "custody_mode": "FIXTURE_IN_PROCESS",
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }


def verify_asymmetric(record: Any, domain: str, *, expected_key_root: str, public_key_hex: str) -> dict[str, Any]:
    item = exact_keys(record, {"body", "body_root", "signature", "key_root", "signature_algorithm"}, "$.signed")
    require(item["signature_algorithm"] == "Ed25519", "SIGNATURE_ALGORITHM_INVALID")
    require(item["body_root"] == root(item["body"]), "SIGNED_BODY_ROOT_MISMATCH")
    require(item["key_root"] == require_root(expected_key_root) == public_key_root(public_key_hex), "SIGNATURE_KEY_ROOT_MISMATCH")
    try:
        signature = base64.b64decode(item["signature"], validate=True)
        public = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        public.verify(signature, _message(domain, item["body_root"]))
    except (ValueError, InvalidSignature) as error:
        raise Refusal("SIGNATURE_INVALID") from error
    return dict(item["body"])


class IdentityRetirementLedger:
    """Cross-registry, cross-role retirement memory for admitted public identities."""

    def __init__(self, *, persistence_callback: Callable[[dict[str, Any]], None] | None = None, fixture_only: bool = False) -> None:
        require(fixture_only or persistence_callback is not None, "RETIREMENT_PERSISTENCE_REQUIRED")
        self._events: list[dict[str, Any]] = []
        self._ever_used: dict[str, str] = {}
        self._active: dict[str, str] = {}
        self._persistence_callback = persistence_callback
        self._fixture_only = fixture_only
        self._persistence_failed = False

    def bind_persistence(self, callback: Callable[[dict[str, Any]], None]) -> None:
        require(self._fixture_only and self._persistence_callback is None, "RETIREMENT_PERSISTENCE_ALREADY_BOUND")
        self._persistence_callback = callback
        self._fixture_only = False

    def _usable(self) -> None:
        require(not self._persistence_failed, "RETIREMENT_RESTART_REQUIRED_AFTER_PERSISTENCE_FAILURE")

    def _persist(self) -> None:
        if self._fixture_only:
            return
        require(self._persistence_callback is not None, "RETIREMENT_PERSISTENCE_REQUIRED")
        try:
            self._persistence_callback(self.snapshot())
        except Exception:
            self._persistence_failed = True
            raise

    def admit(self, *, role_address: str, key_root: str, lineage_root: str) -> dict[str, Any]:
        self._usable()
        require(type(role_address) is str and role_address, "IDENTITY_ROLE_ADDRESS_INVALID")
        key_root, lineage_root = require_root(key_root), require_root(lineage_root)
        require(key_root not in self._ever_used, "HISTORICAL_IDENTITY_REUSE")
        require(role_address not in self._active, "IDENTITY_ROLE_ALREADY_ACTIVE")
        event = {"action": "ADMIT", "role_address": role_address, "key_root": key_root, "lineage_root": lineage_root, "sequence": len(self._events) + 1, "predecessor": self._events[-1]["event_root"] if self._events else "GENESIS"}
        event["event_root"] = root(event)
        self._events.append(event)
        self._ever_used[key_root] = role_address
        self._active[role_address] = key_root
        self._persist()
        return dict(event)

    def retire(self, *, role_address: str, expected_key_root: str, lineage_root: str) -> dict[str, Any]:
        self._usable()
        require(self._active.get(role_address) == require_root(expected_key_root), "IDENTITY_ACTIVE_BINDING_MISMATCH")
        event = {"action": "RETIRE", "role_address": role_address, "key_root": expected_key_root, "lineage_root": require_root(lineage_root), "sequence": len(self._events) + 1, "predecessor": self._events[-1]["event_root"]}
        event["event_root"] = root(event)
        self._events.append(event)
        self._active.pop(role_address)
        self._persist()
        return dict(event)

    def snapshot(self) -> dict[str, Any]:
        return {"schema": "ucl.ucm.identity_retirement_ledger.v1", "sequence": len(self._events), "head": self._events[-1]["event_root"] if self._events else "GENESIS", "events": list(self._events), "ever_used": dict(sorted(self._ever_used.items())), "active": dict(sorted(self._active.items())), "standing": "INFORMATION_ONLY", "authority_effect": "NONE"}

    def signed_snapshot(self, provider: CustodyProvider, handle: str) -> dict[str, Any]:
        body = dict(self.snapshot())
        body["schema"] = "ucl.ucm.identity_retirement_ledger.v2"
        signed = provider.sign(handle, RETIREMENT_DOMAIN, body)
        return {**signed, "ledger_root": root(signed)}

    @classmethod
    def restore_signed(cls, record: Any, *, expected_identity: dict[str, Any]) -> "IdentityRetirementLedger":
        item = exact_keys(record, {"body", "body_root", "signature", "key_root", "signature_algorithm", "ledger_root"}, "$.retirement_ledger")
        signed = {key: item[key] for key in ("body", "body_root", "signature", "key_root", "signature_algorithm")}
        body = verify_asymmetric(signed, RETIREMENT_DOMAIN, expected_key_root=expected_identity["key_root"], public_key_hex=expected_identity["public_key_hex"])
        require(item["ledger_root"] == root(signed), "RETIREMENT_LEDGER_ROOT_INVALID")
        exact_keys(body, {"schema", "sequence", "head", "events", "ever_used", "active", "standing", "authority_effect"}, "$.retirement_ledger.body")
        require(body["schema"] == "ucl.ucm.identity_retirement_ledger.v2", "RETIREMENT_LEDGER_SCHEMA_INVALID")
        return cls.restore_snapshot(body)

    @classmethod
    def restore_snapshot(cls, body: Any) -> "IdentityRetirementLedger":
        exact_keys(body, {"schema", "sequence", "head", "events", "ever_used", "active", "standing", "authority_effect"}, "$.retirement_ledger.body")
        require(body["schema"] in {"ucl.ucm.identity_retirement_ledger.v1", "ucl.ucm.identity_retirement_ledger.v2"}, "RETIREMENT_LEDGER_SCHEMA_INVALID")
        require(body["standing"] == "INFORMATION_ONLY" and body["authority_effect"] == "NONE", "RETIREMENT_LEDGER_EFFECT_INVALID")
        ledger = cls(fixture_only=True)
        for number, event in enumerate(body["events"], 1):
            require(event.get("sequence") == number, "RETIREMENT_LEDGER_SEQUENCE_INVALID")
            require(event.get("predecessor") == (ledger._events[-1]["event_root"] if ledger._events else "GENESIS"), "RETIREMENT_LEDGER_PREDECESSOR_INVALID")
            check = dict(event); declared = check.pop("event_root", None)
            require(declared == root(check), "RETIREMENT_LEDGER_EVENT_ROOT_INVALID")
            if event["action"] == "ADMIT":
                ledger.admit(role_address=event["role_address"], key_root=event["key_root"], lineage_root=event["lineage_root"])
            elif event["action"] == "RETIRE":
                ledger.retire(role_address=event["role_address"], expected_key_root=event["key_root"], lineage_root=event["lineage_root"])
            else:
                require(False, "RETIREMENT_LEDGER_ACTION_INVALID")
        require(ledger.snapshot()["head"] == body["head"] and ledger.snapshot()["ever_used"] == body["ever_used"] and ledger.snapshot()["active"] == body["active"], "RETIREMENT_LEDGER_STATE_MISMATCH")
        return ledger

    def save(self, path: Path, provider: CustodyProvider, handle: str) -> dict[str, Any]:
        record = self.signed_snapshot(provider, handle)
        path = path.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        pending = path.with_name("." + path.name + ".pending")
        pending.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        with pending.open("r+b") as stream:
            os.fsync(stream.fileno())
        os.replace(pending, path)
        return record

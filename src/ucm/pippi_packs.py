"""Deterministic optional-component planning for P/PPI.

The resolver is deliberately effect free.  It tells a human or governed host
what is present, what could be selected, and which exact external artifacts or
bindings are still required.  Download, installation, service registration,
credential use, and external binding remain separately authorized effects.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

from uclop.canonical import root

from .pippi_global import BOUNDARY, HubRefusal


REGISTRY_SCHEMA = "mosaic.ucm.pippi-pack-registry.v0.1"
INVENTORY_SCHEMA = "mosaic.ucm.pippi-pack-inventory.v0.1"
REQUEST_SCHEMA = "mosaic.ucm.pippi-install-plan-request.v0.1"
PLAN_SCHEMA = "mosaic.ucm.pippi-install-plan.v0.1"
PORTABILITY_SCHEMA = "mosaic.ucm.pippi-project-portability.v0.1"

STATES = (
    "BUILT_IN", "AVAILABLE_OFFLINE", "AVAILABLE_REMOTE",
    "INSTALLED_UNBOUND", "BOUND_EXTERNAL", "UNAVAILABLE",
    "INCOMPATIBLE", "HELD_FOR_AUTHORIZATION",
)
PACK_IDS = (
    "PIPPI_CORE", "UCM_CORE", "MOSAIC_UI", "UGK_STANDARDS",
    "UGK_RUNTIME", "SEMCRYS_CORE", "MEMORY_VAULT_ADAPTER",
    "COURTHOUSE_ADAPTER", "NATIVE_HOST_ADAPTER", "UGEL_EXECUTOR",
)
PROFILE_IDS = (
    "MINIMAL_CORE", "RECOMMENDED_LOCAL", "PORTABLE_AGENT",
    "TRANSTEMPORAL_PROJECT", "COURTHOUSE_CONNECTED", "FULL_MOSAIC",
)

SEMCRYS_RELEASE_MANIFEST_SHA256 = "1fcd5fc1a902806064e15cd327f8844579585fac01985bab776e2a93c49710ba"
SEMCRYS_ASSET_INDEX_SHA256 = "cc3227e4209dcb9021d22e296014d67fe93edcd2e1aace859087a64cb61894dc"
MEMORY_VAULT_RELEASE_CONTRACT_SHA256 = "61fe8061d03200799be8b302af82092c3b13d185af5b6c58728514bd683fc89a"


def _sha(value: Any, code: str) -> str:
    if (not isinstance(value, str) or len(value) != 64 or
            any(ch not in "0123456789abcdef" for ch in value)):
        raise HubRefusal(code)
    return value


def _pack(pack_id: str, *, label: str, description: str, required: bool,
          default_selected: bool, dependencies: Iterable[str], capabilities: Iterable[str],
          distribution: str, bundled_manifest: str | None = None,
          manifest_sha256: str | None = None, remote_locator: str | None = None,
          binding_owner: str | None = None) -> dict[str, Any]:
    return {
        "pack_id": pack_id, "label": label, "description": description,
        "required": required, "default_selected": default_selected,
        "dependencies": sorted(set(dependencies)), "conflicts": [],
        "capabilities": sorted(set(capabilities)), "distribution": distribution,
        "bundled_manifest": bundled_manifest, "manifest_sha256": manifest_sha256,
        "remote_locator": remote_locator, "binding_owner": binding_owner,
        "authority_effect": "NONE",
    }


def pack_registry() -> dict[str, Any]:
    packs = [
        _pack("PIPPI_CORE", label="P/PPI Core",
              description="Project, turn, journal, capsule, CLI, ABI, and local coordination machinery.",
              required=True, default_selected=True, dependencies=(),
              capabilities=("TURN_MEDIATION", "PROJECT_CAPSULES", "LOCAL_CONTENT_STORE"),
              distribution="BUILT_IN"),
        _pack("UCM_CORE", label="UCM Constitutional Core",
              description="Typed contracts, capability registry, verification, and non-authorizing operational boundaries.",
              required=True, default_selected=True, dependencies=("PIPPI_CORE",),
              capabilities=("UCM_VALIDATION", "THR_RECORDS", "DKN_BINDINGS"), distribution="BUILT_IN"),
        _pack("MOSAIC_UI", label="Mosaic Native UI",
              description="Dark native dashboard and installer with headless semantic correspondence.",
              required=True, default_selected=True, dependencies=("PIPPI_CORE",),
              capabilities=("NATIVE_UI", "HEADLESS_UI", "RAINBOW_SUN_BRANDING"), distribution="BUILT_IN"),
        _pack("UGK_STANDARDS", label="UGK Standards Pack",
              description="Three Hash Rule, FGA/IEL, claim discipline, and context-injection practices without claiming the canonical UGK runtime.",
              required=False, default_selected=True, dependencies=("UCM_CORE",),
              capabilities=("UGK_PRACTICE_PROFILE", "THREE_HASH_RULE", "CLAIM_DISCIPLINE"),
              distribution="BUILT_IN"),
        _pack("UGK_RUNTIME", label="Canonical UGK Runtime",
              description="Optional separately pinned native UGK implementation and certification surfaces.",
              required=False, default_selected=False, dependencies=("UGK_STANDARDS",),
              capabilities=("UGK_NATIVE_RUNTIME",), distribution="EXTERNAL_BINDING",
              binding_owner="UGK"),
        _pack("SEMCRYS_CORE", label="SemCrys Core v0.1",
              description="Optional exact reconstruction, semantic compression, reusable legends, and compact project transport.",
              required=False, default_selected=False, dependencies=("PIPPI_CORE",),
              capabilities=("SEMCRYS_PACK", "SEMCRYS_UNPACK", "SEMCRYS_VERIFY"),
              distribution="EXTERNAL_DOWNLOAD",
              bundled_manifest="vendor/optional-packs/semcrys-core-v0.1/RELEASE-MANIFEST.json",
              manifest_sha256=SEMCRYS_RELEASE_MANIFEST_SHA256,
              remote_locator="ABLEMAN_MOSAIC_SEMCRYS_V0_1_RELEASE"),
        _pack("MEMORY_VAULT_ADAPTER", label="Mosaic Memory Vault Adapter",
              description="Optional transtemporal persistence, availability checks, exact retrieval, and cross-session reconstruction.",
              required=False, default_selected=False, dependencies=("PIPPI_CORE", "SEMCRYS_CORE"),
              capabilities=("TRANSTEMPORAL_ADMIT", "TRANSTEMPORAL_RESOLVE", "TRANSTEMPORAL_MATERIALIZE"),
              distribution="EXTERNAL_BINDING",
              bundled_manifest="vendor/optional-packs/memory-vault-v0.1/PUBLIC-RELEASE-CONTRACT.json",
              manifest_sha256=MEMORY_VAULT_RELEASE_CONTRACT_SHA256,
              binding_owner="MEMORY_VAULT"),
        _pack("COURTHOUSE_ADAPTER", label="AOK Courthouse Adapter",
              description="Optional governed cross-jurisdiction work-order and result correspondence.",
              required=False, default_selected=False, dependencies=("UCM_CORE",),
              capabilities=("COURTHOUSE_WORK_ORDER", "COURTHOUSE_RESULT_IMPORT"),
              distribution="EXTERNAL_BINDING", binding_owner="AOK_COURTHOUSE"),
        _pack("NATIVE_HOST_ADAPTER", label="Native Enforced Host Adapter",
              description="Optional verified tool and visible-output interposition supplied by a compatible orchestration host.",
              required=False, default_selected=False, dependencies=("PIPPI_CORE", "UCM_CORE"),
              capabilities=("ENFORCED_HOST_MEDIATION",), distribution="EXTERNAL_BINDING",
              binding_owner="ORCHESTRATION_HOST"),
        _pack("UGEL_EXECUTOR", label="UCM Governed Execution Layer",
              description="Optional exact external executor contract and receipt adapter; UCM discovers and binds it but never selects it or mints its grants.",
              required=False, default_selected=False, dependencies=("UCM_CORE",),
              capabilities=("UGEL_EXECUTOR_DISCOVERY", "UGEL_POLICY_CORRESPONDENCE", "UGEL_EXTERNAL_RECEIPTS"),
              distribution="EXTERNAL_BINDING", binding_owner="EXTERNAL_EXECUTOR"),
    ]
    packs.sort(key=lambda row: row["pack_id"])
    profiles = {
        "MINIMAL_CORE": ["MOSAIC_UI", "PIPPI_CORE", "UCM_CORE"],
        "RECOMMENDED_LOCAL": ["MOSAIC_UI", "PIPPI_CORE", "UCM_CORE", "UGK_STANDARDS"],
        "PORTABLE_AGENT": ["MOSAIC_UI", "PIPPI_CORE", "UCM_CORE", "UGK_STANDARDS"],
        "TRANSTEMPORAL_PROJECT": ["MEMORY_VAULT_ADAPTER", "MOSAIC_UI", "PIPPI_CORE", "SEMCRYS_CORE", "UCM_CORE", "UGK_STANDARDS"],
        "COURTHOUSE_CONNECTED": ["COURTHOUSE_ADAPTER", "MOSAIC_UI", "PIPPI_CORE", "UCM_CORE", "UGK_STANDARDS"],
        "FULL_MOSAIC": list(PACK_IDS),
    }
    profiles = {key: sorted(value) for key, value in sorted(profiles.items())}
    body = {
        "schema": REGISTRY_SCHEMA, "public_version": "v0.1", "engineering_revision": "r023",
        "packs": packs, "profiles": profiles, "states": list(STATES),
        "downloads_require_explicit_user_authorization": True,
        "bindings_are_not_capability_grants": True,
        "missing_optional_pack_never_weakens_project_contract": True,
        **BOUNDARY,
    }
    return {**body, "registry_root": root(body)}


def validate_pack_registry(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HubRefusal("PIPPI_PACK_REGISTRY_INVALID")
    expected = pack_registry()
    if value != expected:
        raise HubRefusal("PIPPI_PACK_REGISTRY_INVALID")
    return deepcopy(value)


def default_pack_inventory() -> dict[str, Any]:
    registry = pack_registry()
    rows = []
    for pack in registry["packs"]:
        state = "BUILT_IN" if pack["distribution"] == "BUILT_IN" else (
            "AVAILABLE_REMOTE" if pack["distribution"] == "EXTERNAL_DOWNLOAD" else "UNAVAILABLE")
        rows.append({
            "pack_id": pack["pack_id"], "state": state,
            "installed_root": pack["manifest_sha256"] if state == "BUILT_IN" and pack["manifest_sha256"] else None,
            "binding_root": None, "evidence_roots": [],
        })
    body = {"schema": INVENTORY_SCHEMA, "registry_root": registry["registry_root"],
            "entries": rows, **BOUNDARY}
    return {**body, "inventory_root": root(body)}


def validate_pack_inventory(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != INVENTORY_SCHEMA:
        raise HubRefusal("PIPPI_PACK_INVENTORY_INVALID")
    registry = pack_registry()
    entries = value.get("entries")
    if not isinstance(entries, list) or [row.get("pack_id") for row in entries] != sorted(PACK_IDS):
        raise HubRefusal("PIPPI_PACK_INVENTORY_DENOMINATOR_INVALID")
    pack_index = {row["pack_id"]: row for row in registry["packs"]}
    for row in entries:
        if (not isinstance(row, dict) or set(row) != {"pack_id", "state", "installed_root", "binding_root", "evidence_roots"}
                or row["state"] not in STATES):
            raise HubRefusal("PIPPI_PACK_INVENTORY_ENTRY_INVALID")
        if row["installed_root"] is not None: _sha(row["installed_root"], "PIPPI_PACK_INSTALLED_ROOT_INVALID")
        if row["binding_root"] is not None: _sha(row["binding_root"], "PIPPI_PACK_BINDING_ROOT_INVALID")
        if not isinstance(row["evidence_roots"], list) or row["evidence_roots"] != sorted(set(row["evidence_roots"])):
            raise HubRefusal("PIPPI_PACK_EVIDENCE_INVALID")
        for item in row["evidence_roots"]: _sha(item, "PIPPI_PACK_EVIDENCE_INVALID")
        if row["state"] == "BOUND_EXTERNAL" and row["binding_root"] is None:
            raise HubRefusal("PIPPI_PACK_BINDING_REQUIRED")
        if row["state"] == "INSTALLED_UNBOUND" and row["installed_root"] is None:
            raise HubRefusal("PIPPI_PACK_INSTALLED_ROOT_REQUIRED")
        if (row["state"] == "BOUND_EXTERNAL"
                and pack_index[row["pack_id"]]["distribution"] == "EXTERNAL_DOWNLOAD"
                and row["installed_root"] is None):
            raise HubRefusal("PIPPI_PACK_INSTALLED_ROOT_REQUIRED")
    body = {key: deepcopy(item) for key, item in value.items() if key != "inventory_root"}
    if body.get("registry_root") != registry["registry_root"] or value.get("inventory_root") != root(body):
        raise HubRefusal("PIPPI_PACK_INVENTORY_INVALID")
    return deepcopy(value)


def _dependency_closure(selected: Iterable[str], registry: dict[str, Any]) -> list[str]:
    index = {row["pack_id"]: row for row in registry["packs"]}
    closure = set(selected)
    if not closure <= set(index):
        raise HubRefusal("PIPPI_PACK_UNKNOWN")
    changed = True
    while changed:
        before = set(closure)
        for pack_id in tuple(closure): closure.update(index[pack_id]["dependencies"])
        changed = before != closure
    return sorted(closure)


def build_install_plan(*, profile: str, inventory: dict[str, Any],
                       requested_packs: list[str] | None = None,
                       offline_artifact_roots: list[str] | None = None,
                       allow_remote_downloads: bool = False) -> dict[str, Any]:
    registry = pack_registry(); inventory = validate_pack_inventory(inventory)
    if profile not in PROFILE_IDS: raise HubRefusal("PIPPI_INSTALL_PROFILE_INVALID")
    requested = sorted(set(requested_packs or []))
    selected = _dependency_closure([*registry["profiles"][profile], *requested], registry)
    offline = sorted(set(offline_artifact_roots or []))
    for item in offline: _sha(item, "PIPPI_OFFLINE_ARTIFACT_ROOT_INVALID")
    pack_index = {row["pack_id"]: row for row in registry["packs"]}
    inventory_index = {row["pack_id"]: row for row in inventory["entries"]}
    actions = []; holds = []
    for pack_id in selected:
        pack = pack_index[pack_id]; state = inventory_index[pack_id]["state"]
        if state in {"BUILT_IN", "BOUND_EXTERNAL"}:
            action = "PRESENT"
        elif state == "INSTALLED_UNBOUND":
            action = "BIND_EXTERNAL" if pack["binding_owner"] else "PRESENT"
        elif pack["distribution"] == "EXTERNAL_DOWNLOAD":
            if pack["manifest_sha256"] in offline:
                action = "VERIFY_OFFLINE_ARTIFACT"
                holds.append({"pack_id": pack_id, "code": "PIPPI_OFFLINE_ARTIFACT_VERIFICATION_REQUIRED"})
            elif allow_remote_downloads:
                action = "DOWNLOAD_REQUIRES_USER_AUTHORIZATION"
                holds.append({"pack_id": pack_id, "code": "PIPPI_DOWNLOAD_AUTHORIZATION_REQUIRED"})
            else:
                action = "REMOTE_DOWNLOAD_NOT_SELECTED"
                holds.append({"pack_id": pack_id, "code": "PIPPI_PACK_NOT_LOCALLY_AVAILABLE"})
        elif pack["distribution"] == "EXTERNAL_BINDING":
            action = "BIND_EXTERNAL"
            holds.append({"pack_id": pack_id, "code": "PIPPI_EXTERNAL_BINDING_REQUIRED"})
        else:
            action = "UNAVAILABLE"
            holds.append({"pack_id": pack_id, "code": "PIPPI_PACK_UNAVAILABLE"})
        actions.append({"pack_id": pack_id, "current_state": state, "action": action,
                        "manifest_sha256": pack["manifest_sha256"],
                        "remote_locator": pack["remote_locator"],
                        "binding_owner": pack["binding_owner"]})
    request_body = {"schema": REQUEST_SCHEMA, "profile": profile,
                    "requested_packs": requested, "inventory_root": inventory["inventory_root"],
                    "offline_artifact_roots": offline, "allow_remote_downloads": allow_remote_downloads}
    request_root = root(request_body)
    body = {"schema": PLAN_SCHEMA, "request_root": request_root,
            "registry_root": registry["registry_root"], "inventory_root": inventory["inventory_root"],
            "profile": profile, "selected_packs": selected, "actions": actions,
            "holds": holds, "status": "READY" if not holds else "HELD",
            "plan_performs_effects": False, "explicit_user_authorization_required": bool(holds),
            **BOUNDARY}
    return {**body, "install_plan_root": root(body)}


def explain_project_portability(*, required_packs: list[str], inventory: dict[str, Any]) -> dict[str, Any]:
    registry = pack_registry(); inventory = validate_pack_inventory(inventory)
    required = _dependency_closure(required_packs, registry)
    index = {row["pack_id"]: row for row in inventory["entries"]}
    definitions = {row["pack_id"]: row for row in registry["packs"]}
    def ready(pack_id: str) -> bool:
        state = index[pack_id]["state"]
        return state in {"BUILT_IN", "BOUND_EXTERNAL"} or (
            state == "INSTALLED_UNBOUND" and definitions[pack_id]["binding_owner"] is None)
    missing = [pack_id for pack_id in required if not ready(pack_id)]
    body = {"schema": PORTABILITY_SCHEMA, "registry_root": registry["registry_root"],
            "inventory_root": inventory["inventory_root"], "required_packs": required,
            "missing_packs": missing, "status": "READY" if not missing else "NEEDS_PACKS",
            "view_only_allowed": True, **BOUNDARY}
    return {**body, "portability_root": root(body)}


def verify_bundled_optional_pack_manifests(source_root: Path) -> dict[str, Any]:
    registry = pack_registry(); checked = []
    for pack in registry["packs"]:
        relative = pack["bundled_manifest"]
        if relative is None: continue
        path = source_root / relative
        if not path.is_file(): raise HubRefusal("PIPPI_PACK_MANIFEST_MISSING", pack["pack_id"])
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != pack["manifest_sha256"]:
            raise HubRefusal("PIPPI_PACK_MANIFEST_PIN_MISMATCH", pack["pack_id"])
        try: json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error: raise HubRefusal("PIPPI_PACK_MANIFEST_INVALID", pack["pack_id"]) from error
        checked.append({"pack_id": pack["pack_id"], "manifest_sha256": digest})
    body = {"schema": "mosaic.ucm.pippi-pack-manifest-verification.v0.1",
            "registry_root": registry["registry_root"], "checked": checked,
            "status": "PASS", **BOUNDARY}
    return {**body, "verification_root": root(body)}


def transition_pack_inventory(*, inventory: dict[str, Any], pack_id: str,
                              state: str, installed_root: str | None,
                              binding_root: str | None,
                              evidence_roots: list[str]) -> dict[str, Any]:
    inventory = validate_pack_inventory(inventory)
    if pack_id not in PACK_IDS or state not in STATES:
        raise HubRefusal("PIPPI_PACK_TRANSITION_INVALID")
    if installed_root is not None: _sha(installed_root, "PIPPI_PACK_INSTALLED_ROOT_INVALID")
    if binding_root is not None: _sha(binding_root, "PIPPI_PACK_BINDING_ROOT_INVALID")
    evidence = sorted(set(evidence_roots))
    for item in evidence: _sha(item, "PIPPI_PACK_EVIDENCE_INVALID")
    if state == "BOUND_EXTERNAL" and binding_root is None:
        raise HubRefusal("PIPPI_PACK_BINDING_REQUIRED")
    if state in {"BUILT_IN", "INSTALLED_UNBOUND", "BOUND_EXTERNAL"} and not evidence:
        raise HubRefusal("PIPPI_PACK_VERIFICATION_EVIDENCE_REQUIRED")
    rows = []
    for row in inventory["entries"]:
        rows.append({"pack_id": pack_id, "state": state,
                     "installed_root": installed_root, "binding_root": binding_root,
                     "evidence_roots": evidence} if row["pack_id"] == pack_id else row)
    body = {"schema": INVENTORY_SCHEMA, "registry_root": pack_registry()["registry_root"],
            "entries": rows, **BOUNDARY}
    return validate_pack_inventory({**body, "inventory_root": root(body)})


class PackStore:
    """Small atomic inventory store; component effects are performed elsewhere."""
    def __init__(self, data_root: Path) -> None:
        self.root = Path(data_root).resolve() / "packs"
        self.inventory_path = self.root / "INVENTORY.json"

    def inventory(self) -> dict[str, Any]:
        if not self.inventory_path.is_file(): return default_pack_inventory()
        try: return validate_pack_inventory(json.loads(self.inventory_path.read_text(encoding="utf-8")))
        except (OSError, ValueError) as error: raise HubRefusal("PIPPI_PACK_INVENTORY_INVALID") from error

    def initialize(self) -> dict[str, Any]:
        current = self.inventory()
        if self.inventory_path.is_file(): return current
        self._write(current); return current

    def record(self, *, expected_inventory_root: str, pack_id: str, state: str,
               installed_root: str | None, binding_root: str | None,
               evidence_roots: list[str]) -> dict[str, Any]:
        current = self.inventory()
        if current["inventory_root"] != expected_inventory_root:
            raise HubRefusal("PIPPI_PACK_INVENTORY_HEAD_MISMATCH")
        successor = transition_pack_inventory(inventory=current, pack_id=pack_id,
            state=state, installed_root=installed_root, binding_root=binding_root,
            evidence_roots=evidence_roots)
        self._write(successor); return successor

    def _write(self, value: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        pending = self.inventory_path.with_suffix(".pending")
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
        with pending.open("wb") as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.replace(pending, self.inventory_path)

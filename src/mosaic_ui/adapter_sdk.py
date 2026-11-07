"""Governed lifecycle and evidence contract for optional-domain adapters."""
from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .canonical import commitment
from .domain_protocol import (
    DOMAIN_PROTOCOL_SCHEMA, DOMAINS, DomainRefusal, require_identifier, require_sha256,
)


ADAPTER_SDK_SCHEMA = "mosaic.ui.adapter-sdk.v0.1"
ADAPTER_STATES = ("CREATED", "OPEN", "PROJECTED", "CLOSED")


@dataclass(frozen=True)
class AdapterManifest:
    adapter_id: str
    domain: str
    runtime_binding: str
    artifact_kinds: tuple[str, ...]
    capabilities: tuple[str, ...]
    dependencies: tuple[str, ...] = ()
    host_effects: tuple[str, ...] = ("WRITE_BOUNDED_ARTIFACTS",)

    def as_dict(self) -> dict[str, Any]:
        adapter_id = require_identifier(self.adapter_id, "ADAPTER_ID_REFUSED")
        if self.domain not in DOMAINS or not self.runtime_binding:
            raise DomainRefusal("ADAPTER_MANIFEST_REFUSED", adapter_id)
        for label, values in (("artifact", self.artifact_kinds), ("capability", self.capabilities),
                              ("dependency", self.dependencies), ("effect", self.host_effects)):
            if len(values) != len(set(values)) or not all(isinstance(item, str) and item for item in values):
                raise DomainRefusal("ADAPTER_MANIFEST_REFUSED", f"{adapter_id}:{label}")
        value = {
            "schema": "mosaic.ui.adapter-manifest.v0.1",
            "adapter_id": adapter_id,
            "domain": self.domain,
            "domain_protocol": DOMAIN_PROTOCOL_SCHEMA,
            "adapter_sdk": ADAPTER_SDK_SCHEMA,
            "runtime_binding": self.runtime_binding,
            "artifact_kinds": list(self.artifact_kinds),
            "capabilities": list(self.capabilities),
            "dependencies": list(self.dependencies),
            "host_effects": list(self.host_effects),
            "canonical_dependency": False,
            "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.ADAPTER_MANIFEST.v0.1", value)
        return value


@runtime_checkable
class DomainAdapter(Protocol):
    @property
    def manifest(self) -> AdapterManifest: ...

    @property
    def lifecycle_state(self) -> str: ...

    def open(self, scene: dict[str, Any]) -> dict[str, Any]: ...

    def project(self, snapshot: dict[str, Any], output_root: Path) -> dict[str, Any]: ...

    def observe(self) -> dict[str, Any]: ...

    def close(self) -> dict[str, Any]: ...


class GovernedAdapterSession:
    """Base lifecycle; subclasses implement one bounded artifact projection."""

    manifest: AdapterManifest

    def __init__(self) -> None:
        if not hasattr(self, "manifest"):
            raise DomainRefusal("ADAPTER_MANIFEST_ABSENT", type(self).__name__)
        self.manifest.as_dict()
        self._state = "CREATED"
        self._scene: dict[str, Any] | None = None
        self._observation: dict[str, Any] | None = None

    @property
    def lifecycle_state(self) -> str:
        return self._state

    @property
    def scene(self) -> dict[str, Any]:
        if self._scene is None:
            raise DomainRefusal("ADAPTER_NOT_OPEN", self.manifest.adapter_id)
        return self._scene

    def open(self, scene: dict[str, Any]) -> dict[str, Any]:
        if self._state != "CREATED":
            raise DomainRefusal("ADAPTER_LIFECYCLE_REFUSED", f"{self._state}:OPEN")
        raw = copy.deepcopy(scene)
        supplied_root = raw.pop("scene_commitment", None)
        require_sha256(supplied_root, "ADAPTER_SCENE_ROOT_REFUSED")
        if self.manifest.domain == "PLAY_2D":
            from .play import validate_play_scene
            validated = validate_play_scene(raw)
        else:
            from .spatial import validate_spatial_scene
            validated = validate_spatial_scene(raw)
        scene_root = validated["scene_commitment"]
        if supplied_root != scene_root:
            raise DomainRefusal("ADAPTER_SCENE_COMMITMENT_REFUSED", self.manifest.adapter_id)
        self._scene = validated
        self._state = "OPEN"
        value = {
            "schema": "mosaic.ui.adapter-open-receipt.v0.1",
            "adapter": self.manifest.as_dict(),
            "scene_commitment": scene_root,
            "lifecycle_state": self._state,
            "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.ADAPTER_OPEN_RECEIPT.v0.1", value)
        return value

    def project(self, snapshot: dict[str, Any], output_root: Path) -> dict[str, Any]:
        if self._state not in {"OPEN", "PROJECTED"}:
            raise DomainRefusal("ADAPTER_LIFECYCLE_REFUSED", f"{self._state}:PROJECT")
        if snapshot.get("scene_commitment") != self.scene["scene_commitment"]:
            raise DomainRefusal("ADAPTER_SNAPSHOT_SCENE_REFUSED", self.manifest.adapter_id)
        require_sha256(snapshot.get("semantic_state_root"), "ADAPTER_SEMANTIC_ROOT_REFUSED")
        if not isinstance(output_root, Path):
            raise DomainRefusal("ADAPTER_OUTPUT_ROOT_REFUSED", type(output_root).__name__)
        resolved_root = output_root.resolve()
        result = self._project(copy.deepcopy(snapshot), resolved_root)
        if result.get("authority_effect") != "NONE" or result.get("adapter_id") != self.manifest.adapter_id \
                or result.get("semantic_state_root") != snapshot["semantic_state_root"]:
            raise DomainRefusal("ADAPTER_RESULT_REFUSED", self.manifest.adapter_id)
        require_sha256(result.get("artifact_sha256"), "ADAPTER_ARTIFACT_HASH_REFUSED")
        self._verify_artifacts(result, resolved_root)
        self._observation = copy.deepcopy(result)
        self._state = "PROJECTED"
        return copy.deepcopy(result)

    def _verify_artifacts(self, result: dict[str, Any], output_root: Path) -> None:
        artifacts = result.get("artifacts")
        if artifacts is None:
            rows = ({
                "name": result.get("artifact"), "sha256": result.get("artifact_sha256"),
                "bytes": result.get("artifact_bytes"),
            },)
        elif isinstance(artifacts, dict) and artifacts:
            rows = tuple(artifacts.values())
        else:
            raise DomainRefusal("ADAPTER_ARTIFACT_SET_REFUSED", self.manifest.adapter_id)
        verified_primary = False
        for row in rows:
            if not isinstance(row, dict):
                raise DomainRefusal("ADAPTER_ARTIFACT_RECORD_REFUSED", self.manifest.adapter_id)
            name, expected_hash, expected_bytes = row.get("name"), row.get("sha256"), row.get("bytes")
            if not isinstance(name, str) or not name or Path(name).is_absolute():
                raise DomainRefusal("ADAPTER_OUTPUT_CONTAINMENT_REFUSED", str(name))
            require_sha256(expected_hash, "ADAPTER_ARTIFACT_HASH_REFUSED")
            if not isinstance(expected_bytes, int) or isinstance(expected_bytes, bool) or expected_bytes < 0:
                raise DomainRefusal("ADAPTER_ARTIFACT_BYTES_REFUSED", name)
            candidate = (output_root / name).resolve()
            try:
                candidate.relative_to(output_root)
            except ValueError as exc:
                raise DomainRefusal("ADAPTER_OUTPUT_CONTAINMENT_REFUSED", name) from exc
            if not candidate.is_file():
                raise DomainRefusal("ADAPTER_ARTIFACT_ABSENT", name)
            data = candidate.read_bytes()
            if len(data) != expected_bytes or hashlib.sha256(data).hexdigest() != expected_hash:
                raise DomainRefusal("ADAPTER_ARTIFACT_INTEGRITY_REFUSED", name)
            if expected_hash == result["artifact_sha256"]:
                verified_primary = True
        if not verified_primary:
            raise DomainRefusal("ADAPTER_PRIMARY_ARTIFACT_REFUSED", self.manifest.adapter_id)

    def _project(self, snapshot: dict[str, Any], output_root: Path) -> dict[str, Any]:
        raise NotImplementedError

    def observe(self) -> dict[str, Any]:
        if self._state != "PROJECTED" or self._observation is None:
            raise DomainRefusal("ADAPTER_LIFECYCLE_REFUSED", f"{self._state}:OBSERVE")
        return copy.deepcopy(self._observation)

    def close(self) -> dict[str, Any]:
        if self._state == "CLOSED":
            raise DomainRefusal("ADAPTER_LIFECYCLE_REFUSED", "CLOSED:CLOSE")
        before = self._state
        self._scene = None
        self._state = "CLOSED"
        value = {
            "schema": "mosaic.ui.adapter-close-receipt.v0.1", "adapter_id": self.manifest.adapter_id,
            "previous_state": before, "lifecycle_state": "CLOSED", "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.ADAPTER_CLOSE_RECEIPT.v0.1", value)
        return value


def adapter_lifecycle_witness(
    adapter: DomainAdapter, scene: dict[str, Any], snapshot: dict[str, Any], output_root: Path,
) -> dict[str, Any]:
    if not isinstance(adapter, DomainAdapter):
        raise DomainRefusal("ADAPTER_PROTOCOL_REFUSED", type(adapter).__name__)
    opened = adapter.open(scene)
    projected = adapter.project(snapshot, output_root)
    observed = adapter.observe()
    closed = adapter.close()
    checks = {
        "OPENED": opened["lifecycle_state"] == "OPEN",
        "PROJECTED": projected == observed,
        "CLOSED": closed["lifecycle_state"] == "CLOSED" and adapter.lifecycle_state == "CLOSED",
        "SEMANTIC_STATE_BOUND": projected["semantic_state_root"] == snapshot["semantic_state_root"],
        "AUTHORITY_NONE": all(item["authority_effect"] == "NONE" for item in (opened, projected, closed)),
    }
    value = {
        "schema": "mosaic.ui.adapter-lifecycle-witness.v0.1", "adapter": adapter.manifest.as_dict(),
        "open": opened, "projection": projected, "close": closed, "checks": checks,
        "disposition": "PASS_LOCAL_CANDIDATE" if all(checks.values()) else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
    }
    value["commitment"] = commitment("MOSAIC.UI.ADAPTER_LIFECYCLE_WITNESS.v0.1", value)
    return value


__all__ = [
    "ADAPTER_SDK_SCHEMA", "ADAPTER_STATES", "AdapterManifest", "DomainAdapter",
    "GovernedAdapterSession", "adapter_lifecycle_witness",
]

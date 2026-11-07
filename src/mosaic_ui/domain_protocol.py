"""Shared protocol primitives for optional Mosaic semantic domains.

This module is intentionally engine-neutral.  It defines only negotiation,
validation helpers, and evidence envelopes shared by independently ablatable
domain packages.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import commitment, read_json


DOMAIN_PROTOCOL_SCHEMA = "mosaic.ui.domain-realizer-protocol.v0.1"
SUPPORTED_DOMAIN_PROTOCOLS = (DOMAIN_PROTOCOL_SCHEMA,)
DOMAINS = ("PLAY_2D", "SPATIAL_3D")
DOMAIN_SCHEMA_ROOT = Path(__file__).resolve().parent / "domain_schemas"
DOMAIN_SCHEMA_FILES = {
    "PLAY_2D": "play-scene-v0.1.schema.json",
    "SPATIAL_3D": "spatial-scene-v0.1.schema.json",
}
DOMAIN_DOCUMENT_SCHEMAS = {
    "PLAY_2D": "mosaic.play.scene.v0.1",
    "SPATIAL_3D": "mosaic.spatial.scene.v0.1",
}


class DomainRefusal(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}:{detail}")


def require_exact_mapping(value: Any, keys: set[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise DomainRefusal(code, str(actual))
    return value


def require_identifier(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 128 \
            or not all(character.isalnum() or character in "._-" for character in value):
        raise DomainRefusal(code, str(value))
    return value


def require_int_vector(value: Any, length: int, code: str, *, positive: bool = False) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != length \
            or not all(isinstance(item, int) and not isinstance(item, bool) for item in value):
        raise DomainRefusal(code, str(value))
    result = tuple(value)
    if positive and any(item <= 0 for item in result):
        raise DomainRefusal(code, str(value))
    return result


def require_sha256(value: Any, code: str) -> str:
    if not isinstance(value, str) or len(value) != 64 \
            or any(character not in "0123456789abcdef" for character in value):
        raise DomainRefusal(code, str(value))
    return value


@dataclass(frozen=True)
class DomainRealizerDescriptor:
    realizer_id: str
    domain: str
    protocol: str
    capabilities: tuple[str, ...]
    projections: tuple[str, ...]
    host_effects: tuple[str, ...] = ()
    engine_binding: str = "NONE_EXPERIMENTAL"

    def as_dict(self) -> dict[str, Any]:
        value = {
            "schema": "mosaic.ui.domain-realizer-descriptor.v0.1",
            "realizer_id": require_identifier(self.realizer_id, "DOMAIN_REALIZER_ID_REFUSED"),
            "domain": self.domain,
            "protocol": self.protocol,
            "capabilities": list(self.capabilities),
            "projections": list(self.projections),
            "host_effects": list(self.host_effects),
            "engine_binding": self.engine_binding,
            "authority_effect": "NONE",
        }
        value["commitment"] = commitment("MOSAIC.UI.DOMAIN_REALIZER_DESCRIPTOR.v0.1", value)
        return value


def negotiate_domain_protocol(
    offered: tuple[str, ...] | list[str], descriptor: DomainRealizerDescriptor,
    *, required_capabilities: tuple[str, ...] = (), required_projections: tuple[str, ...] = (),
) -> dict[str, Any]:
    if descriptor.domain not in DOMAINS:
        raise DomainRefusal("DOMAIN_REFUSED", descriptor.domain)
    if not isinstance(offered, (tuple, list)) or not offered \
            or not all(isinstance(item, str) and item for item in offered):
        raise DomainRefusal("DOMAIN_PROTOCOL_OFFER_REFUSED", "INVALID_OFFER")
    if len(set(offered)) != len(offered):
        raise DomainRefusal("DOMAIN_PROTOCOL_OFFER_REFUSED", "DUPLICATE_PROTOCOL")
    selected = next((item for item in offered if item in SUPPORTED_DOMAIN_PROTOCOLS), None)
    if selected is None or descriptor.protocol != selected:
        raise DomainRefusal("DOMAIN_PROTOCOL_NEGOTIATION_REFUSED", ",".join(offered))
    missing_capabilities = sorted(set(required_capabilities) - set(descriptor.capabilities))
    missing_projections = sorted(set(required_projections) - set(descriptor.projections))
    if missing_capabilities:
        raise DomainRefusal("DOMAIN_CAPABILITY_NEGOTIATION_REFUSED", ",".join(missing_capabilities))
    if missing_projections:
        raise DomainRefusal("DOMAIN_PROJECTION_NEGOTIATION_REFUSED", ",".join(missing_projections))
    value = {
        "schema": "mosaic.ui.domain-protocol-negotiation.v0.1",
        "domain": descriptor.domain,
        "realizer_id": descriptor.realizer_id,
        "offered": list(offered),
        "selected": selected,
        "required_capabilities": list(required_capabilities),
        "required_projections": list(required_projections),
        "disposition": "PASS_LOCAL_CANDIDATE",
        "authority_effect": "NONE",
    }
    value["commitment"] = commitment("MOSAIC.UI.DOMAIN_PROTOCOL_NEGOTIATION.v0.1", value)
    return value


def semantic_state_root(domain: str, scene_root: str, state: dict[str, Any]) -> str:
    if domain not in DOMAINS:
        raise DomainRefusal("DOMAIN_REFUSED", domain)
    require_sha256(scene_root, "DOMAIN_SCENE_ROOT_REFUSED")
    return commitment(f"MOSAIC.UI.{domain}.SEMANTIC_STATE.v0.1", {
        "domain": domain, "scene_root": scene_root, "state": state,
    })


def domain_schema_registry(
    root: Path = DOMAIN_SCHEMA_ROOT, domains: tuple[str, ...] = DOMAINS,
) -> dict[str, Any]:
    if not domains or len(domains) != len(set(domains)) or not set(domains) <= set(DOMAINS):
        raise DomainRefusal("DOMAIN_SCHEMA_SCOPE_REFUSED", repr(domains))
    schemas: dict[str, Any] = {}
    for domain in domains:
        filename = DOMAIN_SCHEMA_FILES[domain]
        value = read_json(root / filename)
        required = value.get("required")
        properties = value.get("properties")
        document_schema = DOMAIN_DOCUMENT_SCHEMAS[domain]
        if value.get("$schema") != "https://json-schema.org/draft/2020-12/schema" \
                or value.get("type") != "object" or value.get("additionalProperties") is not False \
                or not isinstance(required, list) or len(required) != len(set(required)) \
                or not isinstance(properties, dict) or set(required) != set(properties) \
                or properties.get("schema", {}).get("const") != document_schema \
                or properties.get("authority_effect", {}).get("const") != "NONE" \
                or value.get("x-mosaic-compatibility-policy") != "EXACT_SCHEMA_ID":
            raise DomainRefusal("DOMAIN_SCHEMA_CONTRACT_REFUSED", domain)
        schemas[domain] = {
            "file": filename, "document_schema": document_schema,
            "required": required, "sha256": commitment("MOSAIC.UI.DOMAIN_SCHEMA_FILE.v0.1", value),
        }
    compatibility = read_json(root / "compatibility-v0.1.json")
    if compatibility.get("schema") != "mosaic.ui.domain-schema-compatibility.v0.1" \
            or compatibility.get("authority_effect") != "NONE" \
            or compatibility.get("forward_compatibility") != "REFUSE_UNKNOWN_SCHEMA" \
            or set(compatibility.get("domains", {})) != set(DOMAINS):
        raise DomainRefusal("DOMAIN_SCHEMA_COMPATIBILITY_REFUSED")
    for domain in domains:
        document_schema = DOMAIN_DOCUMENT_SCHEMAS[domain]
        policy = compatibility["domains"][domain]
        if policy.get("writer_schema") != document_schema \
                or policy.get("accepted_document_schemas") != [document_schema] \
                or policy.get("migration") != "EXPLICIT_ADAPTER_REQUIRED_FOR_ANY_OTHER_SCHEMA":
            raise DomainRefusal("DOMAIN_SCHEMA_COMPATIBILITY_REFUSED", domain)
    value = {
        "schema": "mosaic.ui.domain-schema-registry.v0.1", "domains": list(domains),
        "schemas": schemas, "compatibility": compatibility,
        "disposition": "PASS_LOCAL_CANDIDATE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
    }
    value["commitment"] = commitment("MOSAIC.UI.DOMAIN_SCHEMA_REGISTRY.v0.1", value)
    return value


__all__ = [
    "DOMAIN_DOCUMENT_SCHEMAS", "DOMAIN_PROTOCOL_SCHEMA", "DOMAIN_SCHEMA_FILES", "DOMAIN_SCHEMA_ROOT",
    "DOMAINS", "DomainRealizerDescriptor", "DomainRefusal", "domain_schema_registry",
    "SUPPORTED_DOMAIN_PROTOCOLS", "negotiate_domain_protocol", "require_exact_mapping",
    "require_identifier", "require_int_vector", "require_sha256", "semantic_state_root",
]

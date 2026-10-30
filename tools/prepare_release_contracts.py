#!/usr/bin/env python3
"""Create stable v0.1 contracts from declared values."""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import root
from ucm.system import CAPABILITY_DEFINITIONS, CAPABILITY_PAYLOAD_FIELDS, SYSTEMS, capability_registry


def write(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")


def seal(body: dict) -> dict:
    return {**body, "root": root(body)}


def capability_document() -> str:
    rows = [
        "# Capability surfaces",
        "",
        "This document is generated from the same definitions as `python tools/ucm.py capabilities`.",
        "",
        "| Surface | System | Availability | Effect | Public route | Payload fields | Request schema | Result schema |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, system, effect, availability, route, request, result in CAPABILITY_DEFINITIONS:
        payload = ", ".join(f"`{field}`" for field in CAPABILITY_PAYLOAD_FIELDS[name]) or "_(empty)_"
        rows.append(f"| `{name}` | {system} | {availability} | {effect} | `{route}` | {payload} | `{request}` | `{result}` |")
    rows.extend([
        "",
        "`ucm.invoke` accepts a `mosaic.ucm.request.v0.1` envelope containing `surface`, `payload`, and `request_id`. The machine registry supplies exact request/result schema names. A separate-stage surface refuses through the pure dispatcher rather than silently performing an effect.",
        "",
        "Compatibility modules may expose additional functions. They are not stable public promises unless this generated registry names a route.",
        "",
    ])
    return "\n".join(rows)


def main() -> int:
    boundary = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE", "real_a5": False, "g0": "CLOSED"}
    registry = seal({
        "schema": "mosaic.ucm.system-registry.v0.1",
        "product": "Universal Constitutional Machine",
        "short_name": "UCM",
        "version": "v0.1",
        "publisher": "Ableman Mosaic",
        "copyright": "Copyright 2026 Ableman Mosaic",
        "license": "Apache-2.0",
        "systems": [{"id": sid, "name": name, "role": role} for sid, name, role in SYSTEMS],
        "capability_registry_root": capability_registry()["root"],
        "compatibility_packages": ["uclop", "uclsh"],
        **boundary,
    })
    ceiling = seal({
        "schema": "mosaic.ucm.authority-ceiling.v0.1",
        "version": "v0.1",
        "identities": "UNBOUND",
        "deployment": "NOT_AUTHORIZED",
        "network": "NOT_AUTHORIZED",
        "self_admission": False,
        "release_authority": "NONE",
        **boundary,
    })
    rsc = {
        "schema": "mosaic.realization-space-contract.v0.1",
        "contract_id": "UCM.PORTABLE_AGENT_ENVIRONMENT",
        "contract_version": "0.1.0",
        "description": "Unbound portable agent environment realization space.",
        "subject": {
            "subject_id": "UCM.PORTABLE_AGENT_ENVIRONMENT",
            "subject_schema": "mosaic.ucm.portable-agent-environment.v0.1",
            "authority_owner": "UNBOUND",
            "source_roots": ["sha256:0000000000000000000000000000000000000000000000000000000000000000"],
            "preserved_identity": ["UCM_CONTRACTS", "UCM_CAPABILITIES", "AUTHORITY_CEILING"],
            "forbidden_overrides": ["IDENTITY", "AUTHORITY", "NETWORK_AUTHORITY", "PRODUCTION_ADMISSION"],
        },
        "possibility": {
            "intended_variation": ["processor architecture", "memory capacity", "local agent hosting", "bootstrap transport"],
            "excluded_claims": ["target admission", "network permission", "production readiness", "real identity binding"],
        },
        "axes": [
            {"id": "TARGET_ISA", "label": "Target instruction set", "value_type": "ENUM", "domain": {"values": ["ARM64", "RISCV64", "X64"]}, "default": "X64", "ownership": "AUTHORIAL", "mutability": "INSTANCE", "continuity": "DISCRETE", "authority_effect": "NONE"},
            {"id": "MEMORY_MIB", "label": "Memory capacity", "value_type": "INTEGER", "domain": {"minimum": 128, "maximum": 1048576}, "default": 4096, "unit": "MiB", "ownership": "AUTHORIAL", "mutability": "INSTANCE", "continuity": "DISCRETE", "authority_effect": "NONE"},
            {"id": "SELF_HOSTED_AGENT", "label": "Self-hosted agent environment", "value_type": "BOOLEAN", "domain": {}, "default": False, "ownership": "AUTHORIAL", "mutability": "INSTANCE", "continuity": "DISCRETE", "authority_effect": "NONE"},
            {"id": "NETWORK_BOOTSTRAP", "label": "Bootstrap transport", "value_type": "ENUM", "domain": {"values": ["DISABLED", "ETHERNET_LOCAL_ONLY"]}, "default": "DISABLED", "ownership": "AUTHORIAL", "mutability": "INSTANCE", "continuity": "DISCRETE", "authority_effect": "NONE"},
        ],
        "constraints": [
            {
                "id": "MEMORY_WITHIN_PORTABLE_BOUND",
                "kind": "BUDGET",
                "severity": "HARD",
                "operator": "RANGE",
                "terms": {"axis": "MEMORY_MIB", "minimum": 128, "maximum": 1048576},
                "explanation": "Memory must remain within the declared portable target envelope.",
                "refusal_code": "PORTABLE_MEMORY_BOUND_REFUSED",
            },
            {
                "id": "ETHERNET_PRECEDES_SELF_HOSTING",
                "kind": "DEPENDENCY",
                "severity": "HARD",
                "operator": "REQUIRES",
                "terms": {
                    "if": {"axis": "NETWORK_BOOTSTRAP", "equals": "ETHERNET_LOCAL_ONLY"},
                    "then": {"axis": "SELF_HOSTED_AGENT", "equals": False},
                },
                "explanation": "The bootstrap profile remains externally driven until a later governed self-hosting transition.",
                "refusal_code": "BOOTSTRAP_SELF_HOSTING_ORDER_REFUSED",
            },
        ],
        "objectives": [{"metric_id": "ARTIFACT_BYTES", "unit": "bytes", "direction": "MINIMIZE", "priority": 100, "measurement": "exact packaged bytes", "scope": "PORTABLE"}],
        "capabilities": ["ENUMERATE", "VALIDATE", "NORMALIZE", "SELECT", "LOWER", "COMPARE", "EXPLAIN", "RECEIPT", "PROJECT", "TRACE"],
        "selection": {
            "default_policy": "EXACT_DEFAULTS",
            "policies": ["EXACT_DEFAULTS", "OBJECTIVE_PRIORITY"],
            "seed_required_for_non_unique": False,
            "fallback_policy": "REFUSE",
        },
        "lowering": {
            "targets": [{"target_id": "UNBOUND_COMPUTE_TARGET", "runtime_family": "UNBOUND", "adapter_version": "0.1.0", "required_capabilities": [], "optional_capabilities": [], "preservation_criteria": ["UCM_CONTRACTS", "AUTHORITY_CEILING"], "known_losses": [], "fallbacks": []}],
            "allowed_results": ["EXACT", "BOUNDED", "FALLBACK", "LOSSY", "REFUSED"],
        },
        "evidence": {"required_roots": ["CONTRACT", "SUBJECT", "CONFIGURATION", "IMPLEMENTATION", "OUTPUT"], "required_fields": ["standing", "authority_effect"], "non_claims": ["NO_TARGET_ADMISSION", "NO_NETWORK_AUTHORITY", "NO_PRODUCTION_AUTHORITY"]},
        "authority": {"standing": "INFORMATION_ONLY", "authority_effect": "NONE", "self_admission": False, "release_gate": False, "track_a_dependency": "NONE", "claim_boundary": "UNBOUND_CONFIGURATION_ONLY"},
    }
    configuration = {"TARGET_ISA": "X64", "MEMORY_MIB": 4096, "SELF_HOSTED_AGENT": False, "NETWORK_BOOTSTRAP": "DISABLED"}
    write(ROOT / "spec" / "ucm-system-registry.json", registry)
    write(ROOT / "spec" / "ucm-authority-ceiling.json", ceiling)
    write(ROOT / "examples" / "realization" / "portable-agent-environment.json", rsc)
    write(ROOT / "examples" / "realization" / "portable-agent-environment.configuration.json", configuration)
    (ROOT / "docs" / "CAPABILITY-SURFACES.md").write_text(capability_document(), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


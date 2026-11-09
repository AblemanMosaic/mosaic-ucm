"""Generate checked-in pure-data maturity assets from the implementation."""
from __future__ import annotations

import base64
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root, strict_loads
from ucm.agent_adapter import agent_loop_contract
from ucm.authoring import validate_policy_pack
from ucm.governance import (SUPPORTED_ENVIRONMENT_VARIABLES, abi_stability_table,
                            shell_completion, time_policy)
from ucm.profiles import profile_registry, validate_profile_selection
from ucm.system import CAPABILITY_PAYLOAD_FIELDS, capability_registry


BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")


def policy_pack(pack_id: str, requirements: list[dict]) -> dict:
    body = {"schema": "mosaic.ucm.amcas-policy-pack.v0.1",
            "pack_id": pack_id, "version": "0.1.0", "requirements": requirements}
    return validate_policy_pack({**body, "pack_root": root(body)})


def build() -> None:
    write(ROOT / "spec" / "ABI-STABILITY.json", abi_stability_table())
    write(ROOT / "spec" / "TIME-AND-FRESHNESS-POLICY.json", time_policy())
    write(ROOT / "spec" / "AGENT-LOOP-CONTRACT.json", agent_loop_contract())
    env_body = {"schema": "mosaic.ucm.environment-policy.v0.1",
                "variables": SUPPORTED_ENVIRONMENT_VARIABLES,
                "unknown_policy": "WARN_DEFAULT_REFUSE_STRICT", **BOUNDARY}
    write(ROOT / "spec" / "ENVIRONMENT-POLICY.json",
          {**env_body, "policy_root": root(env_body)})

    registry = profile_registry()
    write(ROOT / "spec" / "product-profiles" / "PROFILE-REGISTRY.json", registry)
    for profile in registry["profiles"]:
        selection = {"schema": "mosaic.ucm.product-profile-selection.v0.1",
                     "profile_id": profile["profile_id"],
                     "capability_registry_root": registry["capability_registry_root"]}
        write(ROOT / "spec" / "product-profiles" /
              f"{profile['profile_id']}-PROFILE.json",
              validate_profile_selection(selection))

    packs = [
        policy_pack("NO_AUTHORITY_V1", [{
            "id": "NO_AUTHORITY", "kind": "ACCEPTANCE",
            "statement": "No contract, receipt, or projection grants authority.",
            "verifier": "AMCAS_AUTHORITY_CEILING_V1", "evidence_required": True,
            "applicability": "REQUIRED",
        }]),
        policy_pack("SOURCE_BOUND_V1", [{
            "id": "SOURCE_BOUND", "kind": "EVIDENCE",
            "statement": "Every result binds the exact subject source root.",
            "verifier": "AMCAS_SOURCE_BINDING_V1", "evidence_required": True,
            "applicability": "REQUIRED",
        }]),
        policy_pack("OFFLINE_PORTABLE_V1", [{
            "id": "OFFLINE_PORTABLE", "kind": "PORTABILITY",
            "statement": "The verification envelope closes without network access.",
            "verifier": "AMCAS_OFFLINE_CLOSURE_V1", "evidence_required": True,
            "applicability": "REQUIRED",
        }]),
    ]
    for pack in packs:
        write(ROOT / "policy-packs" / f"{pack['pack_id'].replace('_V1', '')}-v0.1.json", pack)

    raw_inputs = [
        b'{"b":2,"a":1}',
        b'{\r\n  "a": 1,\r\n  "b": 2\r\n}',
        '{"text":"café","integer":9223372036854775807}'.encode("utf-8"),
        b'{"empty_list":[],"empty_map":{},"null":null}',
        b'{"path":"a/b/c","omitted_is_not_empty":""}',
    ]
    vectors = []
    for index, raw in enumerate(raw_inputs, 1):
        value = strict_loads(raw)
        output = canonical_bytes(value)
        vectors.append({"id": f"CANONICAL-{index:02}",
                        "input_base64": base64.b64encode(raw).decode("ascii"),
                        "canonical_base64": base64.b64encode(output).decode("ascii"),
                        "canonical_sha256": root(value)})
    vector_body = {"schema": "mosaic.ucm.canonical-json-golden-vectors.v0.1",
                   "normalization_policy": "UNICODE_CODEPOINTS_PRESERVED_NO_IMPLICIT_NFC",
                   "path_policy": "PATH_STRINGS_ARE_DATA_UNTIL_A_PATH_SCHEMA_VALIDATES_THEM",
                   "vectors": vectors, **BOUNDARY}
    write(ROOT / "conformance" / "CANONICAL-JSON-GOLDEN-VECTORS-v0.1.json",
          {**vector_body, "vector_set_root": root(vector_body)})

    for shell in ("bash", "zsh", "fish", "powershell"):
        completion = shell_completion(shell)
        suffix = {"bash": "bash", "zsh": "zsh", "fish": "fish",
                  "powershell": "ps1"}[shell]
        path = ROOT / "completions" / f"ucm.{suffix}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(completion["script"], encoding="utf-8", newline="\n")
        write(ROOT / "completions" / f"ucm.{suffix}.json", completion)

    capabilities = capability_registry()
    guide = ["# Active surface guide", "",
             "Each entry supplies the fixed secondary documentation layer. Exact schemas and roots remain authoritative.", ""]
    for surface in capabilities["surfaces"]:
        fields = surface["payload_required"]
        field_text = ", ".join(f"`{field}`" for field in fields) if fields else "_(empty)_"
        guide.extend([
            f"## `{surface['name']}`", "",
            f"**When to call.** Use this {surface['system'].replace('_', ' ').lower()} surface when the request matches `{surface['request_schema']}` and `{surface['effect_scope']}` is within the selected profile.", "",
            f"**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `{surface['request_schema']}` data, or a separately staged effect invoked through a pure route.", "",
            f"**Minimal request.** `{{\"schema\":\"mosaic.ucm.request.v0.2\",\"surface\":\"{surface['name']}\",\"payload\":{{{','.join(json.dumps(field)+':\"…\"' for field in fields)}}},\"profile_selection\":{{\"…\":\"pinned profile\"}},\"request_id\":\"…\"}}`", "",
            "**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.", "",
        ])
    (ROOT / "docs" / "ACTIVE-SURFACE-GUIDE.md").write_text("\n".join(guide), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    build()

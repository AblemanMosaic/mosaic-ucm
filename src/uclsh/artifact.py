from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import root, sha256_bytes
from .errors import require
from .module import check_module


def compiler_profile(document: dict[str, Any], meta_kernel_root: str) -> dict[str, Any]:
    contract = document["compiler_contract"]
    return {
        "schema": "ucl.selfhost.compiler_profile.v1",
        "language_profile": "UCL-SH-1",
        "meta_kernel_root": meta_kernel_root,
        "grammar_root": root(contract["grammar"]),
        "module_schema_root": root(contract["module_schema"]),
        "instruction_signatures_root": root(contract["instruction_signatures"]),
        "pass_graph_root": root(contract["pass_graph"]),
        "effect": "NONE",
    }


def build_artifact_host(source_text: str, document: dict[str, Any], meta_kernel_root: str, primitive_names: set[str]) -> dict[str, Any]:
    check_module(document, primitive_names)
    profile = compiler_profile(document, meta_kernel_root)
    interface = [
        {
            "id": function["id"],
            "params": function["params"],
            "returns": function["returns"],
            "effect": function["effect"],
        }
        for function in document["functions"]
    ]
    body = {
        "schema": "ucl.selfhost.compiled_module.v1",
        "source_root": sha256_bytes(source_text.encode("utf-8")),
        "semantic_root": root(document),
        "compiler_profile_root": root(profile),
        "meta_kernel_root": meta_kernel_root,
        "module": deepcopy(document),
        "interface": interface,
        "trusted_primitives": sorted(primitive_names),
        "effect": "NONE",
        "standing": "INFORMATION_ONLY",
    }
    return {"body": body, "root": root(body)}


def verify_artifact_host(artifact: dict[str, Any], expected_meta_kernel_root: str, primitive_names: set[str]) -> bool:
    require(type(artifact) is dict and set(artifact) == {"body", "root"}, "ARTIFACT_SHAPE_INVALID")
    require(artifact["root"] == root(artifact["body"]), "ARTIFACT_ROOT_MISMATCH")
    body = artifact["body"]
    require(type(body) is dict, "ARTIFACT_BODY_SHAPE_INVALID")
    expected_fields = {"schema", "source_root", "semantic_root", "compiler_profile_root", "meta_kernel_root", "module", "interface", "trusted_primitives", "effect", "standing"}
    require(set(body) == expected_fields, "ARTIFACT_BODY_SHAPE_INVALID")
    require(body["schema"] == "ucl.selfhost.compiled_module.v1", "ARTIFACT_SCHEMA_INVALID")
    # Validate the complete module shape before any profile lookup. Malformed
    # artifacts must fail with a typed language refusal rather than KeyError or
    # TypeError from compiler_profile.
    check_module(body["module"], primitive_names)
    require(body["semantic_root"] == root(body["module"]), "ARTIFACT_SEMANTIC_ROOT_MISMATCH")
    require(body["meta_kernel_root"] == expected_meta_kernel_root, "ARTIFACT_KERNEL_ROOT_MISMATCH")
    require(body["compiler_profile_root"] == root(compiler_profile(body["module"], expected_meta_kernel_root)), "ARTIFACT_PROFILE_ROOT_MISMATCH")
    require(body["trusted_primitives"] == sorted(primitive_names), "ARTIFACT_PRIMITIVES_MISMATCH")
    require(body["effect"] == "NONE" and body["standing"] == "INFORMATION_ONLY", "ARTIFACT_EFFECT_OR_STANDING_FORBIDDEN")
    expected_interface = [
        {"id": item["id"], "params": item["params"], "returns": item["returns"], "effect": item["effect"]}
        for item in body["module"]["functions"]
    ]
    require(body["interface"] == expected_interface, "ARTIFACT_INTERFACE_MISMATCH")
    return True


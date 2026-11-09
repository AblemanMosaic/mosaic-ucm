from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import canonical_bytes, root, sha256_bytes
from .artifact import verify_artifact_host
from .compiler import compile_module_text
from .diverse_seed import compile_module_text_diverse
from .errors import require
from .kernel import Kernel
from .vm import Machine


def bootstrap_compiler(source: bytes | str) -> dict[str, Any]:
    kernel = Kernel()
    source_text = source.decode("utf-8", errors="strict") if type(source) is bytes else source
    source_bytes = source_text.encode("utf-8")
    stage1 = compile_module_text(source_text, kernel=kernel)
    machine = Machine(stage1, kernel)
    stage2 = machine.call(stage1["body"]["module"]["entrypoint"], [source_text])
    require(verify_artifact_host(stage2, kernel.descriptor["root"], kernel.primitive_names) is True, "STAGE2_INVALID")
    diverse = compile_module_text_diverse(source_text)
    stage1_bytes = canonical_bytes(stage1)
    stage2_bytes = canonical_bytes(stage2)
    diverse_bytes = canonical_bytes(diverse)
    require(stage1_bytes == stage2_bytes, "BOOTSTRAP_STAGE_DIVERGENCE")
    require(stage1_bytes == diverse_bytes, "BOOTSTRAP_DIVERSE_SEED_DIVERGENCE")
    body = {
        "schema": "ucl.selfhost.bootstrap_result.v1",
        "source_root": sha256_bytes(source_bytes),
        "stage0": {
            "implementation": "CPYTHON_SEED_A",
            "meta_kernel_root": kernel.descriptor["root"],
            "output_root": stage1["root"],
        },
        "stage1": {
            "implementation": "UCL_SH_COMPILER_ON_META_KERNEL",
            "compiler_root": stage1["root"],
            "output_root": stage2["root"],
            "vm_steps": machine.steps,
        },
        "stage2": {
            "implementation": "UCL_SH_SELF_REBUILD",
            "compiler_root": stage2["root"],
            "byte_identical_to_stage1": True,
        },
        "diverse_seed": {
            "implementation": "CPYTHON_SEED_B_STRUCTURALLY_DISTINCT",
            "output_root": diverse["root"],
            "byte_identical_to_stage1": True,
            "shared_trust": ["CPYTHON_RUNTIME", "UCL_SH_CANONICAL_VALUE_KERNEL", "SHA256"],
        },
        "trusted_base": {
            "meta_kernel": kernel.descriptor,
            "source_encoding": "UTF8_NO_BOM",
            "canonicalization": "JCS-I64-EXACT-UTF8-V1",
            "hash": "SHA256",
            "host_seed": "CPYTHON_3",
        },
        "self_hosting_scope": "UCL_SH_DECLARATIVE_COMPILER_OVER_DECLARED_META_KERNEL",
        "general_soundness_claimed": False,
        "effect": "NONE",
        "standing": "INFORMATION_ONLY",
    }
    result = {"body": body, "root": root(body), "stage1_artifact": deepcopy(stage1)}
    return result


def bootstrap_corpus(compiler_source: bytes | str, modules: dict[str, bytes | str]) -> dict[str, Any]:
    bootstrap = bootstrap_compiler(compiler_source)
    stage1 = bootstrap["stage1_artifact"]
    machine = Machine(stage1)
    rows: list[dict[str, Any]] = []
    for module_id in sorted(modules):
        source = modules[module_id]
        text = source.decode("utf-8", errors="strict") if type(source) is bytes else source
        seed_a = compile_module_text(text)
        self_hosted = machine.call("compile_source", [text])
        seed_b = compile_module_text_diverse(text)
        require(canonical_bytes(seed_a) == canonical_bytes(self_hosted), "CORPUS_SELF_HOST_DIVERGENCE", f"$.modules.{module_id}")
        require(canonical_bytes(seed_a) == canonical_bytes(seed_b), "CORPUS_DIVERSE_SEED_DIVERGENCE", f"$.modules.{module_id}")
        rows.append(
            {
                "module_id": module_id,
                "source_root": sha256_bytes(text.encode("utf-8")),
                "artifact_root": seed_a["root"],
                "seed_a_equal": True,
                "self_hosted_equal": True,
                "seed_b_equal": True,
            }
        )
    body = {
        "schema": "ucl.selfhost.bootstrap_corpus.v1",
        "compiler_bootstrap_root": bootstrap["root"],
        "compiler_root": stage1["root"],
        "modules": rows,
        "all_converged": True,
        "effect": "NONE",
        "standing": "INFORMATION_ONLY",
    }
    return {"body": body, "root": root(body), "bootstrap": bootstrap}


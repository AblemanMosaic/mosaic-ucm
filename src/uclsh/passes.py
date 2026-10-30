from __future__ import annotations

from copy import deepcopy
from importlib import resources
from typing import Any

from .canonical import root, sha256_bytes, strict_loads
from .artifact import verify_artifact_host
from .compiler import compile_module_text
from .errors import require
from .evidence import append_receipt, verify_ledger
from .kernel import Kernel
from .vm import Machine
from .module import EXPECTED_COMPILER_PASS_GRAPH

EXPECTED_PASS_GRAPH = EXPECTED_COMPILER_PASS_GRAPH
EXPECTED_PASS_GRAPH_ROOT = root(EXPECTED_PASS_GRAPH)
SPEC_RESOURCE = "resources/COMPILER-PASS-GRAPH.json"


def _pass_graph_spec() -> dict[str, Any]:
    """Load the pass contract from the installed ``uclsh`` package.

    Runtime resources must not depend on a repository layout or current working
    directory.  Missing or unreadable package data is a typed language-system
    refusal rather than a host ``FileNotFoundError``.
    """
    try:
        raw = resources.files("uclsh").joinpath(SPEC_RESOURCE).read_bytes()
    except (FileNotFoundError, ModuleNotFoundError, OSError) as error:
        require(False, "COMPILER_PIN_RESOURCE_MISSING", detail=type(error).__name__)
    return strict_loads(raw)


def expected_compiler_semantic_root() -> str:
    spec = _pass_graph_spec()
    require(
        type(spec) is dict
        and set(spec) == {"schema", "compiler_module_root", "passes", "implementation", "effect"}
        and spec["schema"] == "ucl.selfhost.compiler_pass_graph.v1"
        and spec["passes"] == EXPECTED_PASS_GRAPH
        and spec["implementation"] == "CALLABLE_UCL_FUNCTIONS"
        and spec["effect"] == "NONE",
        "COMPILER_PIN_SPEC_INVALID",
    )
    return spec["compiler_module_root"]


def build_pass_workflow(compiler_artifact: dict[str, Any], source_text: str) -> dict[str, Any]:
    kernel = Kernel()
    verify_artifact_host(compiler_artifact, kernel.descriptor["root"], kernel.primitive_names)
    compiler_semantic_root = expected_compiler_semantic_root()
    require(compiler_artifact["body"]["semantic_root"] == compiler_semantic_root, "COMPILER_MODULE_PIN_MISMATCH")
    graph = compiler_artifact["body"]["module"]["compiler_contract"]["pass_graph"]
    require(root(graph) == EXPECTED_PASS_GRAPH_ROOT and graph == EXPECTED_PASS_GRAPH, "PASS_GRAPH_PIN_MISMATCH")
    body = {
        "schema": "ucl.selfhost.compiler_workflow.v1",
        "compiler_root": compiler_artifact["root"],
        "compiler_semantic_root": compiler_semantic_root,
        "source_root": sha256_bytes(source_text.encode("utf-8")),
        "meta_kernel_root": kernel.descriptor["root"],
        "passes": deepcopy(graph),
        "edges": [{"from": graph[index]["id"], "to": graph[index + 1]["id"]} for index in range(len(graph) - 1)],
        "terminal_contract": {
            "requires": [item["output_slot"] for item in graph],
            "effect": "NONE",
            "standing": "INFORMATION_ONLY",
        },
    }
    return {"body": body, "root": root(body)}


def execute_pass_workflow(
    compiler_artifact: dict[str, Any],
    source_text: str,
    key_hex: str,
    *,
    fail_pass: str | None = None,
) -> dict[str, Any]:
    kernel = Kernel()
    workflow = build_pass_workflow(compiler_artifact, source_text)
    machine = Machine(compiler_artifact, kernel)
    artifacts: dict[str, Any] = {"source_text": source_text}
    ledger: list[dict[str, Any]] = []
    stopped = False
    for item in workflow["body"]["passes"]:
        if stopped:
            break
        pass_id = item["id"]
        for required in item["requires"]:
            require(required in artifacts, "PASS_REQUIRED_ARTIFACT_MISSING", f"$.passes.{pass_id}", required)
        inputs = [artifacts[name] for name in item["input_slots"]]
        input_roots = [sha256_bytes(value.encode("utf-8")) if type(value) is str else root(value) for value in inputs]
        if fail_pass == pass_id:
            output = {
                "schema": "ucl.selfhost.pass_refusal.v1",
                "pass_id": pass_id,
                "code": "INJECTED_TEST_FAILURE",
                "effect": "NONE",
                "standing": "INFORMATION_ONLY",
            }
            artifacts[item["output_slot"]] = output
            append_receipt(ledger, workflow_root=workflow["root"], stage_id=pass_id, stage=item["kind"], event="STAGE_REFUSED", input_roots=input_roots, output=output, key_hex=key_hex)
            stopped = True
            continue
        output = machine.call(item["callable"], inputs)
        artifacts[item["output_slot"]] = output
        append_receipt(ledger, workflow_root=workflow["root"], stage_id=pass_id, stage=item["kind"], event="STAGE_COMPLETE", input_roots=input_roots, output=output, key_hex=key_hex)

    anchor = ledger[-1]["entry_root"] if ledger else "GENESIS"
    verification = verify_ledger(ledger, workflow_root=workflow["root"], key_hex=key_hex, expected_count=len(ledger), expected_anchor=anchor)
    complete = len(ledger) == len(workflow["body"]["passes"]) and all(entry["body"]["event"] == "STAGE_COMPLETE" for entry in ledger)
    if complete:
        require(artifacts["verification"] is True, "TERMINAL_VERIFICATION_FALSE")
        require(artifacts["compiled_artifact"] == compile_module_text(source_text), "PASS_PIPELINE_SEED_DISAGREEMENT")
    body = {
        "schema": "ucl.selfhost.pass_run.v1",
        "workflow": workflow,
        "artifacts": artifacts,
        "ledger": ledger,
        "ledger_verification": verification,
        "terminal": {
            "status": "COMPLETE" if complete else "REFUSED",
            "completed_passes": [entry["body"]["stage_id"] for entry in ledger if entry["body"]["event"] == "STAGE_COMPLETE"],
            "effect": "NONE",
            "standing": "INFORMATION_ONLY",
        },
    }
    return {"body": body, "root": root(body)}


def verify_pass_run(run: dict[str, Any], key_hex: str, *, expected_count: int, expected_anchor: str) -> dict[str, Any]:
    require(type(run) is dict and run.get("root") == root(run.get("body")), "PASS_RUN_ROOT_MISMATCH")
    body = run["body"]
    workflow = body["workflow"]
    require(workflow["root"] == root(workflow["body"]), "PASS_WORKFLOW_ROOT_MISMATCH")
    require(workflow["body"]["compiler_semantic_root"] == expected_compiler_semantic_root(), "COMPILER_MODULE_PIN_MISMATCH")
    ledger = body["ledger"]
    require(workflow["body"]["passes"] == EXPECTED_PASS_GRAPH, "PASS_GRAPH_PIN_MISMATCH")
    verification = verify_ledger(ledger, workflow_root=workflow["root"], key_hex=key_hex, expected_count=expected_count, expected_anchor=expected_anchor)
    require(verification == body["ledger_verification"], "PASS_LEDGER_STORED_VERIFICATION_MISMATCH")
    for entry in ledger:
        pass_contract = next(item for item in workflow["body"]["passes"] if item["id"] == entry["body"]["stage_id"])
        output = body["artifacts"][pass_contract["output_slot"]]
        require(entry["body"]["output_root"] == root(output), "PASS_OUTPUT_ROOT_MISMATCH", f"$.artifacts.{pass_contract['output_slot']}")
    complete = len(ledger) == len(EXPECTED_PASS_GRAPH) and all(entry["body"]["event"] == "STAGE_COMPLETE" for entry in ledger)
    expected_status = "COMPLETE" if complete else "REFUSED"
    expected_completed = [entry["body"]["stage_id"] for entry in ledger if entry["body"]["event"] == "STAGE_COMPLETE"]
    require(body["terminal"]["status"] == expected_status, "PASS_TERMINAL_STATUS_MISMATCH")
    require(body["terminal"]["completed_passes"] == expected_completed, "PASS_COMPLETED_SET_MISMATCH")
    return verification


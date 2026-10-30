from __future__ import annotations

import hashlib
import importlib
import json
import pathlib
import sys
from copy import deepcopy
from typing import Any

from .authority import AuthorityState, PAIR_DECISION_DOMAIN, make_authority_genesis, verify_pair_attestation
from .bootstrap import bootstrap_corpus
from .canonical import root, sha256_bytes, strict_loads
from .compiler import compile_module_text
from .errors import require
from .evidence import FederationExporter, FederationInbox, append_receipt, key_root, make_capsule, make_federation_genesis, verify_capsule, verify_ledger, verify_signed
from .passes import execute_pass_workflow, verify_pass_run
from .visualize import derive_flow


VERTICAL_STAGES = (
    ("V01", "VERIFY_PREDECESSOR", "FOUNDATION"),
    ("V02", "ROOT_HUMAN_SOURCE", "H3"),
    ("V03", "STAGE0_BUILD", "H4"),
    ("V04", "STAGE1_STAGE2_CONVERGENCE", "H4B"),
    ("V05", "DIVERSE_SEED_CONVERGENCE", "H4B"),
    ("V06", "EXECUTE_COMPILER_PASS_GRAPH", "H4"),
    ("V07", "VERIFY_EXACT_PAIR_AUTHORITY", "H2"),
    ("V08", "EXECUTE_INFORMATION_ONLY_PROGRAM", "H2-H5"),
    ("V09", "VERIFY_PROOF_AND_RECEIPT_CUSTODY", "H4"),
    ("V10", "BUILD_CONTINUITY_CAPSULE", "H4B"),
    ("V11", "FEDERATE_OFFLINE_DOSSIER", "H5"),
    ("V12", "TERMINAL_CLOSURE", "H2-H5"),
)
FIXTURE_GOVERNOR_KEY = "44" * 32
PINNED_PAIR_DECISION_RECORD_ROOT = "1686ae60c723c4f3fa524bf956e0ea54354719d1ee2207f7fc39a1bb188b9634"


def digest(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_predecessor(core: pathlib.Path) -> dict[str, Any]:
    manifest_path = core / "CORE-MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest.get("closed_world") is True, "PREDECESSOR_MANIFEST_NOT_CLOSED")
    expected = {item["path"]: item for item in manifest["files"]}
    actual = {
        path.relative_to(core).as_posix(): path
        for path in core.rglob("*")
        if path.is_file() and path.name != "CORE-MANIFEST.json" and "__pycache__" not in path.parts
    }
    require(set(actual) == set(expected), "PREDECESSOR_FILE_SET_MISMATCH")
    for name, path in actual.items():
        require(path.stat().st_size == expected[name]["size"], "PREDECESSOR_SIZE_MISMATCH", name)
        require(digest(path) == expected[name]["sha256"], "PREDECESSOR_HASH_MISMATCH", name)
    body = {
        "schema": "ucl.selfhost.predecessor_verification.v1",
        "manifest_root": sha256_bytes(manifest_path.read_bytes()),
        "file_count": len(actual),
        "c1_core_archive_sha256": "d053df6f1f3771ffa9f20fdf4f1b60b180c87f28726bfe4732201ff838de4b5f",
        "status": "VERIFIED",
        "effect": "NONE",
        "standing": "INFORMATION_ONLY",
    }
    return {"body": body, "root": root(body)}


def _legacy_execution(core: pathlib.Path, compiler_root: str, bootstrap_root: str) -> dict[str, Any]:
    source_path = core / "src"
    if str(source_path) not in sys.path:
        sys.path.insert(0, str(source_path))
    ucl = importlib.import_module("ucl")
    source = (core / "fixtures" / "threshold.ucl.toml").read_bytes()
    descriptor = {
        "schema": "ucl.realization_descriptor.v0",
        "backend": "SELF_HOSTED_UCL_SH_VM",
        "backend_version": "1",
        "compiler_root": compiler_root,
        "bootstrap_root": bootstrap_root,
        "effect": "NONE",
    }
    key = b"UCL-FIXTURE-CONTINUITY-KEY-DO-NOT-USE-OUTSIDE-TESTS"
    execution = ucl.execute_information_only(source, descriptor, {"x": 5}, key)
    capsule = ucl.make_capsule(
        program_root=execution["body"]["compiled_root"],
        workflow_root=execution["body"]["workflow"]["root"],
        sequence=1,
        phase="TERMINAL",
        completed=[item["id"] for item in execution["body"]["workflow"]["body"]["nodes"]],
        pending=[],
        receipt_anchor=execution["body"]["receipt_verification"]["anchor"],
        predecessor_capsule_root="GENESIS",
        key=key,
    )
    dossier = ucl.export_dossier(execution_bundle=execution, capsule=capsule, nonce="selfhost-legacy-dossier-0001", predecessor_dossier_root="GENESIS", key=key)
    observation = ucl.FederationInbox(key).import_dossier(dossier)
    flow = ucl.derive_flow(execution["body"]["workflow"], execution["body"]["receipts"], key)
    require(flow["body"]["complete"] is True, "LEGACY_FLOW_INCOMPLETE")
    return {"execution": execution, "capsule": capsule, "dossier": dossier, "observation": observation, "flow": flow}


def build_vertical_workflow(compiler_root: str, bootstrap_root: str, predecessor_root: str) -> dict[str, Any]:
    stages = [
        {"id": identifier, "ordinal": index, "stage": stage, "horizon": horizon, "predecessor": None if index == 1 else VERTICAL_STAGES[index - 2][0]}
        for index, (identifier, stage, horizon) in enumerate(VERTICAL_STAGES, 1)
    ]
    body = {
        "schema": "ucl.selfhost.integrated_workflow.v1",
        "compiler_root": compiler_root,
        "bootstrap_root": bootstrap_root,
        "predecessor_root": predecessor_root,
        "stages": stages,
        "edges": [{"from": stages[index]["id"], "to": stages[index + 1]["id"]} for index in range(len(stages) - 1)],
        "terminal_contract": {
            "requires": [item["id"] for item in stages],
            "effect": "NONE",
            "standing": "INFORMATION_ONLY",
            "real_a5": False,
            "g0": "CLOSED",
        },
    }
    return {"body": body, "root": root(body)}


def execute_integrated_vertical(project: pathlib.Path, receipt_key_hex: str, *, fail_stage: str | None = None) -> dict[str, Any]:
    project = project.resolve()
    core = project / "predecessors" / "c1-core"
    compiler_source = (project / "fixtures" / "ucl_selfhost_compiler.ucl.json").read_bytes()
    samples = {
        "compiler": compiler_source,
        "factorial": (project / "fixtures" / "factorial.ucl.json").read_bytes(),
        "records": (project / "fixtures" / "records.ucl.json").read_bytes(),
    }
    predecessor = verify_predecessor(core)
    corpus = bootstrap_corpus(compiler_source, samples)
    bootstrap = corpus["bootstrap"]
    compiler = bootstrap["stage1_artifact"]
    workflow = build_vertical_workflow(compiler["root"], bootstrap["root"], predecessor["root"])
    artifacts: dict[str, Any] = {}
    ledger: list[dict[str, Any]] = []
    pair_state: AuthorityState | None = None
    pass_run: dict[str, Any] | None = None
    legacy: dict[str, Any] | None = None
    capsule: dict[str, Any] | None = None
    federation_observation: dict[str, Any] | None = None

    for identifier, stage, _horizon in VERTICAL_STAGES:
        input_roots = [ledger[-1]["body"]["output_root"]] if ledger else []
        if fail_stage == identifier:
            output = {"schema": "ucl.selfhost.vertical_refusal.v1", "stage_id": identifier, "code": "INJECTED_TEST_FAILURE", "effect": "NONE", "standing": "INFORMATION_ONLY"}
            artifacts[identifier] = output
            append_receipt(ledger, workflow_root=workflow["root"], stage_id=identifier, stage=stage, event="STAGE_REFUSED", input_roots=input_roots, output=output, key_hex=receipt_key_hex)
            break
        if identifier == "V01":
            output = predecessor
        elif identifier == "V02":
            output = {"schema": "ucl.selfhost.human_source_binding.v1", "compiler_source_root": sha256_bytes(compiler_source), "sample_source_roots": {name: sha256_bytes(data) for name, data in samples.items()}, "profile": "UCL-SH-1", "effect": "NONE"}
        elif identifier == "V03":
            output = {"stage1_compiler_root": compiler["root"], "meta_kernel_root": compiler["body"]["meta_kernel_root"], "effect": "NONE"}
        elif identifier == "V04":
            output = {"bootstrap_root": bootstrap["root"], "stage1_root": bootstrap["body"]["stage0"]["output_root"], "stage2_root": bootstrap["body"]["stage1"]["output_root"], "byte_identical": bootstrap["body"]["stage2"]["byte_identical_to_stage1"], "effect": "NONE"}
        elif identifier == "V05":
            output = {"corpus_root": corpus["root"], "modules": corpus["body"]["modules"], "all_converged": corpus["body"]["all_converged"], "effect": "NONE"}
        elif identifier == "V06":
            pass_run = execute_pass_workflow(compiler, compiler_source.decode("utf-8"), receipt_key_hex)
            pass_anchor = pass_run["body"]["ledger"][-1]["entry_root"]
            verify_pass_run(pass_run, receipt_key_hex, expected_count=5, expected_anchor=pass_anchor)
            output = pass_run
        elif identifier == "V07":
            decision_root = root({"policy": "EXACT_PAIR_ADMISSION", "scope": "EXPERIMENTAL"})
            authority_genesis = make_authority_genesis("11" * 32, "22" * 32, "33" * 32, "66" * 32, decision_root, "ucl-selfhost-c6-fixture-authority")
            pair_state = AuthorityState("11" * 32, "22" * 32, "33" * 32, "66" * 32, decision_root, genesis=authority_genesis, expected_genesis_root=authority_genesis["genesis_root"], expected_sequence=0)
            pair = pair_state.attest_pair(root({"meaning": "compiler-semantics"}), root({"jurisdiction": "information-only"}))
            pair_decision = strict_loads((project / "fixtures" / "EXACT-PAIR-DECISION.json").read_bytes())
            require(type(pair_decision) is dict and set(pair_decision) == {"body", "body_root", "signature", "decision_record_root"}, "PAIR_DECISION_SHAPE_INVALID")
            decision_record = {key: pair_decision[key] for key in ("body", "body_root", "signature")}
            decision_body = verify_signed(decision_record, PAIR_DECISION_DOMAIN, FIXTURE_GOVERNOR_KEY)
            require(pair_decision["decision_record_root"] == root(decision_record) == PINNED_PAIR_DECISION_RECORD_ROOT, "PAIR_DECISION_PIN_MISMATCH")
            require(decision_body["authority_decision_root"] == decision_root, "PAIR_DECISION_AUTHORITY_MISMATCH")
            require(decision_body["hm_commitment_root"] == pair["body"]["hm_commitment_root"] and decision_body["hj_commitment_root"] == pair["body"]["hj_commitment_root"], "PAIR_DECISION_COMMITMENT_MISMATCH")
            require(decision_body["hm_key_root"] == key_root("11" * 32) and decision_body["hj_key_root"] == key_root("22" * 32), "PAIR_DECISION_KEY_MISMATCH")
            observation = verify_pair_attestation(pair, hm_key="11" * 32, hj_key="22" * 32, decision_root=pair_state.decision_root, hm_epoch=1, hj_epoch=1, approved_pair_roots=set(decision_body["approved_pair_roots"]))
            output = {"pair": pair, "decision_record_root": pair_decision["decision_record_root"], "observation": observation, "authority_effect": "NONE"}
        elif identifier == "V08":
            legacy = _legacy_execution(core, compiler["root"], bootstrap["root"])
            output = legacy
        elif identifier == "V09":
            require(pass_run is not None and legacy is not None, "VERTICAL_PROOF_INPUT_MISSING")
            output = {
                "schema": "ucl.selfhost.proof_verification.v1",
                "pass_run_root": pass_run["root"],
                "legacy_execution_root": legacy["execution"]["root"],
                "legacy_terminal_present": "TERMINAL" in legacy["execution"]["body"]["artifacts"],
                "all_program_obligations_discharged": all(item["status"] == "DISCHARGED" for item in legacy["execution"]["body"]["artifacts"]["VERIFY_RESULT"]["body"]["program"]),
                "effect": "NONE",
                "standing": "INFORMATION_ONLY",
            }
            require(output["legacy_terminal_present"] and output["all_program_obligations_discharged"], "VERTICAL_PROOF_UNDISCHARGED")
        elif identifier == "V10":
            capsule = make_capsule(program_root=compiler["body"]["semantic_root"], workflow_root=workflow["root"], sequence=1, phase="RUNNING", completed=[item[0] for item in VERTICAL_STAGES[:9]], pending=[item[0] for item in VERTICAL_STAGES[9:]], receipt_anchor=ledger[-1]["entry_root"], predecessor_capsule_root="GENESIS", key_hex=receipt_key_hex)
            verify_capsule(capsule, key_hex=receipt_key_hex, expected_program_root=compiler["body"]["semantic_root"], expected_workflow_root=workflow["root"], expected_sequence=1, expected_predecessor="GENESIS", expected_receipt_anchor=ledger[-1]["entry_root"])
            output = capsule
        elif identifier == "V11":
            require(capsule is not None, "VERTICAL_CAPSULE_MISSING")
            federation_genesis = make_federation_genesis(receipt_key_hex, "88" * 32, workflow["root"], "ucl-selfhost-c6-fixture-federation")
            sender = FederationExporter(receipt_key_hex, genesis=federation_genesis, expected_genesis_root=federation_genesis["genesis_root"])
            dossier = sender.export({"compiler_root": compiler["root"], "bootstrap_root": bootstrap["root"], "capsule_root": capsule["capsule_root"]}, "ucl-selfhost-dossier-0001")
            receiver = FederationInbox(receipt_key_hex, "88" * 32, genesis=federation_genesis, expected_genesis_root=federation_genesis["genesis_root"], expected_sequence=0)
            federation_observation = receiver.import_dossier(dossier)
            output = {"dossier": dossier, "observation": federation_observation, "receiver_state": receiver.snapshot()}
        else:
            require(legacy is not None and federation_observation is not None, "VERTICAL_TERMINAL_INPUT_MISSING")
            output = {
                "schema": "ucl.selfhost.terminal_closure.v1",
                "workflow_root": workflow["root"],
                "compiler_root": compiler["root"],
                "bootstrap_root": bootstrap["root"],
                "legacy_result_root": legacy["execution"]["root"],
                "completed_stages": [item[0] for item in VERTICAL_STAGES],
                "real_a5": False,
                "g0": "CLOSED",
                "effect": "NONE",
                "standing": "INFORMATION_ONLY",
            }
        artifacts[identifier] = output
        append_receipt(ledger, workflow_root=workflow["root"], stage_id=identifier, stage=stage, event="STAGE_COMPLETE", input_roots=input_roots, output=output, key_hex=receipt_key_hex)

    anchor = ledger[-1]["entry_root"] if ledger else "GENESIS"
    verification = verify_ledger(ledger, workflow_root=workflow["root"], key_hex=receipt_key_hex, expected_count=len(ledger), expected_anchor=anchor)
    flow = derive_flow(workflow, ledger, receipt_key_hex, expected_count=len(ledger), expected_anchor=anchor)
    complete = len(ledger) == len(VERTICAL_STAGES) and flow["body"]["complete"]
    body = {
        "schema": "ucl.selfhost.integrated_vertical.v1",
        "workflow": workflow,
        "artifacts": artifacts,
        "ledger": ledger,
        "ledger_verification": verification,
        "flow": flow,
        "status": "COMPLETE" if complete else "REFUSED",
        "real_a5": False,
        "g0": "CLOSED",
        "effect": "NONE",
        "standing": "INFORMATION_ONLY",
    }
    return {"body": body, "root": root(body)}


def verify_integrated_vertical(bundle: dict[str, Any], receipt_key_hex: str, *, expected_count: int, expected_anchor: str) -> dict[str, Any]:
    require(type(bundle) is dict and bundle.get("root") == root(bundle.get("body")), "VERTICAL_ROOT_MISMATCH")
    body = bundle["body"]
    workflow = body["workflow"]
    require(workflow["root"] == root(workflow["body"]), "VERTICAL_WORKFLOW_ROOT_MISMATCH")
    ledger = body["ledger"]
    verification = verify_ledger(ledger, workflow_root=workflow["root"], key_hex=receipt_key_hex, expected_count=expected_count, expected_anchor=expected_anchor)
    require(verification == body["ledger_verification"], "VERTICAL_STORED_VERIFICATION_MISMATCH")
    for entry in ledger:
        require(entry["body"]["output_root"] == root(body["artifacts"][entry["body"]["stage_id"]]), "VERTICAL_ARTIFACT_ROOT_MISMATCH")
    flow = derive_flow(workflow, ledger, receipt_key_hex, expected_count=expected_count, expected_anchor=expected_anchor)
    require(flow == body["flow"], "VERTICAL_FLOW_MISMATCH")
    complete = expected_count == len(VERTICAL_STAGES) and len(ledger) == len(VERTICAL_STAGES) and all(entry["body"]["event"] == "STAGE_COMPLETE" for entry in ledger)
    require(body["status"] == ("COMPLETE" if complete else "REFUSED"), "VERTICAL_STATUS_MISMATCH")
    require(body["real_a5"] is False and body["g0"] == "CLOSED" and body["effect"] == "NONE" and body["standing"] == "INFORMATION_ONLY", "VERTICAL_BOUNDARY_VIOLATION")
    return verification


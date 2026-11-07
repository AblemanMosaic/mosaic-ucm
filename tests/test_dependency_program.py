from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from uclop.canonical import root
from ucm import invoke
from ucm.courthouse_workflow import compile_workflow_ir, validate_workflow_request
from ucm.dependency_adapters import (assess_reuse_graduation,
                                     prepare_courthouse_dependency_binding)
from ucm.dependency_graph import build_graph, build_snapshot, evaluate_graph
from ucm.profiles import profile_allows_surface


ROOT = Path(__file__).resolve().parents[1]
R = [f"{index:x}" * 64 for index in range(1, 10)]
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def graph_node(node_id="input"):
    return {"node_id": node_id, "kind": "INPUT", "dependencies": [],
            "parameters": {}, "transform_id": "INPUT", "transform_version": "v0.1",
            "semantic_contract_root": R[0], "policy_root": R[1],
            "jurisdiction_root": R[2], "environment_root": R[3],
            "closure_coverage": "COMPLETE", "evidence_grade": "DECLARED_INPUT",
            "pure": True}


def workflow_request():
    body = {
        "schema": "mosaic.ucm.courthouse-workflow-request.v0.1",
        "request_id": "DEPENDENCY_READY_001", "campaign_root": R[0],
        "operation_id": "VALIDATE_DEPENDENCY_BOUND_WORK",
        "application_id": "MOSAIC.DEMO", "subject_root": R[1],
        "expected_journal_head": {"sequence": 0, "head": "GENESIS"},
        "architecture_contract_root": R[2], "architecture_candidate_root": R[3],
        "work_package_root": R[4], "objective": "Validate a dependency-bound work package.",
        "cm1_obligations": [{"obligation_id": "DEPENDENCY_READY",
            "obligation_root": R[5], "evidence_kind": "STATIC_CHECK", "required": True}],
        "cm2_preferences": [], "requested_capabilities": [], "policy_pack_roots": [],
        "identity_binding": {"requester_mosaic_id_root": R[0],
            "session_mosaic_id_root": R[1], "jurisdiction_root": R[2],
            "courthouse_identity_root": R[3], "courthouse_protocol_root": R[4]},
        "authority_ceiling": {**BOUNDARY,
            "execution_authority_owner": "COURTHOUSE_VNEXT_EXTERNAL"},
    }
    return {**body, "request_root": root(body)}


class DependencyProgramTests(unittest.TestCase):
    def test_cli_abi_profile_and_no_implicit_write(self):
        request = {"graph_id": "cli", "nodes": [graph_node()],
            "adapter_id": "TEST", "adapter_version": "v0.1",
            "adapter_policy_root": R[4], "schema_registry_root": R[5],
            "trust_root": R[6], "closure_claim": "COMPLETE"}
        via_abi = invoke({"schema": "mosaic.ucm.request.v0.1",
            "surface": "COMPILE_DEPENDENCY_GRAPH", "payload": request,
            "request_id": "dependency-cli-abi"})["result"]
        self.assertEqual(profile_allows_surface(
            "AUTHORING", "COMPILE_DEPENDENCY_GRAPH")["status"], "PASS_ALLOWED")
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            folder_path = Path(folder); request_path = folder_path / "request.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            before = sorted(path.name for path in folder_path.iterdir())
            env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
            completed = subprocess.run([sys.executable, "-m", "ucm.cli",
                "dependency-compile", str(request_path)], cwd=folder_path, env=env,
                capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            self.assertEqual(json.loads(completed.stdout), via_abi)
            self.assertEqual(sorted(path.name for path in folder_path.iterdir()), before)
            help_result = subprocess.run([sys.executable, "-m", "ucm.cli",
                "dependency-compile", "--help"], cwd=folder_path, env=env,
                capture_output=True, text=True)
            self.assertEqual(help_result.returncode, 0)
            self.assertEqual(sorted(path.name for path in folder_path.iterdir()), before)

    def test_native_workflow_ir_accepts_only_ready_dependency_binding(self):
        graph = build_graph(graph_id="workflow", nodes=[graph_node()],
            adapter_id="COURTHOUSE_WORKFLOW_IR", adapter_version="v0.1",
            adapter_policy_root=R[4], schema_registry_root=R[5], trust_root=R[6],
            closure_claim="COMPLETE")
        snapshot = build_snapshot(graph=graph, snapshot_id="ready",
            predecessor_snapshot_root=None, inputs=[{
                "node_id": "input", "presence": {"present": True, "value": "ready"}}])
        evaluation = evaluate_graph(graph=graph, snapshot=snapshot)
        source = workflow_request(); validate_workflow_request(source)
        binding = prepare_courthouse_dependency_binding(evaluation=evaluation,
            required_target_ids=["input"], workflow_request_root=source["request_root"],
            acceptance_case_root=R[7], work_unit_root=R[8], native_validator_root=R[0])
        self.assertEqual(binding["status"], "READY_FOR_NATIVE_VALIDATION")
        compiled = compile_workflow_ir(source)
        self.assertEqual(compiled["request_root"], source["request_root"])
        self.assertFalse(binding["workflow_compiled"])
        self.assertFalse(binding["permit_created"])

    def test_release_lane_never_graduates_reuse(self):
        result = assess_reuse_graduation(adapter_id="NATIVE_PROOF",
            closure_coverage="COMPLETE", conformance_root=R[0], benchmark_root=R[1],
            release_lane=True, identity_drift=False)
        self.assertEqual(result["selected_mode"], "SHADOW_IMPACT")
        self.assertIn("RELEASE_REQUIRES_FULL_CACHE_FREE_QUALIFICATION",
                      result["reason_codes"])
        self.assertFalse(result["release_qualification_reused"])

    def test_documented_self_governed_boundary_demo(self):
        self.assertTrue((ROOT / "docs/DEPENDENCY-AND-EVIDENCE-GRAPH.md").is_file())
        demo = json.loads((ROOT / "examples/dependency-graph/BOUNDARY-DEMO.json")
                          .read_text(encoding="utf-8"))
        self.assertTrue(all(demo["assertions"].values()))
        check = subprocess.run([sys.executable, "-B",
            str(ROOT / "tools/build_dependency_boundary_demo.py"), "--check"],
            cwd=ROOT, capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
        self.assertEqual(check.returncode, 0, check.stderr + check.stdout)

    def test_release_and_operator_apparatus_are_exact_and_unexecuted(self):
        self.assertTrue((ROOT / "tools/build_dependency_graph_operator_kit.py").is_file())
        self.assertTrue((ROOT / "operator/dependency-graph-r021/RUN-TIER1.py").is_file())
        manifest = json.loads((ROOT / "operator/dependency-graph-r021/KIT-DECLARATION.json")
                              .read_text(encoding="utf-8"))
        self.assertTrue(manifest["builder_authored"])
        self.assertFalse(manifest["operator_executed"])
        self.assertFalse(manifest["tier1_executed"])

    def test_operator_kit_pins_the_exact_cold_boot(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "dependency_operator_kit", ROOT / "tools/build_dependency_graph_operator_kit.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            base = Path(folder)
            runtime = base / "runtime.zip"; runtime.write_bytes(b"runtime")
            qualification = base / "qualification.json"; qualification.write_bytes(b"{}\n")
            cold_boot = base / "cold-boot.zip"; cold_boot.write_bytes(b"cold-boot")
            output = base / "kit"
            module.build(runtime, qualification, cold_boot, output)
            with zipfile.ZipFile(output / "UCM-DEPENDENCY-r021-OPERATOR-KIT.zip") as archive:
                kit = json.loads(archive.read("KIT-MANIFEST.json"))
            import hashlib
            self.assertEqual(kit["cold_boot_sha256"],
                             hashlib.sha256(cold_boot.read_bytes()).hexdigest())
            self.assertFalse(kit["operator_executed"])

    def _conditional(self, case_id):
        value = json.loads((ROOT / "program/dependency-graph-r021" /
            f"{case_id}-CONDITIONAL-DISPOSITION.json").read_text(encoding="utf-8"))
        self.assertEqual(value["disposition"],
                         "NOT_SELECTED_NO_NAMED_CONSUMER_OR_BLOCKER")
        self.assertFalse(value["implementation_effect_authorized"])

    def test_optional_interchange_is_conditionally_not_selected(self):
        self._conditional("DG-29")

    def test_advanced_optimization_is_conditionally_not_selected(self):
        self._conditional("DG-30")


if __name__ == "__main__":
    unittest.main()

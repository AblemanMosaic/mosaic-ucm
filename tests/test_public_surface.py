from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ucm import invoke
from uclop.canonical import Refusal
from ucm.system import VERSION, capability_registry, orientation
sys.path.insert(0, str(ROOT / "tools"))
from prepare_release_contracts import capability_document


class PublicSurfaceTests(unittest.TestCase):
    def test_identity_and_boundary_are_stable(self):
        value = orientation()
        self.assertEqual(VERSION, "v0.1")
        self.assertEqual(value["product"], "Universal Constitutional Machine")
        self.assertEqual(value["publisher"], "Ableman Mosaic")
        self.assertEqual(value["license"], "Apache-2.0")
        self.assertEqual(value["authority_effect"], "NONE")
        self.assertFalse(value["real_a5"])
        self.assertEqual(value["g0"], "CLOSED")
        self.assertEqual(len(value["systems"]), 18)
        self.assertFalse(any("c1" in row["name"].lower() or "c2" in row["name"].lower() or "c3" in row["name"].lower() or "c4" in row["name"].lower() for row in value["systems"]))

    def test_capabilities_are_closed_and_non_authorizing(self):
        registry = capability_registry()
        self.assertEqual(registry["authority_effect"], "NONE")
        self.assertEqual(len(registry["surfaces"]), 52)
        self.assertEqual(len({row["name"] for row in registry["surfaces"]}), 52)
        by_name = {row["name"]: row for row in registry["surfaces"]}
        self.assertEqual(by_name["PROJECT_DASHBOARD"]["effect_scope"], "READ_ONLY")
        self.assertEqual(by_name["BUILD_PORTABLE_PROFILE"]["availability"], "SEPARATE_STAGE_REQUIRED")
        self.assertFalse(any(row["availability"] == "ACTIVE" and not row["route"] for row in registry["surfaces"]))
        self.assertEqual(by_name["VERIFY_NATIVE_PROOF"]["result_schema"], "ucl.proof.check.v1")
        self.assertEqual(by_name["PROJECT_DASHBOARD"]["result_schema"], "ucl.ucm.project_intelligence.dashboard.v1")
        self.assertEqual(by_name["PREPARE_AUTONOMOUS_PLAN"]["result_schema"], "ucl.ucm.autonomous_project_manager.plan.v1")
        self.assertEqual(by_name["EXPLAIN_CLAIM"]["result_schema"], "ucl.ucm.explanation_graph.v1")
        self.assertEqual(by_name["SELECT_REALIZATION"]["payload_required"], ["contract", "candidates"])
        self.assertEqual(by_name["PLAN_STAGE_I3_SHADOW"]["effect_scope"], "LOCAL_ARTIFACT_PREPARATION")
        self.assertEqual(by_name["PLAN_STAGE_I3_SHADOW"]["availability"], "SEPARATE_STAGE_REQUIRED")
        self.assertEqual(by_name["VALIDATE_STAGE_I3_PLAN"]["effect_scope"], "PURE_COMPUTATION")
        self.assertEqual(by_name["VALIDATE_NATIVE_HEADLESS_RUNNER_BINDING"]["effect_scope"],
                         "PURE_COMPUTATION")
        self.assertEqual(by_name["BUILD_STAGE_I4_EXACT_RUN_CONTRACT"]["availability"],
                         "LEGACY_COMPATIBILITY_ONLY")
        self.assertEqual(by_name["BUILD_NATIVE_HEADLESS_RUNNER_PREFLIGHT"]["effect_scope"],
                         "PURE_COMPUTATION")
        self.assertEqual(by_name["DERIVE_STAGE_I4_OPERATION_STATE"]["availability"],
                         "LEGACY_COMPATIBILITY_ONLY")
        self.assertEqual(by_name["VALIDATE_STAGE_I4_OBSERVATION"]["availability"],
                         "LEGACY_COMPATIBILITY_ONLY")
        self.assertEqual(by_name["BUILD_STAGE_I4_ANCHORED_RUN_CONTRACT"]["availability"],
                         "LEGACY_COMPATIBILITY_ONLY")
        self.assertEqual(by_name["BUILD_STAGE_I4_AUTHORITY_SAFE_PREFLIGHT"]["payload_required"],
                         ["run_contract", "trust_anchors", "expected_trust_anchors_root",
                          "execution_authority_policy"])
        self.assertEqual(by_name["DERIVE_STAGE_I4_RECEIPT_STATE"]["result_schema"],
                         "mosaic.ucm.stage-i4-operation-state.v0.2")
        self.assertEqual(by_name["BUILD_OPERATIONAL_CONTRACT"]["availability"], "ACTIVE")
        self.assertEqual(by_name["PREPARE_OPERATIONAL_GATEWAY"]["effect_scope"],
                         "LOCAL_ARTIFACT_PREPARATION")
        self.assertEqual(by_name["VERIFY_OPERATIONAL_ARCHIVE"]["effect_scope"],
                         "PURE_COMPUTATION")

    def test_discovery_to_invocation_route_is_stable(self):
        result = invoke({
            "schema": "mosaic.ucm.request.v0.1",
            "surface": "DISCOVER_CAPABILITIES",
            "payload": {},
            "request_id": "test-discovery",
        })
        self.assertEqual(result["surface"], "DISCOVER_CAPABILITIES")
        self.assertEqual(result["result"], capability_registry())

    def test_machine_registry_and_capability_document_share_definitions(self):
        registry = json.loads((ROOT / "spec/ucm-system-registry.json").read_text(encoding="utf-8"))
        self.assertEqual(registry["capability_registry_root"], capability_registry()["root"])
        self.assertEqual((ROOT / "docs/CAPABILITY-SURFACES.md").read_text(encoding="utf-8"), capability_document())

    def test_cli_orients_from_an_arbitrary_working_directory(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools" / "ucm.py"), "orient"], cwd=ROOT.parent, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        value = json.loads(result.stdout)
        self.assertEqual(value["version"], "v0.1")

    def test_module_entrypoint_and_semantic_refusal_exit_code(self):
        environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        oriented = subprocess.run([sys.executable, "-m", "ucm.cli", "orient"], cwd=ROOT.parent, env=environment, capture_output=True, text=True)
        self.assertEqual(oriented.returncode, 0, oriented.stderr + oriented.stdout)
        contract = ROOT / "examples/realization/portable-agent-environment.json"
        invalid = ROOT / ".build/test-inadmissible-configuration.json"
        invalid.parent.mkdir(exist_ok=True)
        invalid.write_text(json.dumps({"TARGET_ISA": "X64", "MEMORY_MIB": 4096, "SELF_HOSTED_AGENT": True, "NETWORK_BOOTSTRAP": "ETHERNET_LOCAL_ONLY"}), encoding="utf-8")
        try:
            checked = subprocess.run([sys.executable, "-m", "ucm.cli", "check-realization", str(contract), str(invalid)], cwd=ROOT.parent, env=environment, capture_output=True, text=True)
            self.assertEqual(checked.returncode, 3, checked.stderr + checked.stdout)
            self.assertEqual(json.loads(checked.stdout)["status"], "REFUSED_INADMISSIBLE")
        finally:
            invalid.unlink(missing_ok=True)

    def test_realization_seed_is_typed_semantics_not_a_credential(self):
        contract = json.loads((ROOT / "examples/realization/portable-agent-environment.json").read_text(encoding="utf-8"))
        contract["selection"] = {"default_policy": "LEXICOGRAPHIC_CONFIGURATION_ROOT", "policies": ["LEXICOGRAPHIC_CONFIGURATION_ROOT"], "seed_required_for_non_unique": True, "fallback_policy": "REFUSE", "seed": 7}
        candidates = [
            {"TARGET_ISA": "X64", "MEMORY_MIB": 4096, "SELF_HOSTED_AGENT": False, "NETWORK_BOOTSTRAP": "DISABLED"},
            {"TARGET_ISA": "ARM64", "MEMORY_MIB": 4096, "SELF_HOSTED_AGENT": False, "NETWORK_BOOTSTRAP": "DISABLED"},
        ]
        response = invoke({"schema": "mosaic.ucm.request.v0.1", "surface": "SELECT_REALIZATION", "payload": {"contract": contract, "candidates": candidates}, "request_id": "semantic-seed"})
        self.assertEqual(response["result"]["status"], "PASS_SELECTED")
        with self.assertRaises(Refusal):
            invoke({"schema": "mosaic.ucm.request.v0.1", "surface": "ORIENT", "payload": {"private_seed": 7}, "request_id": "credential-seed"})


if __name__ == "__main__":
    unittest.main()


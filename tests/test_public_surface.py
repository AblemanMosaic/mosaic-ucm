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
from ucm.system import (LEGACY_SURFACE_REPLACEMENTS, VERSION,
                        capability_registry, legacy_capability_registry,
                        orientation)
sys.path.insert(0, str(ROOT / "tools"))
from prepare_release_contracts import capability_document, legacy_capability_document


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
        self.assertEqual(len(value["systems"]), 32)
        self.assertFalse(any("c1" in row["name"].lower() or "c2" in row["name"].lower() or "c3" in row["name"].lower() or "c4" in row["name"].lower() for row in value["systems"]))

    def test_capabilities_are_closed_and_non_authorizing(self):
        registry = capability_registry()
        self.assertEqual(registry["authority_effect"], "NONE")
        self.assertEqual(len(registry["surfaces"]), 217)
        self.assertEqual(len({row["name"] for row in registry["surfaces"]}), 217)
        by_name = {row["name"]: row for row in registry["surfaces"]}
        self.assertEqual(by_name["PROJECT_DASHBOARD"]["effect_scope"], "READ_ONLY")
        self.assertEqual(by_name["BUILD_PORTABLE_PROFILE"]["availability"], "SEPARATE_STAGE_REQUIRED")
        self.assertEqual(by_name["MANAGE_BOUNDED_CORRECTION"]["effect_scope"], "LOCAL_ARTIFACT_PREPARATION")
        self.assertEqual(by_name["MANAGE_BOUNDED_CORRECTION"]["availability"], "SEPARATE_STAGE_REQUIRED")
        self.assertEqual(by_name["EXECUTE_INCREMENTAL_HOTFIX"]["availability"], "SEPARATE_STAGE_REQUIRED")
        self.assertFalse(any(row["availability"] == "ACTIVE" and not row["route"] for row in registry["surfaces"]))
        self.assertEqual(by_name["VERIFY_NATIVE_PROOF"]["result_schema"], "ucl.proof.check.v1")
        self.assertEqual(by_name["PROJECT_DASHBOARD"]["result_schema"], "ucl.ucm.project_intelligence.dashboard.v1")
        self.assertEqual(by_name["PREPARE_AUTONOMOUS_PLAN"]["result_schema"], "ucl.ucm.autonomous_project_manager.plan.v1")
        self.assertEqual(by_name["EXPLAIN_CLAIM"]["result_schema"], "ucl.ucm.explanation_graph.v1")
        self.assertEqual(by_name["SELECT_REALIZATION"]["payload_required"], ["contract", "candidates"])
        self.assertEqual(by_name["PLAN_STAGE_I3_SHADOW"]["effect_scope"], "LOCAL_ARTIFACT_PREPARATION")
        self.assertEqual(by_name["PLAN_STAGE_I3_SHADOW"]["availability"], "SEPARATE_STAGE_REQUIRED")
        self.assertEqual(by_name["VALIDATE_STAGE_I3_PLAN"]["effect_scope"], "PURE_COMPUTATION")
        self.assertFalse(set(by_name) & set(LEGACY_SURFACE_REPLACEMENTS))
        self.assertEqual(registry["legacy_surface_count"], 16)
        self.assertEqual(by_name["BUILD_OPERATIONAL_CONTRACT"]["availability"], "ACTIVE")
        self.assertEqual(by_name["PREPARE_OPERATIONAL_GATEWAY"]["effect_scope"],
                         "LOCAL_ARTIFACT_PREPARATION")
        self.assertEqual(by_name["VERIFY_OPERATIONAL_ARCHIVE"]["effect_scope"],
                         "PURE_COMPUTATION")
        self.assertEqual(by_name["EVALUATE_CURRENT_ADMISSIBILITY"]["system"],
                         "POINT_OF_USE_ADMISSIBILITY")
        self.assertEqual(by_name["EXPLAIN_CURRENT_ADMISSIBILITY"]["system"],
                         "PIPPI_MEDIATION")
        self.assertEqual(by_name["PREPARE_ADMISSIBILITY_BOUND_GATEWAY"]["system"],
                         "OPERATIONAL_GATEWAY")
        self.assertEqual(by_name["DISCOVER_UGEL_EXECUTOR_PACK"]["system"],
                         "GOVERNED_EXECUTION_LAYER")
        self.assertEqual(by_name["COMPILE_UGEL_CORRESPONDENCE"]["effect_scope"],
                         "PURE_COMPUTATION")

    def test_legacy_routes_are_quarantined_with_current_pointers(self):
        registry = legacy_capability_registry()
        self.assertEqual(registry["selection_requirement"],
                         "EXPLICIT_COMPATIBILITY_PROFILE")
        self.assertEqual(len(registry["surfaces"]), 16)
        self.assertEqual({row["name"] for row in registry["surfaces"]},
                         set(LEGACY_SURFACE_REPLACEMENTS))
        self.assertTrue(all(row["replacement_surface"] in {
            current["name"] for current in capability_registry()["surfaces"]
        } for row in registry["surfaces"]))
        with self.assertRaisesRegex(
                ValueError,
                "UCM_LEGACY_SURFACE_REQUIRES_COMPATIBILITY_PROFILE"):
            invoke({"schema": "mosaic.ucm.request.v0.1",
                    "surface": "DERIVE_STAGE_I4_ELIGIBILITY",
                    "payload": {}, "request_id": "legacy-default-refusal"})

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
        self.assertEqual((ROOT / "docs/LEGACY-CAPABILITY-SURFACES.md").read_text(encoding="utf-8"), legacy_capability_document())

    def test_cli_orients_from_an_arbitrary_working_directory(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools" / "ucm.py"), "orient"], cwd=ROOT.parent, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        value = json.loads(result.stdout)
        self.assertEqual(value["version"], "v0.1")

    def test_legacy_cli_requires_explicit_compatibility(self):
        result = subprocess.run([
            sys.executable, str(ROOT / "tools" / "ucm.py"),
            "stage4-derive-eligibility", "instruction.json", "plan.json",
            "review.zip", "out.json",
        ], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 3, result.stderr + result.stdout)
        refusal = json.loads(result.stdout)
        self.assertEqual(
            refusal["diagnostic"],
            "UCM_LEGACY_SURFACE_REQUIRES_COMPATIBILITY_PROFILE")
        self.assertIn("BUILD_OPERATIONAL_CONTRACT", refusal["detail"])

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

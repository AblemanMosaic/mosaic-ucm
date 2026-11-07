from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from ucm.c_preflight import (
    BASE_CHECKS,
    CHANNELS,
    CHECKS_BY_CLASS,
    RESULT_SCHEMA,
    build_c_change_preflight,
    c_coding_standard,
    evaluate_c_check_results,
    validate_c_change_preflight,
)
from ucm.capabilities import invoke
from ucm.authoring import validate_policy_pack
from ucm.system import capability_registry


ROOT = "a" * 64
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def request(**changes):
    classes = changes.pop("change_classes", ["C_RUNTIME", "SIMULATION"])
    required = set(BASE_CHECKS)
    for change_class in classes:
        required.update(CHECKS_BY_CLASS[change_class])
    value = {
        "proposal_id": "CW.CHANGE.001",
        "subject_root": ROOT,
        "source_manifest_root": "b" * 64,
        "language_standard": "C17",
        "compiler_profile_root": "c" * 64,
        "architecture_contract_root": "d" * 64,
        "change_classes": classes,
        "changed_paths": ["src/core/simulation.c"],
        "declared_write_paths": ["src/core/simulation.c"],
        "declared_check_ids": sorted(required),
        "requested_effect_classes": ["LOCAL_PROCESS", "READ_SOURCE", "WRITE_WORKSPACE"],
        "integration_mode": "SIDECAR_PARTIAL",
        "mediated_channels": sorted(CHANNELS - {"TOOL_DISPATCH"}),
        "native_semantic_authority": "NATIVE_C",
        "python_role": "AUTHORING_VERIFICATION_ONLY",
    }
    value.update(changes)
    return value


class CCodingPreflightTests(unittest.TestCase):
    def test_standard_is_rooted_and_non_granting(self):
        standard = c_coding_standard()
        self.assertEqual(standard["language_standard"], "C17")
        self.assertEqual(standard["authority_effect"], "NONE")
        self.assertFalse(standard["real_a5"])
        self.assertEqual(standard["g0"], "CLOSED")
        self.assertEqual(standard, c_coding_standard())

    def test_c_policy_pack_is_canonical_and_rooted(self):
        pack = json.loads((REPO_ROOT / "policy-packs" /
                           "C-SAFE-DEVELOPMENT-v0.1.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_policy_pack(pack), pack)
        self.assertEqual(len(pack["requirements"]), 13)

    def test_complete_change_is_ready_for_quick_checks(self):
        result = build_c_change_preflight(**request())
        self.assertEqual(result["decision"], "READY_FOR_QUICK_CHECKS")
        self.assertFalse(result["tool_dispatch_authorized"])
        self.assertEqual(result["violations"], [])
        self.assertEqual(validate_c_change_preflight(result), result)

    def test_inferred_class_must_be_declared(self):
        value = request(change_classes=["C_RUNTIME"])
        value["declared_check_ids"] = sorted(BASE_CHECKS | CHECKS_BY_CLASS["C_RUNTIME"])
        result = build_c_change_preflight(**value)
        self.assertEqual(result["decision"], "REFUSED")
        self.assertIn("C_PREFLIGHT_CHANGE_CLASS_INCOMPLETE",
                      [row["code"] for row in result["violations"]])

    def test_forbidden_effect_is_refused(self):
        value = request()
        value["requested_effect_classes"] = ["NETWORK", "READ_SOURCE"]
        result = build_c_change_preflight(**value)
        self.assertIn("C_PREFLIGHT_FORBIDDEN_EFFECT",
                      [row["code"] for row in result["violations"]])

    def test_non_c17_and_python_authority_are_refused(self):
        result = build_c_change_preflight(**request(
            language_standard="GNU17", python_role="LIVE_SIMULATION_AUTHORITY"))
        codes = [row["code"] for row in result["violations"]]
        self.assertIn("C_PREFLIGHT_DIALECT_REFUSED", codes)
        self.assertIn("C_PREFLIGHT_PYTHON_AUTHORITY_INVALID", codes)

    def test_enforced_host_requires_a_verified_host_attestation(self):
        result = build_c_change_preflight(**request(integration_mode="ENFORCED_HOST"))
        self.assertIn("C_PREFLIGHT_HOST_ATTESTATION_REQUIRED",
                      [row["code"] for row in result["violations"]])
        still_refused = build_c_change_preflight(**request(
            integration_mode="ENFORCED_HOST", mediated_channels=sorted(CHANNELS)))
        self.assertIn("C_PREFLIGHT_HOST_ATTESTATION_REQUIRED",
                      [row["code"] for row in still_refused["violations"]])

    def test_write_set_and_check_denominator_are_enforced(self):
        value = request(declared_write_paths=["src/core/other.c"],
                        declared_check_ids=[])
        result = build_c_change_preflight(**value)
        codes = [row["code"] for row in result["violations"]]
        self.assertIn("C_PREFLIGHT_WRITE_SET_INCOMPLETE", codes)
        self.assertIn("C_PREFLIGHT_REQUIRED_CHECKS_MISSING", codes)
        self.assertTrue(result["missing_check_ids"])

    def test_exact_check_results_pass_without_granting_dispatch(self):
        preflight = build_c_change_preflight(**request())
        rows = [{"schema": RESULT_SCHEMA, "check_id": check_id, "status": "PASS",
                 "subject_root": ROOT, "tool_root": "1" * 64,
                 "invocation_root": "2" * 64, "evidence_root": "3" * 64}
                for check_id in preflight["required_check_ids"]]
        result = evaluate_c_check_results(preflight=preflight, check_results=rows)
        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(result["completed_denominator"], result["fixed_denominator"])
        self.assertFalse(result["tool_dispatch_authorized"])

    def test_failed_and_missing_results_refuse(self):
        preflight = build_c_change_preflight(**request())
        first = preflight["required_check_ids"][0]
        rows = [{"schema": RESULT_SCHEMA, "check_id": first, "status": "FAIL",
                 "subject_root": ROOT, "tool_root": "1" * 64,
                 "invocation_root": "2" * 64, "evidence_root": "3" * 64}]
        result = evaluate_c_check_results(preflight=preflight, check_results=rows)
        self.assertEqual(result["decision"], "REFUSED")
        self.assertIn("C_CHECK_RESULTS_FAILED", result["reason_codes"])
        self.assertIn("C_CHECK_RESULTS_MISSING", result["reason_codes"])

    def test_capability_abi_exposes_all_three_surfaces(self):
        registry = capability_registry()
        surfaces = {row["name"] for row in registry["surfaces"]}
        self.assertTrue({"DISCOVER_C_CODING_STANDARD", "PREFLIGHT_C_CHANGE",
                         "EVALUATE_C_CHANGE_RESULTS"} <= surfaces)
        standard = invoke({"schema": "mosaic.ucm.request.v0.1",
            "surface": "DISCOVER_C_CODING_STANDARD", "payload": {},
            "request_id": "c-standard"})
        self.assertEqual(standard["result"]["language_standard"], "C17")
        preflight = invoke({"schema": "mosaic.ucm.request.v0.1",
            "surface": "PREFLIGHT_C_CHANGE", "payload": request(),
            "request_id": "c-preflight"})
        self.assertEqual(preflight["result"]["decision"], "READY_FOR_QUICK_CHECKS")

    def test_cli_projects_standard_preflight_and_exact_results(self):
        build_root = REPO_ROOT / ".build"
        build_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="c-preflight-", dir=build_root) as raw:
            workspace = pathlib.Path(raw)
            request_path = workspace / "request.json"
            request_path.write_text(json.dumps(request()), encoding="utf-8")
            standard = subprocess.run(
                [sys.executable, str(REPO_ROOT / "tools" / "ucm.py"), "c-standard"],
                cwd=REPO_ROOT, capture_output=True, text=True)
            self.assertEqual(standard.returncode, 0, standard.stderr + standard.stdout)
            self.assertEqual(json.loads(standard.stdout)["language_standard"], "C17")
            prepared = subprocess.run(
                [sys.executable, str(REPO_ROOT / "tools" / "ucm.py"),
                 "c-preflight", str(request_path)],
                cwd=REPO_ROOT, capture_output=True, text=True)
            self.assertEqual(prepared.returncode, 0, prepared.stderr + prepared.stdout)
            preflight = json.loads(prepared.stdout)
            self.assertEqual(preflight["decision"], "READY_FOR_QUICK_CHECKS")
            check_results = [
                {"schema": RESULT_SCHEMA, "check_id": check_id, "status": "PASS",
                 "subject_root": ROOT, "tool_root": "1" * 64,
                 "invocation_root": "2" * 64, "evidence_root": "3" * 64}
                for check_id in preflight["required_check_ids"]
            ]
            results_path = workspace / "results.json"
            results_path.write_text(json.dumps({
                "preflight": preflight, "check_results": check_results,
            }), encoding="utf-8")
            evaluated = subprocess.run(
                [sys.executable, str(REPO_ROOT / "tools" / "ucm.py"),
                 "c-check-results", str(results_path)],
                cwd=REPO_ROOT, capture_output=True, text=True)
            self.assertEqual(evaluated.returncode, 0, evaluated.stderr + evaluated.stdout)
            self.assertEqual(json.loads(evaluated.stdout)["decision"], "PASS")


if __name__ == "__main__":
    unittest.main()

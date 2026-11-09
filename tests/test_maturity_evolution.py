from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from uclop.canonical import canonical_bytes, root, strict_loads
from ucm import invoke
from ucm.agent_adapter import AgentToolAdapter, agent_loop_contract
from ucm.authoring import inspect_policy_pack_composition
from ucm.contract_workbench import (
    classify_contract_compatibility,
    compare_configurations,
    compile_authoring_profile,
    doctor_contract,
    explain_selection,
    initialize_amcas_contract,
    initialize_realization_contract,
)
from ucm.evidence_adapters import (build_tool_evidence_subject,
                                   validate_tool_evidence_subject)
from ucm.governance import (EXIT_CODES, abi_stability_table,
                            build_external_approval,
                            external_approval_signing_body,
                            inspect_environment, shell_completion, time_policy,
                            verify_external_approval)
from ucm.presentation import pretty_record
from ucm.profiles import profile_registry
from ucm.system import capability_registry
from ucm.thr_cas import verify_thr_manifest


ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return strict_loads((ROOT / path).read_bytes())


class ContractWorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.subject = "1" * 64
        self.realization = initialize_realization_contract(
            contract_id="EXAMPLE.CONTRACT", subject_id="EXAMPLE.SUBJECT",
            subject_root=self.subject, description="Example authoring scaffold")

    def test_scaffold_is_valid_and_authoring_only(self):
        result = doctor_contract("realization", self.realization)
        self.assertEqual(result["readiness"], "PASS_AUTHORING_ONLY")
        self.assertEqual(result["authority_effect"], "NONE")

    def test_amcas_scaffold_is_unbound_and_non_granting(self):
        contract = initialize_amcas_contract(
            integration_id="EXAMPLE.INTEGRATION", application_id="EXAMPLE.APP",
            application_name="Example App", subject_root=self.subject,
            manifest_root="2" * 64, realization_contract=self.realization)
        result = doctor_contract("amcas", contract)
        self.assertEqual(result["readiness"], "PASS_AUTHORING_ONLY")
        self.assertEqual(contract["authority_ceiling"]["authority_effect"], "NONE")

    def test_constrained_authoring_profile_compiles(self):
        source = (ROOT / "examples/authoring/portable-worker.ucm").read_text(encoding="utf-8")
        result = compile_authoring_profile(source)
        self.assertEqual(result["status"], "PASS_COMPILED_DRAFT")
        self.assertEqual(len(result["contract"]["axes"]), 2)

    def test_compatibility_names_missing_migration(self):
        successor = dict(self.realization)
        successor["description"] = "Successor"
        successor.pop("root")
        successor["root"] = root(successor)
        result = classify_contract_compatibility(
            predecessor=self.realization, successor=successor,
            known_roots=[root(self.realization)])
        self.assertEqual(result["status"], "NEEDS_DECLARED_MIGRATION")

    def test_selection_explanation_and_diff(self):
        left = {"PROFILE": "UNBOUND"}
        result = explain_selection(self.realization, [left])
        self.assertEqual(result["status"], "PASS_EXPLAINED")
        self.assertEqual(result["human_lines"], ["candidate 0: selected"])
        difference = compare_configurations(self.realization, left, left)
        self.assertEqual(difference["admissibility"], "BOTH")
        self.assertEqual(difference["changed_axes"], [])


class PublicBoundaryTests(unittest.TestCase):
    def test_abi_table_is_bound_to_current_registry(self):
        table = abi_stability_table()
        self.assertEqual(table["capability_registry_root"], capability_registry()["root"])
        self.assertEqual(EXIT_CODES["TYPED_REFUSAL"], 3)

    def test_environment_policy_is_explicit(self):
        self.assertEqual(inspect_environment({"UCM_OUTPUT_MODE": "JSON"}, strict=True)["status"],
                         "PASS")
        self.assertEqual(inspect_environment({"UCM_HIDDEN_OVERRIDE": "1"}, strict=True)["status"],
                         "REFUSED_ENVIRONMENT")

    def test_time_policy_uses_caller_time(self):
        self.assertEqual(time_policy()["clock_source"], "CALLER_SUPPLIED_INTEGER")

    def test_completion_is_derived_from_commands_and_surfaces(self):
        completion = shell_completion("bash")
        self.assertIn("contract-doctor", completion["script"])
        self.assertIn("DOCTOR_CONTRACT", completion["script"])

    def test_cli_usage_has_stable_exit_code(self):
        environment = {**os.environ, "PYTHONPATH": str(ROOT / "src"),
                       "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run([sys.executable, "-m", "ucm.cli"], cwd=ROOT,
                                env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, EXIT_CODES["USAGE_ERROR"])

    def test_external_approval_is_verified_but_non_granting(self):
        private = Ed25519PrivateKey.from_private_bytes(b"\x51" * 32)
        public_hex = private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw).hex()
        body = external_approval_signing_body(
            approval_id="A1", operation_root="3" * 64,
            approver_identity_root="4" * 64,
            approver_public_key_hex=public_hex, policy_root="5" * 64,
            decision="APPROVE", issued_at=10, not_after=20)
        approval = build_external_approval(
            approval_id="A1", operation_root="3" * 64,
            approver_identity_root="4" * 64,
            approver_public_key_hex=public_hex, policy_root="5" * 64,
            decision="APPROVE", issued_at=10, not_after=20,
            signature_hex=private.sign(canonical_bytes(body)).hex())
        checked = verify_external_approval(
            approval, expected_operation_root="3" * 64,
            expected_policy_root="5" * 64, now=15)
        self.assertEqual(checked["authority_effect"], "NONE")

    def test_canonical_vectors_are_platform_neutral(self):
        first = strict_loads(b'{"b":2,"a":"caf\xc3\xa9"}\r\n')
        second = strict_loads(b'{\n "a":"caf\xc3\xa9", "b":2\n}')
        self.assertEqual(canonical_bytes(first), canonical_bytes(second))
        self.assertEqual(root(first), root(second))


class EvidenceAndAgentTests(unittest.TestCase):
    def test_external_tool_result_is_presence_and_hash_only(self):
        subject = build_tool_evidence_subject(
            tool="PYTEST", subject_root="1" * 64, invocation_root="2" * 64,
            output_root="3" * 64, environment_root="4" * 64,
            verifier_root="5" * 64, policy_root="6" * 64,
            issuer_root="7" * 64, exit_code=0, counts={"passed": 12},
            issued_at=10, not_after=20)
        self.assertEqual(validate_tool_evidence_subject(subject), subject)
        self.assertIn("UCM_DID_NOT_RUN_THE_TOOL",
                      subject["tool_result"]["non_claims"])

    def test_agent_adapter_pins_registry_and_profile(self):
        capabilities = capability_registry()
        profiles = profile_registry()
        adapter = AgentToolAdapter(
            profile_id="VERIFY_ONLY", capability_registry_root=capabilities["root"],
            profile_registry_root=profiles["profile_registry_root"], dispatcher=invoke)
        result = adapter.call(surface="ORIENT", payload={}, request_id="orientation")
        self.assertEqual(result["surface"], "ORIENT")
        self.assertEqual(agent_loop_contract()["effect_policy"],
                         "NO_EFFECT_WITHOUT_OPERATIONAL_GATEWAY")

    def test_pretty_projection_is_not_authority(self):
        projection = pretty_record({"schema": "example", "status": "PASS",
                                    "root": "8" * 64}, title="Example")
        self.assertIn("Projection only", projection["text"])
        self.assertIn("NOT_ALTERNATE_AUTHORITY", projection["non_claims"])

    def test_policy_pack_composition_reports_no_conflict_for_one_pack(self):
        pack = load("policy-packs/ARCHITECTURE-FIDELITY-v0.1.json")
        self.assertEqual(inspect_policy_pack_composition([pack])["status"],
                         "PASS_COMPOSABLE")


class GovernedProgramTests(unittest.TestCase):
    def test_feedback_register_has_fixed_denominator(self):
        intake = load("program/maturity-evolution/FEEDBACK-INTAKE.json")
        self.assertEqual(intake["fixed_denominator"], 56)
        self.assertEqual(len(intake["requirements"]), 56)
        self.assertEqual(len({row["id"] for row in intake["requirements"]}), 56)

    def test_thr_manifest_keeps_commitments_separate(self):
        folder = ROOT / "program" / "maturity-evolution"
        names = ["FEEDBACK-INTAKE.json", "REALIZATION-CONTRACT.json",
                 "AMCAS-CONTRACT.json", "INTEGRATION-IR.json",
                 "CAMPAIGN-CHARTER.json", "WORK-PACKAGE.json"]
        payloads = {name: (folder / name).read_bytes().rstrip(b"\n") for name in names}
        manifest = load("program/maturity-evolution/THR-MANIFEST.json")
        self.assertEqual(verify_thr_manifest(manifest, payloads=payloads), manifest)
        self.assertEqual(len(set(manifest["commitments"].values())), 5)

    def test_multisession_recovery_demo_does_not_redispatch(self):
        from tools.run_recovery_demo import run
        with tempfile.TemporaryDirectory() as raw:
            result = run(Path(raw) / "result")
        self.assertEqual(result["status"], "PASS_RECOVERED_WITHOUT_REDISPATCH")
        self.assertFalse(result["redispatch_performed"])


if __name__ == "__main__":
    unittest.main()

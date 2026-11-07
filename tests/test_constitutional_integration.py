from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from uclop.canonical import canonical_bytes, root, strict_loads
from ucm.amcas import BOUNDARY
from ucm.application_capsule import build_application_capsule, validate_application_capsule
from ucm.constitutional_runtime import (
    ConstitutionalIntegrationRuntime,
    build_adapter_result,
    build_semantic_gravity,
    validate_adapter_result,
)
from ucm.integration_control import build_control_plan, build_control_result, validate_control_plan
from ucm.integration_observatory import build_observatory
from ucm.operation_gateway import (
    DISPATCH_SCHEMA, PERMIT_SCHEMA, REVOCATION_SCHEMA, TERMINAL_SCHEMA,
    build_operation_contract,
)
from ucm.progress import Progress

ISSUER = Ed25519PrivateKey.from_private_bytes(b"\x41" * 32)
EXECUTOR = Ed25519PrivateKey.from_private_bytes(b"\x42" * 32)
POLICY = strict_loads((Path(__file__).resolve().parents[1] /
    'policy-packs/CONSTITUTIONAL-INTEGRATION-BASE-v0.1.json').read_bytes())


def public(key):
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def signed(body, key, root_field):
    signature = key.sign(canonical_bytes(body)).hex()
    return {**body, "signature_hex": signature,
            root_field: root({**body, "signature_hex": signature})}


def fixture(now=100, request_root=None):
    request_root = request_root or root({"read": "custody"})
    jurisdiction = root({"jurisdiction": "MEMORY_VAULT_PILOT"})
    revocation = signed({
        "schema": REVOCATION_SCHEMA, "issuer_public_key_hex": public(ISSUER),
        "jurisdiction_root": jurisdiction, "generation": 1, "sequence": 1,
        "valid_at": now, "revoked_permit_roots": [], "predecessor_root": "0" * 64,
        **BOUNDARY,
    }, ISSUER, "revocation_registry_root")
    permit = signed({
        "schema": PERMIT_SCHEMA, "permit_id": "permit:memory-vault:pilot",
        "issuer_public_key_hex": public(ISSUER),
        "subject_identity_root": root({"subject": "memory-vault"}),
        "session_root": root({"session": "pilot"}),
        "jurisdiction_root": jurisdiction, "application_id": "MOSAIC.MEMORY_VAULT",
        "action_id": "READ_EVIDENCE", "request_root": request_root,
        "executor_public_key_hex": public(EXECUTOR),
        "allowed_effect_classes": ["READ_STATE"],
        "budget": {"max_cases": 1, "max_duration_ms": 10000, "max_output_bytes": 4096},
        "rollback_root": root({"rollback": "not-required-read-only"}),
        "generation": 1, "nonce": root({"nonce": 41}), "issued_at": 90,
        "not_before": 95, "expires_at": 200,
        "revocation_registry_root": revocation["revocation_registry_root"], **BOUNDARY,
    }, ISSUER, "permit_root")
    contract = build_operation_contract(
        operation_id="op:memory-vault:pilot", permit=permit,
        revocation_registry=revocation, expected_issuer_public_key_hex=public(ISSUER),
        expected_jurisdiction_root=jurisdiction,
        expected_revocation_registry_root=revocation["revocation_registry_root"],
        requested_effect_classes=["READ_STATE"], idempotency_key=root({"idempotency": 41}),
        expected_result_root=root({"vault": "custody-pass"}), now=now)
    return revocation, contract


def adapter(protocol, subject_root, suffix):
    return build_adapter_result(adapter_id=f"adapter:{suffix}", protocol_id=protocol,
        provider_root=root({"provider": suffix}), version="0.1", subject_root=subject_root,
        policy_root=root({"policy": suffix}), input_root=root({"input": suffix}),
        decision="PASS", reason_codes=["NATIVE_CHECK_PASS"],
        evidence_roots=[root({"evidence": suffix})], disposition="ADAPT")


class ConstitutionalIntegrationTests(unittest.TestCase):
    def test_adapter_protocols_keep_evs_jurisdictions_separate(self):
        subject = root({"subject": "x"})
        event = adapter("EVS_EVENT_EVIDENCE_STREAM", subject, "event")
        verification = adapter("EVS_EVIDENCE_VERIFICATION_SUBSYSTEM", subject, "verify")
        self.assertEqual(validate_adapter_result(event), event)
        self.assertNotEqual(event["protocol_id"], verification["protocol_id"])
        self.assertNotEqual(event["adapter_result_root"], verification["adapter_result_root"])

    def test_full_three_gate_positive_flow_preserves_external_executor(self):
        subject = root({"source": "memory-vault-runtime-pilot"})
        reports = [adapter("UGK", subject, "ugk"),
                   adapter("EVS_EVIDENCE_VERIFICATION_SUBSYSTEM",
                           subject, "evs")]
        capsule = build_application_capsule(application_id="MOSAIC.MEMORY_VAULT",
            source_root=subject, amcas_plan={"plan_root": root({"plan": "runtime-pilot"})},
            runtime_contract_root=root({"runtime": "constitutional-integration-v0.1"}),
            policy_pack_roots=[POLICY["policy_pack_root"]], adapter_results=reports,
            active_surfaces=["INTEGRATION_PREPARE", "INTEGRATION_STATE"],
            integration_commands=["ucm integration-validate-capsule"])
        revocation, contract = fixture(request_root=capsule["capsule_root"])
        with tempfile.TemporaryDirectory() as raw:
            progress = Progress(Path(raw) / "progress.jsonl")
            runtime = ConstitutionalIntegrationRuntime(Path(raw) / "runtime", progress=progress)
            prepared = runtime.prepare(contract, application_capsule=capsule,
                adapter_results=reports,
                integration_policy=POLICY,
                expected_integration_policy_root=POLICY["policy_pack_root"],
                expected_issuer_public_key_hex=public(ISSUER),
                expected_jurisdiction_root=contract["jurisdiction_root"],
                expected_revocation_registry_root=revocation["revocation_registry_root"])
            self.assertFalse(prepared["native_executor_selected_by_ucm"])
            self.assertEqual(prepared["application_capsule_root"], capsule["capsule_root"])
            dispatch_body = {"schema": DISPATCH_SCHEMA,
                "operation_id": contract["operation_id"],
                "contract_root": contract["contract_root"],
                "g1_root": prepared["gateway_g1_root"],
                "dispatch_authorization_root": prepared["dispatch_authorization_root"],
                "idempotency_key": contract["idempotency_key"],
                "dispatch_nonce": prepared["dispatch_nonce"],
                "started_at": 101, "status": "DISPATCHED", **BOUNDARY}
            dispatched = runtime.record_dispatch(contract["operation_id"],
                                                   signed(dispatch_body, EXECUTOR, "receipt_root"))
            terminal_body = {"schema": TERMINAL_SCHEMA,
                "operation_id": contract["operation_id"],
                "contract_root": contract["contract_root"],
                "dispatch_root": dispatched["dispatch_receipt"]["receipt_root"],
                "terminal_status": "COMPLETED", "result_root": contract["expected_result_root"],
                "output_bytes": 128, "completed_cases": 1,
                "observed_effect_classes": ["READ_STATE"], "ended_at": 102,
                "receipt_nonce": root({"receipt": 102}), **BOUNDARY}
            completed = runtime.record_terminal(contract["operation_id"],
                signed(terminal_body, EXECUTOR, "receipt_root"), adapter_results=reports,
                integration_policy=POLICY,
                expected_integration_policy_root=POLICY["policy_pack_root"])
            self.assertEqual(completed["terminal_state"], "COMPLETED")
            self.assertEqual(completed["g2_semantic_gravity"]["decision"], "ALLOW")
            self.assertEqual(completed["g3_semantic_gravity"]["decision"], "ALLOW")
            self.assertTrue((Path(raw) / "progress.jsonl").exists())

    def test_semantic_gravity_refuses_missing_required_plane_before_gateway(self):
        _, contract = fixture()
        gravity = build_semantic_gravity(gate="G1_SENTINEL", contract=contract,
            adapter_results=[adapter("UGK", contract["request_root"], "ugk")],
            required_protocols=["SRSA", "UGK"],
            integration_policy_root=POLICY["policy_pack_root"], receipt_roots=[])
        self.assertEqual(gravity["decision"], "REFUSE")
        self.assertEqual(gravity["missing_protocols"], ["SRSA"])

    def test_fixed_denominator_control_plan_and_result(self):
        plan = build_control_plan(subject_root=root({"subject": "batch"}),
            finding_ids=["F-1", "F-2"], impact_surface_ids=["SURFACE.A", "SURFACE.B"],
            test_ids=["TEST.A", "TEST.B"], selected_lanes=["STATIC", "TARGETED"],
            progress_contract_root=root({"progress": "nonsemantic"}),
            qualification_required=False)
        self.assertEqual(validate_control_plan(plan), plan)
        result = build_control_result(plan=plan,
            test_results=[{"test_id": name, "status": "PASS",
                           "evidence_root": root({"test": name})}
                          for name in plan["test_ids"]],
            finding_dispositions=[{"finding_id": name, "disposition": "CLOSED",
                                   "evidence_roots": [root({"finding": name})]}
                                  for name in plan["finding_ids"]])
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["completed_denominator"], result["fixed_denominator"])

    def test_capsule_and_observatory_are_read_only_and_non_authorizing(self):
        subject = root({"source": "memory-vault"})
        report = adapter("COP", subject, "cop")
        capsule = build_application_capsule(application_id="MOSAIC.MEMORY_VAULT",
            source_root=subject, amcas_plan={"plan_root": root({"plan": 1})},
            runtime_contract_root=root({"runtime": 1}),
            policy_pack_roots=[root({"pack": 1})], adapter_results=[report],
            active_surfaces=["INTEGRATION_PREPARE", "INTEGRATION_STATE"],
            integration_commands=["ucm integration-runtime-prepare", "ucm integration-observatory"])
        self.assertEqual(validate_application_capsule(capsule), capsule)
        head_body = {"schema": "mosaic.ucm.integration-journal-head.v0.1",
            "sequence": 0, "head": "0" * 64,
            "events_sha256": root({"events": []}), **BOUNDARY}
        head = {**head_body, "root": root(head_body)}
        observation = build_observatory(capsules=[capsule], operation_states=[],
            journal_heads=[head])
        self.assertTrue(observation["read_only"])
        self.assertEqual(observation["authority_effect"], "NONE")
        self.assertEqual(observation["journal_head_roots"], [head["root"]])
        self.assertFalse(capsule["execution_authorized"])


    def test_public_cli_validation_and_help_are_observation_only(self):
        import json
        import os
        import subprocess
        import sys
        subject = root({"subject": "cli"})
        report = adapter("UGK", subject, "cli")
        capsule = build_application_capsule(application_id="MOSAIC.CLI_FIXTURE",
            source_root=subject, amcas_plan={"plan_root": root({"plan": "cli"})},
            runtime_contract_root=root({"runtime": "cli"}),
            policy_pack_roots=[root({"pack": "cli"})], adapter_results=[report],
            active_surfaces=["INTEGRATION_STATE"],
            integration_commands=["ucm integration-validate-capsule"])
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            adapter_path = workspace / "adapter.json"
            capsule_path = workspace / "capsule.json"
            adapter_path.write_bytes(canonical_bytes(report))
            capsule_path.write_bytes(canonical_bytes(capsule))
            env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
                   "PYTHONDONTWRITEBYTECODE": "1"}
            for command, path in (("integration-validate-adapter", adapter_path),
                                  ("integration-validate-capsule", capsule_path)):
                result = subprocess.run([sys.executable, "-m", "ucm.cli", command, str(path)],
                    cwd=workspace, env=env, capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["standing"], "INFORMATION_ONLY")
            before = sorted(p.name for p in workspace.iterdir())
            result = subprocess.run([sys.executable, "-m", "ucm.cli", "integration-observatory", "--help"],
                cwd=workspace, env=env, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(before, sorted(p.name for p in workspace.iterdir()))

    def test_portable_sdk_imports_from_clean_extraction(self):
        import hashlib
        import os
        import subprocess
        import sys
        import zipfile
        from tools.build_constitutional_integration_kit import build
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            archive_path = workspace / "kit.zip"
            result = build(archive_path)
            self.assertEqual(result["status"], "PASS")
            extracted = workspace / "extracted"
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(extracted)
            manifest = strict_loads((extracted / "sdk/SDK-SOURCE-MANIFEST.json").read_bytes())
            for row in manifest["files"]:
                content = (extracted / "sdk" / row["path"]).read_bytes()
                self.assertEqual(len(content), row["bytes"])
                self.assertEqual(hashlib.sha256(content).hexdigest(), row["sha256"])
            env = {**os.environ,
                   "PYTHONPATH": str(extracted / "sdk/src"),
                   "PYTHONDONTWRITEBYTECODE": "1"}
            completed = subprocess.run([sys.executable, "-c",
                "from ucm.constitutional_runtime import ConstitutionalIntegrationRuntime; "
                "from ucm.application_capsule import validate_application_capsule; "
                "print('PORTABLE_SDK_IMPORT_PASS')"],
                cwd=extracted, env=env, capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("PORTABLE_SDK_IMPORT_PASS", completed.stdout)

    def test_capability_abi_exposes_verify_only_integration_surfaces(self):
        from ucm.capabilities import invoke
        from ucm.profiles import profile_registry
        subject = root({"subject": "abi"})
        report = adapter("UGK", subject, "abi")
        surface = "VALIDATE_NATIVE_CONTROL_PLANE_RESULT"
        payload = {"adapter_result": report}
        request = {"schema": "mosaic.ucm.request.v0.2", "surface": surface,
                   "payload": payload,
                   "profile_selection": {"schema": "mosaic.ucm.product-profile-selection.v0.1",
                       "profile_id": "VERIFY_ONLY",
                       "capability_registry_root": profile_registry()["capability_registry_root"]},
                   "request_id": root({"surface": surface, "payload": payload})}
        response = invoke(request)
        self.assertEqual(response["result"], report)
        self.assertEqual(response["effect_scope"], "PURE_COMPUTATION")

if __name__ == "__main__":
    unittest.main()

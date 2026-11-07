from __future__ import annotations

import tempfile
from pathlib import Path
import json
import subprocess
import sys
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from uclop.canonical import Refusal, canonical_bytes, root
from ucm.amcas import BOUNDARY
from ucm.capabilities import invoke
from ucm.dependency_graph import (build_graph, build_producer_receipt,
                                  build_snapshot, evaluate_graph)
from ucm.operation_gateway import (PERMIT_SCHEMA, REVOCATION_SCHEMA,
                                   OperationGateway, build_operation_contract)
from ucm.pippi import (build_model_draft, build_pippi_context,
                       build_pippi_decision)
from ucm.pippi_work_units import (build_work_selection,
                                  validate_acceptance_case)
from ucm.ugel import (UGEL_SOURCE_ARCHIVE_SHA256, UGEL_SOURCE_ROOT,
                      build_component_policy, build_dispatch_receipt_body,
                      build_executor_binding, build_guest_call,
                      build_terminal_receipt_body, compile_correspondence,
                      evaluate_reference_sim_add, executor_pack_registry)


ISSUER = Ed25519PrivateKey.from_private_bytes(b"\x71" * 32)
EXECUTOR = Ed25519PrivateKey.from_private_bytes(b"\x72" * 32)
ROOT_DIR = Path(__file__).resolve().parents[1]


def public(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def signed(body: dict, key: Ed25519PrivateKey, root_field: str) -> dict:
    signature = key.sign(canonical_bytes(body)).hex()
    return {**body, "signature_hex": signature,
            root_field: root({**body, "signature_hex": signature})}


def graph_node(node_id: str) -> dict:
    return {
        "node_id": node_id, "kind": "INPUT", "dependencies": [],
        "parameters": {}, "transform_id": "UGEL_EXTERNAL_RECEIPT",
        "transform_version": "v0.1",
        "semantic_contract_root": root({"semantic": "sim.add"}),
        "policy_root": root({"policy": "ugel-r022"}),
        "jurisdiction_root": root({"jurisdiction": "ugel-pilot"}),
        "environment_root": root({"environment": "reference-simulator"}),
        "closure_coverage": "COMPLETE", "evidence_grade": "CAPTURED_OBSERVATION",
        "pure": False,
    }


class UgelIntegrationTests(unittest.TestCase):
    def fixture(self):
        policy = build_component_policy(
            component_sha256=root({"component": "sim-add-reference"}),
            contract_root=root({"ugel_execution_contract": "sim-add-v0.1"}),
            allowed_effects=["sim.add"], resource_ids=["calculator:primary"],
            allowed_actions=["RUN"], max_text_bytes=0)
        call = build_guest_call(
            policy=policy, action="RUN", operation_id="op:ugel:sim-add:r022",
            effect_id="sim.add", resource_id="calculator:primary",
            parameters={"left": 20, "right": 22},
            evidence_roots=[root({"acceptance_case": "UGEL-R022-01"})])
        expected = evaluate_reference_sim_add(guest_call=call, policy=policy)
        jurisdiction = root({"jurisdiction": "UGEL_REFERENCE_PILOT"})
        revocation = signed({
            "schema": REVOCATION_SCHEMA,
            "issuer_public_key_hex": public(ISSUER),
            "jurisdiction_root": jurisdiction, "generation": 1,
            "sequence": 1, "valid_at": 100, "revoked_permit_roots": [],
            "predecessor_root": "0" * 64, **BOUNDARY,
        }, ISSUER, "revocation_registry_root")
        permit = signed({
            "schema": PERMIT_SCHEMA, "permit_id": "permit:ugel:sim-add:r022",
            "issuer_public_key_hex": public(ISSUER),
            "subject_identity_root": root({"subject": "ugel-reference-pilot"}),
            "session_root": root({"session": "ugel-r022"}),
            "jurisdiction_root": jurisdiction, "application_id": "MOSAIC.UCM",
            "action_id": "UGEL_SIM_ADD", "request_root": call["request_root"],
            "executor_public_key_hex": public(EXECUTOR),
            "allowed_effect_classes": ["PROCESS"],
            "budget": {"max_cases": 1, "max_duration_ms": 10000,
                       "max_output_bytes": 4096},
            "rollback_root": root({"rollback": "pure-reference-none"}),
            "generation": 1, "nonce": root({"nonce": "ugel-r022"}),
            "issued_at": 90, "not_before": 95, "expires_at": 200,
            "revocation_registry_root": revocation["revocation_registry_root"],
            **BOUNDARY,
        }, ISSUER, "permit_root")
        contract = build_operation_contract(
            operation_id="op:ugel:sim-add:r022", permit=permit,
            revocation_registry=revocation,
            expected_issuer_public_key_hex=public(ISSUER),
            expected_jurisdiction_root=jurisdiction,
            expected_revocation_registry_root=revocation["revocation_registry_root"],
            requested_effect_classes=["PROCESS"],
            idempotency_key=root({"idempotency": "ugel-r022"}),
            expected_result_root=expected["result_root"], now=100)
        binding = build_executor_binding(
            executor_public_key_hex=public(EXECUTOR),
            source_archive_sha256=UGEL_SOURCE_ARCHIVE_SHA256,
            source_root=UGEL_SOURCE_ROOT,
            evidence_roots=[root({"custody": UGEL_SOURCE_ARCHIVE_SHA256})])
        context = build_pippi_context(
            session_root=contract["session_root"],
            subject_root=contract["subject_identity_root"],
            policy_roots=[root({"pippi_policy": "ugel-r022"})],
            capability_registry_root=root({"registry": "r022"}),
            profile_root=root({"profile": "OPERATIONAL"}),
            jurisdiction_root=jurisdiction, retained_context_roots=[],
            mediated_channels=["MODEL_DRAFT", "TOOL_PROPOSAL"])
        draft = build_model_draft(
            turn_id="turn:ugel:r022:1", context=context,
            text="Prepare the declared sim.add operation through the external executor.",
            proposals=[{"proposal_id": "proposal:sim-add", "kind": "TOOL_CALL",
                        "payload_root": call["request_root"],
                        "effect_class": "LOCAL_ARTIFACT_PREPARATION"}])
        decision = build_pippi_decision(
            draft=draft,
            policy_evaluation_roots=[root({"policy_evaluation": "pass"})],
            proposal_dispositions=[{
                "proposal_id": "proposal:sim-add", "declared": True,
                "effectful": True, "decision": "PASS",
                "reason_codes": ["EXTERNAL_EXECUTOR_BOUND",
                                 "OPERATIONAL_CONTRACT_PRESENT"],
                "contract_root": contract["contract_root"],
            }], semantic_resolution_root=None, semantic_status="NOT_REQUIRED")
        correspondence = compile_correspondence(
            pippi_decision=decision, proposal_id="proposal:sim-add",
            operational_contract=contract, executor_binding=binding,
            component_policy=policy, guest_call=call)
        return policy, call, expected, revocation, contract, binding, decision, correspondence

    def test_registry_and_authoring_abi_keep_executor_external(self):
        registry = executor_pack_registry()
        self.assertEqual(registry["native_wasi_runtime_status"], "NOT_BOUND")
        self.assertFalse(registry["executor_selected_by_ucm"])
        response = invoke({"schema": "mosaic.ucm.request.v0.1",
                           "surface": "DISCOVER_UGEL_EXECUTOR_PACK",
                           "payload": {}, "request_id": "ugel-r022-discovery"})
        self.assertEqual(response["result"], registry)
        self.assertEqual(response["authority_effect"], "NONE")

    def test_call_text_limit_is_enforced_before_correspondence(self):
        policy = build_component_policy(
            component_sha256=root({"component": "text-limit"}),
            contract_root=root({"contract": "text-limit"}),
            allowed_effects=["sim.add"], resource_ids=["calculator:primary"],
            allowed_actions=["RUN"], max_text_bytes=3)
        with self.assertRaisesRegex(Refusal, "UGEL_CALL_TEXT_LIMIT"):
            build_guest_call(
                policy=policy, action="RUN", operation_id="op:ugel:text-limit",
                effect_id="sim.add", resource_id="calculator:primary",
                parameters={"left": 1, "right": 2, "text": "four"},
                evidence_roots=[])

    def test_terminal_body_recomputes_result_and_correspondence_roots(self):
        (policy, call, result, _revocation, contract, _binding, _decision,
         correspondence) = self.fixture()
        tampered_result = {**result, "output": {"sum": 99}}
        with self.assertRaisesRegex(Refusal,
                                    "UGEL_REFERENCE_RESULT_ROOT_INVALID"):
            build_terminal_receipt_body(
                correspondence=correspondence,
                operational_contract=contract,
                dispatch_receipt_root=root({"dispatch": "r023"}),
                result=tampered_result, ended_at=102)
        tampered_correspondence = {**correspondence,
                                   "expected_result_root": root({"wrong": 1})}
        with self.assertRaisesRegex(Refusal, "UGEL_CORRESPONDENCE_INVALID"):
            build_terminal_receipt_body(
                correspondence=tampered_correspondence,
                operational_contract=contract,
                dispatch_receipt_root=root({"dispatch": "r023"}),
                result=result, ended_at=102)

    def test_program_records_rebuild_and_name_this_acceptance_case(self):
        root_dir = Path(__file__).resolve().parents[1]
        program_dir = root_dir / "program" / "ugel-executor-r022"
        case = json.loads((program_dir / "UGEL-R022-01-ACCEPTANCE-CASE.json").read_text())
        selection = json.loads((program_dir / "UGEL-R022-01-WORK-SELECTION.json").read_text())
        self.assertEqual(validate_acceptance_case(case), case)
        rebuilt = build_work_selection(
            acceptance_case=case, work_class="DIRECT_ACCEPTANCE_CLOSURE",
            direct_closure_check_id=case["verification_surface"],
            infrastructure_block=None)
        self.assertEqual(rebuilt, selection)
        check = subprocess.run(
            [sys.executable, "-I", str(root_dir / "tools" / "build_ugel_r022_program.py"), "--check"],
            cwd=root_dir, text=True, capture_output=True)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_sim_add_crosses_pippi_gateway_receipts_and_dependency_evidence(self):
        (policy, call, expected, revocation, contract, _binding, _decision,
         correspondence) = self.fixture()
        self.assertNotEqual(correspondence["ugel_domain_root"],
                            correspondence["ucm_semantic_root"])
        self.assertEqual(correspondence["root_relation"],
                         "CORRESPONDENCE_NOT_HASH_IDENTITY")
        with tempfile.TemporaryDirectory(dir=ROOT_DIR / ".build") as raw:
            gateway = OperationGateway(Path(raw) / "gateway")
            prepared = gateway.prepare(
                contract, expected_issuer_public_key_hex=public(ISSUER),
                expected_jurisdiction_root=contract["jurisdiction_root"],
                expected_revocation_registry_root=revocation["revocation_registry_root"])
            dispatch_body = build_dispatch_receipt_body(
                correspondence=correspondence, operational_contract=contract,
                dispatch_authorization=prepared["dispatch_authorization"],
                started_at=101)
            dispatch = gateway.record_dispatch(
                contract["operation_id"], signed(dispatch_body, EXECUTOR, "receipt_root"))
            result = evaluate_reference_sim_add(guest_call=call, policy=policy)
            self.assertEqual(result, expected)
            terminal_body = build_terminal_receipt_body(
                correspondence=correspondence, operational_contract=contract,
                dispatch_receipt_root=dispatch["dispatch_receipt"]["receipt_root"],
                result=result, ended_at=102)
            terminal = gateway.record_terminal(
                contract["operation_id"], signed(terminal_body, EXECUTOR, "receipt_root"))
            self.assertEqual(terminal["state"]["state"], "COMPLETED")
            self.assertEqual(terminal["g2"]["gate"], "G2_WITNESS")
            self.assertEqual(terminal["g3"]["gate"], "G3_DIAGNOSTIC")
            graph = build_graph(
                graph_id="ugel:sim-add:r022", nodes=[graph_node("terminal")],
                adapter_id="UGEL_EXECUTOR", adapter_version="v0.1",
                adapter_policy_root=policy["root"],
                schema_registry_root=executor_pack_registry()["registry_root"],
                trust_root=correspondence["executor_binding_root"],
                closure_claim="COMPLETE")
            snapshot = build_snapshot(
                graph=graph, snapshot_id="ugel:sim-add:terminal",
                predecessor_snapshot_root=None,
                inputs=[{"node_id": "terminal", "presence": {"present": True,
                    "value": {"result_root": result["result_root"],
                              "g2_root": terminal["g2"]["receipt_root"],
                              "g3_root": terminal["g3"]["receipt_root"],
                              "state_root": terminal["state"]["state_root"]}}}])
            evaluation = evaluate_graph(graph=graph, snapshot=snapshot)
            producer = build_producer_receipt(
                producer_root=terminal["g3"]["receipt_root"], graph=graph,
                snapshot=snapshot, evaluation=evaluation,
                execution_capsule_root=correspondence["correspondence_root"],
                checker_root=executor_pack_registry()["registry_root"])
            self.assertEqual(producer["authority_effect"], "NONE")
            self.assertEqual(producer["evaluation_root"], evaluation["evaluation_root"])


if __name__ == "__main__":
    unittest.main()

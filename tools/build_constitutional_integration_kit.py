from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from uclop.canonical import canonical_bytes, root, strict_loads
from ucm.amcas import BOUNDARY
from ucm.application_capsule import build_application_capsule
from ucm.artifacts import deterministic_zip, verify_deterministic_zip
from ucm.constitutional_runtime import ConstitutionalIntegrationRuntime, build_adapter_result
from ucm.integration_control import build_control_plan, build_control_result
from ucm.integration_observatory import build_observatory
from ucm.operation_archive import build_operation_archive
from ucm.operation_gateway import (
    DISPATCH_SCHEMA, PERMIT_SCHEMA, REVOCATION_SCHEMA, TERMINAL_SCHEMA,
    build_operation_contract,
)
from ucm.progress import Progress

ISSUER = Ed25519PrivateKey.from_private_bytes(b"\x51" * 32)
EXECUTOR = Ed25519PrivateKey.from_private_bytes(b"\x52" * 32)
SCHEMA = "mosaic.ucm.application-constitutionalization-kit.v0.1"
ROLE = "UCM_APPLICATION_CONSTITUTIONALIZATION_KIT"


def public(key):
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def signed(body, key, root_field):
    signature = key.sign(canonical_bytes(body)).hex()
    return {**body, "signature_hex": signature,
            root_field: root({**body, "signature_hex": signature})}


def adapter(protocol, subject_root, suffix):
    return build_adapter_result(adapter_id=f"memory-vault:{suffix}", protocol_id=protocol,
        provider_root=root({"fixture_provider": suffix}), version="0.1",
        subject_root=subject_root, policy_root=root({"fixture_policy": suffix}),
        input_root=root({"fixture_input": suffix}), decision="PASS",
        reason_codes=["FIXTURE_POSITIVE_CHECK_PASS"],
        evidence_roots=[root({"fixture_evidence": suffix})], disposition="ADAPT")


def fixture(now=100, request_root=None):
    request_root = request_root or root({"read": "custody-fixture"})
    jurisdiction = root({"jurisdiction": "MEMORY_VAULT_CUSTODY_PILOT"})
    revocation = signed({"schema": REVOCATION_SCHEMA,
        "issuer_public_key_hex": public(ISSUER), "jurisdiction_root": jurisdiction,
        "generation": 1, "sequence": 1, "valid_at": now,
        "revoked_permit_roots": [], "predecessor_root": "0" * 64, **BOUNDARY},
        ISSUER, "revocation_registry_root")
    permit = signed({"schema": PERMIT_SCHEMA,
        "permit_id": "permit:memory-vault:custody-pilot",
        "issuer_public_key_hex": public(ISSUER),
        "subject_identity_root": root({"subject": "memory-vault-fixture"}),
        "session_root": root({"session": "integration-kit-c1"}),
        "jurisdiction_root": jurisdiction, "application_id": "MOSAIC.MEMORY_VAULT",
        "action_id": "READ_EVIDENCE", "request_root": request_root,
        "executor_public_key_hex": public(EXECUTOR),
        "allowed_effect_classes": ["READ_STATE"],
        "budget": {"max_cases": 1, "max_duration_ms": 10000, "max_output_bytes": 4096},
        "rollback_root": root({"rollback": "read-only-not-required"}),
        "generation": 1, "nonce": root({"nonce": 51}), "issued_at": 90,
        "not_before": 95, "expires_at": 200,
        "revocation_registry_root": revocation["revocation_registry_root"], **BOUNDARY},
        ISSUER, "permit_root")
    contract = build_operation_contract(operation_id="op:memory-vault:custody-pilot",
        permit=permit, revocation_registry=revocation,
        expected_issuer_public_key_hex=public(ISSUER),
        expected_jurisdiction_root=jurisdiction,
        expected_revocation_registry_root=revocation["revocation_registry_root"],
        requested_effect_classes=["READ_STATE"], idempotency_key=root({"idempotency": 51}),
        expected_result_root=root({"fixture_result": "custody-pass"}), now=now)
    return revocation, contract


def build(out: Path) -> dict:
    plan_path = ROOT / "integration/stage-i3/authoring/plans/MOSAIC-MEMORY_VAULT-STAGE-I3-PLAN.json"
    plan = strict_loads(plan_path.read_bytes())
    policy = strict_loads((ROOT / "policy-packs/CONSTITUTIONAL-INTEGRATION-BASE-v0.1.json").read_bytes())
    spec = strict_loads((ROOT / "spec/UCM-CONSTITUTIONAL-INTEGRATION-RUNTIME-v0.1.json").read_bytes())
    source_root = root({"application_id": plan["application_id"],
                        "subject_binding": "UNBOUND_FIXTURE"})
    reports = [adapter("UGK", source_root, "ugk"),
               adapter("EVS_EVIDENCE_VERIFICATION_SUBSYSTEM",
                       source_root, "verification")]
    capsule = build_application_capsule(application_id=plan["application_id"],
        source_root=source_root, amcas_plan=plan,
        runtime_contract_root=spec["contract_root"],
        policy_pack_roots=[policy["policy_pack_root"]], adapter_results=reports,
        active_surfaces=["INTEGRATION_OBSERVATORY", "INTEGRATION_PREPARE",
                        "INTEGRATION_STATE"],
        integration_commands=["ucm integration-validate-adapter",
                              "ucm integration-validate-capsule",
                              "ucm integration-observatory"])
    revocation, contract = fixture(request_root=capsule["capsule_root"])
    with tempfile.TemporaryDirectory(prefix="ucm-integration-kit-") as raw:
        workspace = Path(raw)
        runtime = ConstitutionalIntegrationRuntime(workspace / "runtime",
            progress=Progress(workspace / "PROGRESS.jsonl"))
        prepared = runtime.prepare(contract, application_capsule=capsule,
            adapter_results=reports,
            integration_policy=policy,
            expected_integration_policy_root=policy["policy_pack_root"],
            expected_issuer_public_key_hex=public(ISSUER),
            expected_jurisdiction_root=contract["jurisdiction_root"],
            expected_revocation_registry_root=revocation["revocation_registry_root"])
        dispatch = signed({"schema": DISPATCH_SCHEMA,
            "operation_id": contract["operation_id"], "contract_root": contract["contract_root"],
            "g1_root": prepared["gateway_g1_root"],
            "dispatch_authorization_root": prepared["dispatch_authorization_root"],
            "idempotency_key": contract["idempotency_key"],
            "dispatch_nonce": prepared["dispatch_nonce"], "started_at": 101,
            "status": "DISPATCHED", **BOUNDARY}, EXECUTOR, "receipt_root")
        dispatched = runtime.record_dispatch(contract["operation_id"], dispatch)
        terminal = signed({"schema": TERMINAL_SCHEMA,
            "operation_id": contract["operation_id"], "contract_root": contract["contract_root"],
            "dispatch_root": dispatched["dispatch_receipt"]["receipt_root"],
            "terminal_status": "COMPLETED", "result_root": contract["expected_result_root"],
            "output_bytes": 128, "completed_cases": 1,
            "observed_effect_classes": ["READ_STATE"], "ended_at": 102,
            "receipt_nonce": root({"terminal_receipt": 51}), **BOUNDARY},
            EXECUTOR, "receipt_root")
        completed = runtime.record_terminal(contract["operation_id"], terminal,
            adapter_results=reports, integration_policy=policy,
            expected_integration_policy_root=policy["policy_pack_root"])
        state = runtime.state(contract["operation_id"])
        operation_archive = build_operation_archive(runtime.gateway,
            operation_id=contract["operation_id"],
            expected_issuer_public_key_hex=public(ISSUER),
            expected_jurisdiction_root=contract["jurisdiction_root"],
            expected_revocation_registry_root=revocation["revocation_registry_root"])
        control = build_control_plan(subject_root=capsule["capsule_root"],
            finding_ids=["C1-BOUNDARY", "C1-CUSTODY", "C1-GATES"],
            impact_surface_ids=capsule["active_surfaces"],
            test_ids=["TEST.ADAPTERS", "TEST.CAPSULE", "TEST.CONTROL",
                     "TEST.GATE_FLOW", "TEST.OBSERVATORY"],
            selected_lanes=["STATIC", "TARGETED"],
            progress_contract_root=root({"schema": "mosaic.ucm.nonsemantic-progress.v0.1"}),
            qualification_required=False)
        evidence = root({"positive_test_suite": "tests/test_constitutional_integration.py"})
        control_result = build_control_result(plan=control,
            test_results=[{"test_id": test_id, "status": "PASS", "evidence_root": evidence}
                         for test_id in control["test_ids"]],
            finding_dispositions=[{"finding_id": finding_id, "disposition": "CLOSED",
                                   "evidence_roots": [evidence]}
                                  for finding_id in control["finding_ids"]])
        head = runtime.gateway.journal.head()
        observatory = build_observatory(capsules=[capsule], operation_states=[state],
                                       journal_heads=[head])
        pilot_body = {"schema": "mosaic.ucm.memory-vault-custody-pilot.v0.1",
                      "capsule_root": capsule["capsule_root"],
                      "preparation_root": prepared["preparation_root"],
                      "completion_root": completed["completion_root"],
                      "operation_state_root": state["state_root"],
                      "control_result_root": control_result["control_result_root"],
                      "observatory_root": observatory["observatory_root"],
                      "journal_head_root": head["root"],
                      "operation_archive_sha256": hashlib.sha256(operation_archive).hexdigest(),
                      "external_effect_executed": False,
                      "fixture_receipts_exercised": True,
                      "status": "PASS", **BOUNDARY}
        pilot = {**pilot_body, "pilot_root": root(pilot_body)}
    payloads = {
        "README.md": (ROOT / "examples/constitutional-integration/README.md").read_bytes(),
        "docs/CONSTITUTIONAL-INTEGRATION-REVIEW-WORK-ORDER.md": (ROOT / "docs/CONSTITUTIONAL-INTEGRATION-REVIEW-WORK-ORDER.md").read_bytes(),
        "docs/CONSTITUTIONAL-INTEGRATION-RUNTIME.md":
            (ROOT / "docs/CONSTITUTIONAL-INTEGRATION-RUNTIME.md").read_bytes(),
        "spec/UCM-CONSTITUTIONAL-INTEGRATION-RUNTIME-v0.1.json": canonical_bytes(spec),
        "policy/CONSTITUTIONAL-INTEGRATION-BASE-v0.1.json": canonical_bytes(policy),
        "pilot/README.md": (ROOT / "examples/constitutional-integration/memory-vault-custody/README.md").read_bytes(),
        "pilot/AMCAS-PLAN.json": canonical_bytes(plan),
        "pilot/APPLICATION-CAPSULE.json": canonical_bytes(capsule),
        "pilot/ADAPTER-RESULTS.json": canonical_bytes(reports),
        "pilot/CONTROL-PLAN.json": canonical_bytes(control),
        "pilot/CONTROL-RESULT.json": canonical_bytes(control_result),
        "pilot/OBSERVATORY.json": canonical_bytes(observatory),
        "pilot/INTEGRATION-PREPARATION.json": canonical_bytes(prepared),
        "pilot/INTEGRATION-COMPLETION.json": canonical_bytes(completed),
        "pilot/OPERATION-STATE.json": canonical_bytes(state),
        "pilot/JOURNAL-HEAD.json": canonical_bytes(head),
        "pilot/PILOT-RESULT.json": canonical_bytes(pilot),
        "pilot/OPERATION-ARCHIVE.zip": operation_archive,
    }
    sdk_rows = []
    for path in sorted((ROOT / "src").rglob("*")):
        if (not path.is_file() or "__pycache__" in path.parts
                or path.suffix in {".pyc", ".pyo"}):
            continue
        relative = path.relative_to(ROOT).as_posix()
        content = path.read_bytes()
        payloads[f"sdk/{relative}"] = content
        sdk_rows.append({"path": relative, "bytes": len(content),
                         "sha256": hashlib.sha256(content).hexdigest()})
    for name in ("pyproject.toml", "LICENSE"):
        content = (ROOT / name).read_bytes()
        payloads[f"sdk/{name}"] = content
        sdk_rows.append({"path": name, "bytes": len(content),
                         "sha256": hashlib.sha256(content).hexdigest()})
    sdk_rows.sort(key=lambda row: row["path"])
    sdk_body = {"schema": "mosaic.ucm.portable-python-sdk-manifest.v0.1",
                "files": sdk_rows, "file_count": len(sdk_rows),
                "source_manifest_root": root(sdk_rows), **BOUNDARY}
    sdk_manifest = {**sdk_body, "sdk_manifest_root": root(sdk_body)}
    payloads["sdk/SDK-SOURCE-MANIFEST.json"] = canonical_bytes(sdk_manifest)
    raw = deterministic_zip(payloads, schema=SCHEMA, artifact_role=ROLE)
    verify_deterministic_zip(raw, expected_schema=SCHEMA, expected_role=ROLE)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)
    return {"status": "PASS", "path": str(out), "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw), "pilot_root": pilot["pilot_root"],
            "capsule_root": capsule["capsule_root"],
            "sdk_manifest_root": sdk_manifest["sdk_manifest_root"],
            "sdk_file_count": sdk_manifest["file_count"], **BOUNDARY}


def main():
    parser = argparse.ArgumentParser(description="Build the deterministic UCM application constitutionalization kit")
    parser.add_argument("--out", type=Path,
        default=ROOT / "dist/UCM-APPLICATION-CONSTITUTIONALIZATION-KIT-C1.zip")
    args = parser.parse_args()
    import json
    print(json.dumps(build(args.out), sort_keys=True))


if __name__ == "__main__":
    main()

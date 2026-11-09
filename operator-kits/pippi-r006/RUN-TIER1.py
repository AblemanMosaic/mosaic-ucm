#!/usr/bin/env python3
"""Operator-run adversarial court for the P/PPI r006 repair boundary.

This file is builder-authored review material.  The release builder may syntax
check it, but only the operator launcher executes its cases.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import zipfile


FIXED_TIME = (1980, 1, 1, 0, 0, 0)
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def zip_bytes(payloads: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for name in sorted(payloads):
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, payloads[name])
    return output.getvalue()


def signed(body: dict, key, root_field: str) -> dict:
    from uclop.canonical import canonical_bytes, root
    signature = key.sign(canonical_bytes(body)).hex()
    return {**body, "signature_hex": signature,
            root_field: root({**body, "signature_hex": signature})}


def public(key) -> str:
    from cryptography.hazmat.primitives import serialization
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def fixture():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from uclop.canonical import canonical_bytes, root
    from ucm.amcas import BOUNDARY as UCM_BOUNDARY
    from ucm.operation_gateway import REVOCATION_SCHEMA
    from ucm.pippi_host import (CHANNELS, HOST_ATTESTATION_SCHEMA,
                                build_host_adapter_policy,
                                build_host_mediation_attestation)
    attestor = Ed25519PrivateKey.from_private_bytes(b"\x41" * 32)
    issuer = Ed25519PrivateKey.from_private_bytes(b"\x42" * 32)
    executor = Ed25519PrivateKey.from_private_bytes(b"\x43" * 32)
    session_root = root({"operator": "pippi-r006", "kind": "session"})
    project_root = root({"operator": "pippi-r006", "kind": "project"})
    jurisdiction_root = root({"jurisdiction": "PIPPI.R006.OPERATOR"})
    revocation_body = {
        "schema": REVOCATION_SCHEMA, "issuer_public_key_hex": public(issuer),
        "jurisdiction_root": jurisdiction_root, "generation": 1, "sequence": 1,
        "valid_at": 100, "revoked_permit_roots": [],
        "predecessor_root": "0" * 64, **UCM_BOUNDARY,
    }
    revocation = signed(revocation_body, issuer, "revocation_registry_root")
    policy = build_host_adapter_policy(
        policy_id="PIPPI.R006.OPERATOR", adapter_registry_root=root({"adapter": "fixture"}),
        attestor_public_key_hex=public(attestor),
        operation_issuer_public_key_hex=public(issuer),
        operation_jurisdiction_root=jurisdiction_root,
        operation_revocation_registry_root=revocation["revocation_registry_root"],
        maximum_validity_ns=1_000)
    unsigned = {
        "schema": HOST_ATTESTATION_SCHEMA, "host_policy_root": policy["host_policy_root"],
        "adapter_id": "PIPPI.R006.FIXTURE", "adapter_source_root": root({"source": "fixture"}),
        "adapter_registry_root": policy["adapter_registry_root"],
        "session_root": session_root, "subject_root": project_root,
        "mediated_channels": sorted(CHANNELS), "issued_at_ns": 100,
        "expires_at_ns": 200, "attestor_public_key_hex": public(attestor),
        "attestation_grants_authority": False, **UCM_BOUNDARY,
    }
    attestation = build_host_mediation_attestation(
        policy=policy, adapter_id=unsigned["adapter_id"],
        adapter_source_root=unsigned["adapter_source_root"],
        session_root=session_root, subject_root=project_root,
        mediated_channels=unsigned["mediated_channels"], issued_at_ns=100,
        expires_at_ns=200, signature_hex=attestor.sign(canonical_bytes(unsigned)).hex())
    return attestor, issuer, executor, revocation, policy, attestation, session_root, project_root


def operation_result(issuer, executor, revocation, policy, attestation, proposal):
    from uclop.canonical import root
    from ucm.amcas import BOUNDARY as UCM_BOUNDARY
    from ucm.operation_gateway import (DISPATCH_SCHEMA, PERMIT_SCHEMA, TERMINAL_SCHEMA,
                                       OperationGateway, build_operation_contract)
    from ucm.operation_proofs import build_operation_proof_bundle
    from ucm.pippi_host import LAUNCH_RESULT_SCHEMA
    projection = {"status": "LAUNCHED", "kind": proposal["kind"]}
    projection_root = root(projection)
    permit_body = {
        "schema": PERMIT_SCHEMA, "permit_id": "permit:pippi-r006-operator",
        "issuer_public_key_hex": public(issuer),
        "subject_identity_root": proposal["project_root"],
        "session_root": proposal["session_root"],
        "jurisdiction_root": policy["operation_jurisdiction_root"],
        "application_id": "PIPPI.DASHBOARD", "action_id": "HOST.APPLICATION",
        "request_root": proposal["proposal_root"],
        "executor_public_key_hex": public(executor),
        "allowed_effect_classes": proposal["requested_effect_classes"],
        "budget": {"max_cases": 1, "max_duration_ms": 10_000, "max_output_bytes": 65_536},
        "rollback_root": root({"rollback": "fixture"}), "generation": 1,
        "nonce": root({"nonce": proposal["proposal_root"]}), "issued_at": 90,
        "not_before": 95, "expires_at": 200,
        "revocation_registry_root": revocation["revocation_registry_root"], **UCM_BOUNDARY,
    }
    permit = signed(permit_body, issuer, "permit_root")
    operation_id = "op:pippi-r006-operator"
    contract = build_operation_contract(
        operation_id=operation_id, permit=permit, revocation_registry=revocation,
        expected_issuer_public_key_hex=public(issuer),
        expected_jurisdiction_root=policy["operation_jurisdiction_root"],
        expected_revocation_registry_root=revocation["revocation_registry_root"],
        requested_effect_classes=proposal["requested_effect_classes"],
        idempotency_key=root({"proposal": proposal["proposal_root"]}),
        expected_result_root=projection_root, now=100)
    with tempfile.TemporaryDirectory(prefix="pippi-r006-operation-") as raw:
        gateway = OperationGateway(Path(raw))
        prepared = gateway.prepare(contract,
            expected_issuer_public_key_hex=public(issuer),
            expected_jurisdiction_root=policy["operation_jurisdiction_root"],
            expected_revocation_registry_root=revocation["revocation_registry_root"])
        dispatch_body = {
            "schema": DISPATCH_SCHEMA, "operation_id": operation_id,
            "contract_root": contract["contract_root"], "g1_root": prepared["g1"]["receipt_root"],
            "dispatch_authorization_root": prepared["dispatch_authorization"]["receipt_root"],
            "idempotency_key": contract["idempotency_key"],
            "dispatch_nonce": prepared["dispatch_authorization"]["dispatch_nonce"],
            "started_at": 101, "status": "DISPATCHED", **UCM_BOUNDARY,
        }
        dispatched = gateway.record_dispatch(operation_id,
            signed(dispatch_body, executor, "receipt_root"))
        terminal_body = {
            "schema": TERMINAL_SCHEMA, "operation_id": operation_id,
            "contract_root": contract["contract_root"],
            "dispatch_root": dispatched["dispatch_receipt"]["receipt_root"],
            "terminal_status": "COMPLETED", "result_root": projection_root,
            "output_bytes": 1, "completed_cases": 1,
            "observed_effect_classes": proposal["requested_effect_classes"],
            "ended_at": 102, "receipt_nonce": root({"receipt": 102}), **UCM_BOUNDARY,
        }
        gateway.record_terminal(operation_id, signed(terminal_body, executor, "receipt_root"))
        events = gateway.journal.verify()
        proof = build_operation_proof_bundle(operation_id=operation_id, events=events,
            expected_issuer_public_key_hex=public(issuer),
            expected_jurisdiction_root=policy["operation_jurisdiction_root"],
            expected_revocation_registry_root=revocation["revocation_registry_root"])
    body = {"schema": LAUNCH_RESULT_SCHEMA, "proposal_root": proposal["proposal_root"],
            "host_attestation_root": attestation["host_attestation_root"],
            "operation_id": operation_id, "events": events, "proof_bundle": proof,
            "result_projection": projection, "result_projection_root": projection_root,
            "status": "PASS", **UCM_BOUNDARY}
    return {**body, "launch_result_root": root(body)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--runtime-archive", type=Path, required=True)
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    runtime = args.runtime.resolve(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(runtime / "src"))
    from uclop.canonical import canonical_bytes, root
    from ucm.pippi import (build_attested_pippi_context, build_pippi_context,
                           effective_integration_mode, validate_pippi_context)
    from ucm.pippi_host import (CHANNELS, build_host_launch_proposal,
                                validate_host_adapter_policy,
                                validate_host_launch_proposal,
                                validate_host_launch_result,
                                validate_host_mediation_attestation)
    from ucm.pippi_integrations import (bind_external_integration,
        default_integration_availability_registry, validate_integration_availability_registry)
    from ucm.system import capability_registry

    manifest = json.loads((runtime / "MANIFEST.json").read_text(encoding="utf-8"))
    qualification = json.loads(args.qualification.read_text(encoding="utf-8"))
    attestor, issuer, executor, revocation, policy, attestation, session_root, project_root = fixture()
    context = build_attested_pippi_context(
        session_root=session_root, subject_root=project_root,
        policy_roots=[policy["host_policy_root"]],
        capability_registry_root=root({"registry": 1}), profile_root=root({"profile": 1}),
        jurisdiction_root=root({"jurisdiction": 1}), retained_context_roots=[],
        expected_host_policy_root=policy["host_policy_root"], host_policy=policy,
        host_attestation=attestation, now_ns=150)
    registry = default_integration_availability_registry()
    bound = bind_external_integration(registry=registry,
        integration_id="UCM_OPERATIONAL_GATEWAY", binding_root=policy["host_policy_root"],
        evidence_roots=[attestation["host_attestation_root"]])
    proposal = build_host_launch_proposal(project_root=project_root,
        session_root=session_root, host_policy_root=policy["host_policy_root"],
        host_attestation_root=attestation["host_attestation_root"], kind="APPLICATION",
        payload={"command": ["fixture.exe"]}, expected_hub_head="0" * 64)
    result = operation_result(issuer, executor, revocation, policy, attestation, proposal)
    rows: list[dict] = []

    def case(case_id: str, action, expected: str | None = None) -> None:
        status = "FAIL"; diagnostic = "UNEXPECTED_PASS"
        try:
            value = action()
            if expected is None:
                status, diagnostic = "PASS", "CONTROL_PASS"
            else:
                diagnostic = f"UNEXPECTED_PASS:{value!r}"
        except Exception as error:
            diagnostic = str(error)
            if expected is not None and expected in diagnostic:
                status = "PASS"
        row = {"case_id": case_id, "status": status, "diagnostic": diagnostic}
        rows.append(row)
        print(f"[case {len(rows):03}] {case_id}: {status}", flush=True)
        print(f"[summary] completed={len(rows)} failed={sum(r['status']!='PASS' for r in rows)}", flush=True)

    def refuse_if(condition: bool, code: str):
        if condition: raise ValueError(code)
        return True

    case("CONTROL-RUNTIME-MANIFEST", lambda: refuse_if(
        manifest["root"] != qualification["runtime_manifest_root"], "ROOT_MISMATCH"))
    case("CONTROL-RUNTIME-ARCHIVE", lambda: refuse_if(
        sha(args.runtime_archive.read_bytes()) != qualification["runtime_sha256"], "ARCHIVE_MISMATCH"))
    case("CONTROL-POLICY", lambda: validate_host_adapter_policy(policy))
    case("CONTROL-ATTESTATION", lambda: validate_host_mediation_attestation(attestation,
        policy=policy, expected_session_root=session_root, expected_subject_root=project_root, now_ns=150))
    case("CONTROL-CONTEXT", lambda: validate_pippi_context(context))
    case("CONTROL-EXTERNAL-ANCHOR", lambda: refuse_if(
        effective_integration_mode(context, expected_host_policy_root=policy["host_policy_root"]) != "ENFORCED_HOST",
        "ANCHOR_NOT_EFFECTIVE"))
    case("CONTROL-REGISTRY", lambda: validate_integration_availability_registry(registry))
    case("CONTROL-BOUND-GATEWAY", lambda: validate_integration_availability_registry(bound))
    case("CONTROL-PROPOSAL", lambda: validate_host_launch_proposal(proposal))
    case("CONTROL-COMPLETE-GATEWAY-PROOF", lambda: validate_host_launch_result(result,
        proposal=proposal, policy=policy, attestation=attestation, now_ns=150))
    case("CONTROL-ACTIVE-SURFACES", lambda: refuse_if(not {
        "BUILD_PIPPI_HOST_ADAPTER_POLICY", "BUILD_ATTESTED_PIPPI_CONTEXT",
        "BUILD_PIPPI_HOST_LAUNCH_PROPOSAL", "VALIDATE_PIPPI_HOST_LAUNCH_RESULT",
        "BUILD_PIPPI_INTEGRATION_REGISTRY", "BIND_PIPPI_EXTERNAL_INTEGRATION",
    } <= {x["name"] for x in capability_registry()["surfaces"]}, "SURFACE_MISSING"))
    case("LEGACY-ALL-CHANNELS-STAYS-SIDECAR", lambda: refuse_if(
        effective_integration_mode(build_pippi_context(session_root=session_root,
            subject_root=project_root, policy_roots=[], capability_registry_root=root({"r": 1}),
            profile_root=root({"p": 1}), jurisdiction_root=root({"j": 1}),
            retained_context_roots=[], mediated_channels=sorted(CHANNELS))) != "SIDECAR_PARTIAL",
        "LEGACY_MODE_LAUNDERED"))
    case("ATTESTED-WITHOUT-EXTERNAL-ANCHOR-STAYS-SIDECAR", lambda: refuse_if(
        effective_integration_mode(context) != "SIDECAR_PARTIAL", "SELF_ANCHOR_ACCEPTED"))
    case("WRONG-EXTERNAL-POLICY-STAYS-SIDECAR", lambda: refuse_if(
        effective_integration_mode(context, expected_host_policy_root="0" * 64) != "SIDECAR_PARTIAL",
        "WRONG_ANCHOR_ACCEPTED"))
    case("EXPIRED-ATTESTATION", lambda: validate_host_mediation_attestation(attestation,
        policy=policy, expected_session_root=session_root, expected_subject_root=project_root, now_ns=250),
        "PIPPI_HOST_ATTESTATION_BINDING_INVALID")
    case("WRONG-SUBJECT", lambda: validate_host_mediation_attestation(attestation,
        policy=policy, expected_session_root=session_root, expected_subject_root=root({"other": 1}), now_ns=150),
        "PIPPI_HOST_ATTESTATION_BINDING_INVALID")
    bad = deepcopy(attestation); bad["mediated_channels"] = bad["mediated_channels"][:-1]
    case("MISSING-MEDIATED-CHANNEL", lambda: validate_host_mediation_attestation(bad,
        policy=policy, expected_session_root=session_root, expected_subject_root=project_root, now_ns=150),
        "PIPPI_HOST_CHANNELS_INCOMPLETE")
    bad = deepcopy(registry); bad["entries"] = bad["entries"][:-1]
    case("INTEGRATION-DENOMINATOR-SHRINK", lambda: validate_integration_availability_registry(bad),
        "PIPPI_INTEGRATION_DENOMINATOR_INVALID")
    bad = deepcopy(registry); bad["entries"][0]["status"] = "BOUND_EXTERNAL"
    case("BOUND-INTEGRATION-WITHOUT-ROOT", lambda: validate_integration_availability_registry(bad),
        "PIPPI_INTEGRATION_BINDING_REQUIRED")
    bad = deepcopy(registry); bad["entries"][0]["binding_root"] = root({"smuggled": 1})
    case("UNBOUND-INTEGRATION-WITH-ROOT", lambda: validate_integration_availability_registry(bad),
        "PIPPI_INTEGRATION_UNBOUND_HAS_BINDING")
    bad = deepcopy(proposal); bad["requested_effect_classes"] = ["NETWORK"]
    body = {k: v for k, v in bad.items() if k != "proposal_root"}; bad["proposal_root"] = root(body)
    case("PROPOSAL-EFFECT-LAUNDERING", lambda: validate_host_launch_proposal(bad),
        "PIPPI_LAUNCH_PROPOSAL_INVALID")
    bad = deepcopy(result); bad["result_projection"] = {"status": "LAUNCHED", "kind": "VERIFICATION"}
    body = {k: v for k, v in bad.items() if k != "launch_result_root"}; bad["launch_result_root"] = root(body)
    case("RESULT-PROJECTION-LAUNDERING", lambda: validate_host_launch_result(bad,
        proposal=proposal, policy=policy, attestation=attestation, now_ns=150),
        "PIPPI_LAUNCH_RESULT_ROOT_INVALID")
    bad = deepcopy(result); bad["events"] = bad["events"][:-1]
    body = {k: v for k, v in bad.items() if k != "launch_result_root"}; bad["launch_result_root"] = root(body)
    case("RESULT-MISSING-TERMINAL", lambda: validate_host_launch_result(bad,
        proposal=proposal, policy=policy, attestation=attestation, now_ns=150), "OPERATION")
    bad = deepcopy(result); bad["proof_bundle"]["status"] = "REFUSED"
    body = {k: v for k, v in bad.items() if k != "launch_result_root"}; bad["launch_result_root"] = root(body)
    case("RESULT-PROOF-STATUS-LAUNDERING", lambda: validate_host_launch_result(bad,
        proposal=proposal, policy=policy, attestation=attestation, now_ns=150), "PROOF")
    dashboard_source = (runtime / "src/ucm/pippi_dashboard.py").read_text(encoding="utf-8")
    case("DASHBOARD-NO-DIRECT-PROCESS", lambda: refuse_if(
        "subprocess" in dashboard_source or "os.startfile" in dashboard_source,
        "DIRECT_HOST_EFFECT_PRESENT"))
    failed = sum(row["status"] != "PASS" for row in rows)
    body = {"schema": "mosaic.ucm.pippi-r006-operator-tier1-result.v0.1",
            "status": "PASS" if failed == 0 else "HOLD_FOR_REPAIR",
            "cases": rows, "case_count": len(rows), "failed": failed,
            "runtime_sha256": sha(args.runtime_archive.read_bytes()),
            "runtime_manifest_root": manifest["root"],
            "qualification_root": qualification["root"], **BOUNDARY}
    result_record = {**body, "court_root": sha(canonical(body))}
    report = ("# P/PPI r006 operator Tier 1\n\n"
              f"Status: **{result_record['status']}**  \n"
              f"Cases: {len(rows)}; failed: {failed}.  \n"
              "Builder-authored, operator-reproduced evidence; not an independent verdict.\n").encode()
    evidence = zip_bytes({"TIER1-RESULT.json": canonical(result_record) + b"\n",
                          "REPORT.md": report,
                          "RUN-TIER1.py": Path(__file__).read_bytes()})
    evidence_path = out / f"UCM-PIPPI-r006-TIER1-EVIDENCE-{result_record['court_root'][:16]}.zip"
    evidence_path.write_bytes(evidence)
    print(json.dumps({"status": result_record["status"], "cases": len(rows),
        "failed": failed, "court_root": result_record["court_root"],
        "evidence": str(evidence_path), "evidence_sha256": sha(evidence)}, sort_keys=True))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

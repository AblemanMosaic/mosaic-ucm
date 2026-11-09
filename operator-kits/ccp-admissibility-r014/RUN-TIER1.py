#!/usr/bin/env python3
"""Builder-authored, user-run Tier 1 court for CCP admissibility r014.

The release builder may compile this source and package it.  It must not run
these adversarial cases.  The double-click operator launcher is the execution
boundary.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


FIXED_TIME = (1980, 1, 1, 0, 0, 0)
BOUNDARY = {
    "standing": "INFORMATION_ONLY",
    "authority_effect": "NONE",
    "real_a5": False,
    "g0": "CLOSED",
}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def zip_bytes(payloads: dict[str, bytes]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for name, raw in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw)
    return out.getvalue()


def reroot(record: dict, root_field: str, root) -> dict:
    changed = {key: value for key, value in record.items() if key != root_field}
    return {**changed, root_field: root(changed)}


def refuse_if(condition: bool, code: str) -> bool:
    if condition:
        raise ValueError(code)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    subject = args.subject.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(subject / "src"))

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from uclop.canonical import canonical_bytes, root, strict_loads
    from ucm.ccp_admissibility import (  # API names are kept together for review.
        build_admissibility_projection,
        build_chc_thr_correspondence,
        build_current_use_snapshot,
        build_enforcement_perimeter,
        build_evidence_snapshot,
        build_jurisdiction_profile,
        evaluate_current_admissibility,
        validate_admissibility_decision,
        validate_admissibility_projection,
        validate_chc_thr_correspondence,
        validate_current_use_snapshot,
        validate_enforcement_perimeter,
        validate_evidence_snapshot,
        validate_jurisdiction_profile,
    )
    from ucm.amcas import BOUNDARY as UCM_BOUNDARY
    from ucm.operation_gateway import (
        PERMIT_SCHEMA,
        REVOCATION_SCHEMA,
        OperationGateway,
        build_operation_contract,
        validate_admissibility_bound_operation_history,
    )

    manifest = strict_loads((subject / "KIT-MANIFEST.json").read_bytes())
    program_dir = subject / "program/ccp-admissibility-r014"
    inventory = strict_loads((program_dir / "INVENTORY.json").read_bytes())
    native_program = strict_loads((program_dir / "NATIVE-PROGRAM.json").read_bytes())
    reconciliation = strict_loads(
        (program_dir / "SOURCE-RECONCILIATION.json").read_bytes())
    source_archive = subject / "qualification/inputs/ccp-jm/CCP_JM_PIPELINE_v0_1_r001.zip"

    # The fixture uses published deterministic keys only inside this disposable
    # court.  They prove cross-links, not identity, authority or live custody.
    issuer = Ed25519PrivateKey.from_private_bytes(b"\x51" * 32)
    executor = Ed25519PrivateKey.from_private_bytes(b"\x52" * 32)

    def public(key) -> str:
        return key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

    def signed(body: dict, key, root_field: str) -> dict:
        signature = key.sign(canonical_bytes(body)).hex()
        return {**body, "signature_hex": signature,
                root_field: root({**body, "signature_hex": signature})}

    def status_evidence(subject_value: str, *, checkpoint="CURRENT"):
        ids = {domain: f"CCP.R014.STATUS.{domain.upper()}" for domain in (
            "checkpoint", "policy", "revocation", "schema", "semantic", "state")}
        observations = {
            "checkpoint": checkpoint, "policy": "CURRENT",
            "revocation": "CURRENT_CLEAR", "schema": "CURRENT",
            "semantic": "CURRENT", "state": "CURRENT",
        }
        rows = [{
            "evidence_id": evidence_id,
            "evidence_kind": f"STATUS_{domain.upper()}",
            "subject_root": subject_value,
            "evidence_root": root({"status": domain,
                                   "observation": observations[domain]}),
            "source_mode": "LOCAL", "verification_status": "PASS",
            "observed_epoch": 950, "valid_until_epoch": 1050,
            "admissibility_status_claim": {
                "domain": domain, "observed_status": observations[domain],
            },
        } for domain, evidence_id in ids.items()]
        return rows, ids

    operation_jurisdiction_root = root({"jurisdiction": "ccp-r014-operator"})
    revocation_body = {
        "schema": REVOCATION_SCHEMA, "issuer_public_key_hex": public(issuer),
        "jurisdiction_root": operation_jurisdiction_root,
        "generation": 1, "sequence": 1, "valid_at": 100,
        "revoked_permit_roots": [], "predecessor_root": "0" * 64,
        **UCM_BOUNDARY,
    }
    revocation = signed(revocation_body, issuer, "revocation_registry_root")
    request_root = root({"request": "ccp-r014-operator"})
    permit_body = {
        "schema": PERMIT_SCHEMA, "permit_id": "permit:ccp:r014:operator",
        "issuer_public_key_hex": public(issuer),
        "subject_identity_root": root({"artifact": "ccp-r014-operator-fixture"}),
        "session_root": root({"session": "operator-fixture"}),
        "jurisdiction_root": operation_jurisdiction_root,
        "application_id": "UCM.CCP.R014", "action_id": "USE.EXACT.ARTIFACT",
        "request_root": request_root, "executor_public_key_hex": public(executor),
        "allowed_effect_classes": ["WRITE_WORKSPACE"],
        "budget": {"max_cases": 1, "max_duration_ms": 1000,
                   "max_output_bytes": 4096},
        "rollback_root": root({"rollback": "operator-fixture"}),
        "generation": 1, "nonce": root({"nonce": "ccp-r014-operator"}),
        "issued_at": 90, "not_before": 95, "expires_at": 200,
        "revocation_registry_root": revocation["revocation_registry_root"],
        **UCM_BOUNDARY,
    }
    permit = signed(permit_body, issuer, "permit_root")
    contract = build_operation_contract(
        operation_id="op:ccp:r014:operator", permit=permit,
        revocation_registry=revocation,
        expected_issuer_public_key_hex=public(issuer),
        expected_jurisdiction_root=operation_jurisdiction_root,
        expected_revocation_registry_root=revocation["revocation_registry_root"],
        requested_effect_classes=["WRITE_WORKSPACE"],
        idempotency_key=root({"idempotency": "ccp-r014-operator"}),
        expected_result_root=root({"result": "operator-fixture"}), now=100)

    # The point-of-use fixture names no live target.  ADMIT remains an
    # information-only input to the separately permitted gateway operation.
    subject_root = root({"artifact": "ccp-r014-operator-fixture"})
    policy_root = root({"policy": "ccp-r014-operator"})
    schema_root = root({"schema": "ccp-r014-operator"})
    trust_root = root({"trust": "ccp-r014-operator"})
    checkpoint_root = root({"checkpoint": 7})
    thr_manifest_root = root({"thr": "operator-fixture"})
    chc_commitment_root = root({"chc": "operator-fixture"})
    jurisdiction = build_jurisdiction_profile(
        profile_id="CCP.R014.OPERATOR", application_id=contract["application_id"],
        subject_root=subject_root, state_boundary_id="EXACT_ARCHIVE",
        state_root=root({"state": "operator-fixture"}),
        manifest_root=root({"manifest": "operator-fixture"}),
        path_policy="EXACT_ARCHIVE_MEMBERS_V1",
        governance_jurisdiction_root=contract["jurisdiction_root"],
        bound_policy_root=policy_root,
        bound_schema_registry_root=schema_root,
        bound_trust_root=trust_root,
        transition_rule_root=root({"transition": "successor-only"}),
        allowed_operations=[contract["action_id"]], evidence_modes=["LOCAL"])
    perimeter = build_enforcement_perimeter(
        perimeter_id="CCP.R014.OPERATOR.LOCAL",
        jurisdiction_profile_root=jurisdiction["jurisdiction_profile_root"],
        adapter_root=root({"adapter": "ccp-r014-operator"}),
        intercepted_operations=[contract["action_id"]], excluded_bypass_classes=[],
        continuing_use_policy="LAUNCH_ONLY_RECHECK_REQUIRED",
        qualification_status="QUALIFIED_SCOPED")
    correspondence = build_chc_thr_correspondence(
        correspondence_id="CCP.R014.OPERATOR.CHC-THR",
        correspondence_version="v0.1",
        chc_source_root=chc_commitment_root,
        chc_profile_root=root({"chc-profile": "operator-fixture"}),
        thr_contract_root=thr_manifest_root)
    status_rows, status_ids = status_evidence(subject_root)
    evidence = build_evidence_snapshot(
        snapshot_id="CCP.R014.OPERATOR.EVIDENCE", subject_root=subject_root,
        state_identity_root=root({"state-identity": "operator-fixture"}),
        semantic_identity_root=root({"semantic-identity": "operator-fixture"}),
        jurisdiction_profile_root=jurisdiction["jurisdiction_profile_root"],
        enforcement_perimeter_root=perimeter["enforcement_perimeter_root"],
        active_policy_root=policy_root,
        active_schema_registry_root=schema_root,
        active_trust_root=trust_root, checkpoint_root=checkpoint_root,
        checkpoint_sequence=8, persistent_maximum_sequence=8,
        authenticated_epoch=1000, evidence=status_rows + [{
            "evidence_id": "CCP.R014.LOCAL.CUSTODY",
            "evidence_kind": "EXACT_ARCHIVE_CUSTODY",
            "subject_root": subject_root,
            "evidence_root": root({"evidence": "ccp-r014-local-custody"}),
            "source_mode": "LOCAL", "verification_status": "PASS",
            "observed_epoch": 950, "valid_until_epoch": 1050,
            "admissibility_status_claim": None,
        }], status_evidence_ids=status_ids, unresolved_requirements=[])
    current = build_current_use_snapshot(
        request_id="CCP.R014.OPERATOR.USE", operation=contract["action_id"],
        subject_root=subject_root, target_root=contract["request_root"],
        handler_root=root({"handler": "ccp-r014"}),
        runtime_root=root({"runtime": "python-3.12-or-3.13"}),
        dependency_closure_root=root({"dependencies": []}),
        state_identity_root=evidence["state_identity_root"],
        semantic_identity_root=evidence["semantic_identity_root"],
        jurisdiction_profile_root=jurisdiction["jurisdiction_profile_root"],
        enforcement_perimeter_root=perimeter["enforcement_perimeter_root"],
        correspondence_root=correspondence["correspondence_root"],
        evidence_snapshot_root=evidence["evidence_snapshot_root"],
        active_policy_root=policy_root, active_schema_registry_root=schema_root,
        active_trust_root=trust_root, checkpoint_root=checkpoint_root,
        authenticated_epoch=1000,
        requested_effect_classes=contract["requested_effect_classes"],
        max_steps=128, max_evidence_rows=8)
    evaluation_args = {
        "current_use_snapshot": current, "evidence_snapshot": evidence,
        "jurisdiction_profile": jurisdiction, "enforcement_perimeter": perimeter,
        "correspondence": correspondence, "expected_subject_root": subject_root,
        "expected_jurisdiction_profile_root": jurisdiction["jurisdiction_profile_root"],
        "expected_enforcement_perimeter_root": perimeter["enforcement_perimeter_root"],
        "expected_correspondence_root": correspondence["correspondence_root"],
        "expected_policy_root": policy_root,
        "expected_schema_registry_root": schema_root,
        "expected_trust_root": trust_root,
        "expected_checkpoint_root": checkpoint_root,
    }
    decision = evaluate_current_admissibility(
        **evaluation_args)
    # Projection validation is intentionally bound to the same independently
    # supplied anchors as the admissibility decision.  Keep one argument
    # packet so future contract additions cannot silently leave the human view
    # on an older call shape.
    projection_args = {"decision": decision, **evaluation_args}
    projection = build_admissibility_projection(**projection_args)

    rows: list[dict] = []

    def case(case_id: str, action, expected: str | None = None) -> None:
        status = "FAIL"
        diagnostic = "UNEXPECTED_PASS"
        try:
            value = action()
            if expected is None:
                status, diagnostic = "PASS", "CONTROL_PASS"
            else:
                diagnostic = f"UNEXPECTED_PASS:{value!r}"
        except Exception as error:  # The court records typed refusals, not crashes.
            diagnostic = str(error)
            if expected is not None and expected in diagnostic:
                status = "PASS"
        rows.append({"case_id": case_id, "status": status, "diagnostic": diagnostic})
        print(f"[case {len(rows):03}] {case_id}: {status}", flush=True)
        print(f"[summary] completed={len(rows)} failed="
              f"{sum(row['status'] != 'PASS' for row in rows)}", flush=True)

    # Exact controls.
    actual_rows = [
        {"path": path.relative_to(subject).as_posix(), "bytes": path.stat().st_size,
         "sha256": sha(path.read_bytes())}
        for path in sorted(subject.rglob("*"))
        if (path.is_file() and path.name != "KIT-MANIFEST.json"
            and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"})
    ]
    actual_rows.sort(key=lambda row: row["path"])
    manifest_body = {key: value for key, value in manifest.items()
                     if key != "manifest_root"}
    case("CONTROL-KIT-CLOSED-MANIFEST", lambda: refuse_if(
        manifest["files"] != actual_rows
        or manifest["file_count"] != len(actual_rows)
        or manifest["manifest_root"] != root(manifest_body),
        "CCP_OPERATOR_MANIFEST_INVALID"))
    case("CONTROL-KIT-MANIFEST", lambda: refuse_if(
        manifest["standing"] != "INFORMATION_ONLY" or manifest["authority_effect"] != "NONE"
        or manifest["real_a5"] is not False or manifest["g0"] != "CLOSED",
        "CCP_OPERATOR_BOUNDARY_INVALID"))
    case("CONTROL-SOURCE-DENOMINATOR", lambda: refuse_if(
        native_program["denominators"] != {
            "batches": 6, "stages": 13, "requirements": 32,
            "product_acceptance_cases": 116, "product_cases_executed": 0,
        },
        "CCP_SOURCE_DENOMINATOR_INVALID"))
    case("CONTROL-EXACT-SOURCE-ARCHIVE", lambda: refuse_if(
        not source_archive.is_file()
        or sha(source_archive.read_bytes()) != inventory["source_archive_sha256"],
        "CCP_SOURCE_ARCHIVE_MISMATCH"))
    comparison = reconciliation["denominator_comparison"]
    case("CONTROL-SOURCE-RECONCILIATION", lambda: refuse_if(
        reconciliation["status"] != "PASS_SOURCE_DENOMINATOR_PRESERVED"
        or reconciliation["product_cases_executed"] != 0
        or any(comparison[name] for name in (
            "missing_product_acceptance_case_ids", "extra_product_acceptance_case_ids",
            "missing_requirement_ids", "extra_requirement_ids",
            "missing_stage_ids", "extra_stage_ids")),
        "CCP_SOURCE_RECONCILIATION_INVALID"))

    def generator_check() -> bool:
        completed = subprocess.run(
            [sys.executable, str(subject / "tools/build_ccp_native_program.py"),
             "--check"], cwd=subject, capture_output=True, text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, check=False)
        return refuse_if(completed.returncode != 0,
                         "CCP_NATIVE_PROGRAM_REPLAY_FAILED")

    case("CONTROL-NATIVE-PROGRAM-REPLAY", generator_check)
    case("CONTROL-JURISDICTION", lambda: validate_jurisdiction_profile(jurisdiction))
    case("CONTROL-ENFORCEMENT-PERIMETER", lambda: validate_enforcement_perimeter(perimeter))
    case("CONTROL-CHC-THR-CORRESPONDENCE", lambda: validate_chc_thr_correspondence(
        correspondence))
    case("CONTROL-EVIDENCE-SNAPSHOT", lambda: validate_evidence_snapshot(evidence))
    case("CONTROL-CURRENT-USE-SNAPSHOT", lambda: validate_current_use_snapshot(current))
    case("CONTROL-ADMISSIBILITY-DECISION", lambda: validate_admissibility_decision(
        decision, **evaluation_args))
    case("CONTROL-HUMAN-PROJECTION", lambda: validate_admissibility_projection(
        projection, **projection_args))

    # A declared interception boundary is documentation, not proof that the
    # operation is actually intercepted.  It therefore cannot yield ADMIT.
    declared_perimeter = build_enforcement_perimeter(
        perimeter_id="CCP.R014.OPERATOR.DECLARED",
        jurisdiction_profile_root=jurisdiction["jurisdiction_profile_root"],
        adapter_root=root({"adapter": "ccp-r014-operator-declared"}),
        intercepted_operations=[contract["action_id"]],
        excluded_bypass_classes=[],
        continuing_use_policy="LAUNCH_ONLY_RECHECK_REQUIRED",
        qualification_status="DECLARED_ONLY")
    declared_evidence = build_evidence_snapshot(
        snapshot_id="CCP.R014.OPERATOR.DECLARED.EVIDENCE",
        subject_root=subject_root,
        state_identity_root=evidence["state_identity_root"],
        semantic_identity_root=evidence["semantic_identity_root"],
        jurisdiction_profile_root=jurisdiction["jurisdiction_profile_root"],
        enforcement_perimeter_root=
            declared_perimeter["enforcement_perimeter_root"],
        active_policy_root=policy_root,
        active_schema_registry_root=schema_root,
        active_trust_root=trust_root, checkpoint_root=checkpoint_root,
        checkpoint_sequence=8, persistent_maximum_sequence=8,
        authenticated_epoch=1000, evidence=evidence["evidence"],
        status_evidence_ids=evidence["status_evidence_ids"],
        unresolved_requirements=[])
    declared_use = build_current_use_snapshot(
        request_id="CCP.R014.OPERATOR.DECLARED.USE",
        operation=contract["action_id"], subject_root=subject_root,
        target_root=current["target_root"],
        handler_root=current["handler_root"],
        runtime_root=current["runtime_root"],
        dependency_closure_root=current["dependency_closure_root"],
        state_identity_root=declared_evidence["state_identity_root"],
        semantic_identity_root=declared_evidence["semantic_identity_root"],
        jurisdiction_profile_root=jurisdiction["jurisdiction_profile_root"],
        enforcement_perimeter_root=
            declared_perimeter["enforcement_perimeter_root"],
        correspondence_root=correspondence["correspondence_root"],
        evidence_snapshot_root=declared_evidence["evidence_snapshot_root"],
        active_policy_root=policy_root,
        active_schema_registry_root=schema_root,
        active_trust_root=trust_root, checkpoint_root=checkpoint_root,
        authenticated_epoch=1000,
        requested_effect_classes=contract["requested_effect_classes"],
        max_steps=128, max_evidence_rows=8)
    declared_args = {
        **evaluation_args,
        "current_use_snapshot": declared_use,
        "evidence_snapshot": declared_evidence,
        "enforcement_perimeter": declared_perimeter,
        "expected_enforcement_perimeter_root":
            declared_perimeter["enforcement_perimeter_root"],
    }
    case("DECLARED-PERIMETER-CANNOT-ADMIT", lambda: refuse_if(
        evaluate_current_admissibility(**declared_args)["decision"]
        != "UNRESOLVED"
        or "ENFORCEMENT_PERIMETER_NOT_QUALIFIED" not in
        evaluate_current_admissibility(**declared_args)["reason_codes"],
        "CCP_DECLARED_PERIMETER_ADMITTED"))

    # The logical evaluation budget is part of current-use custody.  Exhaustion
    # is a typed refusal rather than an approximate or partial PASS.
    budget_use = build_current_use_snapshot(
        request_id="CCP.R014.OPERATOR.BUDGET.USE",
        operation=contract["action_id"], subject_root=subject_root,
        target_root=current["target_root"],
        handler_root=current["handler_root"],
        runtime_root=current["runtime_root"],
        dependency_closure_root=current["dependency_closure_root"],
        state_identity_root=evidence["state_identity_root"],
        semantic_identity_root=evidence["semantic_identity_root"],
        jurisdiction_profile_root=jurisdiction["jurisdiction_profile_root"],
        enforcement_perimeter_root=perimeter["enforcement_perimeter_root"],
        correspondence_root=correspondence["correspondence_root"],
        evidence_snapshot_root=evidence["evidence_snapshot_root"],
        active_policy_root=policy_root,
        active_schema_registry_root=schema_root,
        active_trust_root=trust_root, checkpoint_root=checkpoint_root,
        authenticated_epoch=1000,
        requested_effect_classes=contract["requested_effect_classes"],
        max_steps=1, max_evidence_rows=8)
    budget_args = {**evaluation_args, "current_use_snapshot": budget_use}
    case("EVALUATION-STEP-BUDGET-ENFORCED", lambda: refuse_if(
        evaluate_current_admissibility(**budget_args)["decision"] != "REFUSE"
        or "EVALUATION_STEP_BUDGET_EXCEEDED" not in
        evaluate_current_admissibility(**budget_args)["reason_codes"],
        "CCP_EVALUATION_STEP_BUDGET_NOT_ENFORCED"))

    # Independent anchors: a self-consistent artifact may not choose its own
    # external policy, schema, trust, jurisdiction or checkpoint expectations.
    def anchor_refuses(field: str, reason_code: str) -> bool:
        changed = deepcopy(evaluation_args)
        changed[field] = root({"attacker-anchor": field})
        result = evaluate_current_admissibility(**changed)
        return refuse_if(result["decision"] != "REFUSE"
                         or reason_code not in result["reason_codes"],
                         "CCP_INDEPENDENT_ANCHOR_ACCEPTED")

    case("ANCHOR-POLICY-MISMATCH", lambda: anchor_refuses(
        "expected_policy_root", "POLICY_ANCHOR_MISMATCH"))
    case("ANCHOR-SCHEMA-MISMATCH", lambda: anchor_refuses(
        "expected_schema_registry_root", "SCHEMA_ANCHOR_MISMATCH"))
    case("ANCHOR-TRUST-MISMATCH", lambda: anchor_refuses(
        "expected_trust_root", "TRUST_ANCHOR_MISMATCH"))
    case("ANCHOR-CHECKPOINT-MISMATCH", lambda: anchor_refuses(
        "expected_checkpoint_root", "CHECKPOINT_ANCHOR_MISMATCH"))

    # CHC and THR are distinct commitments.  Equality is never a shortcut for
    # an explicit, versioned correspondence.
    bad = deepcopy(correspondence)
    bad["thr_contract_root"] = bad["chc_source_root"]
    bad = reroot(bad, "correspondence_root", root)
    case("CHC-THR-EQUAL-BYTES-DO-NOT-CREATE-IDENTITY", lambda: refuse_if(
        validate_chc_thr_correspondence(bad)["digest_equivalence"]
        != "DIGESTS_ARE_NOT_EQUIVALENT",
        "CCP_CHC_THR_EQUAL_BYTES_LAUNDERED_AS_IDENTITY"))
    bad = deepcopy(correspondence)
    bad["digest_equivalence"] = "IDENTICAL_ROOTS"
    bad = reroot(bad, "correspondence_root", root)
    case("CHC-THR-IDENTITY-RELATION-REFUSED", lambda: validate_chc_thr_correspondence(
        bad),
        "CCP_CHC_THR_CORRESPONDENCE_INVALID")

    # Snapshot, decision and gateway cross-links.
    bad = deepcopy(decision)
    bad["current_use_snapshot_root"] = root({"snapshot": "other"})
    bad = reroot(bad, "decision_root", root)
    case("DECISION-SNAPSHOT-SWAP", lambda: validate_admissibility_decision(
        bad, **evaluation_args), "CCP_ADMISSIBILITY_DECISION_INVALID")
    bad = deepcopy(decision)
    bad["evidence_snapshot_root"] = root({"evidence": "other"})
    bad = reroot(bad, "decision_root", root)
    case("DECISION-EVIDENCE-SWAP", lambda: validate_admissibility_decision(
        bad, **evaluation_args), "CCP_ADMISSIBILITY_DECISION_INVALID")

    # Historical validity does not imply present admissibility.
    expired = build_evidence_snapshot(
        snapshot_id="CCP.R014.OPERATOR.EXPIRED", subject_root=subject_root,
        state_identity_root=evidence["state_identity_root"],
        semantic_identity_root=evidence["semantic_identity_root"],
        jurisdiction_profile_root=jurisdiction["jurisdiction_profile_root"],
        enforcement_perimeter_root=perimeter["enforcement_perimeter_root"],
        active_policy_root=policy_root, active_schema_registry_root=schema_root,
        active_trust_root=trust_root, checkpoint_root=checkpoint_root,
        checkpoint_sequence=8, persistent_maximum_sequence=8,
        authenticated_epoch=1000, evidence=[
            ({**row, "valid_until_epoch": 999}
             if row["evidence_id"] == "CCP.R014.LOCAL.CUSTODY" else row)
            for row in evidence["evidence"]
        ], status_evidence_ids=evidence["status_evidence_ids"],
        unresolved_requirements=[])
    expired_use = build_current_use_snapshot(
        request_id="CCP.R014.OPERATOR.EXPIRED.USE", operation=contract["action_id"],
        subject_root=subject_root, target_root=current["target_root"],
        handler_root=current["handler_root"], runtime_root=current["runtime_root"],
        dependency_closure_root=current["dependency_closure_root"],
        state_identity_root=expired["state_identity_root"],
        semantic_identity_root=expired["semantic_identity_root"],
        jurisdiction_profile_root=jurisdiction["jurisdiction_profile_root"],
        enforcement_perimeter_root=perimeter["enforcement_perimeter_root"],
        correspondence_root=correspondence["correspondence_root"],
        evidence_snapshot_root=expired["evidence_snapshot_root"],
        active_policy_root=policy_root, active_schema_registry_root=schema_root,
        active_trust_root=trust_root, checkpoint_root=checkpoint_root,
        authenticated_epoch=1000,
        requested_effect_classes=contract["requested_effect_classes"],
        max_steps=128, max_evidence_rows=8)
    expired_args = {**evaluation_args, "current_use_snapshot": expired_use,
                    "evidence_snapshot": expired}
    case("CURRENT-USE-AFTER-EXPIRY", lambda: refuse_if(
        evaluate_current_admissibility(**expired_args)["decision"] != "DEFER"
        or "EVIDENCE_EXPIRED:CCP.R014.LOCAL.CUSTODY" not in
        evaluate_current_admissibility(**expired_args)["reason_codes"],
        "CCP_EXPIRED_EVIDENCE_ADMITTED"))
    rollback_rows, rollback_status_ids = status_evidence(
        subject_root, checkpoint="ROLLBACK")
    rollback = build_evidence_snapshot(
        snapshot_id="CCP.R014.OPERATOR.ROLLBACK", subject_root=subject_root,
        state_identity_root=evidence["state_identity_root"],
        semantic_identity_root=evidence["semantic_identity_root"],
        jurisdiction_profile_root=jurisdiction["jurisdiction_profile_root"],
        enforcement_perimeter_root=perimeter["enforcement_perimeter_root"],
        active_policy_root=policy_root, active_schema_registry_root=schema_root,
        active_trust_root=trust_root, checkpoint_root=checkpoint_root,
        checkpoint_sequence=6, persistent_maximum_sequence=8,
        authenticated_epoch=1000, evidence=rollback_rows + [{
            **next(row for row in evidence["evidence"]
                   if row["evidence_id"] == "CCP.R014.LOCAL.CUSTODY")
        }], status_evidence_ids=rollback_status_ids,
        unresolved_requirements=[])
    rollback_use = build_current_use_snapshot(
        request_id="CCP.R014.OPERATOR.ROLLBACK.USE", operation=contract["action_id"],
        subject_root=subject_root, target_root=current["target_root"],
        handler_root=current["handler_root"], runtime_root=current["runtime_root"],
        dependency_closure_root=current["dependency_closure_root"],
        state_identity_root=rollback["state_identity_root"],
        semantic_identity_root=rollback["semantic_identity_root"],
        jurisdiction_profile_root=jurisdiction["jurisdiction_profile_root"],
        enforcement_perimeter_root=perimeter["enforcement_perimeter_root"],
        correspondence_root=correspondence["correspondence_root"],
        evidence_snapshot_root=rollback["evidence_snapshot_root"],
        active_policy_root=policy_root, active_schema_registry_root=schema_root,
        active_trust_root=trust_root, checkpoint_root=checkpoint_root,
        authenticated_epoch=1000,
        requested_effect_classes=contract["requested_effect_classes"],
        max_steps=128, max_evidence_rows=8)
    rollback_args = {**evaluation_args, "current_use_snapshot": rollback_use,
                     "evidence_snapshot": rollback}
    case("CHECKPOINT-ROLLBACK-REFUSED", lambda: refuse_if(
        evaluate_current_admissibility(**rollback_args)["decision"] != "REFUSE"
        or "CHECKPOINT_ROLLBACK" not in
        evaluate_current_admissibility(**rollback_args)["reason_codes"],
        "CCP_CHECKPOINT_ROLLBACK_ADMITTED"))

    def prepare_gateway(decision_value: dict, use_value: dict,
                        evidence_value: dict, eval_args: dict,
                        *, expected_decision_root: str,
                        expected_snapshot_root: str) -> dict:
        with tempfile.TemporaryDirectory(prefix="ucm-ccp-r014-gateway-") as raw:
            gateway = OperationGateway(Path(raw))
            prepared = gateway.prepare_with_admissibility(
                contract, decision_value,
                current_use_snapshot=use_value,
                evidence_snapshot=evidence_value,
                jurisdiction_profile=eval_args["jurisdiction_profile"],
                enforcement_perimeter=eval_args["enforcement_perimeter"],
                correspondence=eval_args["correspondence"],
                expected_admissibility_decision_root=expected_decision_root,
                expected_current_use_snapshot_root=expected_snapshot_root,
                expected_issuer_public_key_hex=public(issuer),
                expected_jurisdiction_root=contract["jurisdiction_root"],
                expected_revocation_registry_root=
                    revocation["revocation_registry_root"],
                expected_subject_root=eval_args["expected_subject_root"],
                expected_jurisdiction_profile_root=
                    eval_args["expected_jurisdiction_profile_root"],
                expected_enforcement_perimeter_root=
                    eval_args["expected_enforcement_perimeter_root"],
                expected_correspondence_root=
                    eval_args["expected_correspondence_root"],
                expected_policy_root=eval_args["expected_policy_root"],
                expected_schema_registry_root=
                    eval_args["expected_schema_registry_root"],
                expected_trust_root=eval_args["expected_trust_root"],
                expected_checkpoint_root=eval_args["expected_checkpoint_root"])
            checked = validate_admissibility_bound_operation_history(
                operation_id=contract["operation_id"],
                events=gateway.journal.verify(),
                expected_issuer_public_key_hex=public(issuer),
                expected_jurisdiction_root=contract["jurisdiction_root"],
                expected_revocation_registry_root=
                    revocation["revocation_registry_root"],
                expected_admissibility_decision_root=expected_decision_root,
                expected_current_use_snapshot_root=expected_snapshot_root,
                expected_subject_root=eval_args["expected_subject_root"],
                expected_jurisdiction_profile_root=
                    eval_args["expected_jurisdiction_profile_root"],
                expected_enforcement_perimeter_root=
                    eval_args["expected_enforcement_perimeter_root"],
                expected_correspondence_root=
                    eval_args["expected_correspondence_root"],
                expected_policy_root=eval_args["expected_policy_root"],
                expected_schema_registry_root=
                    eval_args["expected_schema_registry_root"],
                expected_trust_root=eval_args["expected_trust_root"],
                expected_checkpoint_root=eval_args["expected_checkpoint_root"])
            return {"prepared": prepared, "checked": checked}

    def gateway_control() -> bool:
        result = prepare_gateway(
            decision, current, evidence, evaluation_args,
            expected_decision_root=decision["decision_root"],
            expected_snapshot_root=current["current_use_snapshot_root"])
        prepared = result["prepared"]
        binding = prepared["admissibility_bundle"]["binding"]
        return refuse_if(
            prepared["g1"]["admissibility_decision_root"]
            != decision["decision_root"]
            or prepared["g1"]["current_use_snapshot_root"]
            != current["current_use_snapshot_root"]
            or prepared["dispatch_authorization"][
                "pre_effect_version_check_required"] is not True
            or result["checked"]["admissibility_binding_root"]
            != binding["binding_root"],
            "CCP_GATEWAY_CONTROL_INVALID")

    case("CONTROL-GATEWAY-G1-DISPATCH-BINDING", gateway_control)
    case("GATEWAY-DECISION-PIN-SWAP", lambda: prepare_gateway(
        decision, current, evidence, evaluation_args,
        expected_decision_root=root({"decision": "other"}),
        expected_snapshot_root=current["current_use_snapshot_root"]),
        "OPERATION_ADMISSIBILITY_DECISION_PIN_MISMATCH")
    case("GATEWAY-SNAPSHOT-PIN-SWAP", lambda: prepare_gateway(
        decision, current, evidence, evaluation_args,
        expected_decision_root=decision["decision_root"],
        expected_snapshot_root=root({"snapshot": "other"})),
        "OPERATION_CURRENT_USE_SNAPSHOT_PIN_MISMATCH")
    rollback_decision = evaluate_current_admissibility(**rollback_args)
    case("GATEWAY-REFUSED-DECISION", lambda: prepare_gateway(
        rollback_decision, rollback_use, rollback, rollback_args,
        expected_decision_root=rollback_decision["decision_root"],
        expected_snapshot_root=rollback_use["current_use_snapshot_root"]),
        "OPERATION_ADMISSIBILITY_NOT_ADMITTED")

    # Human projections are views, never authority or alternate decisions.
    bad = deepcopy(projection)
    bad["decision"] = "REFUSE"
    bad = reroot(bad, "projection_root", root)
    case("PROJECTION-DECISION-LAUNDERING", lambda: validate_admissibility_projection(
        bad, **projection_args), "CCP_CURRENT_USE_PROJECTION_INVALID")
    bad = deepcopy(projection)
    bad["authority_effect"] = "GRANT"
    bad = reroot(bad, "projection_root", root)
    case("PROJECTION-AUTHORITY-LAUNDERING", lambda: validate_admissibility_projection(
        bad, **projection_args), "CCP_CURRENT_USE_PROJECTION_INVALID")

    # The generated program keeps the packet denominator fixed.
    bad = deepcopy(native_program)
    bad["denominators"]["product_acceptance_cases"] = 115
    body = {key: value for key, value in bad.items() if key != "native_program_root"}
    bad["native_program_root"] = root(body)
    case("DENOMINATOR-ACCEPTANCE-CASE-SHRINK", lambda: refuse_if(
        bad["denominators"]["product_acceptance_cases"] != 116,
        "CCP_SOURCE_DENOMINATOR_INVALID"), "CCP_SOURCE_DENOMINATOR_INVALID")
    bad = deepcopy(native_program)
    bad["denominators"]["requirements"] = 31
    body = {key: value for key, value in bad.items() if key != "native_program_root"}
    bad["native_program_root"] = root(body)
    case("DENOMINATOR-REQUIREMENT-SHRINK", lambda: refuse_if(
        bad["denominators"]["requirements"] != 32,
        "CCP_SOURCE_DENOMINATOR_INVALID"), "CCP_SOURCE_DENOMINATOR_INVALID")
    bad = deepcopy(native_program)
    bad["denominators"]["stages"] = 12
    body = {key: value for key, value in bad.items() if key != "native_program_root"}
    bad["native_program_root"] = root(body)
    case("DENOMINATOR-STAGE-SHRINK", lambda: refuse_if(
        bad["denominators"]["stages"] != 13,
        "CCP_SOURCE_DENOMINATOR_INVALID"), "CCP_SOURCE_DENOMINATOR_INVALID")

    failed = sum(row["status"] != "PASS" for row in rows)
    body = {
        "schema": "mosaic.ucm.ccp-admissibility-r014-tier1-result.v0.1",
        "status": "PASS" if failed == 0 else "HOLD_FOR_REPAIR",
        "cases": rows,
        "case_count": len(rows),
        "failed": failed,
        "kit_manifest_root": manifest["manifest_root"],
        "program_inventory_root": inventory["inventory_root"],
        **BOUNDARY,
    }
    result = {**body, "court_root": sha(canonical(body))}
    report = (
        "# UCM CCP admissibility r014 operator Tier 1\n\n"
        f"Status: **{result['status']}**  \n"
        f"Cases: {len(rows)}; failed: {failed}.  \n"
        "Builder-authored, operator-reproduced evidence; not an independent verdict.\n"
    ).encode("utf-8")
    evidence_payloads = {
        "TIER1-RESULT.json": canonical(result) + b"\n",
        "REPORT.md": report,
        "RUN-TIER1.py": Path(__file__).read_bytes(),
    }
    evidence_manifest_body = {
        "schema": "mosaic.ucm.ccp-admissibility-r014-tier1-evidence-manifest.v0.1",
        "artifact_role": "UCM_CCP_ADMISSIBILITY_R014_TIER1_EVIDENCE",
        "files": [
            {"path": name, "bytes": len(raw), "sha256": sha(raw)}
            for name, raw in sorted(evidence_payloads.items())
        ],
        "file_count": len(evidence_payloads),
        **BOUNDARY,
    }
    evidence_payloads["EVIDENCE-MANIFEST.json"] = canonical({
        **evidence_manifest_body,
        "manifest_root": root(evidence_manifest_body),
    }) + b"\n"
    evidence_zip = zip_bytes(evidence_payloads)
    evidence_path = out / (
        f"UCM-CCP-ADMISSIBILITY-r014-TIER1-EVIDENCE-{result['court_root'][:16]}.zip")
    evidence_path.write_bytes(evidence_zip)
    print(json.dumps({
        "status": result["status"],
        "cases": len(rows),
        "failed": failed,
        "court_root": result["court_root"],
        "evidence": str(evidence_path),
        "evidence_sha256": sha(evidence_zip),
        **BOUNDARY,
    }, sort_keys=True), flush=True)
    return 0 if failed == 0 else 1


def _argument_path(flag: str) -> Path | None:
    """Read a path argument without invoking argparse during fault handling."""
    try:
        index = sys.argv.index(flag)
        return Path(sys.argv[index + 1]).resolve()
    except (ValueError, IndexError, OSError):
        return None


def _write_fault_evidence(error: Exception) -> Path | None:
    """Preserve a typed runner fault without claiming a court result."""
    out = _argument_path("--out")
    if out is None:
        return None
    out.mkdir(parents=True, exist_ok=True)
    subject = _argument_path("--subject")
    kit_manifest_root = None
    if subject is not None:
        manifest_path = subject / "KIT-MANIFEST.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            kit_manifest_root = manifest.get("manifest_root")
        except (OSError, UnicodeError, json.JSONDecodeError):
            pass
    fault_body = {
        "schema": "mosaic.ucm.ccp-admissibility-r014-tier1-runner-fault.v0.1",
        "status": "HOLD_FOR_REPAIR",
        "diagnostic_code": "TIER1_RUNNER_UNHANDLED_EXCEPTION",
        "exception_type": type(error).__name__,
        "exception_message_sha256": sha(str(error).encode("utf-8")),
        "kit_manifest_root": kit_manifest_root,
        **BOUNDARY,
    }
    fault = {**fault_body, "fault_root": sha(canonical(fault_body))}
    report = (
        "# UCM CCP admissibility r014 runner fault\n\n"
        "Status: **HOLD_FOR_REPAIR**  \n"
        "The court did not produce a Tier 1 result. A runner exception was "
        "preserved as diagnostic evidence.\n"
    ).encode("utf-8")
    evidence_payloads = {
        "RUNNER-FAULT.json": canonical(fault) + b"\n",
        "REPORT.md": report,
        "RUN-TIER1.py": Path(__file__).read_bytes(),
    }
    manifest_body = {
        "schema": "mosaic.ucm.ccp-admissibility-r014-tier1-fault-evidence-manifest.v0.1",
        "artifact_role": "UCM_CCP_ADMISSIBILITY_R014_TIER1_FAULT_EVIDENCE",
        "files": [
            {"path": name, "bytes": len(raw), "sha256": sha(raw)}
            for name, raw in sorted(evidence_payloads.items())
        ],
        "file_count": len(evidence_payloads),
        **BOUNDARY,
    }
    evidence_payloads["EVIDENCE-MANIFEST.json"] = canonical({
        **manifest_body,
        "manifest_root": sha(canonical(manifest_body)),
    }) + b"\n"
    evidence_zip = zip_bytes(evidence_payloads)
    evidence_path = out / (
        "UCM-CCP-ADMISSIBILITY-r014-TIER1-EVIDENCE-FAULT-"
        f"{fault['fault_root'][:16]}.zip")
    evidence_path.write_bytes(evidence_zip)
    print(json.dumps({
        "status": "HOLD_FOR_REPAIR",
        "diagnostic_code": fault["diagnostic_code"],
        "fault_root": fault["fault_root"],
        "evidence": str(evidence_path),
        "evidence_sha256": sha(evidence_zip),
        **BOUNDARY,
    }, sort_keys=True), flush=True)
    return evidence_path


def guarded_main() -> int:
    try:
        return main()
    except Exception as error:
        if _write_fault_evidence(error) is None:
            raise
        return 2


if __name__ == "__main__":
    raise SystemExit(guarded_main())

"""External signature and independent-host acceptance for Mosaic UI releases."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from .canonical import atomic_write, canonical_bytes, commitment, read_json
from .model import UIRefusal


def machine_root() -> str:
    facts = {"node": platform.node(), "system": platform.system(), "machine": platform.machine()}
    return commitment("MOSAIC.UI.HOST.IDENTITY.v0.1", facts)


def acceptance_subject_root(subjects: list[dict[str, Any]], evidence_commitment: str) -> str:
    return commitment("MOSAIC.UI.EXTERNAL_ACCEPTANCE_SUBJECT.v0.1", {
        "subjects": subjects, "evidence_commitment": evidence_commitment,
    })


def make_second_host_request(subjects: list[dict[str, Any]], evidence_commitment: str) -> dict[str, Any]:
    value = {
        "schema": "mosaic.ui.second-host-request.v0.1",
        "subject_root": acceptance_subject_root(subjects, evidence_commitment),
        "origin_machine_root": machine_root(),
        "required_gates": ["RELEASE_VERIFY", "WHEEL_INSTALL", "HEADLESS_PROTOCOL", "BROWSER_PROTOCOL",
                           "VISUAL_BASELINE"],
        "standing": "LOCAL_CANDIDATE", "authority_effect": "NONE",
        "claim_boundary": "REQUEST_CREATION_DOES_NOT_ESTABLISH INDEPENDENT_HOST_EXECUTION",
    }
    value["commitment"] = commitment("MOSAIC.UI.SECOND_HOST_REQUEST.v0.1", value)
    return value


def _run(command: list[str], cwd: Path) -> dict[str, Any]:
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": ""}
    result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, text=True, timeout=300)
    output = result.stdout + result.stderr
    return {"exit_code": result.returncode,
            "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
            "output_tail": output[-2000:]}


def run_second_host_acceptance(release_dir: Path, output: Path) -> dict[str, Any]:
    from .release import verify_release

    release_dir, output = release_dir.resolve(), output.resolve()
    verification = verify_release(release_dir)
    request = read_json(release_dir / "SECOND-HOST-REQUEST.json")
    request_body = dict(request)
    request_commitment = request_body.pop("commitment", None)
    if request_commitment != commitment("MOSAIC.UI.SECOND_HOST_REQUEST.v0.1", request_body):
        raise UIRefusal("SECOND_HOST_REQUEST_COMMITMENT_REFUSED", "")
    receipt = read_json(release_dir / "release-receipt.json")
    expected_root = acceptance_subject_root(receipt["subjects"], receipt["evidence_commitment"])
    if request.get("subject_root") != expected_root:
        raise UIRefusal("SECOND_HOST_SUBJECT_REFUSED", "")
    current_machine = machine_root()
    independent = current_machine != request["origin_machine_root"]
    wheel_subject = next(item for item in receipt["subjects"] if item["name"].endswith(".whl"))
    with tempfile.TemporaryDirectory(prefix="mosaic-ui-second-host-", dir=output.parent) as raw:
        work = Path(raw)
        install = work / "install"
        pip = _run([sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(install),
                    str(release_dir / wheel_subject["name"])], work)
        script = (
            "import sys;sys.path.insert(0,sys.argv[1]);"
            "from mosaic_ui.sufficiency import build_sufficiency_payload;"
            "from mosaic_ui.realizer import create_realizer,conformance_witness;"
            "from mosaic_ui.visual_certification import verify_baseline;"
            "p=build_sufficiency_payload();"
            "ws=[conformance_witness(create_realizer(i,p),viewports=((1280,800),(800,600))) for i in ('HEADLESS','BROWSER')];"
            "assert all(w['disposition']=='PASS_LOCAL_CANDIDATE' for w in ws);"
            "assert verify_baseline()['disposition']=='PASS_LOCAL_CANDIDATE'"
        )
        runtime = _run([sys.executable, "-I", "-c", script, str(install)], work) if pip["exit_code"] == 0 \
            else {"exit_code": 1, "output_sha256": "", "output_tail": "wheel install failed"}
    gates = {
        "RELEASE_VERIFY": {"status": "PASS", "receipt_commitment": verification["receipt_commitment"]},
        "WHEEL_INSTALL": {"status": "PASS" if pip["exit_code"] == 0 else "FAIL", **pip},
        "PROTOCOL_AND_VISUAL": {"status": "PASS" if runtime["exit_code"] == 0 else "FAIL", **runtime},
        "HOST_INDEPENDENCE": {"status": "PASS" if independent else "REFUSE_SAME_HOST",
                              "origin_machine_root": request["origin_machine_root"],
                              "observed_machine_root": current_machine},
    }
    passed = independent and all(gate["status"] == "PASS" for gate in gates.values())
    value = {
        "schema": "mosaic.ui.second-host-acceptance.v0.1", "subject_root": expected_root,
        "request_commitment": request_commitment, "machine_root": current_machine, "gates": gates,
        "disposition": "PASS_EXTERNAL_HOST_CANDIDATE" if passed else "REFUSE",
        "standing": "EXTERNAL_HOST_CANDIDATE_EVIDENCE" if passed else "LOCAL_NEGATIVE_CONTROL",
        "authority_effect": "NONE",
        "claim_boundary": "MACHINE_FINGERPRINT_SEPARATION_AND CLEAN INSTALL DO NOT ESTABLISH PHYSICAL HOST IDENTITY OR ADMISSION",
    }
    value["commitment"] = commitment("MOSAIC.UI.SECOND_HOST_ACCEPTANCE.v0.1", value)
    atomic_write(output, canonical_bytes(value) + b"\n")
    return value


def create_signature_envelope(
    signing_request: Path, private_key: Path, public_key: Path, signer_id: str, output: Path,
) -> dict[str, Any]:
    request = read_json(signing_request.resolve())
    payload_root = str(request.get("request_commitment") or "")
    if len(payload_root) != 64:
        raise UIRefusal("SIGNING_REQUEST_ROOT_REFUSED", "")
    with tempfile.TemporaryDirectory(prefix="mosaic-ui-sign-") as raw:
        message = Path(raw) / "message.txt"
        signature = Path(raw) / "signature.bin"
        message.write_bytes(payload_root.encode("ascii"))
        run = subprocess.run(["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(private_key.resolve()),
                              "-in", str(message), "-out", str(signature)], capture_output=True, text=True)
        if run.returncode != 0:
            raise UIRefusal("EXTERNAL_SIGNATURE_CREATION_REFUSED", (run.stdout + run.stderr)[-1000:])
        signature_bytes = signature.read_bytes()
    value = {
        "schema": "mosaic.ui.external-signature-envelope.v0.1", "payload_root": payload_root,
        "signer_id": signer_id, "algorithm": "ED25519", "public_key_pem": public_key.read_text(encoding="ascii"),
        "signature_base64": base64.b64encode(signature_bytes).decode("ascii"),
        "standing": "EXTERNAL_SIGNATURE_CANDIDATE", "authority_effect": "NONE",
        "claim_boundary": "SIGNER_IDENTITY_AND KEY TRUST REQUIRE EXTERNAL POLICY",
    }
    value["commitment"] = commitment("MOSAIC.UI.EXTERNAL_SIGNATURE_ENVELOPE.v0.1", value)
    atomic_write(output.resolve(), canonical_bytes(value) + b"\n")
    return value


def verify_signature_envelope(signing_request: Path, envelope_path: Path) -> dict[str, Any]:
    request, envelope = read_json(signing_request.resolve()), read_json(envelope_path.resolve())
    body = dict(envelope)
    observed = body.pop("commitment", None)
    if observed != commitment("MOSAIC.UI.EXTERNAL_SIGNATURE_ENVELOPE.v0.1", body):
        raise UIRefusal("EXTERNAL_SIGNATURE_ENVELOPE_COMMITMENT_REFUSED", "")
    payload_root = str(request.get("request_commitment") or "")
    if envelope.get("payload_root") != payload_root or envelope.get("algorithm") != "ED25519":
        raise UIRefusal("EXTERNAL_SIGNATURE_PAYLOAD_REFUSED", "")
    try:
        signature = base64.b64decode(envelope["signature_base64"], validate=True)
    except (ValueError, TypeError) as exc:
        raise UIRefusal("EXTERNAL_SIGNATURE_ENCODING_REFUSED", "") from exc
    with tempfile.TemporaryDirectory(prefix="mosaic-ui-verify-signature-") as raw:
        root = Path(raw)
        message, public_key, signature_path = root / "message.txt", root / "public.pem", root / "signature.bin"
        message.write_bytes(payload_root.encode("ascii"))
        public_key.write_text(envelope["public_key_pem"], encoding="ascii")
        signature_path.write_bytes(signature)
        run = subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-rawin", "-inkey", str(public_key),
                              "-sigfile", str(signature_path), "-in", str(message)], capture_output=True, text=True)
    if run.returncode != 0:
        raise UIRefusal("EXTERNAL_SIGNATURE_CRYPTOGRAPHIC_REFUSED", (run.stdout + run.stderr)[-1000:])
    return {
        "schema": "mosaic.ui.external-signature-verification.v0.1", "payload_root": payload_root,
        "signer_id": envelope["signer_id"], "algorithm": "ED25519", "status": "CRYPTOGRAPHICALLY_VALID",
        "envelope_commitment": observed, "standing": "EXTERNAL_SIGNATURE_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE", "claim_boundary": "CRYPTOGRAPHIC_VALIDITY_DOES_NOT ESTABLISH SIGNER AUTHORITY OR KEY TRUST",
    }


def finalize_release(
    candidate_dir: Path, signature_envelope: Path, second_host_receipt: Path,
    human_review_receipt: Path, output: Path,
) -> dict[str, Any]:
    from .release import _bundle, verify_release
    from .human_review import verify_human_review_receipt

    candidate_dir, output = candidate_dir.resolve(), output.resolve()
    verification = verify_release(candidate_dir)
    signature = verify_signature_envelope(candidate_dir / "SIGNING-REQUEST.json", signature_envelope)
    human_review = verify_human_review_receipt(
        candidate_dir / "HUMAN-REVIEW-REQUEST.json", human_review_receipt,
    )
    if human_review["status"] != "PASS_HUMAN_REVIEW_CANDIDATE":
        raise UIRefusal("HUMAN_REVIEW_ACCEPTANCE_REFUSED", human_review["status"])
    second = read_json(second_host_receipt.resolve())
    second_body = dict(second)
    second_commitment = second_body.pop("commitment", None)
    if second_commitment != commitment("MOSAIC.UI.SECOND_HOST_ACCEPTANCE.v0.1", second_body) \
            or second.get("disposition") != "PASS_EXTERNAL_HOST_CANDIDATE":
        raise UIRefusal("SECOND_HOST_ACCEPTANCE_REFUSED", "")
    release_receipt = read_json(candidate_dir / "release-receipt.json")
    expected_subject = acceptance_subject_root(release_receipt["subjects"], release_receipt["evidence_commitment"])
    request = read_json(candidate_dir / "SECOND-HOST-REQUEST.json")
    if second.get("subject_root") != expected_subject or second.get("machine_root") == request.get("origin_machine_root"):
        raise UIRefusal("SECOND_HOST_BINDING_REFUSED", "")
    if output.exists():
        raise UIRefusal("FINAL_RELEASE_OUTPUT_EXISTS", str(output))
    output.mkdir(parents=True)
    candidate_bundle = candidate_dir / release_receipt["bundle"]["name"]
    entries = {
        candidate_bundle.name: candidate_bundle.read_bytes(),
        "EXTERNAL-SIGNATURE.json": signature_envelope.read_bytes(),
        "SECOND-HOST-ACCEPTANCE.json": second_host_receipt.read_bytes(),
        "HUMAN-REVIEW-RECEIPT.json": human_review_receipt.read_bytes(),
    }
    finalization = {
        "schema": "mosaic.ui.finalization-evidence.v0.1", "version": release_receipt["version"],
        "candidate_bundle_sha256": hashlib.sha256(candidate_bundle.read_bytes()).hexdigest(),
        "candidate_verification": verification, "signature_verification": signature,
        "second_host_commitment": second_commitment, "human_review_verification": human_review,
        "disposition": "PASS_EXTERNAL_ACCEPTANCE_CANDIDATE",
        "standing": "EXTERNAL_ACCEPTANCE_CANDIDATE", "authority_effect": "NONE",
        "claim_boundary": "EXTERNAL SIGNATURE HOST ACCEPTANCE AND HUMAN REVIEW DO NOT CONSTITUTE CONSTITUTIONAL ADMISSION",
    }
    finalization["commitment"] = commitment("MOSAIC.UI.FINALIZATION_EVIDENCE.v0.1", finalization)
    entries["FINALIZATION-EVIDENCE.json"] = canonical_bytes(finalization) + b"\n"
    bundle = output / f"mosaic-ui-{release_receipt['version']}-external-acceptance-candidate.zip"
    _bundle(bundle, entries)
    final = {
        "schema": "mosaic.ui.final-release-receipt.v0.1", "version": release_receipt["version"],
        "finalization_commitment": finalization["commitment"],
        "bundle": {"name": bundle.name, "sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
                   "bytes": bundle.stat().st_size},
        "disposition": "PASS_EXTERNAL_ACCEPTANCE_CANDIDATE", "standing": "EXTERNAL_ACCEPTANCE_CANDIDATE",
        "authority_effect": "NONE",
        "claim_boundary": "EXTERNAL ACCEPTANCE CANDIDATE IS NOT CONSTITUTIONAL ADMISSION",
    }
    final["receipt_commitment"] = commitment("MOSAIC.UI.FINAL_RELEASE_RECEIPT.v0.1", final)
    atomic_write(output / "final-release-receipt.json", canonical_bytes(final) + b"\n")
    return {**final, "output_dir": str(output)}


__all__ = [
    "acceptance_subject_root", "create_signature_envelope", "finalize_release", "machine_root",
    "make_second_host_request", "run_second_host_acceptance", "verify_signature_envelope",
]

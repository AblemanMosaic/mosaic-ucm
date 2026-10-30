#!/usr/bin/env python3
"""Freeze the qualified Stage I4 c5 source into cold-boot and review artifacts."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root, strict_loads
from ucm.amcas import BOUNDARY
from ucm.artifacts import deterministic_zip, verify_deterministic_zip


COLD_SCHEMA = "mosaic.ucm.amcas-stage-i4-c5-cold-boot.v0.1"
COLD_ROLE = "UCM_AMCAS_STAGE_I4_C5_COLD_BOOT"
TRANSPORT_SCHEMA = "mosaic.ucm.amcas-stage-i4-c5-review-transport.v0.1"
TRANSPORT_ROLE = "UCM_AMCAS_STAGE_I4_C5_REVIEW_TRANSPORT"
HANDOFF_SCHEMA = "mosaic.ucm.amcas-stage-i4-c5-review-handoff.v0.1"
HANDOFF_ROLE = "UCM_AMCAS_STAGE_I4_C5_REVIEW_HANDOFF"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def payloads(raw: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return {item.filename: archive.read(item) for item in archive.infolist()
                if item.filename != "MANIFEST.json"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.out_dir.exists():
        raise SystemExit("C5_RELEASE_OUTPUT_EXISTS")

    qdir = args.qualification_dir
    source_raw = (qdir / "QUALIFICATION-SOURCE.zip").read_bytes()
    source_manifest = verify_deterministic_zip(
        source_raw,
        expected_schema="mosaic.ucm.stage-i4-c5-qualification-source.v0.1",
        expected_role="UCM_AMCAS_STAGE_I4_C5_QUALIFICATION_SOURCE")
    evidence_raw = (qdir / "QUALIFICATION-EVIDENCE.zip").read_bytes()
    evidence_manifest = verify_deterministic_zip(
        evidence_raw,
        expected_schema="mosaic.ucm.stage-i4-c5-qualification-evidence.v0.1",
        expected_role="UCM_AMCAS_STAGE_I4_C5_QUALIFICATION_EVIDENCE")
    qualification_raw = (qdir / "QUALIFICATION.json").read_bytes()
    qualification = strict_loads(qualification_raw)
    if qualification["status"] != "PASS" or qualification["failures"] != 0 \
            or qualification["errors"] != 0 or qualification["skips"] != 0:
        raise SystemExit("C5_QUALIFICATION_NOT_PASS")
    if qualification["source_file_count"] != len(source_manifest["files"]):
        raise SystemExit("C5_SOURCE_COUNT_MISMATCH")

    cold_raw = deterministic_zip(payloads(source_raw), schema=COLD_SCHEMA,
                                 artifact_role=COLD_ROLE)
    cold_manifest = verify_deterministic_zip(cold_raw, expected_schema=COLD_SCHEMA,
                                             expected_role=COLD_ROLE)
    start = canonical_bytes({
        "schema": "mosaic.ucm.amcas-stage-i4-c5-start.v0.1",
        "subject": "UCM-AMCAS Stage I4 c5 operational gateway",
        "cold_boot_sha256": sha(cold_raw),
        "qualification_root": qualification["qualification_root"],
        "interfaces": {
            "human": ["README.md", "docs/OPERATIONAL-GATEWAY.md"],
            "agent": ["AGENT-ACCESS.md", "spec/ucm-system-registry.json"],
            "cli": "python -m ucm operational-invoke <SURFACE> <PAYLOAD.json>",
            "abi": "ucm.invoke",
        },
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        "real_a5": False, "g0": "CLOSED",
    })
    work_order = ("# Stage I4 c5 joint review work order\n\n"
        "Verify custody and the exact cold boot before reading subject instructions. "
        "Reproduce the 20-test cache-free qualification. Review signed permits, "
        "revocation, G1-before-dispatch ordering, executor-signed dispatch and terminal "
        "receipts, uncertain-result reconciliation without redispatch, cancellation, "
        "restart recovery, proof obligations, THR separation, portable archives, and "
        "library/CLI/ABI/agent parity. Run the supplied Tier 1 operator court only as "
        "an external leg. The builder did not execute it. AOK HeadlessRunner, lattice, "
        "and adapter bindings are outside this subject. Keep INFORMATION_ONLY, authority "
        "effect NONE, real A5 false, and G0 closed.\n").encode("utf-8")
    verifier = (ROOT / "VERIFY.py").read_bytes()
    transport_payloads = {
        "UCL-UCM-AMCAS-STAGE-I4-C5-COLD-BOOT.zip": cold_raw,
        "QUALIFICATION-EVIDENCE.zip": evidence_raw,
        "QUALIFICATION.json": qualification_raw,
        "RUNTIME.json": (qdir / "RUNTIME.json").read_bytes(),
        "STAGE-I4-C5-CONTRACT.json": (ROOT / "spec/STAGE-I4-C5-CONTRACT.json").read_bytes(),
        "OPERATIONAL-GATEWAY-REALIZATION-CONTRACT.json":
            (ROOT / "spec/OPERATIONAL-GATEWAY-REALIZATION-CONTRACT.json").read_bytes(),
        "OPERATIONAL-GATEWAY-ENTRY-CRITERIA.json":
            (ROOT / "spec/OPERATIONAL-GATEWAY-ENTRY-CRITERIA.json").read_bytes(),
        "START.json": start,
        "REVIEW-WORK-ORDER.md": work_order,
        "VERIFY.py": verifier,
    }
    transport_raw = deterministic_zip(transport_payloads, schema=TRANSPORT_SCHEMA,
                                      artifact_role=TRANSPORT_ROLE)
    transport_manifest = verify_deterministic_zip(
        transport_raw, expected_schema=TRANSPORT_SCHEMA, expected_role=TRANSPORT_ROLE)

    receipt_body = {
        "schema": "mosaic.ucm.amcas-stage-i4-c5-freeze-receipt.v0.1",
        "cold_boot_sha256": sha(cold_raw),
        "cold_boot_manifest_root": cold_manifest["manifest_root"],
        "cold_boot_files": len(cold_manifest["files"]),
        "qualification_evidence_sha256": sha(evidence_raw),
        "qualification_evidence_manifest_root": evidence_manifest["manifest_root"],
        "qualification_root": qualification["qualification_root"],
        "source_root": qualification["source_root"],
        "test_count": qualification["test_count"],
        "transport_sha256": sha(transport_raw),
        "transport_manifest_root": transport_manifest["manifest_root"],
        "operator_tier1": "PREPARED_SEPARATELY_NOT_EXECUTED_BY_BUILDER",
        **BOUNDARY,
    }
    receipt_raw = canonical_bytes({**receipt_body, "receipt_root": root(receipt_body)})
    dependencies = canonical_bytes({
        "schema": "mosaic.ucm.amcas-stage-i4-c5-dependencies.v0.1",
        "required": ["blake3>=1,<2", "cryptography>=46,<51", "cffi>=2,<3",
                     "pycparser>=3,<4", "PyYAML>=6,<7"],
        "operational_gateway_required": ["cryptography>=46,<51"],
        "python": ">=3.12,<3.14", "standard_library_only": False,
        **BOUNDARY,
    })
    handoff_raw = deterministic_zip({
        "UCL-UCM-AMCAS-STAGE-I4-C5-REVIEW-TRANSPORT.zip": transport_raw,
        "FREEZE-RECEIPT.json": receipt_raw,
        "DEPENDENCIES.json": dependencies,
        "REVIEW-WORK-ORDER.md": work_order,
        "VERIFY.py": verifier,
    }, schema=HANDOFF_SCHEMA, artifact_role=HANDOFF_ROLE)
    handoff_manifest = verify_deterministic_zip(
        handoff_raw, expected_schema=HANDOFF_SCHEMA, expected_role=HANDOFF_ROLE)

    args.out_dir.mkdir(parents=True)
    outputs = {
        "UCL-UCM-AMCAS-STAGE-I4-C5-COLD-BOOT.zip": cold_raw,
        "UCL-UCM-AMCAS-STAGE-I4-C5-REVIEW-TRANSPORT.zip": transport_raw,
        "UCL-UCM-AMCAS-STAGE-I4-C5-REVIEW-HANDOFF.zip": handoff_raw,
        "FREEZE-RECEIPT.json": receipt_raw,
        "REVIEW-WORK-ORDER.md": work_order,
        "DEPENDENCIES.json": dependencies,
    }
    for name, raw in outputs.items():
        (args.out_dir / name).write_bytes(raw)
    index_body = {
        "schema": "mosaic.ucm.amcas-stage-i4-c5-release-index.v0.1",
        "artifacts": [{"path": name, "bytes": len(raw), "sha256": sha(raw)}
                      for name, raw in sorted(outputs.items())],
        "handoff_manifest_root": handoff_manifest["manifest_root"],
        **BOUNDARY,
    }
    (args.out_dir / "RELEASE-INDEX.json").write_bytes(
        canonical_bytes({**index_body, "index_root": root(index_body)}))
    print(json.dumps({"status": "PASS", "directory": str(args.out_dir),
        "cold_boot_sha256": sha(cold_raw), "transport_sha256": sha(transport_raw),
        "handoff_sha256": sha(handoff_raw), "qualification_root": qualification["qualification_root"],
        "source_root": qualification["source_root"], **BOUNDARY}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

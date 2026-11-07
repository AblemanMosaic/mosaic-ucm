#!/usr/bin/env python3
"""Wrap exact repair-successor bytes in an append-only custody envelope."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, strict_loads
from ucm.artifacts import deterministic_zip, verify_deterministic_zip
from ucm.ecosystem_repair_returns import (
    PACKAGE_ROLE, PACKAGE_SCHEMA, receive_repair_return,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("application_id")
    parser.add_argument("artifact", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--audit-register", type=Path,
                        default=ROOT / "integration" /
                        "ECOSYSTEM-AUDIT-RETURN-REGISTER.json")
    args = parser.parse_args()
    artifact = args.artifact.read_bytes()
    receipt = args.receipt.read_bytes()
    envelope = receive_repair_return(
        strict_loads(args.audit_register.read_bytes()),
        application_id=args.application_id, artifact_raw=artifact,
        artifact_filename=args.artifact.name, receipt_raw=receipt)
    package = deterministic_zip({
        "REPAIR-RETURN-ENVELOPE.json": canonical_bytes(envelope),
        "RETURN-RECEIPT.json": receipt,
        "returned/" + args.artifact.name: artifact,
    }, schema=PACKAGE_SCHEMA, artifact_role=PACKAGE_ROLE)
    manifest = verify_deterministic_zip(
        package, expected_schema=PACKAGE_SCHEMA, expected_role=PACKAGE_ROLE)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as stream:
        stream.write(package)
    print(json.dumps({"status": "PASS_REPAIR_RETURN_RECEIVED",
        "application_id": args.application_id,
        "return_envelope_root": envelope["return_envelope_root"],
        "package_sha256": hashlib.sha256(package).hexdigest(),
        "manifest_root": manifest["manifest_root"], "output": str(args.output),
        "standing": envelope["standing"],
        "authority_effect": envelope["authority_effect"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

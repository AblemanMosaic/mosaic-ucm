#!/usr/bin/env python3
"""Wrap exact session-return bytes in a portable, non-authorizing envelope."""
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
from ucm.ecosystem_returns import receive_session_return


SCHEMA = "mosaic.ucm.ecosystem-session-return-package.v0.1"
ROLE = "UCM_ECOSYSTEM_SESSION_RETURN_PACKAGE"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("application_id")
    parser.add_argument("artifact", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--claimed-status", required=True)
    parser.add_argument("--dispatch", type=Path,
        default=ROOT / "integration" / "ECOSYSTEM-SESSION-DISPATCH.json")
    args = parser.parse_args()
    raw = args.artifact.read_bytes()
    dispatch = strict_loads(args.dispatch.read_bytes())
    envelope = receive_session_return(
        dispatch, application_id=args.application_id, artifact_raw=raw,
        artifact_filename=args.artifact.name, claimed_status=args.claimed_status)
    package = deterministic_zip({
        "RETURN-ENVELOPE.json": canonical_bytes(envelope),
        "returned/" + args.artifact.name: raw,
    }, schema=SCHEMA, artifact_role=ROLE)
    manifest = verify_deterministic_zip(package, expected_schema=SCHEMA,
                                        expected_role=ROLE)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as stream:
        stream.write(package)
    print(json.dumps({
        "status": "PASS_RECEIVED_UNVERIFIED",
        "application_id": args.application_id,
        "return_envelope_root": envelope["return_envelope_root"],
        "package_sha256": hashlib.sha256(package).hexdigest(),
        "manifest_root": manifest["manifest_root"],
        "output": str(args.output),
        "standing": envelope["standing"],
        "authority_effect": envelope["authority_effect"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

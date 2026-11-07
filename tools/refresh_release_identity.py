#!/usr/bin/env python3
"""Refresh the public source manifest and its release-identity binding."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PREDECESSOR_IDENTITY = ROOT / "release" / "PREDECESSOR-r026-RELEASE-IDENTITY.json"
PREDECESSOR_QUALIFICATION = ROOT / "release" / "PREDECESSOR-r026-QUALIFICATION.json"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(1, str(ROOT / "tools"))

from release_common import (ENGINEERING_REVISION, PUBLIC_VERSION, canonical,
                            public_source_body, sha)


def write(path: pathlib.Path, value: dict) -> None:
    path.write_bytes(canonical(value) + b"\n")


def frozen_predecessor() -> tuple[dict, dict]:
    predecessor = json.loads(PREDECESSOR_IDENTITY.read_text(encoding="utf-8"))
    body = {key: value for key, value in predecessor.items() if key != "root"}
    if predecessor.get("root") != sha(canonical(body)):
        raise SystemExit("PREDECESSOR_RELEASE_IDENTITY_ROOT_MISMATCH")
    if predecessor.get("engineering_revision") != "r026":
        raise SystemExit("PREDECESSOR_RELEASE_IDENTITY_REVISION_INVALID")
    value = predecessor.get("source_manifest_root")
    if not isinstance(value, str) or len(value) != 64:
        raise SystemExit("PREDECESSOR_SOURCE_ROOT_INVALID")
    qualification = json.loads(PREDECESSOR_QUALIFICATION.read_text(encoding="utf-8"))
    qbody = {key: item for key, item in qualification.items() if key != "root"}
    if qualification.get("root") != sha(canonical(qbody)):
        raise SystemExit("PREDECESSOR_QUALIFICATION_ROOT_MISMATCH")
    if (qualification.get("engineering_revision") != "r026"
            or qualification.get("source_manifest_root") != value
            or qualification.get("status") != "PASS"):
        raise SystemExit("PREDECESSOR_QUALIFICATION_IDENTITY_MISMATCH")
    return predecessor, qualification


def refreshed_identity_body(identity: dict, manifest_root: str) -> dict:
    predecessor, qualification = frozen_predecessor()
    body = {key: value for key, value in identity.items() if key != "root"}
    body["predecessor_engineering_revision"] = "r026"
    # The r026 release identity intentionally kept operator evidence separate.
    # Preserve that exact statement rather than laundering a later observation
    # into predecessor authority.
    body["predecessor_operator_tier1"] = {
        "provenance": "NOT_FROZEN_IN_PREDECESSOR_RELEASE_IDENTITY",
        "operator_tier1_status": "SEPARATE_USER_RUN_REQUIRED",
        "operator_tier1_case_count": 0,
    }
    body["predecessor_release_identity_root"] = predecessor["root"]
    body["predecessor_source_root"] = predecessor["source_manifest_root"]
    body["predecessor_qualification_root"] = qualification["root"]
    body["source_manifest_root"] = manifest_root
    body["version"] = PUBLIC_VERSION
    body["engineering_revision"] = ENGINEERING_REVISION
    body["release_status"] = "CANDIDATE_REQUIRES_FRESH_QUALIFICATION_AND_OPERATOR_TIER1"
    body["operator_tier1_case_count"] = 0
    body["operator_tier1_status"] = "SEPARATE_USER_RUN_REQUIRED"
    return body


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh the public source manifest and release identity")
    parser.parse_args()
    manifest_body = public_source_body(ROOT)
    manifest = {**manifest_body, "root": sha(canonical(manifest_body))}
    identity_path = ROOT / "release" / "RELEASE-IDENTITY.json"
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    identity_body = refreshed_identity_body(identity, manifest["root"])
    refreshed_identity = {**identity_body, "root": sha(canonical(identity_body))}
    write(ROOT / "release" / "SOURCE-MANIFEST.json", manifest)
    write(identity_path, refreshed_identity)
    print(json.dumps({"status": "PASS", "source_manifest_root": manifest["root"],
                      "release_identity_root": refreshed_identity["root"],
                      "engineering_revision": ENGINEERING_REVISION,
                      "member_count": manifest["member_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


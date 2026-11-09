"""Freeze r036 while preserving the exact r035 predecessor through preimages."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from release_common import canonical, public_source_body, sha

PREDECESSOR_ROOT = "b91652b352cbf12b9a0e4083121439f19ae96ca6224caadab874f8f30c5d29aa"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value) + b"\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predecessor", type=Path, required=True)
    args = parser.parse_args()
    predecessor = args.predecessor.resolve()
    archive = ROOT / "review/r035-predecessor"
    original = json.loads((predecessor / "release/SOURCE-MANIFEST.json").read_bytes())
    if original["root"] != PREDECESSOR_ROOT:
        raise SystemExit("R035_PREDECESSOR_PIN_MISMATCH")
    if sha(canonical({k: v for k, v in original.items() if k != "root"})) != original["root"]:
        raise SystemExit("R035_PREDECESSOR_ROOT_INVALID")
    archive.mkdir(parents=True, exist_ok=True)
    (archive / "SOURCE-MANIFEST.json").write_bytes(
        (predecessor / "release/SOURCE-MANIFEST.json").read_bytes())
    rows = []
    for row in original["members"]:
        old = (predecessor / row["path"]).read_bytes()
        if len(old) != row["bytes"] or sha(old) != row["sha256"]:
            raise SystemExit("R035_PREDECESSOR_MEMBER_DRIFT:" + row["path"])
        current = ROOT / row["path"]
        if current.is_file() and current.read_bytes() == old:
            continue
        target = archive / "preimages" / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(old)
        rows.append({"path": row["path"], "previous_sha256": row["sha256"],
                     "previous_bytes": len(old),
                     "preimage_path": target.relative_to(ROOT).as_posix(),
                     "successor_sha256": sha(current.read_bytes()) if current.is_file() else None})
    body = {"schema": "mosaic.ucm.r036-predecessor-delta.v0.1",
            "predecessor_revision": "r035", "predecessor_source_root": original["root"],
            "predecessor_member_count": len(original["members"]), "changed_members": rows,
            "reconstruction": "UNCHANGED_SUCCESSOR_MEMBERS_PLUS_EXACT_R035_PREIMAGES",
            "authority_effect": "NONE", "standing": "INFORMATION_ONLY"}
    write(archive / "DELTA.json", {**body, "root": sha(canonical(body))})
    for name, target_name in (("RELEASE-IDENTITY.json", "PREDECESSOR-r035-RELEASE-IDENTITY.json"),
                              ("UCM-v0.1-QUALIFICATION.json", "PREDECESSOR-r035-QUALIFICATION.json")):
        (ROOT / "release" / target_name).write_bytes((predecessor / "release" / name).read_bytes())
    source_body = public_source_body(ROOT)
    source = {**source_body, "root": sha(canonical(source_body))}
    old_identity = json.loads((predecessor / "release/RELEASE-IDENTITY.json").read_bytes())
    old_qualification = json.loads((predecessor / "release/UCM-v0.1-QUALIFICATION.json").read_bytes())
    identity_body = {"schema": "mosaic.ucm.release-identity.v0.1",
        "product": "Universal Constitutional Machine", "short_name": "UCM",
        "publisher": "Ableman Mosaic", "copyright": "Copyright 2026 Ableman Mosaic",
        "license": "Apache-2.0", "version": "v0.1", "engineering_revision": "r036",
        "source_manifest_root": source["root"], "predecessor_engineering_revision": "r035",
        "predecessor_source_root": original["root"],
        "predecessor_release_identity_root": old_identity["root"],
        "predecessor_qualification_root": old_qualification["root"],
        "qualification_scope": "POSITIVE_CONSTRUCTION_AND_STATIC_SOURCE",
        "qualification_receipt_path": "UCM-v0.1-QUALIFICATION.json",
        "release_status": "CANDIDATE_POSITIVE_CONSTRUCTION_OPERATOR_REVIEW_PENDING",
        "operator_tier1_status": "SEPARATE_USER_RUN_REQUIRED", "operator_tier1_case_count": 20,
        "independent_review": "NOT_PERFORMED", "installed": "NOT_ESTABLISHED",
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE", "real_a5": False, "g0": "CLOSED"}
    write(ROOT / "release/SOURCE-MANIFEST.json", source)
    identity = {**identity_body, "root": sha(canonical(identity_body))}
    write(ROOT / "release/RELEASE-IDENTITY.json", identity)
    print(json.dumps({"status": "PASS", "source_manifest_root": source["root"],
        "release_identity_root": identity["root"], "predecessor_preimage_count": len(rows),
        "predecessor_member_count": len(original["members"])}))


if __name__ == "__main__":
    main()

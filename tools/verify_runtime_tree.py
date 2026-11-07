#!/usr/bin/env python3
"""Verify an extracted UCM runtime without importing UCM subject code."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from pathlib import PurePosixPath


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=pathlib.Path)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest_path = root / "MANIFEST.json"
    if not manifest_path.is_file():
        raise SystemExit("RUNTIME_MANIFEST_MISSING")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    body = {key: value for key, value in manifest.items() if key != "root"}
    if sha(canonical(body)) != manifest.get("root"):
        raise SystemExit("RUNTIME_MANIFEST_ROOT_MISMATCH")
    if (
        manifest.get("schema") != "mosaic.ucm.artifact-manifest.v0.1"
        or manifest.get("artifact") != "UCM_RUNTIME"
        or manifest.get("completeness") != "COMPLETE_RUNTIME"
        or manifest.get("version") != "v0.1"
        or manifest.get("engineering_revision") != "r023"
        or manifest.get("standing") != "INFORMATION_ONLY"
        or manifest.get("authority_effect") != "NONE"
        or manifest.get("real_a5") is not False
        or manifest.get("g0") != "CLOSED"
    ):
        raise SystemExit("RUNTIME_MANIFEST_BOUNDARY_MISMATCH")
    rows = manifest.get("members")
    if not isinstance(rows, list) or len(rows) != manifest.get("member_count"):
        raise SystemExit("RUNTIME_MANIFEST_ROWS_INVALID")
    expected: dict[str, dict] = {}
    folded: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "sha256", "bytes"}:
            raise SystemExit("RUNTIME_MANIFEST_ROW_INVALID")
        name = row["path"]
        path = PurePosixPath(name) if isinstance(name, str) else PurePosixPath("/")
        if path.is_absolute() or not path.parts or ".." in path.parts or "\\" in name:
            raise SystemExit("RUNTIME_MANIFEST_PATH_REFUSED")
        if name.casefold() in folded:
            raise SystemExit("RUNTIME_MANIFEST_PATH_ALIAS")
        folded.add(name.casefold()); expected[name] = row
    observed: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise SystemExit("RUNTIME_TREE_ALIAS_REFUSED")
        if path.is_file():
            name = path.relative_to(root).as_posix()
            if name != "MANIFEST.json":
                observed.add(name)
    if observed != set(expected):
        raise SystemExit("RUNTIME_TREE_SET_MISMATCH")
    for name, row in expected.items():
        data = (root / pathlib.PurePosixPath(name)).read_bytes()
        if len(data) != row["bytes"] or sha(data) != row["sha256"]:
            raise SystemExit("RUNTIME_TREE_MEMBER_MISMATCH:" + name)
    required_meta = {"META/STATE-MANIFEST.json", "META/DKN-BINDING.json",
                     "META/THR-MANIFEST.json", "META/SELF-CERTIFICATE.json"}
    if not required_meta <= observed:
        raise SystemExit("RUNTIME_CERTIFICATION_META_MISSING")
    state = json.loads((root / "META/STATE-MANIFEST.json").read_text(encoding="utf-8"))
    payload_names = sorted(observed - required_meta)
    state_rows = [{"path": name, "sha256": sha((root / pathlib.PurePosixPath(name)).read_bytes()),
                   "bytes": (root / pathlib.PurePosixPath(name)).stat().st_size}
                  for name in payload_names]
    state_body = {key: value for key, value in state.items() if key != "state_root"}
    if (state.get("state_root") != sha(canonical(state_body))
            or state.get("members") != state_rows
            or state.get("engineering_revision") != manifest["engineering_revision"]):
        raise SystemExit("RUNTIME_CERTIFICATION_STATE_INVALID")
    dkn = json.loads((root / "META/DKN-BINDING.json").read_text(encoding="utf-8"))
    thr = json.loads((root / "META/THR-MANIFEST.json").read_text(encoding="utf-8"))
    cert = json.loads((root / "META/SELF-CERTIFICATE.json").read_text(encoding="utf-8"))
    if (dkn.get("status") != "DECLARED_UNBOUND"
            or cert.get("certificate_status") != "READY_FOR_EXTERNAL_DKN_CERTIFICATION"
            or cert.get("state_root") != state["state_root"]
            or cert.get("thr_body_root") != thr.get("h_body")):
        raise SystemExit("RUNTIME_CERTIFICATION_BOUNDARY_INVALID")
    print(json.dumps({"status": "PASS", "runtime_root": manifest["root"],
                      "member_count": len(expected), "state_root": state["state_root"],
                      "thr_body_root": thr["h_body"],
                      "certificate_status": cert["certificate_status"],
                      "standing": "INFORMATION_ONLY",
                      "authority_effect": "NONE", "real_a5": False, "g0": "CLOSED"},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


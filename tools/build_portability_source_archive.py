#!/usr/bin/env python3
"""Build an exact deterministic source archive for Windows/WSL correspondence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from release_common import canonical, public_source_body, sha

ROOT = Path(__file__).resolve().parents[1]
FIXED = (1980, 1, 1, 0, 0, 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest-output", type=Path)
    args = parser.parse_args()
    body = public_source_body(ROOT)
    source_root = sha(canonical(body))
    manifest = {**body, "root": source_root}
    members = {row["path"]: (ROOT / row["path"]).read_bytes()
               for row in body["members"]}
    members["PORTABILITY-SOURCE-MANIFEST.json"] = canonical(manifest) + b"\n"
    if args.manifest_output is not None:
        args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_output.write_bytes(members["PORTABILITY-SOURCE-MANIFEST.json"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for name, raw in sorted(members.items()):
            info = zipfile.ZipInfo(name, FIXED)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw)
    print(json.dumps({"status": "PASS", "path": str(args.output),
                      "sha256": sha(args.output.read_bytes()),
                      "source_root": source_root,
                      "members": len(members), "standing": "INFORMATION_ONLY",
                      "authority_effect": "NONE", "real_a5": False,
                      "g0": "CLOSED"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

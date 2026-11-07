#!/usr/bin/env python3
"""Build the exact qualification-source archive consumed by the operator kit."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes  # noqa: E402
from amcas_release_common import build_qualification_source_archive  # noqa: E402


def write_new(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        __import__("os").fsync(stream.fileno())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--anchor-out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.anchor_out.exists():
        raise SystemExit("STAGE_I4_C3_QUALIFICATION_SOURCE_DESTINATION_EXISTS")
    first, first_anchor = build_qualification_source_archive()
    second, second_anchor = build_qualification_source_archive()
    if first != second or first_anchor != second_anchor:
        raise SystemExit("STAGE_I4_C3_QUALIFICATION_SOURCE_NONDETERMINISTIC")
    write_new(args.out, first)
    write_new(args.anchor_out, canonical_bytes(first_anchor))
    print(json.dumps({"status": "PASS", "path": str(args.out),
        "bytes": len(first), "sha256": hashlib.sha256(first).hexdigest(),
        "anchor_root": first_anchor["anchor_root"],
        "source_manifest_root": first_anchor["source_manifest_root"]},
        sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

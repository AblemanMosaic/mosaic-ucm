#!/usr/bin/env python3
"""Build one rooted research-review record from a strict JSON request."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from uclop.canonical import canonical_bytes, exact_keys, strict_loads
from ucm.research_reviews import (
    build_finding_adjudication,
    build_review_finding,
    build_review_lens_pack,
    build_saturation_assessment,
    build_successor_ledger,
)


BUILDERS = {
    "lens-pack": build_review_lens_pack,
    "finding": build_review_finding,
    "adjudication": build_finding_adjudication,
    "successor-ledger": build_successor_ledger,
    "saturation": build_saturation_assessment,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    request = exact_keys(strict_loads(args.request.read_bytes()), {"kind", "arguments"})
    if request["kind"] not in BUILDERS or type(request["arguments"]) is not dict:
        raise ValueError("RESEARCH_RECORD_BUILD_REQUEST_INVALID")
    record = BUILDERS[request["kind"]](**request["arguments"])
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    pending = output.with_name(output.name + ".pending")
    with pending.open("wb") as stream:
        stream.write(canonical_bytes(record) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(pending, output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

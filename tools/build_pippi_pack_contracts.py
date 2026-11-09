#!/usr/bin/env python3
"""Generate the public P/PPI component registry and human projection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ucm.pippi_packs import pack_registry  # noqa: E402


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False) + "\n"


def document(registry: dict) -> str:
    index = {row["pack_id"]: row for row in registry["packs"]}
    lines = [
        "# P/PPI capability packs",
        "",
        "P/PPI works as a complete constitutional project and process interface with only its built-in core. Optional packs add realizations; they never relax a contract when absent.",
        "",
        "## Profiles",
        "",
        "| Profile | Packs |",
        "| --- | --- |",
    ]
    for profile, packs in registry["profiles"].items():
        lines.append(f"| `{profile}` | " + ", ".join(f"`{item}`" for item in packs) + " |")
    lines += ["", "## Packs", "", "| Pack | Default | Distribution | Purpose |", "| --- | --- | --- | --- |"]
    for pack_id in sorted(index):
        row = index[pack_id]
        lines.append(f"| `{pack_id}` | {'yes' if row['default_selected'] else 'no'} | `{row['distribution']}` | {row['description']} |")
    lines += [
        "", "## Effect boundary", "",
        "The resolver creates a content-rooted plan only. It does not download, install, bind, register a service, use a credential, or grant authority. Remote acquisition requires explicit user authorization and an external effect gateway. External bindings require their owner's independently verified receipt.",
        "",
        "An installed project records its required pack IDs. Opening it on another host yields `READY` or `NEEDS_PACKS`; view-only inspection remains available. Missing packs do not delete requirements or silently select a weaker realization.",
        "",
        f"Registry root: `{registry['registry_root']}`",
        "",
    ]
    return "\n".join(lines)


def records() -> dict[Path, bytes]:
    registry = pack_registry()
    return {
        ROOT / "spec" / "PIPPI-PACK-REGISTRY.json": canonical(registry).encode("utf-8"),
        ROOT / "docs" / "PIPPI-CAPABILITY-PACKS.md": document(registry).encode("utf-8"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    mismatches = []
    for path, expected in records().items():
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
        elif not path.is_file() or path.read_bytes() != expected:
            mismatches.append(path.relative_to(ROOT).as_posix())
    registry = pack_registry()
    print(canonical({"status": "PASS", "registry_root": registry["registry_root"],
                     "packs": len(registry["packs"]), "profiles": len(registry["profiles"]),
                     "mismatches": mismatches}).strip())
    return 0 if not mismatches else 3


if __name__ == "__main__":
    raise SystemExit(main())

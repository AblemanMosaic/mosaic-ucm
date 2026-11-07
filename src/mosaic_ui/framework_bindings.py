"""Optional compatibility adapters for hosts already using UI frameworks."""
from __future__ import annotations

import argparse
import hashlib
import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from .canonical import atomic_write, canonical_bytes, commitment


ADAPTER_FILES = ("react.js", "vue.js", "svelte.js", "index.d.ts", "package.json")
BINDING_FILES = ADAPTER_FILES


def binding_manifest() -> dict[str, Any]:
    root = files("mosaic_ui").joinpath("contrib", "web_adapters")
    entries = []
    for name in BINDING_FILES:
        data = root.joinpath(name).read_bytes()
        entries.append({"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    value = {
        "schema": "mosaic.ui.framework-adapters.v0.1",
        "frameworks": ["REACT", "SVELTE", "VUE"],
        "canonical_runtime": False,
        "standing": "OPTIONAL_COMPATIBILITY_CONTRIB",
        "entries": entries,
        "authority_effect": "NONE",
    }
    value["commitment"] = commitment("MOSAIC.UI.FRAMEWORK_ADAPTERS.v0.1", value)
    return value


def export_bindings(output: Path) -> dict[str, Any]:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    root = files("mosaic_ui").joinpath("contrib", "web_adapters")
    for name in BINDING_FILES:
        atomic_write(output / name, root.joinpath(name).read_bytes())
    manifest = binding_manifest()
    atomic_write(output / "mosaic-adapters-manifest.json", canonical_bytes(manifest) + b"\n")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    manifest = export_bindings(args.output)
    print(json.dumps(manifest, sort_keys=True))
    return 0


__all__ = ["ADAPTER_FILES", "BINDING_FILES", "binding_manifest", "export_bindings"]


if __name__ == "__main__":
    raise SystemExit(main())

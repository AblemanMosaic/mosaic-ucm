"""Canonical standards-only Mosaic Web distribution."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from .canonical import atomic_write, canonical_bytes, commitment


WEB_FILES = ("core.js", "index.d.ts", "package.json")


def web_manifest() -> dict[str, Any]:
    root = files("mosaic_ui").joinpath("web")
    entries = []
    for name in WEB_FILES:
        data = root.joinpath(name).read_bytes()
        entries.append({"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    value = {
        "schema": "mosaic.ui.web-distribution.v0.1",
        "interface": "WEB_COMPONENT_AND_STANDARD_ES_MODULE",
        "runtime_dependencies": [],
        "framework_dependencies": [],
        "isolation_modes": ["SANDBOXED_IFRAME"],
        "entries": entries,
        "standing": "LOCAL_CANDIDATE",
        "authority_effect": "NONE",
    }
    value["commitment"] = commitment("MOSAIC.UI.WEB_DISTRIBUTION.v0.1", value)
    return value


def export_web(output: Path) -> dict[str, Any]:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    root = files("mosaic_ui").joinpath("web")
    for name in WEB_FILES:
        atomic_write(output / name, root.joinpath(name).read_bytes())
    manifest = web_manifest()
    atomic_write(output / "mosaic-web-manifest.json", canonical_bytes(manifest) + b"\n")
    return manifest


def demo_document(endpoint: str) -> str:
    target = html.escape(str(endpoint), quote=True)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mosaic Web</title>
<style>html,body{{margin:0;height:100%;background:#141618}}mosaic-ui{{height:100%;min-height:520px}}</style>
<script type="module" src="/web/core.js"></script></head>
<body><mosaic-ui endpoint="{target}" title="Mosaic UI hosted surface"></mosaic-ui></body></html>"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(export_web(args.output), sort_keys=True))
    return 0


__all__ = ["WEB_FILES", "demo_document", "export_web", "web_manifest"]


if __name__ == "__main__":
    raise SystemExit(main())

"""Review library surface (library L5): pick any style pack x v0.2 look; /library index; hash-pinned export.

Rulings: L5-R1 extend the workbench; L5-R2 unknown choices get an explicit refusal page (no silent fallback);
L5-R3 no in-shell switcher; L5-R4 export is hash-pinned, signing deferred.
`/` with neither `pack` nor `theme` in its query stays byte-identical to the committed shipped shell.
"""
from __future__ import annotations

import hashlib
import html as _html
import json
import threading
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlsplit

from .canonical import commitment
from .model import UIRefusal
from .review_shell import _font_block, assemble, list_packs, load_binding, load_pack, sheet_from_theme_v02, shell_script

PACK_DEFAULT = ("g2-stage", "signature-dark")
_cache: dict[tuple[str, str], str] = {}
_lock = threading.Lock()


def _themes() -> list[str]:
    from mosaic_ui_std.theme_v02 import list_themes_v02
    return list_themes_v02()


def validate_selection(pack_id: str, theme_id: str) -> None:
    if pack_id not in list_packs():
        raise UIRefusal("REVIEW_LIBRARY_PACK_UNKNOWN", pack_id)
    if theme_id not in _themes():
        raise UIRefusal("REVIEW_LIBRARY_THEME_UNKNOWN", theme_id)


def shell_for(pack_id: str, theme_id: str) -> str:
    validate_selection(pack_id, theme_id)
    with _lock:
        if (pack_id, theme_id) not in _cache:
            _cache[(pack_id, theme_id)] = assemble(pack_id, theme_id)
        return _cache[(pack_id, theme_id)]


def resolve_request(path: str, default: tuple[str, str] | None = None) -> tuple[int, str]:
    """(status, html) for a review-shell request. No pack/theme in the query and no server default -> shipped shell."""
    query = parse_qs(urlsplit(path).query, keep_blank_values=True)
    if "pack" not in query and "theme" not in query and default is None:
        from .review_workbench import REVIEW_WORKBENCH_HTML
        return 200, REVIEW_WORKBENCH_HTML
    base = default or PACK_DEFAULT
    try:
        for key in ("pack", "theme"):
            if len(query.get(key, [])) > 1:
                raise UIRefusal("REVIEW_LIBRARY_SELECTION_AMBIGUOUS", key)
        pack_id = query.get("pack", [base[0]])[0]
        theme_id = query.get("theme", [base[1]])[0]
        return 200, shell_for(pack_id, theme_id)
    except UIRefusal as refusal:
        return 404, refusal_page(refusal.code, refusal.detail)


def _page(title: str, body: str) -> str:
    sheet = sheet_from_theme_v02(PACK_DEFAULT[1])
    tokens = ":root{" + ";".join(f"--{name}:{value}" for name, value in sheet["vars"]) + "}"
    css = """
*{box-sizing:border-box}body{margin:0;background:var(--canvas);color:var(--text);font:15px/1.5 var(--sans)}
main{max-width:1080px;margin:0 auto;padding:32px 24px 48px}
h1{font-size:28px;margin:0 0 6px}h2{font-size:19px;margin:28px 0 8px}p{color:var(--quiet);margin:0 0 12px;max-width:72ch}
a{color:var(--accent)}a:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
.pack{border:1px solid var(--border);border-radius:var(--r-lg);background:var(--surface);padding:16px 18px;margin:14px 0}
.meta{display:flex;flex-wrap:wrap;gap:8px 18px;color:var(--quiet);font-size:13px;margin:4px 0 12px}
ul.looks{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:8px}
ul.looks a{display:block;padding:8px 10px;border:1px solid var(--border);border-radius:var(--r-md);background:var(--raised);text-decoration:none;color:var(--text)}
ul.looks a:hover{border-color:var(--accent)}ul.looks small{display:block;color:var(--quiet)}
code{font-family:var(--mono);font-size:13px}.refusal{border-left:4px solid var(--refused);padding:12px 16px;background:var(--surface)}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{_html.escape(title)}</title><style>\n{_font_block(sheet['fonts'])}\n{tokens}\n{css}</style></head>"
            f"<body><main>{body}</main></body></html>")


def library_page() -> str:
    from mosaic_ui_std.theme_v02 import THEMES_V02_DIR, load_theme_v02
    themes = [(t, load_theme_v02(THEMES_V02_DIR / f"{t}.json")) for t in _themes()]
    parts = ['<h1>Mosaic review library</h1><p>Every optional style pack in every governed look. Each link opens that '
             'combination against the same live review session and API. The canonical adaptive Signature V3 workbench '
             'remains <a href="/">the default route</a>.</p>']
    for pack_id in list_packs():
        manifest = load_pack(pack_id)["manifest"]
        features = [name for name in ("thumbnails", "batch") if name in manifest]
        parts.append(f'<section class="pack" aria-labelledby="pack-{pack_id}"><h2 id="pack-{pack_id}">{_html.escape(manifest["name"])}</h2>'
                     f'<div class="meta"><span>Job: {_html.escape(manifest["job"])}</span><span>Version {_html.escape(manifest["version"])}</span>'
                     f'<span>Pack id <code>{_html.escape(pack_id)}</code></span>'
                     f'<span>Features: {_html.escape(", ".join(features) or "core review")}</span></div><ul class="looks">')
        for theme_id, theme in themes:
            href = f"/?pack={quote(pack_id)}&amp;theme={quote(theme_id)}"
            parts.append(f'<li><a href="{href}">{_html.escape(theme["label"])}<small>{_html.escape(theme["scheme"])} · '
                         f'{_html.escape(manifest["name"])}</small></a></li>')
        parts.append("</ul></section>")
    parts.append("<p>Standing: local candidate. Governed semantic evidence per pack: "
                 "<code>mosaic-ui review-court --pack &lt;id&gt; --themes all</code>.</p>")
    return _page("Mosaic review library", "".join(parts))


def refusal_page(code: str, detail: str) -> str:
    packs = ", ".join(list_packs())
    themes = ", ".join(_themes())
    return _page("Selection refused", f'<h1>Selection refused</h1><div class="refusal" role="alert"><p><code>{_html.escape(code)}</code>: '
                 f'{_html.escape(detail)}</p></div><p>Known packs: <code>{_html.escape(packs)}</code>.</p>'
                 f'<p>Known looks: <code>{_html.escape(themes)}</code>.</p><p><a href="/library">Open the review library</a></p>')


def export_pack(pack_id: str, theme_id: str, output: Path) -> dict[str, Any]:
    """Hash-pinned export (L5-R4): the assembled shell plus a manifest. Signing deferred. Deterministic."""
    from mosaic_ui import __version__
    from mosaic_ui_std.theme_v02 import THEMES_V02_DIR, load_theme_v02, theme_v02_commitment
    html = shell_for(pack_id, theme_id)
    output.mkdir(parents=True, exist_ok=True)
    stem = f"{pack_id}__{theme_id}"
    (output / f"{stem}.html").write_text(html, encoding="utf-8", newline="")
    manifest = {
        "schema": "mosaic.ui.review-pack-export.v0.1", "pack_id": pack_id, "pack_version": load_pack(pack_id)["manifest"]["version"],
        "theme_id": theme_id, "theme_commitment": theme_v02_commitment(load_theme_v02(THEMES_V02_DIR / f"{theme_id}.json")),
        "binding_commitment": load_binding()["commitment"], "mosaic_ui_version": __version__,
        "html_file": f"{stem}.html", "html_sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
        "shell_script_sha256": hashlib.sha256(shell_script().encode("utf-8")).hexdigest(),
        "requires": "a host serving the Mosaic review API (/api/review-ontology, /api/review-session, /api/review-action, /api/review-snapshot)",
        "signature": "NOT_SIGNED (ruling L5-R4: signing deferred)", "standing": "LOCAL_CANDIDATE", "authority_effect": "NONE",
    }
    manifest["commitment"] = commitment("MOSAIC.UI.REVIEW_PACK_EXPORT.v0.1", manifest)
    (output / f"{stem}.manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest

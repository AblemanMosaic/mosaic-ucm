"""Review shell assembly from style packs and v0.2 themes (library L2).

A style pack recomposes the review shell's static markup and CSS; the shell script is never edited (B1).
The binding manifest, generated from the script, records what the script depends on. `assemble` is
deterministic; `REVIEW_WORKBENCH_HTML` is committed as `assemble("g2-stage", "signature-dark")` and a test
fails on drift (ruling L2-R2).
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any

from .canonical import commitment, read_json
from .model import UIRefusal

PACKS_DIR = Path(__file__).resolve().parent / "packs"
BINDING_PATH = Path(__file__).resolve().parent / "review_binding.json"
SHELL_DIR = PACKS_DIR / "_shell"
BASE_DIR = PACKS_DIR / "_base"
# Opt-in features (L4b-R1): a pack declares them as attributes on #catalog; their elements are then required.
OPT_IN = {"data-thumbnails": {"ids": (), "selectors": ()},
          "data-batch": {"ids": ("batch-bar", "batch-clear", "batch-count"), "selectors": ("[data-batch-disposition]",)}}
GOVERNED_ELEMENTS = {"frame": (".frame", "#frame"), "specimen": (".specimen", "#specimen"), "runner": (".status", "#runner")}

# v0.2 theme role -> review shell CSS variable (L2-R2). Shape and density stay pack-level grammar choices.
ROLE_VARS = (("canvas", "canvas"), ("surface", "surface"), ("raised", "surface_raised"), ("field", "field"),
             ("border", "border"), ("border-strong", "border_strong"), ("grid", "surface"), ("text", "text"),
             ("quiet", "text_quiet"), ("accent", "accent"), ("accent-soft", "selection"), ("focus", "focus"),
             ("warning", "pending"), ("refused", "refused"), ("success", "success"), ("on-accent", "on_accent"),
             ("on-refused", "on_refused"))
PACK_SHAPE = (("fs-base", "13px"), ("ctl", "32px"), ("pad", "14px"))


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def shell_script(packs_dir: Path = PACKS_DIR) -> str:
    return _text(packs_dir / "_shell" / "script.html")


def generate_binding(script: str | None = None) -> dict[str, Any]:
    """What the shell script depends on: ids, attribute selectors, and style properties it sets itself."""
    js = script if script is not None else shell_script()
    ids = sorted(set(re.findall(r"\$\('#([\w-]+)'\)", js)) | set(re.findall(r"getElementById\('([\w-]+)'\)", js)))
    selectors = sorted(set(re.findall(r"querySelector(?:All)?\('(\[[\w-]+\])'\)", js)))
    aliases = dict(re.findall(r"\b(\w+)=\$\('#([\w-]+)'\)", js))
    governed = []
    for target, prop in re.findall(r"(\$\('#[\w-]+'\)|\b\w+)\.style\.(\w+)=", js):
        element = target[4:-2] if target.startswith("$('#") else aliases.get(target, target)
        governed.append({"id": element, "property": prop})
    optional = sorted(set(re.findall(r"opt\('([^']+)'\)", js)))
    value = {"schema": "mosaic.ui.review-binding.v0.2", "ids": ids, "attribute_selectors": selectors,
             "optional_ids": sorted(o[1:] for o in optional if o.startswith("#")),
             "optional_selectors": sorted(o for o in optional if o.startswith("[")),
             "governed_style": sorted(governed, key=lambda g: (g["id"], g["property"])),
             "standing": "LOCAL_CANDIDATE", "authority_effect": "NONE"}
    value["commitment"] = commitment("MOSAIC.UI.REVIEW_BINDING.v0.1", value)
    return value


def load_binding() -> dict[str, Any]:
    return read_json(BINDING_PATH)


def load_pack(pack_id: str, packs_dir: Path = PACKS_DIR) -> dict[str, Any]:
    folder = packs_dir / pack_id
    if pack_id.startswith("_") or not (folder / "pack.json").is_file():
        raise UIRefusal("REVIEW_PACK_UNKNOWN", pack_id)
    manifest = read_json(folder / "pack.json")
    if manifest.get("pack_id") != pack_id or manifest.get("authority_effect") != "NONE":
        raise UIRefusal("REVIEW_PACK_MANIFEST_INVALID", pack_id)
    return {"manifest": manifest, "body": _text(folder / "body.html"), "grammar_css": _text(folder / "grammar.css"),
            "base_css": [_text(packs_dir / "_base" / name) for name in manifest["base"]]}


def _css_rules(css: str) -> list[tuple[str, str]]:
    return [(sel.strip(), body) for sel, body in re.findall(r"([^{}@]+)\{([^{}]*)\}", css)]


def validate_pack(pack_id: str, *, extra_css: str = "", body: str | None = None) -> list[str]:
    """Binding contract + CSS discipline. Returns every violation (empty when the pack conforms)."""
    pack, binding = load_pack(pack_id), load_binding()
    markup = pack["body"] if body is None else body
    problems = []
    for element_id in binding["ids"]:
        count = len(re.findall(r'id="' + re.escape(element_id) + '"', markup))
        if count != 1:
            problems.append(f"BINDING_ID_COUNT:{element_id}:{count}")
    for selector in binding["attribute_selectors"]:
        attr = selector.strip("[]")
        if f"{attr}=" not in markup:
            problems.append(f"BINDING_SELECTOR_MISSING:{selector}")
    catalog_tag = (re.search(r'<[a-z]+[^>]*\bid="catalog"[^>]*>', markup) or [""])[0]
    for feature, needs in OPT_IN.items():
        if re.search(r"\b" + feature + r"\b", catalog_tag):
            for element_id in needs["ids"]:
                count = len(re.findall(r'id="' + re.escape(element_id) + '"', markup))
                if count != 1:
                    problems.append(f"OPT_IN_ID_COUNT:{feature}:{element_id}:{count}")
            for selector in needs["selectors"]:
                if selector.strip("[]") + "=" not in markup:
                    problems.append(f"OPT_IN_SELECTOR_MISSING:{feature}:{selector}")
    css = "\n".join([*pack["base_css"], pack["grammar_css"], extra_css])
    allowed = set(pack["manifest"].get("hex_allowlist", {}))
    for literal in sorted(set(re.findall(r"#[0-9a-fA-F]{3,8}\b", css))):
        if literal not in allowed:
            problems.append(f"HEX_LITERAL_NOT_ALLOWED:{literal}")
    for selector, declarations in _css_rules(css):
        for governed in binding["governed_style"]:
            names = GOVERNED_ELEMENTS.get(governed["id"], ("#" + governed["id"],))
            if any(name in selector for name in names):
                css_prop = re.sub(r"([A-Z])", lambda m: "-" + m.group(1).lower(), governed["property"])
                if re.search(re.escape(css_prop) + r"\s*:[^;]*!important", declarations):
                    problems.append(f"GOVERNED_STYLE_OVERRIDDEN:{governed['id']}.{css_prop}")
    if re.search(r"https?://", css + markup):
        problems.append("EXTERNAL_URL")
    return problems


def _font_block(fonts: list[dict[str, Any]]) -> str:
    """One license comment per family, one @font-face per file (variable fonts: one file; static: one per weight)."""
    from mosaic_ui_std.theme_v02 import FONTS_DIR
    out = []
    for font in fonts:
        files = font.get("files") or [{"file": font["file"], "weight": font["weight"]}]
        out.append(f"/* {font['css_family']} (Latin subset, unmodified): {font['notice']}. SIL Open Font License 1.1; "
                   f"license text in {font['license_hint']}. */")
        for item in files:
            data = base64.b64encode((FONTS_DIR / item["file"]).read_bytes()).decode()
            out.append(f"@font-face{{font-family:'{font['css_family']}';font-style:normal;font-display:block;"
                       f"font-weight:{item['weight']};src:url(data:font/woff2;base64,{data}) format('woff2')}}")
    return "\n".join(out)


def sheet_from_theme_v02(theme_id: str) -> dict[str, Any]:
    """Token sheet for the review shell from a v0.2 theme (L2-R2, L2-R3)."""
    from mosaic_ui_std.theme_v02 import THEMES_V02_DIR, load_font_registry, load_theme_v02
    theme = load_theme_v02(THEMES_V02_DIR / f"{theme_id}.json")
    tokens, registry = theme["tokens"], load_font_registry()["fonts"]
    colors, radii, raised = tokens["colors"], tokens["radii"], tokens["elevation"]["raised"]
    sans, mono = tokens["typography"]["roles"]["body"]["font"], tokens["typography"]["roles"]["mono"]["font"]
    fonts = []
    for font_id in dict.fromkeys((sans, mono)):
        entry = registry[font_id]
        notice = _text(Path(__file__).resolve().parents[1] / "mosaic_ui_std" / "fonts" / entry["license_file"]).split("\n", 1)[0].strip()
        notice = re.sub(r"\s*\(https?://[^)]*\)", "", notice)
        fonts.append({"css_family": entry["family"], "font_id": font_id, "notice": notice, "license_hint": "mosaic_ui_std/fonts/",
                      "files": [{"file": item["file"], "weight": item["weight"]} for item in entry["files"]]})
    shadow = f"0 {raised['y']}px {raised['blur']}px rgba(0,0,0,{raised['alpha']})"
    variables = [[name, colors[role]] for name, role in ROLE_VARS]
    variables += [["r-sm", f"{radii['sm']}px"], ["r-md", f"{radii['md']}px"], ["r-lg", f"{radii['lg']}px"]]
    variables += [list(pair) for pair in PACK_SHAPE]
    variables += [["shadow", shadow],
                  ["sans", f"'{registry[sans]['family']}',system-ui,sans-serif"],
                  ["mono", f"'{registry[mono]['family']}',ui-monospace,monospace"]]
    motion = tokens["motion"]
    reduced = "@media (prefers-reduced-motion:reduce){*,*::before,*::after{transition:none!important;animation:none!important}}"
    return {"schema": "mosaic.ui.review-token-sheet.v0.1", "scheme": theme["scheme"],
            "header": (f"/* Mosaic review shell tokens, generated from theme schema v0.2 '{theme_id}' "
                       f"(motion {motion['short_ms']}ms; reduced motion: {motion['reduced_motion']}). Do not edit by hand. */"),
            "vars": variables, "fonts": fonts, "extra_css": [reduced]}


def assemble_with_sheet(pack_id: str, sheet: dict[str, Any], *, extra_css: str = "", packs_dir: Path = PACKS_DIR) -> str:
    pack = load_pack(pack_id, packs_dir)
    tokens = ":root{" + ";".join(f"--{name}:{value}" for name, value in sheet["vars"]) + "}"
    base = [css.replace("__SCHEME__", sheet["scheme"]) for css in pack["base_css"]]
    parts = [_font_block(sheet["fonts"]), sheet["header"], tokens, *base, pack["grammar_css"], *sheet["extra_css"]]
    if extra_css:
        parts.append(extra_css)
    head, script = _text(packs_dir / "_shell" / "head.html"), shell_script(packs_dir)
    return head + "<style>\n" + "\n".join(parts) + "\n</style></head>" + pack["body"] + script


def assemble(pack_id: str, theme_id: str) -> str:
    problems = validate_pack(pack_id)
    if problems:
        raise UIRefusal("REVIEW_PACK_REFUSED", ";".join(problems))
    return assemble_with_sheet(pack_id, sheet_from_theme_v02(theme_id))


def list_packs() -> list[str]:
    return sorted(p.name for p in PACKS_DIR.iterdir() if p.is_dir() and not p.name.startswith("_"))


def dumps_binding(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"

"""Deterministic human projections of authoritative JSON records.

Pretty views are disposable projections.  The JSON record and its root remain
the authority-bearing evidence subject.
"""
from __future__ import annotations

from typing import Any

from uclop.canonical import require, root

from .system import BOUNDARY


def _short(value: Any) -> str:
    if type(value) is str and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value):
        return value[:12] + "…"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    return str(value)


def pretty_record(value: Any, *, title: str = "UCM record") -> dict[str, Any]:
    require(type(value) is dict, "UCM_PRETTY_RECORD_INVALID")
    require(type(title) is str and title.strip(), "UCM_PRETTY_TITLE_INVALID")
    sections = []
    preferred = ("schema", "status", "standing", "authority_effect", "real_a5", "g0")
    identity = [{"field": key, "value": _short(value[key])} for key in preferred if key in value]
    if identity:
        sections.append({"heading": "Identity and status", "rows": identity})
    roots = [{"field": key, "value": _short(item), "full_value": item}
             for key, item in sorted(value.items())
             if (key.endswith("_root") or key in {"root", "head"}) and type(item) is str]
    if roots:
        sections.append({"heading": "Roots", "rows": roots})
    counts = [{"field": key, "value": _short(item)}
              for key, item in sorted(value.items())
              if type(item) is int and type(item) is not bool]
    if counts:
        sections.append({"heading": "Counts", "rows": counts})
    lines = [title, "=" * len(title), "Projection only; verify the canonical JSON record."]
    for section in sections:
        lines.extend(["", section["heading"]])
        lines.extend(f"- {row['field']}: {row['value']}" for row in section["rows"])
    body = {
        "schema": "mosaic.ucm.pretty-record-projection.v0.1",
        "subject_root": root(value), "title": title,
        "sections": sections, "text": "\n".join(lines) + "\n",
        "non_claims": ["NOT_ALTERNATE_AUTHORITY", "NOT_SOURCE_EVIDENCE"],
        **BOUNDARY,
    }
    return {**body, "projection_root": root(body)}

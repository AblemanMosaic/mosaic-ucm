"""Inert, source-preserving document model for Mosaic Reader.

The importers in this module recognize a deliberately bounded text, Markdown,
and HTML subset. They never execute document content, load assets, open links,
or mutate files. Links and assets are retained only as host-admission requests.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from html.parser import HTMLParser
import json
import re
from typing import Any
from urllib.parse import urlparse


DOCUMENT_FORMATS = frozenset({"PLAIN_TEXT", "MARKDOWN", "HTML_SUBSET"})
BLOCK_KINDS = frozenset({
    "PARAGRAPH", "HEADING", "LIST_ITEM", "QUOTE", "CODE_BLOCK", "RULE",
})
MARK_KINDS = frozenset({"STRONG", "EMPHASIS", "UNDERLINE", "CODE", "LINK"})
SUPPORTED_HTML_TAGS = frozenset({
    "a", "b", "blockquote", "br", "code", "div", "em", "h1", "h2", "h3",
    "h4", "h5", "h6", "hr", "i", "img", "li", "ol", "p", "pre", "span",
    "strong", "sub", "sup", "u", "ul",
})
SKIPPED_HTML_CONTENT = frozenset({"script", "style"})
HOST_ADMITTED_SCHEMES = frozenset({"http", "https", "mailto", "doi"})
REFUSED_SCHEMES = frozenset({"javascript", "data", "vbscript"})


class DocumentRefusal(ValueError):
    """Stable refusal from a bounded document importer."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}:{detail}" if detail else code)


@dataclass(frozen=True)
class DocumentMark:
    start: int
    end: int
    kind: str
    value: str | None = None


@dataclass(frozen=True)
class DocumentReference:
    reference_id: str
    role: str
    label: str
    target: str
    disposition: str


@dataclass(frozen=True)
class DocumentBlock:
    block_id: str
    kind: str
    text: str
    level: int | None = None
    marks: tuple[DocumentMark, ...] = ()
    references: tuple[DocumentReference, ...] = ()


@dataclass(frozen=True)
class DocumentIR:
    source: str
    source_format: str
    source_root: str
    document_root: str
    blocks: tuple[DocumentBlock, ...]
    diagnostics: tuple[str, ...]
    unsupported_markup: tuple[str, ...]
    skipped_content: tuple[str, ...]
    authority_effect: str = "NONE"
    execution_authority: bool = False
    network_requests: tuple[str, ...] = ()

    @property
    def plain_text(self) -> str:
        return "\n\n".join(block.text for block in self.blocks if block.kind != "RULE")

    def as_dict(self, *, include_source: bool = True) -> dict[str, Any]:
        value = asdict(self)
        if not include_source:
            value.pop("source", None)
        return value


@dataclass(frozen=True)
class DocumentLimits:
    max_source_chars: int = 2_000_000
    max_blocks: int = 10_000
    max_references: int = 5_000
    max_marks: int = 50_000
    max_inline_nesting: int = 128


def _validate_limits(limits: DocumentLimits) -> None:
    for name in (
        "max_source_chars", "max_blocks", "max_references", "max_marks",
        "max_inline_nesting",
    ):
        value = getattr(limits, name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise DocumentRefusal("DOCUMENT_LIMIT_PROFILE_REFUSED", f"{name}:{value}")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _root(value: Any) -> str:
    return sha256(_canonical_bytes(value)).hexdigest()


def _block_id(index: int, kind: str, level: int | None, text: str) -> str:
    return "block:" + _root({
        "index": index, "kind": kind, "level": level, "text": text,
    })[:24]


def classify_reference(target: str) -> str:
    """Classify a target without resolving, fetching, or opening it."""
    value = str(target or "").strip()
    if not value:
        return "EMPTY_REFUSED"
    scheme = urlparse(value).scheme.lower()
    if scheme in REFUSED_SCHEMES:
        return "SCHEME_REFUSED"
    if scheme in HOST_ADMITTED_SCHEMES:
        return "HOST_ADMISSION_REQUIRED"
    if scheme:
        return "UNKNOWN_SCHEME_REFUSED"
    if value.startswith("#"):
        return "DOCUMENT_FRAGMENT"
    return "LOCAL_REFERENCE_ADMISSION_REQUIRED"


def _reference(role: str, label: str, target: str, ordinal: int) -> DocumentReference:
    disposition = classify_reference(target)
    reference_id = "ref:" + _root({
        "role": role, "label": label, "target": target, "ordinal": ordinal,
    })[:24]
    return DocumentReference(reference_id, role, label, target, disposition)


def _finish(
    source: str,
    source_format: str,
    raw_blocks: list[dict[str, Any]],
    diagnostics: set[str] | list[str],
    unsupported: set[str] | list[str] = (),
    skipped: set[str] | list[str] = (),
    *,
    limits: DocumentLimits,
) -> DocumentIR:
    if len(raw_blocks) > limits.max_blocks:
        raise DocumentRefusal("DOCUMENT_BLOCK_LIMIT_REFUSED", str(len(raw_blocks)))
    reference_count = sum(len(row.get("references", ())) for row in raw_blocks)
    if reference_count > limits.max_references:
        raise DocumentRefusal("DOCUMENT_REFERENCE_LIMIT_REFUSED", str(reference_count))
    mark_count = sum(len(row.get("marks", ())) for row in raw_blocks)
    if mark_count > limits.max_marks:
        raise DocumentRefusal("DOCUMENT_MARK_LIMIT_REFUSED", str(mark_count))
    blocks = tuple(
        DocumentBlock(
            block_id=_block_id(index, row["kind"], row.get("level"), row["text"]),
            kind=row["kind"],
            text=row["text"],
            level=row.get("level"),
            marks=tuple(row.get("marks", ())),
            references=tuple(row.get("references", ())),
        )
        for index, row in enumerate(raw_blocks)
    )
    body = {
        "schema": "mosaic.reader.document-ir.v0.1",
        "source_format": source_format,
        "source_root": sha256(source.encode("utf-8")).hexdigest(),
        "blocks": [asdict(block) for block in blocks],
        "diagnostics": sorted(set(diagnostics)),
        "unsupported_markup": sorted(set(unsupported)),
        "skipped_content": sorted(set(skipped)),
        "authority_effect": "NONE",
        "execution_authority": False,
        "network_requests": [],
    }
    return DocumentIR(
        source=source,
        source_format=source_format,
        source_root=body["source_root"],
        document_root=_root(body),
        blocks=blocks,
        diagnostics=tuple(body["diagnostics"]),
        unsupported_markup=tuple(body["unsupported_markup"]),
        skipped_content=tuple(body["skipped_content"]),
    )


def _bounded_source(source: str | None, limits: DocumentLimits) -> str:
    _validate_limits(limits)
    value = str(source or "")
    if len(value) > limits.max_source_chars:
        raise DocumentRefusal("DOCUMENT_SOURCE_SIZE_REFUSED", str(len(value)))
    return value


def import_plain_text(source: str | None, *, limits: DocumentLimits = DocumentLimits()) -> DocumentIR:
    raw = _bounded_source(source, limits)
    blocks = []
    for paragraph in re.split(r"(?:\r?\n){2,}", raw):
        text = paragraph.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
        if text:
            blocks.append({"kind": "PARAGRAPH", "text": text})
    return _finish(raw, "PLAIN_TEXT", blocks, set(), limits=limits)


_INLINE_TOKEN = re.compile(
    r"!\[([^\]]*)\]\(([^)\s]+)\)"
    r"|\[([^\]]+)\]\(([^)\s]+)\)"
    r"|\*\*([^*\n]+)\*\*"
    r"|__([^_\n]+)__"
    r"|`([^`\n]+)`"
    r"|\*([^*\n]+)\*"
    r"|_([^_\n]+)_"
)


def _markdown_inline(value: str) -> tuple[str, list[DocumentMark], list[DocumentReference]]:
    parts: list[str] = []
    marks: list[DocumentMark] = []
    references: list[DocumentReference] = []
    cursor = 0
    for match in _INLINE_TOKEN.finditer(value):
        parts.append(value[cursor:match.start()])
        start = sum(len(part) for part in parts)
        groups = match.groups()
        if groups[0] is not None:
            label, target, role, kind = groups[0], groups[1], "IMAGE", "LINK"
        elif groups[2] is not None:
            label, target, role, kind = groups[2], groups[3], "LINK", "LINK"
        elif groups[4] is not None or groups[5] is not None:
            label, target, role, kind = groups[4] or groups[5], None, None, "STRONG"
        elif groups[6] is not None:
            label, target, role, kind = groups[6], None, None, "CODE"
        else:
            label, target, role, kind = groups[7] or groups[8], None, None, "EMPHASIS"
        parts.append(label)
        end = start + len(label)
        marks.append(DocumentMark(start, end, kind, target))
        if target is not None and role is not None:
            references.append(_reference(role, label, target, len(references)))
        cursor = match.end()
    parts.append(value[cursor:])
    return "".join(parts), marks, references


def import_markdown(source: str | None, *, limits: DocumentLimits = DocumentLimits()) -> DocumentIR:
    raw = _bounded_source(source, limits)
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[dict[str, Any]] = []
    diagnostics: set[str] = set()
    paragraph: list[str] = []
    index = 0

    def append_inline(kind: str, value: str, level: int | None = None) -> None:
        text, marks, references = _markdown_inline(value)
        if sum(len(row.get("marks", ())) for row in blocks) + len(marks) > limits.max_marks:
            raise DocumentRefusal("DOCUMENT_MARK_LIMIT_REFUSED", str(limits.max_marks))
        if sum(len(row.get("references", ())) for row in blocks) + len(references) > limits.max_references:
            raise DocumentRefusal("DOCUMENT_REFERENCE_LIMIT_REFUSED", str(limits.max_references))
        blocks.append({
            "kind": kind, "text": text, "level": level,
            "marks": marks, "references": references,
        })

    def flush_paragraph() -> None:
        if paragraph:
            append_inline("PARAGRAPH", "\n".join(paragraph).strip())
            paragraph.clear()

    while index < len(lines):
        line = lines[index]
        if line.startswith("```") or line.startswith("~~~"):
            flush_paragraph()
            fence = line[:3]
            language = line[3:].strip()
            index += 1
            code: list[str] = []
            while index < len(lines) and not lines[index].startswith(fence):
                code.append(lines[index])
                index += 1
            if index >= len(lines):
                diagnostics.add("MARKDOWN_UNCLOSED_FENCE")
            else:
                index += 1
            blocks.append({
                "kind": "CODE_BLOCK", "text": "\n".join(code),
                "level": None,
                "marks": ([DocumentMark(0, len("\n".join(code)), "CODE", language)]
                          if code else []),
                "references": [],
            })
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*$", line)
        list_item = re.match(r"^\s*(?:[-+*]|(\d+)\.)\s+(.+)$", line)
        quote = re.match(r"^\s*>\s?(.*)$", line)
        if heading:
            flush_paragraph()
            append_inline("HEADING", heading.group(2), len(heading.group(1)))
        elif re.match(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$", line):
            flush_paragraph()
            blocks.append({"kind": "RULE", "text": ""})
        elif list_item:
            flush_paragraph()
            append_inline("LIST_ITEM", list_item.group(2), 1)
        elif quote:
            flush_paragraph()
            append_inline("QUOTE", quote.group(1), 1)
        elif not line.strip():
            flush_paragraph()
        else:
            paragraph.append(line)
        index += 1
    flush_paragraph()
    return _finish(raw, "MARKDOWN", blocks, diagnostics, limits=limits)


class _HTMLDocumentParser(HTMLParser):
    def __init__(self, limits: DocumentLimits) -> None:
        super().__init__(convert_charrefs=True)
        self.limits = limits
        self.blocks: list[dict[str, Any]] = []
        self.unsupported: set[str] = set()
        self.skipped: set[str] = set()
        self.diagnostics: set[str] = set()
        self.skip_depth = 0
        self.current_kind: str | None = None
        self.current_level: int | None = None
        self.parts: list[str] = []
        self.marks: list[DocumentMark] = []
        self.references: list[DocumentReference] = []
        self.active_marks: list[tuple[str, str | None]] = []
        self.pre_depth = 0

    def _push_mark(self, kind: str, target: str | None = None) -> None:
        if len(self.active_marks) >= self.limits.max_inline_nesting:
            raise DocumentRefusal(
                "DOCUMENT_INLINE_NESTING_REFUSED", str(len(self.active_marks) + 1),
            )
        self.active_marks.append((kind, target))

    @property
    def text(self) -> str:
        return "".join(self.parts)

    def _start_block(self, kind: str, level: int | None = None) -> None:
        self._flush()
        self.current_kind = kind
        self.current_level = level

    def _ensure_block(self) -> None:
        if self.current_kind is None:
            self.current_kind = "PARAGRAPH"

    def _append(self, value: str) -> None:
        if not value:
            return
        self._ensure_block()
        if not self.pre_depth:
            value = re.sub(r"\s+", " ", value)
            if not self.text or self.text.endswith((" ", "\n")):
                value = value.lstrip()
        if not value:
            return
        start = len(self.text)
        self.parts.append(value)
        end = start + len(value)
        if len(self.marks) + len(self.active_marks) > self.limits.max_marks:
            raise DocumentRefusal("DOCUMENT_MARK_LIMIT_REFUSED", str(self.limits.max_marks))
        for kind, target in self.active_marks:
            self.marks.append(DocumentMark(start, end, kind, target))

    def _flush(self) -> None:
        if self.current_kind is None:
            return
        text = self.text if self.current_kind == "CODE_BLOCK" else self.text.strip()
        if text or self.current_kind == "RULE":
            self.blocks.append({
                "kind": self.current_kind,
                "text": text,
                "level": self.current_level,
                "marks": list(self.marks),
                "references": list(self.references),
            })
        self.current_kind = None
        self.current_level = None
        self.parts.clear()
        self.marks.clear()
        self.references.clear()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in SKIPPED_HTML_CONTENT:
            self.skipped.add(tag)
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag not in SUPPORTED_HTML_TAGS:
            self.unsupported.add(tag)
            return
        values = dict(attrs)
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._start_block("HEADING", int(tag[1]))
            self._push_mark("STRONG")
        elif tag in {"p", "div"}:
            self._start_block("PARAGRAPH")
        elif tag == "blockquote":
            self._start_block("QUOTE", 1)
        elif tag == "li":
            self._start_block("LIST_ITEM", 1)
        elif tag == "pre":
            self._start_block("CODE_BLOCK")
            self.pre_depth += 1
            self._push_mark("CODE")
        elif tag == "hr":
            self._start_block("RULE")
            self._flush()
        elif tag == "br":
            self._append("\n")
        elif tag in {"b", "strong"}:
            self._push_mark("STRONG")
        elif tag in {"i", "em"}:
            self._push_mark("EMPHASIS")
        elif tag == "u":
            self._push_mark("UNDERLINE")
        elif tag == "code":
            self._push_mark("CODE")
        elif tag == "a":
            target = values.get("href") or ""
            self._push_mark("LINK", target)
        elif tag == "img":
            label = values.get("alt") or "Image"
            target = values.get("src") or ""
            start = len(self.text)
            self._append(label)
            end = len(self.text)
            self.marks.append(DocumentMark(start, end, "LINK", target))
            self.references.append(_reference("IMAGE", label, target, len(self.references)))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in SKIPPED_HTML_CONTENT:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth or tag not in SUPPORTED_HTML_TAGS:
            return
        mark = None
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6", "b", "strong"}:
            mark = "STRONG"
        elif tag in {"i", "em"}:
            mark = "EMPHASIS"
        elif tag == "u":
            mark = "UNDERLINE"
        elif tag in {"code", "pre"}:
            mark = "CODE"
        elif tag == "a":
            mark = "LINK"
            target = next((value for kind, value in reversed(self.active_marks)
                           if kind == "LINK"), "") or ""
            link_marks = [
                item for item in self.marks
                if item.kind == "LINK" and item.value == target
            ]
            label = self.text[
                min((item.start for item in link_marks), default=len(self.text)):
                max((item.end for item in link_marks), default=len(self.text))
            ]
            self.references.append(_reference("LINK", label, target, len(self.references)))
        if mark is not None:
            for index in range(len(self.active_marks) - 1, -1, -1):
                if self.active_marks[index][0] == mark:
                    self.active_marks.pop(index)
                    break
        if tag == "pre":
            self.pre_depth = max(0, self.pre_depth - 1)
        if tag in {"p", "div", "blockquote", "li", "pre", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._flush()

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self._append(data)

    def close(self) -> None:
        super().close()
        if self.skip_depth:
            self.diagnostics.add("HTML_UNCLOSED_SKIPPED_CONTENT")
        self._flush()


def import_html_subset(source: str | None, *, limits: DocumentLimits = DocumentLimits()) -> DocumentIR:
    raw = _bounded_source(source, limits)
    parser = _HTMLDocumentParser(limits)
    parser.feed(raw)
    parser.close()
    return _finish(
        raw, "HTML_SUBSET", parser.blocks, parser.diagnostics,
        parser.unsupported, parser.skipped, limits=limits,
    )


def import_document(
    source: str | None,
    source_format: str,
    *,
    limits: DocumentLimits = DocumentLimits(),
) -> DocumentIR:
    if source_format not in DOCUMENT_FORMATS:
        raise DocumentRefusal("DOCUMENT_FORMAT_REFUSED", str(source_format))
    if source_format == "PLAIN_TEXT":
        return import_plain_text(source, limits=limits)
    if source_format == "MARKDOWN":
        return import_markdown(source, limits=limits)
    return import_html_subset(source, limits=limits)


__all__ = [
    "BLOCK_KINDS", "DOCUMENT_FORMATS", "HOST_ADMITTED_SCHEMES", "MARK_KINDS",
    "DocumentBlock", "DocumentIR", "DocumentLimits", "DocumentMark",
    "DocumentReference", "DocumentRefusal", "classify_reference", "import_document",
    "import_html_subset", "import_markdown", "import_plain_text",
]

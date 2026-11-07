"""Compatibility projection over Mosaic Reader's inert document IR.

The exact source remains the semantic value. Parsing is delegated to bounded
document importers; this adapter derives only display text and native character
spans. It does not execute content, fetch references, or admit navigation.
"""
from __future__ import annotations

from dataclasses import dataclass

from .document_model import (
    DOCUMENT_FORMATS,
    HOST_ADMITTED_SCHEMES,
    SKIPPED_HTML_CONTENT,
    SUPPORTED_HTML_TAGS,
    DocumentIR,
    DocumentReference,
    import_document,
)


SUPPORTED_TAGS = SUPPORTED_HTML_TAGS
SKIPPED_CONTENT_TAGS = SKIPPED_HTML_CONTENT
LINK_SCHEMES = HOST_ADMITTED_SCHEMES


@dataclass(frozen=True)
class RichSpan:
    start: int
    end: int
    bold: bool = False
    italic: bool = False
    underline: bool = False
    code: bool = False
    superscript: bool = False
    subscript: bool = False
    link: bool = False


@dataclass(frozen=True)
class RichDocumentProjection:
    source: str
    format: str
    plain_text: str
    spans: tuple[RichSpan, ...]
    links: tuple[str, ...]
    unsupported_tags: tuple[str, ...]
    skipped_content_tags: tuple[str, ...]
    source_root: str = ""
    document_root: str = ""
    references: tuple[DocumentReference, ...] = ()
    authority_effect: str = "NONE"
    execution_authority: bool = False
    network_requests: tuple[str, ...] = ()

    @property
    def lossless_source_preserved(self) -> bool:
        return True


def _append_block(parts: list[str], spans: list[RichSpan], block) -> None:
    if parts:
        parts.append("\n\n")
    prefix = ""
    text = block.text
    if block.kind == "LIST_ITEM":
        prefix = "- "
    elif block.kind == "QUOTE":
        prefix = "> "
    elif block.kind == "RULE":
        text = "---"
    start = sum(len(part) for part in parts) + len(prefix)
    parts.extend((prefix, text))
    end = start + len(text)
    if block.kind == "HEADING" and end > start:
        spans.append(RichSpan(start, end, bold=True))
    elif block.kind == "CODE_BLOCK" and end > start:
        spans.append(RichSpan(start, end, code=True))
    for mark in block.marks:
        mark_start = start + max(0, mark.start)
        mark_end = start + min(len(text), mark.end)
        if mark_end <= mark_start:
            continue
        spans.append(RichSpan(
            mark_start,
            mark_end,
            bold=mark.kind == "STRONG",
            italic=mark.kind == "EMPHASIS",
            underline=mark.kind in {"UNDERLINE", "LINK"},
            code=mark.kind == "CODE",
            link=mark.kind == "LINK",
        ))


def project_document_ir(document: DocumentIR) -> RichDocumentProjection:
    """Derive a display-only compatibility projection from canonical IR."""
    parts: list[str] = []
    spans: list[RichSpan] = []
    references: list[DocumentReference] = []
    for block in document.blocks:
        _append_block(parts, spans, block)
        references.extend(block.references)
    links = tuple(dict.fromkeys(
        reference.target for reference in references
        if reference.role == "LINK" and reference.disposition == "HOST_ADMISSION_REQUIRED"
    ))
    return RichDocumentProjection(
        source=document.source,
        format=document.source_format,
        plain_text="".join(parts),
        spans=tuple(spans),
        links=links,
        unsupported_tags=document.unsupported_markup,
        skipped_content_tags=document.skipped_content,
        source_root=document.source_root,
        document_root=document.document_root,
        references=tuple(references),
        authority_effect=document.authority_effect,
        execution_authority=document.execution_authority,
        network_requests=document.network_requests,
    )


def project_rich_document(
    source: str | None, format: str = "HTML_SUBSET",
) -> RichDocumentProjection:
    if format not in DOCUMENT_FORMATS:
        raise ValueError(f"RICH_DOCUMENT_FORMAT_INVALID:{format}")
    return project_document_ir(import_document(source, format))


__all__ = [
    "LINK_SCHEMES", "RichDocumentProjection", "RichSpan", "SKIPPED_CONTENT_TAGS",
    "SUPPORTED_TAGS", "project_document_ir", "project_rich_document",
]

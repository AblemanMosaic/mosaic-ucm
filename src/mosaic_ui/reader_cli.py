"""Installed command-line and native-window entry point for Mosaic Reader."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from typing import Iterable

from .canonical import atomic_write, canonical_bytes
from .reader_app import create_native_reader
from .reader_evidence import build_reader_evidence
from .reader_pipeline import compile_reader


MOSAIC_READER_VERSION = "0.1.0rc1"
FORMAT_SUFFIXES = {
    ".txt": "PLAIN_TEXT",
    ".md": "MARKDOWN",
    ".markdown": "MARKDOWN",
    ".html": "HTML_SUBSET",
    ".htm": "HTML_SUBSET",
}
MAX_SOURCE_BYTES = 8_000_000


class ReaderCLIRefusal(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}:{detail}" if detail else code)


def _read_source(path: Path, requested_format: str) -> tuple[str, str, str]:
    target = path.resolve()
    if path.is_symlink() or not target.is_file():
        raise ReaderCLIRefusal("READER_SOURCE_FILE_REFUSED", str(path))
    data = target.read_bytes()
    if len(data) > MAX_SOURCE_BYTES:
        raise ReaderCLIRefusal("READER_SOURCE_FILE_SIZE_REFUSED", str(len(data)))
    try:
        source = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ReaderCLIRefusal("READER_SOURCE_ENCODING_REFUSED", "UTF-8_REQUIRED") from exc
    source_format = requested_format
    if source_format == "AUTO":
        source_format = FORMAT_SUFFIXES.get(target.suffix.lower(), "")
        if not source_format:
            raise ReaderCLIRefusal("READER_SOURCE_FORMAT_REFUSED", target.suffix.lower())
    return source, source_format, sha256(data).hexdigest()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mosaic-reader",
        description="Open an explicit UTF-8 TXT, Markdown, or restricted-HTML source.",
    )
    parser.add_argument("source", type=Path)
    parser.add_argument(
        "--format",
        choices=("AUTO", "PLAIN_TEXT", "MARKDOWN", "HTML_SUBSET"),
        default="AUTO",
    )
    parser.add_argument("--realizer", choices=("HEADLESS", "WIN32"), default="WIN32")
    parser.add_argument("--title")
    parser.add_argument("--output", type=Path, help="Optional path for the JSON witness.")
    parser.add_argument("--version", action="version", version=f"Mosaic Reader {MOSAIC_READER_VERSION}")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        source, source_format, file_root = _read_source(args.source, args.format)
        title = args.title or args.source.name
        compiled = compile_reader(source, source_format, target=args.realizer, title=title)
        native_descriptor = None
        if args.realizer == "WIN32":
            if os.name != "nt":
                raise ReaderCLIRefusal("READER_WIN32_HOST_REFUSED", os.name)
            native = create_native_reader(source, source_format, title=title)
            exit_code = native.run()
            if exit_code != 0 or native.window.callback_errors:
                raise ReaderCLIRefusal("READER_NATIVE_RUN_REFUSED", str(exit_code))
            native_descriptor = native.witness_descriptor()
        witness = build_reader_evidence(compiled, native_descriptor=native_descriptor)
        result = {
            "schema": "mosaic.reader.cold-boot-result.v0.1",
            "reader_version": MOSAIC_READER_VERSION,
            "source_file_sha256": file_root,
            "source_format": source_format,
            "realizer": args.realizer,
            "witness": witness,
            "status": "PASS_LOCAL_CANDIDATE",
            "authority_effect": "NONE",
        }
        data = canonical_bytes(result) + b"\n"
        if args.output is not None:
            atomic_write(args.output.resolve(), data)
        sys.stdout.write(data.decode("utf-8"))
        return 0
    except (OSError, ValueError) as exc:
        code = getattr(exc, "code", "READER_COLD_BOOT_REFUSED")
        detail = getattr(exc, "detail", str(exc))
        error = {
            "schema": "mosaic.reader.cold-boot-refusal.v0.1",
            "code": code,
            "detail": detail,
            "status": "REFUSED",
            "authority_effect": "NONE",
        }
        print(json.dumps(error, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

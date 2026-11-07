"""Deterministic hostile-input containment probe for Mosaic Reader."""
from __future__ import annotations

from hashlib import sha256
import random
import string

from .canonical import commitment
from .document_model import DocumentLimits, DocumentRefusal, import_document


HOSTILE_CASES = (
    ("HTML_SUBSET", "<script>run()</script><p>safe</p>"),
    ("HTML_SUBSET", "<style>@import url(https://bad.test/x)</style><p>safe</p>"),
    ("HTML_SUBSET", "<img src='https://bad.test/x' onerror='run()'>"),
    ("HTML_SUBSET", "<iframe src='https://bad.test/'></iframe><p>visible</p>"),
    ("HTML_SUBSET", "<svg><script>run()</script></svg><p>visible</p>"),
    ("HTML_SUBSET", "<object data='data:text/html,bad'></object>"),
    ("MARKDOWN", "[bad](javascript:alert(1)) [data](data:text/html,bad)"),
    ("MARKDOWN", "![remote](https://bad.test/image.png)"),
    ("MARKDOWN", "```html\n<script>text only</script>\n```"),
    ("PLAIN_TEXT", "<script>plain text only</script>\x00end"),
)


def run_security_probe(*, seed: int = 8675309, fuzz_cases: int = 128) -> dict:
    if isinstance(fuzz_cases, bool) or not isinstance(fuzz_cases, int) or not 1 <= fuzz_cases <= 10_000:
        raise DocumentRefusal("SECURITY_FUZZ_CASE_COUNT_REFUSED", str(fuzz_cases))
    rows = []
    for source_format, source in HOSTILE_CASES:
        document = import_document(source, source_format)
        if document.execution_authority or document.network_requests:
            raise DocumentRefusal("SECURITY_CONTAINMENT_REFUSED", source_format)
        rows.append({
            "format": source_format,
            "case_root": sha256(source.encode("utf-8")).hexdigest(),
            "document_root": document.document_root,
            "unsupported_markup": list(document.unsupported_markup),
            "skipped_content": list(document.skipped_content),
            "reference_dispositions": sorted({
                reference.disposition
                for block in document.blocks
                for reference in block.references
            }),
        })
    rng = random.Random(seed)
    alphabet = string.ascii_letters + string.digits + "<>[]()/*_`'\"&;:\\ \n\t\x00"
    fuzz_roots = []
    for index in range(fuzz_cases):
        length = rng.randint(0, 512)
        source = "".join(rng.choice(alphabet) for _ in range(length))
        source_format = ("PLAIN_TEXT", "MARKDOWN", "HTML_SUBSET")[index % 3]
        document = import_document(
            source,
            source_format,
            limits=DocumentLimits(
                max_source_chars=1024,
                max_blocks=256,
                max_references=128,
                max_marks=2048,
                max_inline_nesting=32,
            ),
        )
        if document.execution_authority or document.network_requests:
            raise DocumentRefusal("SECURITY_CONTAINMENT_REFUSED", f"FUZZ:{index}")
        fuzz_roots.append(document.document_root)

    negative_controls = []
    controls = (
        ("SOURCE", lambda: import_document("xxxx", "PLAIN_TEXT", limits=DocumentLimits(max_source_chars=3))),
        ("BLOCKS", lambda: import_document("a\n\nb", "PLAIN_TEXT", limits=DocumentLimits(max_blocks=1))),
        ("REFERENCES", lambda: import_document(
            "[a](https://a.test) [b](https://b.test)", "MARKDOWN",
            limits=DocumentLimits(max_references=1),
        )),
        ("MARKS", lambda: import_document(
            "**a** **b**", "MARKDOWN", limits=DocumentLimits(max_marks=1),
        )),
        ("NESTING", lambda: import_document(
            "<b><i><u>x</u></i></b>", "HTML_SUBSET",
            limits=DocumentLimits(max_inline_nesting=2),
        )),
    )
    for name, operation in controls:
        try:
            operation()
        except DocumentRefusal as exc:
            negative_controls.append({"control": name, "refusal_code": exc.code})
        else:
            raise DocumentRefusal("SECURITY_NEGATIVE_CONTROL_FAILED", name)
    witness = {
        "schema": "mosaic.reader.security-probe.v0.1",
        "seed": seed,
        "hostile_case_count": len(rows),
        "hostile_cases": rows,
        "fuzz_case_count": fuzz_cases,
        "fuzz_roots_commitment": commitment("MOSAIC.READER.FUZZ_ROOTS.v0.1", fuzz_roots),
        "negative_controls": negative_controls,
        "network_request_count": 0,
        "execution_authority": False,
        "authority_effect": "NONE",
        "claim_boundary": (
            "DETERMINISTIC LOCAL CORPUS AND SEEDED MALFORMED-INPUT PROBE; NOT AN "
            "INDEPENDENT SECURITY CERTIFICATION OR PROOF OF ABSENCE OF ALL DEFECTS"
        ),
    }
    witness["witness_root"] = commitment("MOSAIC.READER.SECURITY_PROBE.v0.1", witness)
    return witness


__all__ = ["HOSTILE_CASES", "run_security_probe"]

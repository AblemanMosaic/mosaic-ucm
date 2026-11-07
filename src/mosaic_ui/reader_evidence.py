"""Chained parse/compile/realize/display evidence for Mosaic Reader."""
from __future__ import annotations

import copy
from hashlib import sha256
from typing import Any

from mosaic_ui_std.catalog import load_rich_document_catalog

from .canonical import commitment
from .headless import HeadlessUI
from .reader_app import reader_layout
from .reader_pipeline import CompiledReader, validate_compiled_reader
from .rich_document import project_rich_document


class EvidenceRefusal(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}:{detail}" if detail else code)


def _verify_native_descriptor(descriptor: dict[str, Any], input_root: str) -> dict[str, Any]:
    if not isinstance(descriptor, dict):
        raise EvidenceRefusal("READER_NATIVE_EVIDENCE_REFUSED", "SHAPE")
    if descriptor.get("schema") != "mosaic.ui.native-semantic-realization.v0.1":
        raise EvidenceRefusal("READER_NATIVE_EVIDENCE_REFUSED", "SCHEMA")
    if descriptor.get("generated_root") != input_root:
        raise EvidenceRefusal("READER_NATIVE_EVIDENCE_REFUSED", "INPUT_ROOT")
    if descriptor.get("authority_effect") != "NONE":
        raise EvidenceRefusal("READER_NATIVE_EVIDENCE_REFUSED", "AUTHORITY")
    if "reader.document" not in descriptor.get("realized_keys", []):
        raise EvidenceRefusal("READER_NATIVE_EVIDENCE_REFUSED", "DOCUMENT_CONTROL")
    body = copy.deepcopy(descriptor)
    claimed = body.pop("commitment", None)
    expected = commitment("MOSAIC.UI.NATIVE_SEMANTIC_REALIZATION.v0.1", body)
    if claimed != expected:
        raise EvidenceRefusal("READER_NATIVE_EVIDENCE_REFUSED", "COMMITMENT")
    return {
        "descriptor_commitment": claimed,
        "correspondence_commitment": descriptor["correspondence_commitment"],
        "state_commitment": descriptor["state_commitment"],
        "claim_boundary": descriptor["claim_boundary"],
    }


def build_reader_evidence(
    compiled: CompiledReader,
    *,
    width: int = 960,
    height: int = 720,
    native_descriptor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validation = validate_compiled_reader(compiled)
    target = compiled.plan["realization"]["target"]
    if target == "HEADLESS" and native_descriptor is not None:
        raise EvidenceRefusal("READER_NATIVE_EVIDENCE_REFUSED", "UNEXPECTED_FOR_HEADLESS")
    native = None
    if target == "WIN32":
        if native_descriptor is None:
            raise EvidenceRefusal("READER_NATIVE_EVIDENCE_REQUIRED", "WIN32")
        native = _verify_native_descriptor(native_descriptor, compiled.payload["input_root"])
    runtime = HeadlessUI(
        compiled.payload,
        reader_layout,
        catalog=load_rich_document_catalog(),
    )
    projection = runtime.project(width, height).as_dict()
    expected = project_rich_document(
        compiled.document.source,
        compiled.document.source_format,
    )
    accessibility_row = next((
        row for row in projection["accessibility"]["nodes"]
        if row["node_id"] == "reader.document"
    ), None)
    draw_row = next((
        row for row in projection["draw_stream"]["commands"]
        if row.get("node_id") == "reader.document" and row.get("op") == "TEXT"
    ), None)
    state_source = runtime.state["values"].get("reader.document")
    failures = []
    if state_source != compiled.document.source:
        failures.append("STATE_SOURCE_CUSTODY")
    if accessibility_row is None or accessibility_row.get("value") != expected.plain_text:
        failures.append("ACCESSIBILITY_TEXT")
    if draw_row is None or draw_row.get("text") != expected.plain_text:
        failures.append("DRAW_TEXT")
    if failures:
        raise EvidenceRefusal("READER_DISPLAY_FIDELITY_REFUSED", ",".join(failures))

    receipts = []
    previous = "GENESIS"

    def append(stage: str, detail: dict[str, Any]) -> None:
        nonlocal previous
        value = {
            "schema": "mosaic.reader.pipeline-receipt.v0.1",
            "sequence": len(receipts) + 1,
            "stage": stage,
            "detail": detail,
            "previous_receipt_root": previous,
            "authority_effect": "NONE",
            "external_effect_executed": False,
        }
        value["receipt_root"] = commitment("MOSAIC.READER.PIPELINE_RECEIPT.v0.1", value)
        previous = value["receipt_root"]
        receipts.append(value)

    append("IMPORT", {
        "source_root": compiled.document.source_root,
        "document_root": compiled.document.document_root,
        "format": compiled.document.source_format,
        "block_count": len(compiled.document.blocks),
        "reference_count": sum(len(block.references) for block in compiled.document.blocks),
        "unsupported_markup": list(compiled.document.unsupported_markup),
        "skipped_content": list(compiled.document.skipped_content),
    })
    append("COMPILE", {
        "plan_root": compiled.plan["plan_root"],
        "payload_root": compiled.plan["realization"]["payload_root"],
        "contract_root": compiled.plan["realization"]["contract_root"],
        "configuration_root": compiled.plan["realization"]["configuration_root"],
        "target": target,
    })
    append("REALIZE", {
        "target": target,
        "geometry_root": projection["geometry"]["commitment"],
        "accessibility_root": projection["accessibility"]["commitment"],
        "draw_root": projection["draw_stream"]["commitment"],
        "native": native,
    })
    display_root = sha256(expected.plain_text.encode("utf-8")).hexdigest()
    append("DISPLAY", {
        "display_text_root": display_root,
        "state_source_exact": True,
        "accessibility_text_matches": True,
        "draw_text_matches": True,
        "lossless_source_preserved": expected.lossless_source_preserved,
        "network_request_count": len(expected.network_requests),
        "execution_authority": expected.execution_authority,
    })
    witness = {
        "schema": "mosaic.reader.state-display-fidelity.v0.1",
        "validation": validation,
        "target": target,
        "viewport": {"width": width, "height": height},
        "receipts": receipts,
        "terminal_receipt_root": receipts[-1]["receipt_root"],
        "display_text_root": display_root,
        "native": native,
        "authority_effect": "NONE",
        "external_effect_executed": False,
        "claim_boundary": (
            "STATE_TO_DISPLAY_TEXT_AND_DECLARATIVE_CORRESPONDENCE ONLY; DOES NOT "
            "PROVE PIXEL IDENTITY, COMPLETE ASSISTIVE-TECHNOLOGY BEHAVIOR, OR HOST EFFECTS"
        ),
    }
    witness["witness_root"] = commitment("MOSAIC.READER.STATE_DISPLAY_FIDELITY.v0.1", witness)
    return witness


__all__ = ["EvidenceRefusal", "build_reader_evidence"]

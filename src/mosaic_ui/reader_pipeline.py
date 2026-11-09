"""Deterministic source-to-realization planning for Mosaic Reader.

The plan describes an inert document object, operation boundaries, and one selected
display target. Compiling a plan does not realize UI, open links, edit source, or save.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .canonical import commitment
from .document_model import DocumentIR
from .reader_app import reader_payload
from .realization_space import select_configuration, validate_contract


TARGETS = {
    "HEADLESS": "MOSAIC-UI-HEADLESS-TEXT",
    "WIN32": "MOSAIC-UI-WIN32-RICH-DOCUMENT",
}


class PipelineRefusal(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}:{detail}" if detail else code)


@dataclass(frozen=True)
class CompiledReader:
    plan: dict[str, Any]
    payload: dict[str, Any]
    document: DocumentIR


def _contract() -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "source" / "mosaic-reader-realization-contract-v0.1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def compile_reader(
    source: str | None,
    source_format: str,
    *,
    target: str,
    title: str = "Mosaic Reader",
    configuration: dict[str, Any] | None = None,
) -> CompiledReader:
    normalized_target = str(target).upper()
    if normalized_target not in TARGETS:
        raise PipelineRefusal("READER_PIPELINE_TARGET_REFUSED", normalized_target)
    payload, document = reader_payload(source, source_format, title=title)
    contract = _contract()
    checked = validate_contract(contract)
    requested = dict(configuration or {})
    requested["READER.CONTENT.FORMAT"] = document.source_format
    selected = select_configuration(contract, requested=requested)
    target_id = TARGETS[normalized_target]
    lowering = next(
        (item for item in contract["lowering"]["targets"] if item["target_id"] == target_id),
        None,
    )
    if lowering is None or document.source_format not in lowering["supported_region"]:
        raise PipelineRefusal(
            "READER_PIPELINE_REGION_REFUSED",
            f"{normalized_target}:{document.source_format}",
        )
    object_record = {
        "kind": "INERT_DOCUMENT",
        "source_format": document.source_format,
        "source_root": document.source_root,
        "document_root": document.document_root,
        "block_count": len(document.blocks),
        "reference_count": sum(len(block.references) for block in document.blocks),
        "execution_authority": False,
        "network_requests": [],
    }
    operations = [
        {
            "operation": "DISPLAY_DOCUMENT",
            "effect": "PRESENTATION",
            "owner": "MOSAIC-READER-SHELL",
            "admitted_by_plan": True,
        },
        {
            "operation": "REQUEST_LINK_ADMISSION",
            "effect": "EXTERNAL_NAVIGATION_REQUEST",
            "owner": "MOSAIC-READER-NAVIGATION-GATE",
            "admitted_by_plan": False,
        },
        {
            "operation": "APPLY_SOURCE_EDIT",
            "effect": "LOCAL_BUFFER_MUTATION",
            "owner": "MOSAIC-READER-EDIT-SESSION",
            "admitted_by_plan": False,
        },
        {
            "operation": "COMMIT_SAVE",
            "effect": "LOCAL_FILE_MUTATION",
            "owner": "MOSAIC-READER-SAVE-CUSTODY",
            "admitted_by_plan": False,
        },
    ]
    realization = {
        "target": normalized_target,
        "target_id": target_id,
        "contract_root": checked["contract_root"],
        "configuration_root": selected["configuration_root"],
        "payload_root": commitment("MOSAIC.READER.PAYLOAD.v0.1", payload),
        "required_capabilities": copy.deepcopy(lowering["required_capabilities"]),
        "optional_capabilities": copy.deepcopy(lowering["optional_capabilities"]),
        "preservation_criteria": copy.deepcopy(lowering["preservation_criteria"]),
        "known_losses": copy.deepcopy(lowering["known_losses"]),
    }
    plan = {
        "schema": "mosaic.reader.compilation-plan.v0.1",
        "object": object_record,
        "operations": operations,
        "realization": realization,
        "stages": [
            "IMPORT_INERT_SOURCE",
            "VALIDATE_DOCUMENT_MODEL",
            "SELECT_REALIZATION_CONFIGURATION",
            "LOWER_TO_SEMANTIC_PAYLOAD",
        ],
        "input_root": payload["input_root"],
        "authority_effect": "NONE",
        "external_effect_executed": False,
        "claim_boundary": (
            "DECLARATIVE_PLAN_ONLY; DOES_NOT EXECUTE DOCUMENT CONTENT, REALIZE UI, "
            "ADMIT NAVIGATION, APPLY EDITS, OR COMMIT SAVES"
        ),
    }
    plan["plan_root"] = commitment("MOSAIC.READER.COMPILATION_PLAN.v0.1", plan)
    return CompiledReader(plan=plan, payload=payload, document=document)


def validate_compiled_reader(compiled: CompiledReader) -> dict[str, Any]:
    plan = copy.deepcopy(compiled.plan)
    plan_root = plan.pop("plan_root", None)
    expected_plan = commitment("MOSAIC.READER.COMPILATION_PLAN.v0.1", plan)
    failures = []
    if plan_root != expected_plan:
        failures.append("PLAN_ROOT")
    if compiled.plan.get("input_root") != compiled.payload.get("input_root"):
        failures.append("INPUT_ROOT")
    if compiled.plan.get("object", {}).get("source_root") != compiled.document.source_root:
        failures.append("SOURCE_ROOT")
    if compiled.plan.get("object", {}).get("document_root") != compiled.document.document_root:
        failures.append("DOCUMENT_ROOT")
    expected_payload = commitment("MOSAIC.READER.PAYLOAD.v0.1", compiled.payload)
    if compiled.plan.get("realization", {}).get("payload_root") != expected_payload:
        failures.append("PAYLOAD_ROOT")
    if failures:
        raise PipelineRefusal("READER_PIPELINE_BINDING_REFUSED", ",".join(sorted(failures)))
    return {
        "schema": "mosaic.reader.compilation-validation.v0.1",
        "plan_root": plan_root,
        "source_root": compiled.document.source_root,
        "document_root": compiled.document.document_root,
        "payload_root": expected_payload,
        "target": compiled.plan["realization"]["target"],
        "authority_effect": "NONE",
        "external_effect_executed": False,
        "disposition": "PASS_LOCAL_ACCEPTANCE",
    }


__all__ = [
    "CompiledReader", "PipelineRefusal", "TARGETS", "compile_reader",
    "validate_compiled_reader",
]

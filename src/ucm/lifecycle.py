"""Deterministic lifecycle receipts for governed contracts."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import require, require_root, root

from .system import BOUNDARY


TRANSITIONS = {
    ("NONE", "DRAFT"),
    ("DRAFT", "VALIDATED"),
    ("VALIDATED", "FROZEN"),
    ("FROZEN", "SUPERSEDED"),
}


def build_lifecycle_receipt(*, contract_root: str, from_state: str, to_state: str,
                            predecessor_receipt_root: str,
                            evidence_roots: list[str]) -> dict[str, Any]:
    require_root(contract_root); require_root(predecessor_receipt_root)
    require((from_state, to_state) in TRANSITIONS, "UCM_LIFECYCLE_TRANSITION_REFUSED")
    require(type(evidence_roots) is list and len(evidence_roots) == len(set(evidence_roots)),
            "UCM_LIFECYCLE_EVIDENCE_INVALID")
    for value in evidence_roots:
        require_root(value)
    require(from_state != "NONE" or predecessor_receipt_root == "0" * 64,
            "UCM_LIFECYCLE_PREDECESSOR_INVALID")
    require(to_state == "DRAFT" or bool(evidence_roots),
            "UCM_LIFECYCLE_EVIDENCE_REQUIRED")
    body = {"schema": "mosaic.ucm.contract-lifecycle-receipt.v0.1",
            "contract_root": contract_root, "from_state": from_state,
            "to_state": to_state, "predecessor_receipt_root": predecessor_receipt_root,
            "evidence_roots": sorted(deepcopy(evidence_roots)),
            "status": "RECORDED_NOT_RATIFIED",
            "non_claims": ["NOT_AUTHORITY", "NOT_DEPLOYMENT", "NOT_ADMISSION"],
            **BOUNDARY}
    return {**body, "lifecycle_receipt_root": root(body)}

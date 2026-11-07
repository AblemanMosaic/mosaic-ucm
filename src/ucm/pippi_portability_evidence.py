"""Recompute P/PPI portability outputs from exact source bytes.

This module is filesystem-facing by design.  It is used by the native
portability legs and qualification so witness outputs cannot be populated by
copying roots from files without validating the bytes those roots describe.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .operator_history import verify_frozen_operator_registry
from .pippi_adaptive import mediation_library
from .pippi_portability import portability_policy
from .program_history import verify_frozen_program_registry
from .system import capability_registry


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("PIPPI_PORTABILITY_RECORD_INVALID")
    return value


def recompute_canonical_outputs(source_root: Path) -> list[dict[str, str]]:
    """Return the canonical output denominator after validating source bytes."""
    source_root = source_root.resolve()
    program = verify_frozen_program_registry(
        source_root=source_root,
        registry=_read(source_root / "spec/FROZEN-PROGRAM-REGISTRY.json"))
    operator = verify_frozen_operator_registry(
        source_root=source_root,
        registry=_read(source_root / "spec/FROZEN-OPERATOR-REGISTRY.json"))
    outputs = [
        {"artifact_id": "CAPABILITY_REGISTRY",
         "root": capability_registry()["root"]},
        {"artifact_id": "FROZEN_OPERATOR_REGISTRY",
         "root": operator["registry_root"]},
        {"artifact_id": "FROZEN_PROGRAM_REGISTRY",
         "root": program["registry_root"]},
        {"artifact_id": "MEDIATION_LIBRARY",
         "root": mediation_library()["mediation_library_root"]},
        {"artifact_id": "PORTABILITY_POLICY",
         "root": portability_policy()["portability_policy_root"]},
    ]
    return sorted(outputs, key=lambda row: row["artifact_id"])

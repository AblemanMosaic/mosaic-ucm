"""Field diagnostics and a deterministic install canary."""
from __future__ import annotations

import importlib.util
import platform
import sys
from typing import Any

from uclop.canonical import canonical_bytes, root

from .profiles import profile_registry
from .realization import BOUNDARY, validate_configuration, validate_contract
from .system import VERSION, capability_registry


def _canary_contract() -> dict[str, Any]:
    body = {
        "schema": "mosaic.realization-space-contract.v0.1",
        "contract_id": "UCM.FIELD_CANARY",
        "contract_version": "0.1.0",
        "subject": {"subject_id": "UCM.FIELD_CANARY", "subject_schema": "mosaic.ucm.canary.v0.1",
                    "authority_owner": "EXTERNAL", "source_roots": ["0" * 64],
                    "preserved_identity": ["SUBJECT_ROOT"], "forbidden_overrides": ["AUTHORITY"]},
        "possibility": {"intended_variation": ["CANARY_ENABLED"],
                        "excluded_claims": ["NOT_DEPLOYMENT", "NOT_AUTHORITY"]},
        "axes": [{"id": "CANARY_ENABLED", "label": "Canary enabled", "value_type": "BOOLEAN",
                  "domain": {}, "default": True, "ownership": "AUTHORIAL", "mutability": "FROZEN",
                  "continuity": "DISCRETE", "authority_effect": "NONE"}],
        "constraints": [{"id": "CANARY_REQUIRED", "kind": "INVARIANT", "severity": "HARD",
                         "operator": "EQUALS", "terms": {"axis": "CANARY_ENABLED", "value": True},
                         "explanation": "The install canary must remain enabled.",
                         "refusal_code": "UCM_CANARY_DISABLED"}],
        "capabilities": ["VALIDATE", "RECEIPT"],
        "selection": {"default_policy": "EXACT_DEFAULTS", "seed_required_for_non_unique": False},
        "lowering": {"targets": [{"target_id": "VERIFY_ONLY", "adapter_version": "0.1.0",
                                    "required_capabilities": ["VALIDATE"],
                                    "preservation_criteria": ["CANARY_REQUIRED"],
                                    "known_losses": [], "fallbacks": []}],
                     "allowed_results": ["EXACT", "REFUSED"]},
        "evidence": {"required_roots": ["CONTRACT_ROOT"], "required_fields": ["STATUS"],
                     "non_claims": ["NOT_AUTHORITY"]},
        "authority": {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
                      "self_admission": False, "release_gate": False,
                      "track_a_dependency": "NONE"},
    }
    return {**body, "root": root(body)}


def smoke() -> dict[str, Any]:
    contract = validate_contract(_canary_contract())
    checked = validate_configuration(contract, {"CANARY_ENABLED": True})
    profiles = profile_registry()
    body = {"schema": "mosaic.ucm.field-smoke.v0.1", "version": VERSION,
            "canonical_vector_sha256": __import__("hashlib").sha256(
                canonical_bytes({"a": [1, True, None], "z": "UCM"})).hexdigest(),
            "canary_contract_root": contract["root"],
            "canary_check_root": checked["root"],
            "profile_registry_root": profiles["profile_registry_root"],
            "capability_registry_root": capability_registry()["root"],
            "status": "PASS" if checked["status"] == "PASS_ADMISSIBLE" else "FAIL",
            **BOUNDARY}
    return {**body, "smoke_root": root(body)}


def doctor() -> dict[str, Any]:
    canary = smoke()
    body = {"schema": "mosaic.ucm.field-diagnostic.v0.1", "version": VERSION,
            "python": {"implementation": platform.python_implementation(),
                       "version": platform.python_version(),
                       "supported": (3, 12) <= sys.version_info[:2] < (3, 14)},
            "platform": {"system": platform.system(), "machine": platform.machine()},
            "optional_dependencies": {name: importlib.util.find_spec(name) is not None
                                      for name in ("blake3", "cryptography")},
            "canary": canary, "status": "PASS" if canary["status"] == "PASS" else "FAIL",
            "non_claims": ["NOT_QUALIFICATION", "NOT_HOST_ADMISSION", "NOT_AUTHORITY"],
            **BOUNDARY}
    return {**body, "diagnostic_root": root(body)}

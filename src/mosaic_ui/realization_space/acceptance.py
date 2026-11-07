"""Cross-domain acceptance witnesses for the domain-neutral contract kernel."""
from __future__ import annotations

import copy
from typing import Any, Mapping

from .core import RealizationSpaceError, canonical_root
from .registry import RealizationSpaceRegistry


def cross_domain_acceptance(
    contracts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate, compose, and default-select independent domain contracts."""
    if not isinstance(contracts, dict) or len(contracts) < 3:
        raise RealizationSpaceError("RSC_CROSS_DOMAIN_SET_REFUSED", "THREE_DOMAINS_REQUIRED")
    normalized: dict[str, Mapping[str, Any]] = {}
    for raw_domain, contract in contracts.items():
        domain = str(raw_domain).strip().upper()
        if not domain or domain in normalized:
            raise RealizationSpaceError("RSC_CROSS_DOMAIN_LABEL_REFUSED", domain)
        normalized[domain] = contract
    registry = RealizationSpaceRegistry(normalized.values())
    inspection = registry.inspect()
    rows = []
    for domain in sorted(normalized):
        contract = normalized[domain]
        checked = registry.inspect(str(contract["contract_id"]))
        selected = registry.select(str(contract["contract_id"]))
        owner = contract.get("subject", {}).get("authority_owner")
        if not isinstance(owner, str) or not owner:
            raise RealizationSpaceError("RSC_CROSS_DOMAIN_OWNER_REFUSED", domain)
        rows.append({
            "domain": domain,
            "contract_id": checked["contract_id"],
            "contract_root": checked["contract_root"],
            "configuration_root": selected["configuration_root"],
            "axis_count": checked["axis_count"],
            "authority_owner": owner,
            "state_effects": copy.deepcopy(selected["state_effects"]),
            "apply_modes": copy.deepcopy(selected["apply_modes"]),
        })
    body = {
        "schema": "mosaic.realization-space.cross-domain-acceptance.v0.1",
        "domain_count": len(rows),
        "domains": rows,
        "composite_root": inspection["composite"]["composite_root"],
        "axis_owner": copy.deepcopy(inspection["composite"]["axis_owner"]),
        "authority_effect": "NONE",
        "external_effect_executed": False,
        "claim_boundary": (
            "VALIDATION_SELECTION_AND_COMPOSITION_ONLY; DOES_NOT TRANSFER DOMAIN "
            "AUTHORITY OR PROVE A RUNTIME, RELEASE, OR PRODUCTION ADMISSION"
        ),
    }
    body["acceptance_root"] = canonical_root(body)
    return body


__all__ = ["cross_domain_acceptance"]

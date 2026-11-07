"""Registry and inspection surface for independent realization spaces."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Iterable, Mapping
import json

from .core import (
    RealizationSpaceError,
    compose_contracts,
    select_configuration,
    validate_contract,
)


class RealizationSpaceRegistry:
    def __init__(self, contracts: Iterable[Mapping[str, Any]] = ()) -> None:
        self._contracts: dict[str, dict[str, Any]] = {}
        for contract in contracts:
            self.register(contract)

    def register(self, contract: Mapping[str, Any]) -> dict[str, Any]:
        checked = validate_contract(contract)
        contract_id = checked["contract_id"]
        if contract_id in self._contracts:
            raise RealizationSpaceError("RSC_REGISTRY_DUPLICATE", contract_id)
        self._contracts[contract_id] = copy.deepcopy(dict(contract))
        return checked

    def load(self, path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RealizationSpaceError("RSC_REGISTRY_LOAD_REFUSED", str(path)) from exc
        return self.register(value)

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._contracts))

    def inspect(self, contract_id: str | None = None) -> dict[str, Any]:
        if contract_id is None:
            contracts = [validate_contract(self._contracts[key]) for key in self.ids()]
            return {
                "schema": "mosaic.realization-space-registry.v0.1",
                "contracts": [{"contract_id": row["contract_id"],
                               "contract_root": row["contract_root"],
                               "axis_count": row["axis_count"]} for row in contracts],
                "composite": compose_contracts(self._contracts.values()) if contracts else None,
                "authority_effect": "NONE",
            }
        if contract_id not in self._contracts:
            raise RealizationSpaceError("RSC_REGISTRY_UNKNOWN", contract_id)
        return validate_contract(self._contracts[contract_id])

    def contract(self, contract_id: str) -> dict[str, Any]:
        if contract_id not in self._contracts:
            raise RealizationSpaceError("RSC_REGISTRY_UNKNOWN", contract_id)
        return copy.deepcopy(self._contracts[contract_id])

    def select(self, contract_id: str, **options: Any) -> dict[str, Any]:
        return select_configuration(self.contract(contract_id), **options)

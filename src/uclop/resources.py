from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical import exact_keys, require, root


RESOURCE_KEYS = {"steps", "memory_bytes", "solver_calls", "tool_invocations"}


def validate_budget(value: Any, path: str = "$.budget") -> dict[str, int]:
    item = exact_keys(value, RESOURCE_KEYS, path)
    for key in RESOURCE_KEYS:
        require(type(item[key]) is int and type(item[key]) is not bool and item[key] >= 0, "RESOURCE_BUDGET_INVALID", f"{path}.{key}")
    return deepcopy(item)


class ReservationLedger:
    def __init__(self, budget: dict[str, int]) -> None:
        self.budget = validate_budget(budget)
        self.used = {key: 0 for key in RESOURCE_KEYS}
        self.peak = {key: 0 for key in RESOURCE_KEYS}
        self.reservations: list[dict[str, Any]] = []
        self.consumptions: list[dict[str, Any]] = []
        self.releases: list[dict[str, Any]] = []
        self.active: dict[str, dict[str, int]] = {}

    def reserve(self, amount: dict[str, int], purpose: str) -> dict[str, Any]:
        requested = validate_budget(amount, "$.reservation")
        require(type(purpose) is str and purpose, "RESERVATION_PURPOSE_INVALID")
        for key in RESOURCE_KEYS:
            require(self.used[key] + requested[key] <= self.budget[key], "RESOURCE_RESERVATION_REFUSED", f"$.reservation.{key}")
        sequence = len(self.reservations) + 1
        body = {"schema": "ucl.op.resource_reservation.v1", "sequence": sequence, "purpose": purpose, "amount": requested, "prior_used": deepcopy(self.used)}
        receipt = {**body, "reservation_root": root(body)}
        for key in RESOURCE_KEYS:
            self.used[key] += requested[key]
            self.peak[key] = max(self.peak[key], self.used[key])
        self.reservations.append(receipt)
        self.active[receipt["reservation_root"]] = deepcopy(requested)
        return deepcopy(receipt)

    def consume(self, reservation_root: str, amount: dict[str, int], purpose: str) -> dict[str, Any]:
        require(reservation_root in self.active, "RESOURCE_RESERVATION_UNKNOWN")
        require(type(purpose) is str and purpose, "CONSUMPTION_PURPOSE_INVALID")
        observed = validate_budget(amount, "$.consumption")
        totals = {key: sum(row["amount"][key] for row in self.consumptions if row["reservation_root"] == reservation_root) for key in RESOURCE_KEYS}
        for key in RESOURCE_KEYS:
            require(totals[key] + observed[key] <= self.active[reservation_root][key], "RESOURCE_CONSUMPTION_EXCEEDS_RESERVATION", f"$.consumption.{key}")
        body = {"schema": "ucl.op.resource_consumption.v1", "sequence": len(self.consumptions) + 1, "reservation_root": reservation_root, "purpose": purpose, "amount": observed}
        receipt = {**body, "consumption_root": root(body)}; self.consumptions.append(receipt); return deepcopy(receipt)

    def release(self, reservation_root: str, purpose: str) -> dict[str, Any]:
        require(reservation_root in self.active, "RESOURCE_RESERVATION_UNKNOWN")
        require(type(purpose) is str and purpose, "RELEASE_PURPOSE_INVALID")
        amount = self.active.pop(reservation_root)
        for key in RESOURCE_KEYS:
            self.used[key] -= amount[key]
        body = {"schema": "ucl.op.resource_release.v1", "sequence": len(self.releases) + 1, "reservation_root": reservation_root, "purpose": purpose, "amount": amount, "remaining_used": deepcopy(self.used)}
        receipt = {**body, "release_root": root(body)}; self.releases.append(receipt); return deepcopy(receipt)

    def snapshot(self) -> dict[str, Any]:
        body = {"schema": "ucl.op.resource_snapshot.v2", "budget": self.budget, "used": self.used, "peak": self.peak, "reservations": self.reservations, "consumptions": self.consumptions, "releases": self.releases, "active_reservation_roots": sorted(self.active)}
        return {**deepcopy(body), "snapshot_root": root(body)}

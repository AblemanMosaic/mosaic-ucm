"""Deterministic test-matrix sampling (library L3, ruling L3-R2 / RL-7).

Policy: exhaustive while the full product is <= 500 cases; pairwise (strength 2) above that for routine
evidence; strength 3 before a new pack is proposed for ratification. Same factors -> same plan -> same
commitment. `missing_tuples` is the proof that a plan covers every t-way combination.
"""
from __future__ import annotations

import itertools
import math
from typing import Any

from .canonical import commitment
from .model import UIRefusal

EXHAUSTIVE_LIMIT = 500
MODES = ("auto", "exhaustive", "pairwise", "strength3")


def _tuples(levels: list[int], strength: int) -> set[tuple]:
    out = set()
    for cols in itertools.combinations(range(len(levels)), strength):
        for values in itertools.product(*(range(levels[c]) for c in cols)):
            out.add((cols, values))
    return out


def _row_tuples(row: list[int], strength: int) -> set[tuple]:
    return {(cols, tuple(row[c] for c in cols)) for cols in itertools.combinations(range(len(row)), strength)}


def covering_array(levels: list[int], strength: int) -> list[list[int]]:
    """Greedy, fully deterministic strength-t covering array over factor level counts."""
    if strength >= len(levels):
        return [list(r) for r in itertools.product(*(range(n) for n in levels))]
    uncovered = _tuples(levels, strength)
    rows = []
    while uncovered:
        cols, values = min(uncovered)
        row: list[int | None] = [None] * len(levels)
        for c, v in zip(cols, values):
            row[c] = v
        for k in range(len(levels)):
            if row[k] is not None:
                continue
            best, best_gain = 0, -1
            for v in range(levels[k]):
                row[k] = v
                fixed = [i for i in range(len(levels)) if row[i] is not None]
                gain = sum(1 for cs in itertools.combinations(fixed, strength)
                           if k in cs and (cs, tuple(row[i] for i in cs)) in uncovered)
                if gain > best_gain:
                    best, best_gain = v, gain
            row[k] = best
        rows.append(row)  # type: ignore[arg-type]
        uncovered -= _row_tuples(row, strength)  # type: ignore[arg-type]
    return rows  # type: ignore[return-value]


def missing_tuples(plan_rows: list[dict[str, Any]], factors: dict[str, list[Any]], strength: int) -> list[tuple]:
    """Every t-way combination of factor values absent from the plan (empty means full coverage)."""
    names = list(factors)
    seen = {tuple((n, row[n]) for n in combo) for row in plan_rows for combo in itertools.combinations(names, strength)}
    return [t for combo in itertools.combinations(names, strength)
            for t in itertools.product(*([(n, v) for v in factors[n]] for n in combo)) if t not in seen]


def build_plan(factors: dict[str, list[Any]], mode: str = "auto") -> dict[str, Any]:
    if mode not in MODES:
        raise UIRefusal("SAMPLING_MODE_UNKNOWN", mode)
    if not factors or any(not values for values in factors.values()):
        raise UIRefusal("SAMPLING_FACTORS_INVALID", "")
    names, full = list(factors), math.prod(len(v) for v in factors.values())
    chosen = ("exhaustive" if full <= EXHAUSTIVE_LIMIT else "pairwise") if mode == "auto" else mode
    levels = [len(factors[n]) for n in names]
    if chosen == "exhaustive":
        rows = [list(r) for r in itertools.product(*(range(n) for n in levels))]
        strength = len(names)
    else:
        strength = 2 if chosen == "pairwise" else 3
        rows = covering_array(levels, strength)
    cases = [{n: factors[n][i] for n, i in zip(names, row)} for row in rows]
    value = {"schema": "mosaic.ui.sampling-plan.v0.1", "factors": factors, "mode": chosen, "strength": strength,
             "full_product": full, "cases": cases, "case_count": len(cases), "authority_effect": "NONE"}
    value["commitment"] = commitment("MOSAIC.UI.SAMPLING_PLAN.v0.1", value)
    return value

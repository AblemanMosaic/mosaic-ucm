"""Evidence gate classes and the repeatability gate (library L3, ruling L3-R1).

DETERMINISTIC gates must produce the same commitment (or canonical output) in independent processes.
MEASUREMENT gates must produce the same verdict and checks; measured values may vary.
ENVIRONMENT gates need external inputs and are not run here.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from .canonical import canonical_bytes, commitment, read_json
from .model import UIRefusal

REGISTRY_PATH = Path(__file__).resolve().parent / "evidence_gates.json"


def load_registry() -> dict[str, Any]:
    return read_json(REGISTRY_PATH)


def _fingerprint(value: Any) -> str:
    if isinstance(value, dict) and isinstance(value.get("commitment"), str):
        return value["commitment"]
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _verdict(value: Any) -> Any:
    """What a MEASUREMENT gate must repeat: disposition and named check outcomes, not measured values."""
    if not isinstance(value, dict):
        return None
    checks = value.get("checks")
    if isinstance(checks, dict):
        checks = {k: (v if isinstance(v, bool) else v.get("passed") if isinstance(v, dict) else None) for k, v in checks.items()}
    return {"disposition": value.get("disposition"), "checks": checks, "failures": value.get("failure_count", value.get("failures"))}


def run_cli(argv: list[str], *, cwd: Path | None = None, timeout: float = 300) -> Any:
    """One independent process per run, so no in-process cache can mask nondeterminism."""
    done = subprocess.run([sys.executable, "-m", "mosaic_ui.cli", *argv], capture_output=True, text=True,
                          cwd=cwd, timeout=timeout)
    if done.returncode != 0:
        return {"error": f"EXIT_{done.returncode}", "stderr_tail": done.stderr[-300:]}
    return json.loads(done.stdout)


def check_repeatable(runs: list[Callable[[], Any]], gate_class: str) -> dict[str, Any]:
    """Execute each producer twice; compare by class. Producers are injectable for negative controls."""
    results = []
    for produce in runs:
        first, second = produce(), produce()
        if gate_class == "DETERMINISTIC":
            a, b = _fingerprint(first), _fingerprint(second)
        else:
            a, b = _fingerprint(_verdict(first)), _fingerprint(_verdict(second))
        error = (first.get("error") if isinstance(first, dict) else None) or (second.get("error") if isinstance(second, dict) else None)
        results.append({"first": a, "second": b, "repeatable": a == b and not error, "error": error})
    return {"repeatable": all(r["repeatable"] for r in results), "runs": results}


def gate_repeat(*, include_measurement: bool = True, only: list[str] | None = None) -> dict[str, Any]:
    registry = load_registry()
    known = set(registry["commands"]) | set(registry["witnesses"])
    unknown = sorted(set(only or ()) - known)
    if unknown:
        raise UIRefusal("EVIDENCE_GATE_SELECTION_REFUSED", ",".join(unknown))
    report = {}
    for name, entry in registry["commands"].items():
        if only and name not in only:
            continue
        if entry["class"] == "DETERMINISTIC" or (include_measurement and entry["class"] == "MEASUREMENT" and "argv" in entry):
            report[name] = {"class": entry["class"],
                            **check_repeatable([lambda argv=entry["argv"]: run_cli(argv)], entry["class"])}
    if include_measurement:
        for name, entry in registry["witnesses"].items():
            if only and name not in only:
                continue
            module, attribute = entry["callable"].split(":")
            fn = getattr(importlib.import_module(module), attribute)
            produce = (lambda fn=fn: fn("0" * 64)) if attribute == "architecture_witness" else fn
            report[name] = {"class": "MEASUREMENT", **check_repeatable([produce], "MEASUREMENT")}
    if not report:
        raise UIRefusal("EVIDENCE_GATE_EMPTY", ",".join(only or ()))
    failures = sorted(name for name, r in report.items() if not r["repeatable"])
    value = {"schema": "mosaic.ui.gate-repeat.v0.1", "gates": report, "failures": failures,
             "disposition": "PASS_LOCAL_CANDIDATE" if not failures else "FAIL", "authority_effect": "NONE"}
    value["commitment"] = commitment("MOSAIC.UI.GATE_REPEAT.v0.1", {k: v for k, v in value.items() if k != "gates"} |
                                     {"gates": {k: v["repeatable"] for k, v in report.items()}})
    return value

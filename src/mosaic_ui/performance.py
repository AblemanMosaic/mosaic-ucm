"""Deterministic workload construction and local performance-envelope evidence."""
from __future__ import annotations

import argparse
import copy
import gc
import math
import platform
import statistics
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

from mosaic_ui_std.catalog import load_runtime_catalog

from .canonical import atomic_write, canonical_bytes, commitment, read_json
from .headless import HeadlessUI
from .model import UIRefusal, validate_tree
from .pilot import build_payload


DEFAULT_POLICY = Path(__file__).resolve().parent / "source" / "performance-policy.json"
POLICY_KEYS = {"schema", "policy_id", "samples", "cases", "standing", "authority_effect"}
CASE_KEYS = {
    "node_count", "max_construct_ms", "max_snapshot_ms", "max_event_ms",
    "max_project_ms", "max_peak_bytes",
}


class PerformanceRefusal(UIRefusal):
    pass


def validate_performance_policy(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != POLICY_KEYS \
            or value.get("schema") != "mosaic.ui.performance-policy.v0.1":
        raise PerformanceRefusal("PERFORMANCE_POLICY_REFUSED", "SHAPE_OR_SCHEMA")
    if value.get("authority_effect") != "NONE" or value.get("standing") != "LOCAL_CANDIDATE":
        raise PerformanceRefusal("PERFORMANCE_POLICY_REFUSED", "POSTURE")
    samples = value.get("samples")
    if isinstance(samples, bool) or not isinstance(samples, int) or not 1 <= samples <= 10:
        raise PerformanceRefusal("PERFORMANCE_POLICY_REFUSED", "SAMPLES")
    cases = value.get("cases")
    if not isinstance(cases, list) or [item.get("node_count") for item in cases if isinstance(item, dict)] != [25, 250, 1000, 10000]:
        raise PerformanceRefusal("PERFORMANCE_POLICY_REFUSED", "CASE_SET")
    for case in cases:
        if not isinstance(case, dict) or set(case) != CASE_KEYS:
            raise PerformanceRefusal("PERFORMANCE_POLICY_REFUSED", "CASE_SHAPE")
        for key, amount in case.items():
            if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
                raise PerformanceRefusal("PERFORMANCE_POLICY_REFUSED", f"{case.get('node_count')}:{key}")
    return copy.deepcopy(value)


def build_workload(node_count: int) -> tuple[dict[str, Any], Any, tuple[int, int]]:
    if isinstance(node_count, bool) or not isinstance(node_count, int) or node_count < 1:
        raise PerformanceRefusal("PERFORMANCE_NODE_COUNT_REFUSED", str(node_count))
    children = [{
        "kind": "BUTTON" if index == 0 else "BADGE",
        "node_id": f"benchmark.node.{index:05d}",
        "semantics": {
            "role": "button" if index == 0 else "status",
            "name": "B" if index == 0 else f"N{index}",
            "description": "",
            "focusable": index == 0,
            "actions": ["activate"] if index == 0 else [],
        },
        "props": {
            "realization_key": f"benchmark.node.{index:05d}",
            "default": "IDLE",
            **({"target_view": "benchmark"} if index == 0 else {}),
        },
        "children": [],
        **({"operation_ref": "SHOW_BENCHMARK"} if index == 0 else {}),
    } for index in range(node_count)]
    tree = {
        "kind": "WINDOW",
        "node_id": "benchmark.window",
        "semantics": {"role": "application", "name": "Mosaic performance workload", "description": "", "focusable": False, "actions": []},
        "props": {"layout_provider": "mosaic.ui.performance-grid.v0.1"},
        "children": children,
    }
    application = {
        "schema": "mosaic.ui.performance-application.v0.1",
        "application_id": "MOSAIC_PERFORMANCE_WORKLOAD",
        "declared_operation_ids": ["SHOW_BENCHMARK"],
        "lifecycle": {
            "schema": "mosaic.ui.std.lifecycle-binding.v0.1",
            "initial_view": "benchmark",
            "operation_controls": {"cancel_key": None, "progress_key": None},
            "operation_classes": {
                "NAVIGATE": ["SHOW_BENCHMARK"], "LONG_RUNNING": [], "CANCEL": [],
                "TOGGLE_DISCLOSURE": [], "HOST_WITHHELD": [],
            },
            "status_templates": {
                "initial": "Ready", "queued": "{operation_phrase}",
                "progress": "{stage_phrase} {percent} {mm}:{ss}",
                "terminal": "{operation} {terminal} {message}", "cancelled": "{operation}",
            },
            "progress_default_stage": "benchmark",
        },
        "tree": tree,
        "standing": "LOCAL_CANDIDATE",
        "authority_effect": "NONE",
    }
    payload = build_payload()
    payload["application"] = application
    payload["tree_validation"] = validate_tree(tree, {"SHOW_BENCHMARK"})
    payload["input_root"] = commitment("MOSAIC.UI.PERFORMANCE_WORKLOAD.v0.1", {
        "node_count": node_count, "application": application,
    })
    columns = math.ceil(math.sqrt(node_count))
    rows = math.ceil(node_count / columns)
    cell = 24
    viewport = (columns * cell, rows * cell)
    plan = {
        f"benchmark.node.{index:05d}": ((index % columns) * cell, (index // columns) * cell, cell, cell)
        for index in range(node_count)
    }
    return payload, (lambda _width, _height: plan), viewport


def _milliseconds(start: int, end: int) -> float:
    return round((end - start) / 1_000_000, 3)


def _sample(node_count: int, catalog: dict[str, Any]) -> dict[str, Any]:
    payload, layout, viewport = build_workload(node_count)
    gc.collect()
    tracemalloc.start()
    started = time.perf_counter_ns()
    runtime = HeadlessUI(payload, layout, catalog=catalog)
    constructed = time.perf_counter_ns()
    snapshot = runtime.snapshot()
    snapshotted = time.perf_counter_ns()
    runtime.apply({"intent": "FOCUS", "node_id": "benchmark.node.00000"})
    event_applied = time.perf_counter_ns()
    projection = runtime.project(*viewport).as_dict()
    projected = time.perf_counter_ns()
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "construct_ms": _milliseconds(started, constructed),
        "snapshot_ms": _milliseconds(constructed, snapshotted),
        "event_ms": _milliseconds(snapshotted, event_applied),
        "project_ms": _milliseconds(event_applied, projected),
        "peak_bytes": peak,
        "snapshot_commitment": snapshot["commitment"],
        "projection_gate": projection["gates"]["disposition"],
        "projected_node_count": len(projection["semantics"]["nodes"]),
    }


def run_performance_gate(
    policy_path: Path = DEFAULT_POLICY, *, output: Path | None = None,
) -> dict[str, Any]:
    policy = validate_performance_policy(read_json(policy_path.resolve()))
    catalog = load_runtime_catalog()
    cases = []
    failures = []
    for envelope in policy["cases"]:
        samples = [_sample(envelope["node_count"], catalog) for _ in range(policy["samples"])]
        metrics = {
            key: round(statistics.median(sample[key] for sample in samples), 3)
            for key in ("construct_ms", "snapshot_ms", "event_ms", "project_ms", "peak_bytes")
        }
        checks = []
        for metric, limit in (
            ("construct_ms", "max_construct_ms"), ("snapshot_ms", "max_snapshot_ms"),
            ("event_ms", "max_event_ms"), ("project_ms", "max_project_ms"),
            ("peak_bytes", "max_peak_bytes"),
        ):
            passed = metrics[metric] <= envelope[limit]
            checks.append({"metric": metric, "observed": metrics[metric], "limit": envelope[limit],
                           "disposition": "PASS" if passed else "REFUSE"})
            if not passed:
                failures.append({"node_count": envelope["node_count"], "metric": metric,
                                 "observed": metrics[metric], "limit": envelope[limit]})
        structural_pass = all(sample["projection_gate"] == "PASS" and sample["projected_node_count"] == envelope["node_count"] for sample in samples)
        if not structural_pass:
            failures.append({"node_count": envelope["node_count"], "metric": "STRUCTURAL_PROJECTION"})
        cases.append({
            "node_count": envelope["node_count"], "samples": samples, "median": metrics,
            "checks": checks, "structural_projection": "PASS" if structural_pass else "REFUSE",
        })
    value = {
        "schema": "mosaic.ui.performance-evidence.v0.1",
        "policy_id": policy["policy_id"],
        "policy_root": commitment("MOSAIC.UI.PERFORMANCE_POLICY.v0.1", policy),
        "catalog_root": commitment("MOSAIC.UI.STD.CATALOG.v0.1", catalog),
        "environment": {
            "python": platform.python_version(), "implementation": platform.python_implementation(),
            "platform": sys.platform, "machine": platform.machine(),
        },
        "cases": cases,
        "failure_count": len(failures),
        "failures": failures,
        "disposition": "PASS_LOCAL_CANDIDATE" if not failures else "REFUSE",
        "standing": "LOCAL_MACHINE_PERFORMANCE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": "OBSERVED_ENVELOPES_APPLY_TO_THIS_MACHINE_AND_SYNTHETIC_WORKLOAD_ONLY",
    }
    value["commitment"] = commitment("MOSAIC.UI.PERFORMANCE_EVIDENCE.v0.1", value)
    if output is not None:
        atomic_write(output.resolve(), canonical_bytes(value) + b"\n")
    return value


__all__ = [
    "DEFAULT_POLICY", "PerformanceRefusal", "build_workload", "run_performance_gate",
    "validate_performance_policy",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = run_performance_gate(args.policy, output=args.output)
        print(canonical_bytes(result).decode("utf-8"))
        return 0 if result["disposition"] == "PASS_LOCAL_CANDIDATE" else 32
    except (PerformanceRefusal, OSError, ValueError) as exc:
        print(canonical_bytes({
            "schema": "mosaic.ui.performance-refusal.v0.1",
            "disposition": "REFUSE",
            "refusal_code": getattr(exc, "code", "PERFORMANCE_EXECUTION_REFUSED"),
            "detail": getattr(exc, "detail", str(exc)),
            "authority_effect": "NONE",
        }).decode("utf-8"))
        return 32


if __name__ == "__main__":
    raise SystemExit(main())

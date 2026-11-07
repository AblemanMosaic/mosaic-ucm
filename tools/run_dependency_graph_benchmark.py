#!/usr/bin/env python3
"""Measure the bounded dependency evaluator without changing release semantics."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root  # noqa: E402
from ucm.dependency_adapters import build_benchmark_report  # noqa: E402
from ucm.dependency_graph import (build_graph, build_producer_receipt,
    build_reuse_admission, build_snapshot, evaluate_graph, verify_graph)  # noqa: E402


R = [f"{value:x}" * 64 for value in range(1, 9)]


def node(node_id: str, kind: str, dependencies=(), *, parameters=None,
         grade="DETERMINISTIC_DERIVATION") -> dict:
    return {
        "node_id": node_id, "kind": kind,
        "dependencies": [{"node_id": item[0], "edge_kind": item[1],
                          "required": True} for item in dependencies],
        "parameters": parameters or {}, "transform_id": kind,
        "transform_version": "v0.1", "semantic_contract_root": R[0],
        "policy_root": R[1], "jurisdiction_root": R[2],
        "environment_root": R[3], "closure_coverage": "COMPLETE",
        "evidence_grade": grade, "pure": True,
    }


def fixture() -> tuple[dict, dict]:
    graph = build_graph(
        graph_id="benchmark", adapter_id="UCM_BOUNDED_BENCHMARK",
        adapter_version="v0.1", adapter_policy_root=R[1],
        schema_registry_root=R[4], trust_root=R[5],
        nodes=[
            node("source", "INPUT", grade="DECLARED_INPUT"),
            node("title", "SEMANTIC_PROJECT", [("source", "SEMANTIC_PROJECTION")],
                 parameters={"field_path": ["title"]}),
            node("ready", "CHECK_FIELD", [("source", "EVIDENCE")],
                 parameters={"field_path": ["ready"],
                             "expected": {"present": True, "value": True},
                             "reason_code": "SOURCE_NOT_READY"},
                 grade="EXACT_INPUT_CHECK"),
            node("prepare", "PREPARE", [("title", "SEMANTIC_PROJECTION"),
                                           ("ready", "EVIDENCE")],
                 parameters={"preparation_id": "benchmark"},
                 grade="NON_AUTHORIZING_PREPARATION"),
        ],
    )
    snapshot = build_snapshot(
        graph=graph, snapshot_id="benchmark:stable", observed_at_ns=0,
        predecessor_snapshot_root=None,
        inputs=[{"node_id": "source", "presence": {"present": True,
                 "value": {"title": "Stable output", "ready": True}}}],
    )
    return graph, snapshot


def elapsed(callable_, iterations: int):
    start = time.perf_counter_ns()
    value = None
    for _ in range(iterations):
        value = callable_()
    return time.perf_counter_ns() - start, value


def run(iterations: int) -> dict:
    if not 1 <= iterations <= 10_000:
        raise SystemExit("DEPENDENCY_BENCHMARK_ITERATIONS_OUT_OF_RANGE")
    graph, snapshot = fixture()
    hash_ns, _ = elapsed(lambda: root(graph), iterations)
    walk_ns, _ = elapsed(lambda: verify_graph(graph), iterations)
    uncached_ns, uncached = elapsed(
        lambda: evaluate_graph(graph=graph, snapshot=snapshot,
                               mode="DISABLED"), iterations)
    producer = build_producer_receipt(
        producer_root=R[6], graph=graph, snapshot=snapshot,
        evaluation=uncached, execution_capsule_root=R[7], checker_root=R[4])
    admission = build_reuse_admission(
        graph=graph, snapshot=snapshot, prior_graph=graph,
        prior_snapshot=snapshot, prior_evaluation=uncached,
        expected_prior_evaluation_root=uncached["evaluation_root"],
        expected_producer_root=R[6], producer_receipt=producer,
        consumer_trust_root=R[5], admitted_evidence_grades=[
            "DECLARED_INPUT", "DETERMINISTIC_DERIVATION", "EXACT_INPUT_CHECK",
            "NON_AUTHORIZING_PREPARATION"], reuse_mode="VERIFIED_PURE_REUSE")
    shadow_admission = {**admission, "reuse_mode": "SHADOW_IMPACT"}
    shadow_admission["admission_root"] = root({
        key: value for key, value in shadow_admission.items()
        if key != "admission_root"})
    shadow_ns, shadow = elapsed(
        lambda: evaluate_graph(graph=graph, snapshot=snapshot,
                               prior_evaluation=uncached,
                               reuse_admission=shadow_admission,
                               expected_prior_evaluation_root=uncached["evaluation_root"],
                               expected_producer_root=R[6],
                               expected_producer_receipt_root=producer["receipt_root"],
                               expected_consumer_trust_root=R[5],
                               mode="SHADOW_IMPACT"), iterations)
    reuse_ns, reused = elapsed(
        lambda: evaluate_graph(graph=graph, snapshot=snapshot,
                               prior_evaluation=uncached,
                               reuse_admission=admission,
                               expected_prior_evaluation_root=uncached["evaluation_root"],
                               expected_producer_root=R[6],
                               expected_producer_receipt_root=producer["receipt_root"],
                               expected_consumer_trust_root=R[5],
                               mode="VERIFIED_PURE_REUSE"), iterations)
    expected = {row["node_id"]: row["output_root"] for row in uncached["results"]}
    for result in (shadow, reused):
        actual = {row["node_id"]: row["output_root"] for row in result["results"]}
        if actual != expected:
            raise SystemExit("DEPENDENCY_BENCHMARK_SEMANTIC_OUTPUT_DIVERGED")
    output_root = root(expected)
    common = {"output_root": output_root, "hash_ns": hash_ns,
              "walk_ns": walk_ns, "retrieval_ns": 0,
              "storage_bytes": len(canonical_bytes({"graph": graph,
                                                     "snapshot": snapshot})),
              "node_count": len(graph["nodes"]),
              "edge_count": sum(len(row["dependencies"]) for row in graph["nodes"]),
              "change_count": 0}
    report = build_benchmark_report(
        graph_root=graph["graph_root"],
        corpus_root=root({"fixture": "UCM_BOUNDED_BENCHMARK", "iterations": iterations}),
        modes=[
            {**common, "mode": "UNCACHED", "transform_ns": uncached_ns},
            {**common, "mode": "SHADOW_IMPACT", "transform_ns": shadow_ns},
            {**common, "mode": "VERIFIED_PURE_REUSE", "transform_ns": reuse_ns,
             "retrieval_ns": reuse_ns},
        ],
    )
    body = {
        "schema": "mosaic.ucm.dependency-benchmark-evidence.v0.1",
        "iterations": iterations,
        "measurement_scope": "BUILDER_BOUNDED_LOCAL_MEASUREMENT",
        "qualification_or_authority_claim": False,
        "report": report,
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        "real_a5": False, "g0": "CLOSED",
    }
    return {**body, "measurement_root": root(body)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    report = run(args.iterations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(report) + b"\n")
    print(json.dumps({"status": "PASS", "measurement_root": report["measurement_root"],
                      "output": str(args.output.resolve())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

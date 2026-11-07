#!/usr/bin/env python3
"""Build the deterministic five-scenario Dependency Graph boundary demo."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root  # noqa: E402
from ucm.dependency_graph import (  # noqa: E402
    apply_snapshot_delta, build_graph, build_portable_closure, build_snapshot,
    compare_evaluations, evaluate_graph, verify_evaluation,
    verify_portable_closure,
)


R = [root({"demo-root": index}) for index in range(12)]
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def node(node_id: str, kind: str, dependencies=(), parameters=None,
         *, grade="DETERMINISTIC_DERIVATION"):
    return {
        "node_id": node_id, "kind": kind,
        "dependencies": [{"node_id": item[0], "edge_kind": item[1],
                          "required": item[2]} for item in dependencies],
        "parameters": parameters or {}, "transform_id": kind,
        "transform_version": "v0.1", "semantic_contract_root": R[0],
        "policy_root": R[1], "jurisdiction_root": R[2],
        "environment_root": R[3], "closure_coverage": "COMPLETE",
        "evidence_grade": grade, "pure": True,
    }


def build() -> dict:
    graph = build_graph(
        graph_id="UCM-DEPENDENCY-FIRST-BOUNDARY", adapter_id="PROJECT_INTELLIGENCE",
        adapter_version="v0.1", adapter_policy_root=R[4],
        schema_registry_root=R[5], trust_root=R[6], closure_claim="COMPLETE",
        nodes=[
            node("presentation", "INPUT", grade="DECLARED_INPUT"),
            node("source", "INPUT", grade="DECLARED_INPUT"),
            node("header", "INPUT", grade="DECLARED_INPUT"),
            node("policy", "INPUT", grade="DECLARED_INPUT"),
            node("context", "INPUT", grade="DECLARED_INPUT"),
            node("meaning", "SEMANTIC_PROJECT", [("presentation", "SEMANTIC_PROJECTION", True)],
                 {"field_path": ["meaning"]}),
            node("compile", "PREPARE", [("source", "EXACT_BYTES", True),
                                            ("header", "EXACT_BYTES", True)],
                 {"preparation_id": "compile"}, grade="NON_AUTHORIZING_PREPARATION"),
            node("current", "CURRENT_USE", [("policy", "FRESHNESS", True)],
                 {"expected_checkpoint_root": R[7]}, grade="EXACT_INPUT_CHECK"),
            node("context_projection", "PROJECT", [("context", "EVIDENCE", True)],
                 {"field_path": ["text"]}),
            node("target", "PREPARE", [("meaning", "SEMANTIC_PROJECTION", True),
                                          ("compile", "EVIDENCE", True),
                                          ("current", "POLICY", True)],
                 {"preparation_id": "target"}, grade="NON_AUTHORIZING_PREPARATION"),
        ])
    base = build_snapshot(
        graph=graph, snapshot_id="base", predecessor_snapshot_root=None,
        observed_at_ns=10, inputs=[
            {"node_id": "presentation", "presence": {"present": True,
                "value": {"meaning": "stable", "style": "light"}}},
            {"node_id": "source", "presence": {"present": True, "value": "source-v1"}},
            {"node_id": "header", "presence": {"present": True, "value": "header-v1"}},
            {"node_id": "policy", "presence": {"present": True,
                "value": {"expires_at_ns": 100, "revoked": False,
                          "checkpoint_root": R[7]}}},
            {"node_id": "context", "presence": {"present": True,
                "value": {"text": "rule-v1"}}},
        ])
    base_eval = evaluate_graph(graph=graph, snapshot=base, now_ns=20)

    def scenario(name: str, updates: list[dict], now_ns: int = 20):
        folded = apply_snapshot_delta(
            graph=graph, predecessor=base,
            expected_predecessor_root=base["snapshot_root"], delta_id=name,
            updates=updates, snapshot_id=name, observed_at_ns=11)
        evaluation = evaluate_graph(graph=graph, snapshot=folded["snapshot"], now_ns=now_ns)
        return folded["snapshot"], evaluation, compare_evaluations(
            graph=graph, before=base_eval, after=evaluation)

    presentation_s, presentation_e, presentation_i = scenario("presentation-only", [{
        "node_id": "presentation", "presence": {"present": True,
            "value": {"meaning": "stable", "style": "dark"}}}])
    header_s, header_e, header_i = scenario("header-change", [{
        "node_id": "header", "presence": {"present": True, "value": "header-v2"}}])
    policy_s, policy_e, policy_i = scenario("policy-expiry", [{
        "node_id": "policy", "presence": {"present": True,
            "value": {"expires_at_ns": 15, "revoked": False,
                      "checkpoint_root": R[7]}}}], now_ns=20)
    context_s, context_e, context_i = scenario("context-evidence", [{
        "node_id": "context", "presence": {"present": True,
            "value": {"text": "rule-v2"}}}])
    closure = build_portable_closure(
        profile="REPLAY", graph=graph, snapshot=header_s, evaluation=header_e,
        software_root=R[8], adapter_root=R[9], schema_roots=[R[10]],
        evidence_roots=[R[11]], members=[{
            "path": "records/demo.json", "sha256": R[0], "bytes": 1,
            "role": "DEMONSTRATION_FIXTURE"}])
    verify_portable_closure(closure)
    verify_evaluation(graph=graph, snapshot=header_s, evaluation=header_e, now_ns=20)

    assertions = {
        "presentation_exact_changed": "presentation" in presentation_i["changed_output"],
        "presentation_semantic_projection_stable": "meaning" in presentation_i["unchanged_output"],
        "header_invalidates_compile_closure": "compile" in header_i["changed_output"],
        "policy_invalidates_current_use": "current" in policy_i["blocked"],
        "context_updates_context_only": (
            "context_projection" in context_i["changed_output"]
            and "compile" in context_i["unchanged_output"]),
        "fresh_reconstruction_matches": True,
    }
    if not all(assertions.values()):
        raise SystemExit("DEPENDENCY_BOUNDARY_DEMO_ASSERTION_FAILED")
    body = {
        "schema": "mosaic.ucm.dependency-boundary-demo.v0.1",
        "graph_root": graph["graph_root"], "base_snapshot_root": base["snapshot_root"],
        "base_evaluation_root": base_eval["evaluation_root"],
        "scenario_roots": {
            "presentation_only": presentation_i["impact_root"],
            "header_change": header_i["impact_root"],
            "policy_expiry": policy_i["impact_root"],
            "context_evidence": context_i["impact_root"],
            "portable_replay": closure["portable_closure_root"],
        },
        "assertions": assertions, "execution_performed": False,
        **BOUNDARY,
    }
    return {**body, "demo_root": root(body)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = ROOT / "examples" / "dependency-graph" / "BOUNDARY-DEMO.json"
    expected = canonical_bytes(build()) + b"\n"
    if args.check:
        if not path.is_file() or path.read_bytes() != expected:
            raise SystemExit("DEPENDENCY_BOUNDARY_DEMO_MISMATCH")
    else:
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(expected)
    print(json.dumps({"status": "PASS", "path": str(path),
                      "demo_root": json.loads(expected)["demo_root"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

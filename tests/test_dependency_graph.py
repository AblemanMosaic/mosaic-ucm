from __future__ import annotations

import unittest

from uclop.canonical import Refusal, root
from ucm.dependency_graph import (
    apply_snapshot_delta, build_graph, build_portable_closure,
    build_producer_receipt, build_reuse_admission, build_snapshot,
    compare_evaluations, evaluate_graph, explain_node, verify_evaluation,
    verify_graph, verify_portable_closure, verify_snapshot,
)


R = [f"{i:x}" * 64 for i in range(1, 10)]


def node(node_id, kind, dependencies=(), parameters=None, *, closure="COMPLETE",
         grade="DETERMINISTIC_DERIVATION", pure=True, transform=None,
         semantic=R[0], policy=R[1], jurisdiction=R[2], environment=R[3]):
    return {
        "node_id": node_id, "kind": kind,
        "dependencies": [
            {"node_id": item[0], "edge_kind": item[1], "required": item[2]}
            for item in dependencies
        ],
        "parameters": parameters or {}, "transform_id": transform or kind,
        "transform_version": "v0.1", "semantic_contract_root": semantic,
        "policy_root": policy, "jurisdiction_root": jurisdiction,
        "environment_root": environment, "closure_coverage": closure,
        "evidence_grade": grade, "pure": pure,
    }


class DependencyGraphTests(unittest.TestCase):
    def graph(self, *, policy=R[1], closure="COMPLETE"):
        return build_graph(
            graph_id="demo", adapter_id="TEST", adapter_version="v0.1",
            adapter_policy_root=policy, schema_registry_root=R[4], trust_root=R[5],
            closure_claim=closure,
            nodes=[
                node("source", "INPUT", grade="DECLARED_INPUT"),
                node("evidence", "INPUT", grade="DECLARED_INPUT"),
                node("title", "SEMANTIC_PROJECT",
                     [("source", "SEMANTIC_PROJECTION", True)],
                     {"field_path": ["title"]}),
                node("check", "CHECK_FIELD", [("source", "EVIDENCE", True)],
                     {"field_path": ["ready"], "expected": {"present": True, "value": True},
                      "reason_code": "SOURCE_NOT_READY"},
                     grade="EXACT_INPUT_CHECK"),
                node("current", "CURRENT_USE", [("evidence", "FRESHNESS", True)],
                     {"expected_checkpoint_root": R[6]}, grade="EXACT_INPUT_CHECK"),
                node("prepare", "PREPARE", [("title", "SEMANTIC_PROJECTION", True),
                                               ("check", "EVIDENCE", True),
                                               ("current", "POLICY", True)],
                     {"preparation_id": "demo"},
                     grade="NON_AUTHORIZING_PREPARATION"),
            ])

    def snapshot(self, graph, *, title="A", ready=True, expires=100, predecessor=None):
        return build_snapshot(graph=graph, snapshot_id=f"snapshot:{title}:{ready}:{expires}",
            predecessor_snapshot_root=predecessor, observed_at_ns=10,
            inputs=[
                {"node_id": "source", "presence": {"present": True,
                    "value": {"title": title, "ready": ready, "nullable": None}}},
                {"node_id": "evidence", "presence": {"present": True,
                    "value": {"expires_at_ns": expires, "revoked": False,
                              "checkpoint_root": R[6]}}},
            ])

    def test_graph_snapshot_and_null_are_explicit_and_rebuild(self):
        graph = self.graph(); snapshot = self.snapshot(graph)
        self.assertEqual(verify_graph(graph)["status"], "PASS")
        self.assertEqual(verify_snapshot(snapshot, graph)["status"], "PASS")
        source = next(row for row in snapshot["inputs"] if row["node_id"] == "source")
        self.assertTrue(source["presence"]["present"])
        self.assertIsNone(source["presence"]["value"]["nullable"])

    def test_bool_and_integer_are_not_equal(self):
        graph = build_graph(graph_id="typed", adapter_id="TEST", adapter_version="v0.1",
            adapter_policy_root=R[0], schema_registry_root=R[1], trust_root=R[2],
            nodes=[node("a", "LITERAL", parameters={"value": {"x": True}}),
                   node("b", "LITERAL", parameters={"value": {"x": 1}}),
                   node("m", "MERGE_MAPS", [("a", "EXACT_BYTES", True),
                                              ("b", "EXACT_BYTES", True)])])
        snapshot = build_snapshot(graph=graph, snapshot_id="empty", inputs=[],
                                  predecessor_snapshot_root=None)
        with self.assertRaisesRegex(Refusal, "DEPENDENCY_MERGE_CONFLICT"):
            evaluate_graph(graph=graph, snapshot=snapshot)

    def test_sequential_delta_preserves_prior_change(self):
        graph = self.graph(); initial = self.snapshot(graph)
        first = apply_snapshot_delta(graph=graph, predecessor=initial,
            expected_predecessor_root=initial["snapshot_root"], delta_id="d1",
            updates=[{"node_id":"source", "presence":{"present":True,
                "value":{"title":"B", "ready":True, "nullable":None}}}],
            snapshot_id="s1")["snapshot"]
        second = apply_snapshot_delta(graph=graph, predecessor=first,
            expected_predecessor_root=first["snapshot_root"], delta_id="d2",
            updates=[{"node_id":"evidence", "presence":{"present":True,
                "value":{"expires_at_ns":200, "revoked":False,
                         "checkpoint_root":R[6]}}}], snapshot_id="s2")["snapshot"]
        values = {row["node_id"]: row["presence"]["value"] for row in second["inputs"]}
        self.assertEqual(values["source"]["title"], "B")
        self.assertEqual(values["evidence"]["expires_at_ns"], 200)

    def test_policy_changes_definition_and_invocation_identity(self):
        old = self.graph(policy=R[1]); new = self.graph(policy=R[7])
        self.assertNotEqual(old["graph_root"], new["graph_root"])
        old_source = next(row for row in old["nodes"] if row["node_id"] == "source")
        new_source = next(row for row in new["nodes"] if row["node_id"] == "source")
        self.assertEqual(old_source["definition_root"], new_source["definition_root"])
        old_eval = evaluate_graph(graph=old, snapshot=self.snapshot(old), now_ns=20)
        new_eval = evaluate_graph(graph=new, snapshot=self.snapshot(new), now_ns=20)
        self.assertNotEqual(old_eval["evaluation_root"], new_eval["evaluation_root"])

    def test_current_use_blocks_expired_or_failed_prerequisite(self):
        graph = self.graph(); snapshot = self.snapshot(graph, expires=10)
        evaluation = evaluate_graph(graph=graph, snapshot=snapshot, now_ns=20)
        results = {row["node_id"]: row for row in evaluation["results"]}
        self.assertEqual(results["current"]["status"], "BLOCKED_CURRENT_USE")
        self.assertEqual(results["prepare"]["status"], "BLOCKED_PREREQUISITE")
        self.assertFalse(evaluation["execution_performed"])

    def test_failed_check_blocks_preparation(self):
        graph = self.graph(); snapshot = self.snapshot(graph, ready=False)
        evaluation = evaluate_graph(graph=graph, snapshot=snapshot, now_ns=20)
        results = {row["node_id"]: row for row in evaluation["results"]}
        self.assertEqual(results["check"]["status"], "BLOCKED_CHECK_FAILED")
        self.assertEqual(results["prepare"]["status"], "BLOCKED_PREREQUISITE")

    def test_self_rooted_prior_is_not_admitted(self):
        graph = self.graph(); snapshot = self.snapshot(graph)
        evaluation = evaluate_graph(graph=graph, snapshot=snapshot, now_ns=20)
        receipt = build_producer_receipt(producer_root=R[0], graph=graph, snapshot=snapshot,
            evaluation=evaluation, execution_capsule_root=R[1], checker_root=R[2])
        with self.assertRaisesRegex(Refusal, "DEPENDENCY_PRIOR_EVALUATION_UNEXPECTED"):
            build_reuse_admission(graph=graph, snapshot=snapshot,
                prior_graph=graph, prior_snapshot=snapshot, prior_evaluation=evaluation,
                expected_prior_evaluation_root=R[8], expected_producer_root=R[0],
                producer_receipt=receipt, consumer_trust_root=R[5],
                admitted_evidence_grades=["DETERMINISTIC_DERIVATION"],
                reuse_mode="VERIFIED_PURE_REUSE")

    def test_verified_reuse_preserves_unaffected_outputs(self):
        graph = self.graph(); before_snapshot = self.snapshot(graph, title="A")
        before = evaluate_graph(graph=graph, snapshot=before_snapshot, now_ns=20)
        after_snapshot = apply_snapshot_delta(graph=graph, predecessor=before_snapshot,
            expected_predecessor_root=before_snapshot["snapshot_root"], delta_id="evidence-only",
            updates=[{"node_id":"evidence", "presence":{"present":True,
                "value":{"expires_at_ns":200,"revoked":False,"checkpoint_root":R[6]}}}],
            snapshot_id="after")["snapshot"]
        receipt = build_producer_receipt(producer_root=R[0], graph=graph,
            snapshot=before_snapshot, evaluation=before,
            execution_capsule_root=R[1], checker_root=R[2])
        admission = build_reuse_admission(graph=graph, snapshot=after_snapshot,
            prior_graph=graph, prior_snapshot=before_snapshot, prior_evaluation=before,
            expected_prior_evaluation_root=before["evaluation_root"],
            expected_producer_root=R[0], producer_receipt=receipt,
            consumer_trust_root=R[5], admitted_evidence_grades=[
                "DECLARED_INPUT", "DETERMINISTIC_DERIVATION", "EXACT_INPUT_CHECK",
                "NON_AUTHORIZING_PREPARATION"], reuse_mode="VERIFIED_PURE_REUSE")
        after = evaluate_graph(graph=graph, snapshot=after_snapshot, now_ns=20,
            prior_evaluation=before, reuse_admission=admission,
            expected_prior_evaluation_root=before["evaluation_root"],
            expected_producer_root=R[0],
            expected_producer_receipt_root=receipt["receipt_root"],
            expected_consumer_trust_root=R[5],
            mode="VERIFIED_PURE_REUSE")
        self.assertIn("title", after["partitions"]["reused"])
        self.assertNotIn("current", after["partitions"]["reused"])
        full = evaluate_graph(graph=graph, snapshot=after_snapshot, now_ns=20)
        self.assertEqual({r["node_id"]:r["output_root"] for r in after["results"]},
                         {r["node_id"]:r["output_root"] for r in full["results"]})

    def test_declared_closure_never_reuses(self):
        graph = self.graph(closure="DECLARED")
        snapshot = self.snapshot(graph)
        prior = evaluate_graph(graph=graph, snapshot=snapshot, now_ns=20)
        receipt = build_producer_receipt(
            producer_root=R[0], graph=graph, snapshot=snapshot,
            evaluation=prior, execution_capsule_root=R[1], checker_root=R[2])
        admission = build_reuse_admission(
            graph=graph, snapshot=snapshot, prior_graph=graph,
            prior_snapshot=snapshot, prior_evaluation=prior,
            expected_prior_evaluation_root=prior["evaluation_root"],
            expected_producer_root=R[0], producer_receipt=receipt,
            consumer_trust_root=R[5],
            admitted_evidence_grades=["DETERMINISTIC_DERIVATION"],
            reuse_mode="VERIFIED_PURE_REUSE")
        replay = evaluate_graph(
            graph=graph, snapshot=snapshot, now_ns=20,
            prior_evaluation=prior, reuse_admission=admission,
            expected_prior_evaluation_root=prior["evaluation_root"],
            expected_producer_root=R[0],
            expected_producer_receipt_root=receipt["receipt_root"],
            expected_consumer_trust_root=R[5],
            mode="VERIFIED_PURE_REUSE")
        self.assertEqual(graph["closure_claim"], "DECLARED")
        self.assertTrue(all(node["closure_coverage"] == "COMPLETE" for node in graph["nodes"]))
        self.assertEqual(replay["partitions"]["reused"], [])
        self.assertIn("title", replay["partitions"]["evaluated"])

    def test_reuse_rechecks_external_custody_anchors_at_point_of_use(self):
        graph = self.graph(); snapshot = self.snapshot(graph)
        prior = evaluate_graph(graph=graph, snapshot=snapshot, now_ns=20)
        receipt = build_producer_receipt(
            producer_root=R[0], graph=graph, snapshot=snapshot,
            evaluation=prior, execution_capsule_root=R[1], checker_root=R[2])
        admission = build_reuse_admission(
            graph=graph, snapshot=snapshot, prior_graph=graph,
            prior_snapshot=snapshot, prior_evaluation=prior,
            expected_prior_evaluation_root=prior["evaluation_root"],
            expected_producer_root=R[0], producer_receipt=receipt,
            consumer_trust_root=R[5],
            admitted_evidence_grades=["DETERMINISTIC_DERIVATION"],
            reuse_mode="VERIFIED_PURE_REUSE")
        common = dict(
            graph=graph, snapshot=snapshot, now_ns=20,
            prior_evaluation=prior, reuse_admission=admission,
            expected_prior_evaluation_root=prior["evaluation_root"],
            expected_producer_root=R[0],
            expected_producer_receipt_root=receipt["receipt_root"],
            expected_consumer_trust_root=R[5],
            mode="VERIFIED_PURE_REUSE")
        self.assertEqual(evaluate_graph(**common)["status"], "PASS")
        for field, replacement, code in (
            ("expected_prior_evaluation_root", R[8],
             "DEPENDENCY_PRIOR_EVALUATION_UNEXPECTED_AT_USE"),
            ("expected_producer_root", R[8],
             "DEPENDENCY_ADMISSION_PRODUCER_UNEXPECTED_AT_USE"),
            ("expected_producer_receipt_root", R[8],
             "DEPENDENCY_ADMISSION_RECEIPT_UNEXPECTED_AT_USE"),
            ("expected_consumer_trust_root", R[8],
             "DEPENDENCY_ADMISSION_TRUST_UNEXPECTED_AT_USE"),
        ):
            changed = dict(common); changed[field] = replacement
            with self.assertRaisesRegex(Refusal, code):
                evaluate_graph(**changed)

    def test_compare_explain_and_rebuild_oracle(self):
        graph = self.graph(); before_s = self.snapshot(graph, title="A")
        after_s = self.snapshot(graph, title="B", predecessor=before_s["snapshot_root"])
        before = evaluate_graph(graph=graph, snapshot=before_s, now_ns=20)
        after = evaluate_graph(graph=graph, snapshot=after_s, now_ns=20)
        impact = compare_evaluations(graph=graph, before=before, after=after)
        self.assertIn("title", impact["changed_output"])
        explanation = explain_node(graph=graph, evaluation=after, node_id="prepare")
        self.assertTrue(any(path[-1] == "source" for path in explanation["dependency_paths"]))
        self.assertEqual(verify_evaluation(graph=graph, snapshot=after_s,
                                           evaluation=after, now_ns=20)["status"], "PASS")

    def test_portable_closure_has_no_credentials(self):
        graph = self.graph(); snapshot = self.snapshot(graph)
        evaluation = evaluate_graph(graph=graph, snapshot=snapshot, now_ns=20)
        closure = build_portable_closure(profile="REPLAY", graph=graph, snapshot=snapshot,
            evaluation=evaluation, software_root=R[0], adapter_root=R[1],
            schema_roots=[R[2]], evidence_roots=[R[3]],
            members=[{"path":"GRAPH.json","sha256":R[4],"bytes":10,"role":"GRAPH"}])
        self.assertEqual(verify_portable_closure(closure)["status"], "PASS")
        self.assertFalse(closure["credentials_included"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from ucm.dependency_adapters import (
    assess_reuse_graduation, build_amcas_dependency_profile,
    build_architecture_trace, build_benchmark_report,
    build_c_dependency_envelope, build_compiler_proof_binding,
    build_content_reference_snapshot, build_governed_replan_set,
    build_dependency_aware_turn, build_development_check_plan,
    build_policy_pack_dependency_plan, compile_project_dependency_graph,
    build_storage_admission_indexes, capture_observation,
    dependency_adapter_registry, prepare_courthouse_dependency_binding,
    fold_dependency_journal_updates, project_dependency_observatory, project_effect_history,
    reconcile_dependency_turn,
)
from ucm.dependency_graph import build_graph, build_snapshot, evaluate_graph


R = [f"{i:x}" * 64 for i in range(1, 10)]


def node(node_id, kind, dependencies=(), parameters=None):
    return {"node_id":node_id,"kind":kind,"dependencies":[
        {"node_id":d,"edge_kind":k,"required":q} for d,k,q in dependencies],
        "parameters":parameters or {},"transform_id":kind,"transform_version":"v0.1",
        "semantic_contract_root":R[0],"policy_root":R[1],"jurisdiction_root":R[2],
        "environment_root":R[3],"closure_coverage":"COMPLETE",
        "evidence_grade":"DECLARED_INPUT" if kind=="INPUT" else "DETERMINISTIC_DERIVATION",
        "pure":True}


class DependencyAdapterTests(unittest.TestCase):
    def evaluation(self):
        graph=build_graph(graph_id="adapters",nodes=[node("input","INPUT"),
            node("project","PROJECT",[("input","EXACT_BYTES",True)],{"field_path":["x"]})],
            adapter_id="TEST",adapter_version="v0.1",adapter_policy_root=R[4],
            schema_registry_root=R[5],trust_root=R[6],closure_claim="COMPLETE")
        snapshot=build_snapshot(graph=graph,snapshot_id="s",inputs=[
            {"node_id":"input","presence":{"present":True,"value":{"x":1}}}],
            predecessor_snapshot_root=None)
        return graph,snapshot,evaluate_graph(graph=graph,snapshot=snapshot)

    def test_registry_names_domain_boundaries(self):
        registry=dependency_adapter_registry()
        self.assertGreaterEqual(len(registry["adapters"]),15)
        self.assertTrue(all(row["domain_validator_remains_authoritative"]
                            for row in registry["adapters"]))

    def test_project_content_and_replan_use_one_graph_core(self):
        compilation=compile_project_dependency_graph(project_root=R[0],nodes=[node("input","INPUT")],
            adapter_policy_root=R[1],schema_registry_root=R[2],trust_root=R[3],
            closure_claim="DECLARED")
        self.assertEqual(compilation["coverage"],"CONSERVATIVE")
        self.assertFalse(compilation["unknown_dependencies_promoted"])
        observed=build_content_reference_snapshot(graph=compilation["graph"],snapshot_id="refs",
            predecessor_snapshot_root=None,observed_references=[
                {"node_id":"input","presence":{"present":True,"value":{"path":"a"}}}])
        self.assertFalse(observed["unobserved_reference_closure_claimed"])
        evaluation=evaluate_graph(graph=compilation["graph"],snapshot=observed["snapshot"])
        impact={"schema":"mosaic.ucm.dependency-impact.v0.1","graph_root":compilation["graph"]["graph_root"],
            "before_evaluation_root":evaluation["evaluation_root"],"after_evaluation_root":evaluation["evaluation_root"],
            "changed_output":["input"],"changed_semantic":[],"changed_provenance":[],
            "unchanged":[],"blocked":[],"impact_root":R[4],"standing":"INFORMATION_ONLY",
            "authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}
        replan=build_governed_replan_set(impact=impact,node_to_work_packages={"input":["WP-1"]})
        self.assertEqual(replan["work_package_ids"],["WP-1"])
        self.assertFalse(replan["work_authorized"])

    def test_journal_fold_preserves_two_session_updates(self):
        graph=build_graph(graph_id="journal",nodes=[node("a","INPUT"),node("b","INPUT")],
            adapter_id="PIPPI_TURN",adapter_version="v0.1",adapter_policy_root=R[1],
            schema_registry_root=R[2],trust_root=R[3],closure_claim="COMPLETE")
        initial=build_snapshot(graph=graph,snapshot_id="initial",predecessor_snapshot_root=None,
            inputs=[{"node_id":key,"presence":{"present":True,"value":0}} for key in ("a","b")])
        # Compute the exact second expected head from the first lawful delta.
        first=fold_dependency_journal_updates(graph=graph,initial_snapshot=initial,
            expected_initial_head=initial["snapshot_root"],updates=[{"update_id":"A","expected_head":initial["snapshot_root"],
                "snapshot_id":"after-a","updates":[{"node_id":"a","presence":{"present":True,"value":1}}]}])
        result=fold_dependency_journal_updates(graph=graph,initial_snapshot=initial,
            expected_initial_head=initial["snapshot_root"],updates=[
                {"update_id":"A","expected_head":initial["snapshot_root"],"snapshot_id":"after-a",
                 "updates":[{"node_id":"a","presence":{"present":True,"value":1}}]},
                {"update_id":"B","expected_head":first["successor_snapshot"]["snapshot_root"],"snapshot_id":"after-b",
                 "updates":[{"node_id":"b","presence":{"present":True,"value":2}}]}])
        values={row["node_id"]:row["presence"]["value"] for row in result["successor_snapshot"]["inputs"]}
        self.assertEqual(values,{"a":1,"b":2})
        self.assertFalse(result["duplicate_advancement"])

    def test_policy_pack_plan_preserves_native_validation_and_needs_packs(self):
        plan=build_policy_pack_dependency_plan(contract_root=R[0],policy_pack_roots=[R[1]],
            component_requirement_roots=[R[2]],conflict_validation_root=None,packs_available=False)
        self.assertEqual(plan["status"],"NEEDS_PACKS")
        self.assertTrue(plan["native_conflict_validator_required"])
        self.assertFalse(plan["download_performed"])

    def test_pippi_turn_detects_graph_drift(self):
        opening={"turn_opening_root":R[0],"project_root":R[1],"journal_head":R[2]}
        item=build_dependency_aware_turn(opening=opening,graph_root=R[3],
            snapshot_root=R[4],evaluation_root=R[5],impact_root=None,
            injected_context=[{"context_id":"rule","text":"Exact rule text",
                "source_root":R[6],"reason_path":["input","rule"]}],stale_context_ids=[])
        good=reconcile_dependency_turn(dependency_opening=item,report_root=R[7],
            current_project_root=R[1],current_journal_head=R[2],current_graph_root=R[3],
            current_snapshot_root=R[4],current_evaluation_root=R[5])
        self.assertEqual(good["state"],"RECONCILED")
        drift=reconcile_dependency_turn(dependency_opening=item,report_root=R[7],
            current_project_root=R[1],current_journal_head=R[2],current_graph_root=R[8],
            current_snapshot_root=R[4],current_evaluation_root=R[5])
        self.assertEqual(drift["state"],"REFUSED_DRIFT")

    def test_observatory_uses_rooted_status_without_global_held(self):
        graph,snapshot,evaluation=self.evaluation()
        view=project_dependency_observatory(graph=graph,snapshot=snapshot,
            evaluation=evaluation,impact=None,view="HUMAN")
        self.assertEqual(view["summary"]["current"],2)
        self.assertNotIn("HELD", str(view))

    def test_amcas_profile_is_explicit_migration_when_unbound(self):
        item=build_amcas_dependency_profile(amcas_registry_root=R[0],
            application_id="MOSAIC.TEST",dependency_graph_root=None,adapter_id=None,
            closure_coverage="UNBOUND",migration_mode="COMPATIBILITY")
        self.assertEqual(item["status"],"MIGRATION_OR_ADAPTER_REQUIRED")
        self.assertTrue(item["native_authority_preserved"])

    def test_courthouse_binding_never_compiles_or_grants(self):
        _g,_s,evaluation=self.evaluation()
        binding=prepare_courthouse_dependency_binding(evaluation=evaluation,
            required_target_ids=["project"],workflow_request_root=R[0],
            acceptance_case_root=R[1],work_unit_root=R[2],native_validator_root=R[3])
        self.assertEqual(binding["status"],"READY_FOR_NATIVE_VALIDATION")
        self.assertFalse(binding["workflow_compiled"])
        self.assertFalse(binding["permit_created"])

    def test_effect_projection_refuses_automatic_retry(self):
        item=project_effect_history(operation_state={"state":"UNCERTAIN","state_root":R[0]},
                                    dependency_evaluation_root=R[1])
        self.assertTrue(item["reconciliation_required"])
        self.assertFalse(item["automatic_retry_selected"])

    def test_storage_indexes_do_not_turn_missing_bytes_into_reuse(self):
        item=build_storage_admission_indexes(admission_root=R[0],invocation_root=R[1],
            result_root=R[2],content_root=R[3],bytes_available=False,retention_root=R[4])
        self.assertFalse(item["reusable"])
        self.assertEqual(item["content_to_bytes"]["availability"],"UNAVAILABLE")

    def test_development_check_denominator_is_total_and_release_full(self):
        item=build_development_check_plan(evaluation_root=R[0],test_catalog_root=R[1],
            denominator=["A","B"],selected_test_ids=["A"],
            reuse_justifications=[{"test_id":"B","admission_root":R[2]}],
            release_candidate=True)
        self.assertTrue(item["full_cache_free_qualification_required"])
        self.assertFalse(item["release_qualified"])

    def test_compiler_and_proof_binding_requires_revalidation(self):
        item=build_compiler_proof_binding(kind="NATIVE_PROOF_CERTIFICATE",
            input_root=R[0],definition_root=R[1],checker_root=R[2],
            obligation_roots=[R[3]],result_root=R[4],validation_root=R[5],
            evidence_grade="EXACT_INPUT_CHECK")
        self.assertTrue(item["retrieval_requires_revalidation"])
        self.assertFalse(item["graph_reachability_is_proof"])

    def test_c_depfile_controls_reuse_eligibility(self):
        incomplete=build_c_dependency_envelope(source_root=R[0],header_roots=[R[1]],
            generated_input_roots=[],compiler_root=R[2],flags_root=R[3],toolchain_root=R[4],
            environment_root=R[5],depfile_root=None,external_evidence_roots=[])
        complete=build_c_dependency_envelope(source_root=R[0],header_roots=[R[1]],
            generated_input_roots=[],compiler_root=R[2],flags_root=R[3],toolchain_root=R[4],
            environment_root=R[5],depfile_root=R[6],external_evidence_roots=[])
        self.assertFalse(incomplete["reuse_eligible"])
        self.assertTrue(complete["reuse_eligible"])

    def test_architecture_similarity_never_establishes_equivalence(self):
        item=build_architecture_trace(requirement_root=R[0],implementation_roots=[R[1]],
            check_roots=[R[2]],evidence_roots=[R[3]],affected_application_ids=["APP"],
            candidate_relation_roots=[R[4]])
        self.assertFalse(item["semantic_equivalence_established"])
        self.assertTrue(item["human_or_domain_disposition_required"])

    def test_observation_retrieval_is_honest(self):
        item=capture_observation(request_root=R[0],result_root=R[1],observer_root=R[2],
            model_or_tool_root=R[3],mode="RECORDED_RETRIEVAL",observable_metadata={"host":"x"})
        self.assertFalse(item["fresh_execution"])
        self.assertFalse(item["hidden_reasoning_observed"])

    def test_benchmark_and_reuse_graduation_are_bounded(self):
        report=build_benchmark_report(graph_root=R[0],corpus_root=R[1],modes=[
            {"mode":mode,"output_root":R[2],"hash_ns":1,"walk_ns":2,
             "transform_ns":3,"retrieval_ns":4,"storage_bytes":5,
             "node_count":6,"edge_count":5,"change_count":1}
            for mode in ("UNCACHED","SHADOW_IMPACT","VERIFIED_PURE_REUSE")])
        graduated=assess_reuse_graduation(adapter_id="NATIVE_PROOF",
            closure_coverage="COMPLETE",conformance_root=R[3],
            benchmark_root=report["benchmark_root"],release_lane=False,identity_drift=False)
        self.assertEqual(graduated["selected_mode"],"VERIFIED_PURE_REUSE")
        release=assess_reuse_graduation(adapter_id="NATIVE_PROOF",
            closure_coverage="COMPLETE",conformance_root=R[3],
            benchmark_root=report["benchmark_root"],release_lane=True,identity_drift=False)
        self.assertEqual(release["selected_mode"],"SHADOW_IMPACT")


if __name__=="__main__":
    unittest.main()

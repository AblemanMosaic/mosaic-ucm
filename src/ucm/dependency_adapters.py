"""Pure adapters between the Dependency and Evidence Graph and UCM systems.

Adapters describe or project existing native records.  They do not replace the
native validator, create execution eligibility, perform downloads, dispatch an
operation, or convert graph reachability into proof.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .dependency_graph import (EVALUATION_SCHEMA, GRAPH_SCHEMA, IMPACT_SCHEMA,
                               PORTABLE_SCHEMA, SNAPSHOT_SCHEMA,
                               apply_snapshot_delta, build_graph, build_snapshot)


BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def _seal(body: dict[str, Any], field: str) -> dict[str, Any]:
    return {**deepcopy(body), field: root(body)}


ADAPTERS = (
    ("PROJECT_INTELLIGENCE", "STATIC_DECLARED_AND_OBSERVED", "SHADOW_IMPACT"),
    ("CONTENT_REFERENCE", "OBSERVED_REFERENCES_PARTIAL", "SHADOW_IMPACT"),
    ("INCREMENTAL_HOTFIX", "DECLARED_TEST_AND_COMPILATION_CLOSURE", "SHADOW_IMPACT"),
    ("PIPPI_TURN", "JOURNAL_AND_CONTEXT", "VERIFIED_PURE_REUSE"),
    ("AMCAS_BASELINE", "CONTRACT_AND_PARITY", "SHADOW_IMPACT"),
    ("COURTHOUSE_WORKFLOW_IR", "NATIVE_VALIDATOR_REQUIRED", "DISABLED"),
    ("OPERATIONAL_GATEWAY", "OBSERVATION_AND_RECOVERY_ONLY", "DISABLED"),
    ("TRANSTEMPORAL_CAS", "BYTES_AND_ADMISSION_INDEX", "VERIFIED_PURE_REUSE"),
    ("UCL_TESSERA", "PASS_AND_OBLIGATION_CLOSURE", "SHADOW_IMPACT"),
    ("NATIVE_PROOF", "CHECKER_BOUND_CERTIFICATE", "VERIFIED_PURE_REUSE"),
    ("C_DEPFILE", "COMPILER_REPORTED_DEPENDENCIES", "SHADOW_IMPACT"),
    ("EXTERNAL_SOFTWARE_EVIDENCE", "PRODUCER_ATTRIBUTED", "SHADOW_IMPACT"),
    ("POLICY_PACKS", "NATIVE_CONFLICT_VALIDATOR", "SHADOW_IMPACT"),
    ("ARCHITECTURE_TRACE", "CANDIDATE_RELATIONS_ONLY", "SHADOW_IMPACT"),
    ("CAPTURED_OBSERVATION", "OBSERVABLE_ONLY", "DISABLED"),
    ("UGEL_EXECUTOR", "EXTERNAL_RECEIPT_AND_EFFECT_CLOSURE", "DISABLED"),
)


def dependency_adapter_registry() -> dict[str, Any]:
    rows = []
    for adapter_id, coverage, default_mode in ADAPTERS:
        body = {
            "adapter_id": adapter_id, "coverage": coverage,
            "default_mode": default_mode,
            "domain_validator_remains_authoritative": True,
            "graph_grants_authority": False,
            "unknown_dependency_fallback": "FULL_RECOMPUTE",
        }
        rows.append({**body, "adapter_root": root(body)})
    body = {
        "schema": "mosaic.ucm.dependency-adapter-registry.v0.1",
        "adapters": rows,
        "rules": [
            "NATIVE_VALIDATOR_REMAINS_AUTHORITATIVE",
            "UNKNOWN_CLOSURE_FALLS_BACK_TO_FULL_RECOMPUTE",
            "CACHE_NEVER_REUSES_CURRENT_AUTHORITY",
            "GRAPH_REACHABILITY_IS_NOT_DEDUCTIVE_PROOF",
            "OBSERVATION_RETRIEVAL_IS_NOT_FRESH_EXECUTION",
        ],
        **BOUNDARY,
    }
    return _seal(body, "adapter_registry_root")


def compile_project_dependency_graph(*, project_root: str, nodes: list[dict[str, Any]],
                                     adapter_policy_root: str,
                                     schema_registry_root: str,
                                     trust_root: str,
                                     closure_claim: str) -> dict[str, Any]:
    """Compile Project Intelligence declarations into the one native graph core."""
    require_root(project_root)
    graph = build_graph(
        graph_id=f"project:{project_root}", nodes=nodes,
        adapter_id="PROJECT_INTELLIGENCE", adapter_version="v0.1",
        adapter_policy_root=adapter_policy_root,
        schema_registry_root=schema_registry_root, trust_root=trust_root,
        closure_claim=closure_claim)
    body = {
        "schema": "mosaic.ucm.project-dependency-graph-compilation.v0.1",
        "project_root": project_root, "graph": graph,
        "coverage": "CONSERVATIVE" if closure_claim != "COMPLETE" else "COMPLETE",
        "unknown_dependencies_promoted": False,
        **BOUNDARY,
    }
    return _seal(body, "project_dependency_compilation_root")


def build_content_reference_snapshot(*, graph: dict[str, Any], snapshot_id: str,
                                     predecessor_snapshot_root: str | None,
                                     observed_references: list[dict[str, Any]],
                                     observed_at_ns: int | None = None) -> dict[str, Any]:
    """Bind observed references as inputs without claiming unobserved closure."""
    snapshot = build_snapshot(
        graph=graph, snapshot_id=snapshot_id,
        predecessor_snapshot_root=predecessor_snapshot_root,
        inputs=observed_references, observed_at_ns=observed_at_ns)
    body = {
        "schema": "mosaic.ucm.content-reference-snapshot.v0.1",
        "graph_root": graph["graph_root"], "snapshot": snapshot,
        "reference_mode": "OBSERVED_ONLY",
        "unobserved_reference_closure_claimed": False,
        **BOUNDARY,
    }
    return _seal(body, "content_reference_snapshot_root")


def build_governed_replan_set(*, impact: dict[str, Any],
                              node_to_work_packages: dict[str, list[str]]) -> dict[str, Any]:
    """Project changed/blocked nodes into an exact, non-authorizing work set."""
    require(impact.get("schema") == IMPACT_SCHEMA, "DEPENDENCY_REPLAN_IMPACT_INVALID")
    require(type(node_to_work_packages) is dict, "DEPENDENCY_REPLAN_MAP_INVALID")
    affected = sorted(set(impact["changed_output"] + impact["changed_semantic"]
                          + impact["changed_provenance"] + impact["blocked"]))
    packages: set[str] = set()
    uncovered = []
    for node_id in affected:
        mapped = node_to_work_packages.get(node_id)
        if not mapped:
            uncovered.append(node_id); continue
        require(type(mapped) is list and all(type(item) is str and item for item in mapped),
                "DEPENDENCY_REPLAN_MAP_INVALID")
        packages.update(mapped)
    body = {
        "schema": "mosaic.ucm.dependency-replan-set.v0.1",
        "impact_root": impact["impact_root"], "affected_node_ids": affected,
        "work_package_ids": sorted(packages), "uncovered_node_ids": sorted(uncovered),
        "status": "READY" if not uncovered else "CONSERVATIVE_MANUAL_COVERAGE_REQUIRED",
        "work_authorized": False,
        **BOUNDARY,
    }
    return _seal(body, "replan_set_root")


def fold_dependency_journal_updates(*, graph: dict[str, Any],
                                    initial_snapshot: dict[str, Any],
                                    expected_initial_head: str,
                                    updates: list[dict[str, Any]]) -> dict[str, Any]:
    """Fold append-once session deltas while preserving every earlier update."""
    require(initial_snapshot.get("snapshot_root") == expected_initial_head,
            "DEPENDENCY_JOURNAL_EXPECTED_HEAD_MISMATCH")
    current = deepcopy(initial_snapshot); rows = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(updates):
        item = exact_keys(raw, {"update_id", "expected_head", "snapshot_id", "updates"},
                          f"$.updates[{index}]")
        require(type(item["update_id"]) is str and item["update_id"] not in seen_ids,
                "DEPENDENCY_JOURNAL_UPDATE_DUPLICATE")
        require(item["expected_head"] == current["snapshot_root"],
                "DEPENDENCY_JOURNAL_EXPECTED_HEAD_MISMATCH")
        result = apply_snapshot_delta(
            graph=graph, predecessor=current,
            expected_predecessor_root=item["expected_head"],
            delta_id=item["update_id"], updates=item["updates"],
            snapshot_id=item["snapshot_id"])
        current = result["snapshot"]; seen_ids.add(item["update_id"])
        rows.append({"update_id": item["update_id"],
                     "predecessor_root": item["expected_head"],
                     "successor_root": current["snapshot_root"],
                     "delta_root": result["delta"]["delta_root"]})
    body = {
        "schema": "mosaic.ucm.dependency-journal-fold.v0.1",
        "graph_root": graph["graph_root"], "initial_head": expected_initial_head,
        "updates": rows, "successor_snapshot": current,
        "append_once": True, "duplicate_advancement": False,
        **BOUNDARY,
    }
    return _seal(body, "journal_fold_root")


def build_policy_pack_dependency_plan(*, contract_root: str,
                                      policy_pack_roots: list[str],
                                      component_requirement_roots: list[str],
                                      conflict_validation_root: str | None,
                                      packs_available: bool) -> dict[str, Any]:
    """Describe policy/component impact while leaving composition to its native validator."""
    require_root(contract_root)
    for value in [*policy_pack_roots, *component_requirement_roots]: require_root(value)
    if conflict_validation_root is not None: require_root(conflict_validation_root)
    require(type(packs_available) is bool, "DEPENDENCY_PACK_AVAILABILITY_INVALID")
    status = "READY_FOR_NATIVE_VALIDATION" if packs_available else "NEEDS_PACKS"
    body = {
        "schema": "mosaic.ucm.policy-pack-dependency-plan.v0.1",
        "contract_root": contract_root,
        "policy_pack_roots": sorted(set(policy_pack_roots)),
        "component_requirement_roots": sorted(set(component_requirement_roots)),
        "conflict_validation_root": conflict_validation_root,
        "status": status, "native_conflict_validator_required": True,
        "download_performed": False, "install_performed": False,
        **BOUNDARY,
    }
    return _seal(body, "policy_pack_dependency_plan_root")


def build_dependency_aware_turn(*, opening: dict[str, Any], graph_root: str,
                                snapshot_root: str, evaluation_root: str,
                                impact_root: str | None,
                                injected_context: list[dict[str, Any]],
                                stale_context_ids: list[str]) -> dict[str, Any]:
    for value in (graph_root, snapshot_root, evaluation_root):
        require_root(value)
    if impact_root is not None:
        require_root(impact_root)
    require(type(opening) is dict and type(opening.get("turn_opening_root")) is str,
            "DEPENDENCY_TURN_OPENING_INVALID")
    rows = []
    for index, row in enumerate(injected_context):
        item = exact_keys(row, {"context_id", "text", "source_root", "reason_path"},
                          f"$.injected_context[{index}]")
        require(type(item["context_id"]) is str and item["context_id"],
                "DEPENDENCY_CONTEXT_ID_INVALID")
        require(type(item["text"]) is str, "DEPENDENCY_CONTEXT_TEXT_INVALID")
        require_root(item["source_root"])
        require(type(item["reason_path"]) is list and item["reason_path"],
                "DEPENDENCY_CONTEXT_REASON_INVALID")
        rows.append(deepcopy(item))
    rows.sort(key=lambda item: item["context_id"])
    require(len({row["context_id"] for row in rows}) == len(rows),
            "DEPENDENCY_CONTEXT_DUPLICATE")
    stale = sorted(set(stale_context_ids))
    require(all(type(item) is str and item for item in stale),
            "DEPENDENCY_STALE_CONTEXT_INVALID")
    body = {
        "schema": "mosaic.ucm.pippi-dependency-turn-opening.v0.1",
        "base_turn_opening_root": opening["turn_opening_root"],
        "project_root": opening.get("project_root"),
        "journal_head": opening.get("journal_head"),
        "graph_root": graph_root, "snapshot_root": snapshot_root,
        "evaluation_root": evaluation_root, "impact_root": impact_root,
        "injected_context": rows, "injected_context_root": root(rows),
        "stale_context_ids": stale,
        "turn_may_proceed": not stale,
        "capability_ceiling_unchanged": True,
        **BOUNDARY,
    }
    return _seal(body, "dependency_turn_opening_root")


def reconcile_dependency_turn(*, dependency_opening: dict[str, Any],
                              report_root: str, current_project_root: str,
                              current_journal_head: str | None,
                              current_graph_root: str,
                              current_snapshot_root: str,
                              current_evaluation_root: str) -> dict[str, Any]:
    for value in (report_root, current_project_root, current_graph_root,
                  current_snapshot_root, current_evaluation_root):
        require_root(value)
    if current_journal_head is not None:
        require_root(current_journal_head)
    require(type(dependency_opening) is dict and
            dependency_opening.get("schema") == "mosaic.ucm.pippi-dependency-turn-opening.v0.1",
            "DEPENDENCY_TURN_OPENING_INVALID")
    mismatches = []
    for name, actual in (("project_root", current_project_root),
                         ("journal_head", current_journal_head),
                         ("graph_root", current_graph_root),
                         ("snapshot_root", current_snapshot_root),
                         ("evaluation_root", current_evaluation_root)):
        if dependency_opening.get(name) != actual:
            mismatches.append(name.upper() + "_CHANGED_DURING_TURN")
    body = {
        "schema": "mosaic.ucm.pippi-dependency-turn-reconciliation.v0.1",
        "dependency_turn_opening_root": dependency_opening["dependency_turn_opening_root"],
        "report_root": report_root, "current_graph_root": current_graph_root,
        "current_snapshot_root": current_snapshot_root,
        "current_evaluation_root": current_evaluation_root,
        "state": "RECONCILED" if not mismatches else "REFUSED_DRIFT",
        "reason_codes": sorted(mismatches),
        "journal_append_authorized": False,
        **BOUNDARY,
    }
    return _seal(body, "dependency_turn_reconciliation_root")


def project_dependency_observatory(*, graph: dict[str, Any], snapshot: dict[str, Any],
                                   evaluation: dict[str, Any],
                                   impact: dict[str, Any] | None,
                                   view: str) -> dict[str, Any]:
    require(graph.get("schema") == GRAPH_SCHEMA and snapshot.get("schema") == SNAPSHOT_SCHEMA
            and evaluation.get("schema") == EVALUATION_SCHEMA,
            "DEPENDENCY_OBSERVATORY_BOUNDARY_INVALID")
    require(view in {"HUMAN", "AGENT", "FORENSIC"}, "DEPENDENCY_VIEW_INVALID")
    if impact is not None:
        require(impact.get("schema") == IMPACT_SCHEMA, "DEPENDENCY_IMPACT_INVALID")
    result_by_id = {row["node_id"]: row for row in evaluation["results"]}
    cards = []
    for node in graph["nodes"]:
        if node["node_id"] not in result_by_id:
            continue
        result = result_by_id[node["node_id"]]
        state = ("CURRENT" if result["status"] == "PASS" else
                 "STALE" if "EXPIRED" in " ".join(result["reason_codes"]) else
                 "BLOCKED")
        body = {
            "node_id": node["node_id"], "kind": node["kind"], "state": state,
            "status": result["status"], "reason_codes": result["reason_codes"],
            "needs_check": result["status"] != "PASS",
            "check_pointer": (f"dependency-explain:{node['node_id']}"
                              if result["status"] != "PASS" else None),
            "output_root": result["output_root"],
            "evaluation_action": result["evaluation_action"],
        }
        cards.append({**body, "card_root": root(body)})
    cards.sort(key=lambda row: row["node_id"])
    body = {
        "schema": "mosaic.ucm.dependency-observatory.v0.1",
        "view": view, "graph_root": graph["graph_root"],
        "snapshot_root": snapshot["snapshot_root"],
        "evaluation_root": evaluation["evaluation_root"],
        "impact_root": None if impact is None else impact["impact_root"],
        "summary": {
            "current": sum(row["state"] == "CURRENT" for row in cards),
            "stale": sum(row["state"] == "STALE" for row in cards),
            "blocked": sum(row["state"] == "BLOCKED" for row in cards),
            "unknown": sum(row["closure_coverage"] != "COMPLETE"
                           for row in graph["nodes"]),
            "unavailable": 0,
        },
        "cards": cards,
        "next_action_authorized": False,
        **BOUNDARY,
    }
    return _seal(body, "observatory_root")


def build_amcas_dependency_profile(*, amcas_registry_root: str,
                                   application_id: str,
                                   dependency_graph_root: str | None,
                                   adapter_id: str | None,
                                   closure_coverage: str,
                                   migration_mode: str) -> dict[str, Any]:
    require_root(amcas_registry_root)
    require(type(application_id) is str and application_id,
            "DEPENDENCY_AMCAS_APPLICATION_INVALID")
    require(closure_coverage in {"COMPLETE", "DECLARED", "INCOMPLETE", "UNBOUND"},
            "DEPENDENCY_AMCAS_CLOSURE_INVALID")
    require(migration_mode in {"NATIVE", "COMPATIBILITY", "REQUIRED"},
            "DEPENDENCY_AMCAS_MIGRATION_INVALID")
    if dependency_graph_root is not None:
        require_root(dependency_graph_root)
    if adapter_id is not None:
        require(type(adapter_id) is str and adapter_id,
                "DEPENDENCY_AMCAS_ADAPTER_INVALID")
    ready = (dependency_graph_root is not None and adapter_id is not None
             and closure_coverage == "COMPLETE")
    body = {
        "schema": "mosaic.amcas.dependency-evidence-profile.v0.1",
        "amcas_registry_root": amcas_registry_root,
        "element_id": "DEPENDENCY_EVIDENCE_GRAPH",
        "application_id": application_id,
        "dependency_graph_root": dependency_graph_root,
        "adapter_id": adapter_id, "closure_coverage": closure_coverage,
        "migration_mode": migration_mode,
        "status": "READY" if ready else "MIGRATION_OR_ADAPTER_REQUIRED",
        "native_authority_preserved": True,
        **BOUNDARY,
    }
    return _seal(body, "dependency_profile_root")


def prepare_courthouse_dependency_binding(*, evaluation: dict[str, Any],
                                          required_target_ids: list[str],
                                          workflow_request_root: str,
                                          acceptance_case_root: str,
                                          work_unit_root: str,
                                          native_validator_root: str) -> dict[str, Any]:
    for value in (workflow_request_root, acceptance_case_root, work_unit_root,
                  native_validator_root):
        require_root(value)
    require(evaluation.get("schema") == EVALUATION_SCHEMA,
            "DEPENDENCY_COURTHOUSE_EVALUATION_INVALID")
    results = {row["node_id"]: row for row in evaluation["results"]}
    targets = sorted(set(required_target_ids))
    require(targets and all(target in results for target in targets),
            "DEPENDENCY_COURTHOUSE_TARGET_INVALID")
    blocked = sorted(target for target in targets if results[target]["status"] != "PASS")
    body = {
        "schema": "mosaic.ucm.dependency-courthouse-binding.v0.1",
        "evaluation_root": evaluation["evaluation_root"],
        "required_target_ids": targets,
        "workflow_request_root": workflow_request_root,
        "acceptance_case_root": acceptance_case_root,
        "work_unit_root": work_unit_root,
        "native_validator_root": native_validator_root,
        "status": "READY_FOR_NATIVE_VALIDATION" if not blocked else "BLOCKED_PREREQUISITE",
        "blocked_target_ids": blocked,
        "native_validator_required": True,
        "workflow_compiled": False, "permit_created": False,
        "executor_selected": False,
        **BOUNDARY,
    }
    return _seal(body, "dependency_courthouse_binding_root")


def project_effect_history(*, operation_state: dict[str, Any],
                           dependency_evaluation_root: str) -> dict[str, Any]:
    require_root(dependency_evaluation_root)
    require(type(operation_state) is dict and type(operation_state.get("state")) is str,
            "DEPENDENCY_OPERATION_STATE_INVALID")
    state = operation_state["state"]
    uncertain = state == "UNCERTAIN"
    body = {
        "schema": "mosaic.ucm.dependency-effect-history-projection.v0.1",
        "operation_state_root": operation_state.get("state_root") or root(operation_state),
        "dependency_evaluation_root": dependency_evaluation_root,
        "operation_state": state,
        "mode": "OBSERVATION_ONLY",
        "dispatch_performed": False,
        "automatic_retry_selected": False,
        "reconciliation_required": uncertain,
        "next_surface": "RECONCILE_OPERATIONAL_OUTCOME" if uncertain else None,
        **BOUNDARY,
    }
    return _seal(body, "effect_history_projection_root")


def build_storage_admission_indexes(*, admission_root: str,
                                    invocation_root: str,
                                    result_root: str,
                                    content_root: str,
                                    bytes_available: bool,
                                    retention_root: str) -> dict[str, Any]:
    for value in (admission_root, invocation_root, result_root, content_root,
                  retention_root):
        require_root(value)
    require(type(bytes_available) is bool, "DEPENDENCY_AVAILABILITY_INVALID")
    body = {
        "schema": "mosaic.ucm.dependency-storage-indexes.v0.1",
        "invocation_to_result": {"invocation_root": invocation_root,
                                 "result_root": result_root,
                                 "admission_root": admission_root},
        "content_to_bytes": {"content_root": content_root,
                             "availability": "AVAILABLE" if bytes_available else "UNAVAILABLE",
                             "retention_root": retention_root},
        "reusable": bytes_available,
        "producer_identity_preserved": True,
        "jurisdiction_identity_preserved": True,
        **BOUNDARY,
    }
    return _seal(body, "storage_indexes_root")


def build_development_check_plan(*, evaluation_root: str,
                                 test_catalog_root: str,
                                 denominator: list[str],
                                 selected_test_ids: list[str],
                                 reuse_justifications: list[dict[str, Any]],
                                 release_candidate: bool) -> dict[str, Any]:
    require_root(evaluation_root); require_root(test_catalog_root)
    all_ids = sorted(set(denominator)); selected = sorted(set(selected_test_ids))
    require(all_ids and set(selected) <= set(all_ids), "DEPENDENCY_TEST_DENOMINATOR_INVALID")
    reused: dict[str, str] = {}
    for row in reuse_justifications:
        item = exact_keys(row, {"test_id", "admission_root"})
        require(item["test_id"] in all_ids and item["test_id"] not in selected,
                "DEPENDENCY_TEST_REUSE_INVALID")
        require_root(item["admission_root"])
        require(item["test_id"] not in reused, "DEPENDENCY_TEST_REUSE_DUPLICATE")
        reused[item["test_id"]] = item["admission_root"]
    missing = sorted(set(all_ids) - set(selected) - set(reused))
    require(not missing, "DEPENDENCY_TEST_COVERAGE_INCOMPLETE", detail=",".join(missing))
    body = {
        "schema": "mosaic.ucm.dependency-development-check-plan.v0.1",
        "evaluation_root": evaluation_root, "test_catalog_root": test_catalog_root,
        "denominator": all_ids, "selected_test_ids": selected,
        "reused_test_ids": sorted(reused),
        "reuse_admission_roots": [reused[key] for key in sorted(reused)],
        "release_candidate": release_candidate,
        "full_cache_free_qualification_required": release_candidate,
        "release_qualified": False,
        **BOUNDARY,
    }
    return _seal(body, "development_check_plan_root")


def build_compiler_proof_binding(*, kind: str, input_root: str,
                                 definition_root: str, checker_root: str,
                                 obligation_roots: list[str],
                                 result_root: str,
                                 validation_root: str | None,
                                 evidence_grade: str) -> dict[str, Any]:
    require(kind in {"UCL_TESSERA_PASS", "NATIVE_PROOF_CERTIFICATE"},
            "DEPENDENCY_COMPILER_PROOF_KIND_INVALID")
    for value in (input_root, definition_root, checker_root, result_root):
        require_root(value)
    for value in obligation_roots:
        require_root(value)
    if validation_root is not None:
        require_root(validation_root)
    require(evidence_grade in {"DETERMINISTIC_DERIVATION", "EXACT_INPUT_CHECK"},
            "DEPENDENCY_COMPILER_PROOF_GRADE_INVALID")
    body = {
        "schema": "mosaic.ucm.dependency-compiler-proof-binding.v0.1",
        "kind": kind, "input_root": input_root,
        "definition_root": definition_root, "checker_root": checker_root,
        "obligation_roots": sorted(set(obligation_roots)),
        "result_root": result_root, "validation_root": validation_root,
        "evidence_grade": evidence_grade,
        "retrieval_requires_revalidation": True,
        "graph_reachability_is_proof": False,
        **BOUNDARY,
    }
    return _seal(body, "compiler_proof_binding_root")


def build_c_dependency_envelope(*, source_root: str, header_roots: list[str],
                                generated_input_roots: list[str],
                                compiler_root: str, flags_root: str,
                                toolchain_root: str, environment_root: str,
                                depfile_root: str | None,
                                external_evidence_roots: list[str]) -> dict[str, Any]:
    for value in [source_root, compiler_root, flags_root, toolchain_root,
                  environment_root, *header_roots, *generated_input_roots,
                  *external_evidence_roots]:
        require_root(value)
    if depfile_root is not None:
        require_root(depfile_root)
    closure = "COMPLETE" if depfile_root is not None else "INCOMPLETE"
    body = {
        "schema": "mosaic.ucm.c-dependency-envelope.v0.1",
        "source_root": source_root, "header_roots": sorted(set(header_roots)),
        "generated_input_roots": sorted(set(generated_input_roots)),
        "compiler_root": compiler_root, "flags_root": flags_root,
        "toolchain_root": toolchain_root, "environment_root": environment_root,
        "depfile_root": depfile_root, "closure_coverage": closure,
        "external_evidence_roots": sorted(set(external_evidence_roots)),
        "external_tools_executed_by_ucm": False,
        "reuse_eligible": closure == "COMPLETE",
        **BOUNDARY,
    }
    return _seal(body, "c_dependency_envelope_root")


def build_architecture_trace(*, requirement_root: str,
                             implementation_roots: list[str],
                             check_roots: list[str], evidence_roots: list[str],
                             affected_application_ids: list[str],
                             candidate_relation_roots: list[str]) -> dict[str, Any]:
    for value in [requirement_root, *implementation_roots, *check_roots,
                  *evidence_roots, *candidate_relation_roots]:
        require_root(value)
    applications = sorted(set(affected_application_ids))
    require(all(type(item) is str and item for item in applications),
            "DEPENDENCY_ARCHITECTURE_APPLICATION_INVALID")
    body = {
        "schema": "mosaic.ucm.dependency-architecture-trace.v0.1",
        "requirement_root": requirement_root,
        "implementation_roots": sorted(set(implementation_roots)),
        "check_roots": sorted(set(check_roots)),
        "evidence_roots": sorted(set(evidence_roots)),
        "affected_application_ids": applications,
        "candidate_relation_roots": sorted(set(candidate_relation_roots)),
        "semantic_equivalence_established": False,
        "human_or_domain_disposition_required": bool(candidate_relation_roots),
        **BOUNDARY,
    }
    return _seal(body, "architecture_trace_root")


def capture_observation(*, request_root: str, result_root: str,
                        observer_root: str, model_or_tool_root: str,
                        mode: str, observable_metadata: dict[str, Any]) -> dict[str, Any]:
    for value in (request_root, result_root, observer_root, model_or_tool_root):
        require_root(value)
    require(mode in {"FRESH_CAPTURE", "RECORDED_RETRIEVAL"},
            "DEPENDENCY_OBSERVATION_MODE_INVALID")
    require(type(observable_metadata) is dict, "DEPENDENCY_OBSERVATION_METADATA_INVALID")
    body = {
        "schema": "mosaic.ucm.dependency-observation.v0.1",
        "request_root": request_root, "result_root": result_root,
        "observer_root": observer_root, "model_or_tool_root": model_or_tool_root,
        "mode": mode, "observable_metadata": deepcopy(observable_metadata),
        "fresh_execution": mode == "FRESH_CAPTURE",
        "deterministic_rerun_claim": False,
        "hidden_reasoning_observed": False,
        "semantic_approval_inferred": False,
        **BOUNDARY,
    }
    return _seal(body, "observation_root")


def assess_reuse_graduation(*, adapter_id: str, closure_coverage: str,
                            conformance_root: str | None,
                            benchmark_root: str | None,
                            release_lane: bool,
                            identity_drift: bool) -> dict[str, Any]:
    known = {row[0] for row in ADAPTERS}
    require(adapter_id in known, "DEPENDENCY_REUSE_ADAPTER_UNKNOWN")
    require(closure_coverage in {"COMPLETE", "DECLARED", "INCOMPLETE"},
            "DEPENDENCY_REUSE_CLOSURE_INVALID")
    for value in (conformance_root, benchmark_root):
        if value is not None:
            require_root(value)
    eligible = (closure_coverage == "COMPLETE" and conformance_root is not None
                and benchmark_root is not None and not identity_drift and not release_lane)
    mode = "VERIFIED_PURE_REUSE" if eligible else "SHADOW_IMPACT"
    reason = []
    if release_lane: reason.append("RELEASE_REQUIRES_FULL_CACHE_FREE_QUALIFICATION")
    if closure_coverage != "COMPLETE": reason.append("DEPENDENCY_CLOSURE_NOT_COMPLETE")
    if conformance_root is None: reason.append("CONFORMANCE_NOT_SUPPLIED")
    if benchmark_root is None: reason.append("BENCHMARK_NOT_SUPPLIED")
    if identity_drift: reason.append("IDENTITY_DRIFT")
    body = {
        "schema": "mosaic.ucm.dependency-reuse-graduation.v0.1",
        "adapter_id": adapter_id, "closure_coverage": closure_coverage,
        "conformance_root": conformance_root, "benchmark_root": benchmark_root,
        "release_lane": release_lane, "identity_drift": identity_drift,
        "selected_mode": mode, "reason_codes": sorted(reason),
        "full_rebuild_available": True,
        "release_qualification_reused": False,
        **BOUNDARY,
    }
    return _seal(body, "reuse_graduation_root")


def build_benchmark_report(*, graph_root: str, corpus_root: str,
                           modes: list[dict[str, Any]]) -> dict[str, Any]:
    require_root(graph_root); require_root(corpus_root)
    normalized = []
    expected_output_root = None
    for index, raw in enumerate(modes):
        item = exact_keys(raw, {"mode", "output_root", "hash_ns", "walk_ns",
                                "transform_ns", "retrieval_ns", "storage_bytes",
                                "node_count", "edge_count", "change_count"},
                          f"$.modes[{index}]")
        require(item["mode"] in {"UNCACHED", "SHADOW_IMPACT", "VERIFIED_PURE_REUSE"},
                "DEPENDENCY_BENCHMARK_MODE_INVALID")
        require_root(item["output_root"])
        for key in ("hash_ns", "walk_ns", "transform_ns", "retrieval_ns",
                    "storage_bytes", "node_count", "edge_count", "change_count"):
            require(type(item[key]) is int and item[key] >= 0,
                    "DEPENDENCY_BENCHMARK_MEASURE_INVALID", f"$.modes[{index}].{key}")
        if expected_output_root is None:
            expected_output_root = item["output_root"]
        require(item["output_root"] == expected_output_root,
                "DEPENDENCY_BENCHMARK_OUTPUT_DIVERGED")
        normalized.append(deepcopy(item))
    normalized.sort(key=lambda row: row["mode"])
    require({row["mode"] for row in normalized} ==
            {"UNCACHED", "SHADOW_IMPACT", "VERIFIED_PURE_REUSE"},
            "DEPENDENCY_BENCHMARK_DENOMINATOR_INVALID")
    body = {
        "schema": "mosaic.ucm.dependency-benchmark-report.v0.1",
        "graph_root": graph_root, "corpus_root": corpus_root,
        "modes": normalized, "semantic_output_root": expected_output_root,
        "resource_denominators_separate": True,
        "optimization_authorized": False,
        **BOUNDARY,
    }
    return _seal(body, "benchmark_root")


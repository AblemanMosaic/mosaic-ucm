"""Pre-registered comparative evaluation contracts for UCM claims."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from uclop.canonical import exact_keys, require, require_root, root

from .system import BOUNDARY


REQUIRED_ARMS = {"BASELINE", "CONVENTIONAL_ENFORCEMENT", "UCM_GOVERNED"}
REQUIRED_METRICS = {
    "ARCHITECTURAL_VIOLATIONS", "REVIEW_REPAIR_TIME", "UNRELATED_CHANGE_RATE",
    "FALSE_REFUSAL_RATE", "CONTRACT_AUTHORING_TIME", "FOLLOW_ON_DRIFT",
}
EXECUTION_CONTEXT_FIELDS = {
    "model_id_root", "model_settings_root", "executor_session_root",
    "environment_root", "toolchain_root",
}
SCORING_CONTEXT_FIELDS = {"scorer_identity_root", "scorer_session_root"}
SHARED_EXECUTION_CONTEXT_FIELDS = {
    "model_id_root", "model_settings_root", "environment_root", "toolchain_root",
}


def validate_execution_context_registration(protocol: Any, value: Any) -> dict[str, Any]:
    study = validate_study_protocol(protocol)
    item = exact_keys(value, {"schema", "study_root", *SHARED_EXECUTION_CONTEXT_FIELDS,
                              "allowed_deviations", "status", "standing",
                              "authority_effect", "real_a5", "g0",
                              "registration_root"})
    require(item["schema"] == "mosaic.ucm.architecture-study-execution-context.v0.1",
            "UCM_STUDY_CONTEXT_SCHEMA_INVALID")
    require(item["study_root"] == study["study_root"],
            "UCM_STUDY_CONTEXT_BINDING_INVALID")
    for field in SHARED_EXECUTION_CONTEXT_FIELDS:
        require_root(item[field])
    require(item["allowed_deviations"] == []
            and item["status"] == "REGISTERED_BEFORE_KIT_ISSUANCE"
            and {key: item[key] for key in BOUNDARY} == BOUNDARY,
            "UCM_STUDY_CONTEXT_NOT_FIXED")
    body = {key: deepcopy(raw) for key, raw in item.items()
            if key != "registration_root"}
    require(item["registration_root"] == root(body),
            "UCM_STUDY_CONTEXT_ROOT_INVALID")
    return deepcopy(item)


def validate_study_protocol(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "study_id", "claim", "tasks", "arms",
                                    "metrics", "runs_per_task", "model_policy",
                                    "review_policy", "artifact_policy",
                                    "follow_on_task_root", "study_root"})
    require(item["schema"] == "mosaic.ucm.architecture-study.v0.2",
            "UCM_STUDY_SCHEMA_INVALID")
    require(type(item["study_id"]) is str and item["study_id"]
            and type(item["claim"]) is str and item["claim"], "UCM_STUDY_ID_INVALID")
    require(type(item["tasks"]) is list and len(item["tasks"]) >= 1,
            "UCM_STUDY_TASKS_INVALID")
    task_ids = []
    for task in item["tasks"]:
        row = exact_keys(task, {"task_id", "subject_root", "task_root", "difficulty",
                                "architectural_obligation_roots"})
        task_ids.append(row["task_id"])
        require(type(row["task_id"]) is str and row["task_id"]
                and row["difficulty"] in {"EASY", "MEDIUM", "HARD"},
                "UCM_STUDY_TASK_INVALID")
        require_root(row["subject_root"]); require_root(row["task_root"])
        require(type(row["architectural_obligation_roots"]) is list
                and bool(row["architectural_obligation_roots"]),
                "UCM_STUDY_TASK_INVALID")
        for obligation_root in row["architectural_obligation_roots"]:
            require_root(obligation_root)
    require(len(task_ids) == len(set(task_ids)), "UCM_STUDY_TASK_DUPLICATE")
    require(type(item["arms"]) is list, "UCM_STUDY_ARMS_INVALID")
    arm_ids = set()
    for arm in item["arms"]:
        row = exact_keys(arm, {"arm_id", "context_root", "enforcement_profile",
                               "human_oversight_policy_root",
                               "treatment_contract_root"})
        arm_ids.add(row["arm_id"])
        require(row["arm_id"] in REQUIRED_ARMS, "UCM_STUDY_ARM_INVALID")
        require_root(row["context_root"]); require_root(row["human_oversight_policy_root"])
        require_root(row["treatment_contract_root"])
        require(type(row["enforcement_profile"]) is str and row["enforcement_profile"],
                "UCM_STUDY_ARM_INVALID")
    require(arm_ids == REQUIRED_ARMS and len(item["arms"]) == len(REQUIRED_ARMS),
            "UCM_STUDY_ARMS_INCOMPLETE")
    require(type(item["metrics"]) is list and set(item["metrics"]) >= REQUIRED_METRICS
            and len(item["metrics"]) == len(set(item["metrics"])),
            "UCM_STUDY_METRICS_INCOMPLETE")
    require(type(item["runs_per_task"]) is int and item["runs_per_task"] >= 2,
            "UCM_STUDY_POWER_INVALID")
    for key in ("model_policy", "review_policy", "artifact_policy"):
        require(type(item[key]) is dict and bool(item[key]), "UCM_STUDY_POLICY_INVALID")
    model_policy = item["model_policy"]
    require(model_policy.get("matched_model") is True
            and model_policy.get("matched_settings") is True
            and model_policy.get("matched_environment") is True
            and model_policy.get("matched_toolchain") is True
            and model_policy.get("unique_executor_sessions") is True
            and model_policy.get("temperature_policy") == "FIXED_AND_RECORDED"
            and model_policy.get("context_registration_required_before_kit_issuance") is True
            and set(model_policy.get("required_execution_context_roots", []))
                == EXECUTION_CONTEXT_FIELDS,
            "UCM_STUDY_MODEL_POLICY_INCOMPLETE")
    review_policy = item["review_policy"]
    require(review_policy.get("blind_condition_where_feasible") is True
            and review_policy.get("independent_scorers_required") is True
            and review_policy.get("pre_registered_rubric") is True
            and review_policy.get("unique_scorer_sessions") is True
            and review_policy.get("executor_scorer_session_separation_required") is True
            and set(review_policy.get("required_scoring_context_roots", []))
                == SCORING_CONTEXT_FIELDS,
            "UCM_STUDY_REVIEW_POLICY_INCOMPLETE")
    require_root(review_policy.get("scoring_rubric_root"))
    require_root(item["follow_on_task_root"])
    artifact_policy = item["artifact_policy"]
    require(artifact_policy.get("public_subjects_only") is True
            and set(artifact_policy.get("capture", [])) == {
                "PROMPT", "CONTEXT", "ACTIONS", "DIFF", "TESTS", "REVIEW",
                "REPAIRS", "JOURNAL", "RECEIPTS", "FOLLOW_ON_RESULT"}
            and artifact_policy.get("follow_on_required") is True,
            "UCM_STUDY_ARTIFACT_POLICY_INCOMPLETE")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "study_root"}
    require(item["study_root"] == root(body), "UCM_STUDY_ROOT_INVALID")
    return deepcopy(item)


def build_run_roster(protocol: Any) -> dict[str, Any]:
    item = validate_study_protocol(protocol)
    arms = sorted(row["arm_id"] for row in item["arms"])
    runs = []
    for task_index, task in enumerate(sorted(item["tasks"], key=lambda row: row["task_id"])):
        for repetition in range(item["runs_per_task"]):
            for offset, arm_id in enumerate(arms):
                body = {"study_root": item["study_root"], "task_id": task["task_id"],
                        "task_root": task["task_root"], "repetition": repetition + 1,
                        "arm_id": arm_id,
                        "counterbalance_order": (task_index + repetition + offset) % len(arms)}
                runs.append({**body, "run_id": root(body)})
    runs.sort(key=lambda row: (row["task_id"], row["repetition"],
                               row["counterbalance_order"], row["arm_id"]))
    body = {"schema": "mosaic.ucm.architecture-study-roster.v0.1",
            "study_root": item["study_root"], "denominator": len(runs), "runs": runs,
            "status": "PLANNED_NOT_EXECUTED",
            "non_claims": ["NOT_A_STUDY_RESULT", "NOT_EVIDENCE_OF_BENEFIT"], **BOUNDARY}
    return {**body, "roster_root": root(body)}


def validate_run_result(protocol: Any, value: Any,
                        context_registration: Any) -> dict[str, Any]:
    study = validate_study_protocol(protocol)
    registered = validate_execution_context_registration(study, context_registration)
    roster = build_run_roster(study)
    item = exact_keys(value, {"schema", "study_root", "run_id", "task_root",
        "arm_id", "repetition", "model_id_root", "model_settings_root",
        "executor_session_root", "environment_root", "toolchain_root",
        "execution_context_root", "human_oversight_policy_root", "output_root",
        "scorer_identity_root", "scorer_session_root", "scoring_rubric_root",
        "scoring_context_root", "review_record_root", "follow_on_result_root",
        "context_registration_root", "metrics", "status", "result_root"})
    require(item["schema"] == "mosaic.ucm.architecture-study-run-result.v0.3",
            "UCM_STUDY_RESULT_SCHEMA_INVALID")
    expected = next((row for row in roster["runs"] if row["run_id"] == item["run_id"]), None)
    require(expected is not None, "UCM_STUDY_RUN_NOT_REGISTERED")
    require(item["study_root"] == study["study_root"]
            and item["task_root"] == expected["task_root"]
            and item["arm_id"] == expected["arm_id"]
            and item["repetition"] == expected["repetition"],
            "UCM_STUDY_RUN_BINDING_MISMATCH")
    arm = next(row for row in study["arms"] if row["arm_id"] == item["arm_id"])
    require(item["human_oversight_policy_root"] == arm["human_oversight_policy_root"],
            "UCM_STUDY_OVERSIGHT_MISMATCH")
    require(item["context_registration_root"] == registered["registration_root"],
            "UCM_STUDY_CONTEXT_REGISTRATION_MISMATCH")
    for field in SHARED_EXECUTION_CONTEXT_FIELDS:
        require(item[field] == registered[field], "UCM_STUDY_MATCHED_CONTEXT_MISMATCH",
                detail=field)
    for key in (EXECUTION_CONTEXT_FIELDS | SCORING_CONTEXT_FIELDS | {
            "execution_context_root", "output_root", "scoring_rubric_root",
            "scoring_context_root", "review_record_root", "follow_on_result_root"}):
        require_root(item[key])
    execution_context = {key: item[key] for key in sorted(EXECUTION_CONTEXT_FIELDS)}
    require(item["execution_context_root"] == root(execution_context),
            "UCM_STUDY_EXECUTION_CONTEXT_INVALID")
    review_policy = study["review_policy"]
    require(item["scoring_rubric_root"] == review_policy["scoring_rubric_root"],
            "UCM_STUDY_SCORING_RUBRIC_MISMATCH")
    scoring_context = {
        "review_record_root": item["review_record_root"],
        "scorer_identity_root": item["scorer_identity_root"],
        "scorer_session_root": item["scorer_session_root"],
        "scoring_rubric_root": item["scoring_rubric_root"],
    }
    require(item["scoring_context_root"] == root(scoring_context)
            and item["executor_session_root"] != item["scorer_session_root"],
            "UCM_STUDY_SCORING_CONTEXT_INVALID")
    require(type(item["metrics"]) is dict
            and set(item["metrics"]) == set(study["metrics"])
            and all(type(metric) is int and type(metric) is not bool and metric >= 0
                    for metric in item["metrics"].values()),
            "UCM_STUDY_METRICS_INVALID")
    require(item["status"] == "COMPLETE", "UCM_STUDY_RUN_INCOMPLETE")
    body = {key: deepcopy(raw) for key, raw in item.items() if key != "result_root"}
    require(item["result_root"] == root(body), "UCM_STUDY_RESULT_ROOT_INVALID")
    return deepcopy(item)


def aggregate_study_results(protocol: Any, results: Any,
                            context_registration: Any) -> dict[str, Any]:
    study = validate_study_protocol(protocol)
    registered = validate_execution_context_registration(study, context_registration)
    roster = build_run_roster(study)
    require(type(results) is list, "UCM_STUDY_RESULTS_INVALID")
    verified = [validate_run_result(study, value, registered) for value in results]
    require(len(verified) == roster["denominator"], "UCM_STUDY_DENOMINATOR_INCOMPLETE")
    by_id = {row["run_id"]: row for row in verified}
    require(len(by_id) == len(verified)
            and set(by_id) == {row["run_id"] for row in roster["runs"]},
            "UCM_STUDY_RUN_SET_MISMATCH")
    for field in ("model_id_root", "model_settings_root", "environment_root",
                  "toolchain_root"):
        require(len({row[field] for row in verified}) == 1,
                "UCM_STUDY_MATCHED_CONTEXT_MISMATCH", detail=field)
    require(len({row["executor_session_root"] for row in verified}) == len(verified),
            "UCM_STUDY_EXECUTOR_SESSION_REUSED")
    require(len({row["scorer_session_root"] for row in verified}) == len(verified),
            "UCM_STUDY_SCORER_SESSION_REUSED")
    arms = []
    for arm_id in sorted(REQUIRED_ARMS):
        selected = [row for row in verified if row["arm_id"] == arm_id]
        totals = {metric: sum(row["metrics"][metric] for row in selected)
                  for metric in study["metrics"]}
        arms.append({"arm_id": arm_id, "runs": len(selected), "metric_totals": totals,
                     "result_set_root": root(sorted(row["result_root"] for row in selected))})
    body = {"schema": "mosaic.ucm.architecture-study-aggregate.v0.1",
            "study_root": study["study_root"], "roster_root": roster["roster_root"],
            "denominator": roster["denominator"],
            "matched_model_id_root": verified[0]["model_id_root"],
            "matched_model_settings_root": verified[0]["model_settings_root"],
            "matched_environment_root": verified[0]["environment_root"],
            "matched_toolchain_root": verified[0]["toolchain_root"],
            "executor_session_set_root": root(sorted(
                row["executor_session_root"] for row in verified)),
            "scorer_session_set_root": root(sorted(
                row["scorer_session_root"] for row in verified)),
            "scoring_rubric_root": study["review_policy"]["scoring_rubric_root"],
            "arms": arms,
            "status": "OBSERVED_NOT_CAUSAL_CONCLUSION",
            "non_claims": ["NOT_STATISTICAL_SIGNIFICANCE", "NOT_GENERALIZED_BENEFIT",
                           "NOT_DEPLOYMENT_AUTHORITY"], **BOUNDARY}
    return {**body, "aggregate_root": root(body)}

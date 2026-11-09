"""Finalize the exact six-run Track C denominator through the frozen UCM runtime."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile


BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
ROOT_RE = re.compile(r"[0-9a-f]{64}")
CAPTURE_REQUIRED = {
    "RUN-OUTPUT.json", "ACTIONS.json", "DIFF.patch", "TESTS.json", "OUTPUT.zip",
    "REVIEW.md", "REPAIRS.json", "JOURNAL.json", "RECEIPTS.json",
    "FOLLOW-ON-RESULT.json",
}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise SystemExit("STUDY_FINALIZE_JSON_DUPLICATE_KEY")
            result[key] = value
        return result
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              ValueError("non-finite:" + value)))
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit("STUDY_FINALIZE_JSON_INVALID") from error


def exact_rooted(value: object, required: set[str], root_field: str,
                 diagnostic: str) -> dict:
    if type(value) is not dict or set(value) != required:
        raise SystemExit(diagnostic)
    body = {key: item for key, item in value.items() if key != root_field}
    if (type(value.get(root_field)) is not str
            or not ROOT_RE.fullmatch(value[root_field])
            or value[root_field] != sha(canonical(body))):
        raise SystemExit(diagnostic)
    return value


def boundary_holds(value: dict) -> bool:
    return all(value.get(key) == expected for key, expected in BOUNDARY.items())


def rooted(body: dict, field: str) -> dict:
    return {**body, field: sha(canonical(body))}


def verify(verifier: Path, archive: Path, schema: str, role: str) -> None:
    result = subprocess.run([sys.executable, str(verifier), str(archive),
        "--schema", schema, "--role", role], capture_output=True, text=True)
    if result.returncode:
        raise SystemExit("STUDY_FINALIZE_ARCHIVE_VERIFY_FAILED:" + result.stderr.strip())


def deterministic_zip(payloads: dict[str, bytes]) -> bytes:
    rows = [{"path": name, "bytes": len(raw), "sha256": sha(raw)}
            for name, raw in sorted(payloads.items())]
    body = {"schema": "mosaic.ucm.architecture-study-result-package.v0.1",
            "artifact_role": "ARCHITECTURE_STUDY_RESULT_PACKAGE", "files": rows,
            **BOUNDARY}
    all_files = {**payloads, "MANIFEST.json": canonical(rooted(body, "manifest_root"))}
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(all_files.items()):
            info = zipfile.ZipInfo(name, FIXED_TIME); info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    return output.getvalue()


def finalize(package: Path, runtime: Path, returns: Path, scores: Path,
             mapping_path: Path, verifier: Path, output: Path) -> dict:
    verify(verifier, package, "mosaic.ucm.architecture-study-package.v0.1",
           "ARCHITECTURE_STUDY_PACKAGE")
    verify(verifier, runtime, "mosaic.ucm.maturity-canonical-software.v0.1",
           "UCM_MATURITY_CANONICAL_SOFTWARE")
    if output.exists() and any(output.iterdir()):
        raise SystemExit("STUDY_FINALIZE_OUTPUT_NOT_EMPTY")
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package) as coordinator:
        inventory_raw = coordinator.read("STUDY-KIT-INVENTORY.json")
        roster_raw = coordinator.read("STUDY-ROSTER.json")
        protocol_raw = coordinator.read("STUDY-PROTOCOL.json")
        context_registration_raw = coordinator.read("EXECUTION-CONTEXT-REGISTRATION.json")
    inventory = strict_json(inventory_raw)
    roster = strict_json(roster_raw)
    protocol = strict_json(protocol_raw)
    context_registration = strict_json(context_registration_raw)
    exact_rooted(context_registration, {
        "schema", "study_root", "model_id_root", "model_settings_root",
        "environment_root", "toolchain_root", "allowed_deviations", "status",
        "standing", "authority_effect", "real_a5", "g0", "registration_root",
    }, "registration_root", "STUDY_FINALIZE_CONTEXT_REGISTRATION_INVALID")
    if (context_registration.get("schema")
            != "mosaic.ucm.architecture-study-execution-context.v0.1"
            or context_registration.get("study_root") != protocol.get("study_root")
            or context_registration.get("allowed_deviations") != []
            or context_registration.get("status") != "REGISTERED_BEFORE_KIT_ISSUANCE"
            or not boundary_holds(context_registration)):
        raise SystemExit("STUDY_FINALIZE_CONTEXT_REGISTRATION_INVALID")
    exact_rooted(inventory, {
        "schema", "study_root", "roster_root", "context_registration_root",
        "follow_on_task_root", "denominator", "runs", "status",
        "standing", "authority_effect", "real_a5", "g0", "non_claims",
        "inventory_root"}, "inventory_root", "STUDY_FINALIZE_INVENTORY_INVALID")
    exact_rooted(roster, {
        "schema", "study_root", "denominator", "runs", "status", "non_claims",
        "standing", "authority_effect", "real_a5", "g0", "roster_root"},
        "roster_root", "STUDY_FINALIZE_ROSTER_INVALID")
    if (inventory.get("schema") != "mosaic.ucm.architecture-study-kit-inventory.v0.2"
            or roster.get("schema") != "mosaic.ucm.architecture-study-roster.v0.1"
            or inventory.get("study_root") != roster.get("study_root")
            or inventory.get("context_registration_root") != context_registration.get("registration_root")
            or inventory.get("follow_on_task_root") != protocol.get("follow_on_task_root")
            or inventory.get("roster_root") != roster.get("roster_root")
            or inventory.get("denominator") != 6
            or roster.get("denominator") != 6
            or type(inventory.get("runs")) is not list
            or type(roster.get("runs")) is not list
            or len(inventory["runs"]) != 6
            or len(roster["runs"]) != 6
            or not boundary_holds(inventory)
            or not boundary_holds(roster)):
        raise SystemExit("STUDY_FINALIZE_INVENTORY_ROSTER_MISMATCH")
    inventory_row_keys = {"run_id", "task_id", "arm_id", "repetition",
                          "archive", "bytes", "sha256"}
    roster_row_keys = {"study_root", "task_id", "task_root", "repetition",
                       "arm_id", "counterbalance_order", "run_id"}
    if (any(type(row) is not dict or set(row) != inventory_row_keys
            or type(row.get("bytes")) is not int or type(row["bytes"]) is bool
            or row["bytes"] <= 0 or type(row.get("sha256")) is not str
            or not ROOT_RE.fullmatch(row["sha256"])
            for row in inventory["runs"])
            or any(type(row) is not dict or set(row) != roster_row_keys
                   or row.get("study_root") != roster["study_root"]
                   for row in roster["runs"])):
        raise SystemExit("STUDY_FINALIZE_INVENTORY_ROSTER_INVALID")
    mapping_raw = mapping_path.read_bytes()
    mapping = exact_rooted(strict_json(mapping_raw), {
        "schema", "study_root", "roster_root", "denominator", "mappings",
        "status", "non_claims", "standing", "authority_effect", "real_a5",
        "g0", "mapping_root"}, "mapping_root",
        "STUDY_FINALIZE_SCORING_MAP_INVALID")
    if (mapping.get("schema") != "mosaic.ucm.architecture-study-scoring-coordinator-map.v0.1"
            or mapping.get("study_root") != inventory.get("study_root")
            or mapping.get("roster_root") != inventory.get("roster_root")
            or mapping.get("denominator") != 6
            or type(mapping.get("mappings")) is not list
            or len(mapping["mappings"]) != 6
            or mapping.get("status") != "READY_FOR_BLINDED_SCORING"
            or not boundary_holds(mapping)):
        raise SystemExit("STUDY_FINALIZE_SCORING_MAP_INVALID")
    inventory_by_run = {row["run_id"]: row for row in inventory["runs"]}
    roster_by_run = {row["run_id"]: row for row in roster["runs"]}
    if set(inventory_by_run) != set(roster_by_run):
        raise SystemExit("STUDY_FINALIZE_ROSTER_INVENTORY_MISMATCH")
    by_run = {}
    for run_id, inventory_row in inventory_by_run.items():
        roster_row = roster_by_run[run_id]
        if any(inventory_row[key] != roster_row[key]
               for key in ("run_id", "task_id", "arm_id", "repetition")):
            raise SystemExit("STUDY_FINALIZE_ROSTER_INVENTORY_MISMATCH")
        by_run[run_id] = {**inventory_row, **roster_row}
    mapping_keys = {"score_id", "run_id", "execution_return_sha256",
                    "execution_return_root", "scoring_kit", "scoring_kit_sha256"}
    if any(type(row) is not dict or set(row) != mapping_keys
           or any(type(row.get(field)) is not str or not ROOT_RE.fullmatch(row[field])
                  for field in ("score_id", "execution_return_sha256",
                                "execution_return_root", "scoring_kit_sha256"))
           or type(row.get("run_id")) is not str
           or type(row.get("scoring_kit")) is not str
           for row in mapping["mappings"]):
        raise SystemExit("STUDY_FINALIZE_SCORING_MAP_INVALID")
    mappings = {row["score_id"]: row for row in mapping["mappings"]}
    if len(by_run) != 6 or len(mappings) != 6:
        raise SystemExit("STUDY_FINALIZE_DENOMINATOR_INVALID")
    execution_rows = {}
    execution_payloads = {}
    for path in sorted(returns.glob("*.zip")):
        verify(verifier, path, "mosaic.ucm.architecture-study-execution-return.v0.1",
               "ARCHITECTURE_STUDY_EXECUTION_RETURN")
        raw = path.read_bytes()
        with zipfile.ZipFile(path) as archive:
            record = strict_json(archive.read("EXECUTION-RETURN.json"))
            output_record = strict_json(archive.read("capture/RUN-OUTPUT.json"))
            run_kit = archive.read("RUN-KIT.zip")
            capture = {name.removeprefix("capture/"): archive.read(name)
                       for name in archive.namelist() if name.startswith("capture/")}
        run_id = record.get("run_id")
        if run_id not in by_run or run_id in execution_rows:
            raise SystemExit("STUDY_FINALIZE_EXECUTION_SET_INVALID")
        with zipfile.ZipFile(io.BytesIO(run_kit)) as run_archive:
            run_assignment = strict_json(run_archive.read("ASSIGNMENT.json"))
            task = strict_json(run_archive.read("TASK.json"))
        exact_rooted(record, {
            "schema", "run_id", "assignment_root", "run_kit_sha256",
            "output_record_root", "capture_root", "capture", "status",
            "arm_label_disclosed", "non_claims", "standing", "authority_effect",
            "real_a5", "g0", "return_root"}, "return_root",
            "STUDY_FINALIZE_EXECUTION_RECORD_INVALID")
        exact_rooted(output_record, {
            "schema", "run_id", "task_root", "model_id_root",
            "model_settings_root", "executor_session_root", "environment_root",
            "toolchain_root", "execution_context_root", "output_root",
            "actions_root", "tests_root", "follow_on_result_root",
            "context_registration_root", "elapsed_seconds", "notes",
            "output_record_root"}, "output_record_root",
            "STUDY_FINALIZE_EXECUTION_RECORD_INVALID")
        exact_rooted(run_assignment, {
            "schema", "run_id", "task_root", "repetition",
            "condition_context_root", "human_oversight_policy_root",
            "treatment_contract_root", "context_registration_root",
            "follow_on_task_root", "standing", "authority_effect",
            "real_a5", "g0", "assignment_root"},
            "assignment_root", "STUDY_FINALIZE_EXECUTION_RECORD_INVALID")
        registered = by_run[run_id]
        if set(capture) != CAPTURE_REQUIRED:
            raise SystemExit("STUDY_FINALIZE_EXECUTION_CAPTURE_INVALID")
        actions = strict_json(capture["ACTIONS.json"])
        tests = strict_json(capture["TESTS.json"])
        for name in ("REPAIRS.json", "JOURNAL.json", "RECEIPTS.json"):
            strict_json(capture[name])
        follow_on = strict_json(capture["FOLLOW-ON-RESULT.json"])
        capture_rows = [{"path": name, "bytes": len(raw), "sha256": sha(raw)}
                        for name, raw in sorted(capture.items())]
        arm = next((row for row in protocol["arms"]
                    if row["arm_id"] == registered["arm_id"]), None)
        if (record.get("schema") != "mosaic.ucm.architecture-study-execution-return-record.v0.1"
                or record.get("status") != "EXECUTION_COMPLETE_UNSCORED"
                or record.get("arm_label_disclosed") is not False
                or not boundary_holds(record)
                or output_record.get("schema") != "mosaic.ucm.architecture-study-raw-run-output.v0.3"
                or run_assignment.get("schema") != "mosaic.ucm.architecture-study-assignment.v0.2"
                or not boundary_holds(run_assignment)
                or sha(run_kit) != registered["sha256"]
                or record.get("run_kit_sha256") != registered["sha256"]
                or record.get("assignment_root") != run_assignment["assignment_root"]
                or record.get("output_record_root") != output_record["output_record_root"]
                or run_assignment.get("run_id") != run_id
                or output_record.get("run_id") != run_id
                or run_assignment.get("task_root") != registered["task_root"]
                or output_record.get("task_root") != registered["task_root"]
                or task.get("task_root") != registered["task_root"]
                or run_assignment.get("repetition") != registered["repetition"]
                or arm is None
                or run_assignment.get("condition_context_root") != arm["context_root"]
                or run_assignment.get("human_oversight_policy_root")
                    != arm["human_oversight_policy_root"]
                or run_assignment.get("treatment_contract_root")
                    != arm["treatment_contract_root"]
                or run_assignment.get("context_registration_root")
                    != context_registration["registration_root"]
                or run_assignment.get("follow_on_task_root")
                    != protocol["follow_on_task_root"]
                or record.get("capture") != capture_rows
                or record.get("capture_root") != sha(canonical(capture_rows))
                or output_record.get("output_root") != sha(capture["OUTPUT.zip"])
                or output_record.get("actions_root") != sha(canonical(actions))
                or output_record.get("tests_root") != sha(canonical(tests))
                or output_record.get("follow_on_result_root")
                    != sha(canonical(follow_on))
                or output_record.get("context_registration_root")
                    != context_registration["registration_root"]
                or any(type(output_record.get(field)) is not str
                       or not ROOT_RE.fullmatch(output_record[field])
                       for field in ("model_id_root", "model_settings_root",
                                     "executor_session_root", "environment_root",
                                     "toolchain_root", "execution_context_root",
                                     "output_root", "actions_root", "tests_root",
                                     "follow_on_result_root", "context_registration_root"))
                or output_record.get("execution_context_root") != sha(canonical({
                    key: output_record[key] for key in (
                        "environment_root", "executor_session_root", "model_id_root",
                        "model_settings_root", "toolchain_root")}))
                or type(output_record.get("elapsed_seconds")) is not int
                or type(output_record["elapsed_seconds"]) is bool
                or output_record["elapsed_seconds"] < 0
                or type(output_record.get("notes")) is not list
                or any(type(note) is not str for note in output_record["notes"])
                or not capture["REVIEW.md"]):
            raise SystemExit("STUDY_FINALIZE_EXECUTION_BINDING_MISMATCH")
        execution_rows[run_id] = (record, output_record, sha(raw))
        execution_payloads[f"execution-returns/{run_id}.zip"] = raw
    score_rows = {}
    score_payloads = {}
    for path in sorted(scores.glob("*.zip")):
        verify(verifier, path, "mosaic.ucm.architecture-study-score-return.v0.1",
               "ARCHITECTURE_STUDY_SCORE_RETURN")
        raw = path.read_bytes()
        with zipfile.ZipFile(path) as archive:
            assignment = strict_json(archive.read("SCORING-ASSIGNMENT.json"))
            score = strict_json(archive.read("SCORE.json"))
            record = strict_json(archive.read("SCORE-RETURN.json"))
            review_raw = archive.read("SCORING-REVIEW.md")
        score_id = record.get("score_id")
        if score_id not in mappings or score_id in score_rows:
            raise SystemExit("STUDY_FINALIZE_SCORE_SET_INVALID")
        exact_rooted(assignment, {
            "schema", "score_id", "study_root", "task_root",
            "execution_return_sha256", "execution_return_root", "metric_names",
            "executor_session_root", "scoring_rubric_root",
            "independence_policy_root", "blinded", "standing",
            "authority_effect", "real_a5", "g0",
            "scoring_assignment_root"}, "scoring_assignment_root",
            "STUDY_FINALIZE_SCORE_RECORD_INVALID")
        exact_rooted(score, {
            "schema", "score_id", "metrics", "notes", "scorer_identity_root",
            "scorer_session_root", "scoring_rubric_root",
            "independence_policy_root", "review_record_root",
            "scoring_context_root", "score_record_root"},
                     "score_record_root", "STUDY_FINALIZE_SCORE_RECORD_INVALID")
        exact_rooted(record, {
            "schema", "score_id", "scoring_assignment_root",
            "execution_return_root", "score_record_root", "review_record_root",
            "scorer_identity_root", "scorer_session_root", "scoring_rubric_root",
            "scoring_context_root", "status", "arm_label_disclosed", "standing",
            "authority_effect", "real_a5", "g0", "score_return_root"},
            "score_return_root",
            "STUDY_FINALIZE_SCORE_RECORD_INVALID")
        review_policy = protocol.get("review_policy", {})
        independence_policy_root = sha(canonical(review_policy))
        scoring_context = {key: score.get(key) for key in (
            "review_record_root", "scorer_identity_root", "scorer_session_root",
            "scoring_rubric_root")}
        if (assignment.get("schema") != "mosaic.ucm.architecture-study-scoring-assignment.v0.1"
                or assignment.get("blinded") is not True
                or not boundary_holds(assignment)
                or score.get("schema") != "mosaic.ucm.architecture-study-score.v0.2"
                or record.get("schema") != "mosaic.ucm.architecture-study-score-return-record.v0.1"
                or record.get("status") != "SCORE_COMPLETE_BLINDED"
                or record.get("arm_label_disclosed") is not False
                or not boundary_holds(record)
                or score.get("score_id") != score_id
                or assignment.get("score_id") != score_id
                or score.get("review_record_root") != sha(review_raw)
                or assignment.get("scoring_rubric_root")
                    != review_policy.get("scoring_rubric_root")
                or assignment.get("independence_policy_root")
                    != independence_policy_root
                or score.get("scoring_rubric_root")
                    != assignment.get("scoring_rubric_root")
                or score.get("independence_policy_root")
                    != assignment.get("independence_policy_root")
                or score.get("scoring_context_root") != sha(canonical(scoring_context))
                or score.get("scorer_session_root")
                    == assignment.get("executor_session_root")
                or record.get("review_record_root") != score.get("review_record_root")
                or record.get("score_record_root") != score.get("score_record_root")
                or record.get("scoring_assignment_root") != assignment.get("scoring_assignment_root")
                or any(record.get(field) != score.get(field) for field in (
                    "scorer_identity_root", "scorer_session_root",
                    "scoring_rubric_root", "scoring_context_root"))
                or assignment.get("score_id") != sha(canonical({
                    "study_root": assignment.get("study_root"),
                    "execution_return_root": assignment.get("execution_return_root"),
                    "task_root": assignment.get("task_root")}))
                or type(score.get("metrics")) is not dict
                or set(score["metrics"]) != set(protocol["metrics"])
                or set(assignment.get("metric_names", [])) != set(protocol["metrics"])
                or any(type(value) is not int or type(value) is bool or value < 0
                       for value in score["metrics"].values())
                or type(score.get("notes")) is not list
                or any(type(note) is not str for note in score["notes"])
                or any(type(score.get(field)) is not str
                       or not ROOT_RE.fullmatch(score[field]) for field in (
                           "scorer_identity_root", "scorer_session_root",
                           "scoring_rubric_root", "independence_policy_root",
                           "review_record_root", "scoring_context_root"))
                or not review_raw):
            raise SystemExit("STUDY_FINALIZE_SCORE_BINDING_MISMATCH")
        score_rows[score_id] = (assignment, score, record, sha(raw))
        score_payloads[f"score-returns/{score_id}.zip"] = raw
    if len(execution_rows) != 6 or len(score_rows) != 6:
        raise SystemExit("STUDY_FINALIZE_DENOMINATOR_INCOMPLETE")
    temp = Path(tempfile.mkdtemp(prefix="ucm-track-c-runtime-"))
    try:
        with zipfile.ZipFile(runtime) as archive:
            archive.extractall(temp)
        sys.path[:0] = [str(temp), str(temp / "src")]
        from uclop.canonical import root
        from ucm.evaluation import aggregate_study_results, validate_run_result
        results = []
        for score_id, map_row in sorted(mappings.items()):
            run_id = map_row["run_id"]
            execution, output_record, execution_sha = execution_rows[run_id]
            assignment, score, score_return, score_sha = score_rows[score_id]
            if (execution_sha != map_row["execution_return_sha256"]
                    or execution["return_root"] != map_row["execution_return_root"]
                    or assignment["score_id"] != score_id
                    or assignment["study_root"] != protocol["study_root"]
                    or assignment["task_root"] != by_run[run_id]["task_root"]
                    or assignment["execution_return_sha256"] != execution_sha
                    or assignment["execution_return_root"] != execution["return_root"]
                    or assignment["executor_session_root"]
                        != output_record["executor_session_root"]
                    or score_return["scoring_assignment_root"] != assignment["scoring_assignment_root"]
                    or score_return["execution_return_root"] != execution["return_root"]
                    or score_return["score_record_root"] != score["score_record_root"]
                    or score_return["review_record_root"] != score["review_record_root"]):
                raise SystemExit("STUDY_FINALIZE_CROSS_RECORD_MISMATCH")
            registered = by_run[run_id]
            arm = next(row for row in protocol["arms"]
                       if row["arm_id"] == registered["arm_id"])
            body = {
                "schema": "mosaic.ucm.architecture-study-run-result.v0.3",
                "study_root": protocol["study_root"], "run_id": run_id,
                "task_root": registered["task_root"], "arm_id": registered["arm_id"],
                "repetition": registered["repetition"],
                "model_id_root": output_record["model_id_root"],
                "model_settings_root": output_record["model_settings_root"],
                "executor_session_root": output_record["executor_session_root"],
                "environment_root": output_record["environment_root"],
                "toolchain_root": output_record["toolchain_root"],
                "execution_context_root": output_record["execution_context_root"],
                "human_oversight_policy_root": arm["human_oversight_policy_root"],
                "output_root": output_record["output_root"],
                "scorer_identity_root": score["scorer_identity_root"],
                "scorer_session_root": score["scorer_session_root"],
                "scoring_rubric_root": score["scoring_rubric_root"],
                "scoring_context_root": score["scoring_context_root"],
                "review_record_root": score["review_record_root"],
                "follow_on_result_root": output_record["follow_on_result_root"],
                "context_registration_root": context_registration["registration_root"],
                "metrics": score["metrics"], "status": "COMPLETE",
            }
            result = {**body, "result_root": root(body)}
            results.append(validate_run_result(protocol, result, context_registration))
        aggregate = aggregate_study_results(protocol, results, context_registration)
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    results.sort(key=lambda row: row["run_id"])
    results_raw = canonical(results)
    aggregate_raw = canonical(aggregate)
    final_body = {
        "schema": "mosaic.ucm.architecture-study-finalization.v0.1",
        "study_root": protocol["study_root"], "roster_root": aggregate["roster_root"],
        "denominator": 6, "result_set_root": sha(results_raw),
        "aggregate_root": aggregate["aggregate_root"],
        "status": "OBSERVED_NOT_CAUSAL_CONCLUSION",
        "non_claims": ["NOT_STATISTICAL_SIGNIFICANCE", "NOT_GENERALIZED_BENEFIT",
                       "NOT_DEPLOYMENT_AUTHORITY"], **BOUNDARY,
    }
    final_record = rooted(final_body, "finalization_root")
    payloads = {
        "STUDY-KIT-INVENTORY.json": inventory_raw, "STUDY-ROSTER.json": roster_raw,
        "STUDY-PROTOCOL.json": protocol_raw,
        "EXECUTION-CONTEXT-REGISTRATION.json": context_registration_raw,
        "COORDINATOR-SCORING-MAP.json": mapping_raw,
        "RUN-RESULTS.json": results_raw, "STUDY-AGGREGATE.json": aggregate_raw,
        "FINALIZATION-RECORD.json": canonical(final_record),
        "FINALIZE-STUDY-RESULTS.py": Path(__file__).read_bytes(),
        **execution_payloads, **score_payloads,
    }
    archive = deterministic_zip(payloads)
    (output / "UCM-ARCHITECTURE-STUDY-C3-RESULTS.zip").write_bytes(archive)
    (output / "RUN-RESULTS.json").write_bytes(results_raw)
    (output / "STUDY-AGGREGATE.json").write_bytes(aggregate_raw)
    (output / "FINALIZATION-RECORD.json").write_bytes(canonical(final_record))
    return {"status": aggregate["status"], "denominator": 6,
            "aggregate_root": aggregate["aggregate_root"],
            "finalization_root": final_record["finalization_root"],
            "archive_sha256": sha(archive), **BOUNDARY}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--returns", type=Path, required=True)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--verifier", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(finalize(args.package.resolve(), args.runtime.resolve(),
                              args.returns.resolve(), args.scores.resolve(),
                              args.mapping.resolve(), args.verifier.resolve(),
                              args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

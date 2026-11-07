"""Bind the pre-registered architecture study to exact pilot materials."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uclop.canonical import canonical_bytes, root, strict_loads
from ucm.artifacts import deterministic_zip

ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = ROOT / "evaluation" / "tasks" / "reference-data-client"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _load(path: Path):
    return strict_loads(path.read_bytes())


def _source_record(directory: Path) -> dict:
    files = []
    for path in sorted(item for item in directory.rglob("*") if item.is_file()
                       and "__pycache__" not in item.parts
                       and item.suffix.casefold() not in {".pyc", ".pyo"}):
        raw = path.read_bytes()
        files.append({"path": path.relative_to(directory).as_posix(),
                      "bytes": len(raw), "sha256": _sha(raw)})
    body = {"schema": "mosaic.ucm.architecture-study-subject.v0.1",
            "files": files, "file_count": len(files),
            "logical_bytes": sum(row["bytes"] for row in files)}
    return {**body, "subject_root": root(body)}


def finalize_assets(workspace: Path = ROOT) -> dict:
    task_dir = workspace / "evaluation" / "tasks" / "reference-data-client"
    subject_dir = task_dir / "subject"
    source = _source_record(subject_dir)
    payloads = {row["path"]: (subject_dir / row["path"]).read_bytes()
                for row in source["files"]}
    payloads["SOURCE.json"] = canonical_bytes(source)
    subject_archive = deterministic_zip(
        payloads, schema="mosaic.ucm.architecture-study-subject-archive.v0.1",
        artifact_role="ARCHITECTURE_STUDY_SUBJECT")
    (task_dir / "SUBJECT.zip").write_bytes(subject_archive)

    prompt_raw = (task_dir / "TASK-PROMPT.md").read_bytes()
    architecture_raw = (task_dir / "ARCHITECTURE-CONTRACT.json").read_bytes()
    rubric_raw = (task_dir / "SCORING-RUBRIC.json").read_bytes()
    rubric = _load(task_dir / "SCORING-RUBRIC.json")
    architecture = _load(task_dir / "ARCHITECTURE-CONTRACT.json")
    architecture_obligation_root = root(architecture)
    task_body = {
        "schema": "mosaic.ucm.architecture-study-task.v0.1",
        "task_id": "REFERENCE_DATA_CLIENT.CACHE.001",
        "difficulty": "MEDIUM",
        "subject_root": source["subject_root"],
        "subject_archive_sha256": _sha(subject_archive),
        "prompt_sha256": _sha(prompt_raw),
        "architecture_contract_sha256": _sha(architecture_raw),
        "scoring_rubric_sha256": _sha(rubric_raw),
        "architectural_obligation_roots": [architecture_obligation_root],
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        "real_a5": False, "g0": "CLOSED",
    }
    task = {**task_body, "task_root": root(task_body)}
    (task_dir / "TASK.json").write_bytes(canonical_bytes(task))

    contexts = _load(task_dir / "ARM-CONTEXTS.json")
    rooted_arms = []
    for row in contexts["arms"]:
        arm_body = {"arm_id": row["arm_id"], "context": row["context"]}
        rooted_arms.append({**arm_body, "context_root": root(row["context"])})
    contexts_body = {key: value for key, value in contexts.items()
                     if key not in {"arms", "contexts_root"}}
    rooted_contexts_body = {**contexts_body, "arms": rooted_arms}
    rooted_contexts = {**rooted_contexts_body,
                       "contexts_root": root(rooted_contexts_body)}
    (task_dir / "ARM-CONTEXTS.json").write_bytes(canonical_bytes(rooted_contexts))

    oversight = _load(workspace / "evaluation" / "HUMAN-OVERSIGHT-POLICY.json")
    oversight_root = root(oversight)
    protocol_path = workspace / "evaluation" / "ARCHITECTURE-COMPLIANCE-STUDY.json"
    protocol = _load(protocol_path)
    protocol["study_id"] = "UCM.ARCHITECTURE_COMPLIANCE.C2"
    protocol["tasks"] = [{"task_id": task["task_id"],
                          "subject_root": task["subject_root"],
                          "task_root": task["task_root"],
                          "difficulty": task["difficulty"],
                          "architectural_obligation_roots": task["architectural_obligation_roots"]}]
    protocol["model_policy"] = {
        "matched_model": True,
        "matched_settings": True,
        "matched_environment": True,
        "matched_toolchain": True,
        "unique_executor_sessions": True,
        "temperature_policy": "FIXED_AND_RECORDED",
        "required_execution_context_roots": [
            "environment_root", "executor_session_root", "model_id_root",
            "model_settings_root", "toolchain_root",
        ],
    }
    protocol["review_policy"] = {
        "blind_condition_where_feasible": True,
        "independent_scorers_required": True,
        "pre_registered_rubric": True,
        "unique_scorer_sessions": True,
        "executor_scorer_session_separation_required": True,
        "required_scoring_context_roots": [
            "scorer_identity_root", "scorer_session_root",
        ],
        "scoring_rubric_root": root(rubric),
    }
    contexts_by_arm = {row["arm_id"]: row for row in rooted_arms}
    protocol["arms"] = [{**arm, "context_root": contexts_by_arm[arm["arm_id"]]["context_root"],
                          "human_oversight_policy_root": oversight_root}
                         for arm in protocol["arms"]]
    protocol["study_root"] = root({key: value for key, value in protocol.items()
                                    if key != "study_root"})
    protocol_path.write_bytes(canonical_bytes(protocol))
    return {"status": "PASS", "task_root": task["task_root"],
            "subject_root": task["subject_root"],
            "study_root": protocol["study_root"],
            "subject_archive_sha256": _sha(subject_archive),
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


if __name__ == "__main__":
    import json
    print(json.dumps(finalize_assets(), sort_keys=True, separators=(",", ":")))

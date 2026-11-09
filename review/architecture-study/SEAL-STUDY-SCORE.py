"""Seal one independently authored, blinded Track C score return."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile


BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
ROOT_RE = re.compile(r"[0-9a-f]{64}")


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw: bytes):
    seen_error = "STUDY_SCORE_JSON_DUPLICATE_KEY"
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise SystemExit(seen_error)
            value[key] = item
        return value
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              ValueError("non-finite:" + value)))
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit("STUDY_SCORE_JSON_INVALID") from error


def rooted(body: dict, field: str) -> dict:
    return {**body, field: sha(canonical(body))}


def deterministic_zip(payloads: dict[str, bytes]) -> bytes:
    rows = [{"path": name, "bytes": len(raw), "sha256": sha(raw)}
            for name, raw in sorted(payloads.items())]
    body = {"schema": "mosaic.ucm.architecture-study-score-return.v0.1",
            "artifact_role": "ARCHITECTURE_STUDY_SCORE_RETURN", "files": rows,
            **BOUNDARY}
    all_files = {**payloads, "MANIFEST.json": canonical(rooted(body, "manifest_root"))}
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(all_files.items()):
            info = zipfile.ZipInfo(name, FIXED_TIME); info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    return output.getvalue()


def seal(assignment_path: Path, score_path: Path, review_path: Path,
         output: Path) -> dict:
    assignment_raw = assignment_path.read_bytes()
    score_raw = score_path.read_bytes()
    review_raw = review_path.read_bytes()
    if not review_raw:
        raise SystemExit("STUDY_SCORE_REVIEW_EMPTY")
    assignment = strict_json(assignment_raw)
    score = strict_json(score_raw)
    required_assignment = {"schema", "score_id", "study_root", "task_root",
        "execution_return_sha256", "execution_return_root", "metric_names",
        "executor_session_root", "scoring_rubric_root", "independence_policy_root",
        "blinded", "standing", "authority_effect", "real_a5", "g0",
        "scoring_assignment_root"}
    if type(assignment) is not dict or set(assignment) != required_assignment:
        raise SystemExit("STUDY_SCORE_ASSIGNMENT_INVALID")
    assignment_body = {key: value for key, value in assignment.items()
                       if key != "scoring_assignment_root"}
    if (assignment.get("schema") != "mosaic.ucm.architecture-study-scoring-assignment.v0.1"
            or assignment.get("blinded") is not True
            or assignment.get("scoring_assignment_root") != sha(canonical(assignment_body))):
        raise SystemExit("STUDY_SCORE_ASSIGNMENT_INVALID")
    required_score = {"schema", "score_id", "metrics", "notes",
        "scorer_identity_root", "scorer_session_root", "scoring_rubric_root",
        "independence_policy_root", "review_record_root", "scoring_context_root",
        "score_record_root"}
    if type(score) is not dict or set(score) != required_score:
        raise SystemExit("STUDY_SCORE_RECORD_INVALID")
    if (score.get("schema") != "mosaic.ucm.architecture-study-score.v0.2"
            or score.get("score_id") != assignment["score_id"]
            or score.get("review_record_root") != sha(review_raw)
            or score.get("scoring_rubric_root") != assignment["scoring_rubric_root"]
            or score.get("independence_policy_root")
                != assignment["independence_policy_root"]):
        raise SystemExit("STUDY_SCORE_BINDING_MISMATCH")
    if (type(score.get("metrics")) is not dict
            or set(score["metrics"]) != set(assignment["metric_names"])
            or any(type(value) is not int or type(value) is bool or value < 0
                   for value in score["metrics"].values())
            or type(score.get("notes")) is not list
            or any(type(note) is not str for note in score["notes"])):
        raise SystemExit("STUDY_SCORE_METRICS_INVALID")
    for field in ("scorer_identity_root", "scorer_session_root",
                  "scoring_rubric_root", "independence_policy_root",
                  "review_record_root", "scoring_context_root"):
        if type(score.get(field)) is not str or not ROOT_RE.fullmatch(score[field]):
            raise SystemExit("STUDY_SCORE_CONTEXT_ROOT_INVALID")
    scoring_context = {key: score[key] for key in (
        "review_record_root", "scorer_identity_root", "scorer_session_root",
        "scoring_rubric_root")}
    if (score["scoring_context_root"] != sha(canonical(scoring_context))
            or score["scorer_session_root"] == assignment["executor_session_root"]):
        raise SystemExit("STUDY_SCORE_INDEPENDENCE_INVALID")
    score_body = {key: value for key, value in score.items()
                  if key != "score_record_root"}
    if (not ROOT_RE.fullmatch(score["review_record_root"])
            or score["score_record_root"] != sha(canonical(score_body))):
        raise SystemExit("STUDY_SCORE_RECORD_ROOT_INVALID")
    return_body = {
        "schema": "mosaic.ucm.architecture-study-score-return-record.v0.1",
        "score_id": assignment["score_id"],
        "scoring_assignment_root": assignment["scoring_assignment_root"],
        "execution_return_root": assignment["execution_return_root"],
        "score_record_root": score["score_record_root"],
        "review_record_root": score["review_record_root"],
        "scorer_identity_root": score["scorer_identity_root"],
        "scorer_session_root": score["scorer_session_root"],
        "scoring_rubric_root": score["scoring_rubric_root"],
        "scoring_context_root": score["scoring_context_root"],
        "status": "SCORE_COMPLETE_BLINDED",
        "arm_label_disclosed": False,
        **BOUNDARY,
    }
    record = rooted(return_body, "score_return_root")
    archive = deterministic_zip({
        "SCORING-ASSIGNMENT.json": assignment_raw,
        "SCORE.json": canonical(score),
        "SCORING-REVIEW.md": review_raw,
        "SCORE-RETURN.json": canonical(record),
        "SEAL-STUDY-SCORE.py": Path(__file__).read_bytes(),
    })
    if output.exists():
        raise SystemExit("STUDY_SCORE_OUTPUT_EXISTS")
    output.write_bytes(archive)
    return {"status": "PASS", "score_id": assignment["score_id"],
            "score_return_root": record["score_return_root"],
            "archive_sha256": sha(archive), "output": str(output), **BOUNDARY}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assignment", type=Path, required=True)
    parser.add_argument("--score", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(seal(args.assignment.resolve(), args.score.resolve(),
                          args.review.resolve(), args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

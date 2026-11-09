"""Turn a complete six-return denominator into isolated blinded scoring kits."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
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


def rooted(body: dict, field: str) -> dict:
    return {**body, field: sha(canonical(body))}


def strict_json(raw: bytes):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise SystemExit("STUDY_SCORING_JSON_DUPLICATE_KEY")
            value[key] = item
        return value
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              ValueError("non-finite:" + value)))
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit("STUDY_SCORING_JSON_INVALID") from error


def verify(verifier: Path, archive: Path, schema: str, role: str) -> None:
    result = subprocess.run([sys.executable, str(verifier), str(archive),
        "--schema", schema, "--role", role], capture_output=True, text=True)
    if result.returncode:
        raise SystemExit("STUDY_SCORING_ARCHIVE_VERIFY_FAILED:" + result.stderr.strip())


def deterministic_zip(payloads: dict[str, bytes]) -> bytes:
    rows = [{"path": name, "bytes": len(raw), "sha256": sha(raw)}
            for name, raw in sorted(payloads.items())]
    body = {"schema": "mosaic.ucm.architecture-study-scoring-kit.v0.1",
            "artifact_role": "ARCHITECTURE_STUDY_SCORING_KIT", "files": rows,
            **BOUNDARY}
    all_files = {**payloads, "MANIFEST.json": canonical(rooted(body, "manifest_root"))}
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(all_files.items()):
            info = zipfile.ZipInfo(name, FIXED_TIME); info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    return output.getvalue()


def prepare(package: Path, returns: Path, verifier: Path, output: Path,
            sealer: Path, instructions: Path) -> dict:
    verify(verifier, package, "mosaic.ucm.architecture-study-package.v0.1",
           "ARCHITECTURE_STUDY_PACKAGE")
    if output.exists() and any(output.iterdir()):
        raise SystemExit("STUDY_SCORING_OUTPUT_NOT_EMPTY")
    output.mkdir(parents=True, exist_ok=True)
    return_paths = sorted(returns.glob("*.zip"))
    if len(return_paths) != 6:
        raise SystemExit("STUDY_SCORING_DENOMINATOR_INCOMPLETE")
    with zipfile.ZipFile(package) as coordinator:
        inventory = strict_json(coordinator.read("STUDY-KIT-INVENTORY.json"))
        protocol = strict_json(coordinator.read("STUDY-PROTOCOL.json"))
        rubric = coordinator.read("SCORING-RUBRIC.json")
        contract = coordinator.read("ARCHITECTURE-CONTRACT.json")
        oversight = coordinator.read("HUMAN-OVERSIGHT-POLICY.json")
        context_registration = strict_json(
            coordinator.read("EXECUTION-CONTEXT-REGISTRATION.json"))
    expected = {row["run_id"]: row for row in inventory["runs"]}
    seen = set()
    mappings = []
    for number, return_path in enumerate(return_paths, 1):
        verify(verifier, return_path,
               "mosaic.ucm.architecture-study-execution-return.v0.1",
               "ARCHITECTURE_STUDY_EXECUTION_RETURN")
        return_raw = return_path.read_bytes()
        with zipfile.ZipFile(return_path) as archive:
            record = strict_json(archive.read("EXECUTION-RETURN.json"))
            output_record = strict_json(archive.read("capture/RUN-OUTPUT.json"))
            run_kit = archive.read("RUN-KIT.zip")
            captures = {name.removeprefix("capture/"): archive.read(name)
                        for name in archive.namelist() if name.startswith("capture/")}
        run_id = record.get("run_id")
        if run_id not in expected or run_id in seen:
            raise SystemExit("STUDY_SCORING_RUN_SET_MISMATCH")
        seen.add(run_id)
        required_output = {
            "schema", "run_id", "task_root", "model_id_root",
            "model_settings_root", "executor_session_root", "environment_root",
            "toolchain_root", "execution_context_root", "output_root",
            "actions_root", "tests_root", "follow_on_result_root",
            "context_registration_root", "elapsed_seconds", "notes",
            "output_record_root",
        }
        required_record = {
            "schema", "run_id", "assignment_root", "run_kit_sha256",
            "output_record_root", "capture_root", "capture", "status",
            "arm_label_disclosed", "non_claims", "standing", "authority_effect",
            "real_a5", "g0", "return_root",
        }
        capture_rows = [{"path": name, "bytes": len(raw), "sha256": sha(raw)}
                        for name, raw in sorted(captures.items())]
        actions = strict_json(captures["ACTIONS.json"])
        tests = strict_json(captures["TESTS.json"])
        follow_on = strict_json(captures["FOLLOW-ON-RESULT.json"])
        if (type(record) is not dict or set(record) != required_record
                or type(output_record) is not dict or set(output_record) != required_output
                or set(captures) != CAPTURE_REQUIRED
                or output_record.get("schema")
                    != "mosaic.ucm.architecture-study-raw-run-output.v0.3"
                or record.get("status") != "EXECUTION_COMPLETE_UNSCORED"
                or record.get("arm_label_disclosed") is not False
                or sha(run_kit) != expected[run_id]["sha256"]
                or record.get("run_kit_sha256") != expected[run_id]["sha256"]
                or output_record.get("run_id") != run_id
                or record.get("output_record_root")
                    != output_record.get("output_record_root")
                or record.get("capture") != capture_rows
                or record.get("capture_root") != sha(canonical(capture_rows))
                or output_record.get("output_root") != sha(captures["OUTPUT.zip"])
                or output_record.get("actions_root") != sha(canonical(actions))
                or output_record.get("tests_root") != sha(canonical(tests))
                or output_record.get("follow_on_result_root")
                    != sha(canonical(follow_on))
                or record.get("return_root") != sha(canonical({
                    key: value for key, value in record.items() if key != "return_root"}))
                or output_record.get("output_record_root") != sha(canonical({
                    key: value for key, value in output_record.items()
                    if key != "output_record_root"}))
                or any(type(output_record.get(field)) is not str
                       or not ROOT_RE.fullmatch(output_record[field]) for field in (
                           "model_id_root", "model_settings_root",
                           "executor_session_root", "environment_root",
                           "toolchain_root", "execution_context_root", "output_root",
                           "actions_root", "tests_root", "follow_on_result_root",
                           "context_registration_root"))
                or output_record.get("context_registration_root")
                    != context_registration.get("registration_root")
                or output_record.get("execution_context_root") != sha(canonical({
                    key: output_record[key] for key in (
                        "environment_root", "executor_session_root", "model_id_root",
                        "model_settings_root", "toolchain_root")}))):
            raise SystemExit("STUDY_SCORING_RETURN_BINDING_MISMATCH")
        with zipfile.ZipFile(io.BytesIO(run_kit)) as run_archive:
            prompt = run_archive.read("TASK-PROMPT.md")
            subject = run_archive.read("SUBJECT.zip")
            task = strict_json(run_archive.read("TASK.json"))
        rubric_root = sha(rubric)
        review_policy = protocol.get("review_policy", {})
        if (review_policy.get("scoring_rubric_root") != rubric_root
                or review_policy.get("independent_scorers_required") is not True
                or review_policy.get("executor_scorer_session_separation_required") is not True):
            raise SystemExit("STUDY_SCORING_POLICY_INVALID")
        executor_session_root = output_record.get("executor_session_root")
        if (type(executor_session_root) is not str
                or not ROOT_RE.fullmatch(executor_session_root)):
            raise SystemExit("STUDY_SCORING_EXECUTOR_CONTEXT_INVALID")
        independence_policy_root = sha(canonical(review_policy))
        score_id = sha(canonical({"study_root": inventory["study_root"],
                                  "execution_return_root": record["return_root"],
                                  "task_root": task["task_root"]}))
        assignment_body = {
            "schema": "mosaic.ucm.architecture-study-scoring-assignment.v0.1",
            "score_id": score_id, "study_root": inventory["study_root"],
            "task_root": task["task_root"],
            "execution_return_sha256": sha(return_raw),
            "execution_return_root": record["return_root"],
            "executor_session_root": executor_session_root,
            "scoring_rubric_root": rubric_root,
            "independence_policy_root": independence_policy_root,
            "metric_names": protocol["metrics"], "blinded": True, **BOUNDARY,
        }
        assignment = rooted(assignment_body, "scoring_assignment_root")
        score_template = {
            "schema": "mosaic.ucm.architecture-study-score.v0.2",
            "score_id": score_id,
            "metrics": {name: None for name in protocol["metrics"]},
            "notes": [],
            "scorer_identity_root": "<64-lowercase-hex>",
            "scorer_session_root": "<unique-64-lowercase-hex>",
            "scoring_rubric_root": rubric_root,
            "independence_policy_root": independence_policy_root,
            "review_record_root": "<sha256-of-SCORING-REVIEW.md>",
            "scoring_context_root": "<derive-after-completion>",
            "score_record_root": "<derive-after-completion>",
        }
        command = rf'''@echo off
setlocal EnableExtensions
set "PYEXE="
py -3.12 -c "import sys;assert sys.version_info[:2]==(3,12)" >nul 2>nul && set "PYEXE=py -3.12"
if not defined PYEXE py -3.13 -c "import sys;assert sys.version_info[:2]==(3,13)" >nul 2>nul && set "PYEXE=py -3.13"
if not defined PYEXE python -c "import sys;assert (3,12)<=sys.version_info[:2]<(3,14)" >nul 2>nul && set "PYEXE=python"
if not defined PYEXE goto :FAIL
%PYEXE% "%~dp0SEAL-STUDY-SCORE.py" --assignment "%~dp0SCORING-ASSIGNMENT.json" --score "%~dp0SCORE.json" --review "%~dp0SCORING-REVIEW.md" --output "%~dp0SCORE-RETURN.zip" || goto :FAIL
%PYEXE% "%~dp0VERIFY.py" "%~dp0SCORE-RETURN.zip" --schema "mosaic.ucm.architecture-study-score-return.v0.1" --role "ARCHITECTURE_STUDY_SCORE_RETURN" || goto :FAIL
echo PASS - SCORE-RETURN.zip is ready for coordinator finalization.
pause
exit /b 0
:FAIL
echo ERROR - inspect the diagnostic above.
pause
exit /b 1
'''.replace("\n", "\r\n").encode("ascii")
        payloads = {
            "SCORING-ASSIGNMENT.json": canonical(assignment),
            "TASK-PROMPT.md": prompt, "SUBJECT.zip": subject,
            "ARCHITECTURE-CONTRACT.json": contract,
            "SCORING-RUBRIC.json": rubric,
            "HUMAN-OVERSIGHT-POLICY.json": oversight,
            "SCORE.template.json": canonical(score_template),
            "SCORER-INSTRUCTIONS.md": instructions.read_bytes(),
            "SEAL-STUDY-SCORE.py": sealer.read_bytes(),
            "RUN-SEAL-SCORE.cmd": command,
            "VERIFY.py": verifier.read_bytes(),
            **{f"capture/{name}": raw for name, raw in captures.items()},
        }
        kit = deterministic_zip(payloads)
        name = f"SCORING-DISPATCH-{number:03d}.zip"
        (output / name).write_bytes(kit)
        mappings.append({"score_id": score_id, "run_id": run_id,
                         "execution_return_sha256": sha(return_raw),
                         "execution_return_root": record["return_root"],
                         "scoring_kit": name, "scoring_kit_sha256": sha(kit)})
    if seen != set(expected):
        raise SystemExit("STUDY_SCORING_DENOMINATOR_INCOMPLETE")
    mapping_body = {
        "schema": "mosaic.ucm.architecture-study-scoring-coordinator-map.v0.1",
        "study_root": inventory["study_root"], "roster_root": inventory["roster_root"],
        "denominator": 6, "mappings": mappings,
        "status": "READY_FOR_BLINDED_SCORING",
        "non_claims": ["NO_SCORE_RETURN", "NO_AGGREGATE", "NO_BENEFIT_CLAIM"],
        **BOUNDARY,
    }
    mapping = rooted(mapping_body, "mapping_root")
    (output / "COORDINATOR-SCORING-MAP.json").write_bytes(canonical(mapping))
    return mapping


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--returns", type=Path, required=True)
    parser.add_argument("--verifier", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sealer", type=Path, required=True)
    parser.add_argument("--instructions", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.package.resolve(), args.returns.resolve(),
                     args.verifier.resolve(), args.output.resolve(),
                     args.sealer.resolve(), args.instructions.resolve())
    print(json.dumps({"status": "PASS", "scoring_kits": result["denominator"],
                      "mapping_root": result["mapping_root"],
                      "output": str(args.output.resolve()), **BOUNDARY}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

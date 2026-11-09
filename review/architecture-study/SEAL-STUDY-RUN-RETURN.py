"""Seal one isolated Track C execution return without scoring it."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import zipfile


BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
ROOT_RE = re.compile(r"[0-9a-f]{64}")
REQUIRED = {
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
                raise SystemExit("STUDY_RETURN_JSON_DUPLICATE_KEY")
            result[key] = value
        return result
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              ValueError("non-finite:" + value)))
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit("STUDY_RETURN_JSON_INVALID") from error


def rooted(body: dict, field: str) -> dict:
    return {**body, field: sha(canonical(body))}


def safe_zip(raw: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or not names:
                raise SystemExit("STUDY_RETURN_OUTPUT_ARCHIVE_INVALID")
            for name in names:
                pure = PurePosixPath(name)
                if (pure.is_absolute() or ".." in pure.parts or "\\" in name
                        or not name or name.endswith("/")):
                    raise SystemExit("STUDY_RETURN_OUTPUT_ARCHIVE_INVALID")
                archive.read(name)
    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
        raise SystemExit("STUDY_RETURN_OUTPUT_ARCHIVE_INVALID") from error


def deterministic_zip(payloads: dict[str, bytes]) -> bytes:
    rows = [{"path": name, "bytes": len(raw), "sha256": sha(raw)}
            for name, raw in sorted(payloads.items())]
    body = {"schema": "mosaic.ucm.architecture-study-execution-return.v0.1",
            "artifact_role": "ARCHITECTURE_STUDY_EXECUTION_RETURN",
            "files": rows, **BOUNDARY}
    manifest = rooted(body, "manifest_root")
    all_files = {**payloads, "MANIFEST.json": canonical(manifest)}
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(all_files.items()):
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    return output.getvalue()


def seal(run_kit: Path, expected_run_kit_sha256: str,
         capture: Path, output: Path) -> dict:
    kit_raw = run_kit.read_bytes()
    if sha(kit_raw) != expected_run_kit_sha256:
        raise SystemExit("STUDY_RETURN_RUN_KIT_PIN_MISMATCH")
    if not capture.is_dir():
        raise SystemExit("STUDY_RETURN_CAPTURE_DIRECTORY_MISSING")
    actual = {path.name for path in capture.iterdir() if path.is_file()}
    if actual != REQUIRED or any(path.is_dir() for path in capture.iterdir()):
        raise SystemExit("STUDY_RETURN_CAPTURE_SET_INVALID")
    raw_files = {name: (capture / name).read_bytes() for name in sorted(REQUIRED)}
    if any(not raw for raw in raw_files.values()):
        raise SystemExit("STUDY_RETURN_EMPTY_CAPTURE")
    output_record = strict_json(raw_files["RUN-OUTPUT.json"])
    actions = strict_json(raw_files["ACTIONS.json"])
    tests = strict_json(raw_files["TESTS.json"])
    for name in ("REPAIRS.json", "JOURNAL.json", "RECEIPTS.json"):
        strict_json(raw_files[name])
    follow_on = strict_json(raw_files["FOLLOW-ON-RESULT.json"])
    safe_zip(raw_files["OUTPUT.zip"])
    with zipfile.ZipFile(run_kit) as archive:
        assignment = strict_json(archive.read("ASSIGNMENT.json"))
        task = strict_json(archive.read("TASK.json"))
    required_output_keys = {
        "schema", "run_id", "task_root", "model_id_root", "model_settings_root",
        "executor_session_root", "environment_root", "toolchain_root",
        "execution_context_root", "output_root", "actions_root", "tests_root",
        "follow_on_result_root", "context_registration_root",
        "elapsed_seconds", "notes", "output_record_root",
    }
    if type(output_record) is not dict or set(output_record) != required_output_keys:
        raise SystemExit("STUDY_RETURN_OUTPUT_RECORD_INVALID")
    if (output_record.get("schema") != "mosaic.ucm.architecture-study-raw-run-output.v0.3"
            or output_record.get("run_id") != assignment.get("run_id")
            or output_record.get("task_root") != assignment.get("task_root")
            or output_record.get("task_root") != task.get("task_root")):
        raise SystemExit("STUDY_RETURN_OUTPUT_BINDING_MISMATCH")
    for field in ("model_id_root", "model_settings_root", "executor_session_root",
                  "environment_root", "toolchain_root", "execution_context_root",
                  "output_root", "actions_root", "tests_root",
                  "follow_on_result_root", "context_registration_root"):
        if type(output_record.get(field)) is not str or not ROOT_RE.fullmatch(output_record[field]):
            raise SystemExit("STUDY_RETURN_OUTPUT_ROOT_INVALID")
    if (output_record["output_root"] != sha(raw_files["OUTPUT.zip"])
            or output_record["actions_root"] != sha(canonical(actions))
            or output_record["tests_root"] != sha(canonical(tests))
            or output_record["follow_on_result_root"] != sha(canonical(follow_on))
            or output_record["context_registration_root"]
                != assignment.get("context_registration_root")):
        raise SystemExit("STUDY_RETURN_CAPTURE_ROOT_MISMATCH")
    execution_context = {key: output_record[key] for key in (
        "environment_root", "executor_session_root", "model_id_root",
        "model_settings_root", "toolchain_root")}
    if output_record["execution_context_root"] != sha(canonical(execution_context)):
        raise SystemExit("STUDY_RETURN_EXECUTION_CONTEXT_INVALID")
    if (type(output_record.get("elapsed_seconds")) is not int
            or type(output_record["elapsed_seconds"]) is bool
            or output_record["elapsed_seconds"] < 0
            or type(output_record.get("notes")) is not list
            or any(type(item) is not str for item in output_record["notes"])):
        raise SystemExit("STUDY_RETURN_OUTPUT_METADATA_INVALID")
    body = {key: deepcopy(value) for key, value in output_record.items()
            if key != "output_record_root"}
    if output_record["output_record_root"] != sha(canonical(body)):
        raise SystemExit("STUDY_RETURN_OUTPUT_RECORD_ROOT_INVALID")
    capture_rows = [{"path": name, "bytes": len(raw), "sha256": sha(raw)}
                    for name, raw in sorted(raw_files.items())]
    return_body = {
        "schema": "mosaic.ucm.architecture-study-execution-return-record.v0.1",
        "run_id": assignment["run_id"],
        "assignment_root": assignment["assignment_root"],
        "run_kit_sha256": expected_run_kit_sha256,
        "output_record_root": output_record["output_record_root"],
        "capture_root": sha(canonical(capture_rows)),
        "capture": capture_rows,
        "status": "EXECUTION_COMPLETE_UNSCORED",
        "arm_label_disclosed": False,
        "non_claims": ["NOT_SCORED", "NOT_A_STUDY_RESULT", "NOT_A_BENEFIT_CLAIM"],
        **BOUNDARY,
    }
    return_record = rooted(return_body, "return_root")
    payloads = {"RUN-KIT.zip": kit_raw, "EXECUTION-RETURN.json": canonical(return_record),
                **{f"capture/{name}": raw for name, raw in raw_files.items()},
                "SEAL-STUDY-RUN-RETURN.py": Path(__file__).read_bytes()}
    archive = deterministic_zip(payloads)
    if output.exists():
        raise SystemExit("STUDY_RETURN_OUTPUT_EXISTS")
    output.write_bytes(archive)
    return {"status": "PASS", "run_id": assignment["run_id"],
            "return_root": return_record["return_root"],
            "archive_sha256": sha(archive), "output": str(output), **BOUNDARY}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-kit", type=Path, required=True)
    parser.add_argument("--expected-run-kit-sha256", required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = seal(args.run_kit.resolve(), args.expected_run_kit_sha256,
                  args.capture.resolve(), args.output.resolve())
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

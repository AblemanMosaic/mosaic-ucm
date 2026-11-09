from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
ROOT_FIELDS = {
    "SOURCE-MANIFEST.json": "source_manifest_root",
    "QUALIFICATION.json": "qualification_root",
    "LOCALITY.json": "locality_binding_root",
    "EXACT-EXECUTION-CAPSULE.json": "execution_capsule_root",
    "QUALIFICATION-PRODUCER-RECEIPT.json": "artifact_producer_receipt_root",
    "STANDARDS-CATALOG.json": "catalog_root",
    "STANDARDS-EVALUATION.json": "evaluation_root",
    "PROCESS-BASELINE.json": "process_baseline_root",
    "MILESTONE.json": "milestone_root",
    "MILESTONE-ASSESSMENT.json": "milestone_assessment_root",
    "PROCESS-CHECKPOINT.json": "process_checkpoint_root",
    "STANDARDS-SCHEDULE.json": "standards_schedule_root",
    "PROCESS-OBSERVATORY.json": "process_observatory_root",
    "COURTHOUSE-PROCESS-BINDING.json": "courthouse_process_binding_root",
}


class VerificationError(ValueError):
    pass


def refuse(code: str) -> None:
    raise VerificationError(code)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def reject_float(_value: str):
    refuse("PROCESS_ARCHIVE_NON_INTEGER_NUMBER")


def pairs(rows):
    value = {}
    for key, item in rows:
        if key in value:
            refuse("PROCESS_ARCHIVE_DUPLICATE_JSON_KEY")
        value[key] = item
    return value


def loads(raw: bytes):
    try:
        text = raw.decode("utf-8")
        value = json.loads(text, object_pairs_hook=pairs, parse_float=reject_float,
                           parse_constant=lambda _value: refuse(
                               "PROCESS_ARCHIVE_NONFINITE_NUMBER"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError("PROCESS_ARCHIVE_JSON_INVALID") from error
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
    if raw not in {canonical, canonical + b"\n"}:
        refuse("PROCESS_ARCHIVE_JSON_NONCANONICAL")
    return value


def rooted(value: dict, field: str) -> None:
    if not isinstance(value, dict) or field not in value:
        refuse("PROCESS_ARCHIVE_ROOT_FIELD_MISSING")
    body = {key: item for key, item in value.items() if key != field}
    expected = sha(json.dumps(body, ensure_ascii=False, sort_keys=True,
                              separators=(",", ":")).encode("utf-8"))
    if value[field] != expected:
        refuse("PROCESS_ARCHIVE_RECORD_ROOT_MISMATCH")


def verify_thr(value: dict, members: dict[str, bytes]) -> None:
    if value.get("schema") != "mosaic.ucm.thr-cas-manifest.v0.1":
        refuse("PROCESS_ARCHIVE_THR_SCHEMA_INVALID")
    sections = {"H_s": "state", "H_c": "admissibility", "H_m": "meaning",
                "H_j": "locality", "H_r": "receipt_identity"}
    if set(value.get("commitments", {})) != set(sections):
        refuse("PROCESS_ARCHIVE_THR_COMMITMENTS_INVALID")
    for commitment, section in sections.items():
        raw = json.dumps(value[section], ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
        if value["commitments"][commitment] != sha(raw):
            refuse("PROCESS_ARCHIVE_THR_COMMITMENT_MISMATCH")
    state_sources = {
        "PROCESS-BASELINE.json": "PROCESS-BASELINE.json",
        "PROCESS-CHECKPOINT.json": "PROCESS-CHECKPOINT.json",
        "PROCESS-LOCALITY.json": "LOCALITY.json",
        "milestones/MILESTONE.PROCESS.C1.json": "MILESTONE.json",
        "assessments/MILESTONE.PROCESS.C1.json": "MILESTONE-ASSESSMENT.json",
    }
    if set(members).issuperset(state_sources.values()) is False:
        refuse("PROCESS_ARCHIVE_THR_STATE_MEMBER_MISSING")
    state_rows = []
    for path, source in sorted(state_sources.items()):
        raw = members[source]
        canonical_record = raw[:-1] if raw.endswith(b"\n") else raw
        state_rows.append({"path": path, "sha256": sha(canonical_record),
                           "bytes": len(canonical_record)})
    if value["state"] != {"schema": "mosaic.ucm.thr.state.v0.1",
                          "members": state_rows}:
        refuse("PROCESS_ARCHIVE_THR_STATE_MISMATCH")
    rooted(value, "h_body")


def verify(path: Path) -> dict:
    raw_archive = path.read_bytes()
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if names != sorted(names) or len(names) != len(set(names)):
                refuse("PROCESS_ARCHIVE_MEMBER_ORDER_OR_DUPLICATE_INVALID")
            members = {}
            for info in archive.infolist():
                name = info.filename
                pure = PurePosixPath(name)
                if (pure.is_absolute() or "\\" in name or any(
                        part in {"", ".", ".."} for part in pure.parts)):
                    refuse("PROCESS_ARCHIVE_MEMBER_PATH_INVALID")
                if info.date_time != (1980, 1, 1, 0, 0, 0):
                    refuse("PROCESS_ARCHIVE_MEMBER_TIMESTAMP_INVALID")
                members[name] = archive.read(info)
    except zipfile.BadZipFile as error:
        raise VerificationError("PROCESS_ARCHIVE_ZIP_INVALID") from error
    if "INDEX.json" not in members or "VERIFY.py" not in members:
        refuse("PROCESS_ARCHIVE_REQUIRED_MEMBER_MISSING")
    index = loads(members["INDEX.json"])
    rooted(index, "index_root")
    rows = index.get("files")
    if not isinstance(rows, list) or index.get("file_count") != len(rows):
        refuse("PROCESS_ARCHIVE_INDEX_INVALID")
    expected_names = sorted(set(members) - {"INDEX.json"})
    if [row.get("path") for row in rows] != expected_names:
        refuse("PROCESS_ARCHIVE_CLOSED_SET_MISMATCH")
    for row in rows:
        if set(row) != {"path", "sha256", "bytes"}:
            refuse("PROCESS_ARCHIVE_INDEX_ROW_INVALID")
        raw = members[row["path"]]
        if row["sha256"] != sha(raw) or row["bytes"] != len(raw):
            refuse("PROCESS_ARCHIVE_MEMBER_HASH_MISMATCH")
    for name, root_field in ROOT_FIELDS.items():
        value = loads(members[name])
        rooted(value, root_field)
        if any(value.get(key) != expected for key, expected in BOUNDARY.items()):
            refuse("PROCESS_ARCHIVE_AUTHORITY_CEILING_INVALID")
    verify_thr(loads(members["PROCESS-THR-CAS.json"]), members)
    return {"status": "PASS", "archive_sha256": sha(raw_archive),
            "members": len(members), "index_root": index["index_root"], **BOUNDARY}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.archive)
    except VerificationError as error:
        print(json.dumps({"status": "REFUSED", "diagnostic": str(error), **BOUNDARY},
                         sort_keys=True, separators=(",", ":")))
        return 3
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

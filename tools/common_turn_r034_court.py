#!/usr/bin/env python3
"""Builder-authored, operator-runnable r034 common-turn court.

The authoring agent must not run this court.  --preflight-only is a stdlib-only
custody inspection and executes zero subject imports and zero attack cases.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import types
import zipfile

FIXED = (1980, 1, 1, 0, 0, 0)
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
CASE_IDS = (
    "CONTROL-KIT-CLOSED-CUSTODY", "CONTROL-SOURCE-RUNTIME-BOUNDARY",
    "CONTROL-COMMON-TURN", "CONTROL-SCENARIO-REQUIREMENTS",
    "CONTROL-HUMAN-PROJECTION", "RECORD-ROOT-SWAP",
    "RECORD-PROJECT-RESEALED-SWAP", "RECORD-CONTEXT-RESEALED-SWAP",
    "CLAIM-ASSURANCE-LAUNDERING", "EVIDENCE-ASSURANCE-LAUNDERING",
    "ACCEPTANCE-DENOMINATOR-SHRINK", "UNKNOWN-COVERAGE-PRESERVED",
    "VERIFIED-COVERAGE-LAUNDERING", "TOOL-DECLARATION-NOT-ENFORCEMENT",
    "ENFORCED-HOST-RESEALED-OVERCLAIM", "REPORTED-MET-NEVER-CLOSES",
    "RECONCILE-CHANGED-JOURNAL", "REPORT-OPENING-SWAP",
    "NATIVE-TURN-REFERENCE-NOT-PROOF", "CONTROL-EXACT-CMBA-BINDING",
    "CONTROL-CMBA-ASSESSMENT-REPLAY", "CMBA-EXPECTED-PIN-SWAP",
    "CMBA-WHEEL-BYTE-MUTATION", "CMBA-RESEALED-ASSURANCE-LAUNDERING", "CMBA-RESEALED-VALUES-SWAP",
    "CMBA-PRELOADED-FOREIGN-MODULE", "CONTROL-AUTHORITY-CEILING",
)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, code):
    if not condition:
        raise ValueError(code)


def rooted(value, field="root"):
    return (type(value) is dict and value.get(field)
            == sha(canonical({key: item for key, item in value.items() if key != field})))


def relative(name):
    require(type(name) is str and name and "\\" not in name and ":" not in name,
            "ARCHIVE_PATH_INVALID")
    path = PurePosixPath(name)
    require(not path.is_absolute() and name == path.as_posix()
            and not any(part in {"", ".", ".."} for part in path.parts)
            and not name.endswith("/"), "ARCHIVE_PATH_INVALID")
    return name


def verified_archive(path):
    """Verify the entire runtime archive without importing any subject code."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), "RUNTIME_DUPLICATE_MEMBER")
        for name in names:
            relative(name)
        manifest = json.loads(archive.read("MANIFEST.json"))
        require(rooted(manifest), "RUNTIME_MANIFEST_ROOT_INVALID")
        rows = manifest["members"]
        require(len(rows) == manifest["member_count"], "RUNTIME_MEMBER_COUNT_INVALID")
        require([row["path"] for row in rows] == sorted({row["path"] for row in rows}),
                "RUNTIME_MEMBER_ORDER_INVALID")
        require(set(names) == {"MANIFEST.json", *(row["path"] for row in rows)},
                "RUNTIME_MEMBER_SET_INVALID")
        for row in rows:
            raw = archive.read(relative(row["path"]))
            require(len(raw) == row["bytes"] and sha(raw) == row["sha256"],
                    "RUNTIME_MEMBER_BYTES_INVALID")
        return manifest


def verify_cold_boot(path, expected_runtime_sha256):
    """Read-only cold-boot custody and exact embedded runtime correspondence."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), "COLD_BOOT_DUPLICATE_MEMBER")
        for name in names:
            relative(name)
        manifest = json.loads(archive.read("MANIFEST.json"))
        require(rooted(manifest, "manifest_root"), "COLD_BOOT_MANIFEST_ROOT_INVALID")
        rows = manifest["members"]
        require(len(rows) == manifest["member_count"]
                and [row["path"] for row in rows] == sorted({row["path"] for row in rows})
                and set(names) == {"MANIFEST.json", *(row["path"] for row in rows)},
                "COLD_BOOT_MEMBER_DENOMINATOR_INVALID")
        for row in rows:
            raw = archive.read(row["path"])
            require(len(raw) == row["bytes"] and sha(raw) == row["sha256"],
                    "COLD_BOOT_MEMBER_BYTES_INVALID")
        metadata = json.loads(archive.read("BOOT/COLD-BOOT.json"))
        require(rooted(metadata, "cold_boot_root"), "COLD_BOOT_META_ROOT_INVALID")
        require(sha(archive.read("UCM/UCM-v0.1-runtime.zip")) == expected_runtime_sha256
                and metadata.get("runtime_sha256") == expected_runtime_sha256
                and metadata.get("version") == "v0.1" and metadata.get("revision") == "r034",
                "COLD_BOOT_RUNTIME_BINDING_MISMATCH")
        return {"manifest_root": manifest["manifest_root"],
                "cold_boot_root": metadata["cold_boot_root"],
                "embedded_runtime_sha256": expected_runtime_sha256,
                "metadata_scope": "MANIFEST_AND_BOOT_PIN_CUSTODY_ONLY"}


def verify_kit(kit):
    """Closed-set custody preflight.  It neither imports nor runs the subject."""
    manifest = json.loads((kit / "KIT-MANIFEST.json").read_text(encoding="utf-8"))
    require(rooted(manifest, "operator_kit_root"), "KIT_MANIFEST_ROOT_INVALID")
    rows = manifest["members"]
    require(len(rows) == manifest["member_count"], "KIT_MEMBER_COUNT_INVALID")
    require([row["path"] for row in rows] == sorted({row["path"] for row in rows}),
            "KIT_MEMBER_ORDER_INVALID")
    expected = {relative(row["path"]): row for row in rows}
    actual = {path.relative_to(kit).as_posix() for path in kit.rglob("*") if path.is_file()}
    require(actual == {"KIT-MANIFEST.json", *expected}, "KIT_MEMBER_SET_INVALID")
    for name, row in expected.items():
        raw = (kit / name).read_bytes()
        require(len(raw) == row["bytes"] and sha(raw) == row["sha256"],
                "KIT_MEMBER_BYTES_INVALID")
    require(manifest["case_ids"] == list(CASE_IDS)
            and manifest["case_count"] == len(CASE_IDS), "KIT_CASE_DENOMINATOR_INVALID")
    require(all(manifest.get(key) == value for key, value in BOUNDARY.items()),
            "KIT_BOUNDARY_INVALID")
    runtime = verified_archive(kit / "UCM-v0.1-runtime.zip")
    source = json.loads((kit / "SOURCE-MANIFEST.json").read_text(encoding="utf-8"))
    qualification = json.loads((kit / "UCM-v0.1-QUALIFICATION.json").read_text(encoding="utf-8"))
    require(rooted(source) and source["root"] == manifest["source_root"],
            "SOURCE_MANIFEST_ROOT_INVALID")
    require(source["member_count"] == len(source["members"])
            and [row["path"] for row in source["members"]]
                == sorted({row["path"] for row in source["members"]}),
            "SOURCE_MANIFEST_DENOMINATOR_INVALID")
    require(rooted(qualification) and qualification["root"] == manifest["qualification_root"],
            "QUALIFICATION_ROOT_INVALID")
    require(qualification.get("engineering_revision") == "r034"
            and qualification.get("source_manifest_root") == source["root"],
            "QUALIFICATION_SOURCE_BINDING_MISMATCH")
    require(sha((kit / "UCM-v0.1-runtime.zip").read_bytes()) == manifest["runtime_sha256"],
            "RUNTIME_PIN_INVALID")
    require(runtime["root"] == manifest["runtime_manifest_root"],
            "RUNTIME_MANIFEST_PIN_INVALID")
    qualified_runtime = [row for row in qualification.get("artifacts", [])
                         if row.get("role") == "UCM_RUNTIME"]
    require(len(qualified_runtime) == 1
            and qualified_runtime[0].get("sha256") == manifest["runtime_sha256"]
            and qualified_runtime[0].get("manifest_root") == runtime["root"],
            "QUALIFICATION_RUNTIME_BINDING_MISMATCH")
    cold_boot = kit / "PIPPI-v0.1-adaptive-cold-boot.zip"
    if manifest.get("cold_boot_sha256") is not None:
        require(cold_boot.is_file() and sha(cold_boot.read_bytes()) == manifest["cold_boot_sha256"],
                "COLD_BOOT_ARCHIVE_PIN_INVALID")
        require(verify_cold_boot(cold_boot, manifest["runtime_sha256"])
                == manifest.get("cold_boot_binding"), "COLD_BOOT_BINDING_PIN_INVALID")
    else:
        require(not cold_boot.exists() and manifest.get("cold_boot_binding") is None,
                "COLD_BOOT_UNDECLARED_MEMBER")
    source_rows = {row["path"]: row for row in source["members"]}
    require("tools/common_turn_r034_court.py" in source_rows
            and sha((kit / "RUN-TIER1.py").read_bytes())
                == source_rows["tools/common_turn_r034_court.py"]["sha256"],
            "RUNNER_SOURCE_PIN_MISMATCH")
    checked = 0
    for row in runtime["members"]:
        if row["path"].startswith(("src/", "spec/", "vendor/optional-packs/cmba/")):
            require(row["path"] in source_rows
                    and all(source_rows[row["path"]][key] == row[key]
                            for key in ("bytes", "sha256")),
                    "RUNTIME_SOURCE_MEMBER_MISMATCH")
            checked += 1
    require(checked > 0, "RUNTIME_SOURCE_BOUNDARY_EMPTY")
    boundary = json.loads((kit / "BOUNDARY.json").read_text(encoding="utf-8"))
    require(rooted(boundary, "boundary_root"), "BOUNDARY_ROOT_INVALID")
    require(set(boundary["runner_required_paths"]) <= {"KIT-MANIFEST.json", *expected},
            "RUNNER_INPUT_OUTSIDE_BOUNDARY")
    require(manifest["boundary_root"] == boundary["boundary_root"], "BOUNDARY_PIN_INVALID")
    require(boundary["runtime_manifest_root"] == runtime["root"]
            and boundary["runner_path"] == "RUN-TIER1.py", "BOUNDARY_SUBJECT_MISMATCH")
    return manifest, runtime


def zip_write(path, members):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, raw in sorted(members.items()):
            info = zipfile.ZipInfo(name, FIXED)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)


def safe_extract(path, destination):
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            relative(name)
        archive.extractall(destination)


def safe_code(error):
    code = getattr(error, "code", None)
    if not isinstance(code, str):
        code = str(error)
    return code if re.fullmatch(r"[A-Z][A-Z0-9_]{1,120}", code) else None


def run_court(kit, cases, outputs):
    manifest, runtime_manifest = verify_kit(kit)
    fixture = json.loads((kit / "CONTROL.json").read_text(encoding="utf-8"))

    def case(case_id, action):
        try:
            action()
            row = {"case_id": case_id, "status": "PASS"}
        except Exception as error:
            row = {"case_id": case_id, "status": "FAIL",
                   "exception_type": type(error).__name__,
                   "message_sha256": sha(str(error).encode("utf-8"))}
            if safe_code(error):
                row["diagnostic_code"] = safe_code(error)
        cases.append({**row, **BOUNDARY})
        print(f"[case {len(cases):03d}] {case_id}: {row['status']}", flush=True)
        print(f"[summary] completed={len(cases)} failed="
              f"{sum(item['status'] != 'PASS' for item in cases)}", flush=True)

    with tempfile.TemporaryDirectory(prefix="ucm-r034-court-") as raw:
        runtime = Path(raw) / "runtime"
        runtime.mkdir()
        safe_extract(kit / "UCM-v0.1-runtime.zip", runtime)
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(runtime / "src"))
        import ucm
        require(Path(ucm.__file__).resolve() == runtime / "src/ucm/__init__.py",
                "COURT_SUBJECT_IMPORT_ORIGIN_MISMATCH")
        from uclop.canonical import Refusal
        from ucm.pippi_adaptive import reconcile_turn, validate_turn_report
        from ucm.pippi_turn_record import (build_turn_record, validate_turn_record,
                                           project_turn_record, reporting_requirements)
        from ucm.pippi_cmba import (CMBA_WHEEL_SHA256, discover_cmba_binding,
                                    build_cmba_turn_assessment, validate_cmba_turn_assessment)

        opening, report, args = fixture["opening"], fixture["report"], fixture["record_arguments"]
        record = build_turn_record(opening=opening, report=report, **deepcopy(args))
        outputs["CONTROL-TURN-RECORD.json"] = canonical(record) + b"\n"

        def validate(value, supplied_opening=None, supplied_report=None):
            return validate_turn_record(value, opening=supplied_opening or opening,
                                        report=supplied_report or report)

        def reseal(value, field):
            value[field] = sha(canonical({key: item for key, item in value.items() if key != field}))
            return value

        def mutated(field, value, *, resealed=True):
            copy = deepcopy(record)
            copy[field] = value
            return reseal(copy, "turn_record_root") if resealed else copy

        def refuses(action, code):
            try:
                action()
            except Refusal as error:
                require(safe_code(error) == code, "UNEXPECTED_TYPED_REFUSAL")
                return
            raise ValueError("EXPECTED_TYPED_REFUSAL_MISSING")

        case(CASE_IDS[0], lambda: verify_kit(kit))
        case(CASE_IDS[1], lambda: require(runtime_manifest["root"]
             == manifest["runtime_manifest_root"], "RUNTIME_BOUNDARY_MISMATCH"))
        case(CASE_IDS[2], lambda: require(validate(record) == record, "CONTROL_RECORD_MISMATCH"))
        case(CASE_IDS[3], lambda: require(reporting_requirements(opening["scenario"])
             == record["requirements"], "REPORTING_REQUIREMENTS_MISMATCH"))
        projection = project_turn_record(record, opening=opening, report=report)
        outputs["CONTROL-HUMAN-PROJECTION.json"] = canonical(projection) + b"\n"
        case(CASE_IDS[4], lambda: require(projection["turn_record_root"] == record["turn_record_root"]
             and projection["projection_is_evidence"] is False, "PROJECTION_CEILING_MISMATCH"))
        case(CASE_IDS[5], lambda: refuses(lambda: validate(mutated("turn_record_root", "0" * 64,
             resealed=False)), "PIPPI_TURN_RECORD_INVALID"))
        case(CASE_IDS[6], lambda: refuses(lambda: validate(mutated("project_root", "0" * 64)),
             "PIPPI_TURN_RECORD_INVALID"))
        case(CASE_IDS[7], lambda: refuses(lambda: validate(mutated("context", [])),
             "PIPPI_TURN_RECORD_INVALID"))

        def assurance_swap(field):
            value = deepcopy(record)
            value[field][0]["assurance"] = "VERIFIED"
            return validate(reseal(value, "turn_record_root"))

        case(CASE_IDS[8], lambda: refuses(lambda: assurance_swap("claims"), "PIPPI_TURN_RECORD_INVALID"))
        case(CASE_IDS[9], lambda: refuses(lambda: assurance_swap("evidence"), "PIPPI_TURN_RECORD_INVALID"))
        case(CASE_IDS[10], lambda: refuses(lambda: validate(mutated("acceptance_case_roots", [])),
             "PIPPI_TURN_RECORD_INVALID"))

        def unknown_coverage():
            request = deepcopy(args)
            request["coverage"] = []
            value = build_turn_record(opening=opening, report=report, **request)
            require(len(value["coverage"]) == 7
                    and all(row["status"] == "UNKNOWN" for row in value["coverage"])
                    and value["status"] == "NEEDS_INFORMATION", "UNKNOWN_COVERAGE_DISAPPEARED")

        case(CASE_IDS[11], unknown_coverage)
        case(CASE_IDS[12], lambda: refuses(lambda: validate(mutated("verified_channel_ids", ["TOOL_RESULT"])),
             "PIPPI_TURN_RECORD_INVALID"))

        def tool_declaration():
            request = deepcopy(args)
            request["coverage"] = [{"channel": "TOOL_RESULT", "status": "COMPLETE",
                "evidence_ids": [], "limitations": ["Agent declaration only."]}]
            value = build_turn_record(opening=opening, report=report, **request)
            require(value["enforced_host_verified"] is False and value["verified_channel_ids"] == []
                    and value["coverage_assurance"] == "DECLARED_NOT_VERIFIED",
                    "TOOL_COVERAGE_BECAME_HOST_PROOF")

        case(CASE_IDS[13], tool_declaration)
        case(CASE_IDS[14], lambda: refuses(lambda: validate(mutated("enforced_host_verified", True)),
             "PIPPI_TURN_RECORD_INVALID"))
        case(CASE_IDS[15], lambda: require(record["acceptance_case_closed"] is False
             and any(row["disposition"] == "REPORTED_MET" for row in record["acceptance_dispositions"]),
             "REPORTED_DISPOSITION_GRANTED_CLOSURE"))
        case(CASE_IDS[16], lambda: refuses(lambda: reconcile_turn(opening=opening, report=report,
             current_project_root=opening["project_root"], current_journal_head="0" * 64),
             "PIPPI_JOURNAL_CHANGED_DURING_TURN"))
        wrong_report = deepcopy(report)
        wrong_report["turn_opening_root"] = "0" * 64
        reseal(wrong_report, "turn_report_root")
        case(CASE_IDS[17], lambda: refuses(lambda: validate_turn_report(wrong_report, opening=opening),
             "PIPPI_TURN_REPORT_INVALID"))

        def native_reference():
            request = deepcopy(args)
            request["native_turn_roots"] = ["5" * 64]
            value = build_turn_record(opening=opening, report=report, **request)
            require(value["native_turn_roots_are_references"] is True
                    and value["enforced_host_verified"] is False, "REFERENCE_BECAME_NATIVE_PROOF")

        case(CASE_IDS[18], native_reference)
        binding = discover_cmba_binding()
        case(CASE_IDS[19], lambda: require(binding["status"] == "AVAILABLE"
             and binding["expected_wheel_sha256"] == CMBA_WHEEL_SHA256,
             "EXACT_CMBA_BINDING_UNAVAILABLE"))
        cmba_args = {"opening": opening, "report": report, "turn_record": record,
                     "expected_wheel_sha256": CMBA_WHEEL_SHA256}
        assessment = build_cmba_turn_assessment(**cmba_args)
        outputs["CONTROL-CMBA-ASSESSMENT.json"] = canonical(assessment) + b"\n"
        case(CASE_IDS[20], lambda: require(validate_cmba_turn_assessment(assessment, **cmba_args)
             == assessment, "CMBA_REPLAY_MISMATCH"))
        case(CASE_IDS[21], lambda: refuses(lambda: build_cmba_turn_assessment(
             **{**cmba_args, "expected_wheel_sha256": "0" * 64}),
             "PIPPI_CMBA_EXPECTED_WHEEL_PIN_REQUIRED"))

        def wheel_byte_mutation():
            path = runtime / "vendor/optional-packs/cmba/cmba_core-0.1.0a7-py3-none-any.whl"
            original = path.read_bytes()
            require(bool(original), "CMBA_WHEEL_FIXTURE_EMPTY")
            path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
            try:
                refuses(lambda: build_cmba_turn_assessment(**cmba_args),
                        "PIPPI_CMBA_WHEEL_PIN_MISMATCH")
            finally:
                path.write_bytes(original)

        case(CASE_IDS[22], wheel_byte_mutation)

        def assessment_swap(field, value):
            copy = deepcopy(assessment)
            copy[field] = value
            return validate_cmba_turn_assessment(reseal(copy, "assessment_root"), **cmba_args)

        case(CASE_IDS[23], lambda: refuses(lambda: assessment_swap("assurance", "VERIFIED"),
             "PIPPI_CMBA_ASSESSMENT_MISMATCH"))
        case(CASE_IDS[24], lambda: refuses(lambda: assessment_swap("cmba_values", {}),
             "PIPPI_CMBA_ASSESSMENT_MISMATCH"))

        def foreign_module():
            previous = sys.modules.get("cmba_core")
            sys.modules["cmba_core"] = types.ModuleType("cmba_core")
            try:
                refuses(lambda: build_cmba_turn_assessment(**cmba_args),
                        "PIPPI_CMBA_MODULE_ORIGIN_MISMATCH")
            finally:
                if previous is None:
                    sys.modules.pop("cmba_core", None)
                else:
                    sys.modules["cmba_core"] = previous

        case(CASE_IDS[25], foreign_module)
        case(CASE_IDS[26], lambda: require(
            all(value.get(key) == expected for value in (record, projection, assessment, binding)
                for key, expected in BOUNDARY.items())
            and record["effect_authorized"] is False
            and assessment["effect_authorized"] is False, "AUTHORITY_CEILING_MISMATCH"))
    require([row["case_id"] for row in cases] == list(CASE_IDS), "COURT_CASE_DENOMINATOR_MISMATCH")
    return manifest, runtime_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    kit = args.kit_root.resolve()
    if args.preflight_only:
        manifest, runtime = verify_kit(kit)
        print(json.dumps({"status": "PASS", "adversarial_cases_executed": 0,
            "subject_imports": 0, "operator_kit_root": manifest["operator_kit_root"],
            "runtime_manifest_root": runtime["root"], "member_count": manifest["member_count"],
            **BOUNDARY}, sort_keys=True), flush=True)
        return 0
    if args.out_dir is None:
        parser.error("--out-dir is required unless --preflight-only is used")
    out = args.out_dir.resolve()
    require(not out.is_relative_to(kit), "EVIDENCE_OUTPUT_INSIDE_IMMUTABLE_KIT")
    cases, outputs, fault, manifest, runtime = [], {}, None, None, None
    try:
        manifest, runtime = run_court(kit, cases, outputs)
    except Exception as error:
        fault = {"exception_type": type(error).__name__,
                 "message_sha256": sha(str(error).encode("utf-8"))}
        if safe_code(error):
            fault["diagnostic_code"] = safe_code(error)
    failed = sum(row["status"] != "PASS" for row in cases)
    complete = [row["case_id"] for row in cases] == list(CASE_IDS)
    body = {"schema": "mosaic.ucm.r034-common-turn-tier1-result.v0.1",
            "status": "PASS" if failed == 0 and complete and fault is None else "HOLD_FOR_REPAIR",
            "case_inventory": list(CASE_IDS), "expected_case_count": len(CASE_IDS),
            "cases": cases, "case_count": len(cases), "failed": failed,
            "case_inventory_complete": complete, "fault": fault,
            "builder_authored": True, "operator_executed": True,
            "independent_review_claimed": False,
            "operator_kit_root": manifest["operator_kit_root"] if manifest else None,
            "subject_runtime_manifest_root": runtime["root"] if runtime else None,
            "subject_runtime_sha256": sha((kit / "UCM-v0.1-runtime.zip").read_bytes())
                 if (kit / "UCM-v0.1-runtime.zip").is_file() else None,
            **BOUNDARY}
    result = {**body, "court_root": sha(canonical(body))}
    outputs["TIER1-RESULT.json"] = canonical(result) + b"\n"
    outputs["RUN-TIER1.py"] = Path(__file__).read_bytes()
    outputs["REPORT.md"] = ("# UCM r034 common turn operator court\n\n"
        f"Status: {result['status']}\nCases completed: {len(cases)}/{len(CASE_IDS)}\n"
        f"Failed: {failed}\n\nBuilder-authored; operator-executed. No independent-review claim.\n"
        "Standing INFORMATION_ONLY; authority effect NONE; real A5 false; G0 closed.\n").encode()
    inventory = {"schema": "mosaic.ucm.r034-tier1-evidence-contents.v0.1",
                 "members": [{"path": name, "bytes": len(raw), "sha256": sha(raw)}
                             for name, raw in sorted(outputs.items())], **BOUNDARY}
    inventory["contents_root"] = sha(canonical(inventory))
    outputs["EVIDENCE-CONTENTS.json"] = canonical(inventory) + b"\n"
    out.mkdir(parents=True, exist_ok=True)
    target = out / ("UCM-r034-COMMON-TURN-TIER1-EVIDENCE-" + result["court_root"][:16] + ".zip")
    zip_write(target, outputs)
    print(json.dumps({"status": result["status"], "cases": len(cases), "failed": failed,
        "court_root": result["court_root"], "evidence": str(target),
        "evidence_sha256": sha(target.read_bytes()), **BOUNDARY}, sort_keys=True), flush=True)
    return 0 if result["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Builder-authored, operator-runnable r036 composite-boundary court.

The authoring agent must not run this court.  ``--preflight-only`` performs
closed-set stdlib custody checks with zero subject imports and zero attack cases.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import tempfile
import zipfile

FIXED = (1980, 1, 1, 0, 0, 0)
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
CASE_IDS = (
    "CONTROL-KIT-CLOSED-CUSTODY", "CONTROL-SOURCE-RUNTIME-BOUNDARY",
    "CONTROL-QUALIFICATION", "CONTROL-PROFILE", "CONTROL-OBSERVATIONAL",
    "CONTROL-EFFECT-BOUND", "TURN-ROOT-SWAP", "CMBA-ASSESSMENT-SWAP",
    "DKN-LOCALITY-SWAP", "CHC-THR-CONTRACT-SWAP", "CCP-DECISION-SWAP",
    "CCP-SUBJECT-SWAP", "G1-EVENT-SWAP", "G2-EVENT-SWAP", "G3-EVENT-SWAP",
    "THR-MANIFEST-SWAP", "CO-PROJECTION-COLLAPSE",
    "ACCEPTANCE-CLOSURE-LAUNDERING", "EFFECT-AUTHORITY-LAUNDERING",
    "CONTROL-AUTHORITY-CEILING",
)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def rooted(value, field="root"):
    return type(value) is dict and value.get(field) == sha(canonical(
        {key: item for key, item in value.items() if key != field}))


def require(condition, code):
    if not condition:
        raise ValueError(code)


def relative(name):
    require(type(name) is str and name and "\\" not in name and ":" not in name,
            "ARCHIVE_PATH_INVALID")
    path = PurePosixPath(name)
    require(not path.is_absolute() and name == path.as_posix()
            and not any(part in {"", ".", ".."} for part in path.parts)
            and not name.endswith("/"), "ARCHIVE_PATH_INVALID")
    return name


def verify_archive(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), "RUNTIME_DUPLICATE_MEMBER")
        for name in names:
            relative(name)
        manifest = json.loads(archive.read("MANIFEST.json"))
        require(rooted(manifest), "RUNTIME_MANIFEST_ROOT_INVALID")
        rows = manifest["members"]
        require(len(rows) == manifest["member_count"]
                and [row["path"] for row in rows] == sorted({row["path"] for row in rows})
                and set(names) == {"MANIFEST.json", *(row["path"] for row in rows)},
                "RUNTIME_MEMBER_DENOMINATOR_INVALID")
        for row in rows:
            raw = archive.read(relative(row["path"]))
            require(len(raw) == row["bytes"] and sha(raw) == row["sha256"],
                    "RUNTIME_MEMBER_BYTES_INVALID")
        return manifest


def verify_kit(kit):
    manifest = json.loads((kit / "KIT-MANIFEST.json").read_bytes())
    require(rooted(manifest, "operator_kit_root"), "KIT_MANIFEST_ROOT_INVALID")
    rows = manifest["members"]
    expected = {relative(row["path"]): row for row in rows}
    actual = {path.relative_to(kit).as_posix() for path in kit.rglob("*") if path.is_file()}
    require(len(rows) == manifest["member_count"]
            and [row["path"] for row in rows] == sorted(expected)
            and actual == {"KIT-MANIFEST.json", *expected}, "KIT_MEMBER_DENOMINATOR_INVALID")
    for name, row in expected.items():
        raw = (kit / name).read_bytes()
        require(len(raw) == row["bytes"] and sha(raw) == row["sha256"],
                "KIT_MEMBER_BYTES_INVALID")
    require(manifest["case_ids"] == list(CASE_IDS) and manifest["case_count"] == len(CASE_IDS),
            "KIT_CASE_DENOMINATOR_INVALID")
    runtime = verify_archive(kit / "UCM-v0.1-runtime.zip")
    source = json.loads((kit / "SOURCE-MANIFEST.json").read_bytes())
    qualification = json.loads((kit / "UCM-v0.1-QUALIFICATION.json").read_bytes())
    require(rooted(source) and source["root"] == manifest["source_root"], "SOURCE_ROOT_INVALID")
    require(rooted(qualification) and qualification["root"] == manifest["qualification_root"]
            and qualification["engineering_revision"] == "r036"
            and qualification["source_manifest_root"] == source["root"],
            "QUALIFICATION_BINDING_INVALID")
    require(runtime["root"] == manifest["runtime_manifest_root"]
            and sha((kit / "UCM-v0.1-runtime.zip").read_bytes()) == manifest["runtime_sha256"],
            "RUNTIME_BINDING_INVALID")
    qualified = [row for row in qualification["artifacts"] if row.get("role") == "UCM_RUNTIME"]
    require(len(qualified) == 1 and qualified[0]["sha256"] == manifest["runtime_sha256"]
            and qualified[0]["manifest_root"] == runtime["root"], "QUALIFIED_RUNTIME_MISMATCH")
    source_rows = {row["path"]: row for row in source["members"]}
    require(source_rows["tools/cmba_composite_r036_court.py"]["sha256"]
            == sha((kit / "RUN-TIER1.py").read_bytes()), "RUNNER_SOURCE_PIN_MISMATCH")
    for row in runtime["members"]:
        if row["path"].startswith(("src/", "vendor/optional-packs/cmba/")):
            require(row["path"] in source_rows
                    and row["sha256"] == source_rows[row["path"]]["sha256"],
                    "RUNTIME_SOURCE_MEMBER_MISMATCH")
    return manifest


def extract_runtime(path, destination):
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            relative(name)
        archive.extractall(destination)


def write_zip(path, payload):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, raw in sorted(payload.items()):
            info = zipfile.ZipInfo(name, FIXED)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    kit = args.kit_root.resolve()
    manifest = verify_kit(kit)
    if args.preflight_only:
        print(json.dumps({"status": "PASS", "member_count": manifest["member_count"],
            "operator_kit_root": manifest["operator_kit_root"], "subject_imports": 0,
            "adversarial_cases_executed": 0, **BOUNDARY}, sort_keys=True))
        return 0
    require(args.out_dir is not None, "OUT_DIR_REQUIRED")
    out = args.out_dir.resolve()
    require(out != kit and not out.is_relative_to(kit), "EVIDENCE_INSIDE_KIT_REFUSED")
    out.mkdir(parents=True, exist_ok=True)
    results = []

    def case(case_id, action):
        try:
            action()
            status, diagnostic = "PASS", None
        except Exception as error:
            status, diagnostic = "FAIL", type(error).__name__ + ":" + sha(str(error).encode())
        results.append({"case_id": case_id, "status": status, "diagnostic": diagnostic})
        print(f"[case {len(results):03d}] {case_id}: {status}", flush=True)

    def refusal(action):
        try:
            action()
        except (ValueError, KeyError, TypeError):
            return
        raise ValueError("EXPECTED_TYPED_REFUSAL")

    with tempfile.TemporaryDirectory(prefix="ucm-r036-composite-") as raw:
        runtime = Path(raw) / "runtime"
        extract_runtime(kit / "UCM-v0.1-runtime.zip", runtime)
        sys.path.insert(0, str(runtime / "src"))
        from ucm.pippi_cmba_composite import (build_composite_assessment,
            composite_profile, validate_composite_assessment)
        control = json.loads((kit / "CONTROL.json").read_bytes())
        observed = control["observational"]
        effected = control["effect_bound"]
        case(CASE_IDS[0], lambda: verify_kit(kit))
        case(CASE_IDS[1], lambda: require(manifest["runtime_source_boundary"] == "EXACT", "BOUNDARY"))
        case(CASE_IDS[2], lambda: require(manifest["qualification_root"]
            == json.loads((kit / "UCM-v0.1-QUALIFICATION.json").read_bytes())["root"], "QUAL"))
        case(CASE_IDS[3], lambda: require(composite_profile() == control["profile"], "PROFILE"))
        case(CASE_IDS[4], lambda: require(build_composite_assessment(**observed["inputs"])
            == observed["result"], "OBSERVATIONAL"))
        case(CASE_IDS[5], lambda: require(build_composite_assessment(**effected["inputs"])
            == effected["result"], "EFFECT_BOUND"))

        def mutated_result(section, path, value):
            changed = deepcopy(section["result"])
            target = changed
            for key in path[:-1]: target = target[key]
            target[path[-1]] = value
            return lambda: refusal(lambda: validate_composite_assessment(changed, **section["inputs"]))

        case(CASE_IDS[6], mutated_result(observed, ["co_projection_roots", "turn_record"], "0" * 64))
        case(CASE_IDS[7], mutated_result(observed, ["co_projection_roots", "cmba"], "0" * 64))
        case(CASE_IDS[8], mutated_result(observed, ["co_projection_roots", "dkn_locality"], "0" * 64))
        case(CASE_IDS[9], mutated_result(observed, ["co_projection_roots", "chc_thr"], "0" * 64))
        case(CASE_IDS[10], mutated_result(observed, ["co_projection_roots", "ccp_decision"], "0" * 64))
        case(CASE_IDS[11], mutated_result(observed, ["ccp_status"], "REFUSE"))
        case(CASE_IDS[12], mutated_result(effected, ["operation", "g1_root"], "0" * 64))
        case(CASE_IDS[13], mutated_result(effected, ["operation", "g2_root"], "0" * 64))
        case(CASE_IDS[14], mutated_result(effected, ["operation", "g3_root"], "0" * 64))
        case(CASE_IDS[15], mutated_result(effected, ["thr_manifest", "H_r"], "0" * 64))
        case(CASE_IDS[16], mutated_result(observed, ["co_projection_roots", "dkn_locality"],
                                          observed["result"]["co_projection_roots"]["cmba"]))
        case(CASE_IDS[17], mutated_result(observed, ["acceptance_case_closed"], True))
        case(CASE_IDS[18], mutated_result(observed, ["effect_authorized"], True))
        case(CASE_IDS[19], lambda: require(all(not section["result"]["effect_authorized"]
            and not section["result"]["acceptance_case_closed"]
            for section in (observed, effected)), "AUTHORITY_CEILING"))
    failed = sum(row["status"] != "PASS" for row in results)
    body = {"schema": "mosaic.ucm.r036-cmba-composite-tier1-result.v0.1",
        "cases": len(results), "failed": failed,
        "status": "PASS" if failed == 0 else "HOLD_FOR_REPAIR",
        "results": results, "operator_kit_root": manifest["operator_kit_root"],
        **BOUNDARY}
    result = {**body, "court_root": sha(canonical(body))}
    payload = {"TIER1-RESULT.json": canonical(result) + b"\n",
        "REPORT.md": ("# UCM r036 CMBA composite operator court\n\n"
            f"Status: {result['status']}  \nCases: {len(results)}  \nFailed: {failed}\n").encode(),
        "RUN-TIER1.py": Path(__file__).read_bytes()}
    evidence = out / ("UCM-r036-CMBA-COMPOSITE-TIER1-EVIDENCE-" + result["court_root"][:16] + ".zip")
    write_zip(evidence, payload)
    print(json.dumps({"status": result["status"], "cases": len(results), "failed": failed,
        "court_root": result["court_root"], "evidence": str(evidence),
        "evidence_sha256": sha(evidence.read_bytes()), **BOUNDARY}, sort_keys=True))
    return 0 if failed == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())

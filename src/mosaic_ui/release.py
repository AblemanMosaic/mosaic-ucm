"""Deterministic release pipeline and local candidate attestations."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path
from typing import Any

from .canonical import atomic_write, canonical_bytes, commitment, read_json
from .model import UIRefusal


FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)
class ReleaseRefusal(UIRefusal):
    pass


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(command: list[str], cwd: Path) -> dict[str, Any]:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace")
    combined = result.stdout + result.stderr
    return {
        "command": command[1:] if command and Path(command[0]).resolve() == Path(sys.executable).resolve() else command,
        "exit_code": result.returncode,
        "output_sha256": hashlib.sha256(combined.encode("utf-8")).hexdigest(),
        "output_tail": combined[-2000:],
    }


def _write_zip(path: Path, entries: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, data, compresslevel=9)


def _full_wheel(source: Path, output: Path, version: str) -> Path:
    from .ablate import _wheel_entries

    project = tomllib.loads((source / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    scripts = project.get("scripts", {})
    entries: dict[str, bytes] = {}
    for legal in ("LICENSE", "NOTICE"):
        entries[legal] = (source / legal).read_bytes()
    for package in ("mosaic_ui", "mosaic_ui_std"):
        package_root = source / package
        for path in sorted(package_root.rglob("*"),
                           key=lambda item: item.relative_to(package_root).as_posix()):
            if path.is_file() and "__pycache__" not in path.parts:
                entries[path.relative_to(source).as_posix()] = path.read_bytes()
    wheel = output / f"mosaic_ui-{version}-py3-none-any.whl"
    _write_zip(wheel, _wheel_entries(entries, version=version, scripts=scripts))
    return wheel


def _sbom(source: Path, subjects: list[dict[str, Any]], version: str) -> dict[str, Any]:
    files = []
    for package in ("mosaic_ui", "mosaic_ui_std"):
        package_root = source / package
        for path in sorted(package_root.rglob("*"),
                           key=lambda item: item.relative_to(package_root).as_posix()):
            if path.is_file() and "__pycache__" not in path.parts:
                files.append({
                    "type": "file", "name": path.relative_to(source).as_posix(),
                    "hashes": [{"alg": "SHA-256", "content": _sha(path)}],
                })
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "metadata": {"component": {"type": "library", "name": "mosaic-ui", "version": version}},
        "components": files,
        "properties": [
            {"name": "mosaic:standing", "value": "LOCAL_CANDIDATE"},
            {"name": "mosaic:authority_effect", "value": "NONE"},
            {"name": "mosaic:subjects", "value": json.dumps(subjects, sort_keys=True, separators=(",", ":"))},
        ],
    }


def _bundle(path: Path, entries: dict[str, bytes]) -> None:
    _write_zip(path, entries)
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None or set(archive.namelist()) != set(entries):
            raise ReleaseRefusal("RELEASE_BUNDLE_BUILD_REFUSED", "zip-verification")


def _verify_win32_rtl_witness(directory: Path, gate: dict[str, Any]) -> None:
    native_rtl = read_json(directory / "win32-rtl.json")
    native_rtl_body = dict(native_rtl)
    native_rtl_commitment = native_rtl_body.pop("commitment", None)
    capture = directory / "win32-rtl.png"
    if native_rtl_commitment != commitment("MOSAIC.UI.WIN32_25_KIND_SUFFICIENCY.v0.1", native_rtl_body) \
            or native_rtl_commitment != gate.get("witness_commitment") \
            or native_rtl.get("locale") != "ar" or native_rtl.get("direction") != "RTL" \
            or native_rtl.get("disposition") != "PASS_LOCAL_CANDIDATE" \
            or not capture.is_file() or _sha(capture) != native_rtl.get("capture", {}).get("sha256") \
            or _sha(capture) != gate.get("capture_sha256"):
        raise ReleaseRefusal("RELEASE_WIN32_RTL_WITNESS_REFUSED", "")


def _verify_browser_engine_witness(directory: Path, gate: dict[str, Any]) -> None:
    witness = read_json(directory / "browser-engine-acceptance.json")
    body = dict(witness)
    observed = body.pop("commitment", None)
    rows = witness.get("engines", [])
    engine_ids = [row.get("engine_id") for row in rows] if isinstance(rows, list) else []
    invalid_artifact = False
    for row in rows if isinstance(rows, list) else []:
        for name_key, hash_key in (("dom_artifact", "dom_sha256"), ("screenshot_artifact", "screenshot_sha256")):
            name = row.get(name_key)
            if not isinstance(name, str) or Path(name).name != name:
                invalid_artifact = True
                continue
            path = directory / name
            if not path.is_file() or _sha(path) != row.get(hash_key):
                invalid_artifact = True
    if observed != commitment("MOSAIC.UI.BROWSER_ENGINE_ACCEPTANCE.v0.1", body) \
            or observed != gate.get("witness_commitment") \
            or witness.get("disposition") != "PASS_LOCAL_CANDIDATE" \
            or witness.get("engine_count") != len(rows) or len(rows) < 2 \
            or engine_ids != gate.get("engine_ids") or len(set(engine_ids)) != len(engine_ids) \
            or any(row.get("disposition") != "PASS" for row in rows) \
            or not witness.get("comparisons") \
            or any(row.get("disposition") != "PASS" for row in witness["comparisons"]) \
            or invalid_artifact:
        raise ReleaseRefusal("RELEASE_BROWSER_ENGINE_WITNESS_REFUSED", "")


def _verify_session_custody_witness(directory: Path, gate: dict[str, Any]) -> None:
    witness = read_json(directory / "session-custody-evidence.json")
    body = dict(witness)
    observed = body.pop("commitment", None)
    checks = witness.get("checks", {})
    if observed != commitment("MOSAIC.UI.BROWSER_SESSION_CUSTODY_EVIDENCE.v0.1", body) \
            or observed != gate.get("evidence_commitment") \
            or witness.get("disposition") != "PASS_LOCAL_CANDIDATE" \
            or not isinstance(checks, dict) or not checks or not all(value is True for value in checks.values()) \
            or witness.get("session_count") != gate.get("session_count"):
        raise ReleaseRefusal("RELEASE_SESSION_CUSTODY_WITNESS_REFUSED", "")


def _verify_signature_profile_witness(directory: Path, gate: dict[str, Any]) -> None:
    witness = read_json(directory / "signature-profile-evidence.json")
    body = dict(witness)
    observed = body.pop("commitment", None)
    if observed != commitment("MOSAIC.UI.SIGNATURE_PROFILE_WITNESS.v0.1", body) \
            or observed != gate.get("evidence_commitment") \
            or witness.get("profile_id") != "mosaic-signature" \
            or witness.get("case_count") != gate.get("case_count") \
            or witness.get("disposition") != "PASS_LOCAL_CANDIDATE" \
            or any(case.get("disposition") != "PASS" for case in witness.get("cases", [])):
        raise ReleaseRefusal("RELEASE_SIGNATURE_PROFILE_WITNESS_REFUSED", "")


def _verify_win32_signature_witness(directory: Path, gate: dict[str, Any]) -> None:
    witness = read_json(directory / "win32-signature-profile.json")
    body = dict(witness)
    observed = body.pop("commitment", None)
    rows = witness.get("captures", [])
    artifacts_valid = isinstance(rows, list) and len(rows) == 3
    for row in rows if isinstance(rows, list) else []:
        capture = row.get("capture", {})
        raw_path = capture.get("path")
        name = Path(str(raw_path)).name
        path = directory / name
        artifacts_valid = artifacts_valid and bool(name) and path.is_file() and _sha(path) == capture.get("sha256")
    if observed != commitment("MOSAIC.UI.WIN32_SIGNATURE_PROFILE_WITNESS.v0.1", body) \
            or observed != gate.get("witness_commitment") \
            or witness.get("profile_id") != "mosaic-signature" \
            or witness.get("capture_count") != 3 or not artifacts_valid \
            or witness.get("disposition") != "PASS_LOCAL_CANDIDATE" \
            or any(row.get("disposition") != "PASS_LOCAL_CANDIDATE" for row in rows):
        raise ReleaseRefusal("RELEASE_WIN32_SIGNATURE_PROFILE_WITNESS_REFUSED", "")


def _verify_workbench_authoring_witness(directory: Path, gate: dict[str, Any]) -> None:
    witness = read_json(directory / "workbench-authoring-evidence.json")
    body = dict(witness)
    observed = body.pop("commitment", None)
    cases = witness.get("cases", [])
    if observed != commitment("MOSAIC.UI.WORKBENCH_AUTHORING_WITNESS.v0.1", body) \
            or observed != gate.get("evidence_commitment") \
            or witness.get("case_count") != gate.get("case_count") \
            or witness.get("disposition") != "PASS_LOCAL_CANDIDATE" \
            or not cases or any(case.get("disposition") != "PASS" for case in cases):
        raise ReleaseRefusal("RELEASE_WORKBENCH_AUTHORING_WITNESS_REFUSED", "")


def _verify_signature_native_review(directory: Path, gate: dict[str, Any]) -> None:
    witness = read_json(directory / "signature-native-review.json")
    body = dict(witness)
    observed = body.pop("commitment", None)
    capture = witness.get("capture", {})
    name = Path(str(capture.get("path"))).name
    path = directory / name
    if observed != commitment("MOSAIC.UI.SIGNATURE_NATIVE_REVIEW.v0.1", body) \
            or observed != gate.get("witness_commitment") \
            or witness.get("schema") != "mosaic.ui.signature-native-review.v0.1" \
            or witness.get("realizer") != "WIN32" or witness.get("mode") != "CAPTURE" \
            or witness.get("disposition") != "PASS_LOCAL_CANDIDATE" \
            or witness.get("callback_error_count") != 0 or witness.get("failures") \
            or not name or not path.is_file() or _sha(path) != capture.get("sha256") \
            or _sha(path) != gate.get("capture_sha256"):
        raise ReleaseRefusal("RELEASE_SIGNATURE_NATIVE_REVIEW_REFUSED", "")


def _verify_functional_review_witness(directory: Path, gate: dict[str, Any]) -> None:
    witness = read_json(directory / "signature-functional-review.json")
    body = dict(witness)
    observed = body.pop("commitment", None)
    cases = witness.get("cases", [])
    if observed != commitment("MOSAIC.UI.SIGNATURE_FUNCTIONAL_REVIEW_WITNESS.v0.1", body) \
            or observed != gate.get("witness_commitment") \
            or witness.get("case_count") != gate.get("case_count") \
            or witness.get("disposition") != "PASS_LOCAL_CANDIDATE" \
            or not cases or any(case.get("disposition") != "PASS_LOCAL_CANDIDATE" for case in cases):
        raise ReleaseRefusal("RELEASE_FUNCTIONAL_REVIEW_REFUSED", "")


def _verify_win32_functional_review(directory: Path, gate: dict[str, Any]) -> None:
    witness = read_json(directory / "win32-functional-review.json")
    body = dict(witness)
    observed = body.pop("commitment", None)
    cases = witness.get("cases", [])
    artifacts_valid = isinstance(cases, list) and len(cases) == 3
    for case in cases if isinstance(cases, list) else []:
        capture = case.get("capture", {})
        name = Path(str(capture.get("path"))).name
        path = directory / name
        artifacts_valid = artifacts_valid and bool(name) and path.is_file() and _sha(path) == capture.get("sha256")
    if observed != commitment("MOSAIC.UI.WIN32_FUNCTIONAL_REVIEW_WITNESS.v0.1", body) \
            or observed != gate.get("witness_commitment") or not artifacts_valid \
            or witness.get("disposition") != "PASS_LOCAL_CANDIDATE" \
            or any(case.get("disposition") != "PASS_LOCAL_CANDIDATE" for case in cases):
        raise ReleaseRefusal("RELEASE_WIN32_FUNCTIONAL_REVIEW_REFUSED", "")


def _verify_public_contract_witness(
    directory: Path, contract_gate: dict[str, Any], independence_gate: dict[str, Any],
) -> None:
    witness = read_json(directory / "public-contract-evidence.json")
    body = dict(witness)
    observed = body.pop("commitment", None)
    checks = witness.get("checks", {})
    if observed != commitment("MOSAIC.UI.PUBLIC_CONTRACT_WITNESS.v1", body) \
            or witness.get("schema") != "mosaic.ui.public-contract-witness.v1" \
            or witness.get("disposition") != "PASS_LOCAL_CANDIDATE" \
            or witness.get("authority_effect") != "NONE" \
            or not isinstance(checks, dict) or not checks or not all(value is True for value in checks.values()) \
            or witness.get("contract_commitment") != contract_gate.get("contract_commitment") \
            or observed != contract_gate.get("witness_commitment") \
            or observed != independence_gate.get("witness_commitment") \
            or independence_gate.get("track_a_requires_track_b") is not False:
        raise ReleaseRefusal("RELEASE_PUBLIC_CONTRACT_WITNESS_REFUSED", "")


def _verify_consumer_lifecycle_witness(directory: Path, gate: dict[str, Any], receipt: dict[str, Any]) -> None:
    witness = read_json(directory / "consumer-lifecycle-witness.json")
    body = dict(witness)
    observed = body.pop("commitment", None)
    checks = witness.get("checks", {})
    wheel_subjects = [
        item for item in receipt.get("subjects", [])
        if item.get("media_type") == "application/vnd.python.wheel"
    ]
    if observed != commitment("MOSAIC.UI.INDEPENDENT_CONSUMER_LIFECYCLE.v1", body) \
            or observed != gate.get("witness_commitment") \
            or witness.get("schema") != "mosaic.ui.independent-consumer-lifecycle.v1" \
            or witness.get("disposition") != "PASS_LOCAL_CANDIDATE" \
            or witness.get("authority_effect") != "NONE" \
            or not isinstance(checks, dict) or not checks or not all(value is True for value in checks.values()) \
            or len(wheel_subjects) != 1 \
            or witness.get("candidate", {}).get("wheel_sha256") != wheel_subjects[0].get("sha256"):
        raise ReleaseRefusal("RELEASE_CONSUMER_LIFECYCLE_WITNESS_REFUSED", "")


def verify_release(directory: Path) -> dict[str, Any]:
    directory = directory.resolve()
    receipt = read_json(directory / "release-receipt.json")
    if receipt.get("schema") != "mosaic.ui.release-receipt.v0.1":
        raise ReleaseRefusal("RELEASE_RECEIPT_SCHEMA_REFUSED", "")
    body = dict(receipt)
    observed = body.pop("receipt_commitment", None)
    if observed != commitment("MOSAIC.UI.RELEASE_RECEIPT.v0.1", body):
        raise ReleaseRefusal("RELEASE_RECEIPT_COMMITMENT_REFUSED", "")
    evidence = read_json(directory / "release-evidence.json")
    evidence_body = dict(evidence)
    evidence_commitment = evidence_body.pop("commitment", None)
    if evidence_commitment != commitment("MOSAIC.UI.RELEASE.EVIDENCE.v0.1", evidence_body) \
            or evidence_commitment != receipt["evidence_commitment"]:
        raise ReleaseRefusal("RELEASE_EVIDENCE_COMMITMENT_REFUSED", "")
    performance_gate = evidence.get("gates", {}).get("PERFORMANCE_ENVELOPES")
    if performance_gate is not None:
        performance = read_json(directory / "performance-evidence.json")
        performance_body = dict(performance)
        performance_commitment = performance_body.pop("commitment", None)
        if performance_commitment != commitment("MOSAIC.UI.PERFORMANCE_EVIDENCE.v0.1", performance_body) \
                or performance_commitment != performance_gate.get("evidence_commitment") \
                or performance.get("disposition") != "PASS_LOCAL_CANDIDATE":
            raise ReleaseRefusal("RELEASE_PERFORMANCE_EVIDENCE_REFUSED", "")
    architecture_gate = evidence.get("gates", {}).get("ARCHITECTURE_READINESS")
    if architecture_gate is not None:
        architecture = read_json(directory / "architecture-evidence.json")
        architecture_body = dict(architecture)
        architecture_commitment = architecture_body.pop("commitment", None)
        if architecture_commitment != commitment("MOSAIC.UI.ARCHITECTURE_READINESS_EVIDENCE.v0.1", architecture_body) \
                or architecture_commitment != architecture_gate.get("evidence_commitment") \
                or architecture.get("performance_evidence_commitment") != performance_gate.get("evidence_commitment") \
                or architecture.get("disposition") != "PASS_LOCAL_CANDIDATE":
            raise ReleaseRefusal("RELEASE_ARCHITECTURE_EVIDENCE_REFUSED", "")
    accessibility_gate = evidence.get("gates", {}).get("ACCESSIBILITY_CONTRACT")
    if accessibility_gate is not None:
        accessibility = read_json(directory / "accessibility-evidence.json")
        accessibility_body = dict(accessibility)
        accessibility_commitment = accessibility_body.pop("commitment", None)
        if accessibility_commitment != commitment("MOSAIC.UI.ACCESSIBILITY_EVIDENCE.v0.1", accessibility_body) \
                or accessibility_commitment != accessibility_gate.get("evidence_commitment") \
                or accessibility.get("disposition") != "PASS_LOCAL_CANDIDATE":
            raise ReleaseRefusal("RELEASE_ACCESSIBILITY_EVIDENCE_REFUSED", "")
    localization_gate = evidence.get("gates", {}).get("LOCALIZATION_RTL_CONTRACT")
    if localization_gate is not None:
        localization = read_json(directory / "localization-evidence.json")
        localization_body = dict(localization)
        localization_commitment = localization_body.pop("commitment", None)
        if localization_commitment != commitment("MOSAIC.UI.LOCALIZATION_EVIDENCE.v0.1", localization_body) \
                or localization_commitment != localization_gate.get("evidence_commitment") \
                or localization.get("disposition") != "PASS_LOCAL_CANDIDATE":
            raise ReleaseRefusal("RELEASE_LOCALIZATION_EVIDENCE_REFUSED", "")
    native_rtl_gate = evidence.get("gates", {}).get("WIN32_RTL_NATIVE_WITNESS")
    if native_rtl_gate is not None:
        _verify_win32_rtl_witness(directory, native_rtl_gate)
    browser_engine_gate = evidence.get("gates", {}).get("BROWSER_ENGINE_ACCEPTANCE")
    if browser_engine_gate is not None:
        _verify_browser_engine_witness(directory, browser_engine_gate)
    custody_gate = evidence.get("gates", {}).get("SESSION_BACKUP_RECOVERY")
    if custody_gate is not None:
        _verify_session_custody_witness(directory, custody_gate)
    signature_gate = evidence.get("gates", {}).get("SIGNATURE_PROFILE")
    if signature_gate is not None:
        _verify_signature_profile_witness(directory, signature_gate)
    win32_signature_gate = evidence.get("gates", {}).get("WIN32_SIGNATURE_PROFILE_WITNESS")
    if win32_signature_gate is not None:
        _verify_win32_signature_witness(directory, win32_signature_gate)
    authoring_gate = evidence.get("gates", {}).get("WORKBENCH_AUTHORING")
    if authoring_gate is not None:
        _verify_workbench_authoring_witness(directory, authoring_gate)
    native_review_gate = evidence.get("gates", {}).get("SIGNATURE_NATIVE_REVIEW")
    if native_review_gate is not None:
        _verify_signature_native_review(directory, native_review_gate)
    functional_review_gate = evidence.get("gates", {}).get("FUNCTIONAL_REVIEW_SCENARIOS")
    if functional_review_gate is not None:
        _verify_functional_review_witness(directory, functional_review_gate)
    native_functional_gate = evidence.get("gates", {}).get("WIN32_FUNCTIONAL_REVIEW")
    if native_functional_gate is not None:
        _verify_win32_functional_review(directory, native_functional_gate)
    public_contract_gate = evidence.get("gates", {}).get("PUBLIC_CONTRACT_25_KIND_FREEZE")
    independence_gate = evidence.get("gates", {}).get("TRACK_A_OPTIONAL_DOMAIN_INDEPENDENCE")
    if public_contract_gate is not None or independence_gate is not None:
        if public_contract_gate is None or independence_gate is None:
            raise ReleaseRefusal("RELEASE_PUBLIC_CONTRACT_GATE_PAIR_REFUSED", "")
        _verify_public_contract_witness(directory, public_contract_gate, independence_gate)
    consumer_lifecycle_gate = evidence.get("gates", {}).get("INDEPENDENT_CONSUMER_LIFECYCLE")
    if consumer_lifecycle_gate is not None:
        _verify_consumer_lifecycle_witness(directory, consumer_lifecycle_gate, receipt)
    signing = read_json(directory / "SIGNING-REQUEST.json")
    signing_body = dict(signing)
    signing_commitment = signing_body.pop("request_commitment", None)
    if signing_commitment != commitment("MOSAIC.UI.RELEASE.SIGNING_REQUEST.v0.1", signing_body) \
            or signing_commitment != receipt["signing_request"]:
        raise ReleaseRefusal("RELEASE_SIGNING_REQUEST_REFUSED", "")
    provenance = read_json(directory / "provenance.intoto.json")
    if signing["provenance_commitment"] != commitment("MOSAIC.UI.RELEASE.PROVENANCE.v0.1", provenance):
        raise ReleaseRefusal("RELEASE_PROVENANCE_REFUSED", "")
    from .human_review import make_human_review_request

    human_review_request = read_json(directory / "HUMAN-REVIEW-REQUEST.json")
    expected_human_review_request = make_human_review_request(receipt["subjects"], evidence_commitment)
    if human_review_request != expected_human_review_request:
        raise ReleaseRefusal("RELEASE_HUMAN_REVIEW_REQUEST_REFUSED", "")
    for subject in receipt["subjects"]:
        path = directory / subject["name"]
        if not path.is_file() or path.stat().st_size != subject["bytes"] or _sha(path) != subject["sha256"]:
            raise ReleaseRefusal("RELEASE_SUBJECT_REFUSED", subject["name"])
    bundle = directory / receipt["bundle"]["name"]
    if not bundle.is_file() or _sha(bundle) != receipt["bundle"]["sha256"]:
        raise ReleaseRefusal("RELEASE_BUNDLE_REFUSED", receipt["bundle"]["name"])
    with zipfile.ZipFile(bundle) as archive:
        if archive.testzip() is not None:
            raise ReleaseRefusal("RELEASE_BUNDLE_REFUSED", "corrupt")
        expected = {path.name for path in directory.iterdir() if path.is_file() and path.name not in {bundle.name, "release-receipt.json"}}
        if set(archive.namelist()) != expected:
            raise ReleaseRefusal("RELEASE_BUNDLE_INVENTORY_REFUSED", ",".join(sorted(set(archive.namelist()) ^ expected)))
        for name in expected:
            if archive.read(name) != (directory / name).read_bytes():
                raise ReleaseRefusal("RELEASE_BUNDLE_MEMBER_REFUSED", name)
    return {
        "schema": "mosaic.ui.release-verification.v0.1", "status": "PASS",
        "version": receipt["version"], "subject_count": len(receipt["subjects"]),
        "bundle_sha256": receipt["bundle"]["sha256"], "receipt_commitment": observed,
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
    }


def build_release(source: Path, output: Path, *, run_native: bool = False,
                  browser_engines: tuple[str, ...] = (),
                  upgrade_from_wheel: Path | None = None) -> dict[str, Any]:
    source = source.resolve()
    output = output.resolve()
    if output.exists():
        raise ReleaseRefusal("RELEASE_OUTPUT_EXISTS", str(output))
    project = tomllib.loads((source / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = str(project["version"])
    policy = read_json(source / "mosaic_ui" / "source" / "release-policy.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mosaic-ui-release-", dir=output.parent) as raw:
        work = Path(raw)
        tests = _run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], source)
        match = re.search(r"Ran (\d+) tests", tests["output_tail"])
        tests["test_count"] = int(match.group(1)) if match else None
        tests["status"] = "PASS" if tests["exit_code"] == 0 and tests["test_count"] else "FAIL"
        if tests["status"] != "PASS":
            raise ReleaseRefusal("RELEASE_TESTS_REFUSED", tests["output_tail"])

        for name in ("a", "b"):
            built = _run([sys.executable, "tools/build_dist.py", "--output", str(work / f"dist-{name}")], source)
            if built["exit_code"] != 0:
                raise ReleaseRefusal("RELEASE_SOURCE_BUILD_REFUSED", built["output_tail"])
        archive_a = next((work / "dist-a").glob("*.zip"))
        archive_b = next((work / "dist-b").glob("*.zip"))
        if archive_a.read_bytes() != archive_b.read_bytes():
            raise ReleaseRefusal("RELEASE_SOURCE_REPRO_REFUSED", "")

        wheel_a = _full_wheel(source, work / "wheel-a", version)
        wheel_b = _full_wheel(source, work / "wheel-b", version)
        if wheel_a.read_bytes() != wheel_b.read_bytes():
            raise ReleaseRefusal("RELEASE_WHEEL_REPRO_REFUSED", "")
        wheel_install_root = work / "wheel-install"
        wheel_install = _run([
            sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(wheel_install_root), str(wheel_a),
        ], work)
        if wheel_install["exit_code"] != 0:
            raise ReleaseRefusal("RELEASE_WHEEL_INSTALL_REFUSED", wheel_install["output_tail"])
        installed_pilot = _run([
            sys.executable, "-c",
            "import sys; sys.path.insert(0, sys.argv[1]); import mosaic_ui; "
            "from mosaic_ui.pilot import pilot_witness; from mosaic_ui.web_distribution import web_manifest; "
            "w=pilot_witness(); web=web_manifest(); "
            "assert mosaic_ui.__version__ == sys.argv[2]; assert w['disposition'] == 'PASS_LOCAL_CANDIDATE'; "
            "assert all(r['disposition'] == 'COMPLETE' for r in w['runtime']['receipts']); "
            "assert len(web['entries']) == 3 and not web['runtime_dependencies'] and not web['framework_dependencies']",
            str(wheel_install_root), version,
        ], work)
        if installed_pilot["exit_code"] != 0:
            raise ReleaseRefusal("RELEASE_WHEEL_RUNTIME_REFUSED", installed_pilot["output_tail"])

        from .adoption import build_from_manifest, scaffold_consumer, verify_independent_consumer
        from .public_contract import public_contract_witness

        manifest_consumer = work / "manifest-consumer"
        scaffold_consumer(manifest_consumer)
        manifest_package = build_from_manifest(manifest_consumer / "mosaic-ui.json", work / "manifest-package")
        independent_consumer = verify_independent_consumer(wheel_a, work / "independent-consumer")
        public_contract = public_contract_witness()
        atomic_write(work / "public-contract-evidence.json", canonical_bytes(public_contract) + b"\n")
        consumer_lifecycle: dict[str, Any] = {"disposition": "NOT_REQUESTED"}
        if upgrade_from_wheel is not None:
            from .consumer_lifecycle import run_consumer_lifecycle

            consumer_lifecycle = run_consumer_lifecycle(
                upgrade_from_wheel.resolve(), wheel_a, work / "consumer-lifecycle",
            )

        extract = work / "extracted"
        with zipfile.ZipFile(archive_a) as archive:
            archive.extractall(extract)
        extracted_root = extract / f"mosaic-ui-{version}"
        extracted_verify = _run([sys.executable, "verify_dist.py"], extracted_root)
        if extracted_verify["exit_code"] != 0:
            raise ReleaseRefusal("RELEASE_EXTRACTED_VERIFY_REFUSED", extracted_verify["output_tail"])

        pilot = _run([sys.executable, "-c", "from mosaic_ui.pilot import pilot_witness; assert pilot_witness()['disposition'] == 'PASS_LOCAL_CANDIDATE'"], source)
        protocol = _run([sys.executable, "-c", "from mosaic_ui.pilot import build_payload; from mosaic_ui.realizer import create_realizer,conformance_witness; r=create_realizer('HEADLESS',build_payload()); assert conformance_witness(r)['disposition'] == 'PASS_LOCAL_CANDIDATE'"], source)
        browser_protocol = _run([sys.executable, "-c", "from mosaic_ui.sufficiency import build_sufficiency_payload; from mosaic_ui.realizer import create_realizer,conformance_witness; r=create_realizer('BROWSER',build_sufficiency_payload()); assert conformance_witness(r,viewports=((1280,800),(800,600)))['disposition'] == 'PASS_LOCAL_CANDIDATE'"], source)
        sufficiency = _run([sys.executable, "-c", "from mosaic_ui.sufficiency import build_sufficiency_payload; from mosaic_ui.realizer import create_realizer,conformance_witness; p=build_sufficiency_payload(); assert all(conformance_witness(create_realizer(i,p),viewports=((1280,800),(800,600)))['disposition']=='PASS_LOCAL_CANDIDATE' for i in ('HEADLESS','BROWSER'))"], source)
        win32_parity = _run([sys.executable, "-c", "from mosaic_ui.components import load_handlers; from mosaic_ui_std.catalog import load_runtime_catalog; c=load_runtime_catalog(); h=load_handlers(c); kinds=[x['kind'] for x in c['components']]; native={'COMBOBOX','DATA_GRID','LIST','MENU','NAVIGATION','NOTIFICATION','RADIO_GROUP','TREE'}; assert len(kinds)==25 and all('WIN32' in x['realized_by'] and x['kind'] in h for x in c['components']) and all(callable(h[k].build) for k in native)"], source)
        hosted_browser = _run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_browser_host.py", "-v"], source)
        shared_browser = _run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_browser_session_store.py", "-v"], source)
        framework_bindings = _run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_framework_bindings.py", "-v"], source)
        cold_boot = _run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_orient.py", "-v"], source)
        localization_tests = _run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_localization.py", "-v"], source)
        visual = _run([sys.executable, "-c", "from mosaic_ui.visual_certification import verify_baseline; assert verify_baseline()['disposition']=='PASS_LOCAL_CANDIDATE'"], source)
        integration_checks = (pilot, protocol, browser_protocol, sufficiency, win32_parity,
                              hosted_browser, shared_browser, framework_bindings, cold_boot,
                              localization_tests, visual)
        if any(item["exit_code"] != 0 for item in integration_checks):
            raise ReleaseRefusal("RELEASE_INTEGRATION_REFUSED", "".join(item["output_tail"] for item in integration_checks))

        from .performance import run_performance_gate

        performance = run_performance_gate(
            source / "mosaic_ui" / "source" / "performance-policy.json",
            output=work / "performance-evidence.json",
        )
        if performance["disposition"] != "PASS_LOCAL_CANDIDATE":
            raise ReleaseRefusal("RELEASE_PERFORMANCE_REFUSED", json.dumps(performance["failures"], sort_keys=True))

        from .architecture import architecture_witness

        architecture = architecture_witness(
            performance["commitment"], output=work / "architecture-evidence.json",
        )
        if architecture["disposition"] != "PASS_LOCAL_CANDIDATE":
            raise ReleaseRefusal("RELEASE_ARCHITECTURE_REFUSED", json.dumps(architecture["checks"], sort_keys=True))

        from .accessibility import accessibility_witness

        accessibility = accessibility_witness()
        if accessibility["disposition"] != "PASS_LOCAL_CANDIDATE":
            raise ReleaseRefusal("RELEASE_ACCESSIBILITY_REFUSED", json.dumps(accessibility["checks"], sort_keys=True))
        atomic_write(work / "accessibility-evidence.json", canonical_bytes(accessibility) + b"\n")

        from .localization import localization_evidence
        from .sufficiency import build_sufficiency_payload

        localization = localization_evidence(build_sufficiency_payload())
        if localization["disposition"] != "PASS_LOCAL_CANDIDATE":
            raise ReleaseRefusal("RELEASE_LOCALIZATION_REFUSED", json.dumps(localization["failures"], sort_keys=True))
        atomic_write(work / "localization-evidence.json", canonical_bytes(localization) + b"\n")

        from .session_custody import session_custody_witness

        session_custody = session_custody_witness(output=work / "session-custody-evidence.json")
        if session_custody["disposition"] != "PASS_LOCAL_CANDIDATE":
            raise ReleaseRefusal("RELEASE_SESSION_CUSTODY_REFUSED", json.dumps(session_custody["checks"], sort_keys=True))

        from .signature_profile import signature_profile_witness

        signature_profile = signature_profile_witness()
        if signature_profile["disposition"] != "PASS_LOCAL_CANDIDATE":
            raise ReleaseRefusal("RELEASE_SIGNATURE_PROFILE_REFUSED", "")
        atomic_write(work / "signature-profile-evidence.json", canonical_bytes(signature_profile) + b"\n")

        from .workbench import authoring_witness

        workbench_authoring = authoring_witness()
        if workbench_authoring["disposition"] != "PASS_LOCAL_CANDIDATE":
            raise ReleaseRefusal("RELEASE_WORKBENCH_AUTHORING_REFUSED", "")
        atomic_write(work / "workbench-authoring-evidence.json", canonical_bytes(workbench_authoring) + b"\n")

        from .signature_review_host import functional_review_witness

        functional_review = functional_review_witness(work / "functional-review-scenarios")
        if functional_review["disposition"] != "PASS_LOCAL_CANDIDATE":
            raise ReleaseRefusal("RELEASE_FUNCTIONAL_REVIEW_REFUSED", "")
        atomic_write(work / "signature-functional-review.json", canonical_bytes(functional_review) + b"\n")

        browser_engine_evidence: dict[str, Any] = {"disposition": "NOT_REQUESTED", "engines": []}
        browser_engine_output = work / "browser-engine-evidence"
        if browser_engines:
            from .browser_engine_acceptance import run_browser_engine_acceptance

            browser_engine_evidence = run_browser_engine_acceptance(browser_engines, browser_engine_output)
            if browser_engine_evidence["disposition"] != "PASS_LOCAL_CANDIDATE":
                raise ReleaseRefusal("RELEASE_BROWSER_ENGINE_ACCEPTANCE_REFUSED", "")

        from .release_acceptance import create_signature_envelope, verify_signature_envelope

        signing_self_test = work / "signing-self-test"
        signing_self_test.mkdir()
        keygen = _run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(signing_self_test / "private.pem")], work)
        pubout = _run(["openssl", "pkey", "-in", str(signing_self_test / "private.pem"), "-pubout",
                       "-out", str(signing_self_test / "public.pem")], work) if keygen["exit_code"] == 0 else {"exit_code": 1, "output_tail": "keygen failed", "output_sha256": ""}
        self_test_request = {"schema": "mosaic.ui.release-signing-request.v0.1", "request_commitment": "0" * 64}
        atomic_write(signing_self_test / "request.json", canonical_bytes(self_test_request) + b"\n")
        try:
            create_signature_envelope(signing_self_test / "request.json", signing_self_test / "private.pem",
                                      signing_self_test / "public.pem", "LOCAL-CRYPTOGRAPHIC-SELF-TEST",
                                      signing_self_test / "envelope.json")
            signature_test = verify_signature_envelope(signing_self_test / "request.json", signing_self_test / "envelope.json")
        except (UIRefusal, OSError, ValueError) as exc:
            raise ReleaseRefusal("RELEASE_SIGNATURE_VERIFIER_REFUSED", str(exc)) from exc
        if keygen["exit_code"] != 0 or pubout["exit_code"] != 0 or signature_test["status"] != "CRYPTOGRAPHICALLY_VALID":
            raise ReleaseRefusal("RELEASE_SIGNATURE_VERIFIER_REFUSED", keygen["output_tail"] + pubout["output_tail"])

        native: dict[str, Any] = {"status": "NOT_REQUESTED", "claim_boundary": "NO_NATIVE_EVIDENCE_IN_THIS_RELEASE_RUN"}
        pilot_native: dict[str, Any] = {"status": "NOT_REQUESTED"}
        win32_sufficiency: dict[str, Any] = {"status": "NOT_REQUESTED"}
        win32_rtl: dict[str, Any] = {"status": "NOT_REQUESTED"}
        win32_signature: dict[str, Any] = {"status": "NOT_REQUESTED"}
        signature_native_review: dict[str, Any] = {"status": "NOT_REQUESTED"}
        win32_functional_review: dict[str, Any] = {"status": "NOT_REQUESTED"}
        if run_native:
            native = _run([
                sys.executable, "-m", "mosaic_ui.conformance_app", "--output", str(work / "native-witness.json"),
                "--screenshot", str(work / "native-conformance.png"),
            ], source)
            native["status"] = "PASS" if native["exit_code"] == 0 else "FAIL"
            if native["status"] != "PASS":
                raise ReleaseRefusal("RELEASE_NATIVE_REFUSED", native["output_tail"])
            pilot_native = _run([
                sys.executable, "-m", "mosaic_ui.cli", "--output", str(work / "pilot-native.json"),
                "pilot", "--native", "--screenshot", str(work / "pilot-native.png"),
                "--width", "1100", "--height", "760",
            ], source)
            pilot_native["status"] = "PASS" if pilot_native["exit_code"] == 0 else "FAIL"
            if pilot_native["status"] != "PASS":
                raise ReleaseRefusal("RELEASE_PILOT_NATIVE_REFUSED", pilot_native["output_tail"])
            win32_sufficiency = _run([
                sys.executable, "tools/win32_sufficiency_witness.py",
                "--output", str(work / "win32-25-kind.json"),
                "--screenshot", str(work / "win32-25-kind.png"),
            ], source)
            win32_sufficiency["status"] = "PASS" if win32_sufficiency["exit_code"] == 0 else "FAIL"
            if win32_sufficiency["status"] != "PASS":
                raise ReleaseRefusal("RELEASE_WIN32_SUFFICIENCY_REFUSED", win32_sufficiency["output_tail"])
            win32_rtl = _run([
                sys.executable, "tools/win32_sufficiency_witness.py", "--locale", "ar",
                "--output", str(work / "win32-rtl.json"),
                "--screenshot", str(work / "win32-rtl.png"),
            ], source)
            win32_rtl["status"] = "PASS" if win32_rtl["exit_code"] == 0 else "FAIL"
            if win32_rtl["status"] != "PASS":
                raise ReleaseRefusal("RELEASE_WIN32_RTL_REFUSED", win32_rtl["output_tail"])
            win32_signature = _run([
                sys.executable, "tools/win32_signature_witness.py",
                "--output-dir", str(work), "--receipt", str(work / "win32-signature-profile.json"),
            ], source)
            win32_signature["status"] = "PASS" if win32_signature["exit_code"] == 0 else "FAIL"
            if win32_signature["status"] != "PASS":
                raise ReleaseRefusal("RELEASE_WIN32_SIGNATURE_REFUSED", win32_signature["output_tail"])
            signature_native_review = _run([
                sys.executable, "-m", "mosaic_ui.signature_review", "--realizer", "WIN32",
                "--mode", "conformance",
                "--composition", "data-workspace", "--theme", "signature-dark",
                "--density", "comfortable", "--width", "1280", "--height", "800",
                "--capture", str(work / "signature-native-review.png"),
                "--output", str(work / "signature-native-review.json"),
            ], source)
            signature_native_review["status"] = "PASS" if signature_native_review["exit_code"] == 0 else "FAIL"
            if signature_native_review["status"] != "PASS":
                raise ReleaseRefusal("RELEASE_SIGNATURE_NATIVE_REVIEW_REFUSED", signature_native_review["output_tail"])
            win32_functional_review = _run([
                sys.executable, "tools/win32_functional_review_witness.py",
                "--output-dir", str(work), "--receipt", str(work / "win32-functional-review.json"),
            ], source)
            win32_functional_review["status"] = "PASS" if win32_functional_review["exit_code"] == 0 else "FAIL"
            if win32_functional_review["status"] != "PASS":
                raise ReleaseRefusal("RELEASE_WIN32_FUNCTIONAL_REVIEW_REFUSED", win32_functional_review["output_tail"])

        stage = work / "stage"
        stage.mkdir()
        source_zip = stage / archive_a.name
        wheel = stage / wheel_a.name
        shutil.copyfile(archive_a, source_zip)
        shutil.copyfile(wheel_a, wheel)
        subjects = [
            {"name": source_zip.name, "sha256": _sha(source_zip), "bytes": source_zip.stat().st_size, "media_type": "application/zip"},
            {"name": wheel.name, "sha256": _sha(wheel), "bytes": wheel.stat().st_size, "media_type": "application/vnd.python.wheel"},
        ]
        gates = {
            "UNIT_TESTS": {"status": tests["status"], "test_count": tests["test_count"], "output_sha256": tests["output_sha256"]},
            "SOURCE_ARCHIVE_REPRODUCIBLE": {"status": "PASS", "sha256": subjects[0]["sha256"]},
            "WHEEL_REPRODUCIBLE": {"status": "PASS", "sha256": subjects[1]["sha256"]},
            "WHEEL_INSTALL": {"status": "PASS", "pip_output_sha256": wheel_install["output_sha256"],
                              "runtime_output_sha256": installed_pilot["output_sha256"]},
            "EXTRACTED_DISTRIBUTION_VERIFY": {"status": "PASS", "output_sha256": extracted_verify["output_sha256"]},
            "PILOT_INTEGRATION": {"status": "PASS", "output_sha256": pilot["output_sha256"]},
            "REALIZER_PROTOCOL_CONFORMANCE": {"status": "PASS", "output_sha256": protocol["output_sha256"]},
            "BROWSER_REALIZER_CONFORMANCE": {"status": "PASS", "output_sha256": browser_protocol["output_sha256"]},
            "STANDARD_UI_SUFFICIENCY": {"status": "PASS", "output_sha256": sufficiency["output_sha256"], "component_count": 25},
            "WIN32_25_KIND_PARITY": {"status": "PASS", "output_sha256": win32_parity["output_sha256"], "component_count": 25},
            "PUBLIC_CONTRACT_25_KIND_FREEZE": {
                "status": "PASS", "contract_id": public_contract["contract_id"],
                "contract_commitment": public_contract["contract_commitment"],
                "witness_commitment": public_contract["commitment"],
                "component_count": public_contract["component_count"],
            },
            "TRACK_A_OPTIONAL_DOMAIN_INDEPENDENCE": {
                "status": "PASS", "witness_commitment": public_contract["commitment"],
                "track_a_requires_track_b": False,
                "excluded_optional_pathways": public_contract["excluded_optional_pathways"],
            },
            "HOSTED_BROWSER_ARCHITECTURE": {"status": "PASS", "output_sha256": hosted_browser["output_sha256"]},
            "SHARED_SESSION_STORAGE": {"status": "PASS", "output_sha256": shared_browser["output_sha256"],
                                       "backend": "SQLITE_WAL", "scope": "SAME_FILESYSTEM_MULTI_WORKER"},
            "SESSION_BACKUP_RECOVERY": {
                "status": "PASS", "evidence_commitment": session_custody["commitment"],
                "session_count": session_custody["session_count"], "scope": "LOCAL_SQLITE_ONLINE_BACKUP_RESTORE",
            },
            "SOVEREIGN_WEB_RUNTIME": {"status": "PASS", "output_sha256": framework_bindings["output_sha256"],
                                      "interface": "WEB_COMPONENT_AND_STANDARD_ES_MODULE", "dependency_count": 0},
            "OPTIONAL_FRAMEWORK_ADAPTER_BOUNDARY": {"status": "PASS", "output_sha256": framework_bindings["output_sha256"],
                                                    "frameworks": ["react", "vue", "svelte"]},
            "AGENT_COLD_BOOT": {"status": "PASS", "output_sha256": cold_boot["output_sha256"]},
            "ACCESSIBILITY_CONTRACT": {"status": "PASS", "evidence_commitment": accessibility["commitment"],
                                       "component_count": len(accessibility["covered_component_kinds"])},
            "LOCALIZATION_RTL_CONTRACT": {
                "status": "PASS", "output_sha256": localization_tests["output_sha256"],
                "evidence_commitment": localization["commitment"],
                "locales": localization["supported_locales"], "directions": localization["directions"],
            },
            "BROWSER_ENGINE_ACCEPTANCE": {
                "status": "PASS" if browser_engine_evidence["disposition"] == "PASS_LOCAL_CANDIDATE" else "NOT_REQUESTED",
                "witness_commitment": browser_engine_evidence.get("commitment"),
                "engine_ids": [row["engine_id"] for row in browser_engine_evidence.get("engines", [])],
                "engine_family": "CHROMIUM_CLI",
            },
            "VISUAL_CERTIFICATION": {"status": "PASS", "output_sha256": visual["output_sha256"], "case_count": 360},
            "SIGNATURE_PROFILE": {
                "status": "PASS", "profile_id": signature_profile["profile_id"],
                "case_count": signature_profile["case_count"],
                "evidence_commitment": signature_profile["commitment"],
            },
            "WORKBENCH_AUTHORING": {
                "status": "PASS", "case_count": workbench_authoring["case_count"],
                "evidence_commitment": workbench_authoring["commitment"],
            },
            "FUNCTIONAL_REVIEW_SCENARIOS": {
                "status": "PASS", "case_count": functional_review["case_count"],
                "witness_commitment": functional_review["commitment"],
            },
            "PERFORMANCE_ENVELOPES": {
                "status": "PASS", "case_count": len(performance["cases"]),
                "node_counts": [case["node_count"] for case in performance["cases"]],
                "evidence_commitment": performance["commitment"],
            },
            "ARCHITECTURE_READINESS": {
                "status": "PASS", "check_count": len(architecture["checks"]),
                "evidence_commitment": architecture["commitment"],
            },
            "MANIFEST_PACKAGE": {"status": "PASS", "receipt_commitment": manifest_package["commitment"],
                                 "profile_root": manifest_package["profile_root"]},
            "INDEPENDENT_CONSUMER": {"status": "PASS", "receipt_commitment": independent_consumer["commitment"],
                                     "wheel_sha256": independent_consumer["wheel_sha256"]},
            "INDEPENDENT_CONSUMER_LIFECYCLE": {
                "status": "PASS" if consumer_lifecycle["disposition"] == "PASS_LOCAL_CANDIDATE" else "NOT_REQUESTED",
                "witness_commitment": consumer_lifecycle.get("commitment"),
                "baseline_wheel_sha256": consumer_lifecycle.get("baseline", {}).get("wheel_sha256"),
                "candidate_wheel_sha256": consumer_lifecycle.get("candidate", {}).get("wheel_sha256"),
            },
            "SECOND_HOST_KIT": {"status": "PASS", "protocol": "mosaic.ui.second-host-request.v0.1"},
            "EXTERNAL_SIGNING_KIT": {"status": "PASS", "algorithm": "ED25519",
                                     "self_test_envelope": signature_test["envelope_commitment"]},
            "RELEASE_BUNDLE_VERIFY": {"status": "PENDING_SELF_CHECK"},
            "NATIVE_CONFORMANCE": {"status": native["status"]},
            "PILOT_NATIVE": {"status": pilot_native["status"]},
            "WIN32_25_KIND_NATIVE_WITNESS": {"status": win32_sufficiency["status"]},
            "WIN32_SIGNATURE_PROFILE_WITNESS": {
                "status": win32_signature["status"],
                "witness_commitment": read_json(work / "win32-signature-profile.json")["commitment"] if run_native else None,
                "capture_count": 3 if run_native else 0,
            },
            "SIGNATURE_NATIVE_REVIEW": {
                "status": signature_native_review["status"],
                "witness_commitment": read_json(work / "signature-native-review.json")["commitment"] if run_native else None,
                "capture_sha256": _sha(work / "signature-native-review.png") if run_native else None,
            },
            "WIN32_FUNCTIONAL_REVIEW": {
                "status": win32_functional_review["status"],
                "witness_commitment": read_json(work / "win32-functional-review.json")["commitment"] if run_native else None,
                "capture_count": 3 if run_native else 0,
            },
            "WIN32_RTL_NATIVE_WITNESS": {
                "status": win32_rtl["status"],
                "witness_commitment": read_json(work / "win32-rtl.json")["commitment"] if run_native else None,
                "capture_sha256": _sha(work / "win32-rtl.png") if run_native else None,
                "locale": "ar", "direction": "RTL",
            },
        }
        missing = sorted(set(policy["required_gates"]) - set(gates))
        failed = sorted(name for name in policy["required_gates"] if name != "RELEASE_BUNDLE_VERIFY" and gates[name]["status"] != "PASS")
        if missing or failed:
            raise ReleaseRefusal("RELEASE_POLICY_REFUSED", json.dumps({"missing": missing, "failed": failed}))
        sbom = _sbom(source, subjects, version)
        provenance = {
            "_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": item["name"], "digest": {"sha256": item["sha256"]}} for item in subjects],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {
                "buildDefinition": {"buildType": "mosaic.ui.local-release.v0.1", "externalParameters": {
                                        "version": version, "native": run_native,
                                        "browser_engines": [value.partition("=")[0] for value in browser_engines]},
                                    "internalParameters": {"policy_id": policy["policy_id"]},
                                    "resolvedDependencies": ([{
                                        "uri": "mosaic-ui:upgrade-baseline-wheel",
                                        "digest": {"sha256": consumer_lifecycle["baseline"]["wheel_sha256"]},
                                    }] if consumer_lifecycle.get("baseline") else [])},
                "runDetails": {"builder": {"id": "mosaic-ui/release.py@0.21"},
                               "metadata": {"invocationId": commitment("MOSAIC.UI.RELEASE.INVOCATION.v0.1", subjects)}},
            },
            "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
            "claim_boundary": "SLSA_SHAPED_LOCAL_ATTESTATION_NOT_EXTERNAL_BUILDER_CERTIFICATION",
        }
        from .human_review import make_human_review_request
        from .release_acceptance import acceptance_subject_root, make_second_host_request

        evidence = {"schema": "mosaic.ui.release-evidence.v0.1", "policy": policy, "gates": gates,
                    "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE"}
        evidence["commitment"] = commitment("MOSAIC.UI.RELEASE.EVIDENCE.v0.1", evidence)
        signing = {
            "schema": "mosaic.ui.release-signing-request.v0.1", "algorithm": "EXTERNAL_SIGNER_REQUIRED",
            "subjects": subjects, "provenance_commitment": commitment("MOSAIC.UI.RELEASE.PROVENANCE.v0.1", provenance),
            "acceptance_subject_root": acceptance_subject_root(subjects, evidence["commitment"]),
            "signature_status": "UNSIGNED", "standing": "LOCAL_CANDIDATE", "authority_effect": "NONE",
        }
        signing["request_commitment"] = commitment("MOSAIC.UI.RELEASE.SIGNING_REQUEST.v0.1", signing)
        second_host_request = make_second_host_request(subjects, evidence["commitment"])
        human_review_request = make_human_review_request(subjects, evidence["commitment"])
        documents = {
            "SBOM.cdx.json": canonical_bytes(sbom) + b"\n",
            "provenance.intoto.json": canonical_bytes(provenance) + b"\n",
            "release-evidence.json": canonical_bytes(evidence) + b"\n",
            "SIGNING-REQUEST.json": canonical_bytes(signing) + b"\n",
            "SECOND-HOST-REQUEST.json": canonical_bytes(second_host_request) + b"\n",
            "HUMAN-REVIEW-REQUEST.json": canonical_bytes(human_review_request) + b"\n",
            "manifest-package-receipt.json": canonical_bytes({key: value for key, value in manifest_package.items() if key != "output_dir"}) + b"\n",
            "independent-consumer-receipt.json": canonical_bytes({key: value for key, value in independent_consumer.items() if key != "consumer_dir"}) + b"\n",
            "performance-evidence.json": (work / "performance-evidence.json").read_bytes(),
            "architecture-evidence.json": (work / "architecture-evidence.json").read_bytes(),
            "accessibility-evidence.json": (work / "accessibility-evidence.json").read_bytes(),
            "localization-evidence.json": (work / "localization-evidence.json").read_bytes(),
            "session-custody-evidence.json": (work / "session-custody-evidence.json").read_bytes(),
            "signature-profile-evidence.json": (work / "signature-profile-evidence.json").read_bytes(),
            "workbench-authoring-evidence.json": (work / "workbench-authoring-evidence.json").read_bytes(),
            "signature-functional-review.json": (work / "signature-functional-review.json").read_bytes(),
            "public-contract-evidence.json": (work / "public-contract-evidence.json").read_bytes(),
            "consumer-lifecycle-witness.json": (work / "consumer-lifecycle" / "consumer-lifecycle-witness.json").read_bytes(),
        }
        if run_native:
            for name in ("native-witness.json", "native-conformance.png", "pilot-native.json", "pilot-native.png",
                         "win32-25-kind.json", "win32-25-kind.png", "win32-rtl.json", "win32-rtl.png",
                         "win32-signature-profile.json", "signature-native-review.json", "signature-native-review.png",
                         "win32-functional-review.json", "functional-data-workspace.png",
                         "functional-operational-dashboard.png", "functional-settings-workflow.png",
                         "mosaic-signature-data-workspace-signature-dark-comfortable.png",
                         "mosaic-signature-operational-dashboard-signature-dark-comfortable.png",
                         "mosaic-signature-settings-workflow-signature-dark-comfortable.png"):
                documents[name] = (work / name).read_bytes()
        if browser_engine_evidence["disposition"] == "PASS_LOCAL_CANDIDATE":
            documents["browser-engine-acceptance.json"] = (browser_engine_output / "browser-engine-acceptance.json").read_bytes()
            for row in browser_engine_evidence["engines"]:
                for name in (row["dom_artifact"], row["screenshot_artifact"]):
                    documents[name] = (browser_engine_output / name).read_bytes()
        for name, data in documents.items():
            atomic_write(stage / name, data)
        bundle_name = f"mosaic-ui-{version}-release-candidate.zip"
        bundle = stage / bundle_name
        bundle_entries = {item["name"]: (stage / item["name"]).read_bytes() for item in subjects}
        bundle_entries.update(documents)
        _bundle(bundle, bundle_entries)
        gates["RELEASE_BUNDLE_VERIFY"] = {"status": "PASS", "member_count": len(bundle_entries)}
        # Rebuild once with the self-check result, then verify the final bytes unchanged thereafter.
        evidence["gates"] = gates
        evidence.pop("commitment")
        evidence["commitment"] = commitment("MOSAIC.UI.RELEASE.EVIDENCE.v0.1", evidence)
        signing = {
            "schema": "mosaic.ui.release-signing-request.v0.1", "algorithm": "EXTERNAL_SIGNER_REQUIRED",
            "subjects": subjects, "provenance_commitment": commitment("MOSAIC.UI.RELEASE.PROVENANCE.v0.1", provenance),
            "acceptance_subject_root": acceptance_subject_root(subjects, evidence["commitment"]),
            "signature_status": "UNSIGNED", "standing": "LOCAL_CANDIDATE", "authority_effect": "NONE",
        }
        signing["request_commitment"] = commitment("MOSAIC.UI.RELEASE.SIGNING_REQUEST.v0.1", signing)
        second_host_request = make_second_host_request(subjects, evidence["commitment"])
        human_review_request = make_human_review_request(subjects, evidence["commitment"])
        documents["release-evidence.json"] = canonical_bytes(evidence) + b"\n"
        documents["SIGNING-REQUEST.json"] = canonical_bytes(signing) + b"\n"
        documents["SECOND-HOST-REQUEST.json"] = canonical_bytes(second_host_request) + b"\n"
        documents["HUMAN-REVIEW-REQUEST.json"] = canonical_bytes(human_review_request) + b"\n"
        for name in ("release-evidence.json", "SIGNING-REQUEST.json", "SECOND-HOST-REQUEST.json",
                     "HUMAN-REVIEW-REQUEST.json"):
            atomic_write(stage / name, documents[name])
        bundle.unlink()
        bundle_entries.update(documents)
        _bundle(bundle, bundle_entries)
        receipt = {
            "schema": "mosaic.ui.release-receipt.v0.1", "name": project["name"], "version": version,
            "policy_id": policy["policy_id"], "subjects": subjects,
            "bundle": {"name": bundle.name, "sha256": _sha(bundle), "bytes": bundle.stat().st_size},
            "evidence_commitment": evidence["commitment"], "signing_request": signing["request_commitment"],
            "disposition": "PASS_LOCAL_CANDIDATE", "standing": "LOCAL_CANDIDATE", "authority_effect": "NONE",
            "claim_boundary": "LOCAL_REPRODUCIBILITY_AND_GATES_DO_NOT_ESTABLISH EXTERNAL_SIGNATURE_SECOND_HOST_OR_ADMISSION",
        }
        receipt["receipt_commitment"] = commitment("MOSAIC.UI.RELEASE_RECEIPT.v0.1", receipt)
        atomic_write(stage / "release-receipt.json", canonical_bytes(receipt) + b"\n")
        shutil.copytree(stage, output)
    verification = verify_release(output)
    return {**receipt, "output_dir": str(output), "verification": verification}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--browser-engine", action="append", default=[])
    parser.add_argument("--upgrade-from-wheel", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = verify_release(args.output) if args.verify_only else build_release(
            args.source, args.output, run_native=args.native, browser_engines=tuple(args.browser_engine),
            upgrade_from_wheel=args.upgrade_from_wheel,
        )
        print(json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2))
        return 0
    except (ReleaseRefusal, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": "mosaic.ui.release-refusal.v0.1", "disposition": "REFUSE",
                          "refusal_code": getattr(exc, "code", "RELEASE_INPUT_OR_IO_REFUSED"),
                          "detail": getattr(exc, "detail", str(exc)), "authority_effect": "NONE"}, indent=2))
        return 32


if __name__ == "__main__":
    raise SystemExit(main())

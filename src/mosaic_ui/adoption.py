"""Manifest-driven packaging and independent-consumer acceptance for Mosaic UI."""
from __future__ import annotations

import json
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .ablate import build_slice, verify_slice
from .canonical import atomic_write, canonical_bytes, commitment, read_json
from .foundry import compile_library
from .model import ALL_COMPONENT_KINDS, UIRefusal
from .sufficiency import sufficiency_application


MANIFEST_SCHEMA = "mosaic.ui.application-manifest.v0.1"
MANIFEST_KEYS = {
    "schema", "application", "realizers", "pathways", "themes", "retain_kinds",
    "budgets", "standing", "authority_effect",
}
REALIZERS = {"HEADLESS", "BROWSER", "WIN32"}


def validate_manifest(value: Any, base: Path) -> tuple[dict[str, Any], Path]:
    if not isinstance(value, dict) or set(value) != MANIFEST_KEYS or value.get("schema") != MANIFEST_SCHEMA:
        raise UIRefusal("APPLICATION_MANIFEST_SCHEMA_REFUSED", "")
    if value.get("authority_effect") != "NONE":
        raise UIRefusal("APPLICATION_MANIFEST_AUTHORITY_REFUSED", "")
    application = value.get("application")
    if not isinstance(application, str) or not application or Path(application).is_absolute():
        raise UIRefusal("APPLICATION_MANIFEST_PATH_REFUSED", str(application))
    application_path = (base / application).resolve()
    try:
        application_path.relative_to(base.resolve())
    except ValueError as exc:
        raise UIRefusal("APPLICATION_MANIFEST_PATH_REFUSED", application) from exc
    if not application_path.is_file():
        raise UIRefusal("APPLICATION_MANIFEST_APPLICATION_ABSENT", str(application_path))
    for key in ("realizers", "pathways", "themes", "retain_kinds"):
        entries = value.get(key)
        if not isinstance(entries, list) or entries != sorted(set(entries)) \
                or not all(isinstance(item, str) and item for item in entries):
            raise UIRefusal("APPLICATION_MANIFEST_SET_REFUSED", key)
    if not value["realizers"] or not set(value["realizers"]) <= REALIZERS:
        raise UIRefusal("APPLICATION_MANIFEST_REALIZER_REFUSED", ",".join(value["realizers"]))
    if not set(value["retain_kinds"]) <= set(ALL_COMPONENT_KINDS):
        raise UIRefusal("APPLICATION_MANIFEST_KIND_REFUSED", "")
    budgets = value.get("budgets")
    budget_keys = {"max_archive_bytes", "max_runtime_source_bytes", "max_wheel_bytes"}
    if not isinstance(budgets, dict) or set(budgets) != budget_keys:
        raise UIRefusal("APPLICATION_MANIFEST_BUDGET_REFUSED", "SHAPE")
    for key, amount in budgets.items():
        if amount is not None and (isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0):
            raise UIRefusal("APPLICATION_MANIFEST_BUDGET_REFUSED", key)
    return value, application_path


def _run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    run = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=180)
    output = run.stdout + run.stderr
    return {
        "exit_code": run.returncode,
        "output_sha256": commitment("MOSAIC.UI.SUBPROCESS_OUTPUT.v0.1", output),
        "output_tail": output[-2000:],
    }


def _budget_checks(manifest: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    mapping = {
        "max_archive_bytes": "archive_bytes", "max_runtime_source_bytes": "runtime_source_bytes",
        "max_wheel_bytes": "wheel_bytes",
    }
    checks = []
    for budget, field in mapping.items():
        maximum = manifest["budgets"][budget]
        observed = int(result[field])
        passed = maximum is None or observed <= maximum
        checks.append({"budget": budget, "maximum": maximum, "observed": observed,
                       "disposition": "PASS" if passed else "REFUSE"})
    return checks


def build_from_manifest(manifest_path: Path, output: Path) -> dict[str, Any]:
    manifest_path, output = manifest_path.resolve(), output.resolve()
    manifest, application_path = validate_manifest(read_json(manifest_path), manifest_path.parent)
    if output.exists():
        raise UIRefusal("APPLICATION_BUILD_OUTPUT_EXISTS", str(output))
    source = Path(__file__).resolve().parent / "source"
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mosaic-ui-manifest-", dir=output.parent) as raw:
        work = Path(raw)
        generated = work / "generated"
        compile_library(source, generated, application_path)
        result = build_slice(
            generated, work / "package", tuple(manifest["realizers"]), tuple(manifest["themes"]),
            tuple(manifest["retain_kinds"]), include_pathways=tuple(manifest["pathways"]),
        )
        checks = _budget_checks(manifest, result)
        failed = [check["budget"] for check in checks if check["disposition"] != "PASS"]
        if failed:
            raise UIRefusal("APPLICATION_SIZE_BUDGET_REFUSED", ",".join(failed))
        verification = verify_slice(Path(result["archive_path"]), Path(result["receipt_path"]))
        payload_path = work / "payload.json"
        module = (generated / "library.py").read_text(encoding="utf-8")
        namespace: dict[str, Any] = {}
        exec(compile(module, str(generated / "library.py"), "exec"), namespace)
        atomic_write(payload_path, canonical_bytes(namespace["PAYLOAD"]) + b"\n")
        install = work / "install"
        pip = _run([sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(install),
                    result["wheel_path"]], work)
        if pip["exit_code"] != 0:
            raise UIRefusal("APPLICATION_SLICE_INSTALL_REFUSED", pip["output_tail"])
        script = (
            "import json,sys;sys.path.insert(0,sys.argv[1]);"
            "from pathlib import Path;from mosaic_ui.realizer import create_realizer,conformance_witness;"
            "p=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'));"
            "ids=json.loads(sys.argv[3]);"
            "ws=[conformance_witness(create_realizer(i,p),viewports=((1280,800),(800,600))) for i in ids];"
            "assert all(w['disposition']=='PASS_LOCAL_CANDIDATE' for w in ws);print(len(ws))"
        )
        acceptance = _run([sys.executable, "-I", "-c", script, str(install), str(payload_path),
                           json.dumps(manifest["realizers"])], work,
                          {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": ""})
        if acceptance["exit_code"] != 0:
            raise UIRefusal("APPLICATION_SLICE_ACCEPTANCE_REFUSED", acceptance["output_tail"])
        shutil.copytree(work / "package", output)
    receipt = {
        "schema": "mosaic.ui.application-build-receipt.v0.1",
        "manifest_root": commitment("MOSAIC.UI.APPLICATION_MANIFEST.v0.1", manifest),
        "application_sha256": commitment("MOSAIC.UI.APPLICATION.v0.1", read_json(application_path)),
        "slice_receipt_commitment": result["receipt_commitment"], "profile_root": result["profile_root"],
        "archive": Path(result["archive_path"]).name, "wheel": Path(result["wheel_path"]).name,
        "budgets": checks, "verification": verification,
        "installed_acceptance": acceptance, "disposition": "PASS_LOCAL_CANDIDATE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE",
        "claim_boundary": "MANIFEST_BUILD_AND_ISOLATED_INSTALL_DO_NOT_ESTABLISH EXTERNAL_SIGNATURE_OR_ADMISSION",
    }
    receipt["commitment"] = commitment("MOSAIC.UI.APPLICATION_BUILD_RECEIPT.v0.1", receipt)
    atomic_write(output / "application-build-receipt.json", canonical_bytes(receipt) + b"\n")
    return {**receipt, "output_dir": str(output)}


RUN_CONSUMER = r'''from __future__ import annotations
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import mosaic_ui
from mosaic_ui.canonical import canonical_bytes, commitment
from mosaic_ui.foundry import compile_library
from mosaic_ui.probe import load_subject
from mosaic_ui.realizer import conformance_witness, create_realizer

root = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix="mosaic-consumer-") as raw:
    generated = Path(raw) / "generated"
    compile_library(Path(mosaic_ui.__file__).resolve().parent / "source", generated, root / "application.json")
    payload, subject = load_subject(generated)
    witnesses = {}
    for realizer_id in ("HEADLESS", "BROWSER"):
        realizer = create_realizer(realizer_id, payload)
        try:
            witnesses[realizer_id] = conformance_witness(realizer, viewports=((1280, 800), (800, 600)))
        finally:
            realizer.close()
receipt = {
    "schema": "mosaic.ui.independent-consumer-receipt.v0.1",
    "installed_version": mosaic_ui.__version__, "subject": subject,
    "realizers": {key: value["commitment"] for key, value in witnesses.items()},
    "disposition": "PASS_LOCAL_CANDIDATE" if all(value["disposition"] == "PASS_LOCAL_CANDIDATE" for value in witnesses.values()) else "REFUSE",
    "standing": "INDEPENDENT_LOCAL_CONSUMER_EVIDENCE", "authority_effect": "NONE",
    "claim_boundary": "SEPARATE_DIRECTORY_AND_INSTALLED_WHEEL_ON_ONE_HOST_DO_NOT_ESTABLISH SECOND_HOST_ACCEPTANCE",
}
receipt["commitment"] = commitment("MOSAIC.UI.INDEPENDENT_CONSUMER_RECEIPT.v0.1", receipt)
(root / "consumer-receipt.json").write_bytes(canonical_bytes(receipt) + b"\n")
print(json.dumps(receipt, sort_keys=True))
raise SystemExit(0 if receipt["disposition"] == "PASS_LOCAL_CANDIDATE" else 32)
'''


def scaffold_consumer(output: Path) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise UIRefusal("CONSUMER_OUTPUT_EXISTS", str(output))
    output.mkdir(parents=True)
    application = sufficiency_application()
    manifest = {
        "schema": MANIFEST_SCHEMA, "application": "application.json",
        "realizers": ["BROWSER", "HEADLESS"], "pathways": ["REALIZER_PROTOCOL"],
        "themes": [], "retain_kinds": [],
        "budgets": {"max_archive_bytes": 180000, "max_runtime_source_bytes": 240000,
                    "max_wheel_bytes": 180000},
        "standing": "LOCAL_CANDIDATE", "authority_effect": "NONE",
    }
    atomic_write(output / "application.json", canonical_bytes(application) + b"\n")
    atomic_write(output / "mosaic-ui.json", canonical_bytes(manifest) + b"\n")
    atomic_write(output / "run_consumer.py", RUN_CONSUMER.encode("ascii"))
    return {"application": application, "manifest": manifest}


def verify_independent_consumer(wheel: Path, output: Path) -> dict[str, Any]:
    wheel, output = wheel.resolve(), output.resolve()
    scaffold_consumer(output)
    with tempfile.TemporaryDirectory(prefix="mosaic-ui-consumer-install-", dir=output.parent) as raw:
        install = Path(raw) / "install"
        pip = _run([sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(install), str(wheel)], output)
        if pip["exit_code"] != 0:
            raise UIRefusal("INDEPENDENT_CONSUMER_INSTALL_REFUSED", pip["output_tail"])
        run = _run([sys.executable, "-I", str(output / "run_consumer.py"), str(install)], output,
                   {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": ""})
        if run["exit_code"] != 0:
            raise UIRefusal("INDEPENDENT_CONSUMER_RUN_REFUSED", run["output_tail"])
    receipt = read_json(output / "consumer-receipt.json")
    return {**receipt, "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "install_output_sha256": pip["output_sha256"], "run_output_sha256": run["output_sha256"],
            "consumer_dir": str(output)}


__all__ = ["build_from_manifest", "scaffold_consumer", "validate_manifest", "verify_independent_consumer"]

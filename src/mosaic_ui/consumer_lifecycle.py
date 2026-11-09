"""Independent installed-wheel consumer lifecycle and recovery exercise."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .canonical import atomic_write, canonical_bytes, commitment, read_json
from .model import UIRefusal


class ConsumerLifecycleRefusal(UIRefusal):
    pass


PROBE_SCRIPT = r'''from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import mosaic_ui
from mosaic_ui.canonical import atomic_write, canonical_bytes, commitment
from mosaic_ui.foundry import compile_library
from mosaic_ui.probe import load_subject
from mosaic_ui.sufficiency import sufficiency_application
from mosaic_ui_std.catalog import load_catalog, load_runtime_catalog

install = Path(sys.argv[1]).resolve()
work = Path(sys.argv[2]).resolve()
frozen = load_catalog()
runtime = load_runtime_catalog()
generated = work / "generated"
application = work / "application.json"
atomic_write(application, canonical_bytes(sufficiency_application()) + b"\n")
compile_library(Path(mosaic_ui.__file__).resolve().parent / "source", generated, application)
_, subject = load_subject(generated)
value = {
    "version": mosaic_ui.__version__,
    "installed_only": Path(mosaic_ui.__file__).resolve().is_relative_to(install),
    "legacy_catalog_root": commitment("MOSAIC.UI.STD.CATALOG.v0.1", frozen),
    "runtime_catalog_root": commitment("MOSAIC.UI.STD.CATALOG.v0.1", runtime),
    "kinds": [item["kind"] for item in runtime["components"]],
    "states": runtime["states"],
    "realizers": runtime["realizers"],
    "subject_root": subject["generated_root"],
}
print(json.dumps(value, sort_keys=True))
'''


BASELINE_SESSION_SCRIPT = r'''from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from mosaic_ui.browser_realizer import BrowserSessionManager
from mosaic_ui.sufficiency import build_sufficiency_payload

database = Path(sys.argv[2]).resolve()
manager = BrowserSessionManager(build_sufficiency_payload(), session_database=database)
try:
    session = manager.create_session("independent-consumer")
    state, next_sequence = manager.apply_session(
        session.session_id, session.token, 1,
        {"intent": "SELECT", "node_id": "suff.menu", "value": "View"},
        "independent-consumer",
    )
    print(json.dumps({
        "session_id": session.session_id, "token": session.token,
        "owner": "independent-consumer", "selected": state["values"]["suff.menu"],
        "next_sequence": next_sequence,
    }, sort_keys=True))
finally:
    manager.close()
'''


CANDIDATE_RECOVERY_SCRIPT = r'''from __future__ import annotations
import json, shutil, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from mosaic_ui.browser_realizer import BrowserSessionManager
from mosaic_ui.browser_session_store import SQLiteBrowserSessionStore
from mosaic_ui.canonical import atomic_write
from mosaic_ui.model import UIRefusal
from mosaic_ui.session_custody import backup_session_database, verify_session_backup
from mosaic_ui.sufficiency import build_sufficiency_payload

database = Path(sys.argv[2]).resolve()
backup = Path(sys.argv[3]).resolve()
session = json.loads(Path(sys.argv[4]).read_text(encoding="utf-8"))
manager = BrowserSessionManager(build_sufficiency_payload(), session_database=database)
try:
    recovered = manager.get_session(session["session_id"], session["token"], session["owner"])
    before = recovered.realizer.snapshot()["values"]["suff.menu"]
    state, next_sequence = manager.apply_session(
        session["session_id"], session["token"], session["next_sequence"],
        {"intent": "SELECT", "node_id": "suff.menu", "value": "File"}, session["owner"],
    )
finally:
    manager.close()

backup_receipt = backup_session_database(database, backup)
verification = verify_session_backup(backup)
restored = BrowserSessionManager(build_sufficiency_payload(), session_database=backup)
try:
    recovered_again = restored.get_session(session["session_id"], session["token"], session["owner"])
    restored_value = recovered_again.realizer.snapshot()["values"]["suff.menu"]
    restored_sequence = recovered_again.next_sequence
    replay_refused = False
    try:
        restored.apply_session(
            session["session_id"], session["token"], session["next_sequence"],
            {"intent": "SELECT", "node_id": "suff.menu", "value": "View"}, session["owner"],
        )
    except UIRefusal as exc:
        replay_refused = exc.code == "BROWSER_EVENT_SEQUENCE_REFUSED"
    bad_token_refused = False
    try:
        restored.get_session(session["session_id"], "x" * 32, session["owner"])
    except UIRefusal as exc:
        bad_token_refused = exc.code == "BROWSER_SESSION_REFUSED"
finally:
    restored.close()

binding_refused = False
try:
    SQLiteBrowserSessionStore(backup, "0" * 64)
except UIRefusal as exc:
    binding_refused = exc.code == "BROWSER_SESSION_STORE_REFUSED"

corrupt = backup.with_name("corrupt.db")
raw = backup.read_bytes()
atomic_write(corrupt, raw[:max(1, len(raw) // 2)])
corrupt_refused = False
try:
    verify_session_backup(corrupt)
except UIRefusal as exc:
    corrupt_refused = exc.code == "BROWSER_SESSION_BACKUP_REFUSED"

print(json.dumps({
    "before_upgrade_value": before,
    "after_upgrade_value": state["values"]["suff.menu"],
    "after_upgrade_sequence": next_sequence,
    "restored_value": restored_value,
    "restored_sequence": restored_sequence,
    "backup_commitment": backup_receipt["commitment"],
    "verification_commitment": verification["commitment"],
    "replay_refused": replay_refused,
    "bad_token_refused": bad_token_refused,
    "binding_refused": binding_refused,
    "corrupt_backup_refused": corrupt_refused,
}, sort_keys=True))
'''


APPLICATION_BUILD_SCRIPT = r'''from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from mosaic_ui.adoption import build_from_manifest, scaffold_consumer

root = Path(sys.argv[2]).resolve()
consumer = root / "consumer"
package = root / "application-package"
scaffold_consumer(consumer)
receipt = build_from_manifest(consumer / "mosaic-ui.json", package)
print(json.dumps({
    "commitment": receipt["commitment"],
    "profile_root": receipt["profile_root"],
    "archive": receipt["archive"],
    "wheel": receipt["wheel"],
    "disposition": receipt["disposition"],
}, sort_keys=True))
'''


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_json(script: Path, args: list[str], cwd: Path, timeout: int = 240) -> dict[str, Any]:
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": ""}
    result = subprocess.run(
        [sys.executable, "-I", str(script), *args], cwd=cwd, env=environment,
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
    )
    if result.returncode != 0:
        raise ConsumerLifecycleRefusal(
            "CONSUMER_LIFECYCLE_PROCESS_REFUSED", f"{script.name}:{result.stderr[-1000:]}",
        )
    try:
        value = json.loads(result.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise ConsumerLifecycleRefusal("CONSUMER_LIFECYCLE_OUTPUT_REFUSED", script.name) from exc
    if not isinstance(value, dict):
        raise ConsumerLifecycleRefusal("CONSUMER_LIFECYCLE_OUTPUT_REFUSED", script.name)
    value["process_output_sha256"] = hashlib.sha256(
        (result.stdout + result.stderr).encode("utf-8"),
    ).hexdigest()
    return value


def _install(wheel: Path, destination: Path, cwd: Path) -> dict[str, Any]:
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": ""}
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(destination), str(wheel)],
        cwd=cwd, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=240,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        raise ConsumerLifecycleRefusal("CONSUMER_LIFECYCLE_INSTALL_REFUSED", output[-1000:])
    return {"exit_code": 0, "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest()}


def run_consumer_lifecycle(baseline_wheel: Path, candidate_wheel: Path, output: Path) -> dict[str, Any]:
    baseline_wheel, candidate_wheel, output = (
        baseline_wheel.resolve(), candidate_wheel.resolve(), output.resolve(),
    )
    if not baseline_wheel.is_file() or not candidate_wheel.is_file():
        raise ConsumerLifecycleRefusal("CONSUMER_LIFECYCLE_WHEEL_ABSENT", "")
    if baseline_wheel == candidate_wheel or _sha(baseline_wheel) == _sha(candidate_wheel):
        raise ConsumerLifecycleRefusal("CONSUMER_LIFECYCLE_DISTINCT_CANDIDATE_REQUIRED", "")
    if output.exists():
        raise ConsumerLifecycleRefusal("CONSUMER_LIFECYCLE_OUTPUT_EXISTS", str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mosaic-ui-consumer-lifecycle-", dir=output.parent) as raw:
        work = Path(raw)
        evidence = work / "evidence"
        evidence.mkdir()
        scripts = {
            "probe.py": PROBE_SCRIPT,
            "baseline_session.py": BASELINE_SESSION_SCRIPT,
            "candidate_recovery.py": CANDIDATE_RECOVERY_SCRIPT,
            "application_build.py": APPLICATION_BUILD_SCRIPT,
        }
        for name, source in scripts.items():
            atomic_write(work / name, source.encode("utf-8"))
        baseline_install, candidate_install = work / "baseline-install", work / "candidate-install"
        baseline_install_receipt = _install(baseline_wheel, baseline_install, work)
        candidate_install_receipt = _install(candidate_wheel, candidate_install, work)
        baseline_probe = _run_json(work / "probe.py", [str(baseline_install), str(work / "baseline-probe")], work)
        candidate_probe = _run_json(work / "probe.py", [str(candidate_install), str(work / "candidate-probe")], work)
        session_database = work / "sessions.db"
        session = _run_json(
            work / "baseline_session.py", [str(baseline_install), str(session_database)], work,
        )
        session_secret = {key: session[key] for key in ("session_id", "token", "owner", "next_sequence")}
        atomic_write(work / "session-secret.json", canonical_bytes(session_secret) + b"\n")
        recovery = _run_json(
            work / "candidate_recovery.py",
            [str(candidate_install), str(session_database), str(work / "sessions.backup.db"),
             str(work / "session-secret.json")], work,
        )
        application = _run_json(
            work / "application_build.py", [str(candidate_install), str(evidence)], work, timeout=360,
        )
        checks = {
            "BASELINE_INSTALLED_PACKAGE_ONLY": baseline_probe["installed_only"],
            "CANDIDATE_INSTALLED_PACKAGE_ONLY": candidate_probe["installed_only"],
            "VERSION_UPGRADED": baseline_probe["version"] != candidate_probe["version"],
            "LEGACY_CATALOG_ROOT_PRESERVED": baseline_probe["legacy_catalog_root"]
            == candidate_probe["legacy_catalog_root"],
            "RUNTIME_CATALOG_ROOT_PRESERVED": baseline_probe["runtime_catalog_root"]
            == candidate_probe["runtime_catalog_root"],
            "PUBLIC_KIND_SET_PRESERVED": baseline_probe["kinds"] == candidate_probe["kinds"]
            and len(candidate_probe["kinds"]) == 25,
            "STATE_MODEL_PRESERVED": baseline_probe["states"] == candidate_probe["states"],
            "REALIZER_SET_PRESERVED": baseline_probe["realizers"] == candidate_probe["realizers"],
            "APPLICATION_SUBJECT_PRESERVED": baseline_probe["subject_root"] == candidate_probe["subject_root"],
            "APPLICATION_BUILD_PASSED": application["disposition"] == "PASS_LOCAL_CANDIDATE",
            "STATE_UPGRADED": session["selected"] == recovery["before_upgrade_value"] == "View"
            and recovery["after_upgrade_value"] == "File" and recovery["after_upgrade_sequence"] == 3,
            "BACKUP_RESTORED": recovery["restored_value"] == "File"
            and recovery["restored_sequence"] == 3,
            "REPLAY_REFUSED": recovery["replay_refused"],
            "BAD_TOKEN_REFUSED": recovery["bad_token_refused"],
            "BINDING_DRIFT_REFUSED": recovery["binding_refused"],
            "CORRUPT_BACKUP_REFUSED": recovery["corrupt_backup_refused"],
        }
        if not all(checks.values()):
            raise ConsumerLifecycleRefusal(
                "CONSUMER_LIFECYCLE_CHECK_REFUSED",
                ",".join(sorted(name for name, passed in checks.items() if not passed)),
            )
        witness = {
            "schema": "mosaic.ui.independent-consumer-lifecycle.v1",
            "baseline": {
                "version": baseline_probe["version"], "wheel_sha256": _sha(baseline_wheel),
                "install_output_sha256": baseline_install_receipt["output_sha256"],
            },
            "candidate": {
                "version": candidate_probe["version"], "wheel_sha256": _sha(candidate_wheel),
                "install_output_sha256": candidate_install_receipt["output_sha256"],
                "public_kind_count": len(candidate_probe["kinds"]),
            },
            "compatibility": {
                "legacy_catalog_root": candidate_probe["legacy_catalog_root"],
                "runtime_catalog_root": candidate_probe["runtime_catalog_root"],
                "application_subject_root": candidate_probe["subject_root"],
            },
            "application_build": {
                "receipt_commitment": application["commitment"],
                "profile_root": application["profile_root"],
                "archive": application["archive"], "wheel": application["wheel"],
            },
            "recovery": {
                "backup_commitment": recovery["backup_commitment"],
                "verification_commitment": recovery["verification_commitment"],
                "restored_value": recovery["restored_value"],
                "restored_sequence": recovery["restored_sequence"],
            },
            "checks": checks,
            "disposition": "PASS_LOCAL_CANDIDATE",
            "standing": "INDEPENDENT_INSTALLED_CONSUMER_LOCAL_EVIDENCE",
            "authority_effect": "NONE",
            "claim_boundary": "SEPARATE_INSTALLED_WHEELS_ON_ONE_HOST_DO_NOT_ESTABLISH_SECOND_HOST_HUMAN_REVIEW_EXTERNAL_SIGNATURE_OR_RELEASE_ADMISSION",
        }
        witness["commitment"] = commitment("MOSAIC.UI.INDEPENDENT_CONSUMER_LIFECYCLE.v1", witness)
        atomic_write(evidence / "consumer-lifecycle-witness.json", canonical_bytes(witness) + b"\n")
        shutil.copytree(evidence, output)
    return {**witness, "output_dir": str(output)}


__all__ = ["ConsumerLifecycleRefusal", "run_consumer_lifecycle"]

"""Positive construction checks for the r035 review-repair boundary.

Reserved concurrency, fault-injection, and adversarial cases remain in the
operator kit and are not executed by this suite.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from uclop.canonical import canonical_bytes, root
from ucm.pippi_adaptive import build_turn_report
from ucm.pippi_cmba import CMBA_WHEEL_SHA256, build_cmba_turn_assessment
from ucm.pippi_global import PippiHub, build_onboarding, build_project
from ucm.pippi_packs import verify_bundled_optional_pack_manifests
from ucm.pippi_turn_workflow import (build_assessment_attachment, build_turn_bundle,
    project_turn_history, turn_continuation_context)
from ucm.pippi_turn_record import build_turn_record
from test_pippi_turn_record_positive import common_turn_fixture


ROOT = Path(__file__).resolve().parents[1]


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")


class R035ClosureTests(unittest.TestCase):
    def test_runtime_tree_and_installer_revision_binding(self):
        with tempfile.TemporaryDirectory(prefix="ucm-r035-runtime-positive-", dir=ROOT.parent) as raw:
            runtime = Path(raw)
            revision = "r035"
            state_body = {"schema": "mosaic.ucm.state-manifest.v0.1",
                "artifact": "UCM_RUNTIME", "version": "v0.1",
                "engineering_revision": revision, "members": [], "member_count": 0}
            state = {**state_body, "state_root": _sha(canonical_bytes(state_body))}
            thr = {"schema": "mosaic.thr-manifest.v0.1", "h_body": "1" * 64}
            dkn = {"schema": "mosaic.dkn-binding.v0.1", "status": "DECLARED_UNBOUND"}
            cert = {"schema": "mosaic.self-certificate.v0.1",
                    "certificate_status": "READY_FOR_EXTERNAL_DKN_CERTIFICATION",
                    "state_root": state["state_root"], "thr_body_root": thr["h_body"]}
            payloads = {
                "META/STATE-MANIFEST.json": canonical_bytes(state) + b"\n",
                "META/THR-MANIFEST.json": canonical_bytes(thr) + b"\n",
                "META/DKN-BINDING.json": canonical_bytes(dkn) + b"\n",
                "META/SELF-CERTIFICATE.json": canonical_bytes(cert) + b"\n",
            }
            rows = []
            for name, data in sorted(payloads.items()):
                path = runtime / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                rows.append({"path": name, "sha256": _sha(data), "bytes": len(data)})
            body = {"schema": "mosaic.ucm.artifact-manifest.v0.1",
                    "artifact": "UCM_RUNTIME", "completeness": "COMPLETE_RUNTIME",
                    "version": "v0.1", "engineering_revision": revision,
                    "members": rows, "member_count": len(rows),
                    "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
                    "real_a5": False, "g0": "CLOSED"}
            manifest = {**body, "root": _sha(canonical_bytes(body))}
            _write(runtime / "MANIFEST.json", manifest)
            process = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8",
                str(ROOT / "tools" / "verify_runtime_tree.py"), str(runtime),
                "--expected-root", manifest["root"], "--expected-revision", revision],
                capture_output=True, text=True, check=False)
            self.assertEqual(process.returncode, 0, process.stderr)
            result = json.loads(process.stdout)
            self.assertEqual(result["engineering_revision"], revision)
        installer = (ROOT / "install" / "INSTALL-PIPPI.ps1").read_text(encoding="utf-8")
        self.assertIn("$ExpectedRevision", installer)
        self.assertNotIn("Activating the immutable r033 runtime", installer)

    def test_report_amendment_retires_superseded_information_request(self):
        opening, report, details = common_turn_fixture()
        with tempfile.TemporaryDirectory(prefix="ucm-r035-amendment-positive-", dir=ROOT.parent) as raw:
            hub = PippiHub(Path(raw) / "hub")
            hub.initialize(build_onboarding(governor_label="r035-positive", mosaic_id=None,
                dkn_public_key=None, github_account=None, github_credential_reference=None))
            project = build_project(project_id="pippi", title="P/PPI", workspace=str(ROOT),
                github_url=None, application_command=["pippi", "dashboard"],
                verification_command=["pippi", "interface-doctor"], revision="r034")
            hub.add_project(project)
            hub.store_turn_opening_atomic(opening)
            incomplete_record = build_turn_record(opening=opening, report=report,
                claims=[], evidence=[], coverage=[], objectives=[],
                acceptance_dispositions=[], native_turn_roots=[])
            incomplete = build_turn_bundle(opening=opening, report=report,
                                            turn_record=incomplete_record)
            hub.store_turn_bundle_atomic(incomplete)
            complete_record = build_turn_record(opening=opening, report=report, **details)
            complete = build_turn_bundle(opening=opening, report=report,
                turn_record=complete_record,
                supersedes_turn_bundle_root=incomplete["turn_bundle_root"])
            hub.store_turn_bundle_atomic(complete)
            assessment = build_cmba_turn_assessment(opening=opening, report=report,
                turn_record=complete_record, expected_wheel_sha256=CMBA_WHEEL_SHA256)
            attachment = build_assessment_attachment(opening=opening, report=report,
                turn_record=complete_record, assessment=assessment,
                expected_wheel_sha256=CMBA_WHEEL_SHA256)
            hub.store_project_record(project_id=project["project_id"],
                record_kind="turn-assessment", record=attachment,
                root_field="attachment_root", event_type="TURN_ASSESSMENT_ATTACHED")
            history = project_turn_history(hub, project["project_id"])
            self.assertEqual(history["record_count"], 2)
            self.assertFalse(history["records"][0]["active_report"])
            self.assertEqual(history["records"][0]["superseded_by_turn_bundle_root"],
                             complete["turn_bundle_root"])
            self.assertTrue(history["records"][1]["active_report"])
            self.assertEqual(history["records"][1]["assessments"][0]["assessment_root"],
                             assessment["assessment_root"])
            self.assertEqual(turn_continuation_context(hub, project["project_id"])["information_requests"], [])

    def test_atomic_opening_commit_exact_retry_is_idempotent(self):
        opening, _, _ = common_turn_fixture()
        with tempfile.TemporaryDirectory(prefix="ucm-r035-opening-positive-", dir=ROOT.parent) as raw:
            hub = PippiHub(Path(raw) / "hub")
            hub.initialize(build_onboarding(governor_label="r035-positive", mosaic_id=None,
                dkn_public_key=None, github_account=None, github_credential_reference=None))
            project = build_project(project_id="pippi", title="P/PPI", workspace=str(ROOT),
                github_url=None, application_command=["pippi", "dashboard"],
                verification_command=["pippi", "interface-doctor"], revision="r034")
            hub.add_project(project)
            first = hub.store_turn_opening_atomic(opening)
            second = hub.store_turn_opening_atomic(opening)
            self.assertFalse(first["idempotent_replay"])
            self.assertTrue(second["idempotent_replay"])
            self.assertEqual(first["hub_event_root"], second["hub_event_root"])

    def test_active_generated_contracts_match_live_generators(self):
        process = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8",
            str(ROOT / "tools" / "check_active_generated_contracts.py")],
            cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertTrue(json.loads(process.stdout)["frozen_history_excluded"])

    def test_optional_pack_positive_denominator_includes_cmba(self):
        result = verify_bundled_optional_pack_manifests(ROOT)
        self.assertEqual({row["pack_id"] for row in result["checked"]},
                         {"SEMCRYS_CORE", "MEMORY_VAULT_ADAPTER", "CMBA_EVIDENCE"})

    def test_launcher_contract_names_durable_preservation_and_terminal_receipt(self):
        builder = (ROOT / "tools" / "build_common_turn_r035_operator_kit.py").read_text(encoding="utf-8")
        self.assertIn("recovery_workspace_retained", builder)
        self.assertIn("terminal_receipt", builder)
        self.assertIn("durable_preservation_verified", builder)
        self.assertIn("cleanup_status", builder)


if __name__ == "__main__":
    unittest.main()

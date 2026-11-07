from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "public_release_qualification", ROOT / "tools" / "run_public_release_qualification.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

REFRESH_SPEC = importlib.util.spec_from_file_location(
    "refresh_release_identity", ROOT / "tools" / "refresh_release_identity.py")
REFRESH = importlib.util.module_from_spec(REFRESH_SPEC)
assert REFRESH_SPEC.loader is not None
REFRESH_SPEC.loader.exec_module(REFRESH)


class PublicReleaseQualificationTests(unittest.TestCase):
    def test_refresh_preserves_exact_frozen_predecessor(self):
        predecessor = json.loads(
            (ROOT / "release" / "PREDECESSOR-r026-RELEASE-IDENTITY.json").read_text(
                encoding="utf-8"))
        current = json.loads(
            (ROOT / "release" / "RELEASE-IDENTITY.json").read_text(encoding="utf-8"))
        first = REFRESH.refreshed_identity_body(current, "1" * 64)
        second = REFRESH.refreshed_identity_body(first, "2" * 64)
        expected = predecessor["source_manifest_root"]
        self.assertEqual(first["predecessor_source_root"], expected)
        self.assertEqual(second["predecessor_source_root"], expected)
        self.assertEqual(second["source_manifest_root"], "2" * 64)
        qualification = json.loads((ROOT / "release" / "PREDECESSOR-r026-QUALIFICATION.json").read_text(
            encoding="utf-8"))
        self.assertEqual(second["predecessor_release_identity_root"], predecessor["root"])
        self.assertEqual(second["predecessor_qualification_root"], qualification["root"])
        self.assertEqual(second["predecessor_operator_tier1"]["provenance"],
                         "NOT_FROZEN_IN_PREDECESSOR_RELEASE_IDENTITY")
        self.assertEqual(second["predecessor_operator_tier1"]["operator_tier1_case_count"], 0)

    def test_final_identity_removes_unresolvable_predecessor_maturity_pins(self):
        identity = {
            "root": "old", "source_manifest_root": "old-source",
            "canonical_software_sha256": "a" * 64,
            "maturity_freeze_root": "b" * 64,
            "maturity_qualification_root": "c" * 64,
            "maturity_source_root": "d" * 64,
            "qualification_source_sha256": "e" * 64,
            "independent_review_handoff_sha256": "f" * 64,
        }
        result = MODULE.final_identity(identity, "1" * 64)
        self.assertFalse(MODULE.STALE_MATURITY_FIELDS & set(result))
        self.assertEqual(result["source_manifest_root"], "1" * 64)
        self.assertEqual(result["engineering_revision"], "r027")
        self.assertEqual(result["qualification_scope"], "EXACT_PUBLIC_SOURCE_AND_RELEASE")
        body = {key: value for key, value in result.items() if key != "root"}
        self.assertEqual(result["root"], MODULE.sha(MODULE.canonical(body)))

    def test_installer_requires_external_runtime_root_at_every_custody_boundary(self):
        source = (ROOT / "install" / "INSTALL-PIPPI.ps1").read_text(encoding="utf-8")
        self.assertIn("[Parameter(Mandatory=$true)]", source)
        for code in (
            "PIPPI_RUNTIME_EXTERNAL_ROOT_MISMATCH",
            "PIPPI_STAGED_RUNTIME_EXTERNAL_ROOT_MISMATCH",
            "PIPPI_EXISTING_RUNTIME_EXTERNAL_ROOT_MISMATCH",
            "PIPPI_INSTALLED_RUNTIME_EXTERNAL_ROOT_MISMATCH",
        ):
            self.assertIn(code, source)

    def test_replay_is_rooted_and_run_isolated(self):
        qualification_source = (ROOT / "tools/run_public_release_qualification.py").read_text(
            encoding="utf-8")
        self.assertIn("os.chdir(ROOT)", qualification_source)
        self.assertIn('temp_root = out / "temp"', qualification_source)
        with tempfile.TemporaryDirectory() as raw:
            base = pathlib.Path(raw)
            caller = base / "caller"; caller.mkdir()
            scratch = base / "scratch"; scratch.mkdir()
            selected = [
                "tests.test_pippi_portfolio.PippiPortfolioTests.test_installer_targets_r027_and_preserves_global_data_by_default",
                "tests.test_pippi_portfolio.PippiPortfolioTests.test_native_dashboard_uses_portfolio_and_dark_preference",
                "tests.test_pippi_portfolio.PippiPortfolioTests.test_cli_project_brief_matches_the_shared_projection",
                "tests.test_pippi_integrations.IntegrationTests.test_archive_reference_and_local_store",
            ]
            code = (
                "import pathlib,sys,unittest;"
                f"root=pathlib.Path({str(ROOT)!r});"
                "sys.path[:0]=[str(root/'src'),str(root)];"
                f"suite=unittest.TestLoader().loadTestsFromNames({selected!r});"
                "result=unittest.TextTestRunner(verbosity=0).run(suite);"
                "raise SystemExit(0 if result.wasSuccessful() else 1)"
            )
            environment = dict(os.environ)
            environment["TEMP"] = str(scratch); environment["TMP"] = str(scratch)
            run = subprocess.run([sys.executable, "-I", "-B", "-c", code],
                                 cwd=caller, env=environment, text=True, capture_output=True)
            self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
            self.assertEqual(list(caller.iterdir()), [])

    def test_program_checks_run_under_isolated_mode_from_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as raw:
            for name in ("normalize_pippi_work_selection_history.py",
                         "build_pippi_interface_program.py"):
                run = subprocess.run(
                    [sys.executable, "-I", "-B", str(ROOT / "tools" / name), "--check"],
                    cwd=raw, text=True, capture_output=True,
                )
                self.assertEqual(run.returncode, 0, name + "\n" + run.stderr + run.stdout)


if __name__ == "__main__":
    unittest.main()


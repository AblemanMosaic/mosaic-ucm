from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class PippiReleasePackagingTests(unittest.TestCase):
    def test_adaptive_surface_registry_covers_every_pippi_route(self):
        from ucm.pippi_adaptive import ADAPTIVE_CLI_ROUTES

        registry = json.loads((
            ROOT / "spec/PIPPI-CAPABILITY-SURFACE-REGISTRY.json"
        ).read_text(encoding="utf-8"))
        by_name = {row["name"]: row for row in registry["surfaces"]}
        self.assertEqual(set(ADAPTIVE_CLI_ROUTES) - set(by_name), set())
        for name, command in ADAPTIVE_CLI_ROUTES.items():
            self.assertEqual(by_name[name]["route"], f"pippi {command}")

    def test_generated_adaptive_contracts_match_live_registries(self):
        spec = importlib.util.spec_from_file_location(
            "build_pippi_adaptive_contracts",
            ROOT / "tools/build_pippi_adaptive_contracts.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        mismatches = []
        for path, value in module.records().items():
            raw = ((value.rstrip("\n").encode("utf-8")
                    if isinstance(value, str) else module.canonical_bytes(value)) + b"\n")
            if not path.is_file() or path.read_bytes() != raw:
                mismatches.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(mismatches, [])

    def test_portability_source_manifest_matches_release_source(self):
        spec = importlib.util.spec_from_file_location(
            "release_common_portability", ROOT / "tools/release_common.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        body = module.public_source_body(ROOT)
        expected = {**body, "root": module.sha(module.canonical(body))}
        observed = json.loads(
            (ROOT / "PORTABILITY-SOURCE-MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(observed, expected)

    def test_python_distribution_declares_pippi_and_native_packages(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(project["project"]["scripts"]["pippi"], "ucm.pippi_cli:main")
        includes = project["tool"]["setuptools"]["packages"]["find"]["include"]
        self.assertIn("mosaic_ui*", includes)
        self.assertIn("mosaic_ui_std*", includes)
        package_data = project["tool"]["setuptools"]["package-data"]
        self.assertIn("assets/*.png", package_data["mosaic_ui"])
        self.assertIn("themes/*.json", package_data["mosaic_ui_std"])

    def test_runtime_builder_carries_complete_pippi_install_boundary(self):
        spec = importlib.util.spec_from_file_location("build_release", ROOT / "tools/build_release.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        names = {path.relative_to(ROOT).as_posix() for path in module.runtime_files()}
        required = {
            "PIPPI.cmd", "PIPPI-DASHBOARD.cmd", "PIPPI-DASHBOARD.vbs",
            "PIPPI-SERVICE.cmd", "PIPPI-SERVICE.vbs",
            "PIPPI-INSTALLER.BAT", "PIPPI-INSTALLER.vbs",
            "PIPPI-HEADLESS.BAT", "PIPPI-HEADLESS.vbs",
            "PIPPI-START-HERE.md", "PIPPI-AGENT-ACCESS.md",
            "install/INSTALL-PIPPI.cmd", "install/INSTALL-PIPPI.ps1",
            "tools/verify_runtime_tree.py",
            "tools/run_pippi_windows_smoke.py",
            "skill/ucm-pippi-mediated-agent/SKILL.md",
            "skill/ucm-pippi-mediated-agent/references/review-custody.md",
            "skill/ucm-pippi-mediated-agent/references/constitutional-atlas.md",
            "src/ucm/pippi_cli.py", "src/ucm/pippi_reviews.py",
            "src/ucm/pippi_packs.py", "src/ucm/pippi_installer.py",
            "src/ucm/pippi_constitution.py", "src/ucm/pippi_credentials.py",
            "spec/PIPPI-PACK-REGISTRY.json", "docs/PIPPI-CAPABILITY-PACKS.md",
            "spec/PIPPI-CONSTITUTIONAL-STANDARDS-ATLAS.json",
            "spec/PIPPI-PIPELINE-MODEL.json",
            "docs/PIPPI-CONSTITUTIONAL-ATLAS.md",
            "vendor/optional-packs/semcrys-core-v0.1/RELEASE-MANIFEST.json",
            "vendor/optional-packs/memory-vault-v0.1/PUBLIC-RELEASE-CONTRACT.json",
            "src/mosaic_ui/win32.py", "src/mosaic_ui/assets/DeeperLogo.png",
            "src/mosaic_ui_std/signature.py",
            "src/mosaic_ui_std/themes/signature-dark.json",
            "completions/pippi.bash", "completions/pippi.bash.json",
            "completions/pippi.zsh", "completions/pippi.zsh.json",
            "completions/pippi.fish", "completions/pippi.fish.json",
            "completions/pippi.ps1", "completions/pippi.ps1.json",
        }
        self.assertEqual(required - names, set())
        self.assertFalse(any(name.startswith("review/") for name in names))
        self.assertFalse(any(name.startswith("integration/session-returns/") for name in names))
        self.assertFalse(any(name.startswith("integration/successor-returns/") for name in names))
        self.assertFalse(any(name.startswith("tests/") for name in names))

    def test_release_builder_uses_the_canonical_transtemporal_partition_policy(self):
        spec = importlib.util.spec_from_file_location("build_release_policy", ROOT / "tools/build_release.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self.assertEqual(module.REVIEW_CUSTODY_PREFIXES, module._archive_policy.CUSTODY_PREFIXES)
        source = [path.relative_to(ROOT).as_posix() for path in module.all_files()]
        result = module._archive_policy.validate_release_partition(
            runtime_paths=[path.relative_to(ROOT).as_posix() for path in module.runtime_files()],
            sdk_paths=[path.relative_to(ROOT).as_posix() for path in module.sdk_files()],
            review_paths=[path.relative_to(ROOT).as_posix() for path in module.review_files()],
            source_paths=source, review_mode="SELF_CONTAINED_CUSTODY")
        self.assertEqual(result["status"], "PASS")

    def test_installer_requires_exact_runtime_verification_and_immutable_revision(self):
        source = (ROOT / "install/INSTALL-PIPPI.ps1").read_text(encoding="utf-8")
        self.assertIn("verify_runtime_tree.py", source)
        self.assertIn("PIPPI_RUNTIME_SOURCE_REFUSED", source)
        self.assertIn("PIPPI_STAGED_RUNTIME_REFUSED", source)
        self.assertIn("PIPPI_IMMUTABLE_REVISION_CONFLICT", source)
        self.assertIn(r"Pippi\v0.1\r033", source)
        self.assertIn("ExpectedRuntimeRoot", source)
        self.assertIn("PIPPI_RUNTIME_EXTERNAL_ROOT_MISMATCH", source)
        self.assertIn("PIPPI_NONINTERACTIVE_GOVERNOR_LABEL_REQUIRED", source)
        self.assertIn("[switch]$NonInteractive", source)

    def test_no_console_installer_collects_onboarding_without_hidden_prompts(self):
        source = (ROOT / "install/INSTALL-PIPPI.vbs").read_text(encoding="utf-8")
        self.assertIn("-NonInteractive", source)
        self.assertIn("Governor label", source)
        self.assertIn("shell.Run(command, 0, True)", source)
        self.assertIn("PIPPI-INSTALLER.vbs", source)

    def test_windows_smoke_covers_install_service_dashboard_and_uninstall(self):
        source = (ROOT / "tools/run_pippi_windows_smoke.py").read_text(encoding="utf-8")
        for required in ("INSTALL-PIPPI.ps1", "AUTHENTICATED_LOOPBACK_PASS",
                         "dashboard-probe", "UNINSTALL-PIPPI.ps1"):
            self.assertIn(required, source)
        uninstall = (ROOT / "install/UNINSTALL-PIPPI.ps1").read_text(encoding="utf-8")
        self.assertIn("[string]$InstallRoot", uninstall)
        self.assertIn("[string]$DataRoot", uninstall)

    def test_windows_launcher_preserves_the_exact_extracted_runtime(self):
        source = (ROOT / "PIPPI.cmd").read_text(encoding="utf-8")
        self.assertIn('set "PYTHONDONTWRITEBYTECODE=1"', source)

    def test_native_ui_imports_from_the_python_runtime_closure(self):
        from ucm.pippi_dashboard import _load_native

        win32, image, logo, resolve = _load_native()
        self.assertTrue(hasattr(win32, "NativeWindow"))
        self.assertTrue(callable(image))
        self.assertTrue(logo().is_file())
        self.assertEqual(resolve("signature-dark", "comfortable")["authority_effect"], "NONE")

    def test_dashboard_has_no_direct_host_effect_route(self):
        source = (ROOT / "src/ucm/pippi_dashboard.py").read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("os.startfile", source)
        self.assertNotIn("run_review_envelope", source)
        self.assertIn("HostLaunchAdapter", source)
        self.assertIn("validate_host_launch_result", source)

    def test_complete_review_transport_inputs_are_declared(self):
        spec = importlib.util.spec_from_file_location(
            "pippi_review_transport", ROOT / "tools/build_pippi_review_transport.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self.assertEqual(set(module.REQUIRED_BASENAMES), {
            "PIPPI-v0.1-adaptive-cold-boot.zip", "UCM-DEPENDENCY-r021-OPERATOR-KIT.zip",
            "UCM-v0.1-QUALIFICATION.json", "UCM-v0.1-lineage.zip",
            "UCM-v0.1-release.json", "UCM-v0.1-review.zip",
            "UCM-v0.1-runtime.zip", "UCM-v0.1-sdk.zip",
        })


if __name__ == "__main__":
    unittest.main()


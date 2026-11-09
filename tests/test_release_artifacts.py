from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
import unittest
import zipfile
import json

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ReleaseArtifactTests(unittest.TestCase):
    def test_sdk_bundled_verifier_accepts_all_canonical_release_archives(self):
        with tempfile.TemporaryDirectory() as output, tempfile.TemporaryDirectory() as unpacked:
            run = subprocess.run([sys.executable, str(ROOT / "tools/build_release.py"),
                                  "--output", output], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
            sdk = pathlib.Path(output) / "UCM-v0.1-sdk.zip"
            with zipfile.ZipFile(sdk) as archive:
                archive.extract("VERIFY.py", unpacked)
            verifier = pathlib.Path(unpacked) / "VERIFY.py"
            for name in ("UCM-v0.1-runtime.zip", "UCM-v0.1-sdk.zip",
                         "UCM-v0.1-review.zip", "UCM-v0.1-lineage.zip"):
                checked = subprocess.run([sys.executable, str(verifier),
                                          str(pathlib.Path(output) / name)],
                                         capture_output=True, text=True)
                self.assertEqual(checked.returncode, 0,
                                 f"{name}: {checked.stderr}{checked.stdout}")
                self.assertEqual(json.loads(checked.stdout)["status"], "PASS")

    def test_builder_is_deterministic_and_runtime_is_slim(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            for output in (first, second):
                run = subprocess.run([sys.executable, str(ROOT / "tools/build_release.py"), "--output", output], capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
            names = ["UCM-v0.1-runtime.zip", "UCM-v0.1-sdk.zip", "UCM-v0.1-review.zip", "UCM-v0.1-lineage.zip"]
            for name in names:
                self.assertEqual((pathlib.Path(first) / name).read_bytes(), (pathlib.Path(second) / name).read_bytes())
            with zipfile.ZipFile(pathlib.Path(first) / names[0]) as zf:
                members = set(zf.namelist())
                self.assertFalse(any("predecessor" in name.lower() or name.lower().endswith("evidence.zip") for name in members))
                self.assertIn("README.md", members)
                self.assertIn("src/ucm/system.py", members)
                self.assertIn("spec/realization-space-contract-v0.1.schema.json", members)
                self.assertIn("src/uclsh/resources/COMPILER-PASS-GRAPH.json", members)
                self.assertIn("src/ucm/pippi_cli.py", members)
                self.assertIn("src/mosaic_ui/win32.py", members)
                self.assertIn("skill/ucm-pippi-mediated-agent/SKILL.md", members)
                self.assertIn("install/INSTALL-PIPPI.ps1", members)
                self.assertIn("tools/verify_runtime_tree.py", members)
                self.assertEqual({"META/STATE-MANIFEST.json", "META/THR-MANIFEST.json",
                                  "META/DKN-BINDING.json", "META/SELF-CERTIFICATE.json"}
                                 <= members, True)
                certificate = json.loads(zf.read("META/SELF-CERTIFICATE.json"))
                self.assertEqual(certificate["certificate_status"],
                                 "READY_FOR_EXTERNAL_DKN_CERTIFICATION")
                self.assertFalse(certificate["storage_location_bound"])
                self.assertNotIn("tests/test_pippi_reviews.py", members)
                self.assertFalse(any(name.startswith("review/") for name in members))
            with zipfile.ZipFile(pathlib.Path(first) / "UCM-v0.1-sdk.zip") as zf:
                members = set(zf.namelist())
                self.assertIn("tests/test_pippi_reviews.py", members)
                self.assertFalse(any(name.startswith("review/") for name in members))
            with zipfile.ZipFile(pathlib.Path(first) / "UCM-v0.1-review.zip") as zf:
                members = set(zf.namelist())
                self.assertTrue(any(name.startswith("review/") for name in members))
                self.assertFalse(any(name.startswith("src/") for name in members))

    def test_staged_runtime_executes_compiler_pass_workflow_from_arbitrary_cwd(self):
        with tempfile.TemporaryDirectory() as output, tempfile.TemporaryDirectory() as staged, tempfile.TemporaryDirectory() as unrelated:
            run = subprocess.run([sys.executable, str(ROOT / "tools/build_release.py"), "--output", output], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
            with zipfile.ZipFile(pathlib.Path(output) / "UCM-v0.1-runtime.zip") as archive:
                archive.extractall(staged)
            code = (
                "import pathlib,sys;"
                f"root=pathlib.Path({staged!r});"
                "sys.path.insert(0,str(root/'src'));"
                "from uclsh.compiler import compile_module_text;"
                "from uclsh.passes import build_pass_workflow;"
                "source=(root/'fixtures/ucl_selfhost_compiler.ucl.json').read_text(encoding='utf-8');"
                "artifact=compile_module_text(source);"
                "workflow=build_pass_workflow(artifact,source);"
                "assert len(workflow['body']['passes'])==5"
            )
            checked = subprocess.run([sys.executable, "-I", "-c", code], cwd=unrelated, capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stderr + checked.stdout)

    def test_lineage_artifact_is_explicitly_metadata_only(self):
        with tempfile.TemporaryDirectory() as output:
            run = subprocess.run([sys.executable, str(ROOT / "tools/build_release.py"), "--output", output], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
            with zipfile.ZipFile(pathlib.Path(output) / "UCM-v0.1-lineage.zip") as archive:
                manifest = json.loads(archive.read("MANIFEST.json"))
            self.assertEqual(manifest["artifact"], "UCM_LINEAGE_METADATA")
            self.assertEqual(manifest["completeness"], "METADATA_ONLY")

    def test_release_verifier_requires_external_identity(self):
        with tempfile.TemporaryDirectory() as output:
            run = subprocess.run([sys.executable, str(ROOT / "tools/build_release.py"), "--output", output], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
            release_path = pathlib.Path(output) / "UCM-v0.1-release.json"
            release = json.loads(release_path.read_text(encoding="utf-8"))
            self.assertEqual(release["release_kind"], "PUBLIC_LINEAGE")
            verified = subprocess.run([
                sys.executable, str(ROOT / "tools/verify_release.py"), str(release_path),
                "--expected-release-root", release["root"],
            ], capture_output=True, text=True)
            self.assertEqual(verified.returncode, 0, verified.stderr + verified.stdout)
            refused = subprocess.run([
                sys.executable, str(ROOT / "tools/verify_release.py"), str(release_path),
                "--expected-release-root", "0" * 64,
            ], capture_output=True, text=True)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("RELEASE_EXTERNAL_PIN_MISMATCH", refused.stderr + refused.stdout)


if __name__ == "__main__":
    unittest.main()


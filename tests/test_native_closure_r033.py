from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from ucm.c_preflight import BASE_CHECKS, CHANNELS, CHECKS_BY_CLASS, build_c_change_preflight
from ucm.native_core import (
    compile_native_core, detect_c17_compiler, execute_native_binary,
    execute_native_reference, native_core_profile, verify_native_correspondence,
)

ROOT = Path(__file__).resolve().parents[1]


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def rooted(value: dict, field: str) -> bool:
    return value.get(field) == hashlib.sha256(canonical(
        {key: item for key, item in value.items() if key != field})).hexdigest()


def programs() -> list[dict]:
    return [json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((ROOT / "examples/native-core").glob("*.json"))]


class NativeClosureR033Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / ".build").mkdir(exist_ok=True)

    def _compiled(self, work: Path) -> Path:
        compiler = detect_c17_compiler()
        self.assertTrue(compiler["available"], "r033 requires a C17 compiler")
        binary = work / ("ucm-native.exe" if os.name == "nt" else "ucm-native")
        compile_native_core(source=ROOT / "native/ucm_native_core.c",
                            output=binary, compiler=compiler)
        return binary

    def test_r033_boundary_assets_are_exact(self):
        completed = subprocess.run([
            sys.executable, "-B", str(ROOT / "tools/build_native_core_r033_assets.py"),
            "--check"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        boundary = json.loads(
            (ROOT / "spec/UCM-NATIVE-CORE-BOUNDARY-CORPUS.json").read_text())
        self.assertEqual(boundary["program_count"], 4)
        self.assertEqual(len(programs()), 9)

    def test_declared_profile_limits_correspond_exactly(self):
        expected_steps = {
            "ucm.boundary.max_registers": 2,
            "ucm.boundary.max_instructions": 4096,
            "ucm.boundary.max_stack": 2048,
            "ucm.boundary.max_steps": 1_000_000,
        }
        boundary = [row for row in programs() if row["program_id"] in expected_steps]
        with tempfile.TemporaryDirectory(prefix="r033-limits-", dir=ROOT / ".build") as raw:
            work = Path(raw)
            result = verify_native_correspondence(
                programs=boundary, binary=self._compiled(work),
                work_dir=work / "programs")
        self.assertTrue(result["all_correspond"])
        self.assertEqual(result["program_count"], 4)
        for row in result["programs"]:
            self.assertEqual(row["result"]["steps"], expected_steps[row["program_id"]])

    def test_native_projection_is_externally_pinned_and_canonical(self):
        source = next(ROOT.glob("examples/native-core/*three_receipts.ucln"))
        expected = hashlib.sha256(source.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(prefix="r033-canonical-", dir=ROOT / ".build") as raw:
            work = Path(raw)
            binary = self._compiled(work)
            exact = subprocess.run([str(binary), str(source), expected],
                                   capture_output=True, text=True)
            self.assertEqual(exact.returncode, 0, exact.stderr)
            wrong = subprocess.run([str(binary), str(source), "0" * 64],
                                   capture_output=True, text=True)
            self.assertNotEqual(wrong.returncode, 0)
            plus = work / "plus.ucln"
            raw_bytes = source.read_bytes().replace(b"REGISTERS\t3\t1\t1\t1\n",
                                                     b"REGISTERS\t3\t+1\t1\t1\n", 1)
            plus.write_bytes(raw_bytes)
            run = subprocess.run([str(binary), str(plus),
                                  hashlib.sha256(raw_bytes).hexdigest()],
                                 capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)
            trailing = work / "trailing.ucln"
            trailing.write_bytes(source.read_bytes() + b"EXTRA\n")
            run = subprocess.run([str(binary), str(trailing),
                                  hashlib.sha256(trailing.read_bytes()).hexdigest()],
                                 capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)

    def test_cli_fallback_resolves_exact_repository_source(self):
        program = next((ROOT / "examples/native-core").glob("*.json"))
        scratch = ROOT / ".test-tmp"
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="r033-cli-", dir=scratch) as raw:
            work = Path(raw)
            fake = work / "shadow/ucm"
            fake.mkdir(parents=True)
            (fake / "__init__.py").write_text("raise RuntimeError('SHADOW_UCM')\n")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(work / "shadow")
            completed = subprocess.run([
                sys.executable, "-B", str(ROOT / "tools/ucm.py"),
                "native-reference", str(program)],
                cwd=work, env=env, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertEqual(json.loads(completed.stdout)["status"], "PASS")

    def test_r032_review_and_operator_pass_are_exact_predecessor_evidence(self):
        expected = {
            "INDEPENDENT-REPORT.md": "f371442bd769b37d7e0f4700c7e3f67b74c05688060dae7fe048274777baa2e1",
            "INDEPENDENT-FINDINGS.json": "3ac096f2a80a9807d12164c68a0262d68bf1389f8f764a53d579f37d8bb8d945",
            "INDEPENDENT-RECOMPUTE.json": "a746cf3b0ee4386586bb761826821fb6750cffa2c40241c2982dc83654543080",
            "REVIEWER-EVIDENCE.zip": "2f3ef39a1b1cbb27c5fa3ebb60526ec1441205ffcb8513bb0c8f8f00c39ec164",
            "USER-TIER1-PASS-EVIDENCE.zip": "7a58c24aa2ab676ccdc353dc99f7f40d593a495b1c79864f0adb719f81ba0a48",
        }
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((ROOT / "review/r032" / name).read_bytes()).hexdigest(),
                             digest)
        with zipfile.ZipFile(ROOT / "review/r032/USER-TIER1-PASS-EVIDENCE.zip") as archive:
            result = json.loads(archive.read("TIER1-RESULT.json"))
        self.assertTrue(rooted(result, "court_root"))
        self.assertEqual(result["court_root"],
                         "268b9474e6781007b8dd32eff4dc75bfcf94da93faffdcb90716748757961ebf")
        self.assertEqual((result["status"], result["failed"]), ("PASS", 0))

    def test_r031_and_r032_programs_and_courts_are_frozen(self):
        programs_registry = json.loads((ROOT / "spec/FROZEN-PROGRAM-REGISTRY.json").read_text())
        operator_registry = json.loads((ROOT / "spec/FROZEN-OPERATOR-REGISTRY.json").read_text())
        self.assertTrue({"program/transtemporal-native-r031", "program/native-completion-r032"}
                        <= {row["directory"] for row in programs_registry["directories"]})
        self.assertTrue({"operator/transtemporal-native-r031",
                         "operator/transtemporal-native-r031-repaired",
                         "operator/native-completion-r032"}
                        <= {row["directory"] for row in operator_registry["directories"]})

    def test_r033_program_is_current(self):
        completed = subprocess.run([
            sys.executable, "-B", str(ROOT / "tools/build_native_closure_r033_program.py"),
            "--check"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        program = json.loads((ROOT / "program/native-closure-r033/PROGRAM.json").read_text())
        self.assertTrue(rooted(program, "program_root"))
        self.assertEqual(program["engineering_revision"], "r033")
        self.assertEqual(len(program["acceptance_case_roots"]), 7)

    def test_r033_operator_runner_is_reserved_for_user(self):
        declaration = json.loads(
            (ROOT / "operator/native-closure-r033/KIT-DECLARATION.json").read_text())
        self.assertTrue(declaration["builder_authored"])
        self.assertFalse(declaration["operator_executed"])
        self.assertFalse(declaration["tier1_executed"])
        runner = ROOT / "operator/native-closure-r033/RUN-TIER1.py"
        compile(runner.read_text(encoding="utf-8"), str(runner), "exec")

    def test_pippi_c_preflight_covers_native_closure_denominator(self):
        classes = ["C_RUNTIME", "DOCUMENTATION", "PYTHON_TOOLING", "TESTS"]
        checks = set(BASE_CHECKS)
        for change_class in classes:
            checks.update(CHECKS_BY_CLASS[change_class])
        result = build_c_change_preflight(
            proposal_id="UCM.R033.NATIVE_CLOSURE",
            subject_root="1" * 64, source_manifest_root="2" * 64,
            language_standard="C17", compiler_profile_root="3" * 64,
            architecture_contract_root=native_core_profile()["profile_root"],
            change_classes=classes,
            changed_paths=sorted(["native/ucm_native_core.c", "native/ucm_archive_verify.c",
                                  "tests/test_native_closure_r033.py"]),
            declared_write_paths=sorted(["native/ucm_native_core.c", "native/ucm_archive_verify.c",
                                         "tests/test_native_closure_r033.py"]),
            declared_check_ids=sorted(checks),
            requested_effect_classes=["LOCAL_PROCESS", "READ_SOURCE", "WRITE_WORKSPACE"],
            integration_mode="SIDECAR_PARTIAL",
            mediated_channels=sorted(CHANNELS - {"TOOL_DISPATCH"}),
            native_semantic_authority="NATIVE_C",
            python_role="AUTHORING_VERIFICATION_ONLY")
        self.assertEqual(result["decision"], "READY_FOR_QUICK_CHECKS")


if __name__ == "__main__":
    unittest.main()

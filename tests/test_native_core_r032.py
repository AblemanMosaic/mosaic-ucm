from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import tempfile
import unittest
import zipfile

from uclop.canonical import Refusal
from ucm.c_preflight import (BASE_CHECKS, CHANNELS, CHECKS_BY_CLASS,
                             build_c_change_preflight)
from ucm.native_core import (build_native_program, compile_native_core,
                             detect_c17_compiler, execute_native_binary,
                             execute_native_reference, lower_native_program,
                             native_core_profile, validate_native_program,
                             verify_native_correspondence)
from ucm.capabilities import invoke
from ucm.system import capability_registry


ROOT = pathlib.Path(__file__).resolve().parents[1]


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def rooted(value: dict, field: str) -> bool:
    body = {key: item for key, item in value.items() if key != field}
    return value.get(field) == hashlib.sha256(canonical(body)).hexdigest()


def corpus() -> list[dict]:
    return [json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((ROOT / "examples/native-core").glob("*.json"))]


class NativeCoreR032Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / ".build").mkdir(exist_ok=True)

    def test_profile_and_generated_assets_are_exact(self):
        profile = json.loads((ROOT / "spec/UCM-NATIVE-CORE-PROFILE.json").read_text())
        self.assertEqual(profile, native_core_profile())
        completed = subprocess.run([
            __import__("sys").executable, "-B",
            str(ROOT / "tools/build_native_core_r032_assets.py"), "--check"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertEqual(len(corpus()), 9)

    def test_r032_program_is_current(self):
        program = json.loads((ROOT / "program/native-completion-r032/PROGRAM.json")
                             .read_text(encoding="utf-8"))
        self.assertTrue(rooted(program, "program_root"))
        self.assertEqual(program["engineering_revision"], "r032")
        self.assertEqual(len(program["acceptance_case_roots"]), 8)
        registry = json.loads((ROOT / "spec/FROZEN-PROGRAM-REGISTRY.json")
                              .read_text(encoding="utf-8"))
        row = next(item for item in registry["directories"]
                   if item["directory"] == "program/native-completion-r032")
        self.assertEqual(row["frozen_revision"], "r032")

    def test_integrated_r031_repair_is_exact(self):
        repair = json.loads((ROOT / "operator/transtemporal-native-r031-repaired/COURT-REPAIR.json")
                            .read_text(encoding="utf-8"))
        runner = ROOT / "operator/transtemporal-native-r031-repaired/RUN-TIER1.py"
        self.assertEqual(hashlib.sha256(runner.read_bytes()).hexdigest(),
                         repair["repaired_runner_sha256"])
        evidence = ROOT / "review/r031/USER-TIER1-PASS-EVIDENCE.zip"
        self.assertEqual(hashlib.sha256(evidence.read_bytes()).hexdigest(),
                         "f24e8feaff3dd5916382e1e710637712b3261add48bd83ed8a7a00d9d9374099")
        with zipfile.ZipFile(evidence) as archive:
            result = json.loads(archive.read("TIER1-RESULT.json"))
        self.assertTrue(rooted(result, "court_root"))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["case_count"], 14)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["subject_runtime_sha256"],
                         repair["subject_runtime_sha256"])

    def test_cross_platform_native_witnesses_match(self):
        rows = []
        for name in ("WINDOWS-NATIVE-CORE-WITNESS.json",
                     "WSL-NATIVE-CORE-WITNESS.json"):
            row = json.loads((ROOT / "evidence/native-core-r032" / name)
                             .read_text(encoding="utf-8"))
            self.assertTrue(rooted(row, "witness_root"))
            self.assertEqual(row["status"], "PASS_CORRESPONDENCE")
            self.assertEqual(row["program_count"], 5)
            rows.append(row)
        self.assertEqual([row["leg_id"] for row in rows],
                         ["WINDOWS_NATIVE_C17", "WSL_NATIVE_C17"])
        self.assertEqual(rows[0]["profile_root"], rows[1]["profile_root"])
        self.assertEqual(rows[0]["native_source_sha256"],
                         rows[1]["native_source_sha256"])
        self.assertEqual(rows[0]["result_set_root"], rows[1]["result_set_root"])
        self.assertEqual(rows[0]["results"], rows[1]["results"])

    def test_r032_operator_runner_is_reserved_for_user(self):
        declaration = json.loads((ROOT / "operator/native-completion-r032/KIT-DECLARATION.json")
                                 .read_text(encoding="utf-8"))
        self.assertTrue(declaration["builder_authored"])
        self.assertFalse(declaration["operator_executed"])
        self.assertFalse(declaration["tier1_executed"])
        self.assertEqual(declaration["adversarial_cases_executed"], 0)
        runner = ROOT / "operator/native-completion-r032/RUN-TIER1.py"
        compile(runner.read_text(encoding="utf-8"), str(runner), "exec")
        self.assertIn("CONTROL-NATIVE-CORRESPONDENCE", runner.read_text(encoding="utf-8"))

    def test_python_reference_executes_frozen_corpus(self):
        for program in corpus():
            self.assertEqual(validate_native_program(program), program)
            result = execute_native_reference(program)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["result_i64"], program["expected_result_i64"])
            projection = ROOT / "examples/native-core" / (
                program["program_id"].replace(".", "-") + ".ucln")
            self.assertEqual(projection.read_bytes(), lower_native_program(program))

    def test_native_c17_runtime_corresponds_exactly(self):
        compiler = detect_c17_compiler()
        self.assertTrue(compiler["available"], "r032 qualification requires C17")
        with tempfile.TemporaryDirectory(prefix="ucm-native-r032-", dir=ROOT / ".build") as raw:
            work = pathlib.Path(raw)
            binary = work / ("ucm-native.exe" if __import__("os").name == "nt" else "ucm-native")
            compile_native_core(source=ROOT / "native/ucm_native_core.c",
                                output=binary, compiler=compiler)
            result = verify_native_correspondence(programs=corpus(), binary=binary,
                                                  work_dir=work / "corpus")
            self.assertTrue(result["all_correspond"])
            self.assertEqual(result["program_count"], 9)

    def test_native_projection_denominator_and_digest_are_enforced(self):
        compiler = detect_c17_compiler()
        self.assertTrue(compiler["available"])
        program = next(row for row in corpus()
                       if row["program_id"] == "ucm.gate.three_receipts")
        with tempfile.TemporaryDirectory(prefix="ucm-native-negative-", dir=ROOT / ".build") as raw:
            work = pathlib.Path(raw)
            binary = work / ("ucm-native.exe" if __import__("os").name == "nt" else "ucm-native")
            compile_native_core(source=ROOT / "native/ucm_native_core.c", output=binary,
                                compiler=compiler)
            exact = lower_native_program(program)
            for index, mutated in enumerate((
                exact.replace(b"INSTRUCTIONS\t6\n", b"INSTRUCTIONS\t5\n", 1),
                exact.replace(b"AND\n", b"OR\n", 1),
                exact.split(b"BEGIN\n", 1)[0] + b"BEGIN\nEND\t0\t" + b"0" * 64 + b"\n",
            )):
                path = work / f"bad-{index}.ucln"; path.write_bytes(mutated)
                run = subprocess.run([str(binary), str(path),
                    hashlib.sha256(path.read_bytes()).hexdigest()], capture_output=True, text=True)
                self.assertNotEqual(run.returncode, 0)

    def test_python_reference_refuses_overflow_and_step_exhaustion(self):
        overflow = build_native_program(program_id="overflow", registers=[], max_steps=5,
            instructions=[{"op":"PUSH","arg":2**63-1},{"op":"PUSH","arg":1},
                          {"op":"ADD"},{"op":"HALT"}], expected_result_i64=0)
        loop = build_native_program(program_id="loop", registers=[], max_steps=3,
            instructions=[{"op":"JMP","arg":0},{"op":"HALT"}], expected_result_i64=0)
        for program in (overflow, loop):
            with self.assertRaises(Refusal):
                execute_native_reference(program)

    def test_pippi_c_preflight_covers_native_completion_denominator(self):
        classes = ["C_RUNTIME", "DOCUMENTATION", "PYTHON_TOOLING", "TESTS"]
        checks = set(BASE_CHECKS)
        for change_class in classes:
            checks.update(CHECKS_BY_CLASS[change_class])
        result = build_c_change_preflight(
            proposal_id="UCM.R032.NATIVE_COMPLETION",
            subject_root="1" * 64, source_manifest_root="2" * 64,
            language_standard="C17", compiler_profile_root="3" * 64,
            architecture_contract_root=native_core_profile()["profile_root"],
            change_classes=classes,
            changed_paths=["docs/UCM-NATIVE-COMPLETION.md", "native/ucm_native_core.c",
                           "src/ucm/native_core.py", "tests/test_native_core_r032.py",
                           "tools/build_native_core_r032_assets.py"],
            declared_write_paths=["docs/UCM-NATIVE-COMPLETION.md", "native/ucm_native_core.c",
                                  "src/ucm/native_core.py", "tests/test_native_core_r032.py",
                                  "tools/build_native_core_r032_assets.py"],
            declared_check_ids=sorted(checks),
            requested_effect_classes=["LOCAL_PROCESS", "READ_SOURCE", "WRITE_WORKSPACE"],
            integration_mode="SIDECAR_PARTIAL",
            mediated_channels=sorted(CHANNELS - {"TOOL_DISPATCH"}),
            native_semantic_authority="NATIVE_C",
            python_role="AUTHORING_VERIFICATION_ONLY")
        self.assertEqual(result["decision"], "READY_FOR_QUICK_CHECKS")

    def test_cli_and_abi_expose_portable_fallback(self):
        registry = capability_registry()
        names = {row["name"] for row in registry["surfaces"]}
        self.assertTrue({"DISCOVER_NATIVE_CORE_PROFILE", "COMPILE_NATIVE_CORE_PROGRAM",
                         "EXECUTE_NATIVE_CORE_REFERENCE"} <= names)
        program = corpus()[0]
        selection = {"schema": "mosaic.ucm.product-profile-selection.v0.1",
                     "profile_id": "AUTHORING",
                     "capability_registry_root": registry["root"]}
        response = invoke({"schema": "mosaic.ucm.request.v0.2",
            "surface": "EXECUTE_NATIVE_CORE_REFERENCE", "payload": {"program": program},
            "request_id": "native-reference", "profile_selection": selection})
        self.assertEqual(response["result"]["execution"], execute_native_reference(program))
        completed = subprocess.run([__import__("sys").executable, "-B", str(ROOT / "tools/ucm.py"),
            "native-reference", str(next((ROOT / "examples/native-core").glob("*.json")))],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertEqual(json.loads(completed.stdout)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()

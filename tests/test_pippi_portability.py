import json
from pathlib import Path
import tempfile
import unittest

from ucm.operator_history import verify_frozen_operator_registry
from ucm.pippi_portability import (
    build_execution_context, build_portability_witness,
    evaluate_portability_gate, inspect_portable_python_sources,
    portable_path_key, portability_policy, probe_case_sensitivity,
)
from ucm.pippi_portability_evidence import recompute_canonical_outputs
from ucm.program_history import build_frozen_program_row


ROOT = Path(__file__).resolve().parents[1]
R1 = "1" * 64
R2 = "2" * 64


class PippiPortabilityTests(unittest.TestCase):
    def context(self, leg_id: str):
        return build_execution_context(
            host_family="WINDOWS" if leg_id == "WINDOWS_NATIVE" else "LINUX",
            shell_family="POWERSHELL" if leg_id == "WINDOWS_NATIVE" else "BASH",
            path_flavour="WINDOWS" if leg_id == "WINDOWS_NATIVE" else "POSIX",
            filesystem_class=leg_id, case_sensitive=leg_id != "WINDOWS_NATIVE",
            python_implementation="CPython", python_version="3.12.3",
            source="DECLARED_EXTERNAL_HOST",
            wsl_distribution=None if leg_id == "WINDOWS_NATIVE" else "Ubuntu")

    def witness(self, leg_id: str):
        return build_portability_witness(
            leg_id=leg_id, execution_context=self.context(leg_id),
            source_root=R1, test_set_root=R2,
            canonical_outputs=[{"artifact_id": "FROZEN_PROGRAM_REGISTRY", "root": R1}],
            status="PASS", reason_codes=[])

    def test_windows_and_wsl_witnesses_allow_portable_claim(self):
        result = evaluate_portability_gate(witnesses=[
            self.witness("WINDOWS_NATIVE"), self.witness("WSL_NATIVE")])
        self.assertEqual(result["status"], "PASS_PORTABLE")
        self.assertTrue(result["portable_claim_allowed"])

    def test_missing_or_mounted_wsl_leg_cannot_claim_portability(self):
        result = evaluate_portability_gate(witnesses=[self.witness("WINDOWS_NATIVE")])
        self.assertEqual(result["status"], "PLATFORM_LEG_UNAVAILABLE")
        mounted = self.context("WSL_NATIVE")
        mounted["filesystem_class"] = "WSL_MOUNTED_WINDOWS"
        with self.assertRaisesRegex(ValueError, "PIPPI_EXECUTION_CONTEXT_INVALID"):
            build_portability_witness(
                leg_id="WSL_NATIVE", execution_context=mounted,
                source_root=R1, test_set_root=R2, canonical_outputs=[],
                status="PASS", reason_codes=[])

    def test_resealed_policy_swap_is_refused(self):
        witness = self.witness("WINDOWS_NATIVE")
        witness["portability_policy_root"] = "9" * 64
        from uclop.canonical import root
        witness["witness_root"] = root({key: value for key, value in witness.items()
                                         if key != "witness_root"})
        with self.assertRaisesRegex(ValueError, "PIPPI_PORTABILITY_POLICY_MISMATCH"):
            evaluate_portability_gate(witnesses=[witness])

    def test_source_inspection_refuses_host_flavoured_path_sort(self):
        refused = inspect_portable_python_sources(sources=[{
            "path": "src/example.py", "text": "paths = sorted(root.rglob('*'))\n"}])
        self.assertEqual(refused["status"], "REFUSED")
        passed = inspect_portable_python_sources(sources=[{
            "path": "src/example.py",
            "text": "paths = sorted(root.rglob('*'), key=lambda p: p.relative_to(root).as_posix())\n"}])
        self.assertEqual(passed["status"], "PASS")

    def test_active_deterministic_sources_pass_portability_doctor(self):
        paths = sorted(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "src").rglob("*.py"))
        paths += sorted({
            "tools/build_pippi_adaptive_contracts.py",
            "tools/build_pippi_cold_boot.py",
            "tools/build_portability_source_archive.py",
            "tools/build_release.py",
            "tools/run_portability_leg.py",
            "tools/run_public_release_qualification.py",
            "tools/verify_pippi_cold_boot.py",
            "tools/verify_release.py",
        })
        result = inspect_portable_python_sources(sources=[
            {"path": path, "text": (ROOT / path).read_text(encoding="utf-8")}
            for path in paths])
        self.assertEqual(result["status"], "PASS", result["findings"])

    def test_case_sensitivity_is_probed_and_probe_bytes_are_removed(self):
        scratch = ROOT / ".test-tmp"
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as td:
            root = Path(td)
            observed = probe_case_sensitivity(root)
            probe = root / "lowercase-probe"
            probe.write_bytes(b"probe\n")
            expected = not (root / "LOWERCASE-PROBE").exists()
            probe.unlink()
            self.assertEqual(observed, expected)
            self.assertEqual(list(root.iterdir()), [])

    def test_canonical_outputs_are_recomputed_from_exact_source(self):
        outputs = recompute_canonical_outputs(ROOT)
        self.assertEqual([row["artifact_id"] for row in outputs], [
            "CAPABILITY_REGISTRY", "FROZEN_OPERATOR_REGISTRY",
            "FROZEN_PROGRAM_REGISTRY", "MEDIATION_LIBRARY",
            "PORTABILITY_POLICY",
        ])

    def test_program_history_order_is_platform_neutral(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "B").mkdir(); (root / "a").mkdir()
            (root / "B" / "z.txt").write_text("A", encoding="utf-8")
            (root / "a" / "B.txt").write_text("b", encoding="utf-8")
            row = build_frozen_program_row(
                source_root=root, directory=".", frozen_revision="r001",
                provenance="TEST")
            self.assertEqual([m["path"] for m in row["members"]], ["B/z.txt", "a/B.txt"])
            self.assertEqual(portable_path_key(root / "a" / "B.txt", root), "a/B.txt")

    def test_operator_registry_covers_original_and_successor(self):
        registry = json.loads((ROOT / "spec/FROZEN-OPERATOR-REGISTRY.json").read_text())
        checked = verify_frozen_operator_registry(source_root=ROOT, registry=registry)
        directories = {row["directory"] for row in checked["directories"]}
        self.assertIn("operator/dependency-graph-r021", directories)
        self.assertIn("operator/dependency-graph-r023-compat", directories)

    def test_policy_requires_native_windows_and_wsl(self):
        self.assertEqual(portability_policy()["required_leg_ids"],
                         ["WINDOWS_NATIVE", "WSL_NATIVE"])


if __name__ == "__main__":
    unittest.main()

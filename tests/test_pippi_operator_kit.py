from __future__ import annotations
import importlib.util,json
from pathlib import Path
import tempfile,unittest,zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("pippi_operator_builder",ROOT/"tools/build_pippi_adaptive_operator_kit.py")
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

class PippiOperatorKitTests(unittest.TestCase):
    def test_builder_is_deterministic_and_launcher_pins_exact_kit(self):
        with tempfile.TemporaryDirectory() as raw:
            base=Path(raw);runtime=base/"runtime.zip";cold=base/"cold.zip"
            runtime.write_bytes(b"runtime");cold.write_bytes(b"cold")
            first=builder.build(runtime,cold,base/"a");second=builder.build(runtime,cold,base/"b")
            self.assertEqual((base/"a/PIPPI-r020-OPERATOR-KIT.zip").read_bytes(),
                             (base/"b/PIPPI-r020-OPERATOR-KIT.zip").read_bytes())
            self.assertIn(first["kit_sha256"],(base/"a/RUN.ps1").read_text(encoding="utf-8"))
            with zipfile.ZipFile(first["kit"]) as archive:
                manifest=json.loads(archive.read("KIT-MANIFEST.json"))
                self.assertFalse(manifest["operator_executed"])
                self.assertFalse(manifest["tier1_executed"])

    def test_runner_binds_turn_report_to_opening(self):
        source=(ROOT/"operator/pippi-adaptive-r020/RUN-TIER1.py").read_text(encoding="utf-8")
        self.assertIn("validate_turn_report(report,opening=opening)",source)
        self.assertIn('bad_report["turn_opening_root"]',source)
        self.assertIn("validate_turn_report(bad_report,opening=opening)",source)
        self.assertNotIn('bad_report["opening_root"]',source)

    def test_runner_and_manifest_state_authorship_consistently(self):
        source=(ROOT/"operator/pippi-adaptive-r020/RUN-TIER1.py").read_text(encoding="utf-8")
        self.assertIn("Builder-authored, operator-runnable Tier 1 court", source)
        self.assertNotIn("Operator-executed Tier 1 court", source)
        with tempfile.TemporaryDirectory() as raw:
            base=Path(raw);runtime=base/"runtime.zip";cold=base/"cold.zip"
            runtime.write_bytes(b"runtime");cold.write_bytes(b"cold")
            built=builder.build(runtime,cold,base/"kit")
            with zipfile.ZipFile(built["kit"]) as archive:
                manifest=json.loads(archive.read("KIT-MANIFEST.json"))
            self.assertTrue(manifest["builder_authored"])
            self.assertFalse(manifest["operator_executed"])
            self.assertFalse(manifest["tier1_executed"])

if __name__=="__main__":unittest.main()

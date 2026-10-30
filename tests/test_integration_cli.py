from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class IntegrationCliTests(unittest.TestCase):
    def run_ucm(self, *arguments: str):
        return subprocess.run([sys.executable, "-I", "-B", str(ROOT / "tools/ucm.py"),
                               *arguments], cwd=ROOT.parent, capture_output=True, text=True)

    def test_campaign_init_plan_kit_and_verify(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary); workspace = directory / "campaign"
            initialized = self.run_ucm("campaign-init",
                str(ROOT / "examples/amcas/portable-agent.integration.json"), str(workspace))
            self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
            self.assertFalse(json.loads(initialized.stdout)["ready_for_review"])
            planned = self.run_ucm("campaign-plan", str(workspace),
                                   "Integrate exact application bytes", "src/application.py")
            self.assertEqual(planned.returncode, 0, planned.stdout + planned.stderr)
            self.assertEqual(json.loads(planned.stdout)["impact"]["lane"], "QUALIFICATION")
            kit = directory / "kit.zip"
            built = self.run_ucm("build-integration-kit", str(workspace), str(kit))
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            verified = self.run_ucm("verify-integration-archive", str(kit),
                "mosaic.ucm.integration-kit.v0.1", "APPLICATION_INTEGRATION_KIT")
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)

    def test_c2_subject_control_correspondence_and_portfolio_surfaces(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            subject = directory / "subject"; subject.mkdir()
            (subject / "app.txt").write_text("subject\n", encoding="utf-8")
            binding = directory / "SUBJECT-BINDING.json"
            bound = self.run_ucm(
                "integration-bind-subject", str(subject),
                str(ROOT / "examples/integration/subject-binding-policy.json"),
                "--out", str(binding))
            self.assertEqual(bound.returncode, 0, bound.stdout + bound.stderr)
            self.assertTrue(binding.is_file())
            control = self.run_ucm(
                "integration-check-control-planes",
                str(ROOT / "examples/integration/control-plane-disposition.json"))
            self.assertEqual(control.returncode, 0, control.stdout + control.stderr)
            court = directory / "CORRESPONDENCE.json"
            compared = self.run_ucm(
                "integration-correspondence-court",
                str(ROOT / "examples/integration/native-correspondence-cases.json"),
                "--out", str(court))
            self.assertEqual(compared.returncode, 0, compared.stdout + compared.stderr)
            self.assertTrue(court.is_file())
            workspace = directory / "portfolio"
            initialized = self.run_ucm(
                "portfolio-init", str(ROOT / "examples/portfolio/MOSAIC-APPLICATIONS.json"),
                str(workspace))
            self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
            status = json.loads(self.run_ucm("portfolio-status", str(workspace)).stdout)
            self.assertEqual(status["fixed_workflow_denominator"], 7)


if __name__ == "__main__":
    unittest.main()

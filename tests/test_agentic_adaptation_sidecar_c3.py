from __future__ import annotations
import pathlib, subprocess, sys, tempfile, unittest, zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT / "src"))
from build_agentic_adaptation_sidecar import build
from ucm.artifacts import verify_deterministic_zip

class SidecarTests(unittest.TestCase):
    def test_build_is_deterministic_and_self_verifying(self):
        first = build(); second = build(); self.assertEqual(first, second)
        verify_deterministic_zip(first,
            expected_schema="mosaic.ucm.agentic-adaptation-sidecar.v0.1",
            expected_role="UCM_AMCAS_AGENTIC_ADAPTATION_SIDECAR")
        with tempfile.TemporaryDirectory() as folder:
            base = pathlib.Path(folder); archive = base / "sidecar.zip"; archive.write_bytes(first)
            with zipfile.ZipFile(archive) as zf: zf.extractall(base / "sidecar")
            subprocess.run([sys.executable, str(base / "sidecar/VERIFY.py"), str(archive)],
                           check=True, capture_output=True)
            subprocess.run([sys.executable, str(base / "sidecar/UCM-AMCAS-ADAPT.py"),
                            "--ucm-root", str(ROOT), "verify-core"],
                           check=True, capture_output=True)

if __name__ == "__main__": unittest.main()

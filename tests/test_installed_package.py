from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


class InstalledPackageTests(unittest.TestCase):
    def test_wheel_contains_runtime_resource_and_runs_from_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = pathlib.Path(temporary)
            project = base / "project"
            shutil.copytree(
                ROOT,
                project,
                ignore=shutil.ignore_patterns(".git", ".build", "build", "dist", "__pycache__", "*.pyc", "*.pyo"),
            )
            wheels = base / "wheels"
            wheels.mkdir()
            built = subprocess.run([
                sys.executable, "-m", "pip", "wheel", str(project),
                "--no-deps", "--no-build-isolation", "--wheel-dir", str(wheels),
            ], cwd=base, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr + built.stdout)
            wheel = next(wheels.glob("mosaic_ucm-*.whl"))
            installed = base / "installed"
            with zipfile.ZipFile(wheel) as archive:
                archive.extractall(installed)
                self.assertIn("uclsh/resources/COMPILER-PASS-GRAPH.json", archive.namelist())
            code = (
                "import importlib.abc,sys\n"
                f"sys.path.insert(0,{str(installed)!r})\n"
                "class Block(importlib.abc.MetaPathFinder):\n"
                " def find_spec(self,fullname,path=None,target=None):\n"
                "  if fullname=='cryptography' or fullname.startswith('cryptography.'): raise ImportError('optional dependency blocked')\n"
                "  return None\n"
                "sys.meta_path.insert(0,Block())\n"
                "from uclsh.passes import expected_compiler_semantic_root\n"
                "from ucm import invoke,orientation\n"
                "assert len(expected_compiler_semantic_root())==64\n"
                "assert orientation()['version']=='v0.1'\n"
                "assert invoke({'schema':'mosaic.ucm.request.v0.1','surface':'ORIENT','payload':{},'request_id':'base-install'})['result']['version']=='v0.1'\n"
                "assert not any(x=='cryptography' or x.startswith('cryptography.') for x in sys.modules)"
            )
            checked = subprocess.run([sys.executable, "-I", "-c", code], cwd=base, capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stderr + checked.stdout)


if __name__ == "__main__":
    unittest.main()

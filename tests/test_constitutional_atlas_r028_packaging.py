from __future__ import annotations
from pathlib import Path
import py_compile,unittest
ROOT=Path(__file__).resolve().parents[1]
class ConstitutionalAtlasR028PackagingTests(unittest.TestCase):
    def test_operator_runner_is_builder_authored_and_not_executed(self):
        import json
        declaration=json.loads((ROOT/"operator/constitutional-atlas-r028/KIT-DECLARATION.json").read_text())
        self.assertTrue(declaration["builder_authored"]);self.assertFalse(declaration["operator_executed"]);self.assertFalse(declaration["tier1_executed"])
        py_compile.compile(str(ROOT/"operator/constitutional-atlas-r028/RUN-TIER1.py"),doraise=True)
    def test_packagers_name_exact_r028_boundary(self):
        for path in (ROOT/"tools/build_constitutional_atlas_r028_operator_kit.py",ROOT/"tools/build_r028_review_transport.py"):
            py_compile.compile(str(path),doraise=True)
            self.assertIn("r028",path.read_text(encoding="utf-8"))
if __name__=="__main__":unittest.main()

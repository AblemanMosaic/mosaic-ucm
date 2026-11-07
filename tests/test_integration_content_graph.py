from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ucm.content_graph import build_graph, impact_plan


class ContentGraphTests(unittest.TestCase):
    def test_graph_and_conservative_impact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "src").mkdir(); (root / "src" / "a.py").write_text("x=1\n")
            graph = build_graph(root)
            self.assertEqual(graph["workspace_file_count"], 1)
        plan = impact_plan(["src/ucm/integration.py"])
        self.assertEqual(plan["lane"], "QUALIFICATION")
        self.assertIn("GATEWAY", plan["selected_groups"])
        self.assertTrue(impact_plan(["unknown.bin"])["unknown_impact"])

    def test_declared_output_prefix_is_excluded_without_hiding_other_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "src").mkdir(); (root / "src/a.py").write_text("pass\n")
            (root / "evidence/run").mkdir(parents=True)
            (root / "evidence/run/progress.jsonl").write_text("progress\n")
            (root / "evidence/retained.json").write_text("{}")
            graph = build_graph(root, excluded_prefixes=("evidence/run",))
            paths = [row["path"] for row in graph["nodes"]]
            self.assertEqual(paths, ["evidence/retained.json", "src/a.py"])


if __name__ == "__main__":
    unittest.main()

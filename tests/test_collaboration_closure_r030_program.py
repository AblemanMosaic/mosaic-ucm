from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CollaborationClosureR030ProgramTests(unittest.TestCase):
    def builder(self):
        path = ROOT / "tools/build_collaboration_closure_r030_program.py"
        spec = importlib.util.spec_from_file_location("r030_program", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_program_rebuilds_and_names_live_checks(self):
        records = {}
        for path in sorted((ROOT / "program/collaboration-closure-r030").glob("*.json"),
                           key=lambda item: item.name):
            records[path.name] = json.loads(path.read_text())
        frozen = json.loads((ROOT / "spec/FROZEN-PROGRAM-REGISTRY.json").read_text())
        row = next(item for item in frozen["directories"]
                   if item["directory"] == "program/collaboration-closure-r030")
        self.assertEqual(row["frozen_revision"], "r030")
        self.assertEqual(len(records["PROGRAM.json"]["acceptance_case_roots"]), 6)
        self.assertEqual(records["PROGRAM.json"]["operator_tier1_status"], "NOT_RUN")

    def test_predecessor_programs_and_courts_are_frozen(self):
        programs = json.loads((ROOT / "spec/FROZEN-PROGRAM-REGISTRY.json").read_text())
        courts = json.loads((ROOT / "spec/FROZEN-OPERATOR-REGISTRY.json").read_text())
        program_rows = {row["directory"]: row for row in programs["directories"]}
        court_rows = {row["directory"]: row for row in courts["directories"]}
        for revision, name in (("r027", "discovery-parity-r027"),
                               ("r028", "constitutional-atlas-r028"),
                               ("r029", "collaboration-integrity-r029"),
                               ("r030", "collaboration-closure-r030")):
            self.assertEqual(program_rows[f"program/{name}"]["frozen_revision"], revision)
            self.assertEqual(court_rows[f"operator/{name}"]["frozen_revision"], revision)

    def test_r029_returns_are_exact_and_separate(self):
        expectations = {"r029-independent": ["REPORT.md", "FINDINGS.json",
            "RECOMPUTE.json", "REVIEWER-EVIDENCE.zip"],
            "r029-operator": ["OPERATOR-EVIDENCE.zip"]}
        keys = {"REPORT.md": "report_sha256", "FINDINGS.json": "findings_sha256",
            "RECOMPUTE.json": "recompute_sha256",
            "REVIEWER-EVIDENCE.zip": "reviewer_evidence_sha256",
            "OPERATOR-EVIDENCE.zip": "operator_evidence_sha256"}
        for folder, names in expectations.items():
            base = ROOT / "review" / folder
            provenance = json.loads((base / "PROVENANCE.json").read_text())
            body = {key: value for key, value in provenance.items() if key != "root"}
            canonical = json.dumps(body, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":")).encode()
            self.assertEqual(provenance["root"], hashlib.sha256(canonical).hexdigest())
            for name in names:
                self.assertEqual(provenance[keys[name]],
                    hashlib.sha256((base / name).read_bytes()).hexdigest())

    def test_operator_kit_is_builder_authored_and_not_executed(self):
        declaration = json.loads((ROOT / "operator/collaboration-closure-r030/KIT-DECLARATION.json").read_text())
        self.assertTrue(declaration["builder_authored"])
        self.assertFalse(declaration["operator_executed"])
        self.assertFalse(declaration["tier1_executed"])
        runner = (ROOT / "operator/collaboration-closure-r030/RUN-TIER1.py").read_text()
        for marker in ("CCP-UNRESEALED-DECISION-SHAPE-REFUSAL",
                       "CCP-RESEALED-DECISION-LAUNDERING",
                       "CREDENTIAL-MALFORMED-NO-FILESYSTEM-WRITE",
                       "CONTROL-AFTER-FACT-RETRIEVAL-VERIFY"):
            self.assertIn(marker, runner)


if __name__ == "__main__": unittest.main()

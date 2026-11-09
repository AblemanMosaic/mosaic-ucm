from __future__ import annotations
import hashlib, json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class CollaborationIntegrityR029ProgramTests(unittest.TestCase):
    def test_program_is_frozen_under_successor_registry(self):
        registry=json.loads((ROOT/"spec/FROZEN-PROGRAM-REGISTRY.json").read_text())
        rows={row["directory"]:row for row in registry["directories"]}
        row=rows["program/collaboration-integrity-r029"]
        self.assertEqual(row["frozen_revision"],"r029")
        program=json.loads((ROOT/"program/collaboration-integrity-r029/PROGRAM.json").read_text())
        self.assertEqual(len(program["acceptance_case_roots"]),7)
        self.assertEqual(program["operator_tier1_status"],"NOT_RUN")

    def test_r028_returns_are_exact_and_provenanced(self):
        for folder,names in {
            "r028-independent":["REPORT.md","FINDINGS.json","RECOMPUTE.json","REVIEWER-EVIDENCE.zip"],
            "r028-operator":["OPERATOR-EVIDENCE.zip"]}.items():
            provenance=json.loads((ROOT/"review"/folder/"PROVENANCE.json").read_text())
            body={k:v for k,v in provenance.items() if k!="root"}
            self.assertEqual(provenance["root"],hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest())
            for name in names:
                key={"REPORT.md":"report_sha256","FINDINGS.json":"findings_sha256",
                     "RECOMPUTE.json":"recompute_sha256","REVIEWER-EVIDENCE.zip":"reviewer_evidence_sha256",
                     "OPERATOR-EVIDENCE.zip":"operator_evidence_sha256"}[name]
                self.assertEqual(provenance[key],hashlib.sha256((ROOT/"review"/folder/name).read_bytes()).hexdigest())

    def test_operator_kit_is_builder_authored_and_not_executed(self):
        declaration=json.loads((ROOT/"operator/collaboration-integrity-r029/KIT-DECLARATION.json").read_text())
        self.assertTrue(declaration["builder_authored"])
        self.assertFalse(declaration["operator_executed"])
        self.assertFalse(declaration["tier1_executed"])
        runner=(ROOT/"operator/collaboration-integrity-r029/RUN-TIER1.py").read_text(encoding="utf-8")
        self.assertIn("CCP-RESEALED-DECISION-LAUNDERING",runner)
        self.assertIn("RETRIEVAL-BYTE-MUTATION",runner)
        self.assertIn("CHANGE-IDENTITY-KEY-SWAP",runner)

if __name__=="__main__":unittest.main()

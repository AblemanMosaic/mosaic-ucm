from __future__ import annotations
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ConstitutionalAtlasR028ProgramTests(unittest.TestCase):
    def test_frozen_program_is_self_rooted_and_names_historical_checks(self):
        folder=ROOT/"program/constitutional-atlas-r028"
        records={path.name:json.loads(path.read_text(encoding="utf-8"))
                 for path in folder.glob("*.json")}
        program=records["PROGRAM.json"]
        self.assertEqual(len(program["requirement_roots"]),8)
        self.assertEqual(program["operator_tier1_status"],"NOT_RUN")
        self.assertFalse(program["publication_authorized"])
        body={key:value for key,value in program.items() if key!="program_root"}
        raw=json.dumps(body,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
        self.assertEqual(program["program_root"],hashlib.sha256(raw).hexdigest())
        self.assertEqual(program["engineering_revision"],"r028")


if __name__=="__main__":unittest.main()

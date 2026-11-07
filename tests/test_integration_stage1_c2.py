from pathlib import Path
import io
import json
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uclop.canonical import Refusal, canonical_bytes, root
from ucm.stage1 import upgrade_stage1_bundle, verify_stage1_bundle
from _integration_c2_helpers import legacy_stage1_bundle, stage1_bundle


class StageI1Tests(unittest.TestCase):
    def test_complete_bundle_verifies(self):
        with tempfile.TemporaryDirectory() as directory:
            raw, _ = stage1_bundle(Path(directory))
            self.assertEqual(verify_stage1_bundle(raw)["status"], "PASS_VERIFIED")

    def test_resealed_cross_record_mismatch_refuses(self):
        with tempfile.TemporaryDirectory() as directory:
            raw, payloads = stage1_bundle(Path(directory))
            from ucm.artifacts import deterministic_zip
            from ucm.stage1 import SCHEMA, ROLE
            changed = dict(payloads)
            changed["JOURNAL.zip"] = changed["JOURNAL.zip"] + b"x"
            resealed = deterministic_zip(changed, schema=SCHEMA, artifact_role=ROLE)
            with self.assertRaises((Refusal, ValueError, zipfile.BadZipFile)):
                verify_stage1_bundle(resealed)

    def test_legacy_bundle_verifies_and_upgrades_deterministically(self):
        with tempfile.TemporaryDirectory() as directory:
            legacy = legacy_stage1_bundle(Path(directory))
            old = verify_stage1_bundle(legacy)
            self.assertEqual(old["thr_status"], "NOT_PRESENT_LEGACY")
            upgraded = upgrade_stage1_bundle(legacy)
            self.assertEqual(upgraded, upgrade_stage1_bundle(legacy))
            new = verify_stage1_bundle(upgraded)
            self.assertEqual(new["thr_status"], "PASS_SEPARATED")
            self.assertEqual(new["subject_root"], old["subject_root"])

    def test_consistently_resealed_thr_section_mutations_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            raw, payloads = stage1_bundle(Path(directory))
            from ucm.artifacts import deterministic_zip
            from ucm.stage1 import SCHEMA, ROLE
            attacks = {
                "H_s": ("state", "members", None),
                "H_c": ("admissibility", "control_plane_root", "1" * 64),
                "H_m": ("meaning", "contract_root", "2" * 64),
                "H_j": ("locality", "gate_namespace", "UCM.INTEGRATION.FORGED"),
                "H_r": ("receipt_identity", "journal_sha256", "3" * 64),
            }
            for commitment, (section, field, value) in attacks.items():
                with self.subTest(commitment=commitment):
                    changed = dict(payloads)
                    thr = json.loads(changed["THR-CAS-MANIFEST.json"])
                    index = json.loads(changed["STAGE-I1-INDEX.json"])
                    if commitment == "H_s":
                        thr[section][field][0]["sha256"] = "4" * 64
                    else:
                        thr[section][field] = value
                    thr["commitments"][commitment] = root(thr[section])
                    thr["h_body"] = root({key: raw for key, raw in thr.items()
                                          if key != "h_body"})
                    index[commitment] = thr["commitments"][commitment]
                    index["thr_manifest_root"] = thr["h_body"]
                    index["index_root"] = root({key: raw for key, raw in index.items()
                                                if key != "index_root"})
                    changed["THR-CAS-MANIFEST.json"] = canonical_bytes(thr)
                    changed["STAGE-I1-INDEX.json"] = canonical_bytes(index)
                    resealed = deterministic_zip(changed, schema=SCHEMA,
                                                 artifact_role=ROLE)
                    with self.assertRaises((Refusal, ValueError)):
                        verify_stage1_bundle(resealed)


if __name__ == "__main__":
    unittest.main()

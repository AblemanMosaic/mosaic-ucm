from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from uclop.canonical import Refusal, root
from ucm.transtemporal_archive import (build_native_manifest,
                                       build_native_manifest_binding,
    build_semcrys_plan, diff_revisions, ingest_tree, materialize_revision,
    storage_report, verify_revision)
from ucm.capabilities import invoke
from ucm.system import capability_registry
from ucm.native_core import compile_native_core, detect_c17_compiler


ROOT = Path(__file__).resolve().parents[1]


class TranstemporalArchiveTests(unittest.TestCase):
    def _roots(self):
        return root({"semantic": 1}), root({"governance": 1}), root({"jurisdiction": 1})

    def test_readme_leads_with_constitutional_substrate_and_native_scope(self):
        lead=(ROOT/"README.md").read_text(encoding="utf-8")[:5000]
        self.assertIn("substrate for **constitutional computing**",lead)
        self.assertIn("Python supplies the most",lead)
        self.assertIn("native C slices",lead)
        native=(ROOT/"native/ucm_archive_verify.c").read_text(encoding="utf-8")
        self.assertIn("SHA-256 compatibility",native)

    def test_two_revisions_deduplicate_reconstruct_and_keep_integer_ids(self):
        with tempfile.TemporaryDirectory() as raw:
            base=Path(raw);source=base/"source";repo=base/"archive";source.mkdir()
            (source/"a.txt").write_bytes(b"same\n");(source/"b.txt").write_bytes(b"first\n")
            semantic,governance,jurisdiction=self._roots()
            first=ingest_tree(source=source,repository=repo,revision="r001",
                semantic_root=semantic,governance_root=governance,jurisdiction_root=jurisdiction)
            (source/"b.txt").write_bytes(b"second\n");(source/"c.txt").write_bytes(b"same\n")
            second=ingest_tree(source=source,repository=repo,revision="r002",parent_revision="r001",
                semantic_root=semantic,governance_root=governance,jurisdiction_root=jurisdiction)
            left={row["path"]:row["file_id"] for row in first["MANIFEST.json"]["files"]}
            right={row["path"]:row["file_id"] for row in second["MANIFEST.json"]["files"]}
            self.assertEqual(left["a.txt"],right["a.txt"])
            self.assertNotIn(right["c.txt"],set(left.values()))
            report=storage_report(repository=repo)
            self.assertGreater(report["deduplicated_bytes"],0)
            destination=base/"restored"
            materialize_revision(repository=repo,revision="r002",destination=destination)
            self.assertEqual((destination/"b.txt").read_bytes(),b"second\n")
            self.assertEqual(diff_revisions(repository=repo,before="r001",after="r002")["changed"],["b.txt"])
            self.assertEqual(verify_revision(repository=repo,revision="r002")["status"],"PASS")

    def test_tampered_object_refuses_and_dkn_stays_unbound(self):
        with tempfile.TemporaryDirectory() as raw:
            base=Path(raw);source=base/"source";repo=base/"archive";source.mkdir()
            (source/"x").write_bytes(b"x")
            semantic,governance,jurisdiction=self._roots()
            result=ingest_tree(source=source,repository=repo,revision="r001",
                semantic_root=semantic,governance_root=governance,jurisdiction_root=jurisdiction)
            self.assertEqual(result["DKN-BINDING.json"]["status"],"DECLARED_UNBOUND")
            digest=result["MANIFEST.json"]["files"][0]["digest"]["blake3_256"]
            (repo/"objects"/"blake3-256"/digest[:2]/digest).write_bytes(b"y")
            with self.assertRaises((Refusal,ValueError)):
                verify_revision(repository=repo,revision="r001")

    def test_semcrys_is_optional_and_never_claims_an_effect(self):
        with tempfile.TemporaryDirectory() as raw:
            base=Path(raw);source=base/"source";repo=base/"archive";source.mkdir();(source/"x").write_bytes(b"x");(source/"y").write_bytes(b"y")
            semantic,governance,jurisdiction=self._roots()
            ingest_tree(source=source,repository=repo,revision="r001",
                semantic_root=semantic,governance_root=governance,jurisdiction_root=jurisdiction)
            held=build_semcrys_plan(repository=repo,revision="r001",
                semcrys_manifest_root=None,memory_vault_binding_root=None)
            ready=build_semcrys_plan(repository=repo,revision="r001",
                semcrys_manifest_root="1"*64,memory_vault_binding_root="2"*64)
            self.assertEqual(held["status"],"HELD_OPTIONAL_PACK_UNBOUND")
            self.assertEqual(ready["status"],"READY_FOR_EXTERNAL_COMPRESSION")
            self.assertFalse(ready["plan_performs_effects"])

    def test_native_projection_and_cli_help_are_stable(self):
        with tempfile.TemporaryDirectory() as raw:
            base=Path(raw);source=base/"source";repo=base/"archive";source.mkdir();(source/"x").write_bytes(b"x");(source/"y").write_bytes(b"y")
            semantic,governance,jurisdiction=self._roots()
            revision=ingest_tree(source=source,repository=repo,revision="r001",
                semantic_root=semantic,governance_root=governance,jurisdiction_root=jurisdiction)
            native=build_native_manifest(repository=repo,revision="r001")
            binding=build_native_manifest_binding(repository=repo,revision="r001")
            expected_root=revision["MANIFEST.json"]["manifest_root"]
            self.assertTrue(native.startswith(
                f"UCM-NATIVE-MANIFEST\t2\tSHA-256\t{expected_root}\t2\n".encode()))
            self.assertIn(b"\nEND\t2\t",native)
            compiler=detect_c17_compiler();self.assertTrue(compiler["available"])
            executable=base/("ucm-archive-verify.exe" if __import__("os").name=="nt" else "ucm-archive-verify")
            compile_native_core(source=ROOT/"native/ucm_archive_verify.c",output=executable,compiler=compiler)
            manifest_path=base/"NATIVE-MANIFEST.tsv";manifest_path.write_bytes(native)
            passed=subprocess.run([str(executable),str(manifest_path),str(source),expected_root,
                binding["rows_root"],str(binding["member_count"])],
                capture_output=True,text=True)
            self.assertEqual(passed.returncode,0,passed.stderr+passed.stdout)
            self.assertEqual(json.loads(passed.stdout)["checked"],2)
            truncated=base/"TRUNCATED.tsv";truncated.write_bytes(native.split(b"\nEND\t",1)[0]+b"\n")
            refused=subprocess.run([str(executable),str(truncated),str(source),expected_root,
                binding["rows_root"],str(binding["member_count"])],
                capture_output=True,text=True)
            self.assertNotEqual(refused.returncode,0)
            forged=base/"RESEALED-TRUNCATED.tsv"
            lines=native.splitlines(keepends=True)
            forged_rows=lines[1];forged_count=1
            forged.write_bytes(
                f"UCM-NATIVE-MANIFEST\t2\tSHA-256\t{expected_root}\t{forged_count}\n".encode()
                + forged_rows
                + f"END\t{forged_count}\t{hashlib.sha256(forged_rows).hexdigest()}\n".encode())
            refused=subprocess.run([str(executable),str(forged),str(source),expected_root,
                binding["rows_root"],str(binding["member_count"])],capture_output=True,text=True)
            self.assertNotEqual(refused.returncode,0)
        result=subprocess.run([sys.executable,"-m","ucm.pippi_cli","archive-verify","--help"],
            cwd=ROOT,env={**__import__("os").environ,"PYTHONPATH":str(ROOT/"src")},capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("repository",result.stdout)
        builder=subprocess.run([
            sys.executable,"-W","error::SyntaxWarning",
            str(ROOT/"tools/build_transtemporal_r031_operator_kit.py"),"--help"],
            cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(builder.returncode,0,builder.stderr)
        self.assertEqual(builder.stderr,"")

    def test_read_only_public_abi_matches_direct_verification(self):
        with tempfile.TemporaryDirectory() as raw:
            base=Path(raw);source=base/"source";repo=base/"archive";source.mkdir();(source/"x").write_bytes(b"x")
            semantic,governance,jurisdiction=self._roots()
            ingest_tree(source=source,repository=repo,revision="r001",
                semantic_root=semantic,governance_root=governance,jurisdiction_root=jurisdiction)
            registry=capability_registry()
            request={"schema":"mosaic.ucm.request.v0.2","surface":"VERIFY_TRANSTEMPORAL_REVISION",
                "payload":{"repository":str(repo),"revision":"r001"},"request_id":"test:archive",
                "profile_selection":{"schema":"mosaic.ucm.product-profile-selection.v0.1",
                    "profile_id":"VERIFY_ONLY","capability_registry_root":registry["root"]}}
            self.assertEqual(invoke(request)["result"],verify_revision(repository=repo,revision="r001"))

    def test_operator_runner_is_builder_authored_and_unexecuted(self):
        declaration=json.loads((ROOT/"operator/transtemporal-native-r031/KIT-DECLARATION.json").read_text(encoding="utf-8"))
        self.assertTrue(declaration["builder_authored"])
        self.assertFalse(declaration["operator_executed"])
        self.assertFalse(declaration["tier1_executed"])
        source=(ROOT/"operator/transtemporal-native-r031/RUN-TIER1.py").read_text(encoding="utf-8")
        compile(source,"RUN-TIER1.py","exec")
        self.assertIn("OBJECT-BYTES-MUTATION",source)
        self.assertIn("THR-STATE-RESEALED-SWAP",source)


if __name__=="__main__": unittest.main()

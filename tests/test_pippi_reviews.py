from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from tests.release_fixture import write_unbound_release_archive

from ucm.pippi_global import PippiHub, build_onboarding, build_project
from ucm.pippi_reviews import (ReviewStore, SPEC_SCHEMA, build_review_envelope,
                               build_review_return_archive, run_review_envelope,
                               verify_review_envelope)


class PippiReviewEnvelopeTests(unittest.TestCase):
    def fixture(self, root: Path, review_id: str = "review-r003"):
        source = root / "source"; source.mkdir(parents=True)
        (source / "subject.txt").write_text("exact subject\n", encoding="utf-8", newline="\n")
        (source / "runner.py").write_text(
            "import argparse,json,pathlib\n"
            "p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);a=p.parse_args()\n"
            "o=pathlib.Path(a.output_dir);o.mkdir(parents=True,exist_ok=True)\n"
            "(o/'REPORT.json').write_text(json.dumps({'status':'PASS'},sort_keys=True,separators=(',',':'))+'\\n',encoding='utf-8')\n",
            encoding="utf-8", newline="\n")
        spec = {
            "schema": SPEC_SCHEMA,
            "review_id": review_id,
            "review_class": "INDEPENDENT_RELEASE_REVIEW",
            "subject_role": "TEST_SUBJECT",
            "declared_subject_root": None,
            "members": [
                {"source": "runner.py", "path": "runner/review.py", "role": "REVIEW_RUNNER"},
                {"source": "subject.txt", "path": "subject/subject.txt", "role": "SUBJECT"},
            ],
            "runner": {
                "command": ["{PYTHON}", "runner/review.py", "--output-dir", "{OUTPUT_DIR}"],
                "required_paths": ["runner/review.py", "subject/subject.txt"],
                "expected_outputs": ["REPORT.json"],
                "timeout_seconds": 60,
            },
            "limitations": ["TEST_FIXTURE"],
            "independent_review_required": True,
        }
        hub = PippiHub(root / "hub")
        hub.initialize(build_onboarding(governor_label="test-governor", mosaic_id=None,
                                        dkn_public_key=None, github_account=None,
                                        github_credential_reference=None))
        project = hub.add_project(build_project(project_id="sample", title="Sample", workspace=str(source),
            github_url=None, application_command=None, verification_command=None))
        return source, spec, hub, project

    def test_deterministic_envelope_and_standalone_verifier(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source,spec,hub,project=self.fixture(root)
            first=root/"first.zip";second=root/"second.zip"
            a=build_review_envelope(project=project,spec=spec,spec_dir=source,output_path=first)
            b=build_review_envelope(project=project,spec=spec,spec_dir=source,output_path=second)
            self.assertEqual(first.read_bytes(),second.read_bytes())
            self.assertEqual(a["archive_sha256"],b["archive_sha256"])
            self.assertEqual(verify_review_envelope(first)["status"],"PASS")
            unpack=root/"unpack";unpack.mkdir()
            import zipfile
            with zipfile.ZipFile(first,"r") as archive:archive.extractall(unpack)
            result=subprocess.run([sys.executable,str(unpack/"VERIFY.py"),str(first),a["archive_sha256"]],
                                  capture_output=True,text=True,check=True)
            self.assertEqual(json.loads(result.stdout)["status"],"PASS")

    def test_local_replay_records_process_without_interpreting_verdict(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source,spec,hub,project=self.fixture(root)
            envelope=root/"review.zip";evidence=root/"evidence.zip";events=[]
            build_review_envelope(project=project,spec=spec,spec_dir=source,output_path=envelope)
            result=run_review_envelope(envelope,evidence,
                                       expected_sha256=verify_review_envelope(envelope)["archive_sha256"],
                                       progress=events.append)
            self.assertEqual(result["status"],"PASS")
            self.assertEqual(result["domain_verdict"],"NOT_INTERPRETED_BY_PIPPI")
            self.assertTrue(evidence.is_file())
            self.assertEqual([row["phase"] for row in events],["VERIFY","VERIFY","EXTRACT","EXTRACT","RUN","RUN","SEAL"])

    def test_registered_review_courthouse_return_and_publication_hold(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source,spec,hub,project=self.fixture(root)
            envelope=root/"review.zip"
            built=build_review_envelope(project=project,spec=spec,spec_dir=source,output_path=envelope)
            store=ReviewStore(hub);record=store.register(project_id="sample",envelope_path=envelope)
            self.assertEqual(record["status"],"PACKAGED")
            dispatch=store.prepare_courthouse(project_id="sample",review_id=spec["review_id"],
                                               destination_jurisdiction="aok:courthouse")
            self.assertFalse(dispatch["work_order"]["remote_dispatch_authorized"])
            evidence=root/"reviewer";evidence.mkdir();(evidence/"REPORT.md").write_text("PASS\n",encoding="utf-8")
            returned=root/"return.zip"
            build_review_return_archive(review_id=spec["review_id"],envelope_sha256=built["archive_sha256"],
                reviewer_identity_root="a"*64,reported_outcome="QUALIFIED_RECOMMENDATION_ONLY",
                findings=[{"id":"T1","severity":"LOW","summary":"fixture"}],
                limitations=["INDEPENDENT_TIER1_NOT_PERFORMED"],
                evidence_members=[{"source":"REPORT.md","path":"evidence/REPORT.md"}],
                source_dir=evidence,output_path=returned)
            imported=store.import_return(project_id="sample",review_id=spec["review_id"],return_path=returned)
            self.assertEqual(imported["status"],"RETURNED")
            substance=store.substance(project_id="sample",review_id=spec["review_id"])
            self.assertEqual(substance["severity_counts"],{"LOW":1})
            self.assertEqual(substance["reviewer_identity_root"],"a"*64)
            self.assertEqual(substance["findings"][0]["id"],"T1")
            self.assertEqual(substance["interpretation"],"EXACT_PROJECTION_NOT_ALTERNATE_AUTHORITY")
            fixture=write_unbound_release_archive(root/"publication-artifact.zip")
            proposal=store.propose_publication(project_id="sample",review_id=spec["review_id"],
                artifact_path=fixture["path"],artifact_sha256=fixture["sha256"],
                targets=["GITHUB"],dkn_public_namespace=None)
            self.assertTrue(proposal["human_authorization_required"])
            self.assertFalse(proposal["publication_plan"]["provider_dispatch_authorized"])
            self.assertEqual(hub.verify()["review_record_roots"],[proposal["review_record"]["review_record_root"]])

    def test_review_comparison_is_structural_and_nonsemantic(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source,first_spec,hub,project=self.fixture(root)
            store=ReviewStore(hub)
            for review_id in ("review-r003","review-r004"):
                spec={**first_spec,"review_id":review_id};envelope=root/f"{review_id}.zip"
                build_review_envelope(project=project,spec=spec,spec_dir=source,output_path=envelope)
                store.register(project_id="sample",envelope_path=envelope)
            result=store.compare(project_id="sample",left_review_id="review-r003",right_review_id="review-r004")
            self.assertEqual(result["semantic_interpretation"],"NOT_INFERRED")
            self.assertTrue(any(row["field"]=="envelope_root" for row in result["changes"]))


if __name__ == "__main__":
    unittest.main()

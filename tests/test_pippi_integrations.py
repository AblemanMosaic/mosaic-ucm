from __future__ import annotations
import tempfile
from pathlib import Path
import unittest
import json
from ucm.pippi_global import build_project
from ucm.pippi_integrations import archive_local,build_archive_reference,build_courthouse_work_order,build_publication_plan
from ucm.pippi_archive_policy import (ArchivePolicyRefusal,
 CUSTODY_PREFIXES,evaluate_archive_availability,validate_release_partition,
 validate_transtemporal_reference)
from uclop.canonical import root
from tests.release_fixture import (write_signed_release_archive,
                                   write_unbound_release_archive)

class IntegrationTests(unittest.TestCase):
 def project(self,root):return build_project(project_id="p",title="p",workspace=str(root),github_url=None,
  application_command=None,verification_command=None)
 def test_public_archive_policy_matches_code(self):
  policy=json.loads((Path(__file__).resolve().parents[1]/"spec"/"PIPPI-TRANSTEMPORAL-ARCHIVE-POLICY.json").read_text(encoding="utf-8"))
  self.assertEqual(policy["custody_prefixes"],list(CUSTODY_PREFIXES))
  self.assertEqual(policy["profile_rules"]["RUNTIME"],"REFERENCE_ONLY")
  self.assertEqual(policy["profile_rules"]["SDK"],"REFERENCE_ONLY")
 def test_archive_reference_and_local_store(self):
  with tempfile.TemporaryDirectory() as td:
   digest,path=archive_local(data_root=Path(td),data=b"exact")
   record=build_archive_reference(project=self.project(td),artifact_role="REPORT",artifact_sha256=digest,
    artifact_bytes=5,semantic_root=root({"meaning":"review"}),
    metadata_root=root({"role":"REPORT"}),governance_root=root({"effect":"NONE"}),
    backend="LOCAL_CONTENT_STORE",backend_reference=str(path))
   self.assertEqual(record["artifact_sha256"],digest)
   self.assertEqual(record["commitments"]["state_root"],digest)
   self.assertEqual(validate_transtemporal_reference(record),record)
   availability=evaluate_archive_availability(references=[record,record],available_sha256=[digest])
   self.assertEqual(availability["status"],"PASS")
   self.assertEqual(availability["unique_object_count"],1)
   self.assertEqual(availability["deduplicated_bytes"],5)
 def test_missing_transtemporal_object_is_a_typed_hold(self):
  with tempfile.TemporaryDirectory() as td:
   digest,path=archive_local(data_root=Path(td),data=b"exact")
   record=build_archive_reference(project=self.project(td),artifact_role="REPORT",artifact_sha256=digest,
    artifact_bytes=5,semantic_root=root({"meaning":"review"}),
    metadata_root=root({"role":"REPORT"}),governance_root=root({"effect":"NONE"}),
    backend="LOCAL_CONTENT_STORE",backend_reference=str(path))
   result=evaluate_archive_availability(references=[record],available_sha256=[])
   self.assertEqual(result["status"],"HOLD_FOR_ARCHIVE_AVAILABILITY")
 def test_release_profiles_refuse_inline_history_and_bind_review_denominator(self):
  source=["src/ucm/system.py","review/REPORT.md","integration/session-returns/RETURN.zip"]
  result=validate_release_partition(runtime_paths=["src/ucm/system.py"],
   sdk_paths=["src/ucm/system.py"],review_paths=source[1:],source_paths=source,
   review_mode="SELF_CONTAINED_CUSTODY")
  self.assertEqual(result["custody_denominator_count"],2)
  with self.assertRaisesRegex(ArchivePolicyRefusal,"PIPPI_ACTIVE_PROFILE_INLINE_CUSTODY_REFUSED"):
   validate_release_partition(runtime_paths=["review/REPORT.md"],sdk_paths=[],review_paths=source[1:],
    source_paths=source,review_mode="SELF_CONTAINED_CUSTODY")
  with self.assertRaisesRegex(ArchivePolicyRefusal,"PIPPI_REVIEW_CUSTODY_DENOMINATOR_MISMATCH"):
   validate_release_partition(runtime_paths=[],sdk_paths=[],review_paths=["review/REPORT.md"],
    source_paths=source,review_mode="SELF_CONTAINED_CUSTODY")
 def test_courthouse_is_transport_owner_without_dispatch_authority(self):
  with tempfile.TemporaryDirectory() as td:
   record=build_courthouse_work_order(project=self.project(td),objective="review",payload_root="1"*64,
    destination_jurisdiction="aok:courthouse")
   self.assertEqual(record["transport_owner"],"AOK_COURTHOUSE");self.assertFalse(record["remote_dispatch_authorized"])
 def test_crystal_owns_publication(self):
  with tempfile.TemporaryDirectory() as td:
   fixture=write_unbound_release_archive(Path(td)/"artifact.zip")
   record=build_publication_plan(project=self.project(td),artifact_path=fixture["path"],
    artifact_sha256=fixture["sha256"],targets=["CRYSTAL_NETWORK","GITHUB"],
    dkn_public_namespace=None)
   self.assertEqual(record["publication_owner"],"CRYSTAL_NETWORK");self.assertFalse(record["provider_dispatch_authorized"])
   self.assertEqual(record["publication_identity_status"],"CONTENT_ADDRESSED_NOT_DKN_SELF_CERTIFIED")
   self.assertEqual(record["self_certificate_status"],"READY_FOR_EXTERNAL_DKN_CERTIFICATION")
   self.assertEqual(record["self_certificate_root"],fixture["metadata"]["META/SELF-CERTIFICATE.json"]["certificate_root"])
 def test_dkn_publication_refuses_unbound_certificate(self):
  with tempfile.TemporaryDirectory() as td:
   fixture=write_unbound_release_archive(Path(td)/"artifact.zip")
   with self.assertRaisesRegex(Exception,"PIPPI_PUBLICATION_DKN_SELF_CERTIFICATION_REQUIRED"):
    build_publication_plan(project=self.project(td),artifact_path=fixture["path"],
     artifact_sha256=fixture["sha256"],targets=["GITHUB"],
     dkn_public_namespace="dkn:public:example")
 def test_dkn_publication_derives_verified_certificate(self):
  with tempfile.TemporaryDirectory() as td:
   fixture=write_signed_release_archive(Path(td)/"artifact.zip")
   record=build_publication_plan(project=self.project(td),artifact_path=fixture["path"],
    artifact_sha256=fixture["sha256"],targets=["GITHUB"],
    dkn_public_namespace="mosaic.ucm.v0.1")
   self.assertEqual(record["publication_identity_status"],"DKN_SELF_CERTIFIED")
   self.assertEqual(record["self_certificate_status"],"PASS_SELF_CERTIFIED")
   self.assertEqual(record["self_certificate_root"],fixture["metadata"]["META/SELF-CERTIFICATE.json"]["certificate_root"])
 def test_publication_refuses_wrong_artifact_pin(self):
  with tempfile.TemporaryDirectory() as td:
   fixture=write_unbound_release_archive(Path(td)/"artifact.zip")
   with self.assertRaisesRegex(Exception,"PIPPI_PUBLICATION_ARTIFACT_PIN_MISMATCH"):
    build_publication_plan(project=self.project(td),artifact_path=fixture["path"],
     artifact_sha256="f"*64,targets=["GITHUB"],dkn_public_namespace=None)

if __name__=="__main__":unittest.main()

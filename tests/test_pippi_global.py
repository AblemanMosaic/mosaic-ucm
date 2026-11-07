from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from ucm.pippi_global import (CHANNELS, HubRefusal, PippiHub, build_context_injection,
                              build_onboarding, build_project,
                              build_project_identity_transition)


class PippiGlobalTests(unittest.TestCase):
    @staticmethod
    def temporary():
        return tempfile.TemporaryDirectory()
    def onboarding(self):
        return build_onboarding(governor_label="local-governor",mosaic_id="mosaic:person:example",
            dkn_public_key="ed25519:0123456789abcdef0123456789abcdef",github_account="AblemanMosaic",
            github_credential_reference="WINDOWS_CREDENTIAL_MANAGER:github.com/AblemanMosaic")

    def project(self, root: Path):
        return build_project(project_id="sample",title="Sample",workspace=str(root),
            github_url="https://github.com/AblemanMosaic/sample",application_command=["python","app.py"],
            verification_command=["python","verify.py"],readme="README.md",docs=["docs/START.md"])

    def test_public_identity_and_external_secret_policy(self):
        record=self.onboarding()
        self.assertEqual(record["secret_storage"],"EXTERNAL_PROVIDER_ONLY")
        self.assertTrue(record["archive_default_enabled"])
        with self.assertRaisesRegex(HubRefusal,"PIPPI_RAW_CREDENTIAL_REFUSED"):
            build_onboarding(governor_label="g",mosaic_id=None,dkn_public_key=None,
                github_account=None,github_credential_reference="ghp_abcdefghijklmnopqrstuvwxyz")

    def test_version_policy_refuses_implicit_bump(self):
        with self.temporary() as td:
            with self.assertRaisesRegex(HubRefusal,"PIPPI_VERSION_CHANGE_REQUIRES_EXPLICIT_USER_AUTHORIZATION"):
                build_project(project_id="sample",title="Sample",workspace=td,github_url=None,
                    application_command=None,verification_command=None,public_version="v0.2.0")

    def test_revision_is_preferred_and_version_requires_bound_approval(self):
        with self.temporary() as td:
            project=self.project(Path(td))
            revised=build_project_identity_transition(project=project,
                requested_public_version="v0.1",requested_revision="r002",
                external_approval=None,expected_approval_policy_root=None,now=None)
            self.assertEqual(revised["transition"]["change_class"],"ENGINEERING_REVISION")
            self.assertTrue(revised["transition"]["default_preference_applied"])
            with self.assertRaisesRegex(HubRefusal,
                    "PIPPI_VERSION_CHANGE_REQUIRES_EXPLICIT_USER_AUTHORIZATION"):
                build_project_identity_transition(project=project,
                    requested_public_version="v0.2",requested_revision="r002",
                    external_approval=None,expected_approval_policy_root=None,now=None)

    def test_hub_revision_transition_is_journaled(self):
        with self.temporary() as td:
            root=Path(td);hub=PippiHub(root/"hub");hub.initialize(self.onboarding())
            hub.add_project(self.project(root))
            result=hub.transition_project_identity(project_id="sample",
                requested_public_version="v0.1",requested_revision="r002")
            self.assertEqual(result["project"]["revision"],"r002")
            self.assertEqual(hub.get_project("sample")["revision"],"r002")
            self.assertEqual(hub.verify()["event_count"],3)

    def test_hub_project_context_and_chain(self):
        with self.temporary() as td:
            root=Path(td); hub=PippiHub(root/"hub");hub.initialize(self.onboarding())
            project=hub.add_project(self.project(root))
            context=build_context_injection(project=project,session_root="session:one",scenario="CODING",
                requested_rules=["VERSION_POLICY","SEVEN_CHANNEL_COVERAGE","COURTHOUSE_ROUTING"])
            self.assertEqual(context["exact_context"]["coverage_channels"],list(CHANNELS))
            hub.append("CONTEXT_INJECTION_BUILT",{"context_injection_root":context["context_injection_root"]})
            result=hub.verify()
            self.assertEqual(result["status"],"PASS")
            self.assertEqual(result["event_count"],3)

    def test_journal_tamper_refuses(self):
        with self.temporary() as td:
            hub=PippiHub(Path(td)/"hub");hub.initialize(self.onboarding())
            raw=hub.journal.read_text(encoding="utf-8").replace("HUB_INITIALIZED","HUB_CHANGED")
            hub.journal.write_text(raw,encoding="utf-8")
            with self.assertRaisesRegex(HubRefusal,"PIPPI_HUB_JOURNAL_INVALID"):
                hub.verify()

    def test_duplicate_project_refuses(self):
        with self.temporary() as td:
            root=Path(td);hub=PippiHub(root/"hub");hub.initialize(self.onboarding())
            project=self.project(root);hub.add_project(project)
            with self.assertRaisesRegex(HubRefusal,"PIPPI_PROJECT_EXISTS"):
                hub.add_project(project)

    def test_project_tamper_and_stale_head_refuse(self):
        with self.temporary() as td:
            root=Path(td);hub=PippiHub(root/"hub");hub.initialize(self.onboarding())
            project=hub.add_project(self.project(root));path=hub.projects/"sample.json"
            path.write_bytes(path.read_bytes().replace(b'"status":"REGISTERED"',b'"status":"ALTERED"'))
            with self.assertRaisesRegex(HubRefusal,"PIPPI_PROJECT_INVALID"):hub.verify()
            path.write_bytes(__import__('uclop.canonical',fromlist=['canonical_bytes']).canonical_bytes(project)+b"\n")
            with self.assertRaisesRegex(HubRefusal,"PIPPI_EXPECTED_HEAD_MISMATCH"):
                hub.append("TEST",{},expected_head="0"*64)


if __name__=="__main__": unittest.main()


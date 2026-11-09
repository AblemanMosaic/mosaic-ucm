"""One positive cold CLI journey through the existing common-turn workflow."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from uclop.canonical import canonical_bytes
from ucm.pippi_adaptive import negotiate_host_mode
from ucm.pippi_cmba import CMBA_WHEEL_SHA256
from ucm.pippi_global import PippiHub
from ucm.pippi_portability import build_execution_context
from ucm.pippi_service import dispatch_read
from test_pippi_turn_record_positive import common_turn_fixture


ROOT = Path(__file__).resolve().parents[1]
_ISOLATED_CLI = (
    "import pathlib,runpy,sys;"
    "source=pathlib.Path(sys.argv.pop(1)).resolve();"
    "sys.path.insert(0,str(source));import ucm;"
    "assert pathlib.Path(ucm.__file__).resolve().is_relative_to(source);"
    "runpy.run_module('ucm.pippi_cli',run_name='__main__')"
)


class PippiCliCommonPositiveTests(unittest.TestCase):
    def test_real_cli_common_turn_assessment_import_reconcile_and_read_projection(self):
        opening_fixture, report_fixture, details = common_turn_fixture()
        with tempfile.TemporaryDirectory(prefix="ucm-r034-common-cli-", dir=ROOT.parent) as temporary:
            base = Path(temporary).resolve()
            self.assertEqual(base.parent, ROOT.parent.resolve())
            start = base / "empty-start-directory"
            start.mkdir()
            hub_path = base / "local-hub"

            def cli(command: str, *arguments: str, payload=None):
                args = list(arguments)
                if payload is not None:
                    request = base / (command + "-request.json")
                    request.write_bytes(canonical_bytes(payload) + b"\n")
                    args.append(str(request))
                process = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", "-c",
                    _ISOLATED_CLI, str(ROOT / "src"), "--data-root", str(hub_path),
                    command, *args], cwd=start, capture_output=True, check=False)
                self.assertEqual(process.returncode, 0,
                    (command, process.stdout.decode("utf-8", errors="replace"),
                     process.stderr.decode("utf-8", errors="replace")))
                return json.loads(process.stdout)

            onboarding = cli("onboard", "--governor-label", "positive-common-turn-operator")
            self.assertEqual(onboarding["status"], "PASS")
            project = cli("project-add", "pippi", "P/PPI", str(ROOT), "--revision", "r034",
                "--application-command", "pippi", "dashboard",
                "--verification-command", "pippi", "interface-doctor")
            self.assertEqual(project["project_root"], opening_fixture["project_root"])
            host = negotiate_host_mode(host_id="codex-local", requested_mode="EXECUTABLE_LOCAL",
                capability_ids=["ARTIFACT_EXCHANGE", "FILESYSTEM_READ", "PROCESS_EXECUTION"],
                adapter_root=None)
            context = build_execution_context(host_family="WINDOWS", shell_family="POWERSHELL",
                path_flavour="WINDOWS", filesystem_class="WINDOWS_NATIVE", case_sensitive=False,
                python_implementation="CPython", python_version="3.12.3",
                source="DECLARED_EXTERNAL_HOST", wsl_distribution=None)
            prepared = cli("turn-prepare", payload={"project": project, "host_profile": host,
                "sequence": 1, "previous_turn_root": None, "scenario": "CODING",
                "requested_rule_ids": [],
                "acceptance_case_roots": opening_fixture["acceptance_case_roots"],
                "journal_head": opening_fixture["journal_head"], "execution_context": context})
            opening = prepared["record"]
            self.assertEqual(opening, opening_fixture)
            self.assertFalse(prepared["reporting_requirements"]["per_tool_interception_required"])
            report_request = {"opening": opening, **{key: report_fixture[key] for key in (
                "summary", "changed_paths", "artifact_roots", "evidence_roots",
                "unresolved_items", "next_action", "claim_class")}, "turn_details": details}
            submitted = cli("turn-report", payload=report_request)
            report, record = submitted["report"], submitted["turn_record"]
            self.assertEqual(report, report_fixture)
            self.assertEqual(submitted["record"]["turn_record_root"], record["turn_record_root"])
            self.assertEqual(record["status"], "INFORMATION_COMPLETE")

            assessment_request = {"opening": opening, "report": report, "turn_record": record,
                                  "expected_wheel_sha256": CMBA_WHEEL_SHA256}
            assessment = cli("cmba-turn-assess", payload=assessment_request)
            self.assertEqual(assessment["outcome"], "STRUCTURAL_BINDING_VALID")
            verified = cli("cmba-turn-verify", payload={"value": assessment, **assessment_request})
            self.assertEqual(verified, assessment)
            attached = cli("turn-assessment-import",
                payload={"assessment": assessment, **assessment_request})
            self.assertEqual(attached["record"]["assessment"], assessment)
            self.assertFalse(attached["record"]["acceptance_case_closed"])

            reconciled = cli("turn-reconcile", payload={"opening": opening, "report": report,
                "turn_record": record, "current_project_root": project["project_root"],
                "current_journal_head": opening["journal_head"]})
            self.assertEqual(reconciled["record"]["state"], "RECONCILED")
            cli_view = cli("turns", project["project_id"])
            self.assertEqual(cli_view["continuation"]["status"], "READY")
            self.assertEqual(cli_view["history"]["record_count"], 1)
            row = cli_view["history"]["records"][0]
            self.assertTrue(row["journal_committed"])
            self.assertEqual(row["turn_record_root"], record["turn_record_root"])
            self.assertEqual(row["projection"]["summary"], report["summary"])
            self.assertTrue(row["projection"]["lines"])
            self.assertFalse(row["projection"]["projection_is_evidence"])

            # The service invokes this read-only handler after authenticating
            # its transport. This exercises its data projection, not auth itself.
            hub = PippiHub(hub_path)
            service_view = dispatch_read(hub, {"command": "turns", "project_id": project["project_id"]})
            self.assertEqual(service_view, cli_view)
            self.assertEqual(hub.verify()["status"], "PASS")
            self.assertTrue(any(event["event_type"] == "TURN_ASSESSMENT_ATTACHED"
                                for event in hub._events()))
            self.assertEqual(list(start.iterdir()), [])


if __name__ == "__main__":
    unittest.main()

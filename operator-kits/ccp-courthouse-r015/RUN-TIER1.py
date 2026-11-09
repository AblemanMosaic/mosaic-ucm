#!/usr/bin/env python3
"""Builder-authored, operator-run Tier 1 court for the r015 CCP boundary.

The release builder may package and syntax-check this file.  It must not run
these cases.  The double-click launcher is the execution boundary.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile


FIXED_TIME = (1980, 1, 1, 0, 0, 0)
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def zip_bytes(payloads):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for name, raw in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw)
    return out.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    subject = args.subject.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(subject / "src"))
    sys.path.insert(0, str(subject))

    from uclop.canonical import Refusal, root, strict_loads
    from ucm.ccp_courthouse import (
        build_pippi_admission_status,
        validate_admissible_workflow_result,
        validate_admissible_workflow_submission,
        validate_courthouse_admission_envelope,
    )
    from tests.test_ccp_courthouse_positive import fixture, h
    from tests.test_courthouse_workflow import BOUNDARY as TEST_BOUNDARY, gate

    manifest = strict_loads((subject / "KIT-MANIFEST.json").read_bytes())
    cases = []

    def record(case_id, status, observed=None, expected=None):
        row = {"case_id": case_id, "status": status}
        if observed is not None:
            row["observed"] = observed
        if expected is not None:
            row["expected"] = expected
        cases.append(row)
        print(f"[case {len(cases):03d}] {case_id}: {status}", flush=True)
        print(f"[summary] completed={len(cases)} failed={sum(r['status'] != 'PASS' for r in cases)}",
              flush=True)

    def positive(case_id, function):
        try:
            function()
            record(case_id, "PASS")
        except Exception as exc:  # court evidence records the type, not local text
            record(case_id, "FAIL", type(exc).__name__, "PASS")

    def refused(case_id, expected, function):
        try:
            function()
            record(case_id, "FAIL", "ACCEPTED", expected)
        except Refusal as exc:
            observed = getattr(exc, "code", str(exc).split("@", 1)[0])
            record(case_id, "PASS" if observed == expected else "FAIL",
                   observed, expected)
        except Exception as exc:
            record(case_id, "FAIL", type(exc).__name__, expected)

    def reroot(value, field):
        body = {key: item for key, item in value.items() if key != field}
        return {**body, field: root(body)}

    def result_for(submission, *, evidence_roots=None):
        workflow = submission["compiled_workflow"]
        request = submission["workflow_request"]
        roots = (submission["required_g1_evidence_roots"]
                 if evidence_roots is None else evidence_roots)
        g1 = gate("G1_SENTINEL", workflow["workflow_root"], "GENESIS", [], roots)
        g2 = gate("G2_WITNESS", workflow["workflow_root"], g1["receipt_root"],
                  ["PROCESS", "WRITE_WORKSPACE"], [h("effect")])
        g3 = gate("G3_DIAGNOSTIC", workflow["workflow_root"], g2["receipt_root"],
                  ["PROCESS", "WRITE_WORKSPACE"], [h("diagnostic")])
        body = {
            "schema": "mosaic.ucm.aok-vnext-workflow-result.v0.1",
            "workflow_root": workflow["workflow_root"],
            "request_root": request["request_root"],
            "courthouse_identity_root": "4" * 64,
            "selected_realization_root": "5" * 64,
            "selected_executor_root": "6" * 64,
            "g1": g1, "g2": g2, "g3": g3,
            "obligation_dispositions": [
                {"obligation_id": "ARCHITECTURE_FIDELITY", "status": "PASS",
                 "evidence_roots": ["7" * 64]},
                {"obligation_id": "CROSS_PLATFORM_TESTS", "status": "PASS",
                 "evidence_roots": ["8" * 64]},
            ],
            "cm2_evaluated": True,
            "expected_journal_head": {"sequence": 0, "head": "GENESIS"},
            "successor_journal_head": {"sequence": 1, "head": "9" * 64},
            "terminal_status": "PASS", **TEST_BOUNDARY,
        }
        return {**body, "result_root": root(body)}

    # Exact kit custody.
    def manifest_control():
        rows = manifest["files"]
        manifest_body = {key: value for key, value in manifest.items()
                         if key != "manifest_root"}
        assert manifest["manifest_root"] == sha(canonical(manifest_body))
        assert all(manifest[key] == value for key, value in BOUNDARY.items())
        assert manifest["file_count"] == len(rows)
        assert manifest["tier1_executed"] is False
        assert manifest["builder_authored"] is True
        expected = {row["path"] for row in rows}
        actual = {
            path.relative_to(subject).as_posix() for path in subject.rglob("*")
            if path.is_file() and path.name != "KIT-MANIFEST.json"
        }
        assert actual == expected
        for row in rows:
            raw = (subject / row["path"]).read_bytes()
            assert len(raw) == row["bytes"] and sha(raw) == row["sha256"]

    positive("CONTROL-KIT-CLOSED-MANIFEST", manifest_control)
    positive("CONTROL-PROGRAM-REBUILD", lambda: subprocess.run([
        sys.executable, str(subject / "tools/build_ccp_courthouse_program.py"),
        "--check"], cwd=subject, check=True, capture_output=True))
    workflow_request, envelope, submission = fixture()
    positive("CONTROL-ADMISSION", lambda: validate_courthouse_admission_envelope(
        envelope, workflow_request))
    positive("CONTROL-SUBMISSION", lambda: validate_admissible_workflow_submission(
        submission))
    positive("CONTROL-STATUS", lambda: build_pippi_admission_status(
        submission=submission))
    exact_result = result_for(submission)
    positive("CONTROL-BOUND-G1-RESULT", lambda: validate_admissible_workflow_result(
        submission=submission, result=exact_result))

    changed = deepcopy(envelope); changed["subject_root"] = "f" * 64
    changed = reroot(changed, "admission_envelope_root")
    refused("ADMISSION-SUBJECT-SWAP", "CCP_COURTHOUSE_ADMISSION_INVALID",
            lambda: validate_courthouse_admission_envelope(changed, workflow_request))
    changed = deepcopy(envelope); changed["acceptance_case_root"] = "f" * 64
    changed = reroot(changed, "admission_envelope_root")
    refused("ADMISSION-CASE-SWAP", "CCP_COURTHOUSE_ADMISSION_INVALID",
            lambda: validate_courthouse_admission_envelope(changed, workflow_request))
    changed = deepcopy(envelope); changed["work_unit_root"] = "f" * 64
    changed = reroot(changed, "admission_envelope_root")
    refused("ADMISSION-WORK-UNIT-SWAP", "CCP_COURTHOUSE_ADMISSION_INVALID",
            lambda: validate_courthouse_admission_envelope(changed, workflow_request))
    changed = deepcopy(envelope)
    changed["records"]["decision"]["decision"] = "REFUSE"
    changed["records"]["decision"] = reroot(
        changed["records"]["decision"], "decision_root")
    changed = reroot(changed, "admission_envelope_root")
    refused("ADMISSION-DECISION-LAUNDERING", "CCP_DECISION_INVALID",
            lambda: validate_courthouse_admission_envelope(changed, workflow_request))
    changed = deepcopy(envelope)
    changed["records"]["current_use_snapshot"]["authenticated_epoch"] += 1
    changed["records"]["current_use_snapshot"] = reroot(
        changed["records"]["current_use_snapshot"], "current_use_snapshot_root")
    changed = reroot(changed, "admission_envelope_root")
    refused("ADMISSION-CURRENT-USE-SWAP", "CCP_DECISION_CURRENT_USE_ROOT_MISMATCH",
            lambda: validate_courthouse_admission_envelope(changed, workflow_request))
    changed = deepcopy(envelope)
    changed["records"]["enforcement_perimeter"]["qualification_status"] = "DECLARED_ONLY"
    changed["records"]["enforcement_perimeter"] = reroot(
        changed["records"]["enforcement_perimeter"], "enforcement_perimeter_root")
    changed = reroot(changed, "admission_envelope_root")
    refused("ADMISSION-PERIMETER-DOWNGRADE", "CCP_DECISION_PERIMETER_ROOT_MISMATCH",
            lambda: validate_courthouse_admission_envelope(changed, workflow_request))
    changed_request = deepcopy(workflow_request)
    changed_request["policy_pack_roots"] = ["f" * 64]
    changed_request = reroot(changed_request, "request_root")
    refused("REQUEST-POLICY-SWAP", "CCP_COURTHOUSE_POLICY_NOT_BOUND",
            lambda: validate_courthouse_admission_envelope(envelope, changed_request))

    changed = deepcopy(submission)
    changed["required_g1_evidence_roots"] = changed["required_g1_evidence_roots"][:-1]
    changed = reroot(changed, "submission_root")
    refused("SUBMISSION-G1-DENOMINATOR-SHRINK", "CCP_COURTHOUSE_SUBMISSION_INVALID",
            lambda: validate_admissible_workflow_submission(changed))
    changed = deepcopy(submission); changed["dispatch_status"] = "DISPATCHED"
    changed = reroot(changed, "submission_root")
    refused("SUBMISSION-DISPATCH-LAUNDERING", "CCP_COURTHOUSE_SUBMISSION_INVALID",
            lambda: validate_admissible_workflow_submission(changed))
    changed = deepcopy(submission); changed["effect_authorized"] = True
    changed = reroot(changed, "submission_root")
    refused("SUBMISSION-AUTHORITY-LAUNDERING", "CCP_COURTHOUSE_SUBMISSION_INVALID",
            lambda: validate_admissible_workflow_submission(changed))
    changed = deepcopy(submission)
    changed["courthouse_lattice_status"] = "INSTALLED"
    changed = reroot(changed, "submission_root")
    refused("SUBMISSION-LATTICE-OVERCLAIM", "CCP_COURTHOUSE_SUBMISSION_INVALID",
            lambda: validate_admissible_workflow_submission(changed))
    changed = deepcopy(submission)
    changed["admission_step"]["decision"] = "REFUSE"
    changed["admission_step"] = reroot(changed["admission_step"], "admission_step_root")
    changed = reroot(changed, "submission_root")
    refused("SUBMISSION-ADMISSION-STEP-SWAP", "CCP_COURTHOUSE_SUBMISSION_INVALID",
            lambda: validate_admissible_workflow_submission(changed))

    for index, required_root in enumerate(submission["required_g1_evidence_roots"], 1):
        roots = [value for value in submission["required_g1_evidence_roots"]
                 if value != required_root]
        refused(f"RESULT-G1-ROOT-{index}-MISSING",
                "CCP_COURTHOUSE_G1_ADMISSION_EVIDENCE_MISSING",
                lambda roots=roots: validate_admissible_workflow_result(
                    submission=submission, result=result_for(submission,
                                                             evidence_roots=roots)))

    failed = sum(row["status"] != "PASS" for row in cases)
    result_body = {
        "schema": "mosaic.ucm.ccp-courthouse-r015-tier1-result.v0.1",
        "cases": cases, "case_count": len(cases), "failed": failed,
        "status": "PASS" if failed == 0 else "HOLD_FOR_REPAIR",
        "kit_manifest_root": manifest["manifest_root"], **BOUNDARY,
    }
    result = {**result_body, "court_root": sha(canonical(result_body))}
    report = (
        "# CCP Courthouse r015 operator court\n\n"
        f"Status: {result['status']}\n\nCases: {len(cases)}\n\n"
        "Builder-authored, operator-executed evidence; not an independent verdict.\n"
    ).encode("utf-8")
    evidence = zip_bytes({
        "TIER1-RESULT.json": canonical(result) + b"\n",
        "REPORT.md": report,
        "RUN-TIER1.py": Path(__file__).read_bytes(),
    })
    evidence_name = f"UCM-CCP-COURTHOUSE-r015-TIER1-EVIDENCE-{result['court_root'][:16]}.zip"
    evidence_path = out / evidence_name
    evidence_path.write_bytes(evidence)
    print(json.dumps({"status": result["status"], "cases": len(cases),
                      "failed": failed, "court_root": result["court_root"],
                      "evidence": str(evidence_path),
                      "evidence_sha256": sha(evidence), **BOUNDARY},
                     sort_keys=True), flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

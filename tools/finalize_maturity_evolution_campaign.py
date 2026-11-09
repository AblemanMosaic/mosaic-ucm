"""Derive the public dogfood campaign from an exact frozen qualification.

The source campaign is intentionally frozen before qualification.  This tool
copies it into a disposable workspace, appends qualification and disposition
events there, and seals the result as a separate archive.  It never rewrites
the qualified source and therefore avoids a recursive source-root dependency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root, strict_loads  # noqa: E402
from ucm.artifacts import deterministic_zip, verify_deterministic_zip  # noqa: E402
from ucm.evidence_adapters import build_tool_evidence_subject  # noqa: E402
from ucm.journal import CampaignJournal  # noqa: E402


BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
PROGRAM = ROOT / "program" / "maturity-evolution"
ACTOR = {"kind": "SYSTEM", "mosaic_id": None, "session_id": None}

EVIDENCE_PATHS = {
    "AUTHORING": ["src/ucm/contract_workbench.py", "docs/CONTRACT-AUTHORING-PLAYBOOK.md"],
    "AGENT": ["src/ucm/agent_adapter.py", "docs/AGENT-ADAPTER-AND-LOOP.md"],
    "EXPLAIN": ["src/ucm/contract_workbench.py", "docs/ACTIVE-SURFACE-GUIDE.md"],
    "EVOLUTION": ["src/ucm/contract_workbench.py", "docs/STABILITY-PORTABILITY-AND-ROBUSTNESS.md"],
    "DOCS": ["docs/ACTIVE-SURFACE-GUIDE.md", "docs/OPERATOR-PLAYBOOK.md"],
    "EVIDENCE": ["src/ucm/evidence_adapters.py", "docs/EVIDENCE-INTEROPERABILITY.md"],
    "RECOVERY": ["docs/WORKSPACE-RECOVERY-AND-IDEMPOTENCY.md", "src/ucm/journal.py"],
    "ABI": ["spec/ABI-STABILITY.json", "src/ucm/governance.py"],
    "CANONICAL": ["conformance/CANONICAL-JSON-GOLDEN-VECTORS-v0.1.json", "conformance/README.md"],
    "WORKSPACE": ["docs/WORKSPACE-RECOVERY-AND-IDEMPOTENCY.md", "src/ucm/journal.py"],
    "TIME": ["spec/TIME-AND-FRESHNESS-POLICY.json", "src/ucm/governance.py"],
    "IDEMPOTENCY": ["docs/WORKSPACE-RECOVERY-AND-IDEMPOTENCY.md", "src/ucm/journal.py"],
    "BUDGET": ["docs/OPERATOR-PLAYBOOK.md", "src/ucm/operation_gateway.py"],
    "JOURNAL": ["src/ucm/journal_tools.py", "docs/OPERATOR-PLAYBOOK.md"],
    "ROBUSTNESS": ["fuzz/README.md", "fuzz/fuzz_contracts.py", "fuzz/fuzz_canonical.py"],
    "PERFORMANCE": ["docs/STABILITY-PORTABILITY-AND-ROBUSTNESS.md"],
    "POLICY": ["src/ucm/authoring.py", "policy-packs/NO_AUTHORITY-v0.1.json"],
    "PORTABILITY": ["conformance/CANONICAL-JSON-GOLDEN-VECTORS-v0.1.json", "docs/STABILITY-PORTABILITY-AND-ROBUSTNESS.md"],
    "CLI": ["src/ucm/cli.py", "src/ucm/governance.py", "completions/ucm.bash"],
    "PRESENTATION": ["src/ucm/presentation.py"],
    "DIFF": ["src/ucm/contract_workbench.py"],
    "APPROVAL": ["src/ucm/governance.py"],
    "STORAGE": ["src/ucm/journal.py"],
    "ENVIRONMENT": ["spec/ENVIRONMENT-POLICY.json", "src/ucm/governance.py"],
    "AUTHORITY": ["program/maturity-evolution/AMCAS-CONTRACT.json"],
    "THR": ["program/maturity-evolution/THR-MANIFEST.json"],
    "CM1": ["program/maturity-evolution/AMCAS-CONTRACT.json"],
    "CM2": ["program/maturity-evolution/REALIZATION-CONTRACT.json"],
    "TEST": ["tests/test_maturity_evolution.py", "tools/run_maturity_qualification.py"],
    "REVIEW": ["tools/build_maturity_operator_kit.py", "review/JOINT-MATURITY-INDEPENDENT-REVIEW-WORK-ORDER.md"],
    "PACKAGE": ["tools/build_maturity_release.py", "tools/maturity_release_common.py"],
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")


def _source_files(qualification: dict) -> dict[str, dict]:
    return {row["path"]: row for row in qualification["source"]["files"]}


def build(qualification_dir: Path, output: Path) -> dict:
    qualification = strict_loads((qualification_dir / "QUALIFICATION.json").read_bytes())
    if (qualification.get("status") != "PASS" or qualification.get("failures") != 0
            or qualification.get("errors") != 0 or qualification.get("skips") != 0):
        raise SystemExit("UCM_DOGFOOD_QUALIFICATION_INVALID")
    source_files = _source_files(qualification)
    intake = strict_loads((PROGRAM / "FEEDBACK-INTAKE.json").read_bytes())
    runner_raw = (ROOT / "tools" / "run_maturity_qualification.py").read_bytes()
    invocation = {"runner_sha256": sha(runner_raw), "cache_policy": "DISABLED",
                  "test_set_root": qualification["test_set_root"]}
    environment = {"python_range": ">=3.12,<3.14",
                   "dependency_policy": "DECLARED_IN_PYPROJECT"}
    evidence = build_tool_evidence_subject(
        tool="UNITTEST", subject_root=qualification["source"]["source_root"],
        invocation_root=root(invocation), output_root=qualification["qualification_root"],
        environment_root=root(environment), verifier_root=sha(runner_raw),
        policy_root=intake["intake_root"], issuer_root=root({"issuer": "UCM_BUILDER"}),
        exit_code=0, counts={"tests": qualification["test_count"], "failures": 0,
                             "errors": 0, "skips": 0}, issued_at=0, not_after=None)

    rows = []
    for requirement in intake["requirements"]:
        paths = EVIDENCE_PATHS.get(requirement["area"], [])
        missing = [path for path in paths if path not in source_files]
        if missing:
            raise SystemExit("UCM_DOGFOOD_EVIDENCE_PATH_MISSING:" + ",".join(missing))
        status = "PASS_IMPLEMENTED_PENDING_OPERATOR_REVIEW"
        if requirement["id"] == "MR-036":
            status = "PREPARED_NOT_EXECUTED_BY_BUILDER"
        elif requirement["id"] == "MR-047":
            status = "POSITIVE_PORTABILITY_READY_PENDING_CI_MATRIX"
        elif requirement["id"] == "MR-054":
            status = "PASS_ADVERSARIAL_EXECUTION_SEPARATED"
        rows.append({
            "requirement_id": requirement["id"], "area": requirement["area"],
            "cm": requirement["cm"], "status": status,
            "evidence": [{"path": path, "sha256": source_files[path]["sha256"]}
                         for path in paths],
            "qualification_evidence_root": evidence["evidence_subject_root"],
        })
    disposition_body = {
        "schema": "mosaic.ucm.maturity-requirement-disposition.v0.1",
        "feedback_intake_root": intake["intake_root"],
        "qualification_root": qualification["qualification_root"],
        "fixed_denominator": intake["fixed_denominator"],
        "requirements": rows,
        "operator_tier1_status": "SEPARATE_USER_RUN_REQUIRED",
        "independent_review_status": "PENDING",
        **BOUNDARY,
    }
    disposition = {**disposition_body, "disposition_root": root(disposition_body)}

    temporary = Path(tempfile.mkdtemp(prefix="ucm-self-release-campaign-"))
    try:
        campaign = temporary / "campaign"
        shutil.copytree(PROGRAM, campaign)
        journal = CampaignJournal(campaign / "journal")
        journal.verify_read_only()
        journal.append(event_id="maturity-evolution:qualification",
                       event_type="TEST_RECORDED", actor=ACTOR,
                       payload={"qualification_root": qualification["qualification_root"],
                                "evidence_subject_root": evidence["evidence_subject_root"],
                                "test_count": qualification["test_count"], "status": "PASS"})
        for row in rows:
            journal.append(event_id="maturity-evolution:disposition:" + row["requirement_id"],
                           event_type="REQUIREMENT_DISPOSITIONED", actor=ACTOR,
                           payload={"requirement_id": row["requirement_id"],
                                    "status": row["status"],
                                    "disposition_root": disposition["disposition_root"]})
        write(campaign / "QUALIFICATION-EVIDENCE.json", evidence)
        write(campaign / "REQUIREMENT-DISPOSITION.json", disposition)
        checkpoint = journal.checkpoint()
        journal.append(event_id="maturity-evolution:checkpoint",
                       event_type="CHECKPOINT_CREATED", actor=ACTOR,
                       payload={"checkpoint_root": checkpoint["checkpoint_root"],
                                "qualification_root": qualification["qualification_root"]})
        final_checkpoint = journal.checkpoint()
        write(campaign / "CHECKPOINT.json", final_checkpoint)
        summary_body = {
            "schema": "mosaic.ucm.self-release-campaign-summary.v0.1",
            "campaign": "UCM_MATURITY_EVOLUTION_C1",
            "source_root": qualification["source"]["source_root"],
            "qualification_root": qualification["qualification_root"],
            "qualification_evidence_root": evidence["evidence_subject_root"],
            "requirement_disposition_root": disposition["disposition_root"],
            "journal_head_root": final_checkpoint["head"]["root"],
            "fixed_denominator": intake["fixed_denominator"],
            "operator_tier1_status": "SEPARATE_USER_RUN_REQUIRED",
            "independent_review_status": "PENDING",
            "status": "PASS_BUILDER_QUALIFIED_PENDING_REVIEW",
            **BOUNDARY,
        }
        summary = {**summary_body, "summary_root": root(summary_body)}
        write(campaign / "CAMPAIGN-SUMMARY.json", summary)
        payloads = {path.relative_to(campaign).as_posix(): path.read_bytes()
                    for path in campaign.rglob("*") if path.is_file()}
        first = deterministic_zip(payloads,
            schema="mosaic.ucm.self-release-campaign.v0.1",
            artifact_role="UCM_SELF_RELEASE_CAMPAIGN")
        second = deterministic_zip(payloads,
            schema="mosaic.ucm.self-release-campaign.v0.1",
            artifact_role="UCM_SELF_RELEASE_CAMPAIGN")
        if first != second:
            raise SystemExit("UCM_DOGFOOD_CAMPAIGN_NONDETERMINISTIC")
        manifest = verify_deterministic_zip(first,
            expected_schema="mosaic.ucm.self-release-campaign.v0.1",
            expected_role="UCM_SELF_RELEASE_CAMPAIGN")
        output.mkdir(parents=True, exist_ok=True)
        if any(output.iterdir()):
            raise SystemExit("UCM_DOGFOOD_OUTPUT_NOT_EMPTY")
        (output / "UCM-SELF-RELEASE-CAMPAIGN.zip").write_bytes(first)
        write(output / "CAMPAIGN-SUMMARY.json", summary)
        return {"status": "PASS", "campaign_sha256": sha(first),
                "campaign_manifest_root": manifest["manifest_root"],
                "summary_root": summary["summary_root"], **BOUNDARY}
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.qualification_dir.resolve(), args.output.resolve()),
                     sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Freeze the qualified UCM maturity successor and joint review handoff."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root
from ucm.artifacts import deterministic_zip, verify_deterministic_zip


BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
HISTORICAL_STAGE_I3_PIPELINE_SHA256 = (
    "3c549fbcab17aefd5ade76497593b76a25e48c88f1fe28da3fea44ecb73926bc")
HISTORICAL_STAGE_I3_PIPELINE_PATH = (
    ROOT / "review" / "unified-maturity" / "track-b" /
    "HISTORICAL-STAGE-I3-PIPELINE-RELEASE-3c549fbc.zip")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def artifact(role: str, raw: bytes) -> dict:
    return {"role": role, "sha256": sha(raw), "bytes": len(raw)}


def write_new(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)


def build(qualification_dir: Path, operator_dir: Path, campaign_dir: Path,
          output: Path) -> dict:
    qualification_raw = (qualification_dir / "QUALIFICATION.json").read_bytes()
    qualification = json.loads(qualification_raw)
    if (qualification.get("status") != "PASS" or qualification.get("failures") != 0
            or qualification.get("errors") != 0 or qualification.get("skips") != 0):
        raise SystemExit("MATURITY_RELEASE_QUALIFICATION_INVALID")
    files = {
        "CANONICAL-SOFTWARE.zip": (qualification_dir / "CANONICAL-SOFTWARE.zip").read_bytes(),
        "QUALIFICATION-SOURCE.zip": (qualification_dir / "QUALIFICATION-SOURCE.zip").read_bytes(),
        "AUTHORING-PROFILE-OVERLAY.zip": (qualification_dir / "AUTHORING-PROFILE-OVERLAY.zip").read_bytes(),
        "COMPATIBILITY-PROFILE-OVERLAY.zip": (qualification_dir / "COMPATIBILITY-PROFILE-OVERLAY.zip").read_bytes(),
        "OPERATIONAL-PROFILE-OVERLAY.zip": (qualification_dir / "OPERATIONAL-PROFILE-OVERLAY.zip").read_bytes(),
        "VERIFY-ONLY-PROFILE-OVERLAY.zip": (qualification_dir / "VERIFY_ONLY-PROFILE-OVERLAY.zip").read_bytes(),
        "TIER1-OPERATOR-KIT.zip": (operator_dir / "UCM-MATURITY-TIER1-OPERATOR-KIT.zip").read_bytes(),
        "SELF-RELEASE-CAMPAIGN.zip": (campaign_dir / "UCM-SELF-RELEASE-CAMPAIGN.zip").read_bytes(),
    }
    anchors = {
        "CANONICAL-SOFTWARE.zip": qualification["runtime_anchor"]["archive_sha256"],
        "QUALIFICATION-SOURCE.zip": qualification["qualification_source_anchor"]["archive_sha256"],
        "AUTHORING-PROFILE-OVERLAY.zip": qualification["profile_anchors"]["AUTHORING"]["archive_sha256"],
        "COMPATIBILITY-PROFILE-OVERLAY.zip": qualification["profile_anchors"]["COMPATIBILITY"]["archive_sha256"],
        "OPERATIONAL-PROFILE-OVERLAY.zip": qualification["profile_anchors"]["OPERATIONAL"]["archive_sha256"],
        "VERIFY-ONLY-PROFILE-OVERLAY.zip": qualification["profile_anchors"]["VERIFY_ONLY"]["archive_sha256"],
    }
    for name, expected in anchors.items():
        if sha(files[name]) != expected:
            raise SystemExit("MATURITY_RELEASE_ARTIFACT_PIN_MISMATCH:" + name)
    operator_manifest = verify_deterministic_zip(files["TIER1-OPERATOR-KIT.zip"],
        expected_schema="mosaic.ucm.maturity-tier1-operator-kit.v0.2",
        expected_role="UCM_MATURITY_TIER1_OPERATOR_KIT")
    campaign_manifest = verify_deterministic_zip(files["SELF-RELEASE-CAMPAIGN.zip"],
        expected_schema="mosaic.ucm.self-release-campaign.v0.1",
        expected_role="UCM_SELF_RELEASE_CAMPAIGN")
    campaign_summary_raw = (campaign_dir / "CAMPAIGN-SUMMARY.json").read_bytes()
    campaign_summary = json.loads(campaign_summary_raw)
    if (campaign_summary.get("qualification_root") != qualification["qualification_root"]
            or campaign_summary.get("status") != "PASS_BUILDER_QUALIFIED_PENDING_REVIEW"):
        raise SystemExit("MATURITY_RELEASE_DOGFOOD_CAMPAIGN_INVALID")
    historical_pipeline = HISTORICAL_STAGE_I3_PIPELINE_PATH.read_bytes()
    if sha(historical_pipeline) != HISTORICAL_STAGE_I3_PIPELINE_SHA256:
        raise SystemExit("MATURITY_RELEASE_HISTORICAL_PIPELINE_PIN_MISMATCH")
    verify_deterministic_zip(
        historical_pipeline,
        expected_schema="mosaic.ucm.amcas-integration-pipeline-release.v0.1",
        expected_role="UCM_AMCAS_INTEGRATION_PIPELINE")
    current = json.loads((ROOT / "integration/ECOSYSTEM-INTEGRATION-CURRENT-STATE.json").read_text(encoding="utf-8"))
    repairs = json.loads((ROOT / "integration/ECOSYSTEM-REPAIR-RETURN-REGISTER.json").read_text(encoding="utf-8"))
    if (current.get("repair_overlay_count") != repairs.get("repair_return_count")
            or current.get("repair_return_register_root") != repairs.get("repair_register_root")
            or current.get("application_execution_authorized") is not False
            or repairs.get("application_execution_authorized") is not False):
        raise SystemExit("MATURITY_RELEASE_ECOSYSTEM_REPAIR_STATE_INVALID")
    freeze_body = {"schema": "mosaic.ucm.maturity-freeze-receipt.v0.2",
                   "qualification_root": qualification["qualification_root"],
                   "source_root": qualification["source"]["source_root"],
                   "ecosystem_current_state_root": current["current_state_root"],
                   "ecosystem_repair_register_root": repairs["repair_register_root"],
                   "artifacts": [artifact(name.removesuffix(".zip"), raw)
                                 for name, raw in sorted(files.items())],
                   "operator_court_status": "READY_NOT_EXECUTED_BY_BUILDER",
                   "independent_review_status": "PENDING_AFTER_BUILDER_REPAIR",
                   "tracks": {
                       "UCM_PRODUCT_MATURITY": "REPAIRED_AND_POSITIVE_STATIC_QUALIFIED_PENDING_INDEPENDENT_TIER1",
                       "MOSAIC_ECOSYSTEM_INTEGRATION": "SEVEN_OF_SEVEN_STATIC_RECONCILED_HISTORICAL_GENERATOR_CARRIED_EXACT_EXTERNAL_HOLDS_PRESERVED_NO_EXECUTION",
                       "EMPIRICAL_ARCHITECTURE_PROOF": "CONTEXT_AND_FOLLOW_ON_BOUND_PROTOCOL_READY_NOT_EXECUTED",
                   }, **BOUNDARY}
    freeze = {**freeze_body, "freeze_root": root(freeze_body)}
    payloads = {
        **files,
        "QUALIFICATION.json": qualification_raw,
        "FREEZE-RECEIPT.json": canonical_bytes(freeze),
        "SELF-RELEASE-CAMPAIGN-SUMMARY.json": campaign_summary_raw,
        "UNIFIED-MATURITY-PROGRAM.json": (ROOT / "program/UNIFIED-MATURITY-PROGRAM.json").read_bytes(),
        "CONSOLIDATED-HARDENING-CAMPAIGN.json": (ROOT / "program/CONSOLIDATED-HARDENING-CAMPAIGN.json").read_bytes(),
        "ECOSYSTEM-INTEGRATION-BASELINE.json": (ROOT / "integration/ECOSYSTEM-INTEGRATION-BASELINE.json").read_bytes(),
        "ECOSYSTEM-SESSION-DISPATCH.json": (
            ROOT / "integration/ECOSYSTEM-SESSION-DISPATCH.json").read_bytes(),
        "ECOSYSTEM-SESSION-RETURN-INDEX.json": (
            ROOT / "integration/ECOSYSTEM-SESSION-RETURN-INDEX.json").read_bytes(),
        "ECOSYSTEM-INTEGRATION-OUTCOME-REGISTER.json": (
            ROOT / "integration/ECOSYSTEM-INTEGRATION-OUTCOME-REGISTER.json").read_bytes(),
        "ECOSYSTEM-NEXT-WORK-PROGRAM.json": (
            ROOT / "integration/ECOSYSTEM-NEXT-WORK-PROGRAM.json").read_bytes(),
        "ECOSYSTEM-NEXT-WORK-DISPATCH.json": (
            ROOT / "integration/ECOSYSTEM-NEXT-WORK-DISPATCH.json").read_bytes(),
        "ECOSYSTEM-SUCCESSOR-RETURN-INDEX.json": (
            ROOT / "integration/ECOSYSTEM-SUCCESSOR-RETURN-INDEX.json").read_bytes(),
        "ECOSYSTEM-SUCCESSOR-OUTCOME-REGISTER.json": (
            ROOT / "integration/ECOSYSTEM-SUCCESSOR-OUTCOME-REGISTER.json").read_bytes(),
        "ECOSYSTEM-AUDIT-RETURN-REGISTER.json": (
            ROOT / "integration/ECOSYSTEM-AUDIT-RETURN-REGISTER.json").read_bytes(),
        "ECOSYSTEM-REPAIR-RETURN-REGISTER.json": (
            ROOT / "integration/ECOSYSTEM-REPAIR-RETURN-REGISTER.json").read_bytes(),
        "ECOSYSTEM-INTEGRATION-CURRENT-STATE.json": (
            ROOT / "integration/ECOSYSTEM-INTEGRATION-CURRENT-STATE.json").read_bytes(),
        "ECOSYSTEM-AUDIT-REPAIR-PROGRAM.json": (
            ROOT / "integration/ECOSYSTEM-AUDIT-REPAIR-PROGRAM.json").read_bytes(),
        "ECOSYSTEM-STAGE-I3-REBIND-RECONCILIATION.json": (
            ROOT / "integration/stage-i3/STAGE-I3-REBIND-RECONCILIATION.json").read_bytes(),
        "PIPELINE-BOUND-REBIND-PROVENANCE.json": (
            ROOT / "integration/stage-i3/PIPELINE-BOUND-REBIND-PROVENANCE.json").read_bytes(),
        "HISTORICAL-STAGE-I3-PIPELINE-RELEASE-3c549fbc.zip": historical_pipeline,
        "ARCHITECTURE-COMPLIANCE-STUDY.json": (ROOT / "evaluation/ARCHITECTURE-COMPLIANCE-STUDY.json").read_bytes(),
        "ARCHITECTURE-STUDY-EXECUTION-CONTEXT-TEMPLATE.json": (
            ROOT / "evaluation/EXECUTION-CONTEXT.template.json").read_bytes(),
        "ARCHITECTURE-STUDY-FOLLOW-ON-TASK.md": (
            ROOT / "evaluation/tasks/reference-data-client/FOLLOW-ON-TASK.md").read_bytes(),
        "TRACK-A-REVIEW-REGISTER.json": (
            ROOT / "review/unified-maturity/track-a/REVIEW-REGISTER.json").read_bytes(),
        "TRACK-A-REPAIR-DISPOSITION.json": (
            ROOT / "review/unified-maturity/track-a/REPAIR-DISPOSITION.json").read_bytes(),
        "REVIEW-WORK-ORDER.md": (ROOT / "review/JOINT-MATURITY-INDEPENDENT-REVIEW-WORK-ORDER.md").read_bytes(),
        "VERIFY.py": (ROOT / "VERIFY.py").read_bytes(),
        "STAGE.py": (ROOT / "STAGE.py").read_bytes(),
    }
    handoff = deterministic_zip(payloads,
        schema="mosaic.ucm.maturity-independent-review-handoff.v0.1",
        artifact_role="UCM_MATURITY_INDEPENDENT_REVIEW_HANDOFF")
    verify_deterministic_zip(handoff,
        expected_schema="mosaic.ucm.maturity-independent-review-handoff.v0.1",
        expected_role="UCM_MATURITY_INDEPENDENT_REVIEW_HANDOFF")
    output.mkdir(parents=True, exist_ok=True)
    deliverables = {
        "MOSAIC-UCM-MATURITY-CANONICAL-SOFTWARE-v0.1.zip": files["CANONICAL-SOFTWARE.zip"],
        "MOSAIC-UCM-MATURITY-QUALIFICATION-SOURCE-v0.1.zip": files["QUALIFICATION-SOURCE.zip"],
        "MOSAIC-UCM-MATURITY-AUTHORING-PROFILE-v0.1.zip": files["AUTHORING-PROFILE-OVERLAY.zip"],
        "MOSAIC-UCM-MATURITY-COMPATIBILITY-PROFILE-v0.1.zip": files["COMPATIBILITY-PROFILE-OVERLAY.zip"],
        "MOSAIC-UCM-MATURITY-OPERATIONAL-PROFILE-v0.1.zip": files["OPERATIONAL-PROFILE-OVERLAY.zip"],
        "MOSAIC-UCM-MATURITY-VERIFY-ONLY-PROFILE-v0.1.zip": files["VERIFY-ONLY-PROFILE-OVERLAY.zip"],
        "MOSAIC-UCM-v0.1-INDEPENDENT-REVIEW-HANDOFF.zip": handoff,
        "MOSAIC-UCM-v0.1-SELF-RELEASE-CAMPAIGN.zip": files["SELF-RELEASE-CAMPAIGN.zip"],
        "SELF-RELEASE-CAMPAIGN-SUMMARY.json": campaign_summary_raw,
        "FREEZE-RECEIPT.json": canonical_bytes(freeze),
        "REVIEW-WORK-ORDER.md": payloads["REVIEW-WORK-ORDER.md"],
    }
    if any(output.iterdir()):
        raise SystemExit("MATURITY_RELEASE_OUTPUT_NOT_EMPTY")
    for name, raw in deliverables.items():
        write_new(output / name, raw)
    return {"status": "PASS", "freeze_root": freeze["freeze_root"],
            "handoff_sha256": sha(handoff),
            "operator_kit_manifest_root": operator_manifest["manifest_root"],
            "self_release_campaign_manifest_root": campaign_manifest["manifest_root"],
            "deliverables": {name: artifact(name, raw)
                             for name, raw in sorted(deliverables.items())}, **BOUNDARY}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification-dir", type=Path, required=True)
    parser.add_argument("--operator-dir", type=Path, required=True)
    parser.add_argument("--campaign-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    first = Path(tempfile.mkdtemp(prefix="ucm-maturity-release-a-"))
    second = Path(tempfile.mkdtemp(prefix="ucm-maturity-release-b-"))
    try:
        result_a = build(args.qualification_dir.resolve(), args.operator_dir.resolve(),
                         args.campaign_dir.resolve(), first)
        result_b = build(args.qualification_dir.resolve(), args.operator_dir.resolve(),
                         args.campaign_dir.resolve(), second)
        bytes_a = {path.relative_to(first).as_posix(): path.read_bytes()
                   for path in first.rglob("*") if path.is_file()}
        bytes_b = {path.relative_to(second).as_posix(): path.read_bytes()
                   for path in second.rglob("*") if path.is_file()}
        if result_a != result_b or bytes_a != bytes_b:
            raise SystemExit("MATURITY_RELEASE_NONDETERMINISTIC")
        output = args.output.resolve()
        if output.exists() and any(output.iterdir()):
            raise SystemExit("MATURITY_RELEASE_OUTPUT_NOT_EMPTY")
        output.mkdir(parents=True, exist_ok=True)
        for name, raw in bytes_a.items():
            write_new(output / name, raw)
        print(json.dumps(result_a, sort_keys=True, separators=(",", ":")))
        return 0
    finally:
        shutil.rmtree(first, ignore_errors=True); shutil.rmtree(second, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())

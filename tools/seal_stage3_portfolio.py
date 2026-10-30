"""Seal a fixed-denominator Stage I3 planning checkpoint."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, require, root, strict_loads
from ucm.amcas import BOUNDARY
from ucm.artifacts import deterministic_zip, verify_deterministic_zip
from ucm.portfolio import PortfolioCampaign


SCHEMA = "mosaic.ucm.amcas-integration-portfolio-snapshot.v0.5"
ROLE = "PORTABLE_CANONICAL_INTEGRATION_PORTFOLIO"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else canonical_bytes(value))


def build(portfolio: Path, *, predecessor_snapshot: Path, predecessor_sha256: str,
          pipeline_release_sha256: str) -> tuple[bytes, dict]:
    require(len(predecessor_sha256) == 64 and len(pipeline_release_sha256) == 64,
            "STAGE_I3_SEAL_PIN_INVALID")
    predecessor_raw = predecessor_snapshot.read_bytes()
    require(sha(predecessor_raw) == predecessor_sha256,
            "STAGE_I3_PREDECESSOR_SNAPSHOT_INVALID")
    predecessor_stage2 = {}
    with zipfile.ZipFile(predecessor_snapshot) as archive:
        for name in archive.namelist():
            if name.startswith("stage-i2/responses/") and name.endswith(".json"):
                raw = archive.read(name); value = strict_loads(raw)
                predecessor_stage2[value["application_id"]] = raw
    current_stage2 = {}
    for path in (portfolio / "stage-i2" / "responses").glob("*.json"):
        raw = path.read_bytes(); value = strict_loads(raw)
        current_stage2[value["application_id"]] = (path, raw)
    campaign = PortfolioCampaign(portfolio / "campaign")
    status = campaign.status()
    require(status["fixed_workflow_denominator"] == 7
            and status["stage_i3_instruction_denominator_complete"] is True
            and status["stage_i3_plan_denominator_complete"] is True
            and status["ready_for_stage_i3_shadow_review"] is True
            and status["stage_i3_shadow_authorized"] is False
            and status["composition_authorized"] is False,
            "STAGE_I3_PORTFOLIO_INCOMPLETE")
    inventory_rows = []
    reconciliation_rows = []
    for row in status["applications"]:
        application_id = row["application_id"]
        stem = application_id.replace(".", "-")
        instruction_path = portfolio / "stage-i3" / "instructions" / (
            stem + "-STAGE-I3-INSTRUCTION.json")
        response_path = portfolio / "stage-i3" / "responses" / (
            stem + "-STAGE-I3-PLAN.json")
        require(instruction_path.is_file() and response_path.is_file(),
                "STAGE_I3_PORTABLE_FILE_MISSING")
        instruction_raw = instruction_path.read_bytes(); response_raw = response_path.read_bytes()
        require(sha(instruction_raw) == row["stage_i3_instruction_sha256"]
                and sha(response_raw) == row["stage_i3_plan_sha256"],
                "STAGE_I3_PORTABLE_FILE_DRIFT")
        instruction = strict_loads(instruction_raw); plan = strict_loads(response_raw)
        require(instruction["pipeline_release_sha256"] == pipeline_release_sha256
                and instruction["predecessor_portfolio_sha256"] == predecessor_sha256,
                "STAGE_I3_PORTABLE_LINEAGE_INVALID")
        require(application_id in current_stage2,
                "STAGE_I3_STAGE_I2_POINTER_MISSING")
        stage2_response, stage2_raw = current_stage2[application_id]
        require(stage2_response.is_file()
                and sha(stage2_raw) == row["stage_i2_artifact_sha256"],
                "STAGE_I3_STAGE_I2_POINTER_STALE")
        require(application_id in predecessor_stage2,
                "STAGE_I3_PREDECESSOR_STAGE_I2_MISSING")
        predecessor_stage2_sha = sha(predecessor_stage2[application_id])
        current_stage2_sha = sha(stage2_raw)
        reconciliation_rows.append({
            "application_id": application_id,
            "predecessor_stage_i2_sha256": predecessor_stage2_sha,
            "current_stage_i2_sha256": current_stage2_sha,
            "pointer_advanced": predecessor_stage2_sha != current_stage2_sha,
            "current_revision": row["stage_i2_revision"],
            "current_cas_status": row["stage_i2_cas"],
        })
        inventory_rows.append({
            "application_id": application_id,
            "instruction_sha256": row["stage_i3_instruction_sha256"],
            "instruction_root": instruction["instruction_root"],
            "plan_sha256": row["stage_i3_plan_sha256"],
            "plan_root": plan["plan_root"], "plan_status": plan["plan_status"],
            "capability_projection_count": len(plan["capability_projections"]),
            "correspondence_case_count": len(plan["correspondence_cases"]),
            "matched_relation_count": len(instruction["matched_relations"]),
            "hold_count": len(plan["holds"]),
            "execution_authorized": False, "composition_authorized": False,
        })
    inventory_body = {
        "schema": "mosaic.ucm.stage-i3-plan-inventory.v0.1",
        "fixed_workflow_denominator": 7, "applications": inventory_rows,
        "pipeline_release_sha256": pipeline_release_sha256,
        "predecessor_snapshot_sha256": predecessor_sha256,
        "ready_for_stage_i3_shadow_review": True,
        "stage_i3_shadow_authorized": False, "composition_authorized": False,
        **BOUNDARY,
    }
    inventory = {**inventory_body, "inventory_root": root(inventory_body)}
    write(portfolio / "stage-i3" / "evidence" / "STAGE-I3-PLAN-INVENTORY.json",
          inventory)
    reconciliation_body = {
        "schema": "mosaic.ucm.stage-i2-pointer-reconciliation.v0.1",
        "predecessor_snapshot_sha256": predecessor_sha256,
        "fixed_workflow_denominator": 7,
        "rows": sorted(reconciliation_rows, key=lambda item: item["application_id"]),
        "advanced_pointer_count": sum(row["pointer_advanced"] for row in reconciliation_rows),
        "all_current_pointers_cas_verified": all(
            row["current_cas_status"] == "STORED_VERIFIED" for row in reconciliation_rows),
        **BOUNDARY,
    }
    reconciliation = {**reconciliation_body,
        "reconciliation_root": root(reconciliation_body)}
    write(portfolio / "stage-i3" / "evidence" /
          "STAGE-I2-POINTER-RECONCILIATION.json", reconciliation)
    write(portfolio / "PORTFOLIO-STATUS.json", status)
    payloads = {}
    for path in sorted(portfolio.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(portfolio).as_posix()
        if relative.startswith("returns/") or relative.startswith("predecessor/"):
            continue
        if relative.endswith("-SNAPSHOT.zip") or relative.endswith("-SNAPSHOT-RECEIPT.json"):
            continue
        payloads[relative] = path.read_bytes()
    raw = deterministic_zip(payloads, schema=SCHEMA, artifact_role=ROLE)
    manifest = verify_deterministic_zip(raw, expected_schema=SCHEMA, expected_role=ROLE)
    receipt_body = {
        "schema": "mosaic.ucm.amcas-integration-portfolio-snapshot-receipt.v0.5",
        "snapshot_sha256": sha(raw), "snapshot_bytes": len(raw),
        "snapshot_manifest_root": manifest["manifest_root"],
        "portfolio_status_root": status["status_root"],
        "journal_head": status["journal_head"]["head"],
        "stage_i3_inventory_root": inventory["inventory_root"],
        "stage_i2_pointer_reconciliation_root": reconciliation["reconciliation_root"],
        "pipeline_release_sha256": pipeline_release_sha256,
        "predecessor_snapshot_sha256": predecessor_sha256,
        "ready_for_stage_i3_shadow_review": True,
        "stage_i3_shadow_authorized": False, "composition_authorized": False,
        **BOUNDARY,
    }
    return raw, {**receipt_body, "receipt_root": root(receipt_body)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("portfolio", type=Path)
    parser.add_argument("--predecessor-snapshot", type=Path, required=True)
    parser.add_argument("--predecessor-sha256", required=True)
    parser.add_argument("--pipeline-release-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    raw_a, receipt_a = build(args.portfolio.resolve(),
        predecessor_snapshot=args.predecessor_snapshot.resolve(),
        predecessor_sha256=args.predecessor_sha256,
        pipeline_release_sha256=args.pipeline_release_sha256)
    raw_b, receipt_b = build(args.portfolio.resolve(),
        predecessor_snapshot=args.predecessor_snapshot.resolve(),
        predecessor_sha256=args.predecessor_sha256,
        pipeline_release_sha256=args.pipeline_release_sha256)
    require(raw_a == raw_b and receipt_a == receipt_b,
            "STAGE_I3_PORTFOLIO_NONDETERMINISTIC")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    require(not args.out.exists(), "STAGE_I3_PORTFOLIO_OUTPUT_EXISTS")
    args.out.write_bytes(raw_a)
    receipt_path = args.out.with_name(args.out.stem + "-RECEIPT.json")
    require(not receipt_path.exists(), "STAGE_I3_PORTFOLIO_RECEIPT_EXISTS")
    receipt_path.write_bytes(canonical_bytes(receipt_a))
    print(json.dumps({"status": "PASS", "snapshot": str(args.out),
        "snapshot_sha256": sha(raw_a), "receipt": str(receipt_path),
        "stage_i3_inventory_root": receipt_a["stage_i3_inventory_root"],
        **BOUNDARY}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

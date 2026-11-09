"""Seal the post-court portfolio checkpoint without embedding predecessor archives."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, require, root
from ucm.amcas import BOUNDARY
from ucm.artifacts import deterministic_zip, verify_deterministic_zip
from ucm.portfolio import PortfolioCampaign, COURT_EVIDENCE_ROLE, COURT_EVIDENCE_SCHEMA


SCHEMA = "mosaic.ucm.amcas-integration-portfolio-snapshot.v0.4"
ROLE = "PORTABLE_CANONICAL_INTEGRATION_PORTFOLIO"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = value if isinstance(value, bytes) else canonical_bytes(value)
    path.write_bytes(raw)


def build(portfolio: Path, court_evidence: bytes, predecessor_sha256: str) -> tuple[bytes, dict]:
    require(len(predecessor_sha256) == 64, "PIPELINE_PREDECESSOR_HASH_INVALID")
    verify_deterministic_zip(court_evidence, expected_schema=COURT_EVIDENCE_SCHEMA,
                             expected_role=COURT_EVIDENCE_ROLE)
    campaign = PortfolioCampaign(portfolio / "campaign")
    status = campaign.status()
    require(status["correspondence_court"] == "IMPORTED"
            and status["correspondence_court_cas"] == "STORED_VERIFIED"
            and status["correspondence_court_artifact_sha256"] == sha(court_evidence)
            and status["ready_for_stage_i3_shadow_planning"] is True
            and status["stage_i3_shadow_authorized"] is False
            and status["composition_authorized"] is False,
            "PIPELINE_PORTFOLIO_COURT_STATE_INVALID")
    write(portfolio / "PORTFOLIO-STATUS.json", status)
    import_body = {
        "schema": "mosaic.ucm.correspondence-court-import.v0.1",
        "claim": status["correspondence_court_claim"],
        "evidence_sha256": status["correspondence_court_artifact_sha256"],
        "court_root": status["correspondence_court_root"],
        "portfolio_status_root": status["status_root"],
        "journal_head": status["journal_head"]["head"],
        "predecessor_snapshot_sha256": predecessor_sha256,
        "independent_reviewer_authored": False,
        "stage_i3_shadow_authorized": False,
        "composition_authorized": False,
        **BOUNDARY,
    }
    imported = {**import_body, "import_root": root(import_body)}
    write(portfolio / "evidence" / "CORRESPONDENCE-COURT-IMPORT.json", imported)

    payloads: dict[str, bytes] = {}
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
        "schema": "mosaic.ucm.amcas-integration-portfolio-snapshot-receipt.v0.4",
        "snapshot_sha256": sha(raw), "snapshot_bytes": len(raw),
        "snapshot_manifest_root": manifest["manifest_root"],
        "portfolio_status_root": status["status_root"],
        "journal_head": status["journal_head"]["head"],
        "correspondence_court_evidence_sha256": sha(court_evidence),
        "correspondence_court_root": status["correspondence_court_root"],
        "court_claim": status["correspondence_court_claim"],
        "ready_for_stage_i3_shadow_planning": True,
        "stage_i3_shadow_authorized": False,
        "composition_authorized": False,
        "predecessor_snapshot_sha256": predecessor_sha256,
        **BOUNDARY,
    }
    return raw, {**receipt_body, "receipt_root": root(receipt_body)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("portfolio", type=Path)
    parser.add_argument("court_evidence", type=Path)
    parser.add_argument("--predecessor-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    raw_a, receipt_a = build(args.portfolio.resolve(), args.court_evidence.read_bytes(),
                             args.predecessor_sha256)
    raw_b, receipt_b = build(args.portfolio.resolve(), args.court_evidence.read_bytes(),
                             args.predecessor_sha256)
    require(raw_a == raw_b and receipt_a == receipt_b, "PIPELINE_PORTFOLIO_NONDETERMINISTIC")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    require(not args.out.exists(), "PIPELINE_PORTFOLIO_OUTPUT_EXISTS")
    args.out.write_bytes(raw_a)
    receipt_path = args.out.with_name(args.out.stem + "-RECEIPT.json")
    require(not receipt_path.exists(), "PIPELINE_PORTFOLIO_RECEIPT_EXISTS")
    receipt_path.write_bytes(canonical_bytes(receipt_a))
    print(json.dumps({"status": "PASS", "snapshot": str(args.out),
        "snapshot_sha256": sha(raw_a), "receipt": str(receipt_path),
        "court_root": receipt_a["correspondence_court_root"], **BOUNDARY}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

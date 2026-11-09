from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def rooted(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def receipt(body: dict[str, object]) -> dict[str, object]:
    return {**body, "receipt_root": rooted(body)}


def candidate(*, changed_paths: list[str], used: list[str], introduced: list[str],
              with_evidence: bool) -> dict[str, object]:
    body: dict[str, object] = {
        "schema": "mosaic.ucm.architecture-change-manifest.v0.2",
        "subject_root": "1" * 64,
        "changed_paths": changed_paths,
        "existing_abstractions_used": used,
        "introduced_abstractions": introduced,
        "supersession_roots": [],
    }
    change_root = rooted(body)
    tests = []
    proofs = []
    if with_evidence:
        tests.append(receipt({
            "schema": "mosaic.ucm.accepted-test-evidence.v0.1",
            "subject_root": body["subject_root"], "change_root": change_root,
            "test_set_root": "2" * 64, "failures": 0, "errors": 0,
            "skips": 0, "status": "PASS",
        }))
        proofs.append(receipt({
            "schema": "mosaic.ucm.accepted-proof-evidence.v0.1",
            "subject_root": body["subject_root"], "change_root": change_root,
            "proof_contract_root": "3" * 64, "proof_root": "4" * 64,
            "checker_root": "5" * 64, "status": "PASS",
        }))
    complete = {**body, "test_evidence_receipts": tests,
                "proof_evidence_receipts": proofs, "change_root": change_root}
    return {**complete, "candidate_root": rooted(complete)}


def write(name: str, value: dict[str, object]) -> None:
    path = ROOT / "examples" / "architecture" / "reference-data-client" / name
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> None:
    write("CONFORMING-CHANGE.json", candidate(
        changed_paths=["src/reference_client.py", "tests/test_reference_client.py"],
        used=["REFERENCE_CLIENT", "CANONICAL_RESPONSE_DECODER"],
        introduced=[], with_evidence=True))
    write("DRIFTING-CHANGE.json", candidate(
        changed_paths=["src/unrelated_cache.py"], used=[],
        introduced=["SECOND_REFERENCE_CLIENT"], with_evidence=False))


if __name__ == "__main__":
    main()

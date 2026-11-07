"""Canonicalize and root the checked-in maturity program data assets."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def rooted(path: Path, field: str) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    value.pop(field, None)
    value[field] = hashlib.sha256(canonical(value)).hexdigest()
    path.write_bytes(canonical(value))


def main() -> None:
    for path in sorted((ROOT / "policy-packs").glob("*.json")):
        rooted(path, "pack_root")
    rooted(ROOT / "program" / "UNIFIED-MATURITY-PROGRAM.json", "program_root")
    rooted(ROOT / "program" / "CONSOLIDATED-HARDENING-CAMPAIGN.json", "campaign_root")
    study_path = ROOT / "evaluation" / "ARCHITECTURE-COMPLIANCE-STUDY.json"
    study = json.loads(study_path.read_text(encoding="utf-8"))
    replacements = {
        "PLACEHOLDER_BASELINE_CONTEXT": "BASELINE_CONTEXT",
        "PLACEHOLDER_CONVENTIONAL_CONTEXT": "CONVENTIONAL_CONTEXT",
        "PLACEHOLDER_UCM_CONTEXT": "UCM_CONTEXT",
        "PLACEHOLDER_OVERSIGHT": "MATCHED_HUMAN_OVERSIGHT",
        "PLACEHOLDER_OBLIGATION": "SYNTHETIC_ARCHITECTURAL_OBLIGATION",
        "PLACEHOLDER_SUBJECT": "SYNTHETIC_APPLICATION_SUBJECT",
        "PLACEHOLDER_TASK": "SYNTHETIC_MAINTENANCE_TASK",
    }
    for arm in study["arms"]:
        for key in ("context_root", "human_oversight_policy_root"):
            if study_value := replacements.get(arm[key]):
                arm[key] = hashlib.sha256(study_value.encode("ascii")).hexdigest()
    task = study["tasks"][0]
    for key in ("subject_root", "task_root"):
        if task[key] in replacements:
            task[key] = hashlib.sha256(replacements[task[key]].encode("ascii")).hexdigest()
    task["architectural_obligation_roots"] = [
        hashlib.sha256(replacements[value].encode("ascii")).hexdigest()
        if value in replacements else value
        for value in task["architectural_obligation_roots"]
    ]
    study.pop("study_root", None)
    study["study_root"] = hashlib.sha256(canonical(study)).hexdigest()
    study_path.write_bytes(canonical(study))
    example = ROOT / "examples" / "architecture" / "reference-data-client"
    rooted(example / "ARCHITECTURE-CONTRACT.json", "contract_root")
    rooted(example / "CONFORMING-CHANGE.json", "candidate_root")
    rooted(example / "DRIFTING-CHANGE.json", "candidate_root")


if __name__ == "__main__":
    main()

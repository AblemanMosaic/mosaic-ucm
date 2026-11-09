#!/usr/bin/env python3
"""Standard-library deterministic structural runner for research envelopes.

The runner does not perform scholarly judgment.  It checks exact inputs and
emits bounded observations that a declared reviewer may use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


BOUNDARY = {
    "standing": "INFORMATION_ONLY",
    "authority_effect": "NONE",
    "real_a5": False,
    "g0": "CLOSED",
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def rooted(body: dict) -> str:
    return sha(canonical(body))


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_bytes(canonical(value) + b"\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", default="subject/paper.md")
    parser.add_argument("--lens-pack", default="policy/LENS-PACK.json")
    parser.add_argument("--context", default="context/CALIBRATION-CONTEXT.json")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    subject_path = Path(args.subject)
    lens_path = Path(args.lens_pack)
    context_path = Path(args.context)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    subject_raw = subject_path.read_bytes()
    subject_sha = sha(subject_raw)
    text = subject_raw.decode("utf-8")
    lens = load(lens_path)
    context = load(context_path)

    lens_body = {key: value for key, value in lens.items() if key != "lens_pack_root"}
    checks = [
        {
            "check_id": "SUBJECT_SHA256_MATCH",
            "status": "PASS" if subject_sha == context["expected_subject_sha256"] else "FAIL",
            "observed": subject_sha,
            "expected": context["expected_subject_sha256"],
        },
        {
            "check_id": "LENS_PACK_ROOT_MATCH",
            "status": "PASS" if rooted(lens_body) == lens.get("lens_pack_root") else "FAIL",
            "observed": rooted(lens_body),
            "expected": lens.get("lens_pack_root"),
        },
        {
            "check_id": "UTF8_TEXT",
            "status": "PASS",
            "observed": "STRICT_UTF8",
            "expected": "STRICT_UTF8",
        },
    ]
    headings = re.findall(r"(?m)^#{1,6}\s+(.+?)\s*$", text)
    external_urls = sorted(set(re.findall(r"https?://[^\s)>]+", text)))
    corpus_links = sorted(set(re.findall(r"\bAC-[0-9]{4}\b", text)))
    references = [heading for heading in headings if "reference" in heading.lower()]
    numbered_level_two = re.findall(r"(?m)^##\s+(\d+)\.", text)
    duplicate_numbered_sections = sorted({label for label in numbered_level_two
                                          if numbered_level_two.count(label) > 1})
    review_pass_headings = sorted(set(re.findall(r"(?m)^##\s+(P\d+\b[^\n]*)", text)))
    review_observations = []
    if duplicate_numbered_sections:
        review_observations.append({
            "observation_id": "DUPLICATE_NUMBERED_SECTION_LABELS",
            "classification": "POTENTIAL_EDITORIAL_ISSUE",
            "values": duplicate_numbered_sections,
        })
    if review_pass_headings:
        review_observations.append({
            "observation_id": "REVIEW_PASS_HEADINGS_IN_PAPER_BODY",
            "classification": "POTENTIAL_PROJECTION_ARTIFACT",
            "values": review_pass_headings,
        })
    observation_body = {
        "schema": "mosaic.research.deterministic-structural-observation.v0.1",
        "subject_sha256": subject_sha,
        "subject_bytes": len(subject_raw),
        "subject_lines": text.count("\n") + (0 if text.endswith("\n") else 1),
        "heading_count": len(headings),
        "reference_headings": references,
        "external_url_count": len(external_urls),
        "corpus_accession_reference_count": len(corpus_links),
        "checks": sorted(checks, key=lambda row: row["check_id"]),
        "review_observations": review_observations,
        "interpretation": "STRUCTURAL_OBSERVATION_ONLY",
        **BOUNDARY,
    }
    observation = {**observation_body, "observation_root": rooted(observation_body)}
    status = "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL"
    pass_body = {
        "schema": "mosaic.research.review-pass.v0.1",
        "review_id": context["review_id"],
        "subject_root": subject_sha,
        "lens_pack_root": lens["lens_pack_root"],
        "observation_root": observation["observation_root"],
        "status": status,
        "domain_verdict": "NOT_PERFORMED_BY_DETERMINISTIC_RUNNER",
        "independent_review_performed": False,
        "paper_mutated": False,
        "publication_authorized": False,
        **BOUNDARY,
    }
    review_pass = {**pass_body, "review_pass_root": rooted(pass_body)}
    write(output / "DETERMINISTIC-CHECKS.json", observation)
    write(output / "REVIEW-PASS.json", review_pass)
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Shared deterministic release functions for the UCM-AMCAS successor."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root  # noqa: E402
from ucm.artifacts import deterministic_zip, verify_deterministic_zip  # noqa: E402
from ucm.content_graph import build_graph  # noqa: E402


TOP_LEVEL = {"README.md", "AGENT-ACCESS.md", "LICENSE", "NOTICE", "pyproject.toml",
             "VERIFY.py", "STAGE.py", "SECURITY.md", "CONTRIBUTING.md"}
DIRECTORIES = {"src", "spec", "docs", "examples", "fixtures", "skill", "vendor",
               "tests", "integration-kits", "audit", "release", "sidecar"}
TOOLS = {"tools/ucm.py", "tools/build_amcas_program.py", "tools/amcas_release_common.py",
         "tools/build_amcas_release.py", "tools/build_amcas_templates.py",
         "tools/run_amcas_qualification.py", "tools/build_integration_c2_examples.py",
         "tools/build_c2_predecessor.py", "tools/build_agentic_adaptation_sidecar.py",
         "tools/seal_pipeline_portfolio.py", "tools/build_pipeline_release.py",
         "tools/seal_stage3_portfolio.py", "tools/build_stage3_review_handoff.py",
          "tools/rebind_stage3_plans.py", "tools/release_common.py",
          "tools/build_release.py", "tools/verify_release.py",
          "tools/prepare_release_contracts.py",
          "tools/run_stage3_candidate_attack_court.py",
          "tools/build_stage4_work13_checkpoint.py",
          "tools/build_stage3_review_archive.py",
          "tools/build_stage4_c2_operator_subject.py",
          "tools/build_stage4_c2_operator_kit.py",
          "tools/build_stage4_c2_review_handoff.py",
          "tools/freeze_stage4_c2.py",
          "tools/build_stage4_c3_operator_kit.py",
          "tools/build_stage4_c3_operator_delivery.py",
          "tools/build_stage4_c3_qualification_source.py",
          "tools/build_stage4_c3_review_handoff.py",
          "tools/freeze_stage4_c3.py",
          "tools/build_stage4_review_handoff.py",
          "tools/freeze_stage4_work13.py",
          "tools/build_stage4_c4_specs.py",
          "tools/run_stage4_c4_positive_qualification.py",
          "tools/run_stage4_c5_qualification.py",
          "tools/build_stage4_c5_release.py",
          "tools/build_stage4_c5_operator_kit.py",
          "tools/build_stage4_c5_operator_delivery.py"}
TOOLS.update({"tools/build_stage4_c4_operator_kit.py",
              "tools/build_stage4_c4_operator_delivery.py"})
CAMPAIGN_FILES = {"campaign/BASELINE-CAPSULE.json", "campaign/CAMPAIGN-CHARTER.json",
                  "campaign/PROGRAM-LEDGER.json", "campaign/C2-SUCCESSOR.json"}
RUNTIME_EXCLUDED_PREFIXES = (
    "vendor/amcas-standard/evidence/",
    "vendor/amcas-standard/tests/",
    "vendor/amcas-standard/tools/",
)
RUNTIME_EXCLUDED_FILES = {
    "vendor/amcas-standard/FINAL-REPORT.md",
    "vendor/amcas-standard/SOURCE-MANIFEST.json",
    "vendor/amcas-standard/SOURCE-PINS.json",
}


def software_payloads() -> dict[str, bytes]:
    payloads: dict[str, bytes] = {}
    for path in sorted((path for path in ROOT.rglob("*") if path.is_file()),
                       key=lambda item: item.relative_to(ROOT).as_posix()):
        relative = path.relative_to(ROOT).as_posix()
        parts = PurePosixPath(relative).parts
        if relative in RUNTIME_EXCLUDED_FILES or relative.startswith(RUNTIME_EXCLUDED_PREFIXES):
            continue
        if (relative in TOP_LEVEL or relative in TOOLS or relative in CAMPAIGN_FILES
                or (parts and parts[0] in DIRECTORIES)):
            if any(part in {"__pycache__", ".pytest_cache", ".venv"} for part in parts):
                continue
            if path.suffix.casefold() in {".pyc", ".pyo"}:
                continue
            payloads[relative] = path.read_bytes()
    return payloads


def qualification_source_payloads() -> dict[str, bytes]:
    """Return the exact public source closure used to reproduce qualification."""
    source_manifest = ROOT / "release/SOURCE-MANIFEST.json"
    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
    rows = manifest.get("members", manifest.get("files", []))
    payloads: dict[str, bytes] = {}
    for row in rows:
        path = ROOT / row["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise SystemExit("QUALIFICATION_SOURCE_MANIFEST_MISMATCH")
        payloads[row["path"]] = path.read_bytes()
    for path in sorted((ROOT / "release").glob("*"), key=lambda item: item.name):
        if path.is_file():
            payloads[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    return payloads


def build_software_archive() -> tuple[bytes, dict]:
    payloads = software_payloads()
    raw = deterministic_zip(payloads,
        schema="mosaic.ucm.amcas.canonical-software-archive.v0.1",
        artifact_role="CANONICAL_SOFTWARE")
    manifest = verify_deterministic_zip(raw,
        expected_schema="mosaic.ucm.amcas.canonical-software-archive.v0.1",
        expected_role="CANONICAL_SOFTWARE")
    source_body = {"schema": "mosaic.ucm.amcas.software-source.v0.1",
                   "files": manifest["files"], "file_count": len(manifest["files"])}
    anchor_body = {
        "schema": "mosaic.ucm.amcas.software-anchor.v0.1",
        "archive_sha256": hashlib.sha256(raw).hexdigest(), "archive_bytes": len(raw),
        "archive_manifest_root": manifest["manifest_root"],
        "source_root": root(source_body), "source_file_count": len(manifest["files"]),
        "published_ucm_release_root": "80f1f2f8a657a0c61fa46f7edd809f9059901fbbd7e661d2b6885d19974c187c",
        "baseline_capsule_root": __import__("json").loads(
            (ROOT / "campaign/BASELINE-CAPSULE.json").read_text(encoding="utf-8"))["capsule_root"],
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        "real_a5": False, "g0": "CLOSED",
    }
    return raw, {**anchor_body, "anchor_root": root(anchor_body)}


def build_qualification_source_archive() -> tuple[bytes, dict]:
    payloads = qualification_source_payloads()
    raw = deterministic_zip(payloads,
        schema="mosaic.ucm.amcas.qualification-source-archive.v0.1",
        artifact_role="QUALIFICATION_SOURCE")
    manifest = verify_deterministic_zip(raw,
        expected_schema="mosaic.ucm.amcas.qualification-source-archive.v0.1",
        expected_role="QUALIFICATION_SOURCE")
    anchor_body = {
        "schema": "mosaic.ucm.amcas.qualification-source-anchor.v0.1",
        "archive_sha256": hashlib.sha256(raw).hexdigest(), "archive_bytes": len(raw),
        "archive_manifest_root": manifest["manifest_root"],
        "source_manifest_root": json.loads(
            (ROOT / "release/SOURCE-MANIFEST.json").read_text(encoding="utf-8"))["root"],
        "source_file_count": len(manifest["files"]),
        "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
        "real_a5": False, "g0": "CLOSED",
    }
    return raw, {**anchor_body, "anchor_root": root(anchor_body)}


def write_new(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw); stream.flush(); __import__("os").fsync(stream.fileno())

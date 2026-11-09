"""Build the deterministic AMCAS–UCM baseline, parity, and portfolio package."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root, strict_loads
from ucm.amcas_parity import (
    build_amcas_registry,
    build_profile_baseline_migration,
    build_portfolio_observatory,
    build_ucm_coverage_registry,
    compile_amcas_baseline,
    compile_stage_i3_profile_set,
    run_amcas_ucm_parity,
)
from ucm.artifacts import deterministic_zip, verify_deterministic_zip
from ucm.system import BOUNDARY

SCHEMA = "mosaic.ucm.amcas-parity-program-archive.v0.1"
ROLE = "UCM_AMCAS_BASELINE_AND_PARITY_PROGRAM"
DIST = ROOT / "dist/UCM-AMCAS-BASELINE-PARITY-PROGRAM-C1.zip"
RECEIPT = ROOT / "dist/UCM-AMCAS-BASELINE-PARITY-PROGRAM-C1-RECEIPT.json"
SPEC = ROOT / "spec/amcas-baseline"
INTEGRATION = ROOT / "integration/amcas-parity"
PLAN_DIR = ROOT / "integration/stage-i3/authoring/plans"


def write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def semantic_policy() -> dict:
    families = [
        ("ARTIFACT_CUSTODY", "Artifact custody, replay, and evidence access", "CORRESPONDENCE_DEMO_AVAILABLE"),
        ("PRESENTATION", "Human presentation, layout, and interaction projections", "AUTHORING_REQUIRED"),
        ("OPERATION", "Intent, preflight, execution, observation, and terminal state", "AUTHORING_REQUIRED"),
        ("CONTENT_GRAPH", "Content-addressed entities, links, queries, and projections", "AUTHORING_REQUIRED"),
        ("EVIDENCE_QUERY", "Read-only evidence discovery, filtering, explanation, and export", "AUTHORING_REQUIRED"),
        ("IDENTITY_JURISDICTION", "MosaicID, session identity, DKN jurisdiction, and delegation", "AUTHORING_REQUIRED"),
        ("LIFECYCLE_RECOVERY", "Migration, rollback, uncertain state, and no-redispatch recovery", "AUTHORING_REQUIRED"),
    ]
    rows = []
    for family_id, title, status in families:
        body = {"family_id": family_id, "title": title, "status": status,
                "admissible_forms": ["SHARED_CONTRACT", "SHARED_ADAPTER", "SHARED_SERVICE", "PRESERVE_SEPARATE"],
                "default_preference": "SHARED_CONTRACT_THEN_ADAPTER",
                "semantic_equivalence_required": True}
        rows.append({**body, "family_root": root(body)})
    body = {"schema": "mosaic.ucm.semantic-consolidation-baseline.v0.1",
            "policy_id": "SEMANTIC_CONSOLIDATION_BASELINE_V0_1",
            "families": rows,
            "rules": ["NO_NAME_ONLY_EQUIVALENCE", "NO_EFFECTFUL_SERVICE_WITHOUT_CORRESPONDENCE_EVIDENCE",
                      "NATIVE_AUTHORITY_PRESERVED", "CM1_BEFORE_CM2"], **BOUNDARY}
    return {**body, "policy_root": root(body)}


def sdk_payloads() -> tuple[dict[str, bytes], dict]:
    payloads: dict[str, bytes] = {}
    rows = []
    for path in sorted((ROOT / "src").rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        relative = path.relative_to(ROOT).as_posix()
        raw = path.read_bytes()
        payloads[f"sdk/{relative}"] = raw
        rows.append({"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    for name in ("pyproject.toml", "LICENSE"):
        raw = (ROOT / name).read_bytes()
        payloads[f"sdk/{name}"] = raw
        rows.append({"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    rows.sort(key=lambda row: row["path"])
    body = {"schema": "mosaic.ucm.portable-python-sdk-manifest.v0.1",
            "files": rows, "file_count": len(rows), "source_manifest_root": root(rows), **BOUNDARY}
    manifest = {**body, "sdk_manifest_root": root(body)}
    payloads["sdk/SDK-SOURCE-MANIFEST.json"] = canonical_bytes(manifest)
    return payloads, manifest


def build(out: Path = DIST) -> dict:
    registry = build_amcas_registry()
    coverage = build_ucm_coverage_registry(registry)
    parity = run_amcas_ucm_parity(registry, coverage)
    contract = strict_loads((ROOT / "examples/amcas/portable-agent.integration.json").read_bytes())
    program = compile_amcas_baseline(contract, amcas_registry_value=registry, coverage_value=coverage)
    policy = semantic_policy()
    migration = build_profile_baseline_migration()

    profile_sets = []
    for path in sorted(PLAN_DIR.glob("*.json")):
        profile_sets.append(compile_stage_i3_profile_set(strict_loads(path.read_bytes()), registry, coverage))
    consolidation_roots = []
    old = ROOT / "examples/consolidation/memory-vault-custody/CONSOLIDATION-PROGRAM.json"
    if old.exists():
        consolidation_roots.append(strict_loads(old.read_bytes())["consolidation_root"])
    observatory = build_portfolio_observatory(profile_sets=profile_sets,
        parity_result=parity, consolidation_roots=consolidation_roots)

    write(SPEC / "AMCAS-ELEMENT-REGISTRY.json", canonical_bytes(registry))
    write(SPEC / "UCM-COVERAGE-REGISTRY.json", canonical_bytes(coverage))
    write(SPEC / "AMCAS-UCM-PARITY-CONTRACT.json", canonical_bytes({
        "schema": "mosaic.ucm.amcas-parity-contract.v0.1",
        "amcas_registry_root": registry["registry_root"],
        "coverage_root": coverage["coverage_root"],
        "fixed_denominator": parity["fixed_denominator"],
        "allowed_coverage_statuses": ["APPLICATION_ADAPTER_REQUIRED", "IMPLEMENTED", "PARTIAL", "UNIMPLEMENTED"],
        "unimplemented_refuses": True, "declared_gaps_remain_visible": True, **BOUNDARY}))
    for row in registry["elements"]:
        write(SPEC / "elements" / f"{row['element_id']}.json", canonical_bytes(row))
    write(INTEGRATION / "AMCAS-UCM-PARITY-RESULT.json", canonical_bytes(parity))
    write(INTEGRATION / "PORTFOLIO-OBSERVATORY.json", canonical_bytes(observatory))
    write(INTEGRATION / "PIPPI-C1-PROFILE-BASELINE-MIGRATION.json", canonical_bytes(migration))
    write(ROOT / "examples/amcas/portable-agent.baseline-program.json", canonical_bytes(program))
    write(ROOT / "policy-packs/SEMANTIC-CONSOLIDATION-BASELINE-v0.1.json", canonical_bytes(policy))
    for value in profile_sets:
        safe = value["application_id"].replace(".", "-").replace("/", "-")
        write(INTEGRATION / "application-profiles" / f"{safe}.json", canonical_bytes(value))

    payloads = {
        "baseline/AMCAS-ELEMENT-REGISTRY.json": canonical_bytes(registry),
        "baseline/UCM-COVERAGE-REGISTRY.json": canonical_bytes(coverage),
        "baseline/AMCAS-UCM-PARITY-RESULT.json": canonical_bytes(parity),
        "baseline/PORTFOLIO-OBSERVATORY.json": canonical_bytes(observatory),
        "baseline/PIPPI-C1-PROFILE-BASELINE-MIGRATION.json": canonical_bytes(migration),
        "baseline/SEMANTIC-CONSOLIDATION-POLICY.json": canonical_bytes(policy),
        "example/AMCAS-CONTRACT.json": canonical_bytes(contract),
        "example/BASELINE-PROGRAM.json": canonical_bytes(program),
        "docs/AMCAS-UCM-BASELINE-ARCHITECTURE.md": (ROOT / "docs/AMCAS-UCM-BASELINE-ARCHITECTURE.md").read_bytes(),
        "docs/AMCAS-UCM-PARITY-COURT.md": (ROOT / "docs/AMCAS-UCM-PARITY-COURT.md").read_bytes(),
        "docs/AMCAS-MIGRATION-PLAYBOOK.md": (ROOT / "docs/AMCAS-MIGRATION-PLAYBOOK.md").read_bytes(),
        "docs/JOINT-REVIEW-WORK-ORDER.md": (ROOT / "docs/AMCAS-UCM-JOINT-REVIEW-WORK-ORDER.md").read_bytes(),
        "software/amcas_parity.py": (ROOT / "src/ucm/amcas_parity.py").read_bytes(),
        "software/build_amcas_parity_program.py": Path(__file__).read_bytes(),
    }
    for row in registry["elements"]:
        payloads[f"baseline/elements/{row['element_id']}.json"] = canonical_bytes(row)
    for value in profile_sets:
        safe = value["application_id"].replace(".", "-").replace("/", "-")
        payloads[f"application-profiles/{safe}.json"] = canonical_bytes(value)
    for path in sorted(PLAN_DIR.glob("*.json")):
        payloads[f"inputs/stage-i3-plans/{path.name}"] = path.read_bytes()
    qualification = ROOT / "dist/UCM-AMCAS-BASELINE-PARITY-POSITIVE-QUALIFICATION.json"
    if qualification.exists():
        payloads["qualification/POSITIVE-QUALIFICATION.json"] = qualification.read_bytes()
    sdk, sdk_manifest = sdk_payloads()
    payloads.update(sdk)
    first = deterministic_zip(payloads, schema=SCHEMA, artifact_role=ROLE)
    second = deterministic_zip(payloads, schema=SCHEMA, artifact_role=ROLE)
    if first != second:
        raise RuntimeError("AMCAS_PARITY_ARCHIVE_NONDETERMINISTIC")
    verify_deterministic_zip(first, expected_schema=SCHEMA, expected_role=ROLE)
    write(out, first)
    receipt_body = {"schema": "mosaic.ucm.amcas-parity-program-receipt.v0.1",
        "archive_sha256": hashlib.sha256(first).hexdigest(), "archive_bytes": len(first),
        "amcas_registry_root": registry["registry_root"], "coverage_root": coverage["coverage_root"],
        "parity_court_root": parity["court_root"], "fixed_denominator": parity["fixed_denominator"],
        "portfolio_observatory_root": observatory["observatory_root"],
        "application_profile_count": len(profile_sets), "sdk_manifest_root": sdk_manifest["sdk_manifest_root"],
        "operator_tier1_executed": False, "status": "PASS_DETERMINISTIC_PACKAGE", **BOUNDARY}
    receipt = {**receipt_body, "receipt_root": root(receipt_body)}
    write(RECEIPT, canonical_bytes(receipt))
    return {**receipt, "archive": str(out)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build AMCAS–UCM baseline and parity program")
    parser.add_argument("--out", type=Path, default=DIST)
    args = parser.parse_args()
    print(canonical_bytes(build(args.out)).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

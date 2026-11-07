"""Run the one cache-free positive/static AMCAS parity qualification."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True

from uclop.canonical import canonical_bytes, root
from ucm.amcas_parity import (build_amcas_registry, build_portfolio_observatory,
    build_ucm_coverage_registry, compile_stage_i3_profile_set, run_amcas_ucm_parity)
from ucm.amcas import BOUNDARY
from uclop.canonical import strict_loads

MODULES = [
    "tests.test_amcas_parity",
    "tests.test_constitutional_integration",
    "tests.test_public_surface",
    "tests.test_maturity_evolution",
    "tests.test_stage4_c5_operational_positive",
    "tests.test_semantic_consolidation",
    "tests.test_courthouse_workflow",
]
OUT = ROOT / "dist/UCM-AMCAS-BASELINE-PARITY-POSITIVE-QUALIFICATION.json"


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def source_manifest():
    paths = []
    for base in (ROOT / "src", ROOT / "spec/amcas-baseline", ROOT / "integration/amcas-parity",
                 ROOT / "integration/stage-i3/authoring/plans"):
        paths.extend(path for path in base.rglob("*") if path.is_file())
    paths.extend((ROOT / module.replace(".", "/")).with_suffix(".py") for module in MODULES)
    paths += [ROOT / "src/ucm/amcas_parity.py", ROOT / "tools/build_amcas_parity_program.py",
              ROOT / "tools/run_amcas_parity_positive_qualification.py",
              ROOT / "examples/amcas/portable-agent.integration.json",
              ROOT / "examples/amcas/portable-agent.baseline-program.json",
              ROOT / "policy-packs/SEMANTIC-CONSOLIDATION-BASELINE-v0.1.json"]
    paths += list((ROOT / "docs").glob("AMCAS-*.md"))
    unique = sorted({path.resolve() for path in paths if path.exists()
                     and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}})
    rows = []
    for path in unique:
        raw = path.read_bytes()
        rows.append({"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw),
                     "sha256": hashlib.sha256(raw).hexdigest()})
    return rows


def main() -> int:
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite(loader.loadTestsFromName(name) for name in MODULES)
    test_ids = sorted(test.id() for test in flatten(suite))
    print(f"[qualification] collected={len(test_ids)} cache_free=true", flush=True)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    registry = build_amcas_registry()
    coverage = build_ucm_coverage_registry(registry)
    parity = run_amcas_ucm_parity(registry, coverage)
    plans = [strict_loads(path.read_bytes())
             for path in sorted((ROOT / "integration/stage-i3/authoring/plans").glob("*.json"))]
    profiles = [compile_stage_i3_profile_set(plan, registry, coverage) for plan in plans]
    observatory = build_portfolio_observatory(profile_sets=profiles, parity_result=parity)
    files = source_manifest()
    body = {"schema": "mosaic.ucm.amcas-parity-positive-qualification.v0.1",
        "qualification_scope": "POSITIVE_AND_STATIC_ONLY",
        "adversarial_cases_executed": False, "cache_free": True,
        "python_implementation": sys.implementation.name,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "test_modules": MODULES, "test_ids": test_ids, "test_identity_root": root(test_ids),
        "tests_run": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "skips": len(result.skipped),
        "source_files": files, "source_manifest_root": root(files),
        "amcas_registry_root": registry["registry_root"], "coverage_root": coverage["coverage_root"],
        "parity_court_root": parity["court_root"], "parity_denominator": parity["fixed_denominator"],
        "portfolio_observatory_root": observatory["observatory_root"],
        "status": "PASS" if result.wasSuccessful() and not result.skipped else "FAIL",
        **BOUNDARY}
    record = {**body, "qualification_root": root(body)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(canonical_bytes(record))
    print(json.dumps({"status": record["status"], "tests": result.testsRun,
        "qualification_root": record["qualification_root"], "out": str(OUT)}, sort_keys=True), flush=True)
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())




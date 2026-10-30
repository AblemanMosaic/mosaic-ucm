"""Bind the preserved C1 predecessor without copying its build products."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root  # noqa: E402
from ucm.amcas import BOUNDARY  # noqa: E402
from ucm.subject import bind_subject  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("predecessor", type=Path)
    args = parser.parse_args()
    binding = bind_subject(args.predecessor, {
        "schema": "mosaic.ucm.subject-binding-policy.v0.1",
        "subject_id": "MOSAIC.UCM.AMCAS.INTEGRATION.WORKBENCH.C1",
        "mode": "IMMUTABLE_SNAPSHOT", "include": ["**/*"],
        "exclude": [".git/**", ".build/**", "dist/**", "__pycache__/**",
                    ".pytest_cache/**", ".venv/**"],
        "allow_symlinks": False, "git_observation": "OPTIONAL",
    })
    releases = []
    dist = args.predecessor / "dist"
    for path in sorted(dist.glob("*"), key=lambda value: value.name):
        if path.is_file():
            releases.append({"name": path.name, "sha256": sha(path), "bytes": path.stat().st_size})
    body = {
        "schema": "mosaic.ucm.amcas.c1-predecessor.v0.1",
        "predecessor_id": "MOSAIC_UCM_AMCAS_INTEGRATION_WORKBENCH_C1",
        "source_binding_root": binding["binding_root"],
        "source_root": binding["source_root"],
        "source_manifest_root": binding["manifest_root"],
        "source_file_count": binding["file_count"],
        "release_artifacts": releases,
        "custody": "PRESERVED_EXTERNAL_PREDECESSOR",
        **BOUNDARY,
    }
    record = {**body, "predecessor_root": root(body)}
    destination = ROOT / "audit/AMCAS-C1-PREDECESSOR.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(canonical_bytes(record))
    successor_body = {
        "schema": "mosaic.ucm.amcas.c2-successor.v0.1",
        "program_id": "MOSAIC_UCM_AMCAS_INTEGRATION_WORKBENCH_C2",
        "predecessor_root": record["predecessor_root"],
        "objective": "Exact subject binding, native control-plane correspondence, Stage I1 returns, and governed portfolio integration.",
        "compatibility": "C1_RETAINED_AS_EXTERNAL_HASH_BOUND_PREDECESSOR",
        "claim": "BUILDER_SUCCESSOR_PENDING_QUALIFICATION_AND_INDEPENDENT_REVIEW",
        **BOUNDARY,
    }
    (ROOT / "campaign/C2-SUCCESSOR.json").write_bytes(canonical_bytes(
        {**successor_body, "successor_root": root(successor_body)}))
    print(canonical_bytes(record).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

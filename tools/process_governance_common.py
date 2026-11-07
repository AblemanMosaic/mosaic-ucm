from __future__ import annotations

import hashlib
from pathlib import Path

from uclop.canonical import root


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATHS = (
    "AGENT-ACCESS.md",
    "README.md",
    "docs/PIPPI-PROCESS-GOVERNANCE.md",
    "docs/PIPPI-CONSTRUCTION-WORK-ORDER.md",
    "docs/PIPPI.md",
    "policy-packs/PIPPI-PROCESS-GOVERNANCE-v0.1.json",
    "skill/ucm-pippi-mediated-agent/SKILL.md",
    "skill/ucm-pippi-mediated-agent/references/process-governance.md",
    "spec/PIPPI-PROCESS-GOVERNANCE-CONTRACT.json",
    "src/uclop/canonical.py",
    "src/ucm/__init__.py",
    "src/ucm/capabilities.py",
    "src/ucm/cli.py",
    "src/ucm/development_standards.py",
    "src/ucm/governance.py",
    "src/ucm/identity.py",
    "src/ucm/process_governance.py",
    "src/ucm/profiles.py",
    "src/ucm/system.py",
    "src/ucm/thr_cas.py",
    "tests/test_process_governance.py",
    "operator-kits/process-governance-c1/RUN-TIER1.py",
    "tools/build_pippi_process_governance_demo.py",
    "tools/build_process_governance_operator_kit.py",
    "tools/process_governance_common.py",
    "tools/run_process_governance_qualification.py",
    "tools/verify_process_governance_archive.py",
)


def source_manifest() -> dict:
    rows = []
    for relative in SOURCE_PATHS:
        raw = (ROOT / relative).read_bytes()
        rows.append({"path": relative, "sha256": hashlib.sha256(raw).hexdigest(),
                     "bytes": len(raw)})
    body = {"schema": "mosaic.ucm.process-governance-source-manifest.v0.1",
            "files": rows, "file_count": len(rows),
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
    return {**body, "source_manifest_root": root(body)}

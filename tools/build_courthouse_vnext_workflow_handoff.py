"""Build the deterministic UCM/Courthouse vNext Workflow IR handoff."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root


FILES = (
    "docs/COURTHOUSE-VNEXT-WORKFLOW-IR.md",
    "spec/UCM-AOK-VNEXT-WORKFLOW-IR-CONTRACT.json",
    "examples/courthouse-vnext/terminal-ui-workflow-request.json",
    "examples/courthouse-vnext/terminal-ui-workflow-ir.json",
    "src/ucm/courthouse_workflow.py",
    "tests/test_courthouse_workflow.py",
)
TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def build(output: Path) -> dict:
    entries = []
    payloads = {}
    for name in FILES:
        raw = (ROOT / name).read_bytes()
        payloads[name] = raw
        entries.append({"path": name, "bytes": len(raw),
                        "sha256": hashlib.sha256(raw).hexdigest()})
    protocol = json.loads(payloads[
        "spec/UCM-AOK-VNEXT-WORKFLOW-IR-CONTRACT.json"].decode("utf-8"))
    body = {
        "schema": "mosaic.ucm.aok-vnext-workflow-ir-handoff.v0.1",
        "artifact_role": "UCM_AOK_VNEXT_WORKFLOW_IR_INTEGRATION_HANDOFF",
        "protocol_id": protocol["protocol_id"],
        "protocol_contract_root": protocol["contract_root"],
        "files": entries,
        "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE",
        "real_a5": False,
        "g0": "CLOSED",
        "non_claims": ["NOT_VNEXT_INSTALLATION", "NOT_EXECUTION_AUTHORITY",
                       "NOT_COURTHOUSE_DISPOSITION"],
    }
    manifest = {**body, "handoff_root": root(body)}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(payloads):
            info = zipfile.ZipInfo(name, TIMESTAMP)
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payloads[name])
        info = zipfile.ZipInfo("HANDOFF.json", TIMESTAMP)
        info.external_attr = 0o100644 << 16
        archive.writestr(info, canonical_bytes(manifest))
    raw = output.read_bytes()
    return {"path": str(output), "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw), "handoff_root": manifest["handoff_root"],
            "status": "PASS", "authority_effect": "NONE"}


if __name__ == "__main__":
    target = (Path(sys.argv[1]) if len(sys.argv) > 1 else
              ROOT / "dist" / "UCM-AOK-VNEXT-WORKFLOW-IR-C1-HANDOFF.zip")
    print(json.dumps(build(target), sort_keys=True))

"""Build the slim adaptation sidecar used beside Mosaic UCM v0.1."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from uclop.canonical import canonical_bytes, root
from ucm.amcas import BOUNDARY
from ucm.artifacts import deterministic_zip, verify_deterministic_zip

SCHEMA = "mosaic.ucm.agentic-adaptation-sidecar.v0.1"
ROLE = "UCM_AMCAS_AGENTIC_ADAPTATION_SIDECAR"

def build() -> bytes:
    registry = json.loads((ROOT / "spec/ucm-system-registry.json").read_bytes())
    contract_body = {
        "schema": "mosaic.ucm.agentic-adaptation-sidecar-contract.v0.1",
        "product": "Mosaic UCM-AMCAS Agentic Adaptation Sidecar",
        "version": "v0.1",
        "required_ucm_system_registry_root": registry["root"],
        "required_ucm_capability_registry_root": registry["capability_registry_root"],
        "entrypoint": "UCM-AMCAS-ADAPT.py",
        "evidence_rule": "JOURNAL_AND_BOUND_G1_G2_G3_RECEIPTS_ONLY",
        "composition_rule": "BILATERAL_EXPLICIT_STAGE_I2",
        "progress_semantics": "NONSEMANTIC",
        **BOUNDARY,
    }
    payloads = {
        name: (ROOT / "sidecar" / name).read_bytes()
        for name in ("UCM-AMCAS-ADAPT.py", "RUN-UCM-AMCAS-ADAPT.cmd", "START-HERE.md", "VERIFY.py")
    }
    payloads["SIDECAR-CONTRACT.json"] = canonical_bytes(
        {**contract_body, "contract_root": root(contract_body)})
    for path in sorted((ROOT / "skill/ucm-amcas-integration").rglob("*")):
        if path.is_file():
            payloads["skill/ucm-amcas-integration/" + path.relative_to(
                ROOT / "skill/ucm-amcas-integration").as_posix()] = path.read_bytes()
    for path in sorted((ROOT / "integration-kits/templates").glob("*.json")):
        payloads["templates/" + path.name] = path.read_bytes()
    payloads["templates/MOSAIC-APPLICATIONS.json"] = (
        ROOT / "examples/portfolio/MOSAIC-APPLICATIONS.json").read_bytes()
    payloads["templates/PORTABLE-AGENT.integration.json"] = (
        ROOT / "examples/amcas/portable-agent.integration.json").read_bytes()
    for name in ("amcas-integration-contract-v0.2.schema.json",
                 "integration-journal-event-v0.1.schema.json",
                 "integration-session-report-v0.1.schema.json",
                 "realization-space-contract-v0.1.schema.json"):
        payloads["schemas/" + name] = (ROOT / "spec" / name).read_bytes()
    raw = deterministic_zip(payloads, schema=SCHEMA, artifact_role=ROLE)
    verify_deterministic_zip(raw, expected_schema=SCHEMA, expected_role=ROLE)
    return raw

def main() -> int:
    output = Path(sys.argv[1])
    raw = build()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and output.read_bytes() != raw:
        raise SystemExit("SIDECAR_OUTPUT_EXISTS_DIFFERENT")
    output.write_bytes(raw)
    print(json.dumps({"status":"PASS", "path":str(output),
                      "sha256":hashlib.sha256(raw).hexdigest(), "bytes":len(raw), **BOUNDARY},
                     sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

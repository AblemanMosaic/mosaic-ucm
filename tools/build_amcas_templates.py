"""Build validated application integration contract templates."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root  # noqa: E402
from ucm.amcas import validate_contract  # noqa: E402


PROFILES = {
    "DETERMINISTIC-APPLICATION": ("MOSAIC.APPLICATION.DETERMINISTIC", False, False),
    "AGENT-WORKFLOW": ("MOSAIC.APPLICATION.AGENT_WORKFLOW", True, False),
    "FEDERATED-COURTHOUSE": ("MOSAIC.APPLICATION.FEDERATED_COURTHOUSE", True, True),
    "MOSAICOS-M1-BINDING": ("MOSAICOS.M1.UNBOUND_BINDING", True, True),
}


def build(name: str, application_id: str, identity: bool, federation: bool) -> dict:
    value = json.loads((ROOT / "examples/amcas/portable-agent.integration.json")
                       .read_text(encoding="utf-8"))
    value["integration_id"] = application_id + ".INTEGRATION"
    value["application"] = {"id": application_id, "name": name.replace("-", " ").title(),
                            "version": "UNBOUND"}
    value["identities"].update({"user_required": identity, "agent_required": identity,
                                "possession_required": identity,
                                "delegation_required": federation})
    value["identities"]["jurisdiction"]["namespace_id"] = application_id
    value["subject"] = {"source_root": "0" * 64, "manifest_root": "0" * 64,
                        "path_policy": "PORTABLE_POSIX_RELATIVE_V1"}
    placeholder = {"schema": "mosaic.ucm.control-plane-disposition.v0.1",
                   "application_id": application_id, "binding_status": "UNBOUND_TEMPLATE"}
    value["integration_boundary"] = {
        "semantic_authority": application_id + ".NATIVE.UNBOUND",
        "effect_executor": application_id + ".NATIVE.UNBOUND",
        "identity_binding_status": "UNBOUND",
        "jurisdiction_binding_status": "UNBOUND",
        "gate_namespace": "UCM.INTEGRATION",
        "control_plane_root": root(placeholder),
    }
    value["cm1"]["requirements"][0]["subject_root"] = "0" * 64
    value["cm1"]["requirements"].append({
        "id": "BINDING_REQUIRED", "kind": "IDENTITY",
        "statement": "Replace all unbound roots and identities before integration work.",
        "subject_root": root({"profile": name, "state": "UNBOUND"}),
        "verifier": "AMCAS_BINDING_COMPLETENESS_V1", "evidence_required": True,
        "applicability": "REQUIRED",
    })
    value["dependencies"] = [{"id": "UCM_V01", "kind": "TOOL", "required": True,
                                "root": "80f1f2f8a657a0c61fa46f7edd809f9059901fbbd7e661d2b6885d19974c187c"}]
    body = {key: deepcopy(item) for key, item in value.items() if key != "contract_root"}
    value["contract_root"] = root(body)
    return validate_contract(value)


def main() -> int:
    out = ROOT / "integration-kits" / "templates"; out.mkdir(parents=True, exist_ok=True)
    for name, fields in PROFILES.items():
        path = out / f"{name}.integration.json"
        raw = canonical_bytes(build(name, *fields))
        if path.exists() and path.read_bytes() != raw:
            raise SystemExit(f"AMCAS_TEMPLATE_DRIFT:{path.name}")
        path.write_bytes(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Build deterministic C2 integration examples and portfolio roster."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root  # noqa: E402
from ucm.amcas import BOUNDARY  # noqa: E402
from ucm.control_planes import make_control_plane_disposition  # noqa: E402


def write(relative: str, value: dict) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def main() -> int:
    write("examples/integration/subject-binding-policy.json", {
        "schema": "mosaic.ucm.subject-binding-policy.v0.1",
        "subject_id": "EXAMPLE.APPLICATION", "mode": "IMMUTABLE_SNAPSHOT",
        "include": ["**/*"],
        "exclude": [".git/**", ".venv/**", "__pycache__/**", "dist/**"],
        "allow_symlinks": False, "git_observation": "OPTIONAL",
    })
    control = make_control_plane_disposition(
        application_id="EXAMPLE.APPLICATION",
        semantic_authority="EXAMPLE.APPLICATION.NATIVE",
        effect_executor="EXAMPLE.APPLICATION.NATIVE",
        identity_binding_status="UNBOUND", jurisdiction_binding_status="UNBOUND",
        gate_namespace="UCM.INTEGRATION.EXAMPLE.APPLICATION",
        native_control_planes=[{
            "id": "EXAMPLE.APPLICATION.NATIVE", "role": "APPLICATION_SEMANTICS_AND_EFFECTS",
            "disposition": "RETAIN", "semantic_authority": True,
            "effect_classes": ["LOCAL_ARTIFACT_PREPARATION"],
            "equivalence_evidence_root": None,
        }])
    write("examples/integration/control-plane-disposition.json", control)
    result_root = root({"decision": "PASS", "meaning": "example-correspondence"})
    write("examples/integration/native-correspondence-cases.json", {
        "schema": "mosaic.ucm.native-correspondence-cases.v0.1",
        "application_id": "EXAMPLE.APPLICATION", "subject_root": "0" * 64,
        "native_validator_id": "EXAMPLE.APPLICATION.NATIVE",
        "ucm_validator_id": "UCM.SHADOW.UNBOUND",
        "cases": [{"case_id": "EXAMPLE-001",
                   "input_root": root({"example": "replace-before-use"}),
                   "native": {"decision": "PASS", "result_root": result_root},
                   "ucm": {"decision": "PASS", "result_root": result_root}}],
    })
    applications = [
        ("MOSAIC.FIELD_MODELER", "Mosaic Field Modeler", "01a170ce-8e9b-7873-b5d4-3f1a65be4e30", "DETERMINISTIC-APPLICATION"),
        ("MOSAIC.AAC", "Mosaic AAC", "01a097ee-aa41-7e70-a8ed-14f263c743f4", "AGENT-WORKFLOW"),
        ("MOSAIC.2D_3D", "Mosaic 2D and 3D", "01a10039-9128-7ab1-a679-d11cd6250f69", "DETERMINISTIC-APPLICATION"),
        ("MOSAIC.MEMORY_VAULT", "Mosaic Memory Vault", "01a0def1-74b1-74d3-ade9-e16e1c675788", "AGENT-WORKFLOW"),
        ("MOSAIC.MESSENGER_CRYSTAL", "Mosaic Messenger and Crystal Network", "01a0f101-c920-77a2-9384-8b4522d51d2d", "FEDERATED-COURTHOUSE"),
        ("MOSAIC.MEDIA_CENTER", "Mosaic Media Center", "01a10da7-138e-7b40-b670-48e33c38c634", "AGENT-WORKFLOW"),
        ("MOSAIC.READER", "Mosaic Reader", "01a17ea6-3891-77b0-b16b-c7fb3cd8040d", "DETERMINISTIC-APPLICATION"),
    ]
    body = {"schema": "mosaic.ucm.integration-portfolio.v0.1",
            "portfolio_id": "ABLEMAN_MOSAIC_UCM_AMCAS_C2",
            "applications": [{"id": i, "name": n, "thread_id": t, "kit": k}
                             for i, n, t, k in applications], **BOUNDARY}
    write("examples/portfolio/MOSAIC-APPLICATIONS.json",
          {**body, "roster_root": root(body)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Freeze the UCM-AMCAS successor from a completed qualification.

The operational software, durable integration journal, application kit, and
review handoff are separate artifacts.  Every artifact is deterministic and
the handoff binds exact bytes; none grants authority.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root, strict_loads  # noqa: E402
from ucm.amcas import validate_contract  # noqa: E402
from ucm.artifacts import (  # noqa: E402
    build_integration_kit,
    build_integration_kit_from_contract,
    deterministic_zip,
    export_journal_archive,
    verify_deterministic_zip,
)
from ucm.integration import IntegrationCampaign  # noqa: E402
from ucm.reporting import build_report  # noqa: E402
from ucm.control_planes import make_control_plane_disposition  # noqa: E402
from ucm.portfolio import validate_roster  # noqa: E402
from amcas_release_common import build_software_archive, write_new  # noqa: E402


BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def self_control_plane() -> dict:
    return make_control_plane_disposition(
        application_id="MOSAIC.UCM.AMCAS.WORKBENCH",
        semantic_authority="MOSAIC.UCM.AMCAS.NATIVE",
        effect_executor="MOSAIC.UCM.AMCAS.NATIVE",
        identity_binding_status="UNBOUND", jurisdiction_binding_status="UNBOUND",
        gate_namespace="UCM.INTEGRATION.MOSAIC.UCM.AMCAS",
        native_control_planes=[{
            "id": "MOSAIC.UCM.AMCAS.NATIVE", "role": "WORKBENCH_SEMANTICS_AND_EFFECTS",
            "disposition": "RETAIN", "semantic_authority": True,
            "effect_classes": ["LOCAL_ARTIFACT_PREPARATION"],
            "equivalence_evidence_root": None,
        }])


def self_contract(anchor: dict, control: dict) -> dict:
    value = json.loads((ROOT / "examples/amcas/portable-agent.integration.json")
                       .read_text(encoding="utf-8"))
    value["integration_id"] = "MOSAIC.UCM.AMCAS.WORKBENCH.C2"
    value["application"] = {"id": "MOSAIC.UCM.AMCAS.WORKBENCH",
                            "name": "Mosaic UCM AMCAS Integration Workbench",
                            "version": "0.2"}
    value["subject"] = {"source_root": anchor["source_root"],
                        "manifest_root": anchor["archive_manifest_root"],
                        "path_policy": "PORTABLE_POSIX_RELATIVE_V1"}
    value["identities"]["jurisdiction"]["namespace_id"] = "MOSAIC.UCM.AMCAS.C2"
    value["integration_boundary"] = {
        "semantic_authority": control["semantic_authority"],
        "effect_executor": control["effect_executor"],
        "identity_binding_status": control["identity_binding_status"],
        "jurisdiction_binding_status": control["jurisdiction_binding_status"],
        "gate_namespace": "UCM.INTEGRATION",
        "control_plane_root": control["root"],
    }
    value["cm1"]["requirements"] = [
        {"id": "SOURCE_BOUND", "kind": "EVIDENCE",
         "statement": "The frozen software archive equals the qualified source boundary.",
         "subject_root": anchor["source_root"], "verifier": "AMCAS_SOURCE_BINDING_V1",
         "evidence_required": True, "applicability": "REQUIRED"},
        {"id": "QUALIFICATION_PASS", "kind": "ACCEPTANCE",
         "statement": "The cache-free qualification passes with zero failures, errors, or skips.",
         "subject_root": anchor["source_root"], "verifier": "AMCAS_QUALIFICATION_V1",
         "evidence_required": True, "applicability": "REQUIRED"},
        {"id": "PORTABLE_STAGE", "kind": "PORTABILITY",
         "statement": "The canonical software archive verifies, stages, and orients from itself.",
         "subject_root": anchor["archive_manifest_root"], "verifier": "AMCAS_SELF_STAGE_V1",
         "evidence_required": True, "applicability": "REQUIRED"},
        {"id": "NO_AUTHORITY", "kind": "ACCEPTANCE",
         "statement": "Every release artifact preserves the explicit authority ceiling.",
         "subject_root": root(BOUNDARY), "verifier": "AMCAS_AUTHORITY_CEILING_V1",
         "evidence_required": True, "applicability": "REQUIRED"},
    ]
    value["acceptance"] = [
        {"id": "RELEASE_EVIDENCE", "obligation": "CM1:QUALIFICATION_PASS",
         "evidence_schema": "mosaic.ucm.amcas.qualification.v0.1", "required": True}
    ]
    value["dependencies"] = [
        {"id": "PUBLISHED_UCM_V01", "kind": "TOOL", "required": True,
         "root": anchor["published_ucm_release_root"]},
        {"id": "BASELINE_CAPSULE", "kind": "CONTRACT", "required": True,
         "root": anchor["baseline_capsule_root"]},
    ]
    value["portability"]["profiles"] = ["CANONICAL_SOFTWARE", "CANONICAL_JOURNAL",
                                              "APPLICATION_INTEGRATION_KIT"]
    body = {key: deepcopy(item) for key, item in value.items() if key != "contract_root"}
    value["contract_root"] = root(body)
    return validate_contract(value)


def review_work_order(freeze: dict) -> bytes:
    return f"""# Joint independent review — UCM-AMCAS Integration Workbench c2

## Exact boundary

- Freeze root: `{freeze['freeze_root']}`
- Canonical software: `{freeze['software']['sha256']}`
- Canonical journal: `{freeze['journal']['sha256']}`
- Application kit: `{freeze['integration_kit']['sha256']}`
- Qualification: `{freeze['qualification_root']}`

## Review lanes

1. **Tier 0 / custody:** verify every handoff member, rebuild both canonical
   archives, stage the software with its own `STAGE.py`, and run `ucm orient`.
2. **Tier 1 / adversarial:** attack exact subject include/exclude policies,
   archive traversal and duplicate paths, control-plane semantic/effect
   collisions, replacement without exact equivalence, native/UCM correspondence
   row deletion and consistent reseal, Stage I1 missing and cross-swapped records,
   portfolio denominator and thread/application substitutions, CM1/CM2 ordering,
   obligation subjects,
   UCL/Tessera projection, native-proof routing, MosaicID challenge replay,
   journal truncation/reseal/idempotency/restart, all G1/G2/G3 ordering and
   cross-record links, report import, impact planning, archive path closure,
   and the INFORMATION_ONLY/NONE/A5-false/G0-closed ceiling.
3. **Tier 2 / qualification:** run one fresh cache-free qualification only when
   custody, attacks, source drift, platform uncertainty, or required policy
   triggers it. Preserve exact test identities and report skips explicitly.

The builder's evidence is engineering evidence, not independent review.
No verdict grants deployment authority. Native AOK/UGK authority was not bound
in the build session; all receipt claims say so explicitly.
""".encode("utf-8")


def _artifact(role: str, raw: bytes) -> dict:
    return {"role": role, "sha256": sha(raw), "bytes": len(raw)}


def build_skill_archive() -> bytes:
    base = ROOT / "skill/ucm-amcas-integration"
    payloads = {path.relative_to(base).as_posix(): path.read_bytes()
                for path in sorted(base.rglob("*"), key=lambda value: value.as_posix())
                if path.is_file()}
    return deterministic_zip(payloads, schema="mosaic.ucm.integration-skill.v0.1",
                             artifact_role="UCM_AMCAS_INTEGRATION_SKILL")


def build(qualification_path: Path, output: Path) -> dict:
    qualification = strict_loads(qualification_path.read_bytes())
    if qualification.get("status") != "PASS" or any(qualification.get(k) != 0
            for k in ("failures", "errors", "skips")):
        raise SystemExit("AMCAS_RELEASE_QUALIFICATION_INVALID")
    software, anchor = build_software_archive()
    if qualification.get("software_anchor") != anchor:
        raise SystemExit("AMCAS_RELEASE_SOFTWARE_ANCHOR_MISMATCH")
    control = self_control_plane()
    contract = self_contract(anchor, control)
    with tempfile.TemporaryDirectory(prefix="ucm-amcas-freeze-") as temp:
        campaign = IntegrationCampaign.create(Path(temp) / "campaign", contract)
        evidence = [qualification["qualification_root"], anchor["anchor_root"]]
        for index, obligation in enumerate(campaign.compiled()["obligations"]):
            campaign.disposition(obligation["id"], "PASS", evidence,
                                 event_id=f"freeze-disposition-{index:03d}")
        campaign.journal.append(event_id="freeze-test", event_type="TEST_RECORDED",
            actor={"kind": "SYSTEM", "mosaic_id": None, "session_id": None},
            payload={"qualification_root": qualification["qualification_root"],
                     "test_count": qualification["test_count"], "status": "PASS"})
        kit = build_integration_kit(campaign)
        ecosystem_kits: dict[str, bytes] = {}
        for template in sorted((ROOT / "integration-kits/templates").glob("*.integration.json")):
            profile = template.name.removesuffix(".integration.json")
            ecosystem_kits[profile] = build_integration_kit_from_contract(
                strict_loads(template.read_bytes()))
            verify_deterministic_zip(ecosystem_kits[profile],
                expected_schema="mosaic.ucm.integration-kit.v0.1",
                expected_role="APPLICATION_INTEGRATION_KIT")
        journal = export_journal_archive(campaign, software_anchor=anchor)
        verify_deterministic_zip(journal,
            expected_schema="mosaic.ucm.integration-journal-archive.v0.1",
            expected_role="CANONICAL_INTEGRATION_JOURNAL")
        verify_deterministic_zip(kit, expected_schema="mosaic.ucm.integration-kit.v0.1",
                                 expected_role="APPLICATION_INTEGRATION_KIT")
        report = build_report(campaign)
    roster = validate_roster(strict_loads(
        (ROOT / "examples/portfolio/MOSAIC-APPLICATIONS.json").read_bytes()))
    skill = build_skill_archive()
    freeze_body = {
        "schema": "mosaic.ucm.amcas.freeze-receipt.v0.1",
        "software": _artifact("CANONICAL_SOFTWARE", software),
        "software_anchor_root": anchor["anchor_root"],
        "journal": _artifact("CANONICAL_INTEGRATION_JOURNAL", journal),
        "integration_kit": _artifact("APPLICATION_INTEGRATION_KIT", kit),
        "integration_skill": _artifact("UCM_AMCAS_INTEGRATION_SKILL", skill),
        "control_plane_root": control["root"],
        "portfolio_root": roster["roster_root"],
        "ecosystem_kits": [
            {"profile": profile, **_artifact("APPLICATION_INTEGRATION_KIT", raw)}
            for profile, raw in sorted(ecosystem_kits.items())
        ],
        "qualification_root": qualification["qualification_root"],
        "contract_root": contract["contract_root"],
        "ir_root": report["ir_root"], "report_root": report["report_root"],
        "deterministic_rebuilds": 2, **BOUNDARY,
    }
    freeze = {**freeze_body, "freeze_root": root(freeze_body)}
    work_order = review_work_order(freeze)
    handoff_payloads = {
        "CANONICAL-SOFTWARE.zip": software,
        "CANONICAL-INTEGRATION-JOURNAL.zip": journal,
        "APPLICATION-INTEGRATION-KIT.zip": kit,
        **{f"ecosystem-kits/{profile}.zip": raw
           for profile, raw in sorted(ecosystem_kits.items())},
        "QUALIFICATION.json": canonical_bytes(qualification),
        "SOFTWARE-ANCHOR.json": canonical_bytes(anchor),
        "FREEZE-RECEIPT.json": canonical_bytes(freeze),
        "INTEGRATION-REPORT.json": canonical_bytes(report),
        "CONTROL-PLANE-DISPOSITION.json": canonical_bytes(control),
        "PORTFOLIO.json": canonical_bytes(roster),
        "UCM-AMCAS-INTEGRATION-SKILL.zip": skill,
        "REVIEW-WORK-ORDER.md": work_order,
        "VERIFY.py": (ROOT / "VERIFY.py").read_bytes(),
        "STAGE.py": (ROOT / "STAGE.py").read_bytes(),
    }
    handoff = deterministic_zip(handoff_payloads,
        schema="mosaic.ucm.amcas.independent-review-handoff.v0.1",
        artifact_role="INDEPENDENT_REVIEW_HANDOFF")
    verify_deterministic_zip(handoff,
        expected_schema="mosaic.ucm.amcas.independent-review-handoff.v0.1",
        expected_role="INDEPENDENT_REVIEW_HANDOFF")
    output.mkdir(parents=True, exist_ok=True)
    records = {
        "MOSAIC-UCM-AMCAS-CANONICAL-SOFTWARE-v0.1.zip": software,
        "MOSAIC-UCM-AMCAS-CANONICAL-JOURNAL-v0.1.zip": journal,
        "MOSAIC-UCM-AMCAS-APPLICATION-INTEGRATION-KIT-v0.1.zip": kit,
        "MOSAIC-UCM-AMCAS-INTEGRATION-SKILL-v0.1.zip": skill,
        **{f"MOSAIC-UCM-AMCAS-{profile}-KIT-v0.1.zip": raw
           for profile, raw in sorted(ecosystem_kits.items())},
        "MOSAIC-UCM-AMCAS-c2-INDEPENDENT-REVIEW-HANDOFF.zip": handoff,
        "FREEZE-RECEIPT.json": canonical_bytes(freeze),
        "INTEGRATION-REPORT.json": canonical_bytes(report),
        "REVIEW-WORK-ORDER.md": work_order,
    }
    for name, raw in records.items():
        write_new(output / name, raw)
    return {"status": "PASS", "freeze_root": freeze["freeze_root"],
            "handoff_sha256": sha(handoff),
            "artifacts": {name: {"sha256": sha(raw), "bytes": len(raw)}
                          for name, raw in records.items()}, **BOUNDARY}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    first = Path(tempfile.mkdtemp(prefix="ucm-amcas-freeze-a-"))
    second = Path(tempfile.mkdtemp(prefix="ucm-amcas-freeze-b-"))
    try:
        result_a = build(args.qualification, first)
        result_b = build(args.qualification, second)
        files_a = {p.relative_to(first).as_posix(): p.read_bytes() for p in first.rglob("*") if p.is_file()}
        files_b = {p.relative_to(second).as_posix(): p.read_bytes() for p in second.rglob("*") if p.is_file()}
        if files_a != files_b or result_a != result_b:
            raise SystemExit("AMCAS_RELEASE_NOT_DETERMINISTIC")
        if args.output.exists() and any(args.output.iterdir()):
            raise SystemExit("AMCAS_RELEASE_OUTPUT_NOT_EMPTY")
        args.output.mkdir(parents=True, exist_ok=True)
        for name, raw in files_a.items():
            write_new(args.output / name, raw)
        print(canonical_bytes(result_a).decode())
        return 0
    finally:
        shutil.rmtree(first, ignore_errors=True); shutil.rmtree(second, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())

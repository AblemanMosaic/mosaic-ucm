"""Build the rooted UCM-AMCAS campaign baseline and example contract."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root, strict_loads  # noqa: E402
from ucm.amcas import BOUNDARY, make_contract  # noqa: E402
from ucm.realization import validate_contract as validate_realization  # noqa: E402


PACKAGES = [
    ("P01", "Exact baseline and campaign charter"),
    ("P02", "Executable AMCAS and CM1/CM2 contract"),
    ("P03", "MosaicID user and session ceremony"),
    ("P04", "UCL and Tessera integration compilation"),
    ("P05", "UGK and THR governed operation gateway"),
    ("P06", "Durable integration campaign journal"),
    ("P07", "Project intelligence and autonomous planning"),
    ("P08", "Repair, test, and qualification control"),
    ("P09", "Human, agent, CLI, ABI, and progress surfaces"),
    ("P10", "Canonical software and journal archives"),
    ("P11", "Application pilots and integration kits"),
    ("P12", "Cross-session coordination skill"),
    ("P13", "Qualification, freeze, and reviewer handoff"),
]


def sealed(body: dict, field: str = "root") -> dict:
    return {**body, field: root(body)}


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_bytes(value)
    if path.exists() and path.read_bytes() != raw:
        raise SystemExit(f"refusing drift at {path}")
    path.write_bytes(raw)


def main() -> int:
    baseline = sealed({
        "schema": "mosaic.ucm.amcas.baseline-capsule.v0.1",
        "program_id": "MOSAIC_UCM_AMCAS_INTEGRATION_WORKBENCH_C1",
        "published_ucm": {
            "git_commit": "51733b644fa3c43b5b7ef0ee558ec2f9a3b33891",
            "release_root": "80f1f2f8a657a0c61fa46f7edd809f9059901fbbd7e661d2b6885d19974c187c",
            "qualification_root": "301e9aa48eff72d087cc77eeaa505307fb728de8ec1fae8dae9335ecc6485015",
            "source_manifest_root": "5f44ebcd4594297814a51d3b52abcd7a7c44d43f55b44414c826b86898f1418f",
            "standing": "INFORMATION_ONLY",
        },
        "frozen_predecessor": {
            "source_root": "16bd76dca7477bb46c861347b1995585341c69adac3e422851a76fa840b97cf9",
            "qualification_root": "d94874ea5bdd97691298c6102782430b7f2a5da906546461056dac99e5fef5b8",
            "cold_boot_sha256": "57fd3f59283322d49a93b84dc6871b6439bca5d15c8943e364f3d1a02acbcf41",
        },
        "amcas_standard_candidate": {
            "standard_root": "160750718aaa7ee7dd26ee7148e89c676ce3edb89990b5c7c2ac91d4dde66480",
            "claim_ceiling": "PROVISIONAL_SOURCE_BOUND_PORTABLE_STANDARD_AND_REFERENCE_APPLICATION_CORRESPONDENCE_ONLY",
            "canonical_adoption": False,
        },
        "mosaic_id_passport_candidate": {
            "archive_sha256": "9750cc5d4fb5b6b98e039523d0165a240d162061e2c7667757f8c195b55b59be",
            "source_sha256": "4be83ce535884d32300e5b77dff46c737688ee73e64a3c2d016573ecb100c59f",
            "independent_review": "NOT_PERFORMED",
        },
        "native_aok_orientation": "REFUSED_CAPABILITY_LATTICE_ABSENT",
        "do_not_rebuild": [
            "UCL_LANGUAGE", "TESSERA_COMPILATION", "NATIVE_PROOF",
            "REALIZATION_SPACE", "COURT_EXECUTION", "QUALIFICATION_CONTROL",
            "PROJECT_INTELLIGENCE", "AUTONOMOUS_PROJECT_MANAGER", "PORTABLE_BOOTSTRAP",
        ],
        **BOUNDARY,
    }, "capsule_root")
    charter = sealed({
        "schema": "mosaic.ucm.amcas.campaign-charter.v0.1",
        "program_id": baseline["program_id"], "baseline_capsule_root": baseline["capsule_root"],
        "objective": "Build a portable UCM-governed AMCAS integration workbench and canonical journal.",
        "fixed_package_denominator": len(PACKAGES),
        "packages": [{"id": package_id, "name": name} for package_id, name in PACKAGES],
        "effect_ceiling": "NONE", "standing_ceiling": "INFORMATION_ONLY",
        "required_outputs": ["CANONICAL_SOFTWARE_ARCHIVE", "CANONICAL_INTEGRATION_JOURNAL_ARCHIVE",
                             "APPLICATION_INTEGRATION_KITS", "INTEGRATION_REPORT",
                             "REVIEW_HANDOFF", "UCM_AMCAS_INTEGRATION_SKILL"],
        "qualification_rule": "TARGETED_DURING_CONSTRUCTION_THEN_ONE_CACHE_FREE_FULL_RUN",
        "review_rule": "ONE_JOINT_INDEPENDENT_REVIEW_AFTER_INTEGRATED_FREEZE",
        **BOUNDARY,
    }, "charter_root")
    ledger = sealed({
        "schema": "mosaic.ucm.amcas.program-ledger.v0.1",
        "program_id": baseline["program_id"], "baseline_capsule_root": baseline["capsule_root"],
        "charter_root": charter["charter_root"], "phase": "CUMULATIVE_INTEGRATION",
        "packages": [{"id": package_id,
                      "status": ("BASELINE_ESTABLISHED" if package_id == "P01"
                                 else "QUALIFICATION_PENDING" if package_id == "P13"
                                 else "CONSTRUCTED_TARGETED_PASS"),
                      "accepted": False} for package_id, _ in PACKAGES],
        "accepted_closures": [], "unresolved_custody": [
            "NATIVE_AOK_CAPABILITY_LATTICE", "NATIVE_UGK_RECEIPT_VERIFIER",
            "INDEPENDENT_REVIEW", "MOSAICOS_DEEP_INTEGRATION_EVIDENCE"],
        "next_action": "RUN_ONE_CACHE_FREE_FULL_QUALIFICATION_THEN_FREEZE",
        **BOUNDARY,
    }, "ledger_root")
    write(ROOT / "campaign" / "BASELINE-CAPSULE.json", baseline)
    write(ROOT / "campaign" / "CAMPAIGN-CHARTER.json", charter)
    write(ROOT / "campaign" / "PROGRAM-LEDGER.json", ledger)

    realization = strict_loads((ROOT / "examples" / "realization" /
                                "portable-agent-environment.json").read_bytes())
    realization = validate_realization(realization)
    contract = make_contract(
        integration_id="EXAMPLE.PORTABLE_AGENT.INTEGRATION",
        application={"id": "EXAMPLE.PORTABLE_AGENT", "name": "Portable Agent Example", "version": "0.1"},
        subject={"source_root": "1" * 64, "manifest_root": "2" * 64,
                 "path_policy": "PORTABLE_POSIX_RELATIVE_V1"},
        identities={"user_required": False, "agent_required": False,
                    "session_distinct": True, "possession_required": False,
                    "delegation_required": False,
                    "jurisdiction": {"namespace_id": "EXAMPLE.PORTABLE",
                                     "universe_root": None, "epoch_id": None,
                                     "semantic_namespace": None}},
        cm1={"membership_policy": "ALL_APPLICABLE_REQUIREMENTS_PASS",
             "requirements": [
                 {"id": "SOURCE_BOUND", "kind": "EVIDENCE",
                  "statement": "The integration report names the exact application source.",
                  "subject_root": "1" * 64, "verifier": "AMCAS_SOURCE_BINDING_V1",
                  "evidence_required": True, "applicability": "REQUIRED"},
                 {"id": "NO_AUTHORITY", "kind": "ACCEPTANCE",
                  "statement": "No integration record grants operational authority.",
                  "subject_root": root(BOUNDARY), "verifier": "AMCAS_AUTHORITY_CEILING_V1",
                  "evidence_required": True, "applicability": "REQUIRED"}]},
        cm2={"selection_policy": "CM1_THEN_CM2_LEXICOGRAPHIC",
             "preferences": [{"id": "SMALL_ARCHIVE", "objective": "Prefer smaller portable artifacts.",
                              "priority": 1, "metric": "ARTIFACT_BYTES", "direction": "MINIMIZE"}]},
        capabilities=[{"id": "ORIENT", "route": "ucm.orient", "effect_class": "PURE_COMPUTATION",
                       "required": True, "request_schema": "mosaic.ucm.empty.v0.1",
                       "result_schema": "mosaic.ucm.orientation.v0.1"}],
        effects=[],
        dependencies=[{"id": "UCM_V01", "kind": "TOOL",
                       "root": baseline["published_ucm"]["release_root"], "required": True}],
        acceptance=[{"id": "SOURCE_EVIDENCE", "obligation": "CM1:SOURCE_BOUND",
                     "evidence_schema": "mosaic.source-binding.v0.1", "required": True}],
        portability={"profiles": ["SESSION_KIT", "JOURNAL"],
                     "journal_export_required": True, "offline_closure_required": True},
        reporting={"required_sections": ["requirements", "capabilities", "operations",
                                         "findings", "limitations", "portable_artifacts"],
                   "progress_channel": "NONSEMANTIC_JSONL_V1"},
        integration_boundary={
            "semantic_authority": "EXAMPLE.PORTABLE_AGENT.NATIVE",
            "effect_executor": "EXAMPLE.PORTABLE_AGENT.NATIVE",
            "identity_binding_status": "UNBOUND",
            "jurisdiction_binding_status": "UNBOUND",
            "gate_namespace": "UCM.INTEGRATION",
            "control_plane_root": root({
                "schema": "mosaic.ucm.control-plane-disposition.v0.1",
                "application_id": "EXAMPLE.PORTABLE_AGENT",
                "binding_status": "UNBOUND_TEMPLATE",
            }),
        },
        realization_contract=realization,
    )
    write(ROOT / "examples" / "amcas" / "portable-agent.integration.json", contract)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Build the governed successor program from the accepted feedback register."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import canonical_bytes, root
from ucm.amcas import compile_contract, make_contract
from ucm.journal import CampaignJournal
from ucm.realization import validate_contract
from ucm.thr_cas import build_thr_manifest


BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}
PREDECESSOR = {
    "git_commit": "6944a16",
    "release_identity_root": "6420109fe012eef6b921b7a347db0826b706c613d1a0654cd222fd7cef646501",
    "canonical_software_sha256": "7b5de47c3fad676943a7073732cf55dd9e8e39d4438b5ce0c02a366fe0760667",
    "maturity_source_root": "30358687923d617509e986844f2d97c734a58bbe3ad8073db80303660f634f4e",
    "source_manifest_root": "18709f8570b9a8465a5ff72aa27295293a33d11711778b4e2ec8cf73960cafc7",
}


REQUIREMENTS = [
    ("MR-001", "AUTHORING", "Scaffold realization and AMCAS contracts from constrained templates."),
    ("MR-002", "AUTHORING", "Diagnose structural completeness before roots are finalized."),
    ("MR-003", "AUTHORING", "Distinguish schema-valid drafts from campaign-ready contracts."),
    ("MR-004", "AUTHORING", "Provide prose-to-contract examples without replacing canonical JSON."),
    ("MR-005", "AGENT", "Expose a thin strict agent tool adapter over active surfaces only."),
    ("MR-006", "AGENT", "Pin capability and profile registries in every agent sidecar."),
    ("MR-007", "AGENT", "Specify the orient-bind-validate-plan-gate-export agent loop."),
    ("MR-008", "AGENT", "Separate exact tool results and journal roots from chat memory."),
    ("MR-009", "EXPLAIN", "Emit structured constraint evaluation traces."),
    ("MR-010", "EXPLAIN", "Provide deterministic human-readable trace projections."),
    ("MR-011", "EXPLAIN", "Compare two configurations with constraint-level reasons."),
    ("MR-012", "EXPLAIN", "Support compact and expanded local verbosity without changing evidence."),
    ("MR-013", "EVOLUTION", "Document safe contract supersession and migration."),
    ("MR-014", "EVOLUTION", "Classify old contracts as supported, migration-needed, or rejected."),
    ("MR-015", "EVOLUTION", "Define user-contract repair deltas and preserved invariants."),
    ("MR-016", "EVOLUTION", "Keep old journal events valid under their pinned contract roots."),
    ("MR-017", "DOCS", "Document when each active surface is called and why it refuses."),
    ("MR-018", "DOCS", "Provide one minimal request/result and one misuse per active surface."),
    ("MR-019", "DOCS", "Provide a job-oriented operator playbook."),
    ("MR-020", "DOCS", "Keep progress, evidence, authority, and chat summaries distinct."),
    ("MR-021", "EVIDENCE", "Bind ordinary test, typecheck, lint, coverage, SBOM, and CI artifacts."),
    ("MR-022", "EVIDENCE", "Specify custom-verifier obligations and pinning."),
    ("MR-023", "EVIDENCE", "Demonstrate hash-and-presence checking without semantic overclaim."),
    ("MR-024", "RECOVERY", "Demonstrate UNCERTAIN recovery without redispatch."),
    ("MR-025", "RECOVERY", "Demonstrate expected-journal-head refusal."),
    ("MR-026", "RECOVERY", "Demonstrate session export, import, and continuation boundaries."),
    ("MR-027", "RECOVERY", "Publish recovery anti-patterns."),
    ("MR-028", "ABI", "Publish a machine-readable ABI and surface stability charter."),
    ("MR-029", "CANONICAL", "Publish canonicalization edge vectors and one canonical function rule."),
    ("MR-030", "WORKSPACE", "Specify workspace layout, locks, heads, and safe deletion."),
    ("MR-031", "WORKSPACE", "Require custody checks and expected head before stale-lock recovery."),
    ("MR-032", "TIME", "Publish caller-time, freshness, skew, and boundary rules."),
    ("MR-033", "IDEMPOTENCY", "Publish idempotency key generation, scope, retention, and replay rules."),
    ("MR-034", "BUDGET", "Provide budget refusal and rollback-required/forbidden examples."),
    ("MR-035", "JOURNAL", "Provide deterministic journal diff and campaign summary tools."),
    ("MR-036", "ROBUSTNESS", "Fuzz parsers and verifiers toward typed refusal."),
    ("MR-037", "PERFORMANCE", "Define exact incremental revalidation or bounded full recomputation."),
    ("MR-038", "POLICY", "Publish hash-pinned shared policy packs and conflict checks."),
    ("MR-039", "PORTABILITY", "Publish language-neutral formats and non-Python golden vectors."),
    ("MR-040", "CLI", "Publish stable CLI exit codes."),
    ("MR-041", "CLI", "Generate shell completions from the capability registry."),
    ("MR-042", "PRESENTATION", "Pretty-print receipts and reports as non-authoritative projections."),
    ("MR-043", "DIFF", "Classify AMCAS and realization changes by semantic domain."),
    ("MR-044", "APPROVAL", "Verify an optional external human approval receipt when required."),
    ("MR-045", "STORAGE", "Type disk-full and quota failures without claiming success."),
    ("MR-046", "ENVIRONMENT", "Allow-list UCM environment variables and support strict refusal."),
    ("MR-047", "PORTABILITY", "Exercise Windows and POSIX path, lock, and atomic-replace semantics."),
    ("MR-048", "EXPLAIN", "Emit a stable EXPLAIN_SELECTION artifact."),
    ("MR-049", "AUTHORITY", "Keep human approval external and non-granting."),
    ("MR-050", "THR", "Keep H_s, H_c, H_m, H_j, and H_r commitments separate."),
    ("MR-051", "CM1", "Make all safety and claim boundaries hard admissibility requirements."),
    ("MR-052", "CM2", "Use preference ordering only after CM1 membership passes."),
    ("MR-053", "TEST", "Use targeted construction tests and one final cache-free qualification."),
    ("MR-054", "REVIEW", "Reserve adversarial execution for the operator kit and independent reviewer."),
    ("MR-055", "PACKAGE", "Build deterministic software, journal, review, and operator artifacts."),
    ("MR-056", "AUTHORITY", "Remain INFORMATION_ONLY, NONE, real A5 false, and G0 closed."),
]


def sealed(body: dict, field: str) -> dict:
    return {**body, field: root(body)}


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")


def realization_contract() -> dict:
    axes = []
    constraints = []
    for batch in ("PUBLIC_BOUNDARY", "AUTHORING_EXPLANATION", "OPERATIONAL_CUSTODY",
                  "EVIDENCE_AGENT_USABILITY", "PORTABILITY_ROBUSTNESS"):
        axes.append({"id": batch, "label": batch.replace("_", " ").title(),
                     "value_type": "BOOLEAN", "domain": {}, "default": True,
                     "ownership": "AUTHORIAL", "mutability": "FROZEN",
                     "continuity": "DISCRETE", "authority_effect": "NONE"})
        constraints.append({"id": f"{batch}_REQUIRED", "kind": "INVARIANT",
                            "severity": "HARD", "operator": "EQUALS",
                            "terms": {"axis": batch, "value": True},
                            "explanation": f"The {batch} batch is required for the successor.",
                            "refusal_code": f"{batch}_INCOMPLETE"})
    body = {
        "schema": "mosaic.realization-space-contract.v0.1",
        "contract_id": "UCM.MATURITY_EVOLUTION_SUCCESSOR",
        "contract_version": "0.1.0-candidate",
        "description": "Governed realization space for the consolidated UCM maturity successor.",
        "subject": {"subject_id": "MOSAIC.UCM.V0_1", "subject_schema": "mosaic.ucm.release.v0.1",
                    "authority_owner": "ABLEMAN_MOSAIC",
                    "source_roots": [f"sha256:{PREDECESSOR['maturity_source_root']}"],
                    "preserved_identity": ["V0_1_COMPATIBILITY", "FROZEN_HISTORY", "AUTHORITY_CEILING"],
                    "forbidden_overrides": ["FROZEN_PREDECESSOR", "NATIVE_APPLICATION_AUTHORITY"]},
        "possibility": {"intended_variation": ["NEW_NON_GRANTING_AUTHORING_AND_VERIFICATION_SURFACES"],
                        "excluded_claims": ["PRODUCTION_AUTHORITY", "APPLICATION_AUTHORITY", "INDEPENDENT_REVIEW"]},
        "axes": axes, "constraints": constraints,
        "capabilities": ["VALIDATE", "COMPARE", "EXPLAIN", "RECEIPT", "TRACE"],
        "selection": {"default_policy": "EXACT_DEFAULTS", "fallback_policy": "REFUSE",
                      "seed_required_for_non_unique": False},
        "lowering": {"targets": [{"target_id": "PYTHON_PORTABLE", "runtime_family": "PYTHON",
                                    "adapter_version": "0.1.0", "required_capabilities": [],
                                    "optional_capabilities": [],
                                    "preservation_criteria": ["V0_1_COMPATIBILITY", "AUTHORITY_CEILING"],
                                    "known_losses": [], "fallbacks": []}],
                     "allowed_results": ["EXACT", "REFUSED"]},
        "evidence": {"required_roots": ["PREDECESSOR", "SOURCE", "QUALIFICATION", "JOURNAL"],
                     "required_fields": ["standing", "authority_effect", "real_a5", "g0"],
                     "non_claims": ["NOT_INDEPENDENT_REVIEW", "NOT_DEPLOYMENT_AUTHORITY"]},
        "revision": {"predecessor_root": PREDECESSOR["release_identity_root"],
                     "migration": "ADDITIVE_PUBLIC_SURFACES_WITH_FROZEN_V0_1_COMPATIBILITY",
                     "unresolved_questions": ["OPERATOR_TIER1_PENDING", "INDEPENDENT_REVIEW_PENDING"]},
        "authority": {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
                      "self_admission": False, "release_gate": False,
                      "track_a_dependency": "NONE", "claim_boundary": "CANDIDATE_ONLY"},
    }
    return validate_contract({**body, "root": root(body)})


def build() -> None:
    folder = ROOT / "program" / "maturity-evolution"
    requirements = [{"id": identifier, "area": area, "statement": statement,
                     "cm": "CM2" if area in {"PRESENTATION", "PERFORMANCE"} else "CM1",
                     "status": "PLANNED"} for identifier, area, statement in REQUIREMENTS]
    intake_body = {"schema": "mosaic.ucm.feedback-intake.v0.1",
                   "source": "USER_CHAT_FEEDBACK_DERIVED_REGISTER",
                   "not_a_verbatim_transcript": True,
                   "fixed_denominator": len(requirements),
                   "requirements": requirements, "predecessor": PREDECESSOR, **BOUNDARY}
    intake = sealed(intake_body, "intake_root")
    rsc = realization_contract()
    amcas = make_contract(
        integration_id="MOSAIC.UCM.MATURITY_EVOLUTION",
        application={"id": "MOSAIC.UCM", "name": "Mosaic UCM", "version": "v0.1-successor"},
        subject={"source_root": PREDECESSOR["maturity_source_root"],
                 "manifest_root": PREDECESSOR["source_manifest_root"],
                 "path_policy": "PORTABLE_POSIX_RELATIVE_V1"},
        identities={"user_required": False, "agent_required": False,
                    "jurisdiction": {"namespace_id": "MOSAIC.UCM", "universe_root": None,
                                     "epoch_id": None, "semantic_namespace": None},
                    "session_distinct": True, "possession_required": False,
                    "delegation_required": False},
        cm1={"membership_policy": "ALL_APPLICABLE_REQUIREMENTS_PASS",
             "requirements": [{"id": row["id"], "kind": "ACCEPTANCE",
                               "statement": row["statement"],
                               "subject_root": PREDECESSOR["maturity_source_root"],
                               "verifier": "UCM_MATURITY_REQUIREMENT_V1",
                               "evidence_required": True, "applicability": "REQUIRED"}
                              for row in requirements if row["cm"] == "CM1"]},
        cm2={"selection_policy": "CM1_THEN_CM2_LEXICOGRAPHIC",
             "preferences": [{"id": "MINIMIZE_ACTIVE_SURFACES",
                              "objective": "Prefer fewer active mechanisms after CM1 passes.",
                              "priority": 100, "metric": "ACTIVE_SURFACE_COUNT",
                              "direction": "MINIMIZE"}]},
        capabilities=[], effects=[],
        dependencies=[{"id": "FROZEN_UCM_V0_1", "kind": "SOURCE",
                       "root": PREDECESSOR["release_identity_root"], "required": True}],
        acceptance=[{"id": "FIXED_DENOMINATOR", "obligation": "ALL_CM1_REQUIREMENTS",
                     "evidence_schema": "mosaic.ucm.requirement-register.v0.1", "required": True}],
        portability={"profiles": ["SOFTWARE", "JOURNAL", "REVIEW", "OPERATOR_TIER1"],
                     "journal_export_required": True, "offline_closure_required": True},
        reporting={"required_sections": ["requirements", "capabilities", "operations",
                                         "findings", "limitations", "portable_artifacts"],
                   "progress_channel": "NONSEMANTIC_JSONL_V1"},
        realization_contract=rsc,
        integration_boundary={"semantic_authority": "MOSAIC.UCM.NATIVE",
                              "effect_executor": "MOSAIC.UCM.NATIVE",
                              "identity_binding_status": "UNBOUND",
                              "jurisdiction_binding_status": "UNBOUND",
                              "gate_namespace": "UCM.INTEGRATION",
                              "control_plane_root": intake["intake_root"]})
    ir = compile_contract(amcas)
    charter_body = {
        "schema": "mosaic.ucm.maturity-evolution-charter.v0.1",
        "program_id": "UCM_MATURITY_EVOLUTION_C1",
        "predecessor": PREDECESSOR,
        "feedback_intake_root": intake["intake_root"],
        "fixed_denominator": len(requirements),
        "amcas_contract_root": amcas["contract_root"], "ir_root": ir["ir_root"],
        "realization_contract_root": rsc["root"],
        "construction_policy": "TARGETED_TESTS_THEN_ONE_CACHE_FREE_QUALIFICATION",
        "review_policy": "OPERATOR_RUN_TIER1_THEN_INDEPENDENT_REVIEW_AT_BOUNDARY",
        "adversarial_execution_owner": "USER_OR_INDEPENDENT_REVIEWER",
        **BOUNDARY,
    }
    charter = sealed(charter_body, "charter_root")
    package_body = {
        "schema": "mosaic.ucm.governed-successor-work-package.v0.1",
        "charter_root": charter["charter_root"],
        "batches": [
            {"id": "B1", "name": "STABLE_PUBLIC_BOUNDARY", "requirement_ids": [f"MR-{n:03}" for n in range(28, 33)] + ["MR-040", "MR-041", "MR-046"]},
            {"id": "B2", "name": "AUTHORING_AND_EXPLANATION", "requirement_ids": [f"MR-{n:03}" for n in range(1, 17)] + ["MR-038", "MR-043", "MR-048"]},
            {"id": "B3", "name": "OPERATIONAL_CUSTODY", "requirement_ids": [f"MR-{n:03}" for n in range(24, 35)] + ["MR-044", "MR-045", "MR-049"]},
            {"id": "B4", "name": "EVIDENCE_AGENT_USABILITY", "requirement_ids": [f"MR-{n:03}" for n in range(5, 9)] + [f"MR-{n:03}" for n in range(17, 24)] + ["MR-035", "MR-042"]},
            {"id": "B5", "name": "PORTABILITY_AND_ROBUSTNESS", "requirement_ids": ["MR-029", "MR-036", "MR-037", "MR-039", "MR-047", "MR-050", "MR-051", "MR-052", "MR-053", "MR-054", "MR-055", "MR-056"]},
        ],
        "changed_path_prefixes": ["src/ucm/", "tests/", "docs/", "spec/", "examples/",
                                  "policy-packs/", "conformance/", "tools/", "program/maturity-evolution/"],
        "status": "AUTHORIZED_FOR_INFORMATION_ONLY_CONSTRUCTION",
        **BOUNDARY,
    }
    package = sealed(package_body, "work_package_root")
    artifacts = {"FEEDBACK-INTAKE.json": canonical_bytes(intake),
                 "REALIZATION-CONTRACT.json": canonical_bytes(rsc),
                 "AMCAS-CONTRACT.json": canonical_bytes(amcas),
                 "INTEGRATION-IR.json": canonical_bytes(ir),
                 "CAMPAIGN-CHARTER.json": canonical_bytes(charter),
                 "WORK-PACKAGE.json": canonical_bytes(package)}
    thr = build_thr_manifest(
        application_id="MOSAIC.UCM.MATURITY_EVOLUTION",
        payloads=artifacts,
        meaning={"program": "UCM_MATURITY_EVOLUTION_C1", "fixed_denominator": 56},
        admissibility={"amcas_contract_root": amcas["contract_root"],
                       "realization_contract_root": rsc["root"]},
        locality={"jurisdiction": "UNBOUND", "workspace": "PUBLIC_UCM_SUCCESSOR"},
        receipts={"charter_root": charter["charter_root"],
                  "work_package_root": package["work_package_root"]})
    for name, raw in artifacts.items():
        path = folder / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw + b"\n")
    write(folder / "THR-MANIFEST.json", thr)
    journal_dir = folder / "journal"
    if not journal_dir.exists():
        journal = CampaignJournal(journal_dir); journal.initialize()
        actor = {"kind": "SYSTEM", "mosaic_id": None, "session_id": None}
        journal.append(event_id="maturity-evolution:created", event_type="CAMPAIGN_CREATED",
                       actor=actor, payload={"charter_root": charter["charter_root"],
                                             "fixed_denominator": 56})
        journal.append(event_id="maturity-evolution:baseline", event_type="BASELINE_BOUND",
                       actor=actor, payload=PREDECESSOR)
        journal.append(event_id="maturity-evolution:contract", event_type="CONTRACT_COMPILED",
                       actor=actor, payload={"contract_root": amcas["contract_root"],
                                             "ir_root": ir["ir_root"]})
        journal.append(event_id="maturity-evolution:work-package", event_type="ARTIFACT_RECORDED",
                       actor=actor, payload={"work_package_root": package["work_package_root"]})


if __name__ == "__main__":
    build()

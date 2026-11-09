"""Build the governed UCM public vocabulary and its human projections.

The registry is authoritative for token expansion, status, and UCM relationship.
The Markdown files are deterministic views for humans.  This builder deliberately
keeps unresolved names unresolved rather than selecting a plausible expansion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
# Direct execution places ``tools/`` first, where ``tools/ucm.py`` would
# otherwise shadow the actual ``src/ucm`` package.  Keep the documented
# ``python tools/build_public_vocabulary.py`` entry point deterministic even
# when PYTHONPATH already mentions ``src`` later in the search path.
if str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

from ucm.system import SYSTEMS  # noqa: E402
from ucm.pippi_work_units import (  # noqa: E402
    assess_work_unit_outcome,
    build_acceptance_case,
    build_work_selection,
    build_work_unit_state,
)
from ucm.program_history import check_frozen_program_directory  # noqa: E402


BOUNDARY = {
    "standing": "INFORMATION_ONLY",
    "authority_effect": "NONE",
    "real_a5": False,
    "g0": "CLOSED",
}

PREDECESSOR_SOURCE_ROOT = "49a6a386c8552ff97d825625f9d1f90a646d2eeaefc04768516076d7344894cc"
CCP_SOURCE_ROOT = "9a38419d655b9306c7216554081a6c869e12c0dcab1e08b961b8d645115e985e"

RELATIONSHIPS = {
    "IMPLEMENTED_IN_UCM",
    "EXTERNAL_BOUND",
    "ADAPTER_ONLY",
    "PARTIAL_COMPATIBILITY_PROJECTION",
    "RESEARCH_PROVISIONAL",
    "HISTORICAL_VARIANT",
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def root(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def entry(token: str, expansion: str | None, role: str, kind: str,
          relationship: str, standing: str, source: str, *,
          variants: list[str] | None = None,
          nonclaims: list[str] | None = None) -> dict[str, Any]:
    body = {
        "token": token,
        "canonical_expansion": expansion,
        "expansion_variants": variants or [],
        "plain_role": role,
        "object_kind": kind,
        "relationship_to_ucm": relationship,
        "standing": standing,
        "defining_source": source,
        "nonclaims": nonclaims or [],
    }
    return {**body, "entry_root": root(body)}


ENTRIES = [
    entry("UCM", "Universal Constitutional Machine", "Portable substrate for deterministic constitutional computation.", "PRODUCT", "IMPLEMENTED_IN_UCM", "UCM_V0_1_CANONICAL", "README.md"),
    entry("UCL", "Universal Constitutional Language", "Deterministic language for governed constitutional programs.", "LANGUAGE", "IMPLEMENTED_IN_UCM", "UCM_V0_1_CANONICAL", "src/ucm/system.py"),
    entry("AMCAS", "Ableman Mosaic Constitutional Application Specification", "Application constitution and integration contract projected into UCM obligations and preferences.", "SPECIFICATION", "IMPLEMENTED_IN_UCM", "USER_CONFIRMED_2026_11_05", "USER_RULING:2026-11-05", nonclaims=["AMCAS compilation is not application admission or execution authority"]),
    entry("CCP", None, "Source-bound curation and point-of-use admissibility construction program imported through CCP-JM.", "CONSTRUCTION_PROGRAM", "PARTIAL_COMPATIBILITY_PROJECTION", "NATIVE_PROGRAM_BOUND_PRODUCT_INCOMPLETE", "qualification/inputs/ccp-jm/CCP_JM_PIPELINE_v0_1_r001.zip", nonclaims=["No expansion is selected because the supplied controlling packet does not define one", "The native program binding is not a qualified CCP runtime or an authority grant"]),
    entry("CHC", "Cryptographic Homological Compilation", "External architecture that separates state identity, typed semantic identity, and policy-relative admissibility.", "ADMISSIBILITY_ARCHITECTURE", "EXTERNAL_BOUND", "SOURCE_BOUND_PROFILE_UNRESOLVED", "qualification/inputs/ccp-jm/CCP_JM_PIPELINE_v0_1_r001.zip", nonclaims=["CHC H_m is not UCM THR H_m", "CHC binds attestations about meaning; it does not prove their truth", "The governing CHC wire profile remains separately qualified"]),
    entry("P/PPI", "Project/Process Pipeline Interface", "Local project and process governance hub that coordinates Pippi, journals, reviews, and work selection.", "PRODUCT_SURFACE", "IMPLEMENTED_IN_UCM", "UCM_V0_1_CANONICAL", "docs/PIPPI-GLOBAL-HUB.md"),
    entry("THR", "Three Hash Rule", "Commitment discipline that keeps state, admissibility, meaning, locality, and receipt identity separately addressable.", "COMMITMENT_DISCIPLINE", "IMPLEMENTED_IN_UCM", "UCM_V0_1_CANONICAL", "src/ucm/thr_cas.py"),
    entry("DKN", "Distributed Knowledge Network", "Public identity and locality namespace used for portable, storage-independent binding.", "IDENTITY_NAMESPACE", "EXTERNAL_BOUND", "SOURCE_DEFINED", "docs/MOSAIC-ID-SESSIONS.md", nonclaims=["A DKN address is not an authority grant"]),
    entry("UGK", "Universal Governance Kernel", "External governance kernel whose separately rooted reports and HeadlessRunner receipts can be bound by UCM.", "EXTERNAL_SYSTEM", "EXTERNAL_BOUND", "SOURCE_DEFINED", "docs/CONSTITUTIONAL-INTEGRATION-RUNTIME.md", nonclaims=["UCM does not claim to contain or replace the canonical UGK implementation"]),
    entry("AOK", "Agentic Orchestration Kernel", "External orchestration and courthouse system integrated through bounded workflow and result contracts.", "EXTERNAL_SYSTEM", "EXTERNAL_BOUND", "SOURCE_DEFINED", "docs/COURTHOUSE-VNEXT-WORKFLOW-IR.md"),
    entry("ESA", "Epistemic Situational Awareness", "System-level orientation to current epistemic conditions, stakes, admissible continuation, refusal, and stopping.", "CONTROL_PROPERTY", "ADAPTER_ONLY", "SOURCE_DEFINED", "EXTERNAL_CORPUS:Epistemic Situational Awareness"),
    entry("SRSA", "Semantic Reactor Situational Awareness", "Governance-legibility instrumentation for semantic-reactor closure, drift, authority topology, and missing evidence.", "CONTROL_PROPERTY", "ADAPTER_ONLY", "REVIEWED_PROVISIONAL", "docs/CONSTITUTIONAL-INTEGRATION-RUNTIME.md"),
    entry("COP", "Constitutional Observability Platform", "External observability discipline for process state, evidence, and presentation fidelity.", "EXTERNAL_SYSTEM", "ADAPTER_ONLY", "SOURCE_DEFINED", "EXTERNAL_CORPUS:Constitutional Observability Platform"),
    entry("EVS-EVENT", "Event Evidence Stream", "Native event-evidence protocol retained as a distinct jurisdiction.", "NATIVE_PROTOCOL", "ADAPTER_ONLY", "UCM_V0_1_BOUND_PROTOCOL", "docs/CONSTITUTIONAL-INTEGRATION-RUNTIME.md"),
    entry("EVS-VERIFY", "Evidence Verification Subsystem", "Native evidence-verification protocol retained separately from the event stream.", "NATIVE_PROTOCOL", "ADAPTER_ONLY", "UCM_V0_1_BOUND_PROTOCOL", "docs/CONSTITUTIONAL-INTEGRATION-RUNTIME.md", nonclaims=["EVS-EVENT and EVS-VERIFY are not interchangeable"]),
    entry("GOORRT", "Governed Object–Operation–Realization Representation Triad", "Scaffold that keeps object semantics, operation semantics, and computational realization distinct while binding correspondence.", "REPRESENTATION_FRAMEWORK", "RESEARCH_PROVISIONAL", "SOURCE_DEFINED", "EXTERNAL_CORPUS:GOORRT"),
    entry("GOML", "Governed Object/Model Language", "Represents governed objects, identity, semantics, and state.", "REPRESENTATION_LANGUAGE", "PARTIAL_COMPATIBILITY_PROJECTION", "SOURCE_DEFINED", "EXTERNAL_CORPUS:GOORRT"),
    entry("GSOL", "Governed Semantic Operation Language", "Represents governed operations, authority, transitions, and refusals.", "REPRESENTATION_LANGUAGE", "PARTIAL_COMPATIBILITY_PROJECTION", "SOURCE_DEFINED", "EXTERNAL_CORPUS:GOORRT"),
    entry("MCIR", None, "Canonical computational realization representation used to bind governed structure to runtime evidence.", "INTERMEDIATE_REPRESENTATION", "PARTIAL_COMPATIBILITY_PROJECTION", "EXPANSION_VARIANT_UNRESOLVED", "EXTERNAL_CORPUS:MCIR_AND_JNANA", variants=["Meta-Compilation Intermediate Representation", "Mosaic Canonical Intermediate Representation"], nonclaims=["The expansion variants are not silently merged or adjudicated here"]),
    entry("MCRM", None, "Comparison regime for witnessed source, binary, runtime, and semantic realizations; its strongest honest result is bounded correspondence.", "COMPARISON_REGIME", "RESEARCH_PROVISIONAL", "EXPANSION_PENDING_SOURCE_ADJUDICATION", "EXTERNAL_CORPUS:GOORRT_AND_MCIR_ROADMAP", variants=["Machine Code Realization Mining (reported historical expansion)"], nonclaims=["MCRM is not a fourth canonical representation family", "MCRM comparison is not unqualified equivalence"]),
    entry("HLIR", "Human-Legible Intermediate Representation", "Proposal-layer representation that makes intent and authority legible before canonical machine lowering.", "INTERMEDIATE_REPRESENTATION", "RESEARCH_PROVISIONAL", "SOURCE_DEFINED", "EXTERNAL_CORPUS:Human-Legible Intermediate Representation"),
    entry("GCML", None, "Governed machine-facing decision language; exact expansion remains variant-bound.", "LANGUAGE", "RESEARCH_PROVISIONAL", "EXPANSION_VARIANT_UNRESOLVED", "EXTERNAL_CORPUS:GCML", variants=["Governed Controlled Machine Language", "Governed Compiler-Machine Language"]),
    entry("CEIR", "Constitutional Execution Intermediate Representation", "Execution-facing representation for constitutional operations and effects.", "INTERMEDIATE_REPRESENTATION", "RESEARCH_PROVISIONAL", "SOURCE_DEFINED", "EXTERNAL_CORPUS:CEIR"),
    entry("CAR", "Correspondence / Admission Record", "Records the bounded correspondence or admission relating representations, receipts, gaps, and standing.", "RECORD_TYPE", "RESEARCH_PROVISIONAL", "SOURCE_DEFINED", "EXTERNAL_CORPUS:GOORRT", nonclaims=["Correspondence does not establish identity or global equivalence"]),
    entry("RTR", "Receipt / Trace Representation", "Carries the receipts and traces supporting a governed claim.", "RECORD_TYPE", "RESEARCH_PROVISIONAL", "SOURCE_DEFINED", "EXTERNAL_CORPUS:GOORRT"),
    entry("GRR", "Gap / Refusal Representation", "Preserves gaps, refusals, and nonclaims instead of laundering them into success.", "RECORD_TYPE", "RESEARCH_PROVISIONAL", "SOURCE_DEFINED", "EXTERNAL_CORPUS:GOORRT"),
    entry("EPR", "Epistemic Position Representation", "Records the resulting epistemic standing after evidence and correspondence are evaluated.", "RECORD_TYPE", "RESEARCH_PROVISIONAL", "SOURCE_DEFINED", "EXTERNAL_CORPUS:GOORRT"),
    entry("JAR", "Jurisdiction / Authority Representation", "Represents the jurisdiction and authority context under which an operation is evaluated.", "RECORD_TYPE", "RESEARCH_PROVISIONAL", "SOURCE_DEFINED", "EXTERNAL_CORPUS:GOORRT"),
    entry("CSH", "Constitutional Semantic Hashing", "Governance-aware commitment framework for semantic provenance, admissibility, and continuity.", "COMMITMENT_FRAMEWORK", "EXTERNAL_BOUND", "SOURCE_DEFINED", "EXTERNAL_CORPUS:Constitutional Semantic Hashing"),
    entry("UMK", "Universal Modeling Kernel", "Research kernel for modeled possibility.", "RESEARCH_SYSTEM", "RESEARCH_PROVISIONAL", "SOURCE_DEFINED", "EXTERNAL_CORPUS:Ableman Constitutional Governance"),
    entry("URK", "Universal Realization Kernel", "Research kernel for preserving meaning through embodiment in a target.", "RESEARCH_SYSTEM", "RESEARCH_PROVISIONAL", "SOURCE_DEFINED", "EXTERNAL_CORPUS:Ableman Constitutional Governance"),
    entry("UEK", "Universal Execution Kernel", "Research kernel for admitted execution, capability mediation, effects, and recovery.", "RESEARCH_SYSTEM", "RESEARCH_PROVISIONAL", "SOURCE_DEFINED", "EXTERNAL_CORPUS:Ableman Constitutional Governance"),
    entry("ACG", "Ableman Constitutional Governance", "Wider constitutional-governance architecture in which UCM and related kernels are situated.", "RESEARCH_ARCHITECTURE", "RESEARCH_PROVISIONAL", "SOURCE_DEFINED", "EXTERNAL_CORPUS:Ableman Constitutional Governance"),
    entry("SIER", "Semantic Integrity and Evidence Recovery", "Research and recovery program for preserving semantic and evidence integrity.", "RESEARCH_PROGRAM", "RESEARCH_PROVISIONAL", "SOURCE_DEFINED", "EXTERNAL_CORPUS:SIER"),
    entry("SFTIR", "Semantic Field Theory Intermediate Representation", "Research representation for governed semantic-field selection and omission.", "INTERMEDIATE_REPRESENTATION", "EXTERNAL_BOUND", "SOURCE_DEFINED", "EXTERNAL_CORPUS:SFTIR"),
    entry("CM1", None, "Requirements that must hold for a realization to count as valid.", "MODEL_LAYER", "IMPLEMENTED_IN_UCM", "UCM_V0_1_CANONICAL_NOT_AN_ACRONYM", "docs/GLOSSARY.md"),
    entry("CM2", None, "Preferences used to compare valid realizations; they cannot waive CM1.", "MODEL_LAYER", "IMPLEMENTED_IN_UCM", "UCM_V0_1_CANONICAL_NOT_AN_ACRONYM", "docs/GLOSSARY.md"),
    entry("G0", None, "Foundation-admission boundary; CLOSED means no foundational authority grant is claimed.", "GATE_DESIGNATOR", "IMPLEMENTED_IN_UCM", "UCM_V0_1_CANONICAL_NOT_AN_ACRONYM", "docs/AUTHORITY-CEILING.md"),
    entry("G1", None, "Sentinel authorization record produced before external dispatch.", "GATE_DESIGNATOR", "IMPLEMENTED_IN_UCM", "UCM_V0_1_CANONICAL_NOT_AN_ACRONYM", "docs/OPERATIONAL-GATEWAY.md"),
    entry("G2", None, "Witness record binding what the pinned executor reports actually happened.", "GATE_DESIGNATOR", "IMPLEMENTED_IN_UCM", "UCM_V0_1_CANONICAL_NOT_AN_ACRONYM", "docs/OPERATIONAL-GATEWAY.md"),
    entry("G3", None, "Diagnostic classification over authorization, witnessed outcome, and expected state.", "GATE_DESIGNATOR", "IMPLEMENTED_IN_UCM", "UCM_V0_1_CANONICAL_NOT_AN_ACRONYM", "docs/OPERATIONAL-GATEWAY.md"),
    entry("A5", None, "Real-identity qualification boundary retained as false in this release.", "AUTHORITY_MARKER", "IMPLEMENTED_IN_UCM", "UCM_V0_1_CANONICAL_NOT_AN_ACRONYM", "docs/AUTHORITY-CEILING.md", nonclaims=["A5 false does not create or bind a real identity"]),
]


COMMON_TERMS = [
    ("Authority ceiling", "The strongest effect the current contract could permit. It is a limit, not a grant."),
    ("Capability surface", "A named operation with exact request, result, and effect contracts."),
    ("Configuration", "One concrete set of choices inside a realization space."),
    ("Correspondence court", "A check that native behavior and a projected behavior agree on named cases; it does not prove global equivalence."),
    ("Custody", "Evidence showing which exact bytes and state were received, used, and produced."),
    ("Dependency and Evidence Graph", "Typed record of exact, semantic, evidentiary, policy, environment, freshness, availability, and provenance dependencies used for impact, explanation, and strictly admitted reuse. It grants no authority."),
    ("Dependency closure", "The declared completeness of an adapter's dependency knowledge: COMPLETE, DECLARED, or INCOMPLETE. Only complete graph and node closure can participate in verified reuse."),
    ("Journal", "An append-only chain of integration or operation events."),
    ("MosaicID", "A portable public identity artifact. It contains no private key and grants no authority."),
    ("Obligation subject", "The exact bytes, value, or behavior that evidence must check."),
    ("Pippi", "UCM mediation runtime for observable context, drafts, proposals, projections, exceptions, and journals."),
    ("Realization", "A valid way to implement a subject while preserving its identity and requirements."),
    ("Realization Space", "The allowed choices, constraints, and comparison rules for possible realizations."),
    ("Receipt", "A rooted record binding a decision or observation to exact inputs and state."),
    ("Tessera", "The compilation layer that preserves requirements as explicit obligations and evidence subjects."),
    ("Typed refusal", "A machine-readable reason that an operation did not proceed, often with the current route to use."),
]


def registry() -> dict[str, Any]:
    tokens = [item["token"] for item in ENTRIES]
    if tokens != sorted(tokens, key=str.casefold):
        ordered = sorted(ENTRIES, key=lambda item: item["token"].casefold())
    else:
        ordered = list(ENTRIES)
    if len(tokens) != len(set(tokens)):
        raise ValueError("duplicate vocabulary token")
    for item in ordered:
        if item["relationship_to_ucm"] not in RELATIONSHIPS:
            raise ValueError(f"invalid relationship: {item['token']}")
        if item["entry_root"] != root({k: v for k, v in item.items() if k != "entry_root"}):
            raise ValueError(f"entry root mismatch: {item['token']}")
    body = {
        "schema": "mosaic.ucm.public-vocabulary-registry.v0.1",
        "registry_id": "UCM.PUBLIC.VOCABULARY.V0.1",
        "rules": [
            "EXPANSION_REQUIRES_A_DEFINING_SOURCE_OR_USER_RULING",
            "UNRESOLVED_VARIANTS_REMAIN_DISTINCT",
            "IMPLEMENTATION_STATUS_IS_SEPARATE_FROM_CONCEPT_IDENTITY",
            "CORRESPONDENCE_IS_NOT_EQUIVALENCE",
            "IDENTITY_IS_NOT_AUTHORITY",
            "HUMAN_GLOSSARY_IS_A_PROJECTION_OF_THIS_REGISTRY",
        ],
        "entry_count": len(ordered),
        "entries": ordered,
        **BOUNDARY,
    }
    return {**body, "registry_root": root(body)}


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    def clean(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", " ")
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    out.extend("| " + " | ".join(clean(value) for value in row) + " |" for row in rows)
    return "\n".join(out)


def glossary(data: dict[str, Any]) -> str:
    sections = [
        "# UCM public glossary",
        "",
        "## Why this vocabulary exists",
        "",
        "UCM separates concerns that conventional systems often collapse: meaning, state, admissibility, authority, realization, execution, evidence, custody, and presentation. As these layers became independently modeled and machine-verifiable, ordinary words such as *identity*, *result*, *proof*, and *configuration* became ambiguous. The acronyms name stable contracts and boundaries so that a receipt cannot silently substitute for authority, a realization for a specification, or correspondence for equivalence. They are compression after definition, not substitutes for explanation. Every acronym resolves here to an expansion or an explicit unresolved status, a plain-language role, a defining source, and its relationship to UCM.",
        "",
        "The machine-readable authority for token expansion and status is [`spec/PUBLIC-VOCABULARY-REGISTRY.json`](../spec/PUBLIC-VOCABULARY-REGISTRY.json). This document is its human projection. Neither the registry nor this projection grants authority or adopts external research as implemented UCM behavior.",
        "",
        "## Relationship labels",
        "",
        md_table(["Label", "Meaning"], [
            ["`IMPLEMENTED_IN_UCM`", "Code and public surfaces ship in this release."],
            ["`EXTERNAL_BOUND`", "UCM binds identity or evidence from a separately governed system."],
            ["`ADAPTER_ONLY`", "UCM validates a typed adapter result and does not claim the native implementation."],
            ["`PARTIAL_COMPATIBILITY_PROJECTION`", "A limited record or projection exists; the complete external system is not shipped."],
            ["`RESEARCH_PROVISIONAL`", "The concept is useful for orientation but is not an implemented UCM subsystem."],
            ["`HISTORICAL_VARIANT`", "Retained for reconstruction or naming history."],
        ]),
        "",
        "## Common operational terms",
        "",
        md_table(["Term", "Plain-language meaning"], [[name, meaning] for name, meaning in COMMON_TERMS]),
        "",
        "## Acronyms, designators, and representation names",
        "",
    ]
    rows = []
    for item in data["entries"]:
        expansion = item["canonical_expansion"] or "—"
        if item["expansion_variants"]:
            expansion += "; variants: " + "; ".join(item["expansion_variants"])
        rows.append([
            f"`{item['token']}`", expansion, item["plain_role"],
            f"`{item['relationship_to_ucm']}`", item["standing"], item["defining_source"],
        ])
    sections.extend([
        md_table(["Token", "Expansion", "Plain-language role", "UCM relationship", "Standing", "Defining source"], rows),
        "",
        "## THR commitment notation",
        "",
        md_table(["Commitment", "Current UCM meaning"], [
            ["`H_s`", "Exact state or logical payload."],
            ["`H_c`", "Admissibility and governance context."],
            ["`H_m`", "Normalized meaning or semantic role."],
            ["`H_j`", "Locality, jurisdiction, and DKN binding."],
            ["`H_r`", "Receipt identity and expected receipt classes."],
            ["`h_body`", "Integrity of the complete THR record; not a sixth semantic commitment."],
        ]),
        "",
        "## Naming and history rules",
        "",
        "- `AMCAS` means **Ableman Mosaic Constitutional Application Specification** in this project.",
        "- `MCIR`, `MCRM`, and `GCML` retain unresolved or historical expansion variants in the registry; UCM does not choose among them by intuition.",
        "- `EVS-EVENT` and `EVS-VERIFY` are separate protocols even though both are commonly shortened to EVS.",
        "- Candidate labels such as `c3`, `c4`, or `I4` identify frozen construction history, not architectural roles.",
        "- A source-defined concept is not automatically implemented, admitted, or authoritative in UCM.",
        "",
    ])
    return "\n".join(sections)


def system_catalog(data: dict[str, Any]) -> str:
    implemented_rows = [[f"`{sid}`", title, description] for sid, title, description in SYSTEMS]
    related = [item for item in data["entries"] if item["relationship_to_ucm"] != "IMPLEMENTED_IN_UCM"]
    related_rows = [[f"`{item['token']}`", item["plain_role"], f"`{item['relationship_to_ucm']}`", item["standing"]] for item in related]
    return "\n".join([
        "# UCM system catalog",
        "",
        "This catalog separates software shipped by UCM from external systems, adapters, compatibility projections, and research concepts. The distinction prevents a documentation reference from being mistaken for implementation, admission, or authority.",
        "",
        "## Implemented systems",
        "",
        md_table(["System ID", "Stable name", "Role"], implemented_rows),
        "",
        "## Bound, projected, and provisional systems",
        "",
        md_table(["Token", "Role", "Relationship", "Standing"], related_rows),
        "",
        "The public capability registry remains authoritative for callable surfaces. This catalog describes system identity and relationship only; it does not grant capabilities.",
        "",
    ])


def program_records(data: dict[str, Any], rendered: dict[str, bytes]) -> dict[str, bytes]:
    requirement = {
        "schema": "mosaic.ucm.public-vocabulary-requirement.v0.1",
        "requirement_id": "PUBLIC-VOCABULARY-CCP-01",
        "requirement": "ONE_ROOTED_VOCABULARY_REGISTRY_GENERATES_THE_HUMAN_GLOSSARY_AND_SYSTEM_CATALOG_WHILE_PRESERVING_CCP_AND_CHC_SOURCE_STANDING_WITHOUT_LAUNDERING_THEM_INTO_A_QUALIFIED_RUNTIME",
        "predecessor_source_root": PREDECESSOR_SOURCE_ROOT,
        "ccp_source_root": CCP_SOURCE_ROOT,
        **BOUNDARY,
    }
    requirement = {**requirement, "requirement_root": root(requirement)}
    case = build_acceptance_case(
        acceptance_case_id="PUBLIC-VOCABULARY-CCP-01",
        subject_root=CCP_SOURCE_ROOT,
        requirement_root=requirement["requirement_root"],
        verification_surface="python tools/build_public_vocabulary.py --check",
        expected_result_code="PASS",
        current_status="UNMET",
    )
    selection = build_work_selection(
        acceptance_case=case,
        work_class="DIRECT_ACCEPTANCE_CLOSURE",
        direct_closure_check_id=(
            "test_public_vocabulary.PublicVocabularyTests."
            "test_deterministic_regeneration_and_semantic_lint"),
        infrastructure_block=None,
    )
    state = build_work_unit_state(
        work_unit_id="UCM-PUBLIC-VOCABULARY-r013",
        lifecycle_phase="UPDATED",
        acceptance_case=case,
        work_class="DIRECT_ACCEPTANCE_CLOSURE",
        direct_closure_check_id=(
            "test_public_vocabulary.PublicVocabularyTests."
            "test_deterministic_regeneration_and_semantic_lint"),
        infrastructure_block=None,
        execution_holds=[],
        release_blockers=["CACHE_FREE_QUALIFICATION_BEFORE_RELEASE"],
        qualification_gaps=["FULL_RELEASE_QUALIFICATION_NOT_RUN"],
        user_acceptance_pending=False,
        allowed_effect_classes=["LOCAL_ARTIFACT_PREPARATION"],
        forbidden_targets=["AUTHORITY", "FROZEN_R012", "PUBLIC_VERSION"],
        retry_limit=1,
        repair_attempts=0,
        implemented_work_packages=1,
        total_work_packages=1,
        proof_level="TARGETED_REGENERATION_AND_SEMANTIC_LINT",
        operational_maturity="SUCCESSOR_CONSTRUCTION",
        required_next_gate="CACHE_FREE_QUALIFICATION_BEFORE_RELEASE",
    )
    evidence_roots = sorted({
        data["registry_root"],
        hashlib.sha256(rendered["docs/GLOSSARY.md"]).hexdigest(),
        hashlib.sha256(rendered["docs/SYSTEM-CATALOG.md"]).hexdigest(),
    })
    outcome = assess_work_unit_outcome(
        work_unit_state=state,
        acceptance_case=case,
        observed_result_code="PASS",
        evidence_roots=evidence_roots,
    )
    inventory_body = {
        "schema": "mosaic.ucm.public-vocabulary-work-inventory.v0.1",
        "revision": "r013",
        "predecessor_source_root": PREDECESSOR_SOURCE_ROOT,
        "requirement_root": requirement["requirement_root"],
        "acceptance_case_root": case["acceptance_case_root"],
        "work_selection_root": selection["work_selection_root"],
        "work_unit_state_root": state["work_unit_state_root"],
        "work_unit_outcome_root": outcome["work_unit_outcome_root"],
        "registry_root": data["registry_root"],
        "release_blockers": ["CACHE_FREE_QUALIFICATION_BEFORE_RELEASE"],
        **BOUNDARY,
    }
    inventory = {**inventory_body, "inventory_root": root(inventory_body)}
    records = {
        "REQUIREMENT.json": requirement,
        "ACCEPTANCE-CASE.json": case,
        "WORK-SELECTION.json": selection,
        "WORK-UNIT-STATE.json": state,
        "WORK-UNIT-OUTCOME.json": outcome,
        "INVENTORY.json": inventory,
    }
    return {
        f"program/public-vocabulary-r013/{name}": canonical(value) + b"\n"
        for name, value in records.items()
    }


def outputs() -> dict[Path, bytes]:
    data = registry()
    rendered = {
        "spec/PUBLIC-VOCABULARY-REGISTRY.json": canonical(data) + b"\n",
        "docs/GLOSSARY.md": glossary(data).encode("utf-8"),
        "docs/SYSTEM-CATALOG.md": system_catalog(data).encode("utf-8"),
    }
    rendered.update(program_records(data, rendered))
    return {ROOT / name: value for name, value in rendered.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("choose exactly one of --write or --check")
    frozen_registry = json.loads(
        (ROOT / "spec/FROZEN-PROGRAM-REGISTRY.json").read_text(encoding="utf-8"))
    frozen = check_frozen_program_directory(
        source_root=ROOT, registry=frozen_registry,
        directory="program/public-vocabulary-r013")
    failures = []
    for path, expected in outputs().items():
        if path.is_relative_to(ROOT / "program" / "public-vocabulary-r013"):
            continue
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
        elif not path.is_file() or path.read_bytes() != expected:
            failures.append(path.relative_to(ROOT).as_posix())
    result = {
        "status": "PASS" if not failures else "FAIL",
        "mode": "WRITE" if args.write else "CHECK",
        "outputs": [path.relative_to(ROOT).as_posix() for path in outputs()],
        "failures": failures,
        "registry_root": registry()["registry_root"],
        "historical_program_status": frozen["status"],
        "historical_program_root": frozen["directory_root"],
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

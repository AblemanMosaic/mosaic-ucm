# UCM public glossary

## Why this vocabulary exists

UCM separates concerns that conventional systems often collapse: meaning, state, admissibility, authority, realization, execution, evidence, custody, and presentation. As these layers became independently modeled and machine-verifiable, ordinary words such as *identity*, *result*, *proof*, and *configuration* became ambiguous. The acronyms name stable contracts and boundaries so that a receipt cannot silently substitute for authority, a realization for a specification, or correspondence for equivalence. They are compression after definition, not substitutes for explanation. Every acronym resolves here to an expansion or an explicit unresolved status, a plain-language role, a defining source, and its relationship to UCM.

The machine-readable authority for token expansion and status is [`spec/PUBLIC-VOCABULARY-REGISTRY.json`](../spec/PUBLIC-VOCABULARY-REGISTRY.json). This document is its human projection. Neither the registry nor this projection grants authority or adopts external research as implemented UCM behavior.

## Relationship labels

| Label | Meaning |
| --- | --- |
| `IMPLEMENTED_IN_UCM` | Code and public surfaces ship in this release. |
| `EXTERNAL_BOUND` | UCM binds identity or evidence from a separately governed system. |
| `ADAPTER_ONLY` | UCM validates a typed adapter result and does not claim the native implementation. |
| `PARTIAL_COMPATIBILITY_PROJECTION` | A limited record or projection exists; the complete external system is not shipped. |
| `RESEARCH_PROVISIONAL` | The concept is useful for orientation but is not an implemented UCM subsystem. |
| `HISTORICAL_VARIANT` | Retained for reconstruction or naming history. |

## Common operational terms

| Term | Plain-language meaning |
| --- | --- |
| Authority ceiling | The strongest effect the current contract could permit. It is a limit, not a grant. |
| Capability surface | A named operation with exact request, result, and effect contracts. |
| Configuration | One concrete set of choices inside a realization space. |
| Correspondence court | A check that native behavior and a projected behavior agree on named cases; it does not prove global equivalence. |
| Custody | Evidence showing which exact bytes and state were received, used, and produced. |
| Dependency and Evidence Graph | Typed record of exact, semantic, evidentiary, policy, environment, freshness, availability, and provenance dependencies used for impact, explanation, and strictly admitted reuse. It grants no authority. |
| Dependency closure | The declared completeness of an adapter's dependency knowledge: COMPLETE, DECLARED, or INCOMPLETE. Only complete graph and node closure can participate in verified reuse. |
| Journal | An append-only chain of integration or operation events. |
| MosaicID | A portable public identity artifact. It contains no private key and grants no authority. |
| Obligation subject | The exact bytes, value, or behavior that evidence must check. |
| Pippi | UCM mediation runtime for observable context, drafts, proposals, projections, exceptions, and journals. |
| Realization | A valid way to implement a subject while preserving its identity and requirements. |
| Realization Space | The allowed choices, constraints, and comparison rules for possible realizations. |
| Receipt | A rooted record binding a decision or observation to exact inputs and state. |
| Tessera | The compilation layer that preserves requirements as explicit obligations and evidence subjects. |
| Typed refusal | A machine-readable reason that an operation did not proceed, often with the current route to use. |

## Acronyms, designators, and representation names

| Token | Expansion | Plain-language role | UCM relationship | Standing | Defining source |
| --- | --- | --- | --- | --- | --- |
| `A5` | — | Real-identity qualification boundary retained as false in this release. | `IMPLEMENTED_IN_UCM` | UCM_V0_1_CANONICAL_NOT_AN_ACRONYM | docs/AUTHORITY-CEILING.md |
| `ACG` | Ableman Constitutional Governance | Wider constitutional-governance architecture in which UCM and related kernels are situated. | `RESEARCH_PROVISIONAL` | SOURCE_DEFINED | EXTERNAL_CORPUS:Ableman Constitutional Governance |
| `AMCAS` | Ableman Mosaic Constitutional Application Specification | Application constitution and integration contract projected into UCM obligations and preferences. | `IMPLEMENTED_IN_UCM` | USER_CONFIRMED_2026_11_05 | USER_RULING:2026-11-05 |
| `AOK` | Agentic Orchestration Kernel | External orchestration and courthouse system integrated through bounded workflow and result contracts. | `EXTERNAL_BOUND` | SOURCE_DEFINED | docs/COURTHOUSE-VNEXT-WORKFLOW-IR.md |
| `CAR` | Correspondence / Admission Record | Records the bounded correspondence or admission relating representations, receipts, gaps, and standing. | `RESEARCH_PROVISIONAL` | SOURCE_DEFINED | EXTERNAL_CORPUS:GOORRT |
| `CCP` | — | Source-bound curation and point-of-use admissibility construction program imported through CCP-JM. | `PARTIAL_COMPATIBILITY_PROJECTION` | NATIVE_PROGRAM_BOUND_PRODUCT_INCOMPLETE | qualification/inputs/ccp-jm/CCP_JM_PIPELINE_v0_1_r001.zip |
| `CEIR` | Constitutional Execution Intermediate Representation | Execution-facing representation for constitutional operations and effects. | `RESEARCH_PROVISIONAL` | SOURCE_DEFINED | EXTERNAL_CORPUS:CEIR |
| `CHC` | Cryptographic Homological Compilation | External architecture that separates state identity, typed semantic identity, and policy-relative admissibility. | `EXTERNAL_BOUND` | SOURCE_BOUND_PROFILE_UNRESOLVED | qualification/inputs/ccp-jm/CCP_JM_PIPELINE_v0_1_r001.zip |
| `CM1` | — | Requirements that must hold for a realization to count as valid. | `IMPLEMENTED_IN_UCM` | UCM_V0_1_CANONICAL_NOT_AN_ACRONYM | docs/GLOSSARY.md |
| `CM2` | — | Preferences used to compare valid realizations; they cannot waive CM1. | `IMPLEMENTED_IN_UCM` | UCM_V0_1_CANONICAL_NOT_AN_ACRONYM | docs/GLOSSARY.md |
| `COP` | Constitutional Observability Platform | External observability discipline for process state, evidence, and presentation fidelity. | `ADAPTER_ONLY` | SOURCE_DEFINED | EXTERNAL_CORPUS:Constitutional Observability Platform |
| `CSH` | Constitutional Semantic Hashing | Governance-aware commitment framework for semantic provenance, admissibility, and continuity. | `EXTERNAL_BOUND` | SOURCE_DEFINED | EXTERNAL_CORPUS:Constitutional Semantic Hashing |
| `DKN` | Distributed Knowledge Network | Public identity and locality namespace used for portable, storage-independent binding. | `EXTERNAL_BOUND` | SOURCE_DEFINED | docs/MOSAIC-ID-SESSIONS.md |
| `EPR` | Epistemic Position Representation | Records the resulting epistemic standing after evidence and correspondence are evaluated. | `RESEARCH_PROVISIONAL` | SOURCE_DEFINED | EXTERNAL_CORPUS:GOORRT |
| `ESA` | Epistemic Situational Awareness | System-level orientation to current epistemic conditions, stakes, admissible continuation, refusal, and stopping. | `ADAPTER_ONLY` | SOURCE_DEFINED | EXTERNAL_CORPUS:Epistemic Situational Awareness |
| `EVS-EVENT` | Event Evidence Stream | Native event-evidence protocol retained as a distinct jurisdiction. | `ADAPTER_ONLY` | UCM_V0_1_BOUND_PROTOCOL | docs/CONSTITUTIONAL-INTEGRATION-RUNTIME.md |
| `EVS-VERIFY` | Evidence Verification Subsystem | Native evidence-verification protocol retained separately from the event stream. | `ADAPTER_ONLY` | UCM_V0_1_BOUND_PROTOCOL | docs/CONSTITUTIONAL-INTEGRATION-RUNTIME.md |
| `G0` | — | Foundation-admission boundary; CLOSED means no foundational authority grant is claimed. | `IMPLEMENTED_IN_UCM` | UCM_V0_1_CANONICAL_NOT_AN_ACRONYM | docs/AUTHORITY-CEILING.md |
| `G1` | — | Sentinel authorization record produced before external dispatch. | `IMPLEMENTED_IN_UCM` | UCM_V0_1_CANONICAL_NOT_AN_ACRONYM | docs/OPERATIONAL-GATEWAY.md |
| `G2` | — | Witness record binding what the pinned executor reports actually happened. | `IMPLEMENTED_IN_UCM` | UCM_V0_1_CANONICAL_NOT_AN_ACRONYM | docs/OPERATIONAL-GATEWAY.md |
| `G3` | — | Diagnostic classification over authorization, witnessed outcome, and expected state. | `IMPLEMENTED_IN_UCM` | UCM_V0_1_CANONICAL_NOT_AN_ACRONYM | docs/OPERATIONAL-GATEWAY.md |
| `GCML` | —; variants: Governed Controlled Machine Language; Governed Compiler-Machine Language | Governed machine-facing decision language; exact expansion remains variant-bound. | `RESEARCH_PROVISIONAL` | EXPANSION_VARIANT_UNRESOLVED | EXTERNAL_CORPUS:GCML |
| `GOML` | Governed Object/Model Language | Represents governed objects, identity, semantics, and state. | `PARTIAL_COMPATIBILITY_PROJECTION` | SOURCE_DEFINED | EXTERNAL_CORPUS:GOORRT |
| `GOORRT` | Governed Object–Operation–Realization Representation Triad | Scaffold that keeps object semantics, operation semantics, and computational realization distinct while binding correspondence. | `RESEARCH_PROVISIONAL` | SOURCE_DEFINED | EXTERNAL_CORPUS:GOORRT |
| `GRR` | Gap / Refusal Representation | Preserves gaps, refusals, and nonclaims instead of laundering them into success. | `RESEARCH_PROVISIONAL` | SOURCE_DEFINED | EXTERNAL_CORPUS:GOORRT |
| `GSOL` | Governed Semantic Operation Language | Represents governed operations, authority, transitions, and refusals. | `PARTIAL_COMPATIBILITY_PROJECTION` | SOURCE_DEFINED | EXTERNAL_CORPUS:GOORRT |
| `HLIR` | Human-Legible Intermediate Representation | Proposal-layer representation that makes intent and authority legible before canonical machine lowering. | `RESEARCH_PROVISIONAL` | SOURCE_DEFINED | EXTERNAL_CORPUS:Human-Legible Intermediate Representation |
| `JAR` | Jurisdiction / Authority Representation | Represents the jurisdiction and authority context under which an operation is evaluated. | `RESEARCH_PROVISIONAL` | SOURCE_DEFINED | EXTERNAL_CORPUS:GOORRT |
| `MCIR` | —; variants: Meta-Compilation Intermediate Representation; Mosaic Canonical Intermediate Representation | Canonical computational realization representation used to bind governed structure to runtime evidence. | `PARTIAL_COMPATIBILITY_PROJECTION` | EXPANSION_VARIANT_UNRESOLVED | EXTERNAL_CORPUS:MCIR_AND_JNANA |
| `MCRM` | —; variants: Machine Code Realization Mining (reported historical expansion) | Comparison regime for witnessed source, binary, runtime, and semantic realizations; its strongest honest result is bounded correspondence. | `RESEARCH_PROVISIONAL` | EXPANSION_PENDING_SOURCE_ADJUDICATION | EXTERNAL_CORPUS:GOORRT_AND_MCIR_ROADMAP |
| `P/PPI` | Project/Process Pipeline Interface | Local project and process governance hub that coordinates Pippi, journals, reviews, and work selection. | `IMPLEMENTED_IN_UCM` | UCM_V0_1_CANONICAL | docs/PIPPI-GLOBAL-HUB.md |
| `RTR` | Receipt / Trace Representation | Carries the receipts and traces supporting a governed claim. | `RESEARCH_PROVISIONAL` | SOURCE_DEFINED | EXTERNAL_CORPUS:GOORRT |
| `SFTIR` | Semantic Field Theory Intermediate Representation | Research representation for governed semantic-field selection and omission. | `EXTERNAL_BOUND` | SOURCE_DEFINED | EXTERNAL_CORPUS:SFTIR |
| `SIER` | Semantic Integrity and Evidence Recovery | Research and recovery program for preserving semantic and evidence integrity. | `RESEARCH_PROVISIONAL` | SOURCE_DEFINED | EXTERNAL_CORPUS:SIER |
| `SRSA` | Semantic Reactor Situational Awareness | Governance-legibility instrumentation for semantic-reactor closure, drift, authority topology, and missing evidence. | `ADAPTER_ONLY` | REVIEWED_PROVISIONAL | docs/CONSTITUTIONAL-INTEGRATION-RUNTIME.md |
| `THR` | Three Hash Rule | Commitment discipline that keeps state, admissibility, meaning, locality, and receipt identity separately addressable. | `IMPLEMENTED_IN_UCM` | UCM_V0_1_CANONICAL | src/ucm/thr_cas.py |
| `UCL` | Universal Constitutional Language | Deterministic language for governed constitutional programs. | `IMPLEMENTED_IN_UCM` | UCM_V0_1_CANONICAL | src/ucm/system.py |
| `UCM` | Universal Constitutional Machine | Portable substrate for deterministic constitutional computation. | `IMPLEMENTED_IN_UCM` | UCM_V0_1_CANONICAL | README.md |
| `UEK` | Universal Execution Kernel | Research kernel for admitted execution, capability mediation, effects, and recovery. | `RESEARCH_PROVISIONAL` | SOURCE_DEFINED | EXTERNAL_CORPUS:Ableman Constitutional Governance |
| `UGK` | Universal Governance Kernel | External governance kernel whose separately rooted reports and HeadlessRunner receipts can be bound by UCM. | `EXTERNAL_BOUND` | SOURCE_DEFINED | docs/CONSTITUTIONAL-INTEGRATION-RUNTIME.md |
| `UMK` | Universal Modeling Kernel | Research kernel for modeled possibility. | `RESEARCH_PROVISIONAL` | SOURCE_DEFINED | EXTERNAL_CORPUS:Ableman Constitutional Governance |
| `URK` | Universal Realization Kernel | Research kernel for preserving meaning through embodiment in a target. | `RESEARCH_PROVISIONAL` | SOURCE_DEFINED | EXTERNAL_CORPUS:Ableman Constitutional Governance |

## THR commitment notation

| Commitment | Current UCM meaning |
| --- | --- |
| `H_s` | Exact state or logical payload. |
| `H_c` | Admissibility and governance context. |
| `H_m` | Normalized meaning or semantic role. |
| `H_j` | Locality, jurisdiction, and DKN binding. |
| `H_r` | Receipt identity and expected receipt classes. |
| `h_body` | Integrity of the complete THR record; not a sixth semantic commitment. |

## Naming and history rules

- `AMCAS` means **Ableman Mosaic Constitutional Application Specification** in this project.
- `MCIR`, `MCRM`, and `GCML` retain unresolved or historical expansion variants in the registry; UCM does not choose among them by intuition.
- `EVS-EVENT` and `EVS-VERIFY` are separate protocols even though both are commonly shortened to EVS.
- Candidate labels such as `c3`, `c4`, or `I4` identify frozen construction history, not architectural roles.
- A source-defined concept is not automatically implemented, admitted, or authoritative in UCM.

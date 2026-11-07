# Preliminary Mosaic ecosystem semantic-gravity audit

Status: `INFORMATION_ONLY`  
Authority effect: `NONE`  
Scope: the seven-application frozen AMCAS portfolio plus the later session
observations for World Engine, Mosaic UI, Mosaic Terminal UI, and Mosaic Vocal
Lab. This is a planning audit. It does not establish behavioral equivalence or
authorize composition.

## Exact portfolio facts

- Seven frozen application plans contain 35 capability projections and 96
  correspondence cases.
- Effect distribution: 12 pure computation, 7 read-only, 6 local artifact
  preparation, 8 workspace writes, and 2 persistent-host-state operations.
- Therefore 25 of 35 projections (71%) can first be studied without a
  persistent host-state effect.
- Thirteen proposed cross-application relations converge on Memory Vault
  interfaces. Every relation is presently `PLAN` or `HOLD`; none is an admitted
  composition or observed equivalence.
- Only `ARCHIVE_COMPOSE` and `READ_EVIDENCE` repeat as exact capability IDs.
  This materially understates semantic overlap because each application uses
  its own vocabulary.

## Semantic gravity centers

### 1. Artifact custody and replay — strongest current center

Memory Vault already supplies the proposed center for:

- archive composition;
- verified/quarantined replay;
- evidence and receipt views;
- artifact custody;
- filesystem transactions and stewardship;
- verified launch and freshness.

World Engine's predecessor model, Field Modeler, Media Center, and
Messenger/Crystal all declare planned or held relationships to part of this
surface. The likely parsimonious result is one constitutional custody contract
and verifier, with application-owned adapters and domain authority retained.

The current shared relation schema is insufficient for implementation: it
mostly identifies request/result profile names. Operation selectors, privacy,
redaction, version migration, and result normalization remain unbound.

### 2. Governed operation lifecycle — ecosystem-wide center

All applications need some form of:

- exact subject and expected-state binding;
- capability/effect inventory;
- preflight refusal;
- durable intent;
- witness and diagnostic receipts;
- interruption/uncertainty custody;
- no blind redispatch;
- portable journal export.

Terminal UI's deterministic build workflow and Vocal Lab's state-bound REAPER
workflow provide complementary acceptance cases for one Workflow IR and
three-gate operation envelope. The executor and application semantics remain
different; the custody mechanism should be shared.

### 3. Realization selection and configuration

World Engine's predecessor has an explicit realization selector; Memory Vault
has UCM profile selection; Field Modeler anticipates comparison profiles. These
appear to be realizations of one constitutional selection pattern:

1. enumerate candidates;
2. apply CM1 admissibility;
3. compare admissible candidates through CM2;
4. bind the selected configuration and its evidence.

The likely shared element is the Realization Space contract and selection
receipt, not a shared renderer, generator, or storage engine.

### 4. Semantic view models and presentation

Mosaic Reader already separates document import, reader-plan compilation,
headless realization, Win32 realization, navigation gating, and atomic save.
Mosaic UI and Mosaic Terminal UI suggest the same higher-order division:

- shared semantic view model and interaction intent;
- separate GUI, TUI, headless, and native renderers;
- renderer-specific evidence and effect constraints.

Media Center can consume the same projection pattern without surrendering its
catalog, playback, or service authority.

### 5. Content and asset graphs

Field Modeler, World Engine, Reader, Media Center, and AAC all manipulate
structured content with identity, ordering, provenance, and derived views. A
shared content-addressed graph vocabulary is plausible. A shared domain model
is not yet supported: geometry, documents, media catalogs, and spatial audio
carry different invariants.

The near-term target should be shared identity, lineage, dependency, and
projection relations, with domain payloads remaining application-owned.

## Likely near-term gains

| Candidate common mechanism | Immediate gain | Preserve separately |
|---|---|---|
| Workflow IR + three-gate lifecycle | One operation, recovery, and receipt grammar across sessions | Native executors and application decisions |
| Artifact custody contract | Fewer archive, replay, hash, freshness, and evidence adapters | Application retention/privacy policy |
| Realization Space selection | One CM1/CM2 selection and explanation path | Domain candidate generation and scoring |
| Semantic view/interaction model | GUI, TUI, headless, and reader projections share intent | Rendering and platform behavior |
| MosaicID/DKN jurisdiction envelope | Consistent session and artifact identity | Application roles and grants |
| Typed external-evidence envelope | Reuse ordinary tests, proofs, and receipts | Native test semantics and tools |
| Portable integration journal | Central portfolio observability and continuation | Each application's native state |

The major gain is not immediate deletion of code. It is removal of competing
authoritative mechanisms: fewer archive formats, fewer receipt dialects, fewer
ad-hoc retry rules, fewer configuration selectors, and fewer session-specific
interpretations of the same evidence.

## Data-quality and migration blockers

1. The frozen roster still names `MOSAIC.2D_3D`; World Engine must be rebound as
   a successor, not silently renamed.
2. Mosaic UI, Terminal UI, and Vocal Lab are not in the frozen seven-application
   portfolio and need Stage I1 constitutional intake.
3. Evidence requirements mix identifiers with prose and absolute host paths.
   They need typed requirement records before portfolio-wide automation.
4. Application-local capability names hide functional overlap. A canonical CRU
   vocabulary plus explicit local-to-canonical mappings is needed.
5. Proposed relations are plans or holds. No code deduplication should occur
   until behavior, authority, failure, recovery, and privacy correspondence are
   observed.

## Recommended first demonstration

Run three bounded consolidation pilots:

1. **Custody:** Memory Vault with World Engine, Field Modeler, and Media Center;
   compare compose, replay, evidence-view, and custody contracts without live
   restore.
2. **Presentation:** Mosaic UI, Terminal UI, and Reader; bind one semantic view
   model to GUI, TUI, headless, and native projections.
3. **Operation:** Terminal UI and Vocal Lab through the UCM–Courthouse vNext
   Workflow IR boundary; demonstrate the same receipt/recovery grammar over a
   deterministic build and an externally stateful REAPER operation.

Each pilot should first yield correspondence records and semantic diffs. Shared
code or service extraction comes only after CM1 equivalence and authority
separation are demonstrated.


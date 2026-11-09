# Ableman Mosaic Constitutional Application Standard v1 — Candidate

This portable, non-overwriting candidate defines how an Ableman Mosaic
application is described, composed, governed, realized, inspected, and tested.
It turns the earlier coarse Courthouse system map into typed constitutive units:

`CRU + typed relations → BCR → application constitution → governed realization`

The standard deliberately keeps eight roles distinct:

1. **UCM / CGSOS** defines the constitutive ontology: CRUs, BCRs, SHCA, layers,
   composition, and constitutional storage.
2. **MetaMetaModeler** supplies versioned specification packages, application
   profiles, and instance-constitution compilation. It cannot ratify its output.
3. **GOORRT** models objects, operations, transitions, realizations, and their
   correspondence. A finding is not a warrant.
4. **GTK / Hyperpedia / CSIL / SFTIR** supplies semantic identity, relations,
   lineage, selection, and transformation. Missing bridges remain visible.
5. **GCML** performs qualified typed deterministic decisions. It grants no
   effect authority.
6. **UGK** governs intent, authority, admissibility, standing, effects,
   receipts, and reflexive change.
7. **AOK Courthouse** is the orchestration and institutional runtime: Context,
   Workflow and Capability IR, FSC/DSC, GIE/DGIE, AbleTools, custody, courts,
   and user projections.
8. **MosaiCOS** is a conforming composed runtime/application realization, not a
   synonym for any one kernel or compiler.

## What this build establishes

- 24 Courthouse system groups decomposed into internal CRUs;
- exact source pins for UGK r178, MetaMetaModeler, UCM/CGSOS, GOORRT, Semantic
  Composition, the predecessor standard, and selected Courthouse modules;
- typed CRU, BCR, term/jurisdiction, and realization-binding registries;
- explicit UGK, GOORRT, and semantic/context profiles;
- a portable application-constitution schema;
- deterministic `orient`, `init`, `verify`, and `replay` commands;
- a cold-boot `SKILL.md` and Codex implementation guide; and
- a source-bound AOK Courthouse reference constitution.

## What it does not establish

It does not canonically adopt the standard, activate a runtime, prove live
behavior, ratify any source, change standing, or write to the Courthouse. A
static implementation binding is not a runtime observation. The current
Semantic Composition successor remains `CANDIDATE_NOT_INSTALLED`.

Claim ceiling:

`PROVISIONAL_SOURCE_BOUND_PORTABLE_STANDARD_AND_REFERENCE_APPLICATION_CORRESPONDENCE_ONLY`

## Use

```powershell
$py = 'C:\Users\New Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -B tools\mosaic_standard.py orient
& $py -B tools\mosaic_standard.py verify --sources
& $py -B tools\mosaic_standard.py init --output C:\path\to\candidate --name 'My Mosaic Application'
& $py -B tools\mosaic_standard.py replay
```

`init` creates a new candidate directory and refuses to overwrite an existing
one. Canonical adoption always remains a separate Governor decision.


---
name: ableman-mosaic-constitutional-application-standard
description: Cold-boot, inspect, initialize, and verify an Ableman Mosaic constitutional application using source-bound CRU/BCR, GOORRT, UGK, semantic-context, and Courthouse role contracts.
---

# Ableman Mosaic constitutional application standard

Use this bundle as an orientation and construction contract, never as authority.

## Cold boot

1. Run `tools/mosaic_standard.py orient` and retain the `standard_root`.
2. Run `tools/mosaic_standard.py verify`. Add `--sources` when the pinned source
   workspaces are present on the host.
3. Read `README.md`, `IMPLEMENTATION_CODEX.md`, `STANDARD-HEAD.json`, and the
   three profiles before modeling or changing an application.
4. Treat `CRU-REGISTRY.json` as semantic identity, `BCR-REGISTRY.json` as typed
   composition, and `REALIZATION-BINDINGS.json` as scoped realization evidence.
5. Before constructing a new capability, search existing CRUs and bindings.
   Reuse, refine, or add another realization when meanings correspond. Hold an
   unresolved correspondence rather than merging by name.
6. Use `init` only for a new candidate directory. Never overwrite canonical
   application files.
7. Run `verify` and `replay`; report exact evidence classes and gaps.

## Required separations

- representation is not realization;
- a GOORRT finding is not a warrant;
- a receipt is not standing;
- GCML selection is not effect authority;
- MetaMetaModeler release generation is not ratification;
- source presence or a synthetic harness is not runtime correspondence;
- the two qualified EVS jurisdictions must never be merged as bare `EVS`;
- semantic partiality must remain visible; and
- canonical adoption requires a separate explicit transition.

This skill may orient, initialize a disposable candidate, and verify evidence.
It may not mutate protected paths, activate services, admit, ratify, or change
standing.


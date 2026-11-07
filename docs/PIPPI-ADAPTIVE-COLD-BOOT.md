# P/PPI adaptive cold boot

The adaptive cold boot carries one exact UCM runtime, P/PPI's mediation and
project protocols, a non-authoritative UGK practice profile, host skills, and a
return contract. It serves local coding agents and attachment-mediated web
agents from the same rooted records.

## Host modes

- `EXECUTABLE_LOCAL` runs the verifier and journal client on hosts such as
  Codex or Claude Code. The host must declare filesystem, process, and artifact
  capabilities before P/PPI selects this mode.
- `ARTIFACT_MEDIATED_WEB` gives ChatGPT or Claude web the exact project capsule
  and requires a structured return capsule. Reading an attachment is never
  reported as local execution.
- `NATIVE_ENFORCED` is reserved for a later host adapter with a separately
  pinned verifier that proves tool and visible-output interposition. This
  portable adaptive package always refuses that claim; caller-supplied adapter
  roots and capability names are declarations, not verification.

## Turn protocol

1. `pippi host-negotiate REQUEST.json`
2. `pippi turn-prepare REQUEST.json`
3. The agent performs ordinary work within the declared host capability ceiling.
4. `pippi turn-report REQUEST.json`
5. `pippi turn-reconcile REQUEST.json`

A turn report is an observable agent record. P/PPI does not infer hidden
reasoning or unreported effects. Reconciliation refuses if the project root or
journal head changed after the opening record.

## Capsules

`pippi capsule-build` produces a rooted manifest that binds the project, UCM,
UGK profile, mediation library, journal, turn and exact members. Private keys,
tokens, IPC keys and raw credentials are forbidden. Public MosaicID/DKN material
and opaque provider references may travel.

The adaptive UGK profile implements context and record rules for FGA, the Three
Hash Rule, IEL, CK, CGP and claim discipline. It is not the canonical UGK
runtime. Native UGK certification requires a separately pinned exact release.

## Interface discipline

Every active adaptive surface appears in the UCM capability registry with an
ABI schema, CLI route, effect scope and product-profile selection. Run
`pippi interface-doctor` to detect missing payload definitions, duplicate names,
missing routes or missing schemas. `pippi completion SHELL` projects the same
command registry into bash, zsh, fish, or PowerShell completion records.

The qualified release creates an exact operator kit beside the cold boot. Its
`RUN.cmd` is the human execution boundary: it verifies the sealed kit, extracts
to a disposable workspace, prints every case as it runs, preserves a sealed
evidence ZIP, removes temporary files, and pauses. The builder does not execute
that court.

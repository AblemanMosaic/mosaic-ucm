# Contract authoring and evolution playbook

Authors should describe intent before editing a large canonical JSON document.
The authoring profile turns a small set of declared facts into a valid scaffold;
the scaffold remains unbound until its real subject, jurisdiction, evidence, and
acceptance rules are supplied.

## Intent to scaffold

| Intent in plain language | Generated field |
| --- | --- |
| “This contract governs application X.” | `subject.subject_id` and exact `source_roots` |
| “These choices may vary.” | realization `axes` |
| “These conditions must always hold.” | hard constraints / CM1 requirements |
| “Among valid choices, prefer this.” | objectives / CM2 preferences |
| “These actions may have effects.” | AMCAS capabilities and effect classes |
| “The application keeps its own meaning.” | native semantic authority and forbidden overrides |
| “This evidence must come back.” | evidence roots, fields, and acceptance obligations |

```powershell
python tools/ucm.py contract-init realization EXAMPLE.CONTRACT EXAMPLE.SUBJECT `
  1111111111111111111111111111111111111111111111111111111111111111 `
  2222222222222222222222222222222222222222222222222222222222222222 `
  draft.realization.json
python tools/ucm.py contract-doctor realization draft.realization.json
```

`PASS_AUTHORING_ONLY` means the JSON is structurally useful but still contains
explicit unbound markers. `PASS_CAMPAIGN_READY` means no known structural or
semantic placeholder remains. Neither status authorizes an operation.

## CM1 before CM2

CM1 decides membership. A failed hard condition removes the candidate. CM2 may
order only the remaining candidates. Use `explain-selection` for an ordered,
rooted account of eliminations and the winner. Use `configuration-diff` for a
two-configuration comparison with constraint-level reasons.

## Evolution

An old journal event remains interpreted under the contract root it records.
A successor contract names its predecessor in `revision.predecessor_root`.
New events use the successor root; old events are never silently reinterpreted.

`contract-compatibility` returns:

- `SUPPORTED_EXACT` for the same root;
- `SUPPORTED_SUCCESSOR` when the successor names the predecessor;
- `NEEDS_DECLARED_MIGRATION` when a known old root lacks that link;
- `REJECTED_UNKNOWN_PREDECESSOR` outside the admitted history.

A repair delta states the changed semantics and preserved invariants. It is a
record, not adoption or authority. A lifecycle receipt then records the chosen
state transition separately.

## Shared policy packs

Policy packs are pure data. They import named requirements by a pinned pack
root. `NO-AUTHORITY`, `SOURCE-BOUND`, and `OFFLINE-PORTABLE` are reference
packs. Composition refuses one requirement ID with different bodies. Identical
duplicates are reported so the author can remove redundancy before applying.


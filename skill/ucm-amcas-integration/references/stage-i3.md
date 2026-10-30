# Stage I3 shadow planning

Stage I3 converts exact Stage I1 custody and Stage I2 bilateral declarations
into correspondence-backed plans. It does not execute the application, connect
applications, grant a capability, issue a native permit, or authorize
composition.

## Entry conditions

- fixed application denominator and exact application identities;
- exact Stage I1 and latest Stage I2 artifact hashes in CAS;
- exact pipeline release, predecessor snapshot, portfolio status, preflight,
  and correspondence-court roots;
- all Stage I2 matched relations known and included in the instruction;
- `INFORMATION_ONLY`, authority effect `NONE`, real A5 false, and G0 closed.

## Plan contract

For each application require:

1. the exact instruction root and all required evidence roots;
2. explicit preservation of native semantic authority and native effect
   executors;
3. capability projections with native route, UCM projection, effect class,
   CM1/CM2 disposition, typed input/output roots, and complete case IDs;
4. correspondence cases with a rooted input, expected native and UCM decision,
   expected native and UCM result root, and evidence requirements;
5. a disposition for every matched Stage I2 relation;
6. explicit exclusions, holds, plan status, and next action;
7. `shadow_execution_requested: false` and `composition_requested: false`.

When `expected_equivalence` is true, require both the decision and result root
to agree. These are planned predicates, never observations. A later court must
capture native and UCM results independently and preserve divergence.

## Portfolio discipline

Store instruction and plan bytes in CAS and journal each import through G1
Sentinel, G2 Witness, and G3 Diagnostic. Preserve every revision. The current
portable response pointer must equal the current CAS-bound Stage I2 revision;
stale pointers refuse sealing. Do not report review readiness until all fixed
denominator instructions and plans are present and valid.

Review readiness still authorizes no effect. Reviewers must attack application
swaps, missing cases, orphaned cases, stale declarations, changed roots,
self-certified evidence, removed holds, widened authority, and re-sealed
forgeries before any later execution stage is considered.

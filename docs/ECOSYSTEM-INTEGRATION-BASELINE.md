# Mosaic ecosystem integration baseline

The checked-in baseline is an exact summary of the last frozen, seven-application
Stage I3 portfolio. It binds the source portfolio status and record inventory by
SHA-256 and preserves the fixed denominator.

- Four application plans are ready for shadow review.
- Three application plans remain held: AAC, Messenger/Crystal, and Reader.
- No shadow execution, application contact, composition, or authority is authorized.

The baseline is a starting point for Track B. A successor may advance an application
only by importing a new exact return artifact, preserving prior custody, and recording
the resulting journal event. Track A product changes do not silently change this state.

## Exact Stage I3 lineage

[`integration/stage-i3`](../integration/stage-i3) carries the exact seven
application-authored instruction/plan pairs and the exact pipeline-bound
successors referenced by the baseline. The frozen reconciliation proves:

- the denominator remains seven;
- all 35 capability projections, 96 prospective correspondence cases, and 13
  relation dispositions retain identical meaning;
- all holds are preserved;
- the only transition is the repaired pipeline/instruction binding; and
- no application was contacted or executed and no shadow authority was granted.

Two authoring plans arrived as noncanonical JSON bytes. Their exact artifact
hashes remain preserved. Their pipeline-bound successors are canonical, while
the reconciliation uses rooted parsed meaning to demonstrate semantic identity.
This keeps byte custody and semantic custody separate instead of pretending
that formatting changes application meaning.

## Session dispatch

[`ECOSYSTEM-SESSION-DISPATCH.json`](../integration/ECOSYSTEM-SESSION-DISPATCH.json)
records the seven accepted thread-message transports against the exact
pipeline-bound plans. Four sessions received read-only Stage I4 preparation
work; AAC, Messenger/Crystal, and Reader received Stage I3 repair-only work.
Every return remains `PENDING`. Tool acceptance proves only that the message
was accepted for delivery; it is not evidence that the application session
performed, accepted, or completed the work.

Session returns may use application-specific inner formats. The coordinator
normalizes custody with `tools/wrap_ecosystem_session_return.py`. Its outer
envelope binds the returned bytes to the dispatch, application, thread,
instruction and plan, but remains `RECEIVED_UNVERIFIED` until a separate
content check. This prevents transport receipt from laundering an inner claim.
The fixed-denominator return index now records all seven exact packages as
`RECEIVED_UNVERIFIED`. AAC remains held; Messenger/Crystal returned a typed
incomplete record; 2D/3D returned typed source-and-route drift; Field Modeler
returned preparation metadata while remaining ineligible; Memory Vault and
Media Center returned Stage I4 readiness records; Reader returned a launcher
repair with one item addressed pending review and every hold uncleared.

[`ECOSYSTEM-INTEGRATION-OUTCOME-REGISTER.json`](../integration/ECOSYSTEM-INTEGRATION-OUTCOME-REGISTER.json)
performs bounded static reconciliation of those exact records. It does not
replace independent review, prove application behavior, clear a hold or make
any application execution-eligible. Memory Vault preserves the unresolved
native UGK receipt-verifier gap. Every returned status remains an inner claim.

[`ECOSYSTEM-NEXT-WORK-PROGRAM.json`](../integration/ECOSYSTEM-NEXT-WORK-PROGRAM.json)
derives a bounded lane for each outcome: readiness review, source/route rebind,
return recovery, or repair/review. It carries exact return-envelope roots and
all named holds and gaps. Every lane starts `NOT_STARTED`; none grants
execution or hold clearance.

[`ECOSYSTEM-NEXT-WORK-DISPATCH.json`](../integration/ECOSYSTEM-NEXT-WORK-DISPATCH.json)
binds those lanes back to the established seven-session roster. Its transport
status records only that the coordinator delivered each bounded instruction;
it is not evidence of completion, acceptance, review, execution, or hold
clearance.

Successor-work returns use a separate custody generation. Each envelope binds
the second dispatch, the exact prior return-envelope root, and the returned
bytes. [`ECOSYSTEM-SUCCESSOR-RETURN-INDEX.json`](../integration/ECOSYSTEM-SUCCESSOR-RETURN-INDEX.json)
keeps the denominator at seven while work is in flight. A received successor
remains `RECEIVED_UNVERIFIED`; its inner status cannot clear a hold or establish
application execution.

ECOSYSTEM-SUCCESSOR-OUTCOME-REGISTER.json reads the exact returned records into a fixed seven-application static register. Reported repair status remains a subject claim: the register grants no execution, clears no hold, and marks all content as lacking independent review.

Later audit returns are append-only qualifications of an already received
integration subject. They live in `integration/audit-returns/` and are
reconciled in `integration/ECOSYSTEM-AUDIT-RETURN-REGISTER.json`. This layer
does not replace the original seven-application successor register, treat a
self-reported audit as independent review, clear any hold, or authorize
execution. It separates passing focused tests from open findings and carries
the exact THR state, semantic, governance, journal, and reviewed-slice roots.

`integration/ECOSYSTEM-INTEGRATION-CURRENT-STATE.json` is the derived reading
surface. It binds both registers, retains a root of every predecessor row, and
overlays only the latest exact audit status. An audit overlay can add holds or
make a hold more specific; it cannot erase predecessor custody, clear a hold,
or make an application eligible to execute.

`integration/ECOSYSTEM-AUDIT-REPAIR-PROGRAM.json` converts each reconciled audit
into one coherent repair batch. It carries every open hold, prioritizes the P1
set, and requires a current-source Stage I1 reissue plus an append-only journal.
This avoids serial patch/review churn while preserving the rule that a builder
cannot claim independent review or application execution.

Coherent repair returns form a third append-only layer under
`integration/repair-returns/`. The compact
`ECOSYSTEM-REPAIR-RETURN-REGISTER.json` binds the exact repaired Stage I1 bytes,
its external receipt, the predecessor audit and every claimed repaired finding.
The current-state overlay may record those findings as repaired pending review,
but it preserves external identity, jurisdiction, composition, authentication
and native-route holds. It therefore cannot turn a builder repair into an
independent verdict or an execution grant.

# Canonical integration journal

`EVENTS.jsonl` is the append-only source of truth. Every event binds its
sequence, predecessor, stable event ID, actor, payload, boundary, and event
root. `HEAD.json` is a recoverable projection. A crash between the journal and
head updates repairs the projection from the verified journal; it never
replays an external effect.

The journal records contracts, identity, challenges, sessions, operations,
three-gate receipts, requirement dispositions, tests, proofs, findings,
artifacts, checkpoints, reports, interruptions, and recovery. Stable event IDs
make retries idempotent and reject conflicting reuse.

The canonical journal archive contains the contract, IR, history, head,
checkpoint, integration report, and exact software anchor. It is separate from
the canonical software archive so many application campaigns can reuse one
software identity without embedding mutable histories in the runtime.

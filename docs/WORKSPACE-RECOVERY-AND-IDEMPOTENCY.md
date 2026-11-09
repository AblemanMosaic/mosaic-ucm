# Workspace, recovery, and idempotency

## Normative layout

```text
workspace/
  journal/
    EVENTS.jsonl       append-only semantic history
    HEAD.json          recoverable projection of verified history
    .journal.lock      mutable process-exclusion record
  progress.jsonl       optional, nonsemantic, safe to delete
  outputs/             operation-specific results named by contract
```

`EVENTS.jsonl` and accepted receipts are content-addressed custody. `HEAD.json`
is mutable only as a projection of verified history. Progress and temporary
files may be deleted. A caller must not delete a journal, accepted receipt, or
unreconciled output merely because it has a copy elsewhere.

A stale lock is removable only when the recorded owner is gone, the journal
chain verifies, and its actual head equals the caller’s expected head. PID reuse
can conservatively leave a lock in place; it must never justify unsafe theft.

## Idempotency keys

Generate an unpredictable operation-scoped key and bind it to operation,
subject, permit, executor, requested effects, and expected result. Retain the
key for at least as long as the operation archive and executor replay window.
The same key and same body returns existing custody without re-effect. The same
key with a different body refuses.

## Uncertain operations

After dispatch intent, process loss does not mean “nothing happened.” Mark the
operation uncertain, inspect external receipts, then reconcile. Do not
redispatch. A second session imports the portable journal, verifies the head,
re-binds any host-local executor, and continues from recorded state.

Run `python tools/run_recovery_demo.py --output <empty-directory>` for a
no-effect, fixed-key demonstration. Session A records authorization, dispatch,
and `UNCERTAIN`; session B opens the durable custody and reconciles the signed
terminal receipt without calling prepare or dispatch again. The result and
portable operation archive are written separately from progress output.

## Storage failures

`JOURNAL_STORAGE_CAPACITY_EXHAUSTED` covers ENOSPC and quota exhaustion.
`JOURNAL_DURABLE_WRITE_FAILED` covers other failed write/fsync/replace paths.
Neither is success. Free or move unrelated data, preserve the original journal
and temporary recovery material, verify custody, and retry the same logical
request. Never create a new idempotency key to hide an uncertain write.


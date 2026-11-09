# UCM operational gateway

This is the accessible entry point for effectful UCM integration. The gateway
is executor-neutral: it governs permission, custody, receipts, state, proof,
and archives. An external executor remains responsible for the actual effect.

## Conceptual interface

`DESCRIBE` identifies the application, action, subject, session, jurisdiction,
and requested result. `CONSTRAIN` supplies effects, budget, rollback, expiry,
generation, idempotency, and revocation. `CHECK` verifies the signed permit and
current externally anchored revocation registry. `PREPARE` writes authorization,
G1, and dispatch intent durably. `TRACE` consumes signed dispatch and terminal
receipts. `PROVE` rederives the complete history. `EXPLAIN` projects G2/G3 and
terminal state. `ARCHIVE` seals THR-separated state, governance, meaning,
locality, and receipt identity.

## State machine

```text
EMPTY -> AUTHORIZED -> SENTINEL_ALLOWED -> READY -> DISPATCHED
                                                 |          |
                                                 |          +-> UNCERTAIN -> WITNESSED
                                                 |                              |
                                                 +----------------> WITNESSED --+
                                                                                |
                               CANCELLED <- before dispatch      COMPLETED/FAILED/
                                                               DIVERGED/CANCELLED
```

Dispatch is exactly once by contract: the durable dispatch authorization and
executor receipt share one idempotency key. If the outcome is unknown, the
state becomes `UNCERTAIN`; redispatch remains false and only reconciliation is
valid.

## Active surfaces

- `BUILD_OPERATIONAL_CONTRACT`
- `PREPARE_OPERATIONAL_GATEWAY`
- `RECORD_OPERATIONAL_DISPATCH`
- `RECORD_OPERATIONAL_TERMINAL`
- `MARK_OPERATIONAL_UNCERTAIN`
- `RECONCILE_OPERATIONAL_OUTCOME`
- `CANCEL_OPERATIONAL_GATEWAY`
- `INSPECT_OPERATIONAL_STATE`
- `BUILD_OPERATIONAL_PROOF`
- `EXPORT_OPERATIONAL_ARCHIVE`
- `VERIFY_OPERATIONAL_ARCHIVE`
- `RECOVER_OPERATIONAL_JOURNAL`

The first is pure. Journal changes are `LOCAL_ARTIFACT_PREPARATION`. Inspection,
proof, and export are read-only; archive verification is pure. UCM does not
perform the external action represented by the receipt.

## Authority and identity

The caller provides an externally anchored issuer public key, jurisdiction
root, and current revocation-registry root. The permit pins the subject identity,
session, executor key, action, request, effects, budget, rollback root,
generation, nonce, and validity interval. The revocation registry and permit
are Ed25519 signed. The executor signs dispatch and terminal receipts.

All UCM artifacts remain `INFORMATION_ONLY`, authority effect `NONE`, real A5
false, and G0 closed. UCM validates authority supplied from outside; it does not
mint authority.

## Observability and custody

The progress JSONL stream reports phase boundaries and elapsed time. A compact
`.summary.json` sibling reports the current phase and counts. Both can be lost
without changing results.

The append-only journal is authoritative. The portable operation archive
contains the exact contract, operation events, terminal state, proof bundle,
and THR/CAS manifest. The commitments keep state (`H_s`), governance (`H_c`),
meaning (`H_m`), locality (`H_j`), and receipt identity (`H_r`) distinct.

## Recovery

Atomic journal writes and a recoverable head survive normal process failure.
A stale process lock can be removed only when its PID is gone and the caller's
expected journal head matches the fully verified history. No recovery operation
replays an external effect.

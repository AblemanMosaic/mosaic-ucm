# Pippi records and surfaces

## Active ABI surfaces

Use `ucm.invoke` with the exact request schema advertised by `ucm capabilities`:

1. `BUILD_PIPPI_CONTEXT`
2. `BUILD_PIPPI_MODEL_DRAFT`
3. `EVALUATE_PIPPI_DRAFT`
4. `BUILD_PIPPI_HUMAN_PROJECTION`
5. `BUILD_PIPPI_CONSTITUTIONAL_EXCEPTION`
6. `BUILD_PIPPI_TURN_ENVELOPE`

Use `BUILD_DEVELOPMENT_OBSERVATORY` only as a read-only projection over rooted
standards, Pippi, launcher, exception, and journal records.

## Campaign CLI

```text
ucm pippi-create CONTEXT WORKSPACE
ucm pippi-record-turn WORKSPACE CONTEXT DRAFT DECISION PROJECTION TURN --event-id ID
ucm pippi-status WORKSPACE --view HUMAN
ucm pippi-next WORKSPACE
ucm pippi-explain WORKSPACE
ucm pippi-verify WORKSPACE
```

The CLI may be invoked as `python -m ucm` when UCM is not installed as `ucm`.
Discover current schemas and fields from the capability registry instead of
copying stale examples.

## Record relationships

- Context binds session, subject, policies, capability registry, profile,
  jurisdiction, retained-context roots, and mediated channels.
- Draft binds the exact observable text and the complete proposal denominator.
- Decision binds the draft, semantic status, policy-evaluation roots, and one
  disposition per proposal.
- Projection binds the draft and decision; annotations supplement but do not
  alter the original text.
- Exception binds the held proposal, missing rule, affected obligations, and
  any external decision or successor policy.
- Turn binds the ordered predecessor, all mediation records, and exact tool
  proposal, dispatch-receipt, and result roots.
- Journal events make the session portable. A projection or summary is not a
  substitute for the journal.


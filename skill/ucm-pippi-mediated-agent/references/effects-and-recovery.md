# Pippi effects and recovery

## Effect path

Pippi classifies proposals. It never executes them. An allowed effect follows:

1. Pippi decision binds the allowed proposal to its declared contract.
2. The Operational Gateway verifies the external permit, identity,
   jurisdiction, effects, budgets, freshness, rollback, and executor pin.
3. G1 Sentinel and dispatch intent are durable before the executor acts.
4. The external executor returns signed dispatch and terminal receipts.
5. G2 Witness records observed effects; G3 Diagnostic classifies the result.
6. Pippi binds the receipt and result roots into the turn envelope.

Missing authorization, an undeclared effect, or a missing executor is a typed
hold or refusal. It is not evidence that an effect failed.

## Recovery

- Verify the last expected journal head before continuing.
- If no dispatch occurred, a successor turn may repair the proposal or policy
  binding without claiming an effect.
- If dispatch occurred and the terminal state is unknown, record uncertainty
  and reconcile with the pinned executor. Do not redispatch.
- If terminal custody exists, import and validate it, then record a successor
  turn that cites the recovered roots.
- If the active context or policy must change, create a successor context or
  policy record. Never rewrite the earlier turn.
- Export the journal before moving to another session. The receiving session
  must reverify the archive and rebind local host channels; portability of
  records does not imply portability of authority.


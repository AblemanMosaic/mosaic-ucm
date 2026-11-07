# Operator playbook

## Start a campaign

1. Run `ucm orient`, `ucm capabilities`, and `ucm profiles`.
2. Bind the exact source and manifest roots.
3. Scaffold and doctor the realization and AMCAS contracts.
4. Compile AMCAS and create the journal before changing code.
5. Record the fixed requirement denominator and work package.

## Compare realizations

Run `check-realization` for membership, `explain-selection` for an ordered
selection account, and `configuration-diff` for an A/B explanation. A pretty
projection is for review; the JSON receipt remains authoritative.

## Attach ordinary evidence

Record the exact tool invocation, output, environment, verifier, policy, and
subject roots. UCM checks the envelope’s presence, hash, freshness, and binding.
It does not claim that it ran pytest, tsc, eslint, coverage, an SBOM generator,
or a CI service unless a separate execution receipt proves that fact.

## Request an effect

Build and verify the external permit, then prepare the Operational Gateway. The
journal records authorization, G1, and dispatch intent before the external
executor acts. Record signed dispatch and terminal receipts, then derive G2 and
G3. Optional human approval is another externally signed prerequisite; UCM
checks it but does not mint approval.

## Recover uncertainty

Inspect the journal and expected head first. Never redispatch merely because a
chat or process ended. Reconcile a terminal receipt when available, otherwise
leave the operation `UNCERTAIN`. Export the journal before moving sessions.

## Review and handoff

Use journal summary, query, diff, and inclusion proofs. Generate pretty views
only after the exact records exist. Ship software and journal archives as
separate roles, each with its own manifest and THR commitments.


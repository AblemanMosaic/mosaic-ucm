# P/PPI Research Review Extension v0.1

This extension makes iterative research review reproducible without changing
P/PPI's strict v0.1 review-envelope contract. P/PPI continues to own exact
custody, local replay, return binding, and publication holds. The subject
application owns scholarly lenses, findings, adjudication meaning, successor
history, and the interpretation of saturation.

## Versioned records

1. `mosaic.research.review-lens-pack.v0.1` declares the review questions,
   required context roles, deterministic checks, exclusions, and limitations.
2. `mosaic.research.review-finding.v0.1` binds a finding to the exact subject,
   lens pack, source anchor, evidence, counterevidence, and reviewer identity.
3. `mosaic.research.finding-adjudication.v0.1` records acceptance, rejection,
   deferral, supersession, or duplication. Acceptance requires a separate
   author-decision root; an agent recommendation cannot manufacture one.
4. `mosaic.research.successor-ledger.v0.1` separates review-only work from an
   actual successor. A calibration may therefore record `NOT_CREATED` without
   pretending the paper changed.
5. `mosaic.research.saturation-assessment.v0.1` evaluates declining marginal
   yield over a declared pass window. It can only say that the declared lens
   set met its thresholds; it cannot establish truth, novelty, peer review, or
   publication readiness.

All five records are canonical-JSON rooted and carry the P/PPI information-only
boundary: `standing=INFORMATION_ONLY`, `authority_effect=NONE`, `real_a5=false`,
and `g0=CLOSED`.

## Envelope pattern

A research envelope should carry at least:

- the exact subject as role `SUBJECT`;
- a lens pack as `REVIEW_LENS_PACK`;
- corpus or semantic context as `CORPUS_CONTEXT`;
- the standard-library runner as `REVIEW_RUNNER`.

The deterministic runner verifies exact subject and lens roots, then emits
structural observations and a review-pass record. It does not conduct scholarly
review, infer a domain verdict, mutate the subject, or authorize publication.
Human or agent review results return through the existing P/PPI return archive,
which binds the exact envelope SHA-256 and reviewer identity root.

## CLI

Validate a rooted application record:

```text
pippi research-record-verify lens-pack LENS-PACK.json
pippi research-record-verify finding FINDING.json
pippi research-record-verify adjudication ADJUDICATION.json
pippi research-record-verify successor-ledger SUCCESSOR-LEDGER.json
pippi research-record-verify saturation SATURATION.json
```

This command validates form and roots only. It does not confer standing.

## Saturation boundary

The stop condition is intentionally conservative:

- fewer than the declared minimum passes yields `INSUFFICIENT_PASSES`;
- unresolved high-severity findings force `CONTINUE`;
- otherwise every pass in the declared recent window must be at or below the
  configured limits for new findings, accepted changes, weighted yield, and
  regressions.

The result is always qualified as
`REVIEW_SATURATED_FOR_DECLARED_LENS_SET`. New evidence, a changed paper, a new
lens, or an external review reopens the work.

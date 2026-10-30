# Operator-run adversarial review

Use this route when the user chooses to perform an adversarial leg locally or
when the intended independent-review session cannot accept the task. An
unavailable review route is an operational routing fact. It is not evidence of
a defect in the subject and does not itself justify `HOLD_FOR_REPAIR`.

## Builder/operator boundary

When the user reserves adversarial execution to the operator, the builder may
author the fixed case inventory, statically parse the runner, verify exact
hashes, and rebuild the kit deterministically. The builder does not execute any
attack, mutation, tamper, forgery, or fault-injection case. Positive happy-path
tests and static construction checks remain builder work. The launcher must
seal evidence on PASS or FAIL, verify the preserved bytes, remove only its
unique temporary directory, and pause for the human.

## Prepare the kit

1. Freeze the exact review subject and record its expected hash.
2. Create a deterministic archive containing the exact subject, a
   standard-library verifier, the court runner, its fixed contracts, a work
   order, and a self-contained Windows launcher when Windows is the operator
   host.
3. Put the launcher beside the sealed archive. Embed or bind the expected kit
   hash in the launcher; do not discover it from the archive at run time.
4. Make the launcher create a uniquely named disposable directory under the
   operating system's temporary root. Never use a broad or computed cleanup
   target without resolving and checking it first.
5. Show bounded progress: custody, extraction, case execution, evidence
   verification, preservation, and cleanup. Progress is nonsemantic and cannot
   affect verdicts, roots, receipts, or results.

## Run and preserve

1. Verify the sealed kit before extraction.
2. Extract only into the checked disposable directory.
3. Run the exact court and report the total, passed, refused, failed, errored,
   and skipped case counts. A required refusal is a passing adversarial result
   only when its typed diagnostic matches the case contract.
4. Build an evidence archive containing the court result, report, runner or
   runner hash, exact subject binding, and authority ceiling.
5. Verify the evidence archive before copying it beside the launcher.
6. Remove the disposable directory and verify that it is gone. Preserve the
   evidence archive even when the court fails, if it can be sealed safely.
7. Pause at the end of an interactive launcher so a human can read the result.

## Claims and alerts

- Call a successful result `operator-reproduced adversarial evidence`, a
  `manual adversarial leg`, or a `self-run court`.
- Do not describe it as an independent reviewer-authored attack leg. It may
  satisfy engineering closure or a user-defined manual leg, but an external
  work order can still require independent authorship.
- Record reviewer unavailability once as `REVIEW_ROUTE_UNAVAILABLE` when a
  typed record is useful. Continue through the authorized manual route without
  repetitive alarms or retry loops.
- Alert or refuse when any of these occur: sealed-kit hash mismatch, unsafe or
  failed extraction, unexpected file set, court failure or error, forbidden
  skips, evidence-root mismatch, evidence verification failure, cleanup
  failure, unexpected effects, or a change in standing, real A5, G0, or the
  declared authority ceiling.
- A clean manual court does not grant deployment, capability, admission, or
  publication authority. Preserve `INFORMATION_ONLY`, authority effect `NONE`,
  real A5 false, and G0 closed unless a separately verified transition changes
  them.

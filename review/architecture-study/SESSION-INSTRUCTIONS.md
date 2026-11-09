# UCM Track C executor instructions

This folder is one isolated, registered architecture-compliance study run. Do
not request another run kit or infer which comparison arm this is.

1. Verify `RUN-KIT.zip` using the `VERIFY.py` inside that archive before using
   its contents.
2. Read `TASK-PROMPT.md`, `CONDITION-CONTEXT.json`, and
   `HUMAN-OVERSIGHT-POLICY.json`. Work only on the supplied `SUBJECT.zip`.
3. Use the same model, settings, environment, and toolchain registered for all
   six runs. Record each as a root. Create a unique executor-session root for
   this run and do not reuse it for another run or for scoring. Record the
   fixed temperature and other generation settings in the captured journal;
   do not substitute a different model or environment midway.
4. Preserve the complete requested capture: prompt, context, actions, diff,
   tests, output, review, repairs, journal, receipts, and elapsed time. If a
   capture class does not arise, return an explicit typed `NOT_APPLICABLE`
   record rather than silently omitting it.
5. Fill `RUN-OUTPUT.template.json` only from observed results. Do not score the
   run or add an arm label. Rename the completed record to
   `RETURN-CAPTURE/RUN-OUTPUT.json`, complete the standardized `FOLLOW-ON-TASK.md`, and supply the exact required capture set including `FOLLOW-ON-RESULT.json`:
   `ACTIONS.json`, `DIFF.patch`, `TESTS.json`, `OUTPUT.zip`, `REVIEW.md`,
   `REPAIRS.json`, `JOURNAL.json`, and `RECEIPTS.json`. Roots in the output
   record must match the canonical actions and tests plus the exact output ZIP.
6. Double-click `RUN-SEAL-EXECUTION-RETURN.cmd`. Return only the resulting
   `EXECUTION-RETURN.zip` to the coordinator for blinded independent scoring
   and final validation.

This work is `INFORMATION_ONLY`. It grants no authority, performs no UCM
admission, and does not establish a benefit claim.

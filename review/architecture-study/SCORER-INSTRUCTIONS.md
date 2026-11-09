# UCM Track C blinded scorer instructions

Score only the supplied task, architecture contract, rubric, and captured run
artifacts. The executor condition and arm label are intentionally absent.

1. Verify the scoring kit before extracting it.
2. Review the exact subject, task, diff, tests, output, actions, repairs,
   journal, and receipts against `ARCHITECTURE-CONTRACT.json` and
   `SCORING-RUBRIC.json`.
3. Write `SCORING-REVIEW.md`. Fill every integer metric in
   `SCORE.template.json`; record a stable public scorer-identity root and a
   fresh scorer-session root distinct from the executor session in the
   assignment. Preserve the supplied rubric and independence-policy roots.
   Set `review_record_root` to the SHA-256 of the exact review bytes, derive
   `scoring_context_root` from the review, scorer identity/session and rubric
   roots, and recompute `score_record_root` over the canonical record without
   that field. Save it as `SCORE.json`.
4. Double-click `RUN-SEAL-SCORE.cmd`. Return only `SCORE-RETURN.zip` to the
   coordinator.

Do not guess an arm, contact the executor, or interpret one score as a study
conclusion. This work is `INFORMATION_ONLY` with authority effect `NONE`.

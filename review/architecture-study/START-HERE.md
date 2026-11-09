# UCM Track C coordinator

This folder carries the fixed six-run C3 comparative architecture study from
dispatch through blinded scoring and deterministic finalization. Keep the
coordinator material separate from the execution and scoring sessions.

## 1. Prepare execution dispatches

Double-click `RUN-PREPARE-STUDY-DISPATCH.cmd`. It verifies the registered
study package and all six nested run kits, then creates six isolated
`DISPATCH-*` folders. Give each executor exactly one dispatch folder. Do not
give an executor the roster, arm mapping, other dispatches, or scoring rubric.

Each executor binds the registered model/settings/environment/toolchain,
creates a unique executor-session root, completes the exact capture set, and double-clicks its local
`RUN-SEAL-EXECUTION-RETURN.cmd`. Collect the resulting six sealed return ZIPs
in `EXECUTION-RETURNS` beside the coordinator commands.

## 2. Prepare blinded scoring

Double-click `RUN-PREPARE-BLIND-SCORING.cmd`. It requires the complete fixed
denominator of six verified execution returns and creates six isolated
`SCORING-DISPATCH-*` ZIPs plus a coordinator-only mapping. Give each scorer
one scoring ZIP without the mapping or execution arm identity.

Each scorer uses the preregistered rubric, records a unique scorer identity
and session distinct from the executor session, records the rubric metrics and review, then double-clicks
`RUN-SEAL-SCORE.cmd` inside the extracted scoring kit. Collect the six sealed
score returns in `SCORE-RETURNS` beside the coordinator commands.

## 3. Finalize observed results

Double-click `RUN-FINALIZE-STUDY.cmd`. It verifies the study package, frozen
UCM runtime, six execution returns, six score returns, and coordinator map.
It then emits a deterministic result package through the frozen UCM
evaluation functions.

The final status is `OBSERVED_NOT_CAUSAL_CONCLUSION`. These tools do not
invoke a model, grant authority, assert statistical significance, generalize
benefit, or authorize deployment. They remain `INFORMATION_ONLY`, with
authority effect `NONE`, real A5 false, and G0 closed.

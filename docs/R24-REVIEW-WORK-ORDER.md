# UCM v0.1 r024 review work order

Review the exact r024 subject identified by the transport manifest. The work is
`INFORMATION_ONLY`, has authority effect `NONE`, keeps real A5 false and G0
closed, and does not authorize deployment or publication.

## Tier 0 — custody and positive replay

1. Verify the transport, release, qualification, archive and cold-boot roots.
2. Reconstitute the public source and confirm the source manifest.
3. Confirm the r021 original operator court and recovered original/repaired
   preimages remain exact, and that the r023 compatibility change occupies its
   own successor directory.
4. Check the frozen program and operator registries without rewriting history.
5. Replay the qualification on supported Python 3.12 and 3.13 interpreters.
6. Run the same r024 portability test denominator on Windows-native storage and
   on exact source copied to WSL-native storage. Compare canonical outputs;
   preserve platform-specific receipts separately.
7. Confirm `pippi environment-observe`, `portability-policy`,
   `portability-witness`, `portability-gate`, and
   `portability-source-doctor` are reachable through the documented CLI/ABI.
8. Confirm turn openings bind an execution-context root and inject portability
   guidance only for selected scenarios.
9. Confirm the review launcher's CMD and PowerShell names correspond exactly.

## Tier 1 — independent adversarial leg

An independent reviewer should attack the exact r024 runtime and operator kit:

- mutate frozen operator history and swap original/successor directories;
- re-seal unkeyed `Path` ordering and invalid portable paths;
- omit the WSL-native witness, substitute `/mnt/c`, or diverge canonical output;
- swap an execution-context root after turn preparation;
- shrink the portability test or output denominator;
- alter launcher, runtime, qualification or kit custody.

The builder must not execute this leg. The supplied operator kit is
builder-authored and operator-runnable; its result is engineering evidence
unless the reviewer boundary independently establishes otherwise.

## Verdict

Return `HOLD_FOR_REPAIR` for any MED-or-higher failure or reproducibility
failure. Return `INCOMPLETE_REVIEW` when a required leg is missing. A positive
review remains a recommendation only and grants no authority.

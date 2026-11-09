# UCM v0.1 r026 runtime-parity review work order

Standing is `INFORMATION_ONLY`; authority effect is `NONE`; real A5 is false;
G0 is closed. Review grants no deployment, publication, identity, executor, or
capability authority.

## Subject

Review the exact r026 transport and the release, qualification receipt, cold
boot, portability gate, native witnesses, and unexecuted operator kit it pins.
Report full observed hashes before substantive work.

The default `FOCUSED-REVIEW-TRANSPORT` is the review boundary for this repair.
It carries the exact runtime, cold boot, receipt, release record, predecessor
failure evidence, native witnesses, and operator kit. It deliberately omits
the large SDK and review-custody archives. The separately named
`FULL-REPLAY-REVIEW-TRANSPORT` adds those archives only for a reviewer who will
reconstitute and replay the complete public source. Neither packet is an
ordinary runtime distribution.

## Tier 0 — custody and positive correspondence

1. Recompute every transport, release, archive, certification, source,
   qualification, portability, and operator-kit root.
2. Reconstitute the complete source and confirm the runtime is a byte-identical
   subset of the SDK.
3. Run `tools/build_pippi_adaptive_contracts.py --check`. Confirm the cold boot
   and staged runtime both carry those exact generated files, including all
   four completion scripts and their machine-readable contracts.
4. Recompute the portability-source manifest and verify the portability source
   archive against the release source root.
5. Recompute both frozen registries and the complete canonical-output
   denominator. Confirm each native witness carries those exact outputs.
6. Confirm observed execution contexts probe current-filesystem case behavior,
   while declared external contexts remain labelled declarations.
7. Confirm scenario selection mechanically injects every required mediation
   rule and refuses an unknown scenario or a resealed omission.
8. Replay qualification from an unrelated empty directory on Python 3.12 and
   3.13, then rebuild all release and cold-boot artifacts byte-for-byte.

## Tier 1 — independent attack leg

Run the supplied operator kit from its double-click launcher. It must use a
disposable directory, show case progress, seal evidence beside the launcher,
remove disposable files, and pause at termination. Attack at least:

- stale or substituted generated contracts;
- cold-boot/live capability or mediation divergence;
- copied rather than recomputed witness outputs;
- missing or divergent Windows/WSL legs;
- declared case policy substituted for an observed local probe;
- unknown scenarios and omitted scenario-required rules;
- portability-source and frozen-registry mutation;
- authority-ceiling laundering.

The builder must not execute this leg. Operator evidence is engineering
evidence unless the declared reviewer boundary independently establishes review
independence.

## Verdict

Any custody, runtime-parity, qualification, reproducibility, denominator, or
authority-ceiling failure is `HOLD_FOR_REPAIR`. Withhold a terminal verdict if
any required leg is missing. Preserve all lower findings in one batch rather
than serially expanding the reviewed denominator.

# UCM / Pippi r022 UGEL review work order

Review the exact r022 transport as an information-only successor to frozen r021.

## Tier 0 — custody and construction

1. Verify the transport manifest and every nested archive without importing subject code.
2. Reconstruct the source from SDK, review, and lineage partitions and recompute the source manifest.
3. Confirm that Batch E is pinned to archive `70e09459418a6672cc0e1924a7f6338fd1e0a929f8dc6f5630e61d0f866307cc` and source root `8bdcd1532f914f4c471d8311597e61e59d6cfdf15347e3f55d63f6556476d851`.
4. Confirm that UGEL is an optional external executor pack: UCM does not choose it, load it, mint its grants, sign its receipts, or claim a native WASI runtime.
5. Replay the qualification from a clean directory and rebuild all release artifacts and the adaptive cold boot byte-for-byte.
6. Inspect the named `UGEL-R022-01` acceptance case and its source denominator.
7. Exercise the positive `sim.add` correspondence: Pippi decision, exact executor binding, Operational Gateway G1, externally signed dispatch and terminal receipts, G2/G3, journal state, and dependency evidence.

## Tier 1 — operator-run boundary court

Run the supplied `RUN.cmd` on Windows. The builder has not run it. Review at least:

- exact kit, runtime, qualification, Batch E archive, source, WIT, boundary, and host pins;
- UCM and UGEL canonical-domain separation;
- unsupported-effect, policy, resource, parameter, evidence, and pin mutations;
- optional-pack holds and refusal to represent an unbound executor as ready;
- exact qualification coverage of the complete acceptance case.

## Required limits

Do not treat structural verification as semantic proof. Do not infer a native runtime, ambient sandbox, authenticated handles, executor selection, capability grant, application admission, publication permission, or deployment authority. Standing remains `INFORMATION_ONLY`; authority effect `NONE`; real A5 false; G0 closed.

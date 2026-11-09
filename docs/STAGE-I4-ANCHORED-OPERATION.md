# Stage I4 anchored operation

The active Stage I4 path is a preparation and receipt-validation system. It is
not an executor and it cannot grant execution authority.

## Human entry points

1. Inspect `spec/STAGE-I4-C4-CONTRACT.json` and the five pinned trust artifacts
   beside it.
2. Build a contract with `stage4-build-anchored-run-contract`.
3. Derive preflight with `stage4-build-authority-safe-preflight`.
4. Under the current ceiling, finish the operation with
   `stage4-build-receipted-refusal` and record the full G1 receipt through
   `stage4-derive-receipt-state`.

The preflight command has no `execution_authorized` argument. It derives its
effect inventory, context, binding, and authority policy from the complete run
contract and checks them against an expected trust-anchor root supplied across
the artifact boundary. This c4 release accepts only an authority policy with
`execution_authorized: false`.

## Agent capability surfaces

- `BUILD_STAGE_I4_ANCHORED_RUN_CONTRACT`
- `BUILD_STAGE_I4_AUTHORITY_SAFE_PREFLIGHT`
- `BUILD_STAGE_I4_RECEIPTED_REFUSAL`
- `DERIVE_STAGE_I4_RECEIPT_STATE`
- `VALIDATE_STAGE_I4_RECEIPT_STATE`

The older Stage I4 observation, c3 preflight, c3 terminal, and root-only state
surfaces remain present for exact historical compatibility. The capability
registry labels them `LEGACY_COMPATIBILITY_ONLY`; they are not acceptance
surfaces for new work.

## Receipt chain

The active path validates the complete G1, G2, and G3 bodies, their self-roots,
their cross-links, the sealed run-contract root, the execution-context root,
and the external trust-anchor root. Durable operation state consumes the full
receipt body for each transition. A bare receipt root is insufficient.

Native successful execution remains unavailable in this release because the
externally owned AOK HeadlessRunner lattice and authority are not bound. UCM
does not substitute a subprocess. A later governed successor may add a signed
native receipt contract, but it must preserve the external owner and all three
integration gates.

## Qualification and progress

`tools/run_stage4_c4_positive_qualification.py` performs a cache-free staged
positive qualification. It explicitly excludes mutation, tamper, forgery, and
fault-injection cases. Progress is best-effort JSONL and is excluded from every
receipt, root, and verdict. Missing or unwritable progress cannot change a
semantic result.

The operator Tier 1 package is separate. The builder syntax-checks and seals it
without running it. Its output is operator-reproduced builder-authored evidence
unless an independent reviewer authors and executes a separate court.

Everything here remains `INFORMATION_ONLY`, has authority effect `NONE`, keeps
real A5 false, and keeps G0 closed.

# Stability, portability, and robustness

`spec/ABI-STABILITY.json` is the machine table. Within v0.1 an existing schema’s
meaning does not change, new result fields require a new schema, new surfaces
start non-granting, and deprecated surfaces refuse with a pointer to the active
replacement. Repair deltas may fix implementation without broadening authority.

Canonical JSON is UTF-8, sorted-key, compact JSON with duplicate keys, floats,
non-finite numbers, BOMs, lone surrogates, excessive depth, excessive container
sizes, and integers outside signed 64-bit refused. Unicode code points are
preserved; UCM does not silently normalize NFC/NFD. Empty and omitted fields are
different. Path strings are data until a path schema validates POSIX-relative
form. `conformance/CANONICAL-JSON-GOLDEN-VECTORS-v0.1.json` is language-neutral.

The core reads no wall clock for evidence validity. Callers supply integer
`now`; bounds are inclusive and allowed skew is zero unless a future policy says
otherwise. Journal ordering comes from sequence and predecessor roots.

Only the environment variables in `spec/ENVIRONMENT-POLICY.json` affect the
public CLI. Unknown `UCM_*` variables warn by default and refuse in strict mode.

Full journal verification is the v0.1 rule. There is no approximate PASS.
Incremental validation may be added only with a receipt binding a prior full
PASS, exact delta, and recomputed terminal root. Interactive operators should
checkpoint and archive growing journals rather than silently skipping history.

Windows and POSIX qualification must cover canonical vectors, path policy,
locks, atomic replace, self-staging examples, and the same exact public tests.
Known OS differences are recorded as environment evidence, not used to weaken
the portable profile.


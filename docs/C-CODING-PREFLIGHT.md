# C coding preflight

The C coding preflight is Pippi's fast, deterministic standards gate for C
engineering proposals. It helps an agent select the checks required by a
change before invoking an editor, compiler, analyzer, test runner, or other
external tool.

It is a policy and evidence surface. It does not edit source, run a compiler,
grant tool dispatch, or replace the C compiler and native test program.

## Public surfaces

| Surface | CLI | Purpose |
| --- | --- | --- |
| `DISCOVER_C_CODING_STANDARD` | `ucm c-standard` | Return the fixed C17 engineering standard and check vocabulary. |
| `PREFLIGHT_C_CHANGE` | `ucm c-preflight REQUEST.json` | Classify a proposed change and derive the complete quick-check denominator. |
| `EVALUATE_C_CHANGE_RESULTS` | `ucm c-check-results REQUEST.json` | Validate exact externally produced check evidence against the preflight and source root. |

All three surfaces are pure computation. Every result carries authority effect
`NONE`, and both preflight and check evaluation set
`tool_dispatch_authorized` to `false`.

## Agent loop

1. Pin the source manifest, compiler profile, architecture contract, UCM
   capability registry, product profile, policy roots, and Pippi journal head.
2. Declare the intended paths, write set, change classes, effect classes, and
   checks.
3. Run `c-preflight`.
4. On `REFUSED`, resolve every typed violation and resubmit. Do not call the
   proposed tool.
5. On `READY_FOR_QUICK_CHECKS`, an external host adapter may route the declared
   local checks through its separately governed effect path.
6. Convert each terminal result into an exact `mosaic.ucm.c-check-result.v0.1`
   record bound to the subject, tool, invocation, and evidence roots.
7. Run `c-check-results`. Continue only when its decision is `PASS` and the
   host's own effect policy separately allows the next operation.
8. Append the preflight, terminal evidence, evaluation, and visible projection
   to the Pippi campaign journal.

In `SIDECAR_PARTIAL` mode these decisions are useful and durable, but the host
can still bypass them. A verified host adapter must route `TOOL_PROPOSAL` and
`TOOL_DISPATCH` through Pippi before a refusal becomes an enforced block.

## Classification

The preflight recognizes build-system, C runtime, public ABI, world indexing,
simulation, RNG, persistence, rendering, platform, Python tooling, tests, and
documentation changes. Paths imply classes. An agent must declare every
inferred class; omission returns `C_PREFLIGHT_CHANGE_CLASS_INCOMPLETE`.

The required check set always includes source custody, toolchain custody,
warning-clean C17 compilation, architecture-boundary evaluation, and the
absence of undeclared effects. Additional classes add checks such as:

- chunk-coordinate property tests and checked arithmetic;
- fixed-step and deterministic replay;
- RNG golden vectors;
- save-codec, crash-recovery, sanitizer, and fuzz checks;
- ABI compatibility and pointer ownership/lifetime review;
- rendering/simulation separation;
- Python non-authority and fixture validation;
- portability matrices for platform-layer changes.

## Refusal behavior

Preflight refuses unsupported dialects, incomplete write sets, incomplete
change classification, forbidden effects, Python live-simulation authority,
non-native semantic authority, missing mandatory checks, and false
`ENFORCED_HOST` claims. The result names the obligation, reason code, and exact
missing denominator.

Check evaluation refuses missing, failed, not-run, duplicated, unknown, or
wrong-subject results. A passing result proves only that the supplied exact
records satisfy the declared quick-check denominator. It does not prove release
qualification, deployment readiness, absence of all C defects, or authority.

## Effect boundary

The preflight permits only declarations for source reads, workspace writes, and
local processes. Network, installation, deployment, protected writes, and
authority changes refuse. The permitted declaration still does not authorize
execution: the external host or Operational Gateway must make that separate
decision and return terminal custody.


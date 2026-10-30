# Agent access

## Operational entry point

Read `docs/OPERATIONAL-GATEWAY.md`, then call `DISCOVER_CAPABILITIES`. Use only
the active `OPERATIONAL_GATEWAY` surfaces for new operational work. Routes whose
availability is `LEGACY_COMPATIBILITY_ONLY` preserve historical replay and are
not the active architecture.

The stable agent ABI is `ucm.invoke` with schema `mosaic.ucm.request.v0.1`.
The CLI is the same ABI projected as:

```text
ucm operational-invoke <SURFACE> <PAYLOAD.json> --out <RESPONSE.json>
```

Never place a private key in a request. Permit issuers and executors sign in
their own custody environments. UCM receives only public keys, signatures,
contracts, receipts, and externally anchored roots. A public identity or valid
signature proves identity/custody; it does not by itself grant permission.

Progress files are advisory only. Resume or reconcile from the verified
journal state, never from progress output. An `UNCERTAIN` operation must be
reconciled with the original executor-signed terminal receipt and must never be
redispatched.

Start with `ucm orient`, `ucm capabilities`, and
[docs/AMCAS-INTEGRATION-WORKBENCH.md](docs/AMCAS-INTEGRATION-WORKBENCH.md).
For application work, use the supplied integration kit and the packaged
`ucm-amcas-integration` skill. The executable contract and journal are the
control surfaces; prose explains them but cannot override them.

Use `ucm validate-amcas CONTRACT.json`, `ucm compile-amcas CONTRACT.json`, and
`ucm campaign-status WORKSPACE` before planning work. Record every effect or
capability grant through `operation-plan`, `operation-witness`, and
`operation-diagnostic`. Export the resulting journal with `campaign-export`.

Before application work, bind exact source bytes with
`integration-bind-subject`, check the native control-plane disposition, and run
the native/UCM correspondence court. Do not claim Stage I1 from a chat summary,
unreachable path, or zero-root template. Return the deterministic Stage I1
bundle and verify it with `integration-verify-stage1`. In multi-session work,
use the fixed portfolio roster and import each Stage I1 bundle into exact CAS
custody before claiming composition preflight readiness. Require separated
`H_s/H_c/H_m/H_j/H_r` commitments. Do not infer provider/consumer edges from
route names; obtain explicit Stage I2 declarations and run the composition
preflight before a correspondence court.

For a slim portable orientation surface, place the extracted
`MOSAIC-UCM-AMCAS-AGENTIC-ADAPTATION-SIDECAR-v0.1.zip` beside this UCM core.
Run its `verify-core` command before forwarding any UCM operation. Import every
returned Stage I2 declaration with `portfolio-import-stage2`; use
`portfolio-campaign-preflight` so the graph is derived only from the latest
journaled CAS revisions. Provider invitations require matching consumer
imports. Preserve rejected invitations as reconciliation evidence and request
a provider successor rather than editing either declaration locally.

For Stage I4, first run `stage4-derive-eligibility` over the exact Stage I3
instruction, plan, and review archive bytes. The archive must contain the typed
review disposition and exact reviewed-subject bindings. Do not supply a bare
archive hash or caller-selected verdict. Do not construct a run
contract when `eligible_for_shadow_execution` is false. The
`stage4-build-run-contract` surface produces an exact case schedule and effect
membrane but grants no execution authority. A later observation must be
validated with `stage4-validate-observation` and must carry complete typed G1
Sentinel, G2 Witness, G3 Diagnostic, and execution-authority roots. Preserve a
`DIVERGED` result; never rewrite it as success.

No agent surface in this candidate grants external authority. Preserve
`INFORMATION_ONLY`, authority effect `NONE`, real A5 false, and G0 closed.
The observation result separates native/UCM pairwise equivalence from
conformance to the scheduled expected decisions and result roots. Equal wrong
answers are a failure. All public agent, CLI, and direct-library routes enforce
the same contract.

For the c3 successor, use the `stage4-c3-*` surfaces and carry an externally
acknowledged review policy, full relation/case map, execution context, and
native-runner binding. Treat `NATIVE_RUNNER_UNAVAILABLE` as terminal preflight
evidence. Never bypass it with local subprocess execution. Journal the ordered
G1/G2/G3 operation state; after dispatch, an uncertain outcome prohibits
redispatch until an operator resolves custody.

For new work, use the active role-named c4 surfaces described in
`docs/STAGE-I4-ANCHORED-OPERATION.md`. Supply the expected trust-anchor root as
an artifact-bound input; never accept an anchor merely because it self-roots.
Do not pass an authorization boolean. The preflight derives authority from the
sealed policy and must refuse under this release. Journal complete receipt
bodies through `DERIVE_STAGE_I4_RECEIPT_STATE`; a receipt root or transition
label alone is not evidence. Treat all c3 and v0.2 Stage I4 routes as historical
compatibility surfaces for replay, not acceptance surfaces for new work.

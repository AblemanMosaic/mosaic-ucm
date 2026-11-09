# Agent access

For dependency-aware work, orient first, compile or load the governed graph,
capture a complete snapshot, evaluate in `SHADOW_IMPACT`, inspect the exact
impact and explanation, and then call the named native check. Do not infer
authority, proof, or fresh execution from graph reachability or a retained
result. Unknown closure requires full recomputation. See
[Dependency and Evidence Graph](docs/DEPENDENCY-AND-EVIDENCE-GRAPH.md).

## Operational entry point

Read `docs/COMMON-CASE.md`, then call `DISCOVER_CAPABILITIES`. The default
registry contains current surfaces only. Use the `OPERATIONAL_GATEWAY` surfaces
for new operational work. Predecessor routes live in a separate legacy registry
and require the explicit `COMPATIBILITY` profile; a default-profile call returns
a typed refusal naming the current replacement.

The stable agent ABI is `ucm.invoke`. Use `mosaic.ucm.request.v0.2` with an exact `profile_selection`; the legacy v0.1 envelope is retained only as an AUTHORING-bound compatibility route. The dispatcher refuses any surface outside the selected profile. The CLI is the same ABI projected as:

```text
ucm operational-invoke <SURFACE> <PAYLOAD.json> --out <RESPONSE.json>
```

Never place a private key in a request. Permit issuers and executors sign in
their own custody environments. UCM receives only public keys, signatures,
contracts, receipts, and externally anchored roots. A public identity or valid
signature proves identity/custody; it does not by itself grant permission.

Progress files are advisory only. Resume or reconcile from the verified
journal state, never from progress output. `INSPECT_OPERATIONAL_STATE` opens existing custody read-only and refuses a missing journal without creating files. If custody reaches `WITNESSED` before G3 is persisted, call `FINALIZE_OPERATIONAL_TERMINAL`; it rederives G2/G3 from the original signed terminal receipt and never redispatches the external effect. An `UNCERTAIN` operation must be
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
the native/UCM correspondence court. Do not claim custody from a chat summary,
unreachable path, or zero-root template. Return the deterministic custody
bundle and verify it with `integration-verify-stage1`. In multi-session work,
use the fixed portfolio roster and import each bundle into exact CAS custody
before claiming composition preflight readiness. Require separated
`H_s/H_c/H_m/H_j/H_r` commitments. Do not infer provider/consumer edges from
route names; obtain explicit composition declarations and run the composition
preflight before a correspondence court.

For a slim portable orientation surface, place the extracted
`MOSAIC-UCM-AMCAS-AGENTIC-ADAPTATION-SIDECAR-v0.1.zip` beside this UCM core.
Run its `verify-core` command before forwarding any UCM operation. Import every
returned composition declaration with `portfolio-import-stage2`; use
`portfolio-campaign-preflight` so the graph is derived only from the latest
journaled CAS revisions. Provider invitations require matching consumer
imports. Preserve rejected invitations as reconciliation evidence and request
a provider successor rather than editing either declaration locally.

No agent surface in this candidate grants external authority. Preserve
`INFORMATION_ONLY`, authority effect `NONE`, real A5 false, and G0 closed.
The observation result separates native/UCM pairwise equivalence from
conformance to the scheduled expected decisions and result roots. Equal wrong
answers are a failure. All public agent, CLI, and direct-library routes enforce
the same contract.

Stage-labelled routes are historical compatibility surfaces. They remain
documented in `docs/LEGACY-CAPABILITY-SURFACES.md` for exact replay. Do not use
them as acceptance surfaces for new work.

## Constitutional integration runtime

When an application already has UGK, ESA, SRSA, COP, EVS, HeadlessRunner, test,
or repair control planes, preserve their identities and adapt their rooted
results with `ucm.build_adapter_result`. Before an external effect, call
`ConstitutionalIntegrationRuntime.prepare`; give its dispatch authorization to
the authority-selected executor; then record only that executor's signed
dispatch and terminal receipts. Use `build_observatory` for read-only portfolio
status. Never use progress JSONL, a model narrative, an adapter result, or an
application capsule as permission.

See `docs/CONSTITUTIONAL-INTEGRATION-RUNTIME.md` for the complete agent loop.
## AMCAS baseline loop

Before changing an application contract, call `DISCOVER_AMCAS_BASELINE` and `INSPECT_AMCAS_UCM_COVERAGE`. Compile with `COMPILE_AMCAS_BASELINE`; do not delete emitted migration obligations. Compare successors with `DIFF_AMCAS_BASELINES`, treating every authority-adjacent change as requiring review. Confirm the current fixed denominator with `CHECK_AMCAS_UCM_PARITY`. Use `INSPECT_AMCAS_PORTFOLIO` for read-only coverage, intake holds, successor rebinding, and consolidation-campaign roots.

Generated AUTHORING, OPERATIONAL, VERIFY_ONLY, and COMPATIBILITY profile sets bind the exact Stage I3 application plans. A profile attenuates available surfaces; it never grants authority. Follow `docs/AMCAS-MIGRATION-PLAYBOOK.md` and keep native application authority intact.

## Point-of-use admissibility loop

Use the point-of-use surfaces when a previously valid artifact or application
must be checked against current state, policy, schema, trust, jurisdiction, and
checkpoint anchors. Build the records with
`BUILD_ADMISSIBILITY_JURISDICTION`,
`BUILD_ADMISSIBILITY_ENFORCEMENT_PERIMETER`,
`BUILD_CHC_THR_CORRESPONDENCE`, `BUILD_ADMISSIBILITY_EVIDENCE_SNAPSHOT`, and
`BUILD_CURRENT_USE_SNAPSHOT`. Then call `EVALUATE_CURRENT_ADMISSIBILITY` with
independently supplied expected roots. Use
`EXPLAIN_CURRENT_ADMISSIBILITY` for the Pippi question **“Can I use this now?”**

Do not request `ADMIT` from a `DECLARED_ONLY` enforcement perimeter. Bind a
`QUALIFIED_SCOPED` perimeter and keep the evaluator's logical step and evidence
row budgets large enough for the exact frozen snapshot.

Do not treat the explanation, an old decision, or an `ADMIT` decision as an
authority grant. The evaluator performs no evidence acquisition and observes
no effect. For effectful work, pass the exact decision and snapshots through
`PREPARE_ADMISSIBILITY_BOUND_GATEWAY`; the Operational Gateway must revalidate
the roots, record the G1 custody, and require a native target-version check
before dispatch. G2 and G3 still bind the observed result and diagnostic
classification. CHC and UCM THR have a versioned role correspondence, not
digest identity or wire compatibility. See `docs/CCP-ADMISSIBILITY.md`.

## Pippi mediation loop

Use the packaged `ucm-pippi-mediated-agent` skill for this loop. It layers over
`ucm-amcas-integration`: Pippi governs each observable agent turn, while the
integration skill governs the application contract, effect path, and handoff.

For governed agent work, build or load a Pippi context before emitting a visible
answer or proposing a tool call. Preserve the model draft byte-for-byte, evaluate
every proposal against the declared policy and capability roots, hold every
undeclared effect, and project only a validated decision. Persist turns through
`PippiCampaign`; use `pippi-status`, `pippi-next`, and `pippi-explain` for current
state. Progress JSONL is never evidence. A semantic-passage provider may clarify
qualified integer senses without rewriting the original text, but remains
unbound until its external provider root is pinned. Launcher and harness receipts
describe external execution; they do not authorize or perform it.

For project-scale work, create a P/PPI process baseline and milestone contract
before treating plans as actionable. Bind every resumable runner through an
exact execution capsule, schedule standards from meaningful project events,
and keep implemented, tested, reviewed and accepted status separate. Use
`ucm process-build` or the `BUILD_PROCESS_*` ABI surfaces. See
`docs/PIPPI-PROCESS-GOVERNANCE.md`. These records do not authorize effects;
the courthouse or another admitted executor must return the native receipts.

For C work, call `DISCOVER_C_CODING_STANDARD`, then submit the exact proposal to
`PREFLIGHT_C_CHANGE` before an editor, compiler, analyzer, or test tool. A typed
`REFUSED` result is the tool response: resolve its complete violation list before
resubmitting. `READY_FOR_QUICK_CHECKS` derives a fixed check denominator but does
not authorize dispatch. After the host runs separately authorized local checks,
submit exact subject/tool/invocation/evidence-bound records to
`EVALUATE_C_CHANGE_RESULTS`. See `docs/C-CODING-PREFLIGHT.md`.

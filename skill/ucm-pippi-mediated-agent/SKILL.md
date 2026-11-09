---
name: ucm-pippi-mediated-agent
description: Mediate observable agent context, draft responses, tool proposals, visible projections, exceptions, and journal handoffs through UCM Pippi. Use when an agent session, coding workflow, or host adapter must operate through Pippi. Do not use this skill as authority to execute tools, grant capabilities, inspect hidden reasoning, or claim enforced-host coverage without a verified adapter.
---

# UCM Pippi-Mediated Agent

Use Pippi as the governed boundary around observable agent work. The executable
UCM schemas, capability registry, policies, and journal validators decide
whether a record is accepted; this skill coordinates their use.

## Navigate the constitution before changing it

1. Run `pippi standards` and pin the returned atlas root. Use
   `pippi standard-explain RULE_ID` to see exact injected text, triggers,
   evidence fields, refusal codes, co-projections, and known ablation failures.
2. Run `pippi pipeline-model` and identify the current state and proposed
   transition. Use `pippi transition-explain TRANSITION_ID` before work. A
   transition that requires CCP stays held until its independently rooted
   current-use decision admits that exact subject under that jurisdiction.
3. Run `pippi context-explain REQUEST.json` when selecting context. Preserve
   the exact scenario, variables, required rules, explicit additions, reason
   paths, and explanation root. Never claim a rule was injected from chat
   memory alone.
4. Keep co-projections distinct. AMCAS states application obligations; UGK
   constrains transitions and claim discipline; CCP evaluates point-of-use
   admissibility; P/PPI selects work and context; the Operational Gateway alone
   mediates effects. THR domains, DKN identity/locality, dependency evidence,
   realization selection, and courthouse correspondence remain separately
   rooted.
5. For a P/PPI change, pin the starting release and atlas, name one acceptance
   case, advance the engineering revision by default, and export a signed
   constitutional change capsule. A capsule is a proposal and never replaces
   the canonical installation until imported, checked, qualified, and accepted.
6. Collaborators carry public MosaicID passports and DKN bindings using stable
   nonce `mosaic.ucm.v0.1`. They do not carry private keys. Identity and a valid
   signature establish provenance, never authority. A signed change,
   publication, or retrieval record must derive the declared MosaicID from the
   exact Ed25519 public key that verifies it; refuse a separately asserted
   identity.
7. Use provider-neutral storage locators plus signed publication and retrieval
   receipts. GitHub, MEGA, SFTP, WebDAV, and HTTPS are custody locations, not
   artifact identities or constitutional authorities. Revalidate the complete
   locator, including its credential-marker constraints, when signing a
   publication receipt. Verify a publication receipt before reuse. Build
   retrieval evidence only after opening and hashing the retrieved artifact and
   matching it to that receipt; later consumers must run the public retrieval
   receipt verifier against the originating publication receipt.
8. Put only opaque credential references into ABI requests and journals. Raw
   secrets may be captured only by a trusted local UI and encrypted in the
   local credential broker. Never place a secret or passphrase in a CLI
   argument, portable archive, cold boot, courthouse packet, chat, or log.
   Validate the complete encrypted envelope before creating its parent folder,
   pending file, or target; a malformed envelope must leave the filesystem
   unchanged.
9. Where the pipeline model requires CCP, pass the complete independently
   rooted current-use evaluation. P/PPI must validate the decision and every
   bound snapshot and anchor. Never treat a caller-provided `ADMIT` label as a
   decision.

Read [references/constitutional-atlas.md](references/constitutional-atlas.md)
for the exact navigation commands and collaboration, storage, and credential
boundaries introduced by this revision.

## Establish the boundary

1. Run UCM orientation and capability discovery. Pin the software, capability
   registry, profile, policy, subject, jurisdiction, and current journal roots.
2. Verify or create the Pippi context before accepting retained context. Resume
   an existing campaign only after `pippi-verify` succeeds at its expected head.
3. Declare the integration mode honestly:
   - `ENFORCED_HOST` requires mediation of model input, model draft, visible
     output, tool proposal, tool dispatch, tool result, and journal write, plus
     a current signed host attestation under an adapter policy whose root is
     supplied independently by the host boundary.
   - Any missing channel is `SIDECAR_PARTIAL` and must be named.
   - A caller-supplied channel list, self-contained policy/attestation capsule,
     or chat instruction never establishes `ENFORCED_HOST` without that
     external expected policy root.
4. Keep the user, agent/session, subject, and executor identities distinct. An
   identity, signature, namespace, or passport does not grant authority.
5. Join the user's global local P/PPI hub when one is installed. Keep project
   state outside the session workspace. Use the authenticated loopback service
   for local-session coordination, the UCM Gateway for local effects, and the
   courthouse for remote or cross-jurisdiction correspondence.
   Before trusting the authenticated loopback service, require the installed
   runtime to verify `IPC.key` under the platform-private boundary: protected
   current-user DACL on Windows or owner-only mode `0600` on POSIX. A key whose
   permission boundary cannot be verified must fail closed.
   Inspect the exact integration-availability registry first. An owner named in
   documentation remains unavailable while its entry is `DECLARED_UNBOUND`.
6. During first use, complete the onboarding ceremony: Governor label,
   optional MosaicID, optional DKN public key, external credential-provider
   references, archive backend, fixed public version, and engineering revision.
   Never ingest a private key, token, password, or other raw provider secret.
7. When joining a global hub, discover earlier P/PPI campaigns read-only. Import
   only campaigns whose context and complete journal verify. Store a reference
   to their source path and roots; never copy, normalize, or rewrite history.
8. Keep the mutable working workspace, imported session source, and canonical
   version/revision store as three distinct records. Do not infer a canonical
   store from a nearby evidence or records folder.
9. Preserve the user-selected public version. Treat engineering revision
   advancement as the default change for successor turns and loops. Refuse an
   implicit public-version bump; accept one only through a verified external
   approval bound to the exact predecessor, successor version, and revision.
10. Inspect `pippi pack-list` and `pippi pack-inventory` before assuming an
    optional realization exists. The P/PPI/UCM/Mosaic UI core is complete on
    its own; the UGK standards profile is recommended and built in. Treat the
    canonical UGK runtime, SemCrys, Memory Vault, Courthouse, native-host, and
    UGEL executor capabilities as optional exact packs or external bindings. A plan is not
    an install, a downloaded archive is not a binding, and a binding is not an
    authority grant.
11. For a project handoff, run `pippi project-portability` against its exact
    required pack IDs. Preserve `NEEDS_PACKS` rather than deleting requirements
    or selecting a weaker realization. View-only inspection may continue.
    Remote acquisition needs explicit user authorization and an external
    effect gateway; record a pack only after artifact verification evidence
    and the expected inventory head match.

Read [references/host-boundary.md](references/host-boundary.md) when building or
assessing an adapter. Read [references/records-and-surfaces.md](references/records-and-surfaces.md)
when constructing records or operating a campaign.

When work spans several turns, milestones, agents, or review boundaries, read
[references/process-governance.md](references/process-governance.md). Bind the
exact project baseline, execution dependency closure, acceptance policy,
replanning denominator, locality and current journal before presenting project
status or a next action.

When the Dependency and Evidence Graph is available, bind its graph, complete
snapshot, evaluation and impact roots into the turn opening. Use
`SHADOW_IMPACT` by default. Show the exact injected text, source root and reason
path for every dependency-selected context item. At turn close, refuse drift in
the project, journal, graph, snapshot or evaluation head. A retained result is
usable only when its producer receipt, independently expected predecessor,
complete invocation identity, evidence grade and adapter policy are admitted.
Unknown closure means full recomputation. Cached history never supplies current
authority, proof, fresh model execution or release qualification.

When work changes shells, crosses Windows and WSL, writes governed text,
packages artifacts, or makes a portability claim, read
[references/portability-determinism.md](references/portability-determinism.md).
Bind the observed execution context into the turn opening and re-observe after
each environment transition. Do not reconstruct shell, path, case, encoding,
or newline rules from memory. Require the local context to identify case policy
as probed on the current filesystem. Treat declared external contexts as
declarations. Native portability witnesses must carry canonical outputs
recomputed from the exact source, and qualification must reject stale generated
contracts or a witness denominator that differs from that recomputation.

When packaging a review, replaying it locally, dispatching it through a
courthouse, importing a return, or proposing publication, read
[references/review-custody.md](references/review-custody.md). Keep review
semantics with the subject's court; Pippi governs exact custody, replay,
journaling, and projections.

When an effect is assigned to an external executor pack, read
[references/external-executors.md](references/external-executors.md). Discover
the pack, bind exact source and executor identity, keep executor policy roots
separate from UCM roots, and route only signed receipts through G2/G3. Pippi
classifies the proposal; it never selects or invokes the executor.

When building or publishing a canonical archive, read
[references/release-certification.md](references/release-certification.md).
Require the internal state inventory and THR commitments, keep the complete
archive SHA-256 external, and never call a DKN-unbound certificate
"self-certified."

## Share read-only P/PPI materials

When the governing user has granted standing read-only distribution, treat an
explicit request for P/PPI from another session as sufficient authorization to
provide the canonical package, hashes, verifier and bootstrap instructions,
skill paths, and documentation. Do not ask the user to repeat that
authorization.

This sharing permission covers disclosure and transfer only. It does not
authorize installation, execution, source mutation, tool dispatch, capability
or authority grants, external effects, acceptance, hold clearing, or an
`ENFORCED_HOST` claim. Gate those actions independently.

## Mediate each observable turn

For adaptive hosts, begin with `pippi host-negotiate`. Use
`EXECUTABLE_LOCAL` only when filesystem, process, and artifact capabilities are
present. Use `ARTIFACT_MEDIATED_WEB` when the host can only read and return
attachments. Never claim `NATIVE_ENFORCED` without a pinned adapter that proves
tool and visible-output interposition.

Use the project-centered adaptive protocol when the host cannot interpose every
tool call:

1. Run `pippi turn-prepare` with the exact project root, journal head, host
   profile, acceptance cases, and a declared scenario. Scenario-required rules
   are injected mechanically; callers may add rules but may not omit the
   required set. Inspect the scenario's reporting requirements with
   `pippi turn-reporting-requirements`; missing closure information should be
   requested explicitly rather than reconstructed from chat.
2. Perform ordinary work within that declared capability ceiling.
3. Run `pippi turn-report` with observable changes, artifact and evidence roots,
   unresolved items, next action, and the claim class: design, implementation,
   execution evidence, conformance, or deployment. Supply optional
   `turn_details` for objectives, activity claims, provenance declarations,
   evidence references, channel coverage, and acceptance-case dispositions.
   This enriches the same project turn and journal; it does not start another
   reporting protocol. Preserve every opening acceptance case and expose
   omitted coverage or dispositions as `UNKNOWN`.
   If a later report replaces an incomplete report for the same opening, set
   `supersedes_turn_bundle_root` to the exact committed bundle. Never edit the
   earlier bundle or create two successors from one report.
4. Run `pippi turn-reconcile`. It must refuse if the project or journal head
   changed after preparation. Begin another turn only after reconciliation or
   an explicit interrupted/abandoned disposition. When a common turn record
   was built, pass it as optional `turn_record` so reconciliation binds its
   exact root. Use `pippi turns` for the project's retained turns and
   `pippi turn-record-view` for a deterministic human projection.

Read [references/common-turn-records.md](references/common-turn-records.md)
when authoring enriched reports, checking missing information, or binding a
turn to CMBA. Treat `AGENT_REPORTED`, `HOST_CAPTURED`, `VERIFIER_DERIVED`,
`EXTERNALLY_ATTESTED`, and `UNKNOWN` as caller-declared bases. Every such claim
and evidence reference remains `DECLARED_NOT_VERIFIED` in this record; a
receipt root or a supplied channel label does not establish observation or
host enforcement. Reporting completeness is distinct from verification,
acceptance closure, effect permission, and whole-host interception. CMBA's
optional generic-profile evaluation checks the record's binding and structure;
it does not establish the truth of reported activity.

When the turn must bind CMBA to DKN locality, separated THR commitments, CHC
correspondence, CCP current-use admission, or G1/G2/G3 history, use the r036
composite profile described in that reference. Require every native validator
and independent expected anchor; never infer one co-projection from another.

Use `pippi mediation-library` to inspect exact injected text. UGK-derived rules
must preserve FGA transition form, separated Three Hash Rule commitments, IEL
validate-before-mutate behavior, CK portability, CGP posture, and claim
discipline. A contextual UGK profile is not a canonical UGK runtime or receipt
verifier.

1. Build the rooted context capsule from declared context roots and mediated
   channels.
2. Preserve the model's observable prose exactly in a model-draft record.
   Represent tool calls, capability grants, policy changes, and other proposed
   actions as typed proposals; do not infer proposals from hidden reasoning.
3. Evaluate every proposal against the pinned policy and application contract.
   Every proposal must receive exactly one disposition.
4. Hold every undeclared effectful proposal. Produce a constitutional exception
   that names the missing rule and affected obligations rather than inventing
   permission or silently widening policy.
5. Attach semantic annotations without rewriting the original prose. If a
   semantic passage is unresolved, return it for clarification or hold it; do
   not claim GCNL/CSIL/GTK resolution that was not actually performed.
6. Build the requested human, agent, or forensic projection. Treat it as a
   rooted view of the draft and decision, never as a second authority record.
7. Route allowed effect proposals to the externally bound UCM Operational
   Gateway. Require a launch proposal bound to the host attestation and accept
   completion only after re-verifying the complete operation history, proof
   bundle, G1/G2/G3 receipts and result projection. Pippi itself neither
   executes nor grants.
8. Bind tool proposals, dispatch receipts, tool results, context, draft,
   decision, and projection into the ordered turn envelope. Append it once to
   the canonical campaign journal.
9. Verify the campaign and expose the new head. Never use chat memory, console
   text, or progress JSONL as custody.
10. Use `dependency-impact` and `dependency-explain` to select the named native
    check. Do not let graph reachability replace AMCAS, CCP, Workflow IR,
    Gateway, policy-pack, compiler or proof validation.

## Govern work units before effects

1. Discover or create the governed process checkpoint before starting work.
2. Bind every implementation work unit to one exact acceptance case and run
   `pippi work-selection-verify` before implementation. Name the subject,
   requirement, verification surface, expected result, and direct closure
   check. Do not select shared infrastructure unless that case is `BLOCKED` and
   a rooted infrastructure-block record proves the missing capability with
   diagnostic evidence and an unblock criterion. General usefulness is not a
   blocker. Completing infrastructure never closes the acceptance case; require
   a following direct step.
3. Preflight the complete planned record bundle before expensive computation or
   effects. Check schemas, canonical ordering, uniqueness, dependency closure,
   enums, effect ceilings, and expected journal and process heads.
4. Classify blockers correctly. `execution_holds` prevent the work unit from
   running. `release_blockers` permit bounded construction but block release.
   `qualification_gaps` limit claims. `user_acceptance_pending` is a human gate.
5. After any material effect, write a no-replay capsule naming completed effect
   receipt roots, remaining tail operations, retry budget, and authoritative
   heads. Resume from that capsule; never reconstruct effect custody from chat.
6. Treat result append and process-checkpoint advance as one prepared record
   bundle. Finish it idempotently or preserve the explicit `PREPARED` state.
7. Report program progress, proof level, operational maturity, release blockers,
   and acceptance status as separate facts.
8. Bound each work unit with stop conditions, repair-attempt limits, deferred
   obligations, and a reason-coded continue/defer/escalate decision.

## User-visible behavior

- Present the governed human projection as the official mediated response.
- Keep original text available and identify held or refused proposals with
  typed reasons and the next resolvable action.
- Offer human, agent, and forensic views over the same rooted state. Do not hide
  a refusal merely to simplify the display.
- Stream compact nonsemantic progress when work is long, but label it as
  progress and keep it outside evidence roots.
- When the host cannot prevent an unmediated channel, disclose that coverage
  gap instead of presenting the session as fully governed.
- Derive review findings, limitations, evidence lists, and outcomes from the
  exact sealed envelope or return archive on demand. A dashboard, modal, or
  pretty view is a projection over that archive, never a second review record.
- For a long review replay, show compact `VERIFY -> EXTRACT -> RUN -> SEAL`
  progress with elapsed time and the evidence destination. Keep that stream
  nonsemantic and outside evidence roots.

## Govern review and publication custody

1. Build and verify a closed review envelope before registering it. Pin its
   archive SHA-256 externally and preserve its subject, manifest, runner,
   limitations, and independent-review requirement exactly.
2. Track review custody through `PACKAGED`, `DISPATCH_PREPARED`, `RETURNED`, and
   `PUBLICATION_PROPOSED`. Do not skip or infer a state from chat or filenames.
3. A local replay must use a disposable workspace and produce sealed evidence.
   Describe it as process isolation unless an independently verified OS sandbox
   was actually used.
4. When the governing user asks to run adversarial review manually, prepare an
   exact self-running operator kit with live progress, sealed evidence, cleanup,
   and a terminal pause. Do not run the adversarial leg yourself unless the user
   separately authorizes that execution. Treat operator evidence as engineering
   evidence, not an independent verdict unless the declared reviewer boundary
   establishes independence.
5. Route remote or cross-jurisdiction review correspondence through the
   courthouse. Import only a return whose review ID, envelope SHA-256, contents
   root, and return root verify against the registered envelope.
6. A returned verdict never grants authority or authorizes publication. It may
   create only a held publication proposal after Pippi opens the exact artifact,
   verifies the externally supplied SHA-256 and embedded META records, and
   derives the THR body, DKN binding, and self-certificate roots. Never accept
   caller-asserted certificate status or roots. A DKN-namespaced proposal
   requires a cryptographically verified `PASS_SELF_CERTIFIED` certificate.
   Require explicit human authorization at the publishing boundary.
7. Prefer the Pippi review surfaces `review-envelope-build`,
   `review-envelope-verify`, `review-run-local`, `review-dispatch-courthouse`,
   `review-import-return`, `review-compare`, and
   `review-publication-proposal`. If a host adapter exposes equivalent tools,
   pin its registry and schemas before relying on them.

## Effects, recovery, and exceptions

- Apply the UCM-AMCAS integration skill for application contracts, CM1/CM2,
  MosaicID, operational permits, G1/G2/G3, external executors, and portable
  application handoffs.
- After a dispatch with an uncertain terminal result, block redispatch until
  custody is reconciled. An identical retry may return recorded custody;
  changed reuse must conflict.
- Treat constitutional exceptions as requests for an external decision or a
  successor policy root. They do not amend the active policy themselves.
- On context, journal, profile, policy, registry, or jurisdiction drift, stop at
  the last verified head and return the typed mismatch.

Read [references/effects-and-recovery.md](references/effects-and-recovery.md)
before dispatch, recovery, or exception handling.

## Close or hand off

Run `pippi-verify`, export the exact campaign journal and required receipts,
and report the pinned context, terminal turn, journal head, integration mode,
mediated-channel coverage, unresolved exceptions, and effect custody. State
implemented, tested, reviewed, and authorized status separately. Preserve
`INFORMATION_ONLY`, authority effect `NONE`, real A5 false, and G0 closed unless
a separately verified authority transition explicitly changes them.

For portable handoff, build and verify a P/PPI project capsule. Bind the exact
UCM root, UGK profile or runtime root, mediation-library root, host profile,
project root, journal head, turn root, public identity roots, and every member.
Select `CONTEXT_ONLY`, `WORK_CAPSULE`, `PROJECT_PORTABLE`, `AIRGAP_COMPLETE`, or
`FULL_REFERENCE` explicitly. Exclude private keys, tokens, passwords, IPC keys,
and raw provider credentials. A web return is agent-reported material until the
local installation imports and reconciles it transactionally.

Read `docs/PIPPI-MODULAR-INSTALLATION.md` and the generated
`spec/PIPPI-PACK-REGISTRY.json` when choosing a local profile. On Windows, use
`PIPPI-INSTALLER.vbs` for the native rainbow-sun UI and `PIPPI-HEADLESS.vbs`
for a no-console plan. Their common planner performs no installation effects.

Treat pack discovery and planning as read-only. `pack-inventory`,
`install-plan`, and `project-portability` must not initialize or update a user
inventory. Persist pack state only through the explicit, head-checked
`pack-record` surface after the relevant external operation and evidence exist.

For large or revision-rich projects, prefer the r031 transtemporal custody
surfaces. Run `archive-ingest` only as an explicit write operation, then run
`archive-verify` and a disposable `archive-materialize` before treating the
revision as reconstructable. BLAKE3-256 is the primary content address and
SHA-256 is the interoperability projection; neither may be silently omitted.
Keep THR state, semantic, governance, jurisdiction, and receipt commitments
separate. Keep DKN `DECLARED_UNBOUND` until a real public key and signature are
verified. `archive-report` may show duplicated logical bytes but never
authorizes deletion.

SemCrys and Memory Vault remain optional packs. `archive-semcrys-plan` performs
no compression, upload, or credential use. Require exact pack roots and a
post-compression restoration receipt whose bytes pass the original dual-digest
manifest. Never put private keys, tokens, or raw provider credentials in a
portable archive. Use the native C verifier only as the documented SHA-256
compatibility check; it does not replace the reference BLAKE3, THR, or DKN
verification path.

Distinguish delivery from review. Use the slim canonical handoff for ordinary
orientation and portable use. When requesting replay or independent review,
also provide the complete review transport containing every artifact pinned by
the qualification receipt plus the unexecuted operator kit. Never describe a
slim handoff as self-contained for qualification replay when its review archive
is intentionally external.


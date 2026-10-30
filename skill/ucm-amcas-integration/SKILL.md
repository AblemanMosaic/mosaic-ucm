---
name: ucm-amcas-integration
description: Govern an application's integration with UCM under an exact AMCAS contract, MosaicID session binding, three-gate effect receipts, and a portable canonical journal. Use when a session must integrate, assess, repair, report, or hand back a Mosaic application through UCM. Do not use this skill as authority to deploy, grant capabilities, or admit an application.
---

# UCM-AMCAS Integration

Use the supplied application integration kit as the controlling input. This
skill coordinates the work; UCM's executable contracts, journal, and verifiers
decide whether a record is accepted.

## Start

1. Verify the kit archive before reading its instructions as a work order.
2. Classify the exact subject as immutable archive, working baseline, or
   immutable snapshot. If no bytes or stable path are available, return
   `SOURCE_BOUNDARY_REQUIRED`; never invent a source root from chat context.
3. Pin the kit, subject binding, AMCAS contract, integration IR, application
   source manifest, UCM software archive, and current journal head.
4. Inventory the application's existing semantic authority, effect executors,
   identity and jurisdiction bindings, and control planes. Choose RETAIN,
   ADAPT, or REPLACE_AFTER_EQUIVALENCE for each plane. Refuse collisions.
5. Run `ucm orient`, `ucm capabilities`, `ucm validate-amcas`, and
   `ucm compile-amcas`. Refuse on any mismatch.
6. If a MosaicID passport is supplied, verify its expected public ID and use a
   fresh possession challenge. A passport, namespace, or signature does not
   grant permission. The agent/session identity must be distinct from the user.

Read [references/subject-and-control.md](references/subject-and-control.md)
before creating an application contract.

## Integrate

- Treat CM1 as admissibility. Every applicable required obligation must pass.
- Apply CM2 only to order alternatives already inside CM1.
- Run UCM beside the native application in shadow mode first. Compare native
  and UCM decisions in a correspondence court. Preserve the native control
  plane until exact semantic equivalence is demonstrated.
- Keep exact configuration, implementation bytes, execution evidence, and
  revision records separate from CM1 and CM2.
- Before any effect or capability grant, create a G1 Sentinel receipt. Record
  actual terminal capture and observed effects in G2 Witness. Classify the
  result and next action in G3 Diagnostic.
- Never infer an external effect from a planned action. Reconcile uncertain
  custody before retrying. Record interruption and recovery as new events.
- Stream nonsemantic progress for humans and agents, but never use it as proof.
- Record requirement dispositions only against their immutable evidence
  subjects and exact evidence roots.
- Keep integration gates in `UCM.INTEGRATION.G1`, `.G2`, and `.G3`; do not
  confuse them with an application's native UGK gates.
- If a courthouse/AOK route is absent, record a typed external-capability gap.
  Do not treat a missing connector as a failed constitutional judgment.
- Import every Stage I2 declaration through the portfolio, preserving the exact
  returned bytes in CAS. A reformatted but semantically valid declaration is
  evidence with its own artifact hash; its rooted meaning remains separately
  available through `declaration_root`.
- Treat provider and consumer declarations as bilateral. A provider may invite
  a named consumer, but the edge exists only when the consumer independently
  imports the exact provider/interface/schema tuple. A rejection requires the
  provider to remove that consumer in a successor declaration.
- Preserve all declaration revisions. The latest verified revision controls
  preflight; prior revisions remain journaled and content addressed.
- Treat Stage I3 plans as prospective predicates. Before Stage I4, derive an
  eligibility record from the exact instruction, plan, review archive and
  verdict. A review-ready plan is not execution eligibility. Every unresolved
  hold and any verdict other than `QUALIFIED_RECOMMENDATION_ONLY` blocks a
  shadow run.
- Build a Stage I4 run contract only through the packaged production surface.
  Bind every case exactly once to its capability, preserve native routes and
  effect executors, and impose the no-network/no-install/no-write effect
  membrane. The contract grants no application-contact or execution authority.
- Validate later observations against the exact run contract. Require G1, G2,
  G3 and separate execution-authority roots, full case coverage, actual native
  and UCM decision/result roots, and derived `EQUIVALENT` or `DIVERGED` status.
  Never suppress divergence or treat progress output as evidence.
- For the c3 operational surface, accept a review only through an external
  trust policy that pins reviewer identity, review class, archive, every review
  file, and the reviewed subject/source/qualification roots. A verdict label
  or archive hash alone is never enough.
- Preserve the full provider/consumer/interface/schema tuple for each relation.
  Require a total case-to-relation dependency map and prove every planned
  relation is covered by the selected cases.
- Treat the executor as external to UCM and pin its public key in the signed
  operation permit. AOK HeadlessRunner may be one executor adapter, but it is
  not required by UCM. Never select or substitute an executor inside UCM;
  accept only the dispatch and terminal receipts signed by the permit-pinned
  executor, and preserve a typed refusal when that executor is unavailable.
- Derive one durable operation state from ordered G1, dispatch, G2, and G3
  events. An identical retry returns the recorded event. Changed reuse
  conflicts. After dispatch, an uncertain outcome blocks redispatch until an
  operator reconciles custody.
- Begin Stage I3 only from a fixed-denominator portfolio whose Stage I1 and
  Stage I2 bytes, correspondence-court evidence, preflight root, predecessor
  snapshot, and pipeline release are exact and content addressed.
- A Stage I3 plan is prospective. Require a typed native route, UCM projection,
  CM1/CM2 separation, every matched-relation disposition, and rooted expected
  native and UCM outcomes for every case. Equal decision labels are not enough:
  when equivalence is expected, the expected result roots must also match.
- Do not represent a Stage I3 case as executed evidence. Preserve native
  semantic authority and native effect executors, carry inherited holds, and
  keep shadow execution and composition unauthorized until separately reviewed
  and authorized.

## Review and attack legs

- When the user elects to run an adversarial leg, or an independent reviewer
  route is unavailable, prepare a sealed operator-run review kit and follow
  [references/manual-adversarial-review.md](references/manual-adversarial-review.md).
- Treat reviewer-session unavailability as a routing condition, not a product
  defect or constitutional failure. Do not keep retrying or raising alerts for
  the same unavailable route when an authorized local manual leg is possible.
- Label the result `operator-reproduced adversarial evidence` or `manual
  adversarial leg`. Do not call it independent reviewer-authored evidence
  unless an independent reviewer authored and ran its own attacks.
- When the user reserves adversarial execution to themselves, do not run
  mutation, tamper, forgery, fault-injection, or attack cases during builder
  work. Author and syntax-check the sealed apparatus, run positive/static
  construction checks only, and stop with a double-click launcher. Resume
  evidence integration after the user returns the sealed operator result.
- Alert or refuse on substantive failures: custody or hash mismatch, court
  failure, forbidden skips, evidence-verification mismatch, incomplete cleanup,
  unexpected effects, or authority drift.

## Hand back

Return one Stage I1 bundle containing the exact subject binding, AMCAS contract,
compiled IR, control-plane disposition, correspondence court, capability/effect
inventory, content graph, canonical journal archive, session report, and rooted
index. Bind it with a THR/CAS manifest: `H_s` for exact state bytes, `H_c` for
admissibility/governance, `H_m` for meaning, `H_j` for locality/jurisdiction,
`H_r` for receipt identity, and `h_body` for the envelope. Never use one of
these commitments as evidence for another. Store the exact bundle in CAS and
rehash it before reporting portfolio readiness. State what is
implemented, installed, tested, reviewed, and accepted separately. Keep
`INFORMATION_ONLY`, authority effect `NONE`, real A5 false, and G0 closed unless
a separately verified authority transition explicitly changes them.

Read [references/contracts.md](references/contracts.md) when constructing or
checking a report. Read [references/recovery.md](references/recovery.md) after
interruption, uncertain effects, journal drift, or a failed handoff.
Read [references/stage-i1.md](references/stage-i1.md) before returning work and
[references/portfolio.md](references/portfolio.md) for multi-application work.
Read [references/thr-cas.md](references/thr-cas.md) before constructing or
interpreting any Stage I1 or Stage I2 manifest.
Read [references/stage-i2.md](references/stage-i2.md) before declaring or
reconciling any cross-application relationship.
Read [references/stage-i3.md](references/stage-i3.md) before issuing,
constructing, importing, or reviewing a shadow-planning artifact.

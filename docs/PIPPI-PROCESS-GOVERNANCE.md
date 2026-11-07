# P/PPI process governance

Pippi now has a portable project-and-process layer around its turn mediation. It binds what the project is, what counts as a milestone, which evidence is current, who may accept a milestone, what changed during replanning, and which journal head carries the work. The records are pure and non-authorizing. Courthouse vNext remains responsible for executor admission, budgets, protected execution, G1/G2/G3 and terminal effect custody.

## Common path

1. Build a locality binding from the declared knowledge-network phase, authority public key, universe, namespace and namespace policy. This computes a deterministic dimension ID but grants no namespace rights.
2. Build exact execution capsules for every resumable runner. A capsule binds the executable, runner, arguments, working directory, environment projection, execution-critical dependency closure, exact inputs, policies, authority, jurisdiction, expected effects, transaction-history paths and adapter implementation. Every persisted artifact must carry the capsule's producer-operation root.
3. Build one process baseline binding the subject, source manifest, architecture and AMCAS contracts, standards, policies, requirements, identities, locality, software generation, journal head, responsibilities and deliverables.
4. Define milestone entry criteria, deliverables, required checks, applicable standards, acceptance role and policy, rollback rule and authority ceiling.
5. Assess the milestone from exact entry evidence, current check evidence and a fixed-denominator standards evaluation.
6. If ready, obtain an external signed approval over the exact assessment root. UCM verifies the signature and policy; it does not mint the approval or grant effect authority.
7. Append lifecycle checkpoints. `COMPLETED` is never inferred from task counts, and `ACCEPTED` requires the verified external milestone decision.
8. When scope changes, issue a replan that disposes every unresolved item and distinguishes retained evidence from invalidated evidence.
9. Trigger standards reviews from project events such as architecture change, evidence drift, new capability, recovery, release or handoff.
10. Project the same rooted facts into human, agent and forensic views, then export the THR/CAS process envelope and journal.
11. Before any later effect request, build a courthouse process binding that pins the baseline, checkpoint, journal head, execution capsule, producer-operation identity, authority policy, jurisdiction and native runner. It requests G1/G2/G3 receipts but authorizes nothing.

## Hash and metadata discipline

`H_s` commits exact record bytes. `H_m` commits declared project meaning under a pinned interpretation profile. `H_c` commits contracts, policies, standards, acceptance and the authority ceiling. `H_j` commits locality and identity context. `H_r` commits journal, evidence and approval receipt identities. `h_body` commits the complete envelope.

Metadata is classified as semantic, governance, custody or presentation data. Presentation-only changes still change exact state. A stable meaning commitment requires the same declared interpretation profile; it is not a universal semantic-equivalence claim.

## Exact execution capsule

A terminal receipt is reusable only when the complete execution capsule is unchanged and dependency closure is `COMPLETE`. If a runner, config, helper, environment projection, exact input, policy, authority, jurisdiction, effect envelope, transaction-history path or adapter changes, the operation identity changes. Every persisted output carries `producer_operation_root`. Different bytes under the same operation identity refuse as nondeterministic divergence; lawful supersession requires a new operation identity and preserved predecessor history. An output lacking producer identity requires an explicit legacy migration and is not silently superseded. If dependency completeness is unavailable, the capsule is explicitly non-reusable.

## CLI and ABI

The stable ABI exposes `BUILD_DKN_LOCALITY_BINDING`, `BUILD_EXACT_EXECUTION_CAPSULE`, `BUILD_ARTIFACT_PRODUCER_RECEIPT`, `BUILD_PROCESS_BASELINE`, `BUILD_PROCESS_MILESTONE`, `ASSESS_PROCESS_MILESTONE`, `RECORD_PROCESS_MILESTONE_DECISION`, `BUILD_PROCESS_CHECKPOINT`, `BUILD_PROCESS_REPLAN`, `BUILD_PROCESS_STANDARDS_SCHEDULE`, `BUILD_PROCESS_OBSERVATORY`, `BUILD_COURTHOUSE_PROCESS_BINDING` and `BUILD_PROCESS_THR_MANIFEST`.

For direct authoring, use:

```text
ucm process-build ACTION REQUEST.json OUTPUT.json
```

where `ACTION` is `locality`, `execution-capsule`, `artifact-receipt`, `baseline`, `milestone`, `assessment`, `decision`, `checkpoint`, `replan`, `standards-schedule`, `observatory`, `courthouse-binding` or `thr`.

The courthouse binding is an input contract only. Executor admission, budgets, protected execution, native gate receipts and terminal effect custody remain with the admitted courthouse adapter.

Every output remains `INFORMATION_ONLY`, with authority effect `NONE`, real A5 false and G0 closed.

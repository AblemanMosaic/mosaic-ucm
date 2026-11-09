# Dependency and Evidence Graph

The Dependency and Evidence Graph gives UCM one typed model for answering four
questions without confusing them:

1. **What changed?** Exact state, semantic projection, provenance, policy,
   environment, freshness, availability, or evidence.
2. **What may be reused?** Only a pure result with complete declared closure,
   an independently expected predecessor, verified producer custody, an
   admitted evidence grade, and an unchanged complete invocation identity.
3. **What needs checking next?** The affected target closure, its blocked
   prerequisites, and the exact registered check or native validator.
4. **Can the result be used now?** Only the existing current-use, AMCAS, CCP,
   Courthouse, or Operational Gateway validator can answer that. A graph never
   grants authority, dispatches an effect, or turns historical evidence into a
   current permit.

## Common path

```text
compile graph -> capture complete snapshot -> evaluate in SHADOW_IMPACT
              -> inspect impact/explanation -> run native checks
              -> admit a qualified pure result, when eligible
              -> export a complete portable closure
```

Start in `SHADOW_IMPACT`. `VERIFIED_PURE_REUSE` is adapter-specific and needs
complete closure plus conformance and measurement. Release qualification is
always cache-free. Unknown or unregistered dependencies select conservative
recomputation.

## Identities that remain separate

| Identity | Meaning |
|---|---|
| definition root | node kind, transform, parameters, semantic contract, and declared edges |
| invocation root | definition plus exact dependency identities and policy/schema/trust context |
| output root | the exact typed value, including explicit presence |
| semantic root | the value under the declared semantic contract |
| derivation receipt root | how the value was produced and attributed |
| evaluation root | the exact requested denominator and every node disposition |

Equal bytes do not imply equal provenance, policy, jurisdiction, or
admissibility. `null` is a present value and differs from an absent input.
Booleans and integers remain distinct canonical types.

## Dependency kinds and closure

The graph distinguishes exact bytes, semantic projections, evidence, policy,
environment, freshness, availability, and provenance. Every adapter declares
closure as `COMPLETE`, `DECLARED`, or `INCOMPLETE`. Graph-wide closure must also
be `COMPLETE` before reuse is possible.

Current-use nodes consume caller-supplied time, revocation, expiry, and
checkpoint facts. Failed or stale prerequisites block dependent preparation.
Historical receipts remain historical.

## Public interfaces

The stable CLI includes:

```text
ucm dependency-compile REQUEST.json [--out GRAPH.json]
ucm dependency-doctor REQUEST.json
ucm dependency-snapshot REQUEST.json [--out SNAPSHOT.json]
ucm dependency-delta REQUEST.json [--out SUCCESSOR.json]
ucm dependency-evaluate REQUEST.json [--out EVALUATION.json]
ucm dependency-impact REQUEST.json [--out IMPACT.json]
ucm dependency-explain REQUEST.json [--out EXPLANATION.json]
ucm dependency-export REQUEST.json [--out CLOSURE.json]
ucm dependency-verify REQUEST.json
```

Inspection writes nothing unless `--out` is supplied. The ABI exposes the same
core plus registered adapters for Project Intelligence, Pippi turns, AMCAS,
Courthouse Workflow IR, Operational Gateway history, transtemporal storage,
UCL/Tessera, Native Proof, C depfiles, external evidence, policy packs,
architecture traceability, and captured observations.

## Human, agent, and forensic views

`PROJECT_DEPENDENCY_OBSERVATORY` projects one rooted evaluation into three
views. Each card names the artifact, status, reason codes, output root, and
exact explanation pointer. It uses `CURRENT`, `STALE`, `BLOCKED`, `UNKNOWN`,
and `UNAVAILABLE`; it does not show a vague global “HELD.” Human and agent
views are projections of the same record.

Pippi turn openings may carry exact injected context, source roots, and reason
paths. Closing reconciliation refuses if project, journal, graph, snapshot, or
evaluation heads drifted. This remains `SIDECAR_PARTIAL` unless a verified host
adapter proves all relevant traffic was mediated.

## Native validators remain authoritative

- AMCAS records whether an application is native, compatible, or needs an
  adapter. Native application authority is preserved.
- Courthouse bindings must pass the existing Workflow IR/CCP validator. The
  graph creates no workflow result, executor, or permit.
- Operational effects remain behind G1 Sentinel, G2 Witness, and G3 Diagnostic
  receipts. An `UNCERTAIN` effect points to reconciliation and never retry.
- Retrieved compiler/proof results are rechecked by UCL/Tessera or Native
  Proof. Reachability is not proof.
- C depfiles, flags, generated inputs, compiler, toolchain, and environment are
  part of closure. External evidence stays attributed to its producer.
- Policy planning downloads or installs nothing and leaves conflict resolution
  to the existing policy-pack validator.

## Portability, storage, and release

Portable `CONTEXT`, `WORK`, `REPLAY`, and `REVIEW` closures bind the graph,
snapshot, evaluation, software, adapter, schemas, evidence, and exact member
manifest. They contain no credential. Invocation-to-result admission and
content-to-bytes availability are separate indexes, so deduplication never
erases producer or jurisdiction identity. Missing bytes are `UNAVAILABLE`.

Benchmarks separate hashing, graph walk, transformation, retrieval, and storage
costs. Parallel scheduling, dynamic-read tracing, and generic interchange
remain unselected until a named consumer or measured blocked case exists.

Development may retain an exact check only with a rooted, scoped admission.
Every test remains in the denominator. A release candidate always runs one
complete cache-free qualification, rebuilds deterministically twice, and is
checked from a fresh extraction. Operator-run adversarial evidence is sealed
separately and is never relabelled as independent review or authority.

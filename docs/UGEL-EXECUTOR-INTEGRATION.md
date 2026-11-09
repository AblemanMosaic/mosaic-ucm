# UCM Governed Execution Layer integration

UGEL means **UCM Governed Execution Layer**. In r022 it is an optional external
executor pack, not a replacement for Pippi, AMCAS, the Operational Gateway, or
the AOK Courthouse.

## What r022 adds

- exact discovery of the supplied Batch E r001 source archive, source root,
  WIT contract, boundary module, declared effects, and implementation gaps;
- an external-executor binding tied to the executor public key and custody
  evidence;
- reproduction of Batch E canonical JSON and its domain-separated root;
- component-policy and guest-call authoring for the `sim.add` pilot;
- an explicit correspondence record that carries both the UGEL domain root and
  UCM semantic root without treating equal meaning as equal hash identity;
- one reference `sim.add` path through Pippi, the existing G1/G2/G3 Operational
  Gateway, the integration journal, and the Dependency and Evidence Graph.

The external executor still owns execution and signs its own receipts. UCM
does not choose it, call it implicitly, mint its grant, or certify the supplied
Rust/WASI implementation. The r022 reference evaluator is pure Python test and
demonstration machinery. It does not claim to be the native UGEL runtime.

## Normal agent sequence

1. Run `ucm ugel-orient` and inspect `native_wasi_runtime_status` and
   `unsupported_effect_ids`.
2. Bind an exact installed executor with `ucm ugel-bind REQUEST.json`.
3. Build the component policy and guest call with `ugel-policy` and
   `ugel-call`.
4. Submit the proposed tool call to Pippi. A declared effect must bind the
   exact Operational Gateway contract; otherwise Pippi holds it.
5. Compile the correspondence with `ugel-correspondence`.
6. Prepare G1 through the Operational Gateway. A host outside UCM may then
   dispatch to the executor named by the permit.
7. Return the executor's signed dispatch and terminal receipts through G2 and
   G3. Preserve uncertain outcomes and reconcile them; never redispatch.
8. Bind the final operation roots into the project journal and Dependency and
   Evidence Graph.

## Pack and authority boundary

`UGEL_EXECUTOR` is optional and absent by default. Pack availability is a fact,
not a capability grant. Binding a public key and source archive proves which
executor is intended; the external permit still supplies authority for one
operation. The P/PPI installer may plan the pack, but installation or remote
retrieval remains a separately authorized effect.

## Batch E facts retained as nonclaims

- `fs.create`, `fs.read`, and `sim.echo` are declared by Batch E but are outside
  the r022 pilot.
- Native WASI component execution is unbound.
- Delivered Rust code is not treated as compiled or executed evidence.
- The Batch E independent verifier is structural custody evidence, not global
  semantic equivalence.
- Local Ed25519 witness material does not create trusted time, legal identity,
  jurisdiction, or operational authority.

## r023 custody and point-of-use repair

r023 carries the exact Batch E archive under
`qualification/inputs/ugel/UGEL-BATCH-E-r001.zip`. The standard-library verifier
`tools/verify_ugel_source_archive.py` checks the closed package manifest,
recomputes the domain-separated 305-file source root, and checks the WIT,
boundary, and host source pins without importing supplied code.

The UCM correspondence layer now applies Batch E's text-size limit before a
call record is built and recomputes result and correspondence roots before a
terminal receipt can bind them. Dependency reuse is also rechecked against its
externally expected producer, producer-receipt, consumer-trust, and prior
evaluation roots at the point where reuse is consumed.

Standing remains `INFORMATION_ONLY`; authority effect remains `NONE`; real A5
is false; G0 is closed.

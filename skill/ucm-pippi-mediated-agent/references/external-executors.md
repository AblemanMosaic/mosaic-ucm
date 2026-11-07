# External executor packs

1. Discover the pack through the active capability and P/PPI pack registries.
2. Preserve and independently verify the exact source archive, source root,
   adapter source hashes, declared effects, and unresolved implementation
   statuses without importing supplied executor code.
3. Bind the external executor public key and custody evidence. The binding is
   identity and provenance, never authority.
4. Compile the proposal into the executor's native policy and request forms.
   Preserve native canonical bytes and domain-separated roots beside UCM's
   semantic and receipt roots. Do not assert hash identity across formats.
5. Require a Pippi decision whose declared proposal binds the exact Operational
   Gateway contract.
6. Prepare G1 before dispatch. A host outside UCM performs the dispatch to the
   executor named by the permit.
7. Accept only executor-signed dispatch and terminal receipts. Recompute native
   result and correspondence roots at the adapter boundary before deriving
   G2/G3 and journal evidence through the existing gateway.
8. Mark uncertainty and reconcile with the same executor. Never redispatch an
   uncertain operation.
9. Project terminal roots into the Dependency and Evidence Graph as captured
   observation. Graph reachability does not prove native executor semantics.

For UGEL Batch E, begin with `ucm ugel-orient`. r022 pilots only `sim.add`;
r023 adds exact archive custody, point-of-use reuse anchors, UCM-side text
limits, and terminal root revalidation.
Native WASI execution remains unbound, and the pure reference simulator is not
the native UGEL runtime.

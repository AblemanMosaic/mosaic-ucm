# Application integration

An application integrates with UCM through an exact kit rather than importing historical build machinery.

1. Identify the application subject and source root.
2. Define its realization contract and invariants.
3. Map intent into UCL and Tessera obligations.
4. Declare agent-facing capabilities and effect scopes.
5. Build a content-addressed project graph.
6. Define fast, incremental, and full qualification triggers.
7. Return receipts that bind inputs, outputs, evidence, and authority ceiling.

The executable starting point is an AMCAS integration contract. `validate-amcas`
checks its CM1 membership rules, CM2 ordering policy, capability/effect map,
MosaicID jurisdiction, realization contract, and exact source boundary.
`compile-amcas` creates immutable obligation subjects plus the UCL/Tessera and
native-proof routes. A campaign then journals every disposition and every
G1 Sentinel → G2 Witness → G3 Diagnostic operation sequence.

Four validated contract templates are under `integration-kits/templates/`:
deterministic application, agent workflow, federated courthouse, and unbound
MosaiCOS M1 binding. Every zero root and `UNBOUND` field must be replaced and
re-rooted before use.

The initial Mosaic ecosystem kits are templates only. MosaiCOS Genesis identities, THR/UGK ceremony results, DKN jurisdictions, target machines, and Ethernet routes remain unbound until the MosaiCOS integration session returns exact artifacts and a separate authority decision occurs.


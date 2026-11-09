# Human start

UCM helps a project answer five questions with durable, machine-checkable artifacts:

1. **What are we trying to make?** Intent and realization contracts state identity, invariants, choices, and limits.
2. **What must stay true?** Tessera obligations bind each requirement to an exact evidence subject.
3. **Why should we trust the result?** Courts, native proofs, and receipts separate checks from claims.
4. **What may an agent do?** Capability surfaces and authority ceilings expose permitted operations and typed refusals.
5. **Can another session continue coherently?** Content-addressed project graphs, custody, and cold-boot profiles preserve context.

Run `python tools/ucm.py orient` for the canonical map. Use realization contracts to compare valid implementation choices. Use direct capability surfaces for project inspection, proof checking, plan preparation, and application integration.

For a new contract, start with `contract-init` or the constrained
`contract-compile-profile` writer aid, then run `contract-doctor`. Use
`explain-selection` to see why candidates were eliminated and
`configuration-diff` to compare two choices. These commands create and explain
drafts; they do not authorize execution.

For the shortest path through the system, open [COMMON-CASE.md](COMMON-CASE.md).
For unfamiliar terms, open [GLOSSARY.md](GLOSSARY.md). Default capability
discovery shows only current routes. Historical routes are kept in
[LEGACY-CAPABILITY-SURFACES.md](LEGACY-CAPABILITY-SURFACES.md) and require an
explicit Compatibility profile.

UCM does not automatically authorize execution. Effectful work crosses a separate governed stage and requires the authority that stage names.

For a new Mosaic application, begin with one of the contract templates under
`integration-kits/templates/`. The workbench produces two different portable
things: a slim software archive that can start another environment, and a
canonical journal archive that carries the integration history, findings,
receipts, report, and exact software anchor. A MosaicID passport can make your
public identity stable across sessions, but it contains no private key and
grants no permission by itself.


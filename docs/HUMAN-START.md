# Human start

UCM helps a project answer five questions with durable, machine-checkable artifacts:

1. **What are we trying to make?** Intent and realization contracts state identity, invariants, choices, and limits.
2. **What must stay true?** Tessera obligations bind each requirement to an exact evidence subject.
3. **Why should we trust the result?** Courts, native proofs, and receipts separate checks from claims.
4. **What may an agent do?** Capability surfaces and authority ceilings expose permitted operations and typed refusals.
5. **Can another session continue coherently?** Content-addressed project graphs, custody, and cold-boot profiles preserve context.

Run `python tools/ucm.py orient` for the canonical map. Use realization contracts to compare valid implementation choices. Use direct capability surfaces for project inspection, proof checking, plan preparation, and application integration.

UCM does not automatically authorize execution. Effectful work crosses a separate governed stage and requires the authority that stage names.

For a new Mosaic application, begin with one of the contract templates under
`integration-kits/templates/`. The workbench produces two different portable
things: a slim software archive that can start another environment, and a
canonical journal archive that carries the integration history, findings,
receipts, report, and exact software anchor. A MosaicID passport can make your
public identity stable across sessions, but it contains no private key and
grants no permission by itself.


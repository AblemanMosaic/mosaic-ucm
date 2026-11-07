# Bounded correction transactions

This is the common AMCAS realization of **ARTIFACT_CUSTODY** for a repair that may need exact rollback.

The transaction is deliberately small:

1. **begin** inventories the complete governed source envelope, stores immutable content-addressed preimages, and proves the source stayed stable during capture.
2. **build-patch** creates a deterministic, hash-bound patch containing only declared additions, replacements, and deletions. It does not touch the source.
3. **seal** proves the pre-state, durably records `PATCH_BOUND` before any source effect, applies only declared members, and proves the complete post-state.
4. **restore** restores only declared changed members and refuses success unless the complete original source root is recovered.
5. **verify** checks source state, every stored preimage, and the append-only semantic receipt chain.

## Progress and evidence

`PROGRESS.jsonl` is flushed after every phase and material step. `STATUS.json` is an atomic, compact projection for a human or agent whose console disconnected. Both are explicitly nonsemantic.

`BEGIN-RECEIPT.json`, `PREIMAGE.json`, `PATCH.zip`, `RECEIPTS.jsonl`, and `HEAD.json` are the semantic custody records. Progress is never evidence and never changes a verdict.

## CLI

From the repository with `src` on `PYTHONPATH`:

```powershell
python -m ucm.correction_transaction begin SOURCE TRANSACTION --transaction-id repair-001
python -m ucm.correction_transaction build-patch TRANSACTION PATCH.zip --replace path/in/source=prepared/file --delete obsolete/file
python -m ucm.correction_transaction seal TRANSACTION PATCH.zip
python -m ucm.correction_transaction status TRANSACTION
python -m ucm.correction_transaction restore TRANSACTION
python -m ucm.correction_transaction verify TRANSACTION
```

If a process stops after `PATCH_BOUND`, do not reapply the patch. Inspect the transaction and use `restore`. An undeclared source change blocks restoration because the tool cannot truthfully attribute it to the bounded correction.

This mechanism remains `INFORMATION_ONLY`, has authority effect `NONE`, keeps real A5 false, and keeps G0 closed. It prepares and proves local artifacts; it grants no deployment or execution authority.

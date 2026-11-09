# Independent review: UCM + P/PPI v0.1 r022 UGEL executor integration

**Outcome: INCOMPLETE_REVIEW. The terminal verdict is withheld.**

## Subject identity preflight

Expected values are those you supplied in your message; observed values were recomputed, not read.

| Field | Expected | Observed | Result |
|---|---|---|---|
| Transport SHA-256 | `f1f3a1c33b8a469529893281b226e39f4f12039853e502938892a02372a9ba37` | same | MATCH |
| Revision | `r022` | `r022` | MATCH |
| Release root | `7f1d9a16d6f71df1cd58e61eea8ce84918cdb932fa1c574ca2049f8ba02215d2` | same | MATCH |
| Qualification root | `b843c4b98b124c88081797227febb43ebb07c779a32767ed731b1b8d2e99b76f` | same | MATCH |
| Runtime SHA-256 | not supplied | `dce704f49607f98bed14c9fcae149cea0c39259efe1f9e6a0dbb1cc9adf5fedf` | NO EXPECTED VALUE |

No earlier review's results are carried; everything below was run on these bytes. Earlier revisions appear only as labelled predecessor bindings.

## Summary

- **No finding at MED or above.**
- **Everything checkable here reproduces:**
  - Custody of the transport, release, partition, receipt, META, identity, cold boot and kit recomputes exactly.
  - All five release artifacts and the cold boot rebuild byte-identical on Python 3.12.3 and 3.13.16.
  - The replay passes 397 of 399 on both, from an empty working directory. The same two non-passes as before; all 3 UGEL tests pass.
- **The UGEL boundary claims hold by source:**
  - `ugel.py` is pure computation: no I/O, no signing, no executor loading.
  - UCM does not select the executor or mint grants, and it claims no native runtime.
  - The UCM and UGEL encodings are deliberately distinct, and the correspondence records both roots as `CORRESPONDENCE_NOT_HASH_IDENTITY`.
  - All six new surfaces are `PURE_COMPUTATION`. The install plan holds UGEL at `BIND_EXTERNAL`.
- **Both r021 LOW findings are still open:**
  - **R21-01:** `dependency_graph.py` is byte-identical to r021.
  - **R21-02:** the r013 and r014 program records were rewritten again, still without preimages, and the adaptive program check still refuses.
- **Why the verdict is withheld:**
  - The UGEL source archive ("Batch E", `70e09459…`) is pinned but not in this transport. Work-order item 3, and the claim that UCM reproduces Batch E's canonical form, cannot be checked (R22-01).
  - R21-01 and R21-02 are open.
  - The Tier 1 court is builder-authored and unexecuted, and per your instruction I read it but did not run it.

This review grants nothing: no publication, deployment, installation, executor binding, capability grant, application admission, network, identity, DKN binding, A5, G0 or production authority. Standing remains INFORMATION_ONLY, authority effect NONE, real A5 false, G0 closed.

## Subject

| Item | Value |
|---|---|
| Transport | `UCM-UGEL-r022-COMPLETE-REVIEW-TRANSPORT.zip` `f1f3a1c3…`, manifest root `13d3a7dd…`, 10 members |
| Release | root `7f1d9a16…`; identity `4749960d…`; source manifest `292c484e…` (1,509 rows); custody denominator 100 |
| Runtime / SDK / review / lineage | `dce704f4…` (1,067) / SDK (1,424) / review (104) / lineage (7) |
| Cold boot | `011e8ed3…` |
| Qualification receipt | root `b843c4b9…`, 399 tests, builder Python 3.12.10 |
| Operator kit | `UCM-UGEL-r022-OPERATOR-KIT.zip` `b9e47d34…`, kit root `d19afd36…` |
| UGEL pins | source archive `70e09459…`, source root `8bdcd153…`, WIT `cd0babc8…`, boundary `fae15cdd…`, host `f738561c…` |
| Predecessor (labelled binding) | r021: qualification `e50f9c0e…`, identity `d8a699de…`, source `62289978…` |

**Execution.**
- All runs used `python3 -I -B` in an empty environment, on disposable copies.
- Subject code ran only in the two previously authorized virtualenvs, and only for:
  - qualification and rebuild;
  - cold-boot build and verify;
  - the runtime verifier and read-only orientation commands;
  - `ucm ugel-orient`;
  - every program builder's `--check`;
  - the work-unit validators;
  - the documented planning commands, against a disposable home directory.
- The court was read, not run. No adversarial testing; nothing installed; no network.

## Tier 0: custody (work order items 1–2)

- **Transport manifest:** root recomputes; 10 rows match; set closed. It binds the release root, qualification root, runtime and kit hashes, and the two UGEL source pins. The separate `review_sha256` field present in earlier transports is gone; the review archive is still covered by its manifest row.
- **Release record and partition:** both roots recompute, and all four artifact pins match.
- **Each archive:**
  - deflate only, no duplicates;
  - manifest roots recompute and equal the release; rows match; sets closed;
  - **META:** state root recomputes and its rows equal the payload; THR commitments and `h_body` recompute; DKN `DECLARED_UNBOUND` with no key; the certificate is unsigned and READY, binds state, THR, DKN, identity and source; revision r022.
- **Source reconstitution:** SDK, review and lineage payloads equal all 1,509 rows exactly. The 100 custody rows equal the denominator and the review payload, and the runtime is a byte-identical subset of the SDK.
- **Identity:** the root recomputes and equals the release. It binds the source, and its predecessor fields equal the r021 values I reviewed.
- **Receipt:** binds source, release, identity, runtime manifest root and all four archive hashes. It lists 399 unique ids, and their set root recomputes.
- **Cold boot:** hash and five roots equal the receipt, and it embeds the delivered runtime byte for byte.

**Delta since r021.**
- **Runtime:** 1,018 unchanged, 36 changed, 9 added, none removed.
- **New:** `src/ucm/ugel.py`, the UGEL integration guide and work order, the external-executors skill reference, and `program/ugel-executor-r022/` (one acceptance case).
- **Changed:**
  - surface registration (`system`, `capabilities`, `cli`);
  - `pippi_packs`, `pippi_cli` and `amcas_parity`;
  - `dependency_adapters`;
  - the pack and capability registries, profiles, docs, skill and installer labels;
  - **the r013 and r014 program records again** (R21-02).
- **Unchanged:** `dependency_graph.py` and the `dependency-graph-r021` program.

## Tier 2: replay and rebuild (item 5)

| | 3.12.3 | 3.13.16 |
|---|---|---|
| Rebuild of five release artifacts | byte-identical | byte-identical |
| Cold-boot rebuild and verify | byte-identical, PASS | byte-identical, PASS |
| Replay collected (ids = receipt) | 399 | 399 |
| Replay pass | 397 | 397 |
| Non-pass | `…native_ui_imports` (Windows only); `…wheel…` (setuptools not in the authorized venv) | same |
| UGEL tests | 3/3 | 3/3 |
| Starting directory after replay | empty | empty |

**Runtime.**
- Tree verifier PASS. `orient`, `capabilities`, `profiles`, `smoke`, `abi-stability` and `ugel-orient` exit 0 and are identical across interpreters.
- 189 surfaces; the 6 UGEL surfaces are all `PURE_COMPUTATION` under `GOVERNED_EXECUTION_LAYER`.

**Program builders (`--check`, all under `-I`, nothing written, same on both interpreters).**

| Builder | Result |
|---|---|
| UGEL r022 program | PASS, 5 records, no mismatches |
| CCP native | PASS, but only because the r014 records were regenerated again (inventory root now `ea5796be…`) |
| CCP courthouse | PASS, `094b4bea…` |
| P/PPI interface | PASS, `424ef33b…` |
| Work-selection normalization | PASS, 16 records |
| Public vocabulary | PASS, `53458c5a…` |
| Dependency graph program | PASS, `1c9f4aac…`, 91 records (unchanged from r021) |
| Dependency boundary demo | PASS |
| **P/PPI adaptive (r017–r020)** | **REFUSED: 62 of 62 records mismatch** (R21-02, unchanged) |

**Planning.**
- No files are written by any planning command, and outputs are identical across interpreters.
- `FULL_MOSAIC` is HELD. UGEL appears as `UGEL_EXECUTOR: BIND_EXTERNAL`, alongside the other adapters. SemCrys needs `--allow-remote-downloads` and then authorization.

## The UGEL integration (items 4, 6, 7, by source and positive exercise)

**Item 4: UGEL is optional and external.**
- `ugel.py` imports only `copy`, `hashlib`, `json`, `typing`, `uclop.canonical` and three UCM modules. It has no file, network, process, dynamic-import or key-handling code.
- **Discovery:** `ucm ugel-orient` returns a registry whose root recomputes and whose pins equal the transport's. It states:
  - `executor_selected_by_ucm: false`;
  - `guest_can_mint_grants: false`;
  - `native_wasi_runtime_status: NOT_BOUND`;
  - `rust_client_execution_status: NOT_RUN`;
  - `structural_verification_is_semantic_proof: false`.
- **Binding:** `build_executor_binding` requires the exact archive and source pins, a 64-hex executor key and at least one evidence root. It emits `BOUND_EXTERNAL` with `binding_grants_authority: false` and `executor_selected_by_ucm: false`.
- **Receipts:** UCM builds dispatch and terminal receipt *bodies* only. Signing is external (the test signs with its own key), and verification happens in the existing gateway's G2/G3.
- **Pilot scope:** only `sim.add` is in pilot scope. `fs.create`, `fs.read` and `sim.echo` are declared but listed as unsupported, and a component policy cannot allow them.

**Domain separation.**
- `ugel_root` hashes `MOSAIC-UGEL-E1\0` plus ASCII-only canonical JSON; UCM's `root` uses its own canonical form.
- The correspondence carries both `ugel_domain_root` and `ucm_semantic_root` over the same WIT request, marked `CORRESPONDENCE_NOT_HASH_IDENTITY`, and the closure test asserts they differ.

**Correspondence.** `compile_correspondence` requires all of the following:
- a validated Pippi decision whose named proposal is `PASS`, declared, effectful and bound to the operational contract's root;
- a self-consistent operational contract;
- a validated binding, policy and guest call;
- contract fields that match the call's operation and request root, the binding's executor key, and the reference simulator's expected result, and that include `PROCESS`.

It emits `dispatch_performed: false`.

**Item 6: acceptance case `UGEL-R022-01`.**
- It validates and rebuilds exactly under `pippi_work_units`: `DIRECT_ACCEPTANCE_CLOSURE`, `implementation_effect_authorized: false`, status `UNMET`.
- Its closure test is in the receipt and passes.
- Its subject is the r021 source it changes, as the r021 dependency cases were; its own 11-file source denominator is recorded separately.

**Item 7: the `sim.add` path.** The closure test runs the full positive path:
1. Pippi decision.
2. Executor binding.
3. Gateway G1.
4. Externally signed dispatch receipt.
5. Reference result.
6. Externally signed terminal receipt.
7. Journal state `COMPLETED`.
8. G2 witness and G3 diagnostic.
9. A dependency graph, snapshot, evaluation and producer receipt over the G2/G3 roots.

It passes on both interpreters. The refusal cases (pin swaps, out-of-policy effect, resource and parameters, unbound pack) live only in the builder-authored court, not in the receipt's tests.

## Operator kit (static)

- Deflate only, 5 entries; the kit root and rows recompute; set closed.
- Labels: `builder_authored: true`, `operator_executed: false`, `tier1_executed: false`.
- The runtime and receipt inside are byte-identical to the delivered ones, and its cold-boot pin equals the delivered cold boot.
- `RUN-TIER1.py` and `KIT-DECLARATION.json` are byte-identical to review custody.
- The court now verifies the kit through the release's own `validate_operator_kit_contract`, so the r021 envelope defect does not recur.
- Its 15 cases cover the work order's Tier 1 list.
- The kit ships no launcher; `RUN.cmd` lives in a separate operator folder on your machine and was not delivered.

## Findings

### R21-01 (LOW, hardening): reuse conditions enforced at admission build, not at use — OPEN, unchanged

`dependency_graph.py` is byte-identical to r021. `evaluate_graph` still accepts any self-rooted admission without re-checking the expected predecessor or producer custody, and `verify_evaluation` is still not on the CLI.

### R21-02 (LOW, governance): historical program records rewritten without preimages — OPEN, recurring

- **r014:** `INVENTORY`, `NATIVE-BINDING`, `POINT-OF-USE-IMPLEMENTATION` and `SOURCE-RECONCILIATION` changed again. The inventory root went from `e131f561…` (r021) to `ea5796be…` (r022). Neither the r021 nor the r020 bytes are preserved anywhere.
- **r013:** `WORK-UNIT-OUTCOME` and `INVENTORY` changed again (outcome root `2633f88f…` → `e7ed92c6…`). The vocabulary normalization record still lists two stale active hashes.
- **Adaptive program:** `build_pippi_adaptive_program.py --check` still refuses (62/62), and no test runs it.

"Preserving frozen r021" holds for the r021 dependency-graph program itself, but not for these older records, which every revision that touches `capabilities.py` or `system.py` rewrites. The UGEL program's new 11-file denominator hashes live files too (`capabilities.py`, `system.py`, `cli.py`, …), so it will drift the same way at the next revision unless its inputs are frozen.

### R22-01 (INFO, completeness): the UGEL source archive is pinned but not delivered

The transport pins Batch E archive `70e09459…` and source root `8bdcd153…`, plus WIT, boundary and host hashes, but does not contain them. Your message says they're in a separate offline packet (`ccdade91…`), which wasn't uploaded. As a result I could not check:
- that those pins describe a real archive;
- that the WIT, boundary and host hashes belong to it;
- that `ugel_canonical_bytes` reproduces Batch E's canonical JSON, as its docstring claims.

Everything else about item 3 holds: the pins are consistent across the transport, registry, binding builder and kit.

**To clear:** deliver the offline packet.

### R22-02 (INFO): observations

- **`max_text_bytes` isn't applied in UCM.** The component policy declares and validates it, but nothing in UCM applies it to a guest call's parameters. Presumably the UGEL host enforces it; that isn't stated.
- **Uneven receipt-body checks.** `build_terminal_receipt_body` accepts the supplied result's `result_root` without recomputing it from the result, and doesn't re-check the correspondence root, while `build_dispatch_receipt_body` does. These are body builders for an external signer, the gateway checks the signed receipts, and neither builder is a CLI surface.
- **Self-rooted binding.** The executor binding is built from caller-supplied key and evidence roots, and the evidence roots are shape-checked, not resolved. It is anchored only through the contract's executor key and the gateway's signature checks. This is consistent with `binding_grants_authority: false`.
- **Refusals in the court only.** The receipt has 3 UGEL tests, all positive-path.
- **R20-01 unchanged:** `public-vocabulary-r012` still names a tool check.
- **Carried:** r015–r017 never reviewed; the receipt root depends on the Python patch version; two tests are Windows-only.

## Carried-finding dispositions

| Finding | Disposition |
|---|---|
| R21-01 (LOW) | open, unchanged |
| R21-02 (LOW) | open, recurring |
| R21-03 (INFO) | the r021 launcher fix doesn't carry into the r022 kit itself (launcher not delivered); other items carried |
| R19-01 and earlier | closed; no regression |

## Not performed

- **Tier 1:** the court was not run, per your instruction; it is builder-authored in any case.
- **Batch E verification** (R22-01).
- **Windows execution;** the wheel test (venv constraint).
- **Content review** of the CCP cases, the courthouse protocol and the dependency requirements.

## State

r022 adds UGEL as a properly external, optional executor pack: pure UCM-side code, exact pins, separate canonical domains, and a positive `sim.add` path through Pippi, the gateway and dependency evidence, all on an exactly reproducible release. It does not repair the two open r021 findings, and one of them recurs. The UGEL source it pins wasn't delivered.

## To clear

1. Deliver the offline packet with the Batch E archive (R22-01).
2. Batch R21-01 and R21-02, freezing program inputs so later revisions stop rewriting history.
3. Have a reviewer independent of the build perform Tier 1 on runtime `dce704f4…`, including the Windows legs.

If that finds nothing at MED or above, a terminal recommendation becomes possible.

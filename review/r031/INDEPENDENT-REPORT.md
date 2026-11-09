# Independent review: UCM v0.1 r031 transtemporal native (final transport)

**Outcome: HOLD_FOR_REPAIR, on one MED finding about evidence binding. The product itself reproduces exactly.**

- **R31-01 (MED):** the r031 acceptance program doesn't bind what was qualified.
  - `build_transtemporal_r031_program.py --check` fails against the qualified source. Two denominator files changed after the program was sealed.
  - All six R31 closure check ids carry a `tests.` prefix that the receipt doesn't use, so none of them appears in the receipt.
  - The tests themselves pass. Nothing in the qualification catches either defect.
- **Everything the work order asked for holds:**
  - custody is exact;
  - the replay passes 453 of 455 on Python 3.12.3 and 3.13.16, with only the two usual environment non-passes, and its test-id set equals the receipt;
  - the release (four archives and the record) and the cold boot rebuild byte-identical on both interpreters;
  - the portability source manifest and both witnesses reproduce exactly.
- **Transtemporal archive:** verified independently with my own script and the authorized `blake3` package. It reconstructs the delivered r031 runtime byte for byte. Its deduplication, stable file ids, diff and no-deletion retention plan are all exact.
- **C11 verifier:** compiles warning-free under gcc and clang, and passes all 1,270 files of the exact r031 tree. It has no denominator, though (R31-03, LOW).
- **Your operator runs:**
  - your first r031 run HOLD because of a court defect: the court created its scratch folder inside the kit;
  - the repaired run passed 14/14, but its court isn't in the qualified source, and the kit manifest miscounts its members (R31-02, LOW);
  - both runs are user-run and builder-authored, so neither is independent Tier 1.
- **Closed:** R29-01 (statically, in the r030 court), my R29-02 items, and the frozen-registry lag.

If you don't treat program records as a required leg, R31-01 is LOW and the outcome is INCOMPLETE_REVIEW: only the independent Tier 1 leg would remain.

This review grants nothing. Standing remains INFORMATION_ONLY, authority effect NONE, real A5 false, G0 closed.

## Subject identity

No expected values were supplied, so these are observed values, recomputed rather than read. The receipt you attached is byte-identical to the one in the transport.

| Field | Observed |
|---|---|
| Transport SHA-256 | `33e1cac29dfa6eebc15c4682a590681d2620e992edca338240c093069af619e6` |
| Revision | `r031` |
| Release root | `8e6dbf64573c060a82bc2d9105b308901175b24376991a21598715b08d2a8cbe` |
| Qualification root | `bdb2b4587f2fe5ac78f88ac0a572cbdab83a4a9b1085c8ef79c5280e55d22d9e` (455 tests; receipt `4369605b…`) |
| Runtime SHA-256 | `7ed74bbb27487d4df83dd4ca83bdf8acceeade319e0cf0355d6b6381c72058a5` |
| Source root | `603b6e4d13be2d24e304bae4d20de22fa6843060a4521bcd74f7d17b6d5b089c` |
| Cold boot | `2c9f3d49a748849a054a1d47ae11f7f28b7f7509eea6edd7d6e1ef0068dd9b31` |
| Operator kit (repaired) | `bedfa2b4fdf8192fad1a83e410464e6c2a54f8b0c7c612fa3eb541741b0f83a5` |
| Transtemporal history | `314f672a19e23e12ba79ac97f39ba05465c2e016137edff9ba6d836a99101118` |

**Predecessor binding (labelled, unverified).** The identity names r030: qualification `25436291…`, identity `360194d2…`, source `7ada9854…`. r030 was never delivered to me, so I can't verify those values. The runtime diff against r029, the last revision I reviewed, is 64 files changed, 46 added and none removed. The new modules are `transtemporal_archive`, `_blake3_portable` and `native/ucm_archive_verify.c`.

**Execution.**
- Everything ran in an empty environment, from empty working directories, on disposable copies.
- Subject code ran only in the two authorized virtualenvs.
- Custody, the transtemporal archive, the kits and frozen rows were checked with my own scripts.
- I compiled the C verifier with the system gcc and clang; nothing was installed.
- The courts were read, not run. No negative or forgery exercises; no network.

## Custody

- **Transport:** root, 19 rows and closed set verified. It binds release, qualification, runtime, kit and source.
- **Archives:** runtime 1,270 members, SDK 1,756, review 149, lineage 7. Every manifest and META verifies; DKN is unbound and the certificates are READY at r031.
- **Reconstitution:** 1,851 rows recompute to `603b6e4d…`.
- **Receipt:** binds everything; 455 unique ids.
- **Cold boot:** the THR, state and certificate verify, and it embeds the exact runtime.
- **Kit:** 32 members. Root, rows and closed set verify. Its seven pinned files are byte-identical to the transport, and `RUN.ps1` pins `bedfa2b4…`.
- **Records:** the operator disposition and its user Tier 1 evidence verify. The evidence's court equals the kit's, and its court root recomputes.

## Replay and rebuild

| Leg | 3.12.3 | 3.13.16 |
|---|---|---|
| Qualification replay | 453/455 | 453/455 |
| Non-passes | wheel (no setuptools); native UI (Windows-only) | same |
| Test-id set = receipt | yes | yes |
| Release: four archives + record | byte-identical | byte-identical |
| Cold boot rebuild / verify | byte-identical / exit 0 | byte-identical / exit 0 |
| `build_pippi_adaptive_contracts.py --check` | PASS (14) | PASS (14) |
| `build_transtemporal_r031_program.py --check` | **FAIL** (`R031_PROGRAM_DRIFT`) | **FAIL** |
| Portability source manifest | byte-identical; root = source = both witnesses | same |
| Original kit rebuilt from source | byte-identical to `0e98de83…` (the HOLD kit) | same |

## Interfaces and history

- **Routes:** 36 adaptive routes, each exactly once with its exact route.
- **Registry and contracts:**
  - each of the 80 registry entries equals its live entry;
  - the mediation library and 8 completion files equal live generation in the runtime and the cold boot;
  - the atlas and pipeline equal live generation;
  - the live capability root `02d2ad51…` equals both witnesses.
- **Frozen registries:** program has 28 rows and operator 18, now including r027–r030. All rebuild from bytes in POSIX order, and both equal the witnesses.
- **Carried returns:** my r029 return is byte-identical to what I delivered. Your r029 HOLD evidence (`72b484fd…`) verifies, and its two failures record `PREDICATE_FALSE`, consistent with R29-01.
- **R29-01 repair (static):** the r030 court now has `CCP-UNRESEALED-DECISION-SHAPE-REFUSAL`, expecting `GATEWAY_DISPOSITION_INVALID`, and a fully resealed `CCP-RESEALED-DECISION-LAUNDERING`, expecting `DECISION_INVALID`.
- **R29-02 items:**
  - the credential envelope is validated before any write;
  - publication signing revalidates the storage locator;
  - `validate_signed_retrieval_receipt` now exists.

## Transtemporal archive (independent verification)

My script reads the ZIP directly and uses `blake3` and `hashlib`, not subject code.

- **Archive manifest:** root, 1,333 rows (SHA-256 and BLAKE3) and closed set verified.
- **Objects:** 1,320, each stored at its own BLAKE3 address, and every one referenced.
- **r030 and r031:**
  - manifest, receipt, THR (state = manifest root, receipt = receipt root) and DKN (`DECLARED_UNBOUND`, no key) roots all recompute;
  - rows verify by both digests;
  - paths are unique, sorted and portable.
- **Reconstruction:** the r031 revision reconstructs the delivered runtime ZIP exactly, all 1,270 members. r030 is internally consistent, but its source isn't here.
- **Lineage:** the parent link is exact. Every shared path keeps its file id, and the 25 new ids are fresh.
- **Diff:** 25 added, 50 changed, 0 removed, equal to my recomputation.
- **Storage:** logical 18,972,616 bytes, unique 10,622,047, deduplicated 8,350,569. All equal the report.
- **Retention:** a dry run with no proposed deletions and `safe_deletion: false`. Its r031 input hashes equal the delivered runtime.
- **SemCrys plan:** `HELD_OPTIONAL_PACK_UNBOUND`, with no effects.
- **Subject verifier:** `verify_revision` also passes on a disposable extraction.

## C11 native verifier

- `ucm_archive_verify.c` (106 lines) is a self-contained SHA-256 implementation with a strict header, a portable-path check (no absolute paths, `.`/`..` segments, backslashes or control characters), a size check, and a 1 MiB line cap.
- It compiles warning-free under `-std=c11 -Wall -Wextra -Wpedantic` with gcc 13.3 and clang.
- On the exact r031 tree, both builds print `checked: 1270, PASS`.
- The subject's `build_native_manifest` output is byte-identical to my own rendering of the protocol.
- The doc keeps BLAKE3, roots, THR and DKN with the Python verifier, and the C verifier claims none of them.

## Findings

### R31-01 (MED): the r031 acceptance program doesn't bind the qualified source or receipt

- `--check` fails on both interpreters with `R031_PROGRAM_DRIFT:SOURCE-DENOMINATOR.json`. Two of its 15 denominator files changed after sealing:
  - `tests/test_transtemporal_archive.py`: 7,167 → 7,496 bytes;
  - `tools/build_transtemporal_r031_operator_kit.py`: 5,880 → 5,881 bytes.
- All six R31 selections close on `tests.test_transtemporal_archive.…`, but the receipt lists those tests only as `test_transtemporal_archive.…`. Every other selection in the tree (125) uses the receipt's form.
- `pippi_work_units` never resolves a closure id against a receipt, and no test in the receipt runs the current program's `--check`, so neither defect is caught.
- The r028 and r029 program checks passed in their own revisions.

**Effect:** R31-01..06 can't be shown, by exact identity, to close on the qualified bytes. The tests themselves pass in my replay.

**Severity:** I rated this MED by the R24-01 precedent: a generated record that is stale against the source it ships with.

**Repair:**
- regenerate the program after the final source edit, using the receipt's id form;
- add a qualification test that runs the current program's `--check` and requires every closure id to be in the receipt.

### R31-02 (LOW): the court that passed isn't in the qualified source

- The source's `operator/transtemporal-native-r031/RUN-TIER1.py` is the original runner (`ba5f698a…`). Its kit builder rebuilds the original kit `0e98de83…` exactly, and that is the kit whose run HOLD.
- The repaired kit is that kit plus three changes:
  - a one-line runner change: the scratch `dir=out.parent` was removed, so the scratch folder goes to the system temp folder;
  - `COURT-REPAIR.json`;
  - `PREDECESSOR-HOLD-EVIDENCE.zip`.
- Every hash in `COURT-REPAIR.json` verifies. But no shipped tool builds the repaired kit, and its `member_count` still says 29 for 31 rows.

**Repair:** carry the repaired runner and its builder in the next source, freeze it, and derive `member_count` from the rows.

### R31-03 (LOW): the native verifier has no denominator

- The protocol carries no row count and no manifest-root binding, and the verifier doesn't look for unlisted files.
- By source, a header-only manifest returns `PASS` with `checked: 0`, and a truncated one passes on its remaining rows.
- The doc says the verifier checks SHA-256 "for every file".
- It is mitigated by the narrow scope and the mandatory Python verifier. Not executed.

**Repair:** add a trailer line carrying the count and manifest root, refuse `checked == 0` or a count mismatch, and optionally report unlisted files.

### R31-04 (INFO): observations

- **r030:** never delivered to me, so the predecessor is unverified. The r030 court has no operator run in custody.
- **Historical builders:**
  - `build_collaboration_closure_r030_program.py --check` crashes with `KeyError('member_count')`;
  - the r027–r029 builders refuse against current source;
  - the history test covers four other builders.
  The frozen registries themselves verify.
- **Native study:** `R031-NATIVE-STUDY` is a Windows timing record (ratio 0.852) and wasn't reproduced; its nonclaims are explicit.
- **r030 failed qualifications:** they are retained in the SDK and labelled FAIL, which is honest.
- **Carried selections:** R28-07 and R20-01 still don't resolve against the current receipt.

### R31-05 (INFO): carried

- R21-01's secondary items; `sim.add` shape is checked only at evaluation.
- r015–r017, r025 and r030 were never reviewed.
- Two Windows-only tests; the wheel test needs setuptools; the receipt root depends on the Python patch version; the case probe writes transiently.

## Carried-finding dispositions

| Finding | Disposition |
|---|---|
| R29-01 (LOW) | **CLOSED** (static; r030 court unexecuted) |
| R29-02 (INFO) | envelope, locator, retrieval validator and freezing **closed**; anchor independence remains the caller's duty |
| R28-04 frozen lag | **CLOSED** |

## Not performed

- **Independent Tier 1:** not run, per your instruction. Your 14/14 PASS is user-run and builder-authored.
- Windows and WSL legs (builder witnesses only); the native UI; the native timing study.
- Negative or forgery exercises. R31-03 is by source.

## State

r031 adds a transtemporal store: many near-identical releases kept as one content-addressed history. Each revision reconstructs byte for byte, and nothing is deleted. It also adds a small, honest native SHA-256 check over that store. Both work as described, and the whole release reproduces exactly from its own source.

What doesn't hold is the bookkeeping around r031's own acceptance:
- the program record was sealed before its last source edits;
- its closure ids use a form the receipt doesn't;
- the court that passed lives only in a repaired kit.

## To clear

1. Regenerate the r031 program after the final edit, using the receipt's id form, and gate it in qualification (R31-01).
2. Bring the repaired runner and its builder into source, and fix `member_count` (R31-02).
3. Optionally, give the native protocol a denominator (R31-03).
4. Have a reviewer independent of the build perform Tier 1, including the Windows and WSL legs.

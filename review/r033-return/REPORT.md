# Independent review: UCM v0.1 r033 native closure

**Outcome: INCOMPLETE_REVIEW. No finding at MED or above; the terminal verdict is withheld only for independent Tier 1.**

- **All three r032 findings are closed:**
  - **R32-01:** the C17 core now reads every register set the profile allows. All nine corpus programs, including the four limit programs, correspond exactly. So do my own limit programs.
  - **R32-02:** the fallback test runs from source and passes on a clean host. Qualification now pins the import path.
  - **R32-03:** the archive verifier now takes an external rows root and member count, as well as the manifest root.
- **The release reproduces completely:**
  - custody is exact, with 1,954 source rows;
  - the replay passes 473 of 475 on Python 3.12.3 and 3.13.16, with only the two usual environment non-passes, and its test-id set equals the receipt;
  - the release and cold boot were rebuilt twice per interpreter, and all eight rebuilds are byte-identical;
  - the operator kit rebuilds byte-identically.
- **Native correspondence on a third platform:** on Linux, under gcc and clang, all nine programs give exactly the results recorded by both your Windows and WSL witnesses.
- **One LOW (R33-01):** the transport's `PORTABILITY-SOURCE-MANIFEST.json` is a stale copy. Nothing in the proof chain reads it.
- **Your r032 Tier 1 run (14/14 PASS)** is carried byte-exact with provenance. It is user-run and builder-authored.

This review grants nothing. Standing remains INFORMATION_ONLY, authority effect NONE, real A5 false, G0 closed.

## Subject identity

No expected values were supplied, so these are observed values, recomputed rather than read.

| Field | Observed |
|---|---|
| Transport SHA-256 | `225ace8dbecef970616c5916a4daa89d1d5719730608c27ede771992c4a60be7` (root `c58e039d…`) |
| Revision | `r033` |
| Release root | `d8c41b03aec805a400cba5d44cd20d903d4ee6d0064a53c897a3a432ea0a2354` |
| Qualification root | `c7a67b7dc03bfb454d08795ea130668c97fa20eecf6f99c1fa758bad614fad09` (475 tests) |
| Runtime SHA-256 | `b36529bc578e7684085b2d243d3fd597b5da5219b41cf3353165713cd920b704` |
| Source root | `169470fe465f9e6a926874ec6df3945f071dca1f7ef488ef103657307eefd605` |
| Cold boot | `54445acfde8291734fc54bda834c883e8b9fafa2b81f4ed27e67b49d5f745707` |
| Operator kit | `158e30b9700b96b9e7493e7e3575c3f1f2e395d43ef0af88fc1cd266721fa764` |

**Predecessor binding.** The release identity names r032 with qualification `5b5a64e2…`, identity `1ee0ffc5…` and source `d52891c5…`. All three equal my r032 observations in full.

**Execution.**
- Everything ran in an empty environment, from empty working directories, on disposable copies.
- Subject code ran only in the two authorized virtualenvs.
- The shipped `VERIFY-TRANSPORT.py` was read, not run.
- I compiled the C files with the system gcc 13.3 and clang, using your exact flags. Nothing was installed and there was no network.
- The work order invites additional attacks. Per your standing instruction I ran none, and I read the court rather than running it.

## Custody

- **Transport:** root, 19 rows and closed set verified. It binds release, qualification, runtime, kit, cold boot and source.
- **Archives:** runtime 1,344 members, SDK 1,856, review 167, lineage 7. Every manifest, state, THR, DKN (unbound) and certificate (READY, r033) verifies.
- **Reconstitution:** 1,954 rows recompute to `169470fe…`, and the runtime is a subset of the SDK.
- **Receipt:** binds everything; 475 unique ids.
- **Cold boot:** the THR, state and certificate verify, and it embeds the exact runtime.
- **Kit:** 34 members. Root, rows and closed set verify, and `member_count` (33) equals its rows. It is labelled builder-authored and unexecuted, and its five pinned files equal the transport. `RUN.ps1` pins `158e30b9…`.

## Replay and rebuild

| Leg | 3.12.3 | 3.13.16 |
|---|---|---|
| Qualification replay | 473/475 | 473/475 |
| Non-passes | wheel (no setuptools); native UI (Windows-only) | same |
| Test-id set = receipt; shadow guard reached `qualification_start` | yes | yes |
| Release (four archives + record), build 1 and build 2 | byte-identical | byte-identical |
| Cold boot, build 1 and build 2 | byte-identical | byte-identical |
| Operator kit, `RUN.cmd`, `RUN.ps1` rebuilt from source | byte-identical | byte-identical |
| `build_native_closure_r033_program.py --check` | PASS (24) | PASS (24) |
| `build_native_core_r033_assets.py` / `…r032_assets.py --check` | PASS / PASS | PASS / PASS |
| `build_pippi_adaptive_contracts.py --check` | PASS (14) | PASS (14) |
| In-source portability source manifest | byte-identical (`169470fe…`) | same |

## Work-order items

- **Items 1–2:** custody as above.
- **Item 3:**
  - qualification exports `PYTHONPATH=src` and `PYTHONNOUSERSITE=1`, removes `PYTHONHOME`, and probes that `ucm` resolves to `src/ucm/__init__.py`;
  - the fallback test now invokes `tools/ucm.py -B`, which inserts `src`;
  - it passes on clean hosts.
- **Item 4:** two rebuilds per interpreter, all byte-identical.
- **Item 5 (native core):**
  - both C files compile warning-free under `-std=c17 -Werror` with gcc and clang;
  - the subject's `verify_native_correspondence` returns `all_correspond: true` for all nine programs, under both compilers and both interpreters;
  - `lower_native_program` reproduces each shipped `.ucln` exactly;
  - the boundary programs really reach their limits: 256 registers, 4,096 instructions, a 2,048-step stack program, and exactly 1,000,000 steps.
  - My own programs, which are not in the corpus, also correspond under both compilers: 256 registers at I64_MIN, at I64_MAX, all zero, or mixed full-width values, and a 4,096-instruction program.
  - Linux results equal both witnesses' results exactly, and all three bind native source `5eb3059d…`.
- **Item 6 (parser):**
  - integers must be canonical: no leading zeros, `+`, whitespace or `-0`;
  - hex digests must be lowercase and 64 characters;
  - the file's SHA-256 must equal an external argument before parsing;
  - any byte after `END` refuses (`NATIVE_TRAILING_DATA_REFUSED`).
  - By source; your court and tests cover these refusals, and the tests pass in replay.
- **Item 7 (archive verifier):**
  - it requires external manifest root, rows root and member count, and refuses a mismatch or trailing data;
  - on the exact r031 tree it reports `checked: 1270`, PASS, under both compilers;
  - `build_native_manifest_binding` pins equal my independent recomputation;
  - your resealed-truncation test passes in replay.
- **Item 8 (history):**
  - the frozen registries now hold 30 program and 21 operator rows, including r031, the r031 repaired court, and r032. All rebuild in POSIX order and equal the witnesses.
  - My r032 REPORT, FINDINGS, RECOMPUTE and evidence ZIP are byte-identical to what I delivered.
  - `review/r032/PROVENANCE.json` recomputes, and names your r032 run.
  - That run (`7a58c24a…`) passed 14/14 on runtime `19d41ff3…`. Its court root recomputes, and its court is byte-identical to the r032 kit's.
- **Interfaces:**
  - 36 P/PPI routes, each exactly once;
  - each of the 80 registry entries equals its live entry;
  - the contracts, atlas and pipeline equal live generation;
  - the live capability root `145e0c67…` equals both witnesses;
  - R33-01..07 validate and rebuild exactly, each closes on a receipt test, and none authorizes effect.
- **Court (read):** 16 cases. It uses the system temporary root, and adds `PROJECTION-NONCANONICAL-INTEGER` and `PROJECTION-TRAILING-DATA`.

## Findings

### R33-01 (LOW): the transport's portability source manifest is stale

- The transport member and its copy at `evidence/r033-portability/` have root `13caa7b2…`.
- The qualified source's own manifest, which I rebuilt byte-identically, has root `169470fe…`. That is the root the witnesses and receipt bind.
- The stale copy differs in 26 rows: `VERIFY.py`, `tests/test_public_release_qualification.py`, and 24 r033 program records.
- **Effect:** nothing reads it, but rebuilding the portability source from it would yield a different source than was qualified.

**Repair:** regenerate it, or drop it, and check that every carried manifest root equals the witnesses' `source_root`.

### R33-02 (INFO): observations

- **Python pin:** `execute_native_binary` derives the "external" projection SHA-256 from the file it passes, so on the Python path the pin can't disagree with the file. The correspondence comparison still catches a mismatch. The C CLI itself accepts a genuinely external pin.
- **Double read:** the C core hashes the file and then reopens it to parse. Reading it once would close that window.
- **Shadow probe:** the probe inserts `src` first and then checks where `ucm` came from, so it can only confirm that `src/ucm` imports. The real protection is the exported environment.
- **Historical builders:** the r032 program builder now reports drift against current source. That is the historical-builder pattern; r032 is frozen and verifies.
- **Unresolved selections:** R28-07, R20-01 and the six r031 `tests.`-form selections still don't resolve against the current receipt.

### R33-03 (INFO): carried

- R21-01's secondary items; `sim.add` shape is checked only at evaluation.
- r015–r017, r025 and r030 were never reviewed.
- Two Windows-only tests; the wheel test needs setuptools; the receipt root depends on the Python patch version; the case probe writes transiently.

## Carried-finding dispositions

| Finding | Disposition |
|---|---|
| R32-01 (MED) | **CLOSED** |
| R32-02 (MED) | **CLOSED** |
| R32-03 (LOW) | **CLOSED** |
| R32-04 (INFO) | canonical integers, trailing data, external pin and r031/r032 freezing **closed**; the rest is in R33-02 |

## Not performed

- **Independent Tier 1 for r033:** not run, per your instruction. The court is builder-authored and unexecuted.
- The Windows and WSL legs themselves. A Linux third-platform correspondence run was performed.
- Additional attacks or negative exercises, per your instruction.

## State

r033 closes the native line that began in r031:
- the bounded C17 core now matches the Python reference across its whole declared profile, not just a convenient corpus, on three platforms and under three compilers;
- the archive verifier binds what it checks to externally supplied roots and counts;
- qualification is hermetic with respect to the `ucm` it tests;
- r031 and r032 are frozen in history.

The release reproduces byte for byte from its own source. What remains is one stale copied file, and the independent Tier 1 leg.

## To clear

1. Regenerate or drop the stale portability source manifest copies (R33-01).
2. Have a reviewer independent of the build perform Tier 1 on runtime `b36529bc…`, including the Windows and WSL legs. You can also run `RUN.cmd` as user-run evidence.

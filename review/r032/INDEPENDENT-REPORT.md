# Independent review: UCM v0.1 r032 native completion

**Outcome: HOLD_FOR_REPAIR, on two MED findings. Both are narrow and fail closed.**

- **R32-01 (MED):** the C17 native core can't read the register sets its own profile allows.
  - It reads each line into 512 bytes, but the profile allows 256 i64 registers on one header line, up to 5,390 bytes.
  - On programs valid under the profile, the Python reference passes while the C core refuses. That happens from 24 full-width registers, and even 255 zero-valued registers refuse.
  - The refusal is typed and nothing executes wrongly. But it contradicts work-order item 5, "agree exactly", and the doc's rule that Python must not widen the C profile.
- **R32-02 (MED):** the closure test for R32-05 isn't hermetic.
  - It runs `python -m ucm.cli` without putting `src` on the path, so a clean replay fails it on both interpreters. With `src` on the path it passes.
  - Your receipt recorded PASS, so some `ucm` was importable on the build host, possibly an installed copy rather than the qualified bytes.
- **Everything else holds:**
  - custody is exact;
  - the release, cold boot and operator kit all rebuild byte-identical on Python 3.12.3 and 3.13.16;
  - the five-program corpus matches both witnesses exactly on a third platform (Linux, gcc and clang);
  - interface parity, frozen rows and the portability source manifest all reproduce.
- **R31 dispositions:**
  - **R31-01 closed:** the program is current, its ids are in receipt form, and qualification gates on them.
  - **R31-02 closed:** the repaired court is in source, and the kit is reproducible. Freezing is still pending.
  - **R31-03 repaired**, with a narrow residual (R32-03, LOW).

This review grants nothing. Standing remains INFORMATION_ONLY, authority effect NONE, real A5 false, G0 closed.

## Subject identity

No expected values were supplied, so these are observed values, recomputed rather than read.

| Field | Observed |
|---|---|
| Transport SHA-256 | `24f5cd92beaba58e1772dbcb3b4d94a972ff41c9d95c0870193680869e54ee61` (root `0fd02b34…`) |
| Revision | `r032` |
| Release root | `6ee309d0a9c144877fc9dfc058af7e78efba8c31dc3530d47baa56c4c30652c1` |
| Qualification root | `5b5a64e2f23e2f65ef6e053487e66066f46022c7fcca877a8a9f5c4e66827e36` (466 tests) |
| Runtime SHA-256 | `19d41ff3a4d645f2ac192a91d68618c89cac97e0cbeb8ed30a56a7c57b964757` |
| Source root | `d52891c508a55ad7cff7ab2a201c9749407c5991bc04ac489d6a9ae12c9bc94d` |
| Cold boot | `8e4ea819fc64e31eab63ca0fac702da042c026fce6e65e667a1104dfd8812796` |
| Operator kit | `6a9253ca1a658b3e5eb05cf3b92075ea339ed4d645ca738367ba1e9cfcb566f3` |

**Predecessor binding.** The release identity names r031 with qualification `bdb2b458…`, identity `ea3511bb…` and source `603b6e4d…`. All three equal my r031 observations in full.

**Execution.**
- Everything ran in an empty environment, from empty working directories, on disposable copies.
- Subject code ran only in the two authorized virtualenvs.
- The shipped `VERIFY.py` was read, not run. Custody used my own scripts, adapted to the new transport layout.
- I compiled both C files with the system gcc 13.3 and clang, using your exact flags. Nothing was installed.
- The court was read, not run. No negative or forgery exercises. R32-01 used only programs that are valid under the profile.

## Custody

- **Transport:** root `0fd02b34…`, 26 rows, closed set. It binds release, qualification, runtime and revision.
- **Archives:** runtime 1,311 members, SDK 1,810, review 159, lineage 7. Every manifest, state, THR, DKN (unbound) and certificate (READY, r032) verifies.
- **Reconstitution:** 1,908 rows recompute to `d52891c5…`, and the runtime is a subset of the SDK.
- **Receipt:** binds everything; 466 unique ids.
- **Cold boot:** the THR, state and certificate verify, and it embeds the exact runtime.
- **Kit:** 37 members. Root, rows and closed set verify, and `member_count` (36) equals its rows. It is labelled builder-authored and unexecuted, and its five pinned files equal the transport. `RUN.ps1` pins `6a9253ca…`.
- **Carried r031 material:**
  - my REPORT, FINDINGS, RECOMPUTE and evidence ZIP are byte-identical to what I delivered;
  - your r031 PASS evidence is byte-identical to the one in the r031 transport;
  - the repaired runner, repair record and declaration are byte-identical to the r031 repaired kit, and are now in source at `operator/transtemporal-native-r031-repaired/`.

## Replay and rebuild

| Leg | 3.12.3 | 3.13.16 |
|---|---|---|
| Qualification replay | 463/466 | 463/466 |
| Non-passes | wheel (no setuptools); native UI (Windows-only); **`test_cli_and_abi_expose_portable_fallback`** (R32-02) | same |
| Test-id set = receipt | yes | yes |
| Release: four archives + record | byte-identical | byte-identical |
| Cold boot rebuild / verify | byte-identical / exit 0 | byte-identical / exit 0 |
| Operator kit, `RUN.cmd`, `RUN.ps1` rebuilt from source | byte-identical | byte-identical |
| `build_native_completion_r032_program.py --check` | PASS (27) | PASS (27) |
| `build_native_core_r032_assets.py --check` | PASS (12 files, 5 programs) | PASS |
| `build_pippi_adaptive_contracts.py --check` | PASS (14) | PASS (14) |
| Portability source manifest | byte-identical | byte-identical |

## Work-order items

- **Items 1–3:** custody and rebuild as above. The replay is as above, with one subject-caused non-pass (R32-02).
- **Item 4 (witnesses):** both witnesses record `PASS_CORRESPONDENCE` over the same five programs.
  - They have the same results and result-set root `10f57fe8…`, and bind native source `b0880b43…` (equal to the shipped `ucm_native_core.c`).
  - Their compilers differ: MSYS2 gcc 16.1 on Windows and Ubuntu gcc 13.3 on WSL.
- **Item 5 (correspondence):**
  - Against my Linux gcc and clang builds, the subject's `verify_native_correspondence` returns `all_correspond: true` for all five programs on both interpreters.
  - Every projection hash, result and step count equals the witnesses, and `lower_native_program` reproduces each shipped `.ucln` exactly.
  - Across the profile's declared range, though, the two realizations don't agree (R32-01).
- **Item 6 (R31-01):**
  - all eight closure ids are in receipt form and present in the receipt;
  - the denominator covers 75 files, including the r031 carried evidence and the repaired court;
  - qualification runs the program and asset `--check`s, refuses (`R032_ACCEPTANCE_CLOSURE_CHECK_NOT_IN_QUALIFICATION`) unless all eight ids are present, and issues a receipt only on a fully passing suite;
  - R32-01..08 validate and rebuild exactly, and none authorizes effect.
  - **Closed.**
- **Item 7 (R31-02):** the r031 PASS is carried in `review/r031/` and bound through the r032 denominator. The release identity records r032's own Tier 1 as `SEPARATE_USER_RUN_REQUIRED`, with 0 cases. **Closed.**
- **Item 8 (R31-03):**
  - header version 2 carries the manifest root, which must equal an external argument, and a non-zero count;
  - an `END` trailer carries the count and a SHA-256 of the row stream;
  - a missing trailer or any mismatch refuses.
  - **Repaired.** The residual is R32-03.
- **Item 9 (profile):** the profile is closed:
  - 18 opcodes, signed i64 values and booleans of 0 or 1;
  - fixed limits: 4,096 instructions, 256 registers, a 1,024-value stack and 1,000,000 steps;
  - checked add, subtract and multiply, and checked divide and modulo including INT64_MIN/−1, with truncating division in both realizations;
  - bounded jumps, a terminal `HALT` with exactly one stack value, no effects, and typed refusals.
  The register limit is declared but not reachable in C (R32-01).
- **Item 10 (C standard):** the program builder's `build_c_change_preflight` reaches `READY_FOR_QUICK_CHECKS` over the exact denominator: C17, warnings as errors, the declared write set equal to the changed set, and the full check denominator. The Windows and WSL portability gates verify.
- **Item 11 (claims):** the docs state plainly that the native core is not the full UCL-SH language, P/PPI, AMCAS or the gateway, and that Python remains the authoring layer and fallback. The profile records `full_ucl_sh_claimed: false`.
- **Interfaces and history:**
  - 36 P/PPI routes, each exactly once;
  - each of the 80 registry entries equals its live entry, and the contracts and atlas equal live generation;
  - the live capability root `145e0c67…` equals both witnesses;
  - frozen program (28) and operator (18) rows all rebuild in POSIX order and equal the witnesses.
- **Court (read):** 14 cases. It uses the system temporary root, so the r031 repair is carried. It includes code mutation, denominator shrink, body-root swap, overflow, step bound and fallback parity. It has no case at a declared profile limit.

## Findings

### R32-01 (MED): the C17 core can't read register sets the profile allows

- `ucm_native_core.c` reads every line with `fgets` into a 512-byte buffer. The `REGISTERS` header puts every register value on one line.
- The profile and `validate_native_program` allow 256 i64 registers, which makes a line of up to 5,390 bytes.
- I built programs that are valid under the profile with `build_native_program`. The Python reference passed every one; the C core, under both gcc and clang, behaved as follows:

| Register values | Count | `REGISTERS` line | C result |
|---|---|---|---|
| I64_MIN | 23 | 496 B | PASS, corresponds |
| I64_MIN | 24 | 517 B | `NATIVE_PROGRAM_HEADER_INVALID` |
| I64_MIN | 100 / 255 / 256 | 2,114–5,390 B | `NATIVE_REGISTER_COUNT_MISMATCH` |
| 0 | 100 | 214 B | PASS, corresponds |
| 0 | 255 / 256 | 524–526 B | `NATIVE_REGISTER_COUNT_MISMATCH` |

- **Contradicts:**
  - work-order item 5;
  - the doc's statement that Python "is not allowed to silently widen the C profile";
  - the profile's `max_registers: 256`.
- **Why nothing caught it:** the corpus, witnesses and court never approach a declared limit.

**Repair:**
- size the buffer to the profile maximum, or emit one register per line;
- add boundary programs to the frozen corpus: 256 registers at I64_MIN and I64_MAX, 4,096 instructions, the step bound and the stack bound.

### R32-02 (MED): closure test R32-05 depends on a `ucm` outside the qualified source

- `test_cli_and_abi_expose_portable_fallback` runs `[sys.executable, "-m", "ucm.cli", …]` with `cwd=ROOT` and no `PYTHONPATH`. Other CLI tests set `PYTHONPATH=ROOT/src`.
- A clean replay fails it on both interpreters with `No module named 'ucm'`. With `src` on the path, it passes on both.
- Your 3.12.10 receipt recorded PASS, so `ucm` was importable there from outside the qualification's own path setup, possibly an installed copy.
- This is the direct closure check for R32-05.

**Repair:**
- give the test `PYTHONPATH=ROOT/src`, or invoke `tools/ucm.py`;
- have qualification refuse when an installed `ucm` shadows the source.

### R32-03 (LOW): the archive verifier's external pin covers only the header

- The external root is compared with the header's own `manifest_root` string, and the trailer's row digest is declared by the same manifest.
- So damage and naive truncation now refuse. By source, though, a truncated manifest whose header count and trailer are recomputed still passes.

**Repair:** pin the row-stream digest externally, for example from a Python receipt, or narrow the doc to accidental truncation.

### R32-04 (INFO): observations

- **C core inputs:**
  - it accepts non-canonical integer spellings (`strtoimax` allows leading whitespace and `+`);
  - it ignores bytes after `END`, though `program_sha256` still covers them;
  - its digests are self-declared, so it runs any self-consistent projection within the profile; no `program_root` is pinned.
- **r031 history:** the programs and courts aren't frozen yet; both registries are unchanged at 28 and 18 rows. `review/r031` has no `PROVENANCE.json`; r032 binds it through its denominator instead.
- **Unresolved selections:** the historical r031 selections keep their `tests.` ids. Like R28-07 and R20-01, they don't resolve against the current receipt.
- **Bytecode:** the fallback test's child interpreter writes bytecode into the source tree.

### R32-05 (INFO): carried

- R21-01's secondary items; `sim.add` shape is checked only at evaluation.
- r015–r017, r025 and r030 were never reviewed.
- Two Windows-only tests; the wheel test needs setuptools; the receipt root depends on the Python patch version; the case probe writes transiently.

## Carried-finding dispositions

| Finding | Disposition |
|---|---|
| R31-01 (MED) | **CLOSED** |
| R31-02 (LOW) | **CLOSED**; freezing pending (R32-04) |
| R31-03 (LOW) | **REPAIRED**; residual R32-03 |
| R31-04/05 | carried |

## Not performed

- **Independent Tier 1:** not run, per your instruction.
- The Windows and WSL legs themselves. I added a third-platform (Linux) corpus run.
- Negative or forgery exercises. R32-03 is by source.

## State

r032 adds what it set out to add: a small, effect-free native core with checked integer semantics that executes the same five constitutional predicates identically on Windows, WSL and Linux, under three compilers and in Python. It also closes the r031 bookkeeping:
- the acceptance program is now current and gated by qualification;
- the repaired court lives in source;
- the kit rebuilds exactly.

What remains is a gap between the profile's declared limits and what the C reader can parse, plus one test that leans on the build host's environment. Both are small, fail closed, and have one-line fixes. Neither is visible to a corpus that stays far from the limits.

## To clear

1. Fix the C line buffer, or the register encoding, and add limit-boundary programs to the corpus (R32-01).
2. Make the R32-05 fallback test hermetic, and refuse a shadowing installed `ucm` (R32-02).
3. Optionally, pin the archive row digest externally (R32-03), and freeze r031.
4. Have a reviewer independent of the build perform Tier 1.

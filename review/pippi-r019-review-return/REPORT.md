# Independent review: Mosaic UCM + P/PPI v0.1 r019 complete review transport

**Outcome: INCOMPLETE_REVIEW. The terminal verdict is withheld.**

- **All three r018 LOW findings are closed** on my own evidence:
  - **R18-01:** the transport now carries the review archive. Replay and rebuild both run.
  - **R18-02:** every r016–r018 work selection now validates and rebuilds under the release's own rule. The exact preimages are kept, and a verified map links old roots to new ones.
  - **R18-03:** planning and inventory commands now write nothing.
- **Tier 2 is back.** All five release artifacts and the cold boot rebuild byte-for-byte on Python 3.12.3 and 3.13.16. The qualification replay passes 351 of 353 on both. Of the two non-passes, one needs Windows and the other needs a build tool I'm not authorized to install.
- **One new LOW finding (R19-01):** three tests resolve paths relative to the working directory. The replay therefore passes only when started from the source root, and nothing says so.
- **Why the verdict is withheld:** only the independent Tier 1 leg and the Windows legs remain. The kit is builder-authored and unexecuted. Per your instruction, I read the court but did not run it.

This review grants nothing: no publication, deployment, installation, application execution, network, identity, federation, DKN binding, pack acquisition, program admission, A5, G0 or production authority. Standing remains INFORMATION_ONLY, authority effect NONE, real A5 false, G0 closed; the subject stays DKN-unbound.

## Subject

| Item | Value |
|---|---|
| Transport | `MOSAIC-UCM-PIPPI-v0_1-r019-COMPLETE-REVIEW-TRANSPORT.zip` `4aaa6910…`. Manifest root `9ccf6b6b…`; 9 members; `replay_inputs_complete: true` |
| Release | root `245699f0…`; identity `8749fc43…`; source manifest `f6f40e00…` (1,306 rows); custody denominator 89; `review_mode: SELF_CONTAINED_CUSTODY` |
| Runtime / SDK / review / lineage | `ac0e77c6…` (898) / `a42195ac…` (1,226) / `5ab7f018…` (93) / `09633e0d…` (7) |
| Cold boot | `340d89a7…`, manifest root `ceccc000…` |
| Qualification receipt | root `164d86d3…`, 353 tests, builder Python 3.12.10, 0/0/0 |
| Operator kit | `PIPPI-r019-OPERATOR-KIT.zip` `65df90c8…`, manifest root `589accb0…` |

**Execution.** All runs used `python3 -I -B` in an empty environment, on disposable copies.
- Stdlib checks ran on system CPython 3.12.3 and 3.13.16.
- Subject code ran only in the two previously authorized virtualenvs, and only for:
  - qualification and rebuild;
  - cold-boot build and verify;
  - the runtime tree verifier and read-only orientation commands;
  - the program builders' and the normalization tool's `--check` mode;
  - the work-unit validators;
  - the documented planning commands, against a disposable home directory.
- Two of the `--check` tools import a sibling module from `tools/`. I ran those two with `-E -s -B` instead of `-I`, so that the subject's own `tools/` directory was on the import path.
- `RUN-TIER1.py` was read, not run. Nothing was installed and no network was used.

## Tier 0: custody

**Transport and release.**
- **Transport manifest:** the root recomputes, all 9 rows match, and the set is closed. It binds the release root, qualification root, review, runtime and kit hashes. It records `operator_kit_executed: false`.
- **Release record and partition:** both roots recompute, and all four artifact pins match.
- **Each archive:**
  - deflate only, with no duplicate names;
  - manifest root recomputes and equals the release record; rows match; set closed;
  - **META:** the state root recomputes and its rows equal the payload; THR H_s, H_c, H_j, H_m, H_r and `h_body` recompute and equal the release; DKN `DECLARED_UNBOUND`, with no key and no permission; the self-certificate root recomputes; unsigned and READY; it binds state, THR, DKN, identity and source; revision r019.
- **Source reconstitution:** the SDK, review and lineage payloads equal all 1,306 rows exactly. The 89 custody rows equal the denominator and the review payload, and the runtime is a byte-identical subset of the SDK.
- **Identity:** the root recomputes and equals the release. It binds the source and names r018 as predecessor (qualification `ceb1cb9a…`, identity `992c5af8…`, source `77216006…`, all matching what I reviewed). It records `operator_tier1_status: SEPARATE_USER_RUN_REQUIRED`.
- **Receipt:** binds source, release, identity, runtime manifest root, and the runtime, SDK, review and lineage hashes. It lists 353 unique ids, and their set root recomputes.

**Cold boot.**
- Its hash and all five roots equal the receipt.
- The 24 rows match and the set is closed. THR and the certificate bindings recompute.
- It embeds the delivered runtime byte for byte.

**Operator kit (static).**
- Deflate only, 4 entries.
- The manifest root recomputes. The labels say `builder_authored: true`, `operator_executed: false`, `tier1_executed: false`.
- The runtime and cold boot inside it are byte-identical to the delivered ones.
- Its `RUN-TIER1.py` is byte-identical to `operator/pippi-adaptive-r019/RUN-TIER1.py` in the source.

**Delta since r018.**
- **Runtime:** 793 files unchanged, 52 changed, 49 added, none removed. The changes are:
  - the pack, CLI and installer modules;
  - the install scripts;
  - the runtime verifier;
  - documentation;
  - the r016–r018 program records, which were normalized;
  - the new `program/pippi-adaptive-r019/` (15 selections) and the normalization record.
- **SDK:** additionally changes the release tools and tests, and adds the `historical/` preimages.

## Tier 2: replay and rebuild (R18-01 closed)

**Rebuild.** `build_release.py`, run from the reconstituted source, makes all five artifacts byte-identical to the delivered files on both interpreters. `build_pippi_cold_boot.py`, given the delivered runtime, reproduces the delivered cold boot byte for byte, and `verify_pippi_cold_boot.py` passes.

**Qualification replay**, run from the source root, one interpreter at a time:

| | 3.12.3 | 3.13.16 |
|---|---|---|
| Collected | 353 (ids = receipt) | 353 |
| Pass | 351 | 351 |
| Non-pass | `…native_ui_imports`: `mosaic_ui.win32` requires Windows | same |
| | `…wheel…`: pip cannot load `setuptools.build_meta`, because setuptools is not in the authorized venv | same |

- Neither non-pass is attributable to the subject. The wheel test never got as far as testing the subject here.
- My first attempt ran both interpreters in parallel from one empty directory. It gave 348 and 345 passes:
  - three portfolio tests failed because they read `install/…` and `src/…` relative to the working directory (R19-01);
  - on 3.13, three adaptive tests failed because the two concurrent runs shared one cwd-relative temp directory. That was my harness, not the subject.

  Both runs are kept in the evidence.

**Runtime.**
- `verify_runtime_tree.py`: PASS (root `d61ff5c9…`).
- `orient`, `capabilities`, `profiles`, `smoke` and `abi-stability` exit 0 and give identical output on both interpreters.

**Program builders (`--check`, nothing written, same on both interpreters).**
- CCP native: PASS (13 stages, 32 requirements, 116 cases).
- CCP courthouse: PASS, `094b4bea…`.
- P/PPI adaptive: PASS, 47 records, no mismatches. It now runs because the custody is present.
- P/PPI interface: PASS, `424ef33b…`. This was the stale r016 builder check in R18-04; it now checks the normalized records.
- `normalize_pippi_work_selection_history.py --check`: PASS, root `332270fb…`, 16 records.

## R18-02: work-selection normalization (closed)

- **Normalization record:** its root recomputes, and its 16 mappings cover every r016–r018 selection.
- **Preimages:** all 55 files under `historical/pippi-work-selection-preimages/` match the record's rows. They are **byte-identical to the r018 SDK records** I reviewed, and the set is closed.
- **The map:** each mapping's preimage roots equal the preimage files, and its normalized roots and subject root equal the active records.
- **Under the governed `pippi_work_units` rule:**
  - all 33 selections in r014–r019 validate and rebuild exactly;
  - each acceptance case's `subject_root` equals its program's source denominator, and its `requirement_root` matches;
  - every case is `UNMET`; every selection carries `implementation_effect_authorized: false`;
  - every named closure test is in the receipt.
- The r019 program adds cases for court repair, plan purity, work selection, the review transport and the release verifier.
- Outside r014–r019, the r012/r013 vocabulary selections also validate and rebuild. Their closure ids name a tool check, not a test (pre-existing; see R19-02).

## R18-03: pure planning (closed)

- In a fresh home and working directory, `pack-inventory`, `install-plan RECOMMENDED_LOCAL` and `install-plan FULL_MOSAIC` write nothing. Before, they wrote `INVENTORY.json`.
- All planning outputs are identical across interpreters.
- `FULL_MOSAIC` is HELD with `plan_performs_effects: false`:
  - the four adapters need an external binding;
  - SemCrys is `REMOTE_DOWNLOAD_NOT_SELECTED`, or `DOWNLOAD_REQUIRES_USER_AUTHORIZATION` with `--allow-remote-downloads`.

## r018 operator return and the r019 court (read, not run)

- **The r018 evidence** (in review custody):
  - its manifest root and rows recompute;
  - the result is `HOLD_FOR_REPAIR`, with 27 PASS and 2 FAIL (`CONTROL-TURN-REPORT`, `REPORT-OPENING-SWAP`);
  - its court is byte-identical to the r018 source court.

  It is user-run and builder-authored, so it is not independent.
- **The r019 court** changes only those two cases and adds two controls:
  - It now passes `opening=` to `validate_turn_report`, whose signature makes `opening` a required keyword. The r018 call omitted it, so the control would raise.
  - The swap case now changes `turn_opening_root`, the field the validator actually rebuilds, instead of a non-contract `opening_root`.
  - New `PACK-PLANNING-LEAVES-NO-INVENTORY` control.
  - New `CONTROL-NORMALIZED-WORK-SELECTIONS` control, which expects exactly 16 records.

  Both repairs are correct by source. This does not show the rest of the court runs clean.

## Findings

### R19-01 (LOW, reproducibility): the qualification replay depends on the working directory

- `run_public_release_qualification.py` puts `ROOT` on `sys.path` but does not change into it.
- Several tests resolve paths from the working directory:
  - `test_pippi_portfolio` reads `install/INSTALL-PIPPI.ps1`, `src/ucm/pippi_dashboard.py` and `src/mosaic_ui/win32.py` by relative path, and runs the CLI with `cwd=Path.cwd()`;
  - `test_pippi_adaptive` and `test_pippi_integrations` create temp directories under `Path.cwd()/.test-tmp`.
- So a replay started anywhere other than the source root:
  - fails three receipt tests;
  - writes into whatever directory it was started from;
  - collides with any concurrent replay from that directory.
- Neither `REVIEW-START-HERE.md` nor the tool says to start from the root. The pattern predates r019; it shows up now because r019 is the first handoff since r014 that can be replayed.

**Repair:** resolve paths from `ROOT` in the tests (or `chdir(ROOT)` in the tool), and put temp directories under the tool's own temp root.

### R19-02 (INFO): observations

- **Rewritten history:** the active r016–r018 records were rewritten. Anyone holding r018-era roots must use the normalization map; the preimages are preserved exactly.
- **Two tools fail under `-I`:** `build_pippi_interface_program.py` and `normalize_pippi_work_selection_history.py` import a sibling module from `tools/`, so they fail under `python -I` (no script-directory path). The other builders do not.
- **Docstring mismatch:** the r019 court's docstring says "Operator-executed", while the kit manifest says `builder_authored: true`.
- **Vocabulary closure ids:** the r012/r013 vocabulary selections name a tool check (`public_vocabulary_deterministic_regeneration_and_semantic_lint`) as their closure id, not a receipt test.
- **Unreviewed revisions:** r015–r017 were never delivered as releases.
- **Carried:** the receipt root depends on the Python patch version; two tests remain Windows-only.

## Carried-finding dispositions

| Finding | Disposition |
|---|---|
| R18-01 (LOW) | **CLOSED**: transport complete; rebuild byte-identical; replay 351/353 |
| R18-02 (LOW) | **CLOSED**: 33 r014–r019 selections validate and rebuild; preimages exact; map verified |
| R18-03 (LOW) | **CLOSED**: no files written by planning or inventory |
| R18-04 (INFO) | interface builder check fixed; delegation note not applicable (no handoff `START-HERE.md` in this transport); remainder carried in R19-02 |
| Earlier (REL4–CCP13R) | closed; their tests pass in the r019 replay, including both r014 kit tests |

## Not performed

- **Tier 1:** the court was not run, per your instruction; it is builder-authored in any case.
- **Windows execution:** launchers, installer, service, dashboard and `mosaic_ui.win32`.
- **The wheel test:** blocked by the venv constraint.
- **Separate review of r015–r017; content review of the CCP cases and the courthouse protocol.**

## State

r019 is a bounded repair of r018, and it restores the full Tier 0 and Tier 2 legs:
- the release, its receipt and its cold boot reproduce exactly from the delivered bytes;
- work-selection history is back under one governed rule, with nothing lost;
- planning is side-effect-free.

By component:
- **Release custody, certification and cold boot:** production-shaped, unbound by design.
- **P/PPI adaptive and pack layers:** qualified by builder replay and confirmed by mine; not attacked independently.
- **Open:** the independent attack leg and the Windows legs.

## To clear

1. Batch R19-01.
2. Have a reviewer independent of the build perform Tier 1 on runtime `ac0e77c6…`, including the Windows legs. The r019 kit binds that exact runtime and cold boot.

If that finds nothing at MED or above, a terminal recommendation becomes possible.

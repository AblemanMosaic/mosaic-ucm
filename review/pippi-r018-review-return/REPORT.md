# Independent review: Mosaic UCM + P/PPI v0.1 r018 canonical handoff

**Outcome: INCOMPLETE_REVIEW. The terminal verdict is withheld.**

- **No finding at MED or above.** Three LOW hardening findings are batched:
  - R18-01: the handoff cannot be qualified or rebuilt from the delivered bytes, because the review archive is left out.
  - R18-02: the r016–r018 work-selection records no longer follow the release's own work-selection rule.
  - R18-03: "planning is pure" is overstated; the first plan or inventory call writes a per-user file.
- **Everything present checks out.** Custody of the handoff, release, partition, qualification receipt and META records recomputes exactly. So does the new adaptive cold-boot archive, which embeds the delivered runtime byte for byte.
- **Positive-path behaviour matches the docs.** Planning never downloads; optional packs need a binding or explicit download authorization; the installer still pins the exact runtime root.
- **Why the verdict is withheld:**
  - The full Tier 2 replay and rebuild cannot run on these bytes (R18-01). A partial replay passes 319 of 347; every non-pass is explained by the missing review custody or by Windows.
  - The independent Tier 1 leg has not been performed. No operator kit was delivered, and per your instruction I did no adversarial testing.

This review grants nothing: no publication, deployment, installation, application execution, network, identity, federation, DKN binding, pack acquisition, program admission, A5, G0 or production authority. Standing remains INFORMATION_ONLY, authority effect NONE, real A5 false, G0 closed; the subject stays DKN-unbound.

## Subject

| Item | Value |
|---|---|
| Handoff | `71914e42-MOSAIC-UCM-PIPPI-v0.1-r018-CANONICAL-HANDOFF.zip` `453289f6…` |
| Delivery manifest | root `f02a5539…`, schema `mosaic.ucm.pippi-canonical-handoff.v0.1`, 7 members, `review_custody_inline: false` |
| Release | root `a7385417…`; identity `992c5af8…`; source manifest `77216006…` (1,192 rows); custody denominator 82 |
| Runtime | `e01267ac…`, manifest root `332c1314…`, 849 members |
| SDK / lineage | `6cff37b3…` (1,117) / `17a32713…` (7) |
| Review archive | `f7c638da…` (43,222,882 bytes): pinned by release and receipt, **not delivered** |
| Cold boot | `PIPPI-v0.1-adaptive-cold-boot.zip` `9c0698ad…`, manifest root `42ad6126…`, 24 members |
| Qualification receipt | root `ceb1cb9a…`, 347 tests, builder Python 3.12.10, 0/0/0 |

**Execution.** All runs used `python3 -I -B` in an empty environment, on disposable copies.
- Stdlib checks ran on system CPython 3.12.3 and 3.13.16.
- Subject code ran only in the two previously authorized virtualenvs, and only for:
  - the qualification and build tools (both refused at their source check);
  - an unmodified `unittest` discovery of the shipped tests;
  - `verify_runtime_tree.py` and the read-only orientation commands;
  - the program builders' `--check` mode;
  - the work-unit validators;
  - the documented `pack-list`, `pack-inventory` and `install-plan` commands, against a disposable home directory.
- The launchers, the installer and its PowerShell script were read, not run. Nothing was installed and no network was used.

## Tier 0: custody

**Handoff and release.**
- The delivery manifest root recomputes, its rows match the bytes, and the member set is closed. It binds the release root and the qualification root.
- The release record root and partition root recompute, and all present artifact pins match.
- Runtime, SDK and lineage archives:
  - deflate only; manifest roots recompute and equal the release record; rows match; sets are closed; revision r018;
  - **META:** the state root recomputes and its rows equal the payload; THR H_s, H_c, H_j, H_m, H_r and `h_body` recompute; DKN `DECLARED_UNBOUND`, with no key and no permission; the self-certificate is unsigned and READY, and binds state, THR, DKN, identity and source.
- **Source reconstitution:** the SDK and lineage payloads equal every non-custody row of the 1,192-row source manifest exactly. The 82 custody rows equal the denominator and all sit under the custody prefixes, so they live only in the missing review archive. The runtime is a byte-identical subset of the SDK.
- **Identity:** the root recomputes, equals the release record and binds the source. Scope is `EXACT_PUBLIC_SOURCE_AND_RELEASE`; status `CANDIDATE_BUILDER_QUALIFIED_OPERATOR_TIER1_PENDING`.
- **Receipt:** binds source, release root, identity, runtime manifest root and the runtime, SDK, lineage and review hashes. The review hash equals the release pin. It lists 347 unique test ids, and their set root recomputes.

**Adaptive cold boot (new).**
- The receipt pins its hash and five roots, and all of them recompute:
  - hash `9c0698ad…`;
  - manifest root `42ad6126…` (keyed `manifest_root`);
  - state `e3ae429d…`;
  - THR body `b4808e3e…`;
  - DKN `9d6bed2f…`;
  - certificate `ac8ff239…`.
- Deflate only, no unsafe or duplicate names; 24 rows match and the set is closed.
- THR commitments and `h_body` recompute.
- The certificate is unsigned and READY. It binds its own state, THR and DKN roots, plus the release identity and source manifest.
- **What it carries:**
  - `UCM/UCM-v0.1-runtime.zip`, byte-identical to the delivered runtime;
  - six documents byte-identical to runtime files (the cold-boot contract and doc, the capability-surface registry, the mediation library, the skill and the UGK profile);
  - generated shell completions;
  - a boot record that pins runtime `e01267ac…`, with `native_enforced_available: false`.

**Delta since r014.**
- 706 files are unchanged, 53 changed and 86 added; none were removed.
- New modules: `ccp_courthouse`, `pippi_adaptive` and `pippi_installer`.
- New: VBS and BAT launchers, the pack registry and capability-surface specs, and program records for r015–r018.
- r015–r017 were never delivered to me as releases.

## Tier 2: replay and rebuild

**Full replay and rebuild: not possible.** On both interpreters, `run_public_release_qualification.py` and `build_release.py` stop immediately with `SOURCE_MANIFEST_BYTES_OR_SET_MISMATCH`, because the 82 review-custody rows are absent (R18-01).

**Partial replay.** Running the shipped tests with the qualification tool's own discovery and import paths, but without its source-custody gate:

| | 3.12.3 | 3.13.16 |
|---|---|---|
| Collected | 347 (ids = receipt) | 347 |
| Pass | 319 | 319 |
| Non-pass: review custody absent | 26 | 26 (same set) |
| Non-pass: Windows-only (`mosaic_ui.win32`) | 2 | 2 |

All 26 custody non-passes name a missing file under `review/`, `operator/`, `operator-kits/` or `integration/*-returns/`, or fail the source-manifest check. All the new r015–r018 tests that don't need those files pass. These include courthouse positives, adaptive turn/ABI/CLI, cold-boot determinism and nested runtime verification, packs, planning, portability, inventory, and the installer probe. This is supporting evidence only. It is not the receipt's replay, because the receipt is bound to a source this handoff cannot reconstitute.

**Runtime.**
- `verify_runtime_tree.py`: PASS (root `332c1314…`, 849 members).
- `orient`, `capabilities`, `profiles`, `smoke` and `abi-stability` all exit 0 and give identical output on both interpreters.

**Program builders (`--check`, nothing written).**
- `build_ccp_native_program`: PASS. Counts unchanged: 13 stages, 32 requirements, 116 cases.
- `build_ccp_courthouse_program`: PASS, inventory root `094b4bea…`, 7 records.
- `build_pippi_adaptive_program`: cannot run, because it needs `operator/pippi-adaptive-r018/RUN-TIER1.py` from the review custody.
- `build_pippi_interface_program`: `MISMATCH:SOURCE-DENOMINATOR.json`. Its r016 denominator hashes 16 live files that later revisions changed. This is historical drift; no test covers it (R18-04).

## Packs, planning and launchers

**Planning (documented commands, disposable home).**
- `pack-list`, `pack-inventory` and `install-plan` give identical output on both interpreters.
- `install-plan FULL_MOSAIC` returns HELD with `plan_performs_effects: false`:
  - built-in packs are PRESENT;
  - the courthouse, Memory Vault, native host and UGK runtime adapters need an external binding;
  - SemCrys is `REMOTE_DOWNLOAD_NOT_SELECTED`.
- With `--allow-remote-downloads`, SemCrys becomes `DOWNLOAD_REQUIRES_USER_AUTHORIZATION`, still HELD.
- An unknown profile is refused with a usage error (exit 64).
- The two bundled optional-pack manifests match their registry pins.

**No network code.** Nothing in `ucm/` or the new modules imports a network library, and none of the launchers or install scripts download anything. The installer UI states `installer_performs_downloads: False`.

**Launchers (read, not run).**
- The four new VBS files run `cmd.exe` with a hidden window.
- `install/INSTALL-PIPPI.vbs`:
  - requires a 64-character root and refuses quotes, `& | < > ^ % !` and line breaks in every field;
  - runs `INSTALL-PIPPI.ps1` hidden with `-ExecutionPolicy Bypass` (an existing pattern);
  - logs to `%TEMP%`.
- The PowerShell script still compares the external root against the manifest of the staged, existing and installed runtime, four checks in all.

## Findings

### R18-01 (LOW, completeness): the canonical handoff cannot be qualified or rebuilt from its own bytes

- The release and receipt pin `UCM-v0.1-review.zip` (`f7c638da…`), which holds the 82 custody rows of the source manifest, but the handoff leaves it out by design.
- As a result:
  - the shipped qualification replay and the release rebuild both refuse with `SOURCE_MANIFEST_BYTES_OR_SET_MISMATCH`;
  - `verify_release` cannot verify all four artifacts;
  - 26 of 347 receipt tests cannot pass.
- `START-HERE.md` discloses the exclusion, and nothing is misrepresented, so this is LOW. But a receipt that a reviewer cannot replay is a builder claim. From r007 to r014 this leg was independently reproducible.

**Repair:** ship the review archive alongside the slim handoff for review deliveries (or as a pinned sibling), so that replay and rebuild can run.

### R18-02 (LOW, hardening): r016–r018 work-selection records bypass the release's own rule

The governed rule is `pippi_work_units`, which r009/r010 introduced and you asked to be dogfooded. Under it, a selection must:
- validate an acceptance case that has `subject_root`, `verification_surface` and `current_status`;
- use `work_class` `DIRECT_ACCEPTANCE_CLOSURE` or `SHARED_INFRASTRUCTURE`;
- carry `implementation_effect_authorized: false`.

How each revision's records compare:
- **r014 and r015:** conform, and rebuild exactly.
- **r016:** `WORK-SELECTION.json` keeps the canonical schema id `mosaic.ucm.pippi-work-selection.v0.1`, but the content doesn't conform:
  - `work_class: "DIRECT"`;
  - `selection_basis: ONE_ACCEPTANCE_CASE_DIRECT_CLOSURE`;
  - no `implementation_effect_authorized` field;
  - its acceptance case has no `subject_root`.

  The release's validator refuses it (`PIPPI_ACCEPTANCE_SURFACE_INVALID`).
- **r017/r018:** the 15 records use new parallel schemas (`pippi-adaptive-acceptance-case`, `pippi-adaptive-work-selection`) built by a separate builder. They have no subject binding, verification surface, case status or effect flag. All 15 are refused by the governed validator.

Each record does name a closure test that is in the receipt, so the traceability is real. But the selections are no longer bound to the subject they close. One schema id now means two different shapes, which is a silent semantic change.

**Repair:** generate r016–r018 selections through `pippi_work_units`, or version the alternative schema explicitly and give it a validator. Never reuse the canonical id for a different shape.

### R18-03 (LOW, hardening): "planning is pure" is overstated

- `pack-inventory` and `install-plan` persist a default `INVENTORY.json` under the per-user data directory on first call. This is `PackStore.initialize()`; `pack-list` writes nothing.
- The file holds only the default inventory and grants nothing. But `START-HERE.md` says "Planning is pure", and the plan reports `plan_performs_effects: false`.

**Repair:** read the default inventory without persisting it in the plan and inventory paths, or document the first-use write.

### R18-04 (INFO): observations

- **Unreviewed revisions:** r015–r017 were never delivered as releases. Their changes (courthouse, interface, adaptive) are covered here only by custody, the partial replay and reading.
- **Delegation backwards in `START-HERE.md`:** it says the BAT launchers "delegate to the hidden VBS paths", but it is the other way round: each VBS runs its BAT or `PIPPI.cmd` hidden, and the BAT files call `PIPPI.cmd` directly.
- **Historical builder:** `build_pippi_interface_program.py --check` fails on the r018 tree (stale r016 denominator).
- **No operator kit:** the r018 kit `UCM-PIPPI-v0.1-r018-OPERATOR-REVIEW-READY` is referenced but not delivered. Its builder test needs review custody.
- **Interpreter choice:** `PIPPI.cmd` picks the interpreter through `py` or `PATH`. The receipt root still depends on the Python patch version, and two tests are Windows-only.

## Carried-finding dispositions

| Finding | Disposition |
|---|---|
| CCP14-01 (INFO) | carried; extended by R18-04 |
| CCP13-01/02, CCP13R-01, REL9-01, REL7-01, REL4-01/02 | closed earlier. Their tests pass in the partial replay, except the two r014 kit tests (kit labels; crash-record hashing), which read the kit from review custody. |

## Not performed

- **Full Tier 2 qualification replay and release rebuild:** blocked by R18-01.
- **Tier 1:** no kit delivered; and per your instruction, no adversarial testing.
- **Windows execution:** launchers, installer, service, dashboard and `mosaic_ui.win32`.
- **Separate review of r015–r017.**
- **Content review of the CCP product cases or the courthouse protocol.**

## State

r018 turns P/PPI into a modular, pack-based product with an adaptive cold boot. The pack layer keeps acquisition, installation, binding and authority as separate states, and on every path I exercised it plans without downloading.

By component:
- **Release custody, certification and cold-boot packaging:** production-shaped, unbound by design.
- **Qualification:** a builder claim for this handoff. It is not reproducible from the delivered bytes.
- **Work-selection discipline:** has drifted since r015.
- **Tier 1 and Windows legs:** open.

## To clear

1. Deliver the review archive with the handoff, so that replay and rebuild can run (R18-01).
2. Batch R18-02 and R18-03.
3. Have a reviewer independent of the build perform Tier 1 on runtime `e01267ac…`, including the Windows legs.

If that finds nothing at MED or above, a terminal recommendation becomes possible.

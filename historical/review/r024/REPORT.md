# Independent review: UCM v0.1 r024 portability and determinism

**Outcome: HOLD_FOR_REPAIR.**

One MED finding (R24-01). The generated P/PPI contracts were not regenerated for r024, so the shipped cold-boot archive gives a cold-booted agent the r023 contract:
- its surface registry and shell completions lack all five new portability commands;
- its mediation library lacks both new portability rules.

The release's own generator `--check` refuses 11 of 12 files on both interpreters, and no test runs it. The work order says any reproducibility failure is HOLD_FOR_REPAIR.

Everything else r024 set out to fix is fixed:
- **R23-01 (path ordering) is closed.** Both frozen registries are in POSIX order and verify on Linux under 3.12.3 and 3.13.16. The replay passes 417 of 419 on both, with only the usual two environment non-passes.
- **R23-02 (r021 court history) is closed.** The original r021 court is restored, the repaired court you ran is preserved, and the r023 adaptation has its own successor directory. All of these are byte-identical to the real deliveries I hold.
- **R23-03 (launcher name) is closed.**
- **The release reproduces:** custody is exact, and the release and cold boot rebuild byte-identical.

This review grants nothing: no publication, deployment, installation, executor binding, admission, network, identity, DKN binding, A5, G0 or production authority. Standing remains INFORMATION_ONLY, authority effect NONE, real A5 false, G0 closed.

## Subject identity

No expected values were supplied, so these are observed values, recomputed rather than read.

| Field | Observed |
|---|---|
| Transport SHA-256 | `241ba777cd620daf8ed2a39b41f20f1cd0f5a56f969446e944b8a917f01ff179` |
| Revision | `r024` |
| Release root | `b75285baf68dc938837acf29c1361e394e55dc268550ae0652065c300c3b4eb4` |
| Qualification root | `852fa36e834eb03634f9be9eb81add2972ec215ebedabad291a1a5338cf36d16` (419 tests) |
| Runtime SHA-256 | `03b340f4b2e4ecbe4f576dc4431a45fb540aaf162680cacb4707f23e43b003d2` |
| Source root | `bde77dbbd4e494756fe2ff35063a6a38669e87318d06d87bf5814864868ab4a3` |
| Predecessor (labelled binding) | r023: qualification `90442801…`, source `c3bb27e8…`, equal to the r023 release I reviewed |

The transport's subject fields equal these values. No earlier review's results were carried.

**Execution.**
- All runs used `python3 -I -B` in an empty environment, on disposable copies.
- Subject code ran only in the two authorized virtualenvs.
- Independent checks used my own stdlib scripts.
- The court and launchers were read, not run. No adversarial testing; nothing installed; no network.
- **First replay attempt:** it stopped at once because the qualification tool now requires `--portability-gate`. When restarting it, I accidentally started one replay untracked. I stopped it and recorded its stray exit line separately. The tracked 3.13 run then re-verified its source tree against the manifest before testing.

## Items 1–2: custody and source

- **Transport:** root recomputes; 14 rows match; set closed. It binds release, qualification, runtime, source and kit.
- **Release record and partition:** roots recompute, and the four artifact pins match.
- **Archives:**
  - deflate only; manifest roots recompute; rows match; sets closed;
  - **META:** state, THR and certificate roots recompute; DKN `DECLARED_UNBOUND`; certificate unsigned and READY; revision r024.
- **Source:** the SDK, review and lineage payloads cover all 1,639 rows exactly. The 113 custody rows equal the denominator, and the runtime is a byte-identical subset of the SDK.
- **Extra SDK files:** the SDK also carries five files outside the source manifest: the portability evidence (gate and two witnesses, byte-identical to the transport copies), a 65.8 MB portability source archive, and `PORTABILITY-SOURCE-MANIFEST.json` (R24-02).
- **Identity and receipt:** both roots recompute; the receipt's bindings and 419-id set root hold.
- **Cold boot:** hash and five roots equal the receipt, and it embeds the runtime byte for byte. But it carries stale contracts (R24-01).

## Items 3–4: frozen history — R23-01 and R23-02 CLOSED

**Program registry: 21 directories, root `105ada3b…`.** My own stdlib script rebuilt every row from the files:
- all bytes match;
- every stored member list is in POSIX order, including the three directories that broke in r023 (`maturity-evolution`, `pippi-r010`, `pippi-r011`);
- every directory root and the registry root recompute.

`program_history._members` now sorts by relative POSIX path.

**Operator registry: 11 directories, root `95869c1e…`.** Same results, and its covered directories are:
- `operator/dependency-graph-r021`: the **original** r021 court, byte-identical to the r021 kit's court;
- `historical/operator-preimages/r021/original`: the original kit zip (byte-identical to the r021 kit I reviewed), its manifest, court, declaration, runtime and receipt;
- `historical/operator-preimages/r021/repaired`: the repaired kit zip (byte-identical to the addendum's), its court, repair disposition and **your 16/16 evidence** (byte-identical to the addendum's evidence);
- `operator/dependency-graph-r023-compat`: the r023 adaptation, byte-identical to the court that r023 had put over the original;
- the r017–r020, r022 and r023 court directories.

**Builders.** Every program and registry builder's `--check` passes on both interpreters, and nothing is written. The historical ones report `PASS_FROZEN_CUSTODY`, including the adaptive program, which refused in r021–r023.

## Item 5: replay and rebuild

| | 3.12.3 | 3.13.16 |
|---|---|---|
| Release rebuild | byte-identical | byte-identical |
| Cold-boot rebuild and verify | byte-identical, PASS | byte-identical, PASS |
| Replay collected (ids = receipt) | 419 | 419 |
| Pass | 417 | 417 |
| Non-pass | `…native_ui_imports` (Windows only); `…wheel…` (setuptools not in the authorized venv) | same |
| History, portability and repair tests | all PASS | all PASS |
| Starting directory after replay | empty | empty |

The qualification tool now requires `--portability-gate`. I passed the gate shipped in the source; the tool checks its root, `PASS_PORTABLE` status, required legs and witness roots.

## Items 6–7: portability evidence and commands

**Witnesses.** The Windows-native and WSL-native witnesses are builder-run. Each declares its execution context, source root (`bde77dbb…`, which matches the release and the shipped portability source archive), test-set root and five canonical outputs. Both list identical outputs.

**Independent agreement from a third platform (Linux, POSIX-native, both interpreters):**
- the two live outputs I recomputed (mediation library `8833b801…`, portability policy `e5c85440…`) equal both witnesses;
- my independent rebuild of the two registry roots equals both witnesses;
- re-running `portability-gate` over the two shipped witnesses reproduces `PASS_PORTABLE` and the exact gate root `c3352990…`.

**Commands.**
- `environment-observe`, `portability-policy`, `portability-witness`, `portability-gate` and `portability-source-doctor` are reachable through the documented CLI and exit 0.
- Outputs are identical across interpreters, except the execution context, which differs only by Python version. Nothing is written.
- Over all 454 Python files in `src/` and `tools/`, the source doctor reports 37 host-flavoured sorts: 35 in `tools/`, and 2 in `src/` that sort name strings rather than paths (false positives).

## Item 8: turn openings

`prepare_turn` validates the execution context and binds `execution_context_root` into the opening, and `validate_turn_opening` re-checks it. **But** guidance injection is caller-chosen: the opening includes exactly the rule IDs the caller requests. Each rule's `triggers` list (for example `PACKAGING`, `RELEASE_PLANNING`, `PORTABILITY_CLAIM`) is descriptive metadata only, and nothing ties the requested rules to the turn's `scenario`. "Only for selected scenarios" holds only in the sense that the caller selects (R24-03).

## Item 9: launcher — R23-03 CLOSED

`RUN.cmd` calls `"%~dp0RUN.ps1"`, and `RUN.ps1` is present. It:
- pins kit `f1723026…`, matching the kit's hash;
- extracts to a disposable folder;
- runs the court;
- copies the evidence out before reporting status;
- always removes the disposable folder.

## Acceptance cases and kit

- **Cases:** all six `portability-determinism-r024` cases validate and rebuild exactly under `pippi_work_units`: `UNMET`, `implementation_effect_authorized: false`, each with a receipt test that passes on both interpreters.
- **Kit (static):**
  - 9 entries; kit root and rows recompute; set closed;
  - labels `builder_authored: true`, `operator_executed: false`, `tier1_executed: false`;
  - the runtime, receipt, gate and witnesses inside are byte-identical to the transport, and the cold-boot pin matches;
  - the court is byte-identical to review custody, with 18 cases.

## Findings

### R24-01 (MED, reproducibility): the shipped cold boot carries the r023 P/PPI contracts

`tools/build_pippi_adaptive_contracts.py --check` refuses on both interpreters. 11 of its 12 generated files no longer match what the code produces:
- `spec/PIPPI-CAPABILITY-SURFACE-REGISTRY.json`;
- `spec/PIPPI-ADAPTIVE-COLD-BOOT-CONTRACT.json`, still `revision: r023`;
- `spec/PIPPI-MEDIATION-LIBRARY.json`;
- all eight shell-completion files.

None of them contains Windows line endings; they are stale. `build_pippi_cold_boot.py` copies these files into the cold boot, so the shipped cold boot (`5a25631c…`) has:
- a surface registry and bash, zsh, fish and PowerShell completions with **none** of `environment-observe`, `portability-policy`, `portability-witness`, `portability-gate` or `portability-source-doctor`;
- a mediation library with 12 rules and **no** `EXECUTION_CONTEXT_DISCIPLINE` or `PORTABILITY_DETERMINISM` rule (root `6099c407…`). The live code and both witnesses use `8833b801…`.

So an agent booted from the cold boot can't discover r024's portability surfaces or receive its portability guidance. The witnesses' "canonical" mediation-library output is not the one that ships. The cold boot still rebuilds byte-identically, because it faithfully copies the stale files, and no test runs the contracts check.

**Repair:** regenerate with `build_pippi_adaptive_contracts.py --write`, rebuild the cold boot, and add a qualification test that runs the contracts `--check`. Consider also having the portability witness compare the shipped mediation library's root rather than only the live one.

### R24-02 (INFO): `PORTABILITY-SOURCE-MANIFEST.json` is stale

This SDK file has the same 1,639 paths and byte total as the release source manifest, but a different root (`9ebe7ef9…` vs `bde77dbb…`). The difference is one row: `tests/test_pippi_release_packaging.py`, whose recorded hash matches neither the release copy nor the copy in the shipped portability source archive. The archive itself matches the release source exactly, and the witnesses bind `bde77dbb…`, so nothing depends on the stale manifest. It should be regenerated or removed.

### R24-03 (INFO): portability evidence design

- **Read, not recomputed:** three of the five witness "canonical outputs" (both frozen registries and the r024 program) are read from the root already stored in each file, not recomputed, so they can't diverge across platforms. The real cross-platform checks are the leg's tests, which do assert POSIX ordering on any host and verify the operator registry.
- **Declarations:** witnesses are declarations (the caller supplies outputs and status), and the gate compares declarations. Both legs here are builder-run.
- **Assumed, not probed:** `observe_execution_context` labels its result observed, but sets case sensitivity from the platform name: Windows and macOS are assumed case-insensitive.
- **Turn guidance is caller-selected** (item 8); rule triggers aren't enforced against the scenario.
- **Doctor coverage:** the source-doctor test covers a fixed list of 9 files. 35 unkeyed path sorts remain in `tools/`, mostly historical kit and program builders.

### R24-04 (INFO): carried observations

- R21-01's secondary items (`verify_evaluation` not on the CLI; closures shape-check evaluations).
- `sim.add` parameter shape is checked only at evaluation.
- The r022 PASS-run kit (`c277ad3d…`) was never delivered.
- R20-01 is unchanged.
- Cases bind to the predecessor source.
- r015–r017 were never reviewed.
- The receipt root depends on the Python patch version; two tests are Windows-only.

## Carried-finding dispositions

| Finding | Disposition |
|---|---|
| R23-01 (MED) | **CLOSED**: registries in POSIX order; verified independently and by replay on both interpreters |
| R23-02 (LOW) | **CLOSED**: original, repaired and r023-adapted r021 courts all preserved, byte-exact |
| R23-03 (INFO) | **CLOSED** |
| R23-04 (INFO) | carried in R24-04 |
| R21-01, R21-02, R22-01 and earlier | closed; no regression |

## Not performed

- **Tier 1:** the court was not run, per your instruction; it is builder-authored in any case.
- **Windows and WSL legs:** these are builder evidence; my Linux run is a third, independent agreement on the declared outputs, not a substitute for either leg.
- **The wheel test** (venv constraint).
- **Content review** of the CCP cases, the courthouse protocol and the dependency requirements.

## State

r024 makes the release deterministic across Windows and POSIX hosts: path ordering is explicit, frozen history (program records and operator courts) is complete, exact and verifiable everywhere, and a two-leg portability gate is part of qualification. The one gap is packaging: r024's new agent-facing contracts were never regenerated, so the cold boot still describes r023.

## To clear

1. Repair R24-01: regenerate the contracts, rebuild the cold boot, and add a contracts `--check` test.
2. Optionally address R24-02 and R24-03.
3. Have a reviewer independent of the build perform Tier 1 on the repaired runtime, including the Windows and WSL legs.

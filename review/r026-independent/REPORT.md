# Independent review: UCM v0.1 r026 runtime-parity focused transport

**Outcome: INCOMPLETE_REVIEW. The terminal verdict is withheld.**

- **No finding at MED or above.**
- **The R24-01 repair holds on everything this transport lets me check:**
  - the mediation library and all eight completion files in both the runtime and the cold boot are exactly what the live code generates;
  - the cold-boot contract is now r026, and its recorded mediation, surface and capability roots equal the live ones;
  - the surface registry lists the new portability commands.
- **Two of my R24-03 points are closed by source:**
  - the observed execution context now probes the actual filesystem;
  - turn openings now add every scenario-required rule mechanically and refuse a resealed omission.
- **All five witness outputs agree from a third platform:** recomputed on Linux under both interpreters, they equal both the Windows and WSL witnesses.
- **One LOW finding (R26-01):** `portability-source-doctor` is the only `pippi` command missing from the P/PPI surface registry that the cold boot ships.
- **Why the verdict is withheld:** this focused transport deliberately omits the SDK, review and lineage archives. The work order's own items 2 (reconstitution), 4 (portability source), 8 (replay and rebuild) and part of items 3 and 5 can't be performed without them. Tier 1 is unexecuted, and per your instruction I didn't run it.

This review grants nothing. Standing remains INFORMATION_ONLY, authority effect NONE, real A5 false, G0 closed.

## Subject identity

No expected values were supplied, so these are observed values, recomputed rather than read.

| Field | Observed |
|---|---|
| Transport SHA-256 | `a886b5a9674dcee0994ee7901dd38278d02af58cfed1ac0aaaebd4fd872be41c` |
| Revision | `r026` |
| Release root | `ab23924e363cac303a11638c8decf774bea4e6322fc6e41ba722bd89f4db7d5c` |
| Qualification root | `f1f5c4bbc4077077cc86cdafaf8f4c37ac00c8d8f606b3e4e57e32d3e16bcc0a` (424 tests) |
| Runtime SHA-256 | `031e906105eabf2201d55aaa6d3437ae42fa1f6126f01f5de792d9a4c495e270` |
| Source root | `d61502f23fce6cdeb7772b4ee3d3efd3d36249f276fde86d976ae09e6f0c595c` |
| Cold boot | `57b3ed049f63e1e8c704c9dfca26cec6198b38c1d7f2def769a30b0c00c994af` |
| Operator kit | `d06b308d9577021abb585c9f8b1d4508231c0c7c9031f8fdf18a7b143aca6058` |

**Predecessor.** The release identity record is in the SDK, which isn't here, so I couldn't verify the predecessor binding. r025 was never delivered to me; the only trace is your r025 HOLD evidence inside the kit.

**Execution.**
- All runs used `python3 -I -B` in an empty environment, on disposable copies.
- Subject code ran only in the two authorized virtualenvs, and only for:
  - live contract generation;
  - registry and policy roots;
  - `environment-observe`, from an empty directory.
- Registry rows were rebuilt with my own stdlib script.
- The court and launcher were read, not run. No adversarial testing; nothing installed; no network.

## Item 1: custody (everything present)

- **Transport:** root recomputes; 11 rows match; set closed. It binds release, qualification, runtime, kit and source, and records `qualification_replay_complete: false`.
- **Release record and partition:** roots recompute, and the runtime pin matches. The SDK, review and lineage pins exist but those archives are absent.
- **Runtime archive:**
  - deflate only, 1,160 members; manifest root recomputes and equals the release; rows match; set closed;
  - **META:** state root and rows, THR commitments and body, DKN `DECLARED_UNBOUND` with no key, and the certificate (unsigned, READY, binds identity and source, revision r026) all recompute.
- **Receipt:** root recomputes. It binds source, release, identity, runtime and runtime manifest root, and its SDK, review and lineage pins equal the release's. It lists 424 unique ids with a recomputing set root, and binds the portability gate root.
- **Gate and witnesses:** all three roots recompute, and both witnesses bind source `d61502f2…`.
- **Cold boot:** hash and five roots equal the receipt. Rows match; THR and certificate bindings recompute; it embeds the runtime byte for byte.
- **Kit:**
  - kit root and 11 rows recompute; set closed;
  - labels `builder_authored: true`, `operator_executed: false`, `tier1_executed: false`;
  - the runtime, cold boot, receipt, gate and witnesses inside are byte-identical to the transport;
  - the launcher pins the kit hash, uses a disposable folder, prints progress, preserves evidence, cleans up and pauses.

## Item 3: generated contracts — R24-01 repaired in substance

I regenerated every contract that comes from a pure library function, under both interpreters (identical output), and compared the bytes:

| File | Runtime = live | Cold boot = live |
|---|---|---|
| `spec/PIPPI-MEDIATION-LIBRARY.json` (root `4afa21e2…`, with `EXECUTION_CONTEXT_DISCIPLINE` and `PORTABILITY_DETERMINISM`) | yes | yes |
| `completions/pippi.{bash,zsh,fish,ps1}` and their `.json` contracts (8 files) | yes | yes |

- The surface registry is identical in the runtime and the cold boot. Its root recomputes, and its `capability_registry_root` equals the live registry root (`5c80f811…`).
- The cold-boot contract says `revision: r026`. Its mediation, surface and capability roots equal the live and shipped values.
- **Not performed:** `build_pippi_adaptive_contracts.py --check` itself, which ships in the SDK. The registry and contract are confirmed against their recorded roots and the live registry, not by rerunning that builder.

## Item 5: canonical outputs and frozen registries

The witnesses' denominator is now five outputs. Both witnesses list identical values, and all five reproduce on Linux:

| Output | Witnesses | Linux, recomputed |
|---|---|---|
| `CAPABILITY_REGISTRY` | `5c80f811…` | live registry root, equal |
| `MEDIATION_LIBRARY` | `4afa21e2…` | live, equal |
| `PORTABILITY_POLICY` | `863a2234…` | live, equal |
| `FROZEN_PROGRAM_REGISTRY` | `24bd1750…` | registry root recomputes; 19 of 23 rows rebuilt from the runtime's files, in POSIX order, all exact |
| `FROZEN_OPERATOR_REGISTRY` | `7622e61d…` | registry root recomputes; its 13 rows cover review-custody and historical directories, which aren't in this transport |

The witness tool ships in the SDK, so I couldn't confirm by reading it that it now recomputes rather than copies stored roots. The registry rows I could rebuild agree with the stored roots.

## Item 6: case probe — CLOSED

- `observe_execution_context` now calls `probe_case_sensitivity(Path.cwd())`. That creates `.pippi-case-probe-<random>` exclusively, checks whether the upper-cased name resolves, and always deletes it.
- Observed contexts must carry `case_sensitivity_source: PROBED_CURRENT_FILESYSTEM`, and declared ones `DECLARED_BY_CALLER`; a mismatch refuses.
- Run from an empty directory on both interpreters, it reports `POSIX_NATIVE`, case-sensitive, probed, and leaves the directory empty.

## Item 7: scenario selection — CLOSED

- `SCENARIO_TRIGGERS` maps seven scenarios to trigger sets. `prepare_turn` refuses an unknown scenario (`PIPPI_SCENARIO_INVALID`) and selects the union of the caller's rules and every rule whose triggers intersect the scenario's.
- `validate_turn_opening` recomputes that required set and refuses an opening missing any of them, even if resealed.
- This is by source; the corresponding tests ship in the SDK.

## Your r025 operator run (carried in the kit)

- Its manifest recomputes. Result `HOLD_FOR_REPAIR`, 25 cases, 3 failed, on r025 runtime `3a8d00e7…`:
  - `CONTROL-GENERATED-CONTRACTS` (`KeyError`);
  - `CONTROL-COLD-BOOT-CONTRACT-PARITY` (`FileNotFoundError`);
  - `CONTROL-AUTHORITY-CEILING`.
- The authority-ceiling case is defined as "every earlier case passed and authority effect is NONE", so it failed only because of the other two; it isn't an authority breach.
- r026's court keeps those controls and adds cases for runtime-completion boundaries, cold-boot/runtime parity, recomputed witness outputs, stored-root substitution, scenario-rule injection and omission, and probe cleanliness.

## Findings

### R26-01 (LOW, runtime parity): one P/PPI command is missing from the shipped P/PPI surface registry

- The P/PPI surface registry (59 surfaces) is a filtered subset of the live capability registry (194).
- `INSPECT_PIPPI_PORTABLE_SOURCE` (`pippi portability-source-doctor`) is in the live registry and in all four completion scripts, but is classed under `DEVELOPMENT_STANDARDS`, so the filter drops it.
- It is the only `pippi`-routed surface absent from the registry the cold boot ships. A cold-booted agent can therefore see the command in completions but not discover it as a P/PPI surface.

The generated bytes are faithful to their generator, so I've rated this LOW rather than a parity failure. If you count any P/PPI surface missing from the cold boot as runtime parity, the work order would make it HOLD_FOR_REPAIR.

**Repair:** include every route in `ADAPTIVE_CLI_ROUTES` in the surface registry regardless of system, or reclassify the surface, and add a test that the registry covers that map.

### R26-02 (INFO, completeness): required legs need the full transport

The focused transport omits the SDK, review and lineage archives by design, so these legs were not performed:
- item 2: reconstitution and the runtime-subset check;
- item 3: the generator `--check`;
- item 4: the portability source manifest (my R24-02) and source archive;
- item 5: 4 historical program rows and all 13 operator rows;
- item 8: replay on both interpreters, and the release and cold-boot rebuilds.

The predecessor binding and the witness tool's recompute behaviour also need the SDK.

**To clear:** deliver the `FULL-REPLAY-REVIEW-TRANSPORT`.

### R26-03 (INFO): observations

- **The probe writes.** `environment-observe` now briefly writes into the working directory, so in a read-only directory it refuses (`PIPPI_CASE_SENSITIVITY_PROBE_FAILED`) rather than reporting.
- **Carried:** R21-01's secondary items; `sim.add` parameter shape is checked only at evaluation; R20-01; r015–r017 and r025 never reviewed; two Windows-only tests; the receipt root depends on the Python patch version.

## Carried-finding dispositions

| Finding | Disposition |
|---|---|
| R24-01 (MED) | **repaired in substance**: runtime and cold boot equal live generation for every checkable file, and the contract is r026; the generator `--check` awaits the full transport |
| R24-02 (INFO) | not checkable here (SDK) |
| R24-03 (INFO) | case probe **closed**; scenario selection **closed**; recomputed-output tool and doctor coverage need the SDK |
| R23 and earlier | closed in r024; no regression visible in the runtime |

## Not performed

- Items 2, 4 and 8, and parts of items 3 and 5 (R26-02).
- **Tier 1:** builder-authored and unexecuted; not run, per your instruction.
- **Windows and WSL legs** (builder witnesses only); the wheel test.

## State

r026 fixes the r024 packaging defect where it matters most: what a cold-booted agent receives now matches the live runtime, with one narrow gap (R26-01). It also turns two portability conveniences into enforced behaviour: a real filesystem probe, and mechanically required scenario guidance. What it does not include is the material needed to replay and rebuild it.

## To clear

1. Deliver the full-replay transport so items 2, 4 and 8 and the rest of items 3 and 5 can run.
2. Repair R26-01, or confirm you accept it as LOW.
3. Have a reviewer independent of the build perform Tier 1, including the Windows and WSL legs.

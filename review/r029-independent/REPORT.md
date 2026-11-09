# Independent review: UCM v0.1 r029 collaboration integrity

**Outcome: INCOMPLETE_REVIEW. The terminal verdict is withheld.**

- **All three r028 findings are repaired in source, as recommended:**
  - **R28-01:** every signer identity must now equal the MosaicID derived from the signing key. This covers change capsules, publication receipts (building and validating them) and retrieval receipts.
  - **R28-02:** the CCP binding no longer takes a status from the caller. It validates the complete decision against its evidence and derives the status from it.
  - **R28-03:** retrieval validates the signed publication receipt, hashes the actual file, and requires the two hashes to match.
- **Your Tier 1 HOLD is a court defect, not a product failure (R29-01, LOW).**
  - Case 010 alters the CCP decision but never reseals it. The product refuses that forgery, but at an earlier check and under a different code than the case demands.
  - Case 017 failed only because it aggregates the others.
  - This is the same class of defect as R27-01. Your own unit test does the reseal correctly, and it passes.
- **The release reproduces completely:**
  - custody is exact;
  - the replay passes 442 of 444 on both interpreters, with only the usual two environment non-passes, and its test-id set equals the receipt;
  - the release, cold boot and operator kit all rebuild byte-identical on Python 3.12.3 and 3.13.16;
  - both generator `--check`s pass, and the portability source manifest rebuilds exactly.
- **Carried r028 evidence is exact.** My r028 return is byte-identical to what I delivered. Your r028 run (19/19 PASS) binds the r028 runtime and is labelled user-run.
- **Why the verdict is withheld:**
  - the independent Tier 1 leg and the Windows/WSL legs remain;
  - your run is user-run and builder-authored, so it isn't independent Tier 1, and it couldn't pass until R29-01 is repaired.

I read the court and the source. Per your instruction I ran no forgery or negative exercise.

This review grants nothing. Standing remains INFORMATION_ONLY, authority effect NONE, real A5 false, G0 closed.

## Subject identity

No expected values were supplied, so these are observed values, recomputed rather than read.

| Field | Observed |
|---|---|
| Transport SHA-256 | `8d96ae510cd207411038295f701caf35a8c8900e264c9383b9bf4706c7024566` |
| Revision | `r029` |
| Release root | `310de97a200e52a722fb93102195a6527f4ada0d0845ef69873415906ad59053` |
| Qualification root | `56d0b379ae0b7973ec0ff63d5913c5a3a60bf57e19f2bd73862a7351753946dc` (444 tests) |
| Runtime SHA-256 | `0e45fe24337952ca04b70b2bb24ffcde3aacec09606cb01488c8a425df373ecb` |
| Source root | `351eb8fdc7a2eed1d2130ade239da9b7e39c240f7d08ecc71c6a7f10790b91ab` |
| Cold boot | `b65eb2e2390efd0f02ed31648d09f9de6a1ef66d73ab3e7ab9e2bcf47aa1bad2` |
| Operator kit | `a05f665c26929b045c65353e4177efde139e8e070ec3e6834e5902f103065b1e` |

**Predecessor binding.** The release identity names r028 with qualification `f14106bf…`, identity `7dd9149c…` and source `cff86ff9…`. All three equal my r028 observations in full.

The runtime diff against r028 is 38 files changed, 24 added and none removed. The source changes are in 8 modules, including `pippi_constitution`, `pippi_credentials` and the CLI and capability files. The additions are the r029 program and work order.

**Execution.**
- Everything ran in an empty environment, from empty working directories, on disposable copies.
- Subject code ran only in the two authorized virtualenvs.
- Custody, frozen rows and the kit were checked with my own stdlib scripts.
- The court and launcher were read, not run. Nothing was installed and there was no network.

## Custody

- **Transport:** root, 14 rows and closed set verified. It binds release, qualification, runtime, kit and source.
- **Archives:** runtime 1,223 members, SDK 1,686, review 138, lineage 7. Every manifest and META verifies, and the certificates are READY at r029.
- **Reconstitution:** 1,784 source rows recompute to `351eb8fd…`.
- **Receipt:** binds everything; 444 unique ids.
- **Cold boot:** the THR, state and certificate verify, and it embeds the exact runtime.
- **Kit:** 33 members. Root, rows and closed set verify, and it is labelled builder-authored and unexecuted. Its six pinned files are byte-identical to the transport, and `RUN.ps1` pins the kit hash.

## Replay and rebuild

| Leg | 3.12.3 | 3.13.16 |
|---|---|---|
| Qualification replay | 442/444 | 442/444 |
| Non-passes | wheel (no setuptools); native UI (Windows-only) | same |
| Test-id set = receipt | yes | yes |
| Release: four archives + record | byte-identical | byte-identical |
| Cold boot rebuild / verify | byte-identical / exit 0 | byte-identical / exit 0 |
| Operator kit rebuild (`RUN.cmd`, `RUN.ps1`, kit) | byte-identical | byte-identical |
| `build_pippi_adaptive_contracts.py --check` | PASS (14) | PASS (14) |
| `build_collaboration_integrity_r029_program.py --check` | PASS (23) | PASS (23) |
| Portability source manifest | byte-identical; root = source = both witnesses | same |

## Work-order items

- **Item 3 (predecessor):** exact, as above.
- **Item 4 (carried r028 evidence):**
  - both provenance roots recompute;
  - my `REPORT.md`, `FINDINGS.json` and `RECOMPUTE.json` and the evidence ZIP (`cb9ecec6…`) are byte-identical to what I delivered;
  - your r028 operator evidence verifies: manifest rows, court root, 19/19 PASS on runtime `3e8372c2…` and receipt `eb2ea85b…`;
  - that court is byte-identical to the r028 kit's;
  - it is labelled `USER_RUN_BUILDER_AUTHORED_OPERATOR_COURT`, and r029 doesn't treat it as its own evidence.
- **Item 6 (identity from key):** `_identity_from_key` requires the declared root to equal `mosaic_id(key)`. It is applied when building changes, when building and validating publications, and when building retrievals.
- **Item 7 (retrieval):** validates the publication receipt, streams and hashes the actual file, and refuses a mismatch with `PIPPI_RETRIEVAL_ARTIFACT_HASH_MISMATCH`.
- **Item 8 (CCP):**
  - the evaluation must contain exactly the decision, use snapshot, evidence snapshot, jurisdiction profile, enforcement perimeter, correspondence and eight expected anchors;
  - `validate_admissibility_decision` recomputes the decision from those inputs and requires exact equality;
  - the use snapshot's operation must equal the transition;
  - status and roots are derived, not supplied.
- **Item 9 (credentials):**
  - salt and nonce come only from `os.urandom`;
  - the pending file is `O_CREAT|O_EXCL` at mode 0600, with a random name;
  - links and reparse points are refused on the parent and the target, before and after staging;
  - private-file protection is applied and verified on both files.
- **Item 10:** `PUBLISHED` is the only terminal state, and SEALED now leads on. The cold boot carries all 11 files of the mediated-agent skill, references included, byte-identical to the runtime.
- **Item 11 (interfaces):**
  - 31 adaptive routes, each exactly once with its exact `pippi` route, including `publication-receipt-verify`;
  - each of the 75 registry entries equals its live entry;
  - the mediation library and 8 completion files equal live generation in the runtime and the cold boot;
  - the atlas and pipeline specs equal live generation;
  - the live capability root `ba748378…` equals both witnesses.
- **Atlas and pipeline (carried positive checks):** 14 rules and 5 co-projections, with no identity equivalence. 11 states, all reachable, and no authority grant. The context reasons are exact for all 7 scenarios.
- **Frozen registries:** program 24 rows and operator 14, all rebuilt in POSIX order and equal to the witnesses. Neither has changed since r027.
- **Acceptance cases:** R29-01..07 validate and rebuild exactly, each closes on a receipt test, and none authorizes effect. They bind predecessor source `cff86ff9…`.

## Findings

### R29-01 (LOW, court defect): case 010 tests an unresealed forgery against the resealed-forgery code

- The court sets `forged["decision"]["decision"] = "REFUSE"` and nothing else. It then requires the refusal to contain `CCP_ADMISSIBILITY_DECISION_INVALID`.
- In `ccp_admissibility`, `_validate_decision_shape` runs first. The control decision's `gateway_disposition` is `SEPARATE_GATEWAY_AUTHORIZATION_REQUIRED`, which is valid only for ADMIT.
- So the forgery is refused at line 854 with `CCP_ADMISSIBILITY_GATEWAY_DISPOSITION_INVALID`, before the decision-equality check at line 892. Its `decision_root` would also have failed.
- `refuses()` matches the exact code, so it returns False and the case records `PREDICATE_FALSE`.
- `test_ccp_binding_holds_nonadmitted_transition` performs the full reseal: it sets the gateway disposition and recomputes the root. It expects `DECISION_INVALID` and passes in replay.

**Effect:** your HOLD carries no evidence of a CCP bypass, and case 017 failed only as the aggregate. Your evidence ZIP (`72b484fd…`) wasn't in the transport, so this diagnosis comes from the source path, which is deterministic. I didn't execute the forgery.

**Repair:** make the case mirror the unit test, or accept any `CCP_ADMISSIBILITY_*` refusal. Keep the unresealed variant as its own case expecting the shape refusal.

### R29-02 (INFO): observations

- **CCP anchors:** they travel in the same bundle as the decision. The binding proves that the decision is the exact evaluation of the bundled evidence against those anchors, and the decision root commits to them. It can't prove the anchors came from an independent source; that stays the caller's duty.
- **Historical programs:**
  - The carried r028 selection R28-07 names a test that r029 renamed, so it no longer resolves against the r029 receipt. It did close against r028's.
  - The r027 and r028 programs still aren't frozen.
  - The historical program builders (r026–r028) refuse `--check` against current source.
- **Publication receipts:** they check a storage locator's root and artifact hash, but don't re-run the locator's credential-mark validation.
- **Credential writes:** `write_local_credential` doesn't validate the envelope before writing it.
- **Retrieval receipts:** no validator exists for one after the fact. Verification happens only at signing time.

### R29-03 (INFO): carried

- R20-01.
- R21-01's secondary items; `sim.add` shape is checked only at evaluation.
- r015–r017 and r025 were never reviewed.
- Two Windows-only tests; the wheel test needs setuptools; the receipt root depends on the Python patch version; the case probe writes transiently.

## Carried-finding dispositions

| Finding | Disposition |
|---|---|
| R28-01 (LOW) | **CLOSED** |
| R28-02 (LOW) | **CLOSED** (anchor independence: see R29-02) |
| R28-03 (LOW) | **CLOSED** |
| R28-04 (INFO) | terminal state, credential staging, caller randomness and skill closure **closed**; frozen-registry lag carried |

## Court (read, not run)

The court has 17 cases. They cover:
- key-bound change and publication, and identity/key swaps for both;
- actual-bytes retrieval and byte mutation;
- validated CCP and resealed laundering;
- removal of the caller-supplied CCP label;
- the terminal state;
- skill closure;
- removal of caller randomness and exclusive pending files for credentials;
- CLI/ABI parity;
- the authority ceiling.

Statically, every other case's expected code or predicate matches the source. Only case 010 is defective.

## Not performed

- **Independent Tier 1:** not run, per your instruction.
- Windows and WSL legs; running the native UI.
- Negative or forgery exercises. R29-01 is by source.

## State

r029 turns the r028 collaboration primitives from recorded claims into checked facts:
- a signature now proves who signed;
- a retrieval receipt now proves the bytes matched what was published;
- a CCP-gated transition is ready only when a fully re-evaluated decision says ADMIT.

The release reproduces exactly, and every r028 finding is closed. Your HOLD comes from the court's own forgery being malformed.

## To clear

1. Repair case 010 (R29-01) and rebuild the kit.
2. Have a reviewer independent of the build perform Tier 1 on runtime `0e45fe24…`, including the Windows and WSL legs.
3. Optionally, attach the r029 user-run evidence ZIP (`72b484fd…`) so its case details can be checked against this diagnosis.

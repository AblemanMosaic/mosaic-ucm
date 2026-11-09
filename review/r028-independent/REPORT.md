# Independent review: UCM v0.1 r028 constitutional atlas

**Outcome: INCOMPLETE_REVIEW. The terminal verdict is withheld.**

- **No finding at MED or above.** Three LOW findings, all in the new signed and CCP collaboration surfaces:
  - **R28-01:** signed capsules and receipts don't bind the named identity to the signing key;
  - **R28-02:** the CCP transition binding trusts a caller-asserted `ADMIT`;
  - **R28-03:** the retrieval receipt claims a hash check it never performs.
- **The release reproduces completely.** This is the first full transport since r024:
  - custody is exact;
  - the replay passes 439 of 441 on Python 3.12.3 and 3.13.16, with only the usual two environment non-passes, and its test-id set equals the receipt;
  - the release (four archives and the record) and the cold boot rebuild byte-identical on both;
  - both generator `--check`s pass;
  - the portability source manifest rebuilds byte-identical.
- **The atlas, pipeline and context selection hold on every positive check:**
  - the atlas covers all 14 mediation rules, and no co-projection claims identity equivalence;
  - all 11 pipeline states are reachable, and no transition grants authority;
  - every scenario's reason paths are exact;
  - the runtime and cold-boot copies equal live generation.
- **Closed:** R24-01 (generator `--check`), R24-02 (portability source manifest), R26-02 and R27-02 (full-transport legs).
- **Why the verdict is withheld:** only the independent Tier 1 leg and the Windows/WSL legs remain. The court is builder-authored; per your instruction I read it and did not run it.

This review grants nothing. Standing remains INFORMATION_ONLY, authority effect NONE, real A5 false, G0 closed.

## Subject identity

No expected values were supplied, so these are observed values, recomputed rather than read.

| Field | Observed |
|---|---|
| Transport SHA-256 | `d7f5b6deae9226e8ab596e2a530b4956a1fc4dce937e4c60c2352ab986e8838a` |
| Revision | `r028` |
| Release root | `c3baa2763d709c2f1f0daaae93653e0c809dcecc7bb0a8aaf389c2315e1ab5ac` |
| Qualification root | `f14106bfb3a78e3a86d83898f07b0f567dc5d0cb7913d3a377aa4bd14f6dd08b` (441 tests) |
| Runtime SHA-256 | `3e8372c2c5dd976ef02e3af2928a06b6d5946f556cd49829d1f8ecaccabcf79f` |
| Source root | `cff86ff9d12f04385a89f43cb9e94df2310b44a7272765d60238b5c556dad3be` |
| Cold boot | `c6977374127e0d665f7476a2467bfe62e277ede57fdfe106c045e329bf5a3154` |
| Operator kit | `54196133106efac930ff1e02d63ae44219374fe1f6d0431a6a6171a6e00731ef` |

**Predecessor binding.** The release identity names r027 with:
- qualification `8c6feecd…` and source `de36dc95…`, both equal to my r027 observations;
- identity `01ab0ea8…`, which I couldn't observe in r027 because the SDK was absent.

The runtime diff against the r027 runtime I reviewed: 44 files changed, 33 added, none removed. The additions are the constitution and credential modules, the atlas and pipeline specs and doc, and `program/constitutional-atlas-r028`.

**Execution.**
- All runs used an empty environment, from empty working directories, on disposable copies.
- Subject code ran only in the two authorized virtualenvs.
- `build_portability_source_archive.py` imports a sibling module, so it ran with `-E -s -B`; everything else ran with `-I -B`.
- Frozen rows and kit custody were checked with my own stdlib scripts.
- The court and launcher were read, not run. No adversarial or negative exercises; nothing installed; no network.

## Custody

- **Transport:** root, rows and closed set verified. It binds release, qualification, runtime, kit and source, with scope `COMPLETE_SOURCE_REPLAY_AND_OPERATOR_TIER1`.
- **Archives:** runtime 1,199 members, SDK 1,653, review 129, lineage 7. Every manifest and META verifies: state, THR, DKN (`DECLARED_UNBOUND`) and certificate (READY, r028).
- **Reconstitution:** 1,747 source rows recompute to `cff86ff9…`, and the 125 custody rows equal the denominator. Four SDK files sit outside the manifest by design: the portability source manifest and the r028 gate and witnesses.
- **Receipt:** binds source, release, identity, runtime and every archive; 441 unique ids.
- **Cold boot:** binds and embeds the exact runtime.
- **Kit:** 35 members. Root, rows and closed set verify; it is labelled builder-authored and unexecuted, and its six pinned files are byte-identical to the transport. `RUN.ps1` pins the kit hash.

## Replay and rebuild

| Leg | 3.12.3 | 3.13.16 |
|---|---|---|
| Qualification replay | 439/441 | 439/441 |
| Non-passes | wheel (no setuptools); native UI (`requires Windows`) | same |
| Test-id set = receipt | yes | yes |
| `build_release.py`: runtime, SDK, review, lineage, release record | all byte-identical | all byte-identical |
| `build_pippi_cold_boot.py` | byte-identical (`c6977374…`) | byte-identical |
| `verify_pippi_cold_boot.py` on the delivered cold boot | exit 0 | exit 0 |
| `build_pippi_adaptive_contracts.py --check` | PASS (14) | PASS (14) |
| `build_constitutional_atlas_r028_program.py --check` | PASS (26) | PASS (26) |
| Portability source manifest rebuild | byte-identical (`1d100eed…`) | byte-identical |

## Atlas, pipeline and context (work-order content)

Identical output on both interpreters.

- **Atlas denominator:** 14 rules, in the same order as the mediation library. Every rule has non-empty systems, surfaces, evidence fields, refusal codes and ablation failure modes, and every named surface exists in the live registry. The ablation status is honestly labelled `HISTORICAL_EVIDENCE_REFERENCED_NOT_REEXECUTED`.
- **Co-projections:** 5; none claims identity equivalence. The validator demands exact equality with live generation, so any change is refused.
- **Pipeline:** 11 states and 10 transitions.
  - Every endpoint is known, every state is reachable from REGISTERED, and no state has more than one outgoing transition.
  - Every required rule is in the atlas, and no transition grants authority.
  - Only ORIENT_PROJECT skips the CCP check.
  - The model binds the atlas root.
- **Context selection:** I ran all 7 scenarios, each with no requested rules and with all rules requested.
  - Required rules always carry `SCENARIO_REQUIRED` with their matched triggers.
  - Explicit additions carry `EXPLICIT_REQUEST` exactly when no trigger matched.
- **Parity:**
  - the atlas and pipeline specs in the runtime and the cold boot equal live bytes;
  - all 30 adaptive routes appear exactly once with the exact `pippi <command>` route;
  - each of the 74 surface-registry entries equals its live entry;
  - the mediation library and all 8 completion files equal live in the runtime and the cold boot;
  - the live capability root `e5f1b4f2…` equals both witnesses.
- **Frozen registries:** program has 24 rows and operator 14. All rows rebuild from bytes in POSIX order, with their roots. Both equal the witnesses, and both are unchanged from r027.
- **Acceptance cases:** R28-01..08 validate and rebuild exactly, each closes on a receipt test, and none authorizes effect. They bind the predecessor source `de36dc95…`, which is the convention since r021. Of the 112 selections in the tree, only the carried R20-01 item doesn't close.
- **Collaborator binding:** sound. `verify_passport` rebuilds the passport from the public key, the DKN stable nonce is fixed, and possession is honestly `False`.
- **Credentials:**
  - references refuse secret-bearing handles, and so do storage locators;
  - the local vault is scrypt (2^15) with AES-256-GCM, bound to the reference by AAD;
  - no CLI or tool calls the vault.
- **Native UI:** read statically, since it is Windows-only. The CONSTITUTION tab computes its rows from the live atlas and pipeline.
- **Skill:** the cold-boot `SKILL.md` is byte-identical to the runtime's.

## Findings

### R28-01 (LOW): identity roots on signed capsules and receipts are not bound to the signing key

- `change_capsule_signing_body` checks `author_identity_root` only as 64-hex, and the key only as a valid key. The publication and retrieval bodies do the same for `publisher_identity_root` and `retriever_identity_root`.
- So a valid signature proves possession of *some* key, while the identity it names can be anything. Your own test and the r028 court both sign with arbitrary roots (`R[7]`, `"8"*64`).
- The atlas doc says a capsule "binds … identity", and the test is named `…_binds_base_delta_identity_and_dkn`.
- The binding is already available: `verify_passport` derives `mosaic_id` from the key, and `build_collaborator_binding` uses it.

**Repair:** require the identity root to equal the identity derived from the signing key, or accept a passport and verify it; add a refusal case.

**Escalation:** I rated this LOW because capsules are `PROPOSAL_ONLY` and grant nothing. If you treat the doc's binding claim as an acceptance requirement, it is MED and r028 is HOLD_FOR_REPAIR.

### R28-02 (LOW): CCP readiness comes from a caller-asserted string

- `build_ccp_transition_binding` takes `current_use_status` from the caller and returns `PASS_READY` whenever that string is `ADMIT`.
- `current_use_decision_root` is format-checked only; no CCP decision is read or validated.
- The court's `CCP-BYPASS-REFUSED` case exercises only `DEFER`.
- It is mitigated by `effect_authorized: False`, but it records readiness nothing substantiates, and "CCP bypass" is on your attack list.

**Repair:** take and validate the decision record, and derive the status and root from it.

### R28-03 (LOW): the retrieval receipt claims a check it doesn't perform

- `artifact_verified_after_retrieval: True` is hard-coded, and the receipt is labelled `RETRIEVED_AND_HASH_VERIFIED`.
- But the function never sees the artifact bytes or the publication receipt, so it never checks that the retrieved hash equals the published one.
- The atlas doc says the two receipts "bind the same artifact hash".

**Repair:** check it, or label the field as the retriever's attestation.

### R28-04 (INFO): observations

- The pipeline lists SEALED as terminal, but PROPOSE_PUBLICATION leaves it.
- The credential vault's `.pending` temporary file is not created exclusively and follows symlinks. Its contents are encrypted, and nothing calls it.
- The vault accepts caller-supplied salt and nonce. The defaults are random, but a caller that reuses both repeats the key and the nonce.
- The cold boot ships `SKILL.md` without its `references/`, including the new `constitutional-atlas.md`. They are reachable only inside the embedded runtime. This pattern predates r028.
- `program/discovery-parity-r027` is carried byte-identical but not yet frozen.

### R28-05 (INFO): carried

- R20-01.
- R21-01's secondary items; `sim.add` shape is checked only at evaluation.
- r015–r017 and r025 were never reviewed.
- Two Windows-only tests; the wheel test needs setuptools; the receipt root depends on the Python patch version; the case probe writes transiently.

## Carried-finding dispositions

| Finding | Disposition |
|---|---|
| R24-01 | **CLOSED**: generator `--check` passes on both interpreters |
| R24-02 | **CLOSED**: portability source manifest rebuilds byte-identical and equals the source and witness roots |
| R26-02, R27-02 | **CLOSED**: all full-transport legs performed |
| R27-01 | historical; the r028 court reads `route` throughout |

## Court (read, not run)

The court has 19 cases: controls, plus the following.
- denominator shrink;
- co-projection and pipeline laundering;
- CCP DEFER;
- unknown context rule;
- credential-in-locator;
- signature swap;
- DKN nonce swap;
- CLI/ABI parity;
- cold-boot atlas and pipeline parity.

Statically, each refusal code it expects matches the source, so none of these cases is likely to fail for court reasons, as R27-01's did. Missing cases: a mismatched identity root (R28-01), an unsubstantiated ADMIT (R28-02), and a retrieval/publication hash mismatch (R28-03). A court is proven only by running it.

## Not performed

- **Tier 1:** builder-authored; not run, per your instruction.
- Windows and WSL legs (builder witnesses only); running the native UI.
- Negative or forgery exercises, per your instruction. R28-01..03 rest on the source and your own tests.

## State

r028 adds a navigable map of the constitution: rules, co-projections, pipeline states, and explanations of why context was chosen. It also adds the first collaboration primitives: identity binding, credential references, signed changes and storage receipts. The map is complete, reproducible and correctly non-authorizing, and the whole release now replays and rebuilds exactly from its own source. The collaboration primitives are honest about granting nothing. But three of them record identity, CCP readiness and retrieval verification that the code doesn't check.

## To clear

1. Repair R28-01..03, or accept them as LOW. Add court cases for each.
2. Have a reviewer independent of the build perform Tier 1 on runtime `3e8372c2…`, including the Windows and WSL legs.

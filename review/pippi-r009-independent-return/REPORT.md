# Independent review: UCM P/PPI r009 delivery

**Outcome: INCOMPLETE_REVIEW. The terminal verdict is withheld.**

- No finding at MED or above. REL7-01 is **closed** on my own evidence: publication planning now opens the exact SHA-pinned archive, verifies its closed manifest and all four META records, and derives every certification field; the caller-status parameters are gone.
- Custody, the archive partition, every META certification record, the qualification receipt's binding to the exact source and release, deterministic rebuild on both interpreters, the version-transition rules and the new work-selection rule all pass on positive evidence.
- The verdict is withheld only because the independent adversarial leg (Tier 1) has not been performed. The r008 operator evidence carried in this candidate is user-run, builder-authored, and against the r008 runtime, not r009; the r009 kit is unexecuted. Neither is an independent verdict.
- One LOW hardening finding (REL9-01) is batched.

This review was passive and positive-path: no adversarial testing, no re-sealed or forged artifacts, no Windows execution. It authorizes no publication, deployment, installation, application execution, network, identity, federation, DKN binding, A5, G0 or production authority. Standing remains INFORMATION_ONLY, authority effect NONE, real A5 false, G0 closed; the delivered subject stays DKN-unbound.

## Subject

| Item | Value |
|---|---|
| Handoff | `UCM-PIPPI-r009-INDEPENDENT-REVIEW-HANDOFF.zip` `c1a5208f…` (= `HANDOFF.sha256`), manifest root `5b97c7d7…`, 12 members |
| Release | root `0405a6ff…`, identity `f854df53…`, source manifest `2eab3248…` (995 rows), partition root `6e1b4683…`, custody denominator 54 |
| Runtime | `0d44e5ab…`, manifest root `f122f694…`, 715 payload + 4 META |
| SDK / review / lineage | `ed7d0764…` (940) / `c9612df2…` (54) / `199e136c…` (3) |
| Qualification receipt | root `cdda7ca8…`, 297 tests, builder Python 3.12.10 |
| Repair ledger | root `1f6821bd…`; r009 operator kit carried, unexecuted |

**Execution.** `python3 -I -B` in an empty environment on disposable copies; system CPython 3.12.3/3.13.16 for stdlib checks; the two previously authorized isolated virtualenvs for subject execution. Nothing installed; no network. Subject code executed only for `run_public_release_qualification.py`, `build_release.py`, `verify_runtime_tree.py`, read-only orientation, and documented-input exercises of three public functions (`build_publication_plan` against the real delivered archives, `build_project_identity_transition`, and the `pippi_work_units` builders).

## Tier 0: custody (items 1, 2, 4)

- Shipped `VERIFY.py` passes on 3.12 and 3.13; it differs from r007's only in the default filename. Inner ledger, work order and verifier equal the delivered copies.
- Release record and partition roots recompute; all four artifact pins and the `DETERMINISM.json` pins match; the Windows smoke record (seven phases PASS) names runtime root `f122f694` — builder evidence.
- Every archive: deflate only; manifest root recomputes and equals the release record; rows match; set closed. META: state root recomputes and its rows equal the non-META payload; THR H_s/H_c/H_j/H_m/H_r and `h_body` recompute; DKN binding `DECLARED_UNBOUND`, no key, `permission_granted: false`; self-certificate root recomputes, unsigned, READY, binds state/THR/DKN/identity/source; release record binds all four embedded roots and the certificate status. `verify_runtime_tree.py` checks the same.
- Source reconstitution: SDK + review + lineage payloads equal the 995-row manifest exactly; 54 custody rows = denominator; runtime is a byte-identical subset of the SDK.
- Identity root recomputes, equals the release record, binds the source manifest, `qualification_scope: EXACT_PUBLIC_SOURCE_AND_RELEASE`, `operator_tier1_case_count: 0`. The receipt binds source manifest, release root, identity, all four archive hashes and the runtime manifest root; 297 unique test ids, set root recomputes.
- Carried reviews: my r007 return (REPORT, FINDINGS, RECOMPUTE, evidence) is byte-identical to what I delivered, with a provenance record naming its hashes. The r008 operator return is attributed `USER_RUN_OPERATOR_KIT` (34/34, court root recomputes) against r008 runtime `32bef127…`, qualification `6048ea39…`; its disposition says `rel7_01: CLOSED_BY_OPERATOR_EVIDENCE`. Operator evidence does not close an independent finding; closure below is on my evidence.
- Delta vs r007 runtime: 20 files changed (P/PPI CLI, dashboard, integrations, reviews, work units, `mosaic_ui/win32.py`, installer, verifier, docs, skill), nothing added or removed.

## Tier 2: replay and rebuild (item 3)

| | 3.12.3 | 3.13.16 |
|---|---|---|
| Collected | 297 (ids = receipt) | 297 |
| Pass | 295 | 295 |
| Non-pass | `…native_ui_imports` (`mosaic_ui.win32 requires Windows`); `…wheel…` (same import inside the staged wheel) | same two |

Both non-passes are Windows-host dependencies, unchanged from r007; the builder's receipt is 0/0/0 on Windows 3.12.10. `build_release.py` from the same source: all five artifacts byte-identical to the delivered files on both interpreters. Runtime: tree verifier PASS; orientation commands exit 0 and are identical across interpreters except `doctor`'s Python version.

## Item 5: version transitions

Unchanged from r007 and re-read: revision bumps by default; version change refuses without a signed external approval bound to the exact operation root, policy root and time; revision transitions refuse unexpected approvals; no authority granted.

## Items 6–7: publication planning (REL7-01)

`build_publication_plan` now takes only `project, artifact_path, artifact_sha256, targets, dkn_public_namespace`; the CLI no longer has `--self-certificate-status` or root flags. `_verify_publication_artifact` reads the file, checks the supplied SHA-256, requires exactly one `MANIFEST.json`, verifies the manifest root and every member hash and size, requires all four META records and runs `verify_embedded_metadata` over the payload, then derives status and roots.

Exercised with the real delivered archives (`tier2/publication/publication-plan-check-r009.json`): runtime with exact pin and no DKN namespace → accepted, `CONTENT_ADDRESSED_NOT_DKN_SELF_CERTIFIED`, with derived certificate root, THR body root, DKN binding root and status **equal to the embedded META records**; same with a DKN namespace → refused `PIPPI_PUBLICATION_DKN_SELF_CERTIFICATION_REQUIRED` (unbound); wrong pin → `…ARTIFACT_PIN_MISMATCH`; missing file → `…ARTIFACT_MISSING`; lineage archive → accepted with its own derived roots. The DKN branch additionally requires `dkn_status == BOUND_EXTERNAL` and namespace equality, by source.

**REL7-01: CLOSED.** Item 7's remaining legs (unsigned, mismatched-namespace, malformed, wrong-pin beyond hash, and acceptance of a genuinely Ed25519-bound artifact) require constructing re-sealed or signed archives and were not performed; they belong to Tier 1.

## Items 8–10: work selection

Exercised through the public builders (`tier2/work-selection/work-selection-check.json`):
- Direct closure with case and check → accepted (`DIRECT_CASE_CLOSURE`, `implementation_effect_authorized: false`); missing check → refused; a block on direct work → refused.
- Shared infrastructure without a block → refused; a block on an UNMET case → refused (`…CASE_NOT_BLOCKED`); a block with no evidence roots → refused; a valid block on a BLOCKED case → accepted (`DEMONSTRATED_ACCEPTANCE_BLOCKER`); a block bound to a different case → refused (`…CASE_MISMATCH`); an edited acceptance case → refused (self-root).
- Outcomes: direct work closes the case only when observed = expected; infrastructure work never sets `acceptance_case_closed` (`PREREQUISITE_SATISFIED_FOLLOW_ON_DIRECT_STEP_REQUIRED`); case mismatch refuses. `pippi work-selection-verify` validates the same shape and journals it (source).

Items 8–10 are confirmed as implemented. As the builder's own note says, the rule makes the chosen case explicit and rooted; it cannot judge whether it is the right case, and the blocker evidence roots are checked for shape, not resolved.

## Findings

### REL9-01 (LOW, hardening, batched): infrastructure outcomes are judged against the acceptance case's result code, not the block's unblock criterion

`assess_work_unit_outcome` compares `observed_result_code` with the acceptance case's `expected_result_code` for both work classes. A shared-infrastructure step therefore reads `PREREQUISITE_SATISFIED` only when it reports the acceptance case's own code (e.g. `PASS`), and reads `PREREQUISITE_UNMET` when it reports the block's `unblock_criterion` (exercised: `X_PASS` → UNMET). The never-closes invariant holds either way; the prerequisite semantics are conflated with the case's. Repair: for `SHARED_INFRASTRUCTURE`, compare against the bound block's `unblock_criterion` (or a declared prerequisite result code) and record the block root in the outcome.

### REL9-02 (INFO): observations

- The ledger and r008 disposition describe REL7-01 as closed by operator evidence; closure is determined here on reviewer evidence.
- Receipt root remains Python-patch-version dependent; two of 297 tests remain Windows-only.
- `IPC.key` `chmod 0o600` remains ineffective on Windows ACLs.

## Carried-finding dispositions

| Finding | Disposition |
|---|---|
| REL7-01 (MED) | **CLOSED** (positive evidence against the delivered archives) |
| REL7-02 (INFO) | noted, unchanged |
| REL4-01, REL4-02 | closed (r007) |
| Ledger PIPPI-WORK-SELECTION-01/02 | consistent with evidence (items 8–10) |
| Ledger PIPPI-CERT-01, PIPPI-VERSION-01 | consistent with evidence |
| Ledger R008-OPERATOR-TIER1 | user-run builder court on r008; carried exactly; not independent, not r009 |
| Ledger PIPPI-WINDOWS-01 | builder evidence only |

## Not performed

- Tier 1 (item 11), including item 7's negative and bound-artifact legs; the r009 operator kit was not run.
- Windows legs (item 12).
- Content review of ecosystem return packages.

## State

Lineage position: r009 closes the last open MED from r007 and adds acceptance-bound work selection. Everything checkable from a POSIX host without adversarial construction now passes; what remains open is exclusively the independent attack leg and the Windows-host legs. Scaffold vs production: release custody and certification metadata are production-shaped and unbound by design; work selection is a journaled preflight rule, not an effect gate.

## To clear

1. Have a reviewer independent of the build perform Tier 1 on runtime `0d44e5ab…` (the r009 kit's cases plus item 7's negative legs), on a Windows host for items 7 and 12.
2. Batch REL9-01.

If that finds nothing at MED or above, a terminal recommendation becomes possible.

# Independent review: UCM P/PPI r007 delivery

**Verdict: HOLD_FOR_REPAIR.**

One MED finding, REL7-01: the DKN-addressed publication gate is declarative. `build_publication_plan` marks a plan `DKN_SELF_CERTIFIED` whenever the caller asserts `PASS_SELF_CERTIFIED` (a CLI flag); it never opens the artifact or verifies the embedded self-certificate, and it accepts the status with no certificate root at all. The ledger's repair claim PIPPI-PUBLICATION-01 ("refuses unless the embedded certificate is PASS_SELF_CERTIFIED") is not what the code does, so work-order item 6 cannot be confirmed. The plan is non-dispatching and marked human-authorization-required, which is why this is MED and not HIGH.

Both findings from my r004 review are closed: the delivered 290-test qualification receipt binds the exact public source, release root, identity and all four archive hashes (REL4-01), and the installer now refuses without an external runtime root, checked at four points (REL4-02). Custody, the archive partition, all META certification records, deterministic rebuild on both interpreters, and the revision/version-transition rules all pass.

This review was passive and positive-path. No adversarial testing and no Windows execution. It authorizes no publication, deployment, installation, application execution, network, identity, federation, DKN binding, A5, G0 or production authority. Standing remains INFORMATION_ONLY, authority effect NONE, real A5 false, G0 closed; the delivered subject stays DKN-unbound.

## Subject

| Item | Value |
|---|---|
| Delivery folder | `UCM-PIPPI-r007-DELIVERY-20261105` (six files, staged read-only) |
| Handoff | `UCM-PIPPI-r007-INDEPENDENT-REVIEW-HANDOFF.zip` `9f4c8bd0…` (= `HANDOFF.sha256`), manifest root `4deddd79…`, 12 members |
| Release record | root `12bf76d9…`, identity `ff631aa2…`, source manifest `fa2fbe88…` (980 rows), partition root `9442182d…`, custody denominator 42 |
| Runtime | `f22fa377…`, manifest root `3b44a9d6…`, 715 payload + 4 META members |
| SDK / review / lineage | `5a054001…` (937) / `d1b14a90…` (42) / `b9698715…` (3) |
| Qualification receipt | root `19499df5…`, 290 tests, builder Python 3.12.10 |
| Repair ledger | root `02cbb65e…`; operator kit `6a40765e…` (not run) |

**Execution.** `python3 -I -B` in an empty environment on disposable copies; system CPython 3.12.3/3.13.16 for stdlib checks; the two previously authorized isolated virtualenvs for subject execution. Nothing installed; no network; installer, service, dashboard and operator kit read, not run. Subject code executed only for the builder's `run_public_release_qualification.py`, `build_release.py`, `verify_runtime_tree.py`, read-only orientation commands, and two documented-input exercises of public functions (`build_publication_plan`, `build_project_identity_transition`). No forged signatures, certificates or approvals.

## Tier 0: custody (work-order items 1, 2, 4)

- Shipped `VERIFY.py` (identical inside and outside the handoff) passes on 3.12 and 3.13. The ledger and work order inside the handoff equal the delivered copies.
- Release record root and partition root recompute; all four artifact pins match; `DETERMINISM.json` pins equal the delivered bytes. Every archive: deflate only, manifest root recomputes and equals the release record, rows match, member set closed.
- **META records (item 4), every archive:** `STATE-MANIFEST` root recomputes, member count and rows equal the non-META payload; `THR-MANIFEST`: H_s/H_c/H_j/H_m/H_r each recompute from the mapped section and `h_body` recomputes over the whole record; `DKN-BINDING` root recomputes, status `DECLARED_UNBOUND`, no key, `permission_granted: false`; `SELF-CERTIFICATE` root recomputes, binds the state root, THR body root, DKN binding root, release identity root and source manifest root, carries no signature, status `READY_FOR_EXTERNAL_DKN_CERTIFICATION`; the release record's `state_root`, `thr_body_root`, `dkn_binding_root` and `self_certificate_root` equal the embedded values. `verify_runtime_tree.py` now checks these too.
- **Source reconstitution (item 2):** SDK + review + lineage payloads (excluding `MANIFEST.json`, `META/`, `release/`) equal the 980-row source manifest exactly; 42 rows under custody prefixes = denominator; runtime payload (715) is byte-identical to the SDK.
- **Identity and receipt (closes REL4-01):** `RELEASE-IDENTITY.json` root recomputes, equals the release record, binds the source manifest, and now carries `qualification_receipt_path` and `qualification_scope: EXACT_PUBLIC_SOURCE_AND_RELEASE`; the stale maturity fields are gone (the qualification tool lists them as `STALE_MATURITY_FIELDS`). The delivered receipt binds source manifest, release root, identity, runtime/SDK/review/lineage hashes and runtime manifest root; test-set root recomputes over 290 unique ids.
- The operator kit's `KIT-MANIFEST.json` pins the exact runtime hash and the exact qualification receipt, `tier1_executed: false`; `RUN.ps1` re-pins both before running. Not executed (item 7, no authorization sought; builder-authored court).
- Carried reviews: my UMT1 return and the unified register are byte-identical to the earlier dispatch; the r003 packaging review is carried; no record of my r004 review is carried.

## Tier 2: replay and rebuild (item 3)

`tools/run_public_release_qualification.py` from the reconstituted source, both interpreters: 290 tests collected, identities equal the delivered receipt, **288 pass**; the two non-passes are the same on both interpreters and are Windows-host dependencies: `test_pippi_release_packaging…native_ui_imports` (`mosaic_ui.win32 requires Windows`) and `test_installed_package…wheel` (the staged wheel's self-check also imports `mosaic_ui.win32`; confirmed on system Python with `setuptools`). The builder's receipt was produced on Windows 3.12.10 with 0/0/0.

`tools/build_release.py` from the same source: runtime, SDK, review, lineage and release index byte-identical to the delivered files on both interpreters.

Runtime: `verify_runtime_tree.py` PASS (root `3b44a9d6`, certificate status READY); `orient`, `capabilities`, `legacy-capabilities`, `profiles`, `doctor`, `smoke`, `abi-stability`, `environment-check` exit 0, identical across interpreters except `doctor`'s Python version.

## Items 5 and 6: version transitions and DKN publication

**Item 5 (confirmed).** `build_project_identity_transition`: r001→r002 with no approval is accepted as `ENGINEERING_REVISION`, `default_preference_applied: true`; a non-increasing revision refuses; a revision transition that supplies any approval refuses (`…APPROVAL_UNEXPECTED`); v0.1→v0.2 with no approval refuses (`…REQUIRES_EXPLICIT_USER_AUTHORIZATION`); with an empty approval object it refuses through `governance.verify_external_approval` (`REQUIRED_FIELD_MISSING: approval_id, approval_root, approver_identity_root, approver_public_key_hex`), which binds the approval to the exact operation root, a policy root and a freshness time. The transition record carries the BOUNDARY and grants nothing. `build_project` refuses any `public_version` other than the policy's.

**Item 6 (not confirmed).** See REL7-01.

## Windows legs (item 8)

Not executed here. The handoff's `PIPPI-WINDOWS-SMOKE.json` (root `1953bbce…`) records a builder-run install → state verify → authenticated loopback → stop → dashboard probe → uninstall against runtime root `3b44a9d6` on your machine; it is builder evidence. Static reading: the installer now takes a mandatory `-ExpectedRuntimeRoot` (64-hex validated) and compares it to the source, staged, existing and installed manifests; the `.cmd` wrapper refuses without one. Service and dashboard code are unchanged in posture from r004 (loopback, random port, per-data-root auth key, no outbound network in `src/`).

## Findings

### REL7-01 (MED): DKN-addressed publication plans accept a caller-asserted certificate status

- `pippi_integrations.build_publication_plan` refuses a `dkn_public_namespace` only when `self_certificate_status != "PASS_SELF_CERTIFIED"`. The status is a free parameter, exposed as `pippi review-publication-proposal --self-certificate-status`; `thr_body_root` and `self_certificate_root` are optional and unchecked against `artifact_sha256`. `pippi_reviews.propose_publication` passes them straight through.
- Exercised with documented inputs (`tier2/publication/publication-plan-check.json`): DKN namespace + READY status → refused; + no status → refused; + `PASS_SELF_CERTIFIED` with **no certificate roots** → accepted, `publication_identity_status: DKN_SELF_CERTIFIED`; + arbitrary roots → accepted.
- The real check exists elsewhere: `release_certification.build_embedded_metadata` only emits `PASS_SELF_CERTIFIED` after an Ed25519 verification over the signing body with the DKN public key, and refuses a signature on an unbound binding. The plan builder does not call it or `verify_embedded_metadata`.
- Effect: a publication plan can be labelled DKN-self-certified for an artifact that has no certificate. Nothing in this release dispatches a plan (`provider_dispatch_authorized: false`, `human_authorization_required: true`), so no effect occurs; but the plan is the record a publisher would consume, and the ledger states the gate as verified.
- Repair: have the plan builder read the artifact named by `artifact_sha256` (or take the four META records as inputs), run `verify_embedded_metadata`, derive `self_certificate_status`, `self_certificate_root` and `thr_body_root` from it, and drop the CLI flag; correct the ledger text.

### REL7-02 (INFO): observations

- The qualification receipt includes `python` (3.12.10), so its root is not reproducible on another patch version; all other receipt fields match my replay.
- Two of the 290 qualification tests are Windows-only, so the receipt's 0/0/0 cannot be reproduced on POSIX.
- `IPC.key` `chmod 0o600` remains ineffective on Windows ACLs (unchanged from r004).

## Carried-finding dispositions

| Finding | Disposition |
|---|---|
| REL4-01 (MED) no receipt / contradictory identity | **CLOSED** |
| REL4-02 (LOW) installer without external root | **CLOSED** |
| PPUB-03 | closed (r004) |
| PPUB-01 | closed with REL4-01 |
| PPUB-02 wheel closure | still host-limited here |
| Ledger PIPPI-CERT-01 | consistent with evidence (META records recompute; subject unbound) |
| Ledger PIPPI-VERSION-01 | consistent with evidence |
| Ledger PIPPI-PUBLICATION-01 | **not met as stated** → REL7-01 |
| Ledger PIPPI-WINDOWS-01 | builder evidence only |

## Not performed

- Tier 1 (item 7): not run; no authorization sought.
- Windows legs (item 8): installer, service, dashboard probe, uninstaller, `mosaic_ui.win32`.
- Content review of ecosystem return packages.
- Signature verification of a bound certificate (none exists; subject is unbound by design).

## State

Lineage position: r007 closes both r004 release-custody findings and adds a certification layer (state/THR/DKN/self-certificate) that recomputes end to end. Capability gained: a public release whose qualification receipt, identity and archives are mutually bound and rebuild deterministically; an externally pinned installer; refusal-by-default version policy. Scaffold vs production: the certification metadata is production-shaped but intentionally unbound; the publication plan is a preflight record whose certificate gate is declarative until REL7-01 is repaired.

## To clear

1. Repair REL7-01 and correct the ledger.
2. Independent Tier 1 on the exact runtime `f22fa377…`, including the Windows legs on a Windows host.

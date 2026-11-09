# Common P/PPI turn records

Use the ordinary `turn-prepare -> work -> turn-report -> turn-reconcile` path.
The common record enriches that same turn. Existing opening and report bytes
and roots remain intact, and existing journal history remains readable.

## Select detail from the work

Discover the current CLI and ABI registry before constructing a request.
`pippi turn-reporting-requirements` selects reporting information by the declared
scenario. The pure API is `reporting_requirements(scenario)`.

| Scenario | Requested activity kinds | Evidence references requested |
|---|---|---|
| CODING | CHANGE, CHECK | Optional |
| PACKAGING | CHECK | Required |
| RELEASE_PLANNING | CHECK | Required |
| PORTABILITY_CLAIM | CHECK | Required |
| REVIEW | CHECK | Required |
| RECOVERY | CHECK | Required |
| REMOTE_WORK | EXTERNAL_RECEIPT | Required |

Every scenario requests objectives, dispositions covering the complete opening
acceptance-case denominator, and declared coverage of `VISIBLE_OUTPUT` and
`JOURNAL_WRITE`. Other channels remain visible even when unknown. The policy
requests information at turn granularity; it does not require interposition
on every tool call.

## Author one enriched report

The ordinary `turn-report` JSON request may include an optional `turn_details`
object. Its exact keys are:

```json
{
  "claims": [],
  "evidence": [],
  "coverage": [],
  "objectives": [],
  "acceptance_dispositions": [],
  "native_turn_roots": []
}
```

Empty lists are permitted as a truthful incomplete report. The builder records
missing information instead of inventing it. Use these exact input row shapes:

To amend a committed report, submit a second complete report for the same
opening and set `supersedes_turn_bundle_root` to the exact earlier bundle.
Never rewrite or delete the earlier bundle. The hub accepts one linear
successor only. Continuation context uses only the active report for
missing-information prompts while history preserves both reports, their
journal sequences, and any exact CMBA assessment attachments. The public
`turn-report` response still returns `record` (the bundle), `report`, and
`turn_record`; r035 deliberately preserves that r034 response contract.

| Collection | Exact row keys |
|---|---|
| claims | `claim_id`, `activity_kind`, `statement`, `declared_basis`, `evidence_ids` |
| evidence | `evidence_id`, `subject_root`, `source_root`, `producer_id`, `receipt_root`, `declared_basis`, `description` |
| coverage | `channel`, `status`, `evidence_ids`, `limitations` |
| objectives | `objective_id`, `statement`, `acceptance_case_roots` |
| acceptance_dispositions | `acceptance_case_root`, `disposition`, `claim_ids`, `evidence_ids` |

Identifiers and statements are nonempty strings. Reference lists contain unique
strings; rooted references are full lowercase SHA-256 values. `source_root` and
`receipt_root` may be null. `evidence_ids` and `claim_ids` must refer to rows in
this record. Objective and disposition case roots must refer to the opening's
acceptance cases. `native_turn_roots` is a list of unique full roots.

The builder sorts rows and reference lists canonically and preserves exact
prose. Duplicate identifiers refuse. Rows cannot carry extra keys.

- `activity_kind`: `PROPOSAL`, `CHANGE`, `CHECK`, `TOOL_RESULT`,
  `EXTERNAL_RECEIPT`, or `OTHER`.
- `declared_basis`: `AGENT_REPORTED`, `HOST_CAPTURED`, `VERIFIER_DERIVED`,
  `EXTERNALLY_ATTESTED`, or `UNKNOWN`.
- Coverage `channel`: `MODEL_INPUT`, `DRAFT`, `VISIBLE_OUTPUT`, `TOOL_PROPOSAL`,
  `TOOL_DISPATCH`, `TOOL_RESULT`, or `JOURNAL_WRITE`.
- Coverage `status`: `UNKNOWN`, `PARTIAL`, `COMPLETE`, or `NOT_APPLICABLE`.
- Case `disposition`: `UNKNOWN`, `OPEN`, `REPORTED_MET`, `REPORTED_UNMET`, or
  `DEFERRED`.

The builder supplies an `UNKNOWN` row for every omitted channel and opening
acceptance case. It never shrinks the denominator. Context, rules, execution
context, project identity, and journal continuity come from the validated
opening. Summary, changed paths, artifact/evidence roots, unresolved items,
next action, and claim class come from the validated ordinary report.

## Preserve the evidence boundary

The record preserves the declared basis of a claim; it cannot verify that a
caller really captured or checked the activity. Claim and evidence rows receive
the derived `assurance: DECLARED_NOT_VERIFIED`, including rows labelled
`HOST_CAPTURED`, `VERIFIER_DERIVED`, or `EXTERNALLY_ATTESTED`.

The record checks structure, canonical roots, and links. Supplied producer IDs,
subject/source roots, receipts, and native turns remain references. They require
their own supported verifier before another system may treat them as verified
observations. `verified_channel_ids` stays empty and `enforced_host_verified`
stays false. A native-turn reference establishes no full interception claim.

`INFORMATION_COMPLETE` means the scenario's requested reporting fields were
supplied. `NEEDS_INFORMATION` lists explicit missing fields. Neither status
establishes truth, conformance, an acceptance closure, or a capability grant.
`REPORTED_MET` is a reported disposition; `acceptance_case_closed` remains false.
Effect permission remains governed by the Operational Gateway and G1/G2/G3.

`turn-prepare` checks continuation state and commits the opening under the same
hub lock. An exact retry is idempotent. A distinct concurrent opening cannot
bypass an unresolved predecessor close.

## Validate, reconcile, and observe

`pippi turn-record-build` exposes the pure common-record builder when a caller
already has an exact opening and report. It produces the same record used by
the optional `turn_details` path. Do not append the same turn twice through both
paths.

The pure module `ucm.pippi_turn_record` exposes:

```text
build_turn_record(*, opening, report, claims, evidence, coverage, objectives,
                  acceptance_dispositions, native_turn_roots)
validate_turn_record(value, *, opening, report)
project_turn_record(value, *, opening, report, view="HUMAN")
```

The root key is `turn_record_root`. Validation rebuilds the complete record
against the exact opening and report. For normal closure, `turn-reconcile`
accepts optional `turn_record`; `turn-record-reconcile` exposes the explicit
rich-record route. Use the current registry for their request envelopes.
`pippi turns` lists retained turns for a project. `turn-record-view` derives a
human or machine projection, with missing information and reference counts,
from validated records. The dashboard reads those same project records.
Projection text and chat summaries are not alternate evidence records.

## Optional CMBA binding and assessment

Use `pippi cmba-binding` to inspect the exact optional CMBA binding.
`cmba-turn-assess` validates the common record and evaluates its commitment
through the pinned CMBA generic profile. `cmba-turn-verify` checks an assessment
against the exact turn and CMBA binding. Preserve the record, binding,
evaluation, and assessment roots separately.

This profile checks binding and structure. It does not interpret all P/PPI
policy, prove reported activity, close a case, grant a permit, or establish
native-host enforcement. CMBA's native UCM r033 Pippi adapter has a separate
bounded contract; using the generic profile does not widen that adapter's tool
coverage. DKN authenticity, CHC correspondence, CCP admissibility, UCM authority,
and CMBA evaluation remain distinct claims.

Keep the public version at v0.1 unless the user explicitly authorizes a change;
use the engineering revision for an accepted successor. For adversarial review,
prepare the exact operator kit for the user with progress, sealing, cleanup,
and terminal pause. Do not execute that adversarial leg without separate user
authorization.

## Composite CMBA boundary

When a common turn must be related to the wider constitutional stack, discover
`pippi cmba-composite-profile`, build with `cmba-composite-build`, and verify
with `cmba-composite-verify`. Supply the exact CMBA assessment, DKN locality
binding, CHC/THR correspondence, complete CCP evaluation and, when applicable,
the operational journal plus independent issuer, jurisdiction and revocation
anchors. An effect-bound composite must bind the operation request to the exact
turn root and the G1 admissibility bundle to the exact CCP decision. Terminal
status requires re-derived G1, G2, G3 and proof roots.

Do not collapse these roots. CMBA structure, DKN locality, THR domains, CHC
correspondence, CCP admission and Gateway receipts remain separate claims. The
composite never grants authority and cannot replace Gateway dispatch custody.

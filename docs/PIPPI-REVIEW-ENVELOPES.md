# P/PPI review envelopes

P/PPI review envelopes separate four activities that are often collapsed:

1. **Construction** freezes the exact review subject, runner, inputs, and declared
   limitations into a deterministic closed archive.
2. **Review execution** replays the subject-owned runner in a disposable workspace.
   P/PPI records custody and process completion; it does not interpret the domain
   verdict and does not claim the workspace is an OS sandbox.
3. **Return import** accepts only a closed return archive bound to the exact envelope
   SHA-256 and a named reviewer identity root.
4. **Publication proposal** remains a separate plan requiring human authorization.

Remote or cross-jurisdiction review uses the AOK Courthouse as transport owner.
P/PPI authors the exact work order and imports the bound result; it does not create
a second remote correspondence architecture.

## Minimal envelope specification

```json
{
  "schema": "mosaic.ucm.pippi-review-envelope-spec.v0.1",
  "review_id": "release-review-r003",
  "review_class": "INDEPENDENT_RELEASE_REVIEW",
  "subject_role": "PIPPI_RELEASE_CANDIDATE",
  "declared_subject_root": null,
  "members": [
    {"source": "candidate.zip", "path": "subject/candidate.zip", "role": "SUBJECT"},
    {"source": "RUN-REVIEW.py", "path": "runner/RUN-REVIEW.py", "role": "REVIEW_RUNNER"}
  ],
  "runner": {
    "command": ["{PYTHON}", "runner/RUN-REVIEW.py", "--output-dir", "{OUTPUT_DIR}"],
    "required_paths": ["runner/RUN-REVIEW.py", "subject/candidate.zip"],
    "expected_outputs": ["REPORT.json"],
    "timeout_seconds": 3600
  },
  "limitations": ["NOT_AN_OS_SANDBOX"],
  "independent_review_required": true
}
```

Member paths must be sorted, unique, relative, and explicitly assigned a role.
`SUBJECT` members form a separate subject-manifest root. `VERIFY.py` is standard
library only and verifies custody without loading P/PPI or subject modules.

## CLI lifecycle

```text
pippi review-envelope-build PROJECT SPEC.json REVIEW.zip
pippi review-envelope-verify REVIEW.zip --expected-sha256 EXTERNAL_PIN
pippi review-run-local PROJECT REVIEW_ID LOCAL-EVIDENCE.zip
pippi review-dispatch-courthouse PROJECT REVIEW_ID aok:courthouse
pippi review-import-return PROJECT REVIEW_ID REVIEW-RETURN.zip
pippi review-compare PROJECT LEFT_REVIEW RIGHT_REVIEW
pippi review-publication-proposal PROJECT REVIEW_ID ARTIFACT.zip EXPECTED_ARTIFACT_SHA --target GITHUB
```

The native dashboard's **Reviews** workspace reports the exact subject and envelope,
courthouse request, returned outcome, and publication proposal. A displayed outcome
is explicitly a reviewer report, not P/PPI authority.

The publication proposal surface opens the exact local artifact, verifies its
external SHA-256, archive manifest, payload denominator, and all four embedded
META records, and derives the THR and self-certificate fields. Callers cannot
assert certificate status or roots. The local path is an input only and is not
embedded in the storage-agnostic plan.

The native workflow uses the same contracts as the CLI:

- return selection is an operating-system file dialog followed by exact archive,
  envelope, review-ID, contents, and return-root verification;
- substance disclosure re-reads the exact stored archives and does not copy findings
  into a second authority store;
- local replay is off the UI thread and reports `VERIFY`, `EXTRACT`, `RUN`, and `SEAL`
  as non-evidentiary progress alongside elapsed time and the evidence destination;
- publication input creates a held plan over an exact artifact SHA-256, bounded
  targets, and optional public DKN namespace. It never dispatches publication.

## Operator review kits

Repeated manual courts use a common P/PPI operator-kit contract rather than
reimplementing custody and launcher semantics for each subject. The subject
still owns its case runner. P/PPI fixes the exact runtime, qualification and
cold-boot pins; builder/operator authorship; unexecuted status; live progress;
evidence-before-status ordering; disposable extraction; cleanup; and final
interactive pause.

```text
pippi operator-kit-contract REQUEST.json
pippi operator-kit-verify CONTRACT.json
```

These commands compile and verify data only. They do not run the court. A
subject-specific packaging tool may place the resulting rooted contract in a
sealed kit and generate the platform launcher.

# Release and review

The v0.1 publication contains source code and stable contracts. Generated ZIPs remain outside Git:

```powershell
python tools/write_source_manifest.py
python tools/build_release.py --audit-source C:\path\to\frozen-c4
python tools/verify_release.py dist\UCM-v0.1-release.json --expected-release-root <externally-recorded-root>
```

The runtime includes every resource read by its advertised operations, including the UCL compiler-pass graph. It excludes tests, predecessor archives, and review evidence. The SDK adds tests, development tools, compatibility specifications, and the declared compatibility delta.

Every build emits three nonrecursive delivery archives: `UCM-v0.1-runtime.zip`
for installed operation, `UCM-v0.1-sdk.zip` for authoring and development, and
`UCM-v0.1-review.zip` for tests, tools, work orders, and review custody. Runtime
and SDK archives do not carry predecessor archives, ecosystem return packages,
or review evidence. Ecosystem session, successor, audit, and repair returns live
only in the review-custody archive. Without
`--audit-source`, the builder also emits `UCM-v0.1-lineage.zip`, explicitly
marked `METADATA_ONLY`, and a `PUBLIC_LINEAGE` release index reproducible from
the public repository. With a pinned c4 source it verifies every historical
input against `audit/C4-FROZEN-LINEAGE.json` and emits `UCM-v0.1-audit.zip`,
marked `COMPLETE_FROZEN_CUSTODY`, with a distinct `COMPLETE_AUDIT` release
index. Qualification builds both forms twice and separately binds their roots
plus the byte-identical runtime, SDK, and review artifacts shared by both.

Qualification verifies the live source manifest before and after testing, independently recomputes the frozen c4 source identity, checks its qualification and freeze pins, runs the public tests, builds twice, and verifies the release against an external root. Independent review should repeat those checks, exercise each public route from the staged runtime, and attack the cross-record bindings. This repository does not turn a recommendation into authority.

`release/UCM-v0.1-QUALIFICATION.json` is the frozen builder receipt for the current source. `release/UCM-v0.1-PUBLIC-RELEASE.json` records the clean-checkout public release index. Both are deliberately excluded from the SDK payload they describe, so recording them cannot change the release root. The source manifest excludes all release metadata and binds the executable public source independently.


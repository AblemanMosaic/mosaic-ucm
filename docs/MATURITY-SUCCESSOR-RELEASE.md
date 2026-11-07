# Unified maturity successor release

The successor preserves frozen UCM v0.1 and builds a new review subject. It does
not overwrite the public v0.1 release identity. Its exact identity is the freeze
receipt and qualification-source root.

## Artifact model

- `CANONICAL-SOFTWARE` is the parsimonious deployable core. It contains active
  runtime, contracts, policy packs, conformance vectors, examples, orientation,
  field diagnostics, and the exact unbound MosaiCOS M0 fixture. It omits tests,
  review evidence, and vendor test/tool material.
- `QUALIFICATION-SOURCE` is the larger source, test, builder, review-order, and
  custody closure used to reproduce the qualification. Generated `release/`
  receipts are derived afterward and excluded from this source to prevent stale
  or recursively self-bound candidate identity.
- AUTHORING, COMPATIBILITY, OPERATIONAL, and VERIFY_ONLY are small overlays bound to the same
  capability registry. They attenuate surfaces and grant no authority.
- The operator kit is a separate sealed archive. The builder never runs it.
- The independent-review handoff binds every artifact and the three-track work
  order without embedding prior transport archives in the deployable core.
- Exact later application audit returns remain in qualification custody rather
  than the deployable runtime. Their compact register, derived current state,
  and batch repair program ship as active planning records.
- Exact repair-successor returns follow the same split: raw bytes remain in
  qualification custody while the repair register and non-authorizing current
  state remain available to the operational profile.

## Build order

After targeted construction tests pass, run exactly one cache-free positive/static
qualification:

```powershell
python tools/run_maturity_qualification.py --output <empty-qualification-directory>
python tools/finalize_maturity_evolution_campaign.py --qualification-dir <qualification-directory> --output <empty-campaign-directory>
python tools/build_maturity_operator_kit.py --qualification-dir <qualification-directory> --output <empty-operator-directory>
python tools/build_maturity_release.py --qualification-dir <qualification-directory> --operator-dir <operator-directory> --campaign-dir <campaign-directory> --output <empty-release-directory>
```

The user then double-clicks `RUN-MATURITY-TIER1.cmd` in the operator directory.
The builder first seals `OPERATOR-RUNNER-IMPORT-CONTRACT.json`, a static binding
from every UCM/UCL operator-runner import to the exact frozen qualification
source. Subject code is not imported or executed during this check. A removed or
renamed API therefore blocks packaging instead of failing during the user run.
It verifies the exact kit, runs the consolidated court in a disposable workspace,
preserves sealed evidence, removes temporary files, and pauses. Independent review
uses the work order under `review/` and treats the operator result as engineering
evidence rather than a terminal independent verdict.

`UCM-SELF-RELEASE-CAMPAIGN.zip` is the dogfood record. It begins from the exact
source-controlled campaign, attaches the frozen qualification through the same
external-evidence envelope available to applications, dispositions the fixed
56-requirement register, and advances a copied journal. It is derived after
qualification so it cannot recursively change the source root it records.

After the operator returns the evidence, bind it to the exact frozen handoff with:

```powershell
python tools/build_maturity_operator_evidence_addendum.py `
  --operator-kit <exact-operator-kit.zip> `
  --operator-evidence <returned-evidence.zip> `
  --review-handoff <exact-review-handoff.zip> `
  --freeze-receipt <exact-freeze-receipt.json> `
  --expected-kit-sha256 <pinned-kit-sha256> `
  --expected-review-handoff-sha256 <pinned-handoff-sha256> `
  --output <new-operator-evidence-addendum.zip>
```

The importer verifies the kit, embedded qualification source, exact court runner,
subject hash, result root, case uniqueness, all-PASS status, freeze root and handoff
pin. It refuses evidence from an earlier candidate. The resulting addendum remains
operator-reproduced engineering evidence with independent review still pending.

## Claim boundary

All artifacts remain `INFORMATION_ONLY`, authority effect `NONE`, real A5 false,
and G0 closed. The ecosystem baseline does not contact applications. MosaiCOS M1
preparation binds no target, identity, network, execution, or acceptance authority.
The architecture pilot is bound to exact task materials and six isolated run kits but remains unexecuted.

# Common turn records and CMBA

P/PPI v0.1 r035 keeps the existing opening/report/reconciliation workflow and adds a richer common turn record. Agents can record purpose, exact supplied standards, reported activity, evidence references, coverage and acceptance dispositions. The user and agent inspect projections of that same record.

## The everyday workflow

1. Run `pippi turn-prepare REQUEST.json`. Its response includes the native opening, scenario-selected reporting requirements, and any prior turn requiring closure. Continuation checking and opening commit occur under one hub lock. Repeating the same opening is idempotent. Opening a different turn while an earlier one remains unclosed returns `PREVIOUS_TURN_CLOSE_REQUIRED` with its roots and instructions.
2. Perform the authorized work in the surrounding host. Per-tool interception is not required by this adaptive protocol.
3. Run `pippi turn-report REQUEST.json`. Keep the existing report fields and add optional `turn_details`: `objectives`, `claims`, `evidence`, `coverage`, `acceptance_dispositions`, and `native_turn_roots`. The response continues to include the exact legacy report plus the common record in one immutable bundle. This is the explicit r034-to-r035 response-compatibility decision. Missing details become explicit information requests rather than disappearing from coverage.

To amend a committed report, submit a new complete report for the same opening with `supersedes_turn_bundle_root` naming the exact prior bundle. Records remain immutable. A committed bundle can have at most one successor, and a successor cannot silently branch from an already superseded bundle. Continuation and dashboard projections show only the active report's information requests while retaining the full report chain, journal sequence and exact CMBA assessment attachments.
4. If CMBA is selected, run `pippi cmba-binding`, then `pippi cmba-turn-assess REQUEST.json` with the independently expected wheel SHA-256. Use `pippi cmba-turn-verify REQUEST.json` to recompute it, and `pippi turn-assessment-import REQUEST.json` to attach the validated assessment to the same project journal.
5. Run `pippi turn-reconcile REQUEST.json` with the existing fields and optional `turn_record`. Common reconciliation binds that exact richer record. Reconciliation records report custody; it does not close an acceptance case or establish that reported effects occurred.
6. Run `pippi turns PROJECT_ID`. The dashboard's Overview and Evidence views and the authenticated service's `turns` handler expose the same source records. No second journal is created.

`turn-record-build`, `turn-record-view`, `turn-record-reconcile`, and `turn-reporting-requirements` are pure construction/projection counterparts. Discover their exact payloads through `ucm capabilities`. The legacy ABI report builder remains available unchanged.

## What the record says

Every claim has an `activity_kind`, exact statement, declared basis and supporting evidence IDs. Available bases are `AGENT_REPORTED`, `HOST_CAPTURED`, `VERIFIER_DERIVED`, `EXTERNALLY_ATTESTED`, and `UNKNOWN`. Evidence references identify a subject root, optional source and receipt roots, producer ID and description.

These are declarations until their native verifier establishes more. The builder derives `assurance: DECLARED_NOT_VERIFIED` rather than accepting an assurance flag from the caller. Coverage is likewise declared. The record preserves all seven channel positions, fills omitted ones as `UNKNOWN`, and never establishes `ENFORCED_HOST` from a report. Native turn roots are explicit references, not proof that native turn validation was performed.

Every acceptance case named by the opening appears exactly once. Omitted dispositions become `UNKNOWN`. `REPORTED_MET` means the agent reports the criterion met; it is not an external acceptance decision. `INFORMATION_COMPLETE` means requested reporting information was supplied, not that its claims are true, verified, complete execution coverage, or authorized.

Requirements depend on scenario. Coding asks for changed-work and check statements; review, packaging, recovery and portability ask for check information; remote work asks for external receipt information. Missing information stays inspectable and is returned as context at the next opening. The original source-journal snapshot bound in the opening and observed hub custody are separate roots; recording a report advances the hub journal and must not be described as observing an external source journal.

## What CMBA adds now

The optional offline artifact is the exact supplied CMBA wheel, SHA-256 `fad457fd7a8fe4598da1280fbca90881cfc5e48a5dd410ab9c784ffcb19c70ca`. It is loaded only by the explicitly selected assessment surface after wheel, RECORD and member verification. No pip install, signing, network request or external effect is performed.

The adapter validates the native opening/report/common record, then uses the actual CMBA generic profile to bind their exact values, inspect the binding, evaluate structural consistency, and replay the evaluation. Native roots and CMBA roots remain distinct. The result `STRUCTURAL_BINDING_VALID` establishes commitment structure and exact-value correspondence. It does not authenticate the declared producer, verify reported tools or tests, recompute project policy, perform CCP current-use admission, grant a permit, or establish host interposition.

CMBA's existing r033 Pippi/CCP native adapters remain separately identified. The Pippi adapter's no-tool limit and r033 pins are preserved; loading the common record through the generic profile does not claim that adapter now supports r035 or tool-bearing turns. The upstream `0.1.0a7` collision remains disclosed in the optional pack contract.

## Historical records and local upgrades

Legacy opening, report and reconciliation constructors remain byte-compatible for the same inputs. Common records are new immutable objects linked to those old records. Existing journals are never normalized or rewritten. Historical common records retain their original project revision, and the history view distinguishes the current project root from prior roots.

The optional pack registry has a new revision/root. An old stored pack inventory must be explicitly migrated or recreated under its own governed update; the planner must not silently accept its old registry root. This candidate does not install itself or replace the user's active hub.

Run the positive demo with `python -B tools/run_common_turn_r035_demo.py --output OUT`. Its request can be frozen once and replayed using `--request REQUEST.json` to compare canonical outputs across Windows and WSL. Actual hub timestamps/custody are separate from the stable comparison outputs.

The source carries a scoped positive construction qualification. The existing full public suite and operator adversarial court are distinct legs; the builder does not claim they ran when it only ran positive construction. The operator kit is supplied unexecuted for the user. Standing remains INFORMATION_ONLY, authority effect NONE, real A5 false, G0 closed.

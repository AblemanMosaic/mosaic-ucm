# Incremental hotfix validation

This development lane sits between a bounded correction transaction and the one cache-free release qualification.

It computes a content-addressed affected closure, binds an exact test catalog, derives exact cache keys, emits proof-of-reuse records, and validates complete compilation/test denominators. Its strongest successful outcome is `INCREMENTAL_PASS`.

`INCREMENTAL_PASS` never means release-qualified. Every result carries `full_qualification_required_for_release: true`, `release_qualified: false`, standing `INFORMATION_ONLY`, and authority effect `NONE`.

## Pipeline

1. Create and seal a bounded correction candidate.
2. Write a plan request containing the candidate workspace, changed paths, test catalog, prior cache records, and all compiler/contract/policy/toolchain/environment/configuration roots.
3. Run `ucm hotfix-plan REQUEST.json PLAN.json --progress PROGRESS.jsonl`.
4. Run `ucm hotfix-execute PLAN.json WORKSPACE COMPILE.json TESTS.json --progress PROGRESS.jsonl`; this syntax-compiles every cache miss and runs exactly the selected unittest identities in a subprocess with bytecode writes disabled.
5. Record exact PASS results with result roots.
6. Run `ucm hotfix-validate PLAN.json COMPILE.json TESTS.json VALIDATION.json --progress PROGRESS.jsonl`.
7. Restore the candidate or promote its exact root into a clean cache-free qualification.

Changes to the capability registry, impact engine, correction machinery, UCL/Tessera implementation, builders, qualification runners, ABI table, or product profiles select `FULL_QUALIFICATION` for the development lane as well.

Progress JSONL is nonsemantic. Plans, proof-of-reuse records, compilation results, test results, and validation receipts are evidence subjects.

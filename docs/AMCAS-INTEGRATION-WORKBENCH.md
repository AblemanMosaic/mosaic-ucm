# UCM-AMCAS Integration Workbench

This successor composes the existing UCM systems into one application
integration pipeline. It does not replace UCL, Tessera, native proof,
realization contracts, project intelligence, qualification, custody, or the
portable bootstrap. It gives those systems one shared application contract,
event journal, operation protocol, report, and archive boundary.

## Conceptual interface

Humans and agents begin with five questions:

1. **What is the exact subject?** An immutable archive, immutable snapshot, or
   explicit working baseline with application source and manifest roots.
2. **What must be true?** CM1 requirements and immutable evidence subjects.
3. **What is preferred?** CM2 priorities among CM1-admissible choices.
4. **What may happen?** Capabilities, declared effects, budgets, rollback, and
   the external authority ceiling.
5. **What happened?** Journal events, three-gate receipts, tests, proofs,
   findings, and portable artifacts.

The AMCAS compiler turns these answers into an integration IR. Project
intelligence maps affected artifacts. The operation gateway records G1
Sentinel, G2 Witness, and G3 Diagnostic receipts for every effect or capability
grant. The report is derived from the journal. The journal archive can be
carried between sessions and verified independently of the mutable workspace.

## C2 workflow

1. Bind the exact subject with `integration-bind-subject`.
2. Record native semantic authority, effect executors, identity, jurisdiction,
   and RETAIN/ADAPT/REPLACE_AFTER_EQUIVALENCE dispositions.
3. Compile an AMCAS v0.2 contract whose integration boundary binds that record.
4. Run the native implementation and UCM projection in shadow mode. A
   correspondence court records equivalent decisions and divergences.
5. Record work under `UCM.INTEGRATION.G1`, `.G2`, and `.G3`.
6. Return one deterministic Stage I1 bundle. Its verifier recompiles the IR,
   recomputes the court, binds the journal, and checks every cross-record root.
7. For a portfolio, use a fixed roster and record intake, instruction, and
   Stage I1 import for every application.

The default is to retain native semantics and effects. Replacement requires
rooted equivalence evidence. UCM does not become the application's effect
executor merely because it observes or governs the work.

## Accessible entry points

```text
ucm integration-bind-subject SUBJECT BINDING-POLICY.json --out SUBJECT-BINDING.json
ucm integration-check-control-planes CONTROL-PLANE-DISPOSITION.json
ucm integration-correspondence-court CASES.json --out CORRESPONDENCE-COURT.json
ucm integration-verify-stage1 APPLICATION-STAGE-I1.zip
ucm portfolio-init PORTFOLIO.json WORKSPACE
ucm portfolio-status WORKSPACE
```

See `SUBJECT-BINDING.md`, `NATIVE-CORRESPONDENCE.md`, `STAGE-I1-RETURN.md`,
and `PORTFOLIO-INTEGRATION.md` in this directory.

## Boundaries

The included AMCAS standard is a source-bound candidate, not adopted law. THR
fields in workbench receipts are a preserved correspondence; a native UGK
receipt verifier is still required before any authority claim. This candidate
remains `INFORMATION_ONLY`, with authority effect `NONE`, real A5 false, and G0
closed.

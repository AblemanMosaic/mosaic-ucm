# P/PPI work-unit and no-replay protocol

P/PPI separates four facts that must never be collapsed:

- **execution holds** prevent the current work unit from running;
- **release blockers** allow internal construction but prevent release/admission;
- **qualification gaps** bound what the evidence can support;
- **user acceptance pending** is an explicit terminal human gate.

## Acceptance-bound work selection

Every implementation work unit names exactly one acceptance case: its subject
root, governing requirement root, verification surface, and expected result
code. Before implementation begins, run:

```text
pippi work-selection-verify WORK-SELECTION.json
```

A direct implementation step is valid only as `DIRECT_ACCEPTANCE_CLOSURE` and
must name the check it is intended to make pass. A `SHARED_INFRASTRUCTURE` step
is valid only when the acceptance case is already `BLOCKED` and an exact
infrastructure-block record binds non-empty diagnostic evidence, the missing
capability, and the condition that will remove the block. General usefulness,
future reuse, or architectural preference is not blocker evidence.

Completing shared infrastructure never closes the acceptance case. It yields
`PREREQUISITE_SATISFIED_FOLLOW_ON_DIRECT_STEP_REQUIRED`; a following direct
step must still execute the named acceptance case. This prevents infrastructure
work from silently replacing product closure and gives each loop an explicit
stop condition. The infrastructure outcome is judged against the exact bound
block's `unblock_criterion`, not the product case's expected result, and records
the `infrastructure_block_root` it satisfied.

Progress is a numerator and denominator. Proof level and operational maturity
are separate fields. A qualified slice may be complete while the larger program
is only halfway through its fixed work packages.

Before expensive work, a record-bundle preflight checks schemas, roots,
ordering, uniqueness, effect classes, and the expected prior head. After a
material effect, a no-replay capsule binds completed effect receipt roots,
remaining tail operations, retry budget, and journal/process heads. A prepared
bundle makes “result appended, process not advanced” an explicit recoverable
state rather than an ambiguous partial success.

The reusable lifecycle is dormant candidate → isolated install → connected →
updated → rollback proved → uninstalled → live admission pending. Each step
declares effect classes, forbidden targets, and the next required gate. A live
host mutation always remains separately authorized.


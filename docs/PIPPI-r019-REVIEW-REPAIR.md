# P/PPI r019 review repair

r019 is a bounded successor to qualified r018. It does not change the public
version and grants no authority.

## Operator court

The r018 operator run produced 27 passing cases and two failures. Both failures
were court defects: the runner omitted the required `opening` argument when it
validated a turn report, and the swap case changed `opening_root` instead of the
contract field `turn_opening_root`. The r019 court supplies the exact opening in
both paths and changes the bound field. The failed r018 evidence is preserved
under `review/pippi-r018-operator-return/`.

## Work-selection normalization

Exact r016-r018 preimages remain under
`historical/pippi-work-selection-preimages/`. The active records are reprojected
through the canonical `pippi_work_units` protocol. Every acceptance case now
binds its source denominator as its subject, names its verification surface and
expected result, and remains `UNMET` until observed evidence closes it. Every
selection states `implementation_effect_authorized: false`. The normalization
receipt maps every old root to its successor root.

## Pure inspection

`pack-inventory`, `install-plan`, `project-portability`, and the installer probe
read an in-memory default inventory when no inventory exists. They create no
file. `pack-record` is the explicit, head-checked inventory mutation surface.
Opening the native installer also remains a read-only planning action.

## Two delivery profiles

The slim canonical handoff excludes review custody and remains appropriate for
portable operation. A separate complete review transport carries all four
release archives, the qualification receipt, cold boot, and exact operator kit.
It is therefore large enough for replay and rebuild without bloating the cold
boot or active runtime.

All records remain `INFORMATION_ONLY`, with authority effect `NONE`, real A5
`false`, and G0 `CLOSED`.

# Constitutional Launcher and Behavioral Harness

The launcher is a shared CM1/CM2 contract for Mosaic application startup. CM1 binds the subject, executable, arguments, environment policy, external executor, readiness contract, allowed effects, G1/G2/G3 gates, and uncertainty policy. CM2 supplies the display name, splash asset, human phase labels, and readiness probe.

The host may present a splash or modal instead of a persistent console. UCM records launch observations and derives state; it does not spawn the program. `READY` requires readiness evidence. Terminal states require witness and diagnostic roots. An uncertain outcome must be reconciled without blind relaunch.

The Behavioral Harness describes controlled transitions for tests and hotfix validation. Time, randomness, filesystem, network, process, and environment controls are explicit. An external executor supplies pre-state, action, post-state, control, write, and executor-receipt roots. PASS requires every required control and only allowed writes.


# Authoring and evolution

UCM distinguishes **authoring**, **operating**, and **verification** profiles.
A profile attenuates surfaces; it never grants authority.

The authoring layer provides semantic linting, rooted policy packs, feature
negotiation, semantic diffs and complexity reporting. Schema validity alone is
insufficient: a contract may still be vacuous, self-certifying or impossible.

Feature descriptors declare the minimum and maximum semantics understood by a
contract. Unsupported levels refuse. Extensions use reverse-domain-style
namespaces and cannot alter the authority ceiling. A semantic migration receipt
records predecessor, successor, changed meaning and preserved invariants; it is
not ratification or adoption.

Initial policy packs live under `policy-packs/`. Importing a pack copies its
requirements into a successor AMCAS contract and recomputes the contract root.
The predecessor remains unchanged.
## Contract lifecycle

`ucm lifecycle-transition` records the forward-only sequence `NONE -> DRAFT ->
VALIDATED -> FROZEN -> SUPERSEDED`. Every transition after DRAFT requires rooted
evidence and binds its predecessor receipt. A lifecycle receipt records state; it
does not ratify, admit, deploy, or grant authority.

## Governed work packages

`ucm work-package` composes the existing Project Intelligence graph, Autonomous
Project Manager simulation plan, and an application-owned architecture fidelity
check. It is the stable authoring entry point for a proposed change. The returned
package includes the impact graph, review work order, simulation-only plan, and
architecture result under one root. It performs no project change or test execution.


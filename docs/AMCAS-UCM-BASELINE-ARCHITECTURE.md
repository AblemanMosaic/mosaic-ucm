# AMCAS–UCM Baseline Architecture

AMCAS is the normative application contract vocabulary. UCM is one executable realization of it. This program makes that relationship explicit and machine-checkable without claiming that the two are semantically identical.

## Common path

1. `ucm amcas-baseline` returns the versioned registry of twenty baseline elements.
2. `ucm amcas-coverage` accounts for every active UCM surface against exactly one element and lists declared gaps.
3. `ucm amcas-compile-baseline CONTRACT.json` compiles an exact AMCAS contract into UCM profile bindings, element requirements, policy-pack requirements, and explicit migration obligations.
4. `ucm amcas-semantic-diff BEFORE.json AFTER.json` classifies contract changes and calls out authority-adjacent changes.
5. `ucm amcas-parity` runs the fixed-denominator parity court over the element registry and current active surface registry.
6. Application sessions use the generated AUTHORING, OPERATIONAL, VERIFY_ONLY, or COMPATIBILITY profile. Native application authority remains with the application.

## Baseline elements

The baseline covers application identity, jurisdiction, capabilities and effects, three-gate workflow, artifact custody, journals, realization selection, evidence, correspondence courts, policy packs, semantic graphs, presentation and agent ABIs, test/repair control, lifecycle and migration, privacy, portable bootstrap, federation, native proof, and portfolio observability.

Each element is classified as `CORE_REQUIRED`, `PROFILE_REQUIRED`, or `APPLICATION_LOCAL`. Classifications determine which product profiles must carry the element. Application-local elements never enter the core implicitly.

## CM1 and CM2

CM1 remains the membership boundary: all applicable hard requirements must pass. CM2 ranks only configurations already admitted by CM1. UCM profile choice, semantic-gravity proposals, and consolidation hypotheses cannot override a CM1 refusal.

## Exact boundary

The registry, coverage registry, compiled program, semantic diff, parity result, profile sets, and observatory are all canonically rooted. The coverage registry accounts for active UCM surfaces; compatibility-only surfaces stay in the separate legacy registry. A missing or unknown element, system, or surface refuses.

## Current declared gaps

The parity court currently exposes partial presentation and privacy coverage, plus application-adapter requirements for correspondence courts and semantic graphs. These gaps are migration obligations. They do not block read-only planning, and they cannot be described as complete parity.

## Authority

All products remain `INFORMATION_ONLY`, authority effect `NONE`, real A5 false, and G0 closed. Compilation is not admission. A profile is not a permit. A parity pass is not proof of application behavior. Effectful execution still requires the external executor and the G1 → external effect → G2 → G3 receipt chain.

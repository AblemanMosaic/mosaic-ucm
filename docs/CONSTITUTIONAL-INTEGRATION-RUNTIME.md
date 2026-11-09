# Constitutional Integration Runtime

This is the stable bridge from an application's native control planes into UCM's receipt-mediated Operational Gateway. It gives humans and agents one path for preparing an operation, observing an external executor, diagnosing the terminal state, and exporting exact evidence. It remains `INFORMATION_ONLY`: UCM verifies authorization and receipts but does not select or invoke the executor.

## Common path

1. Build or import the exact application AMCAS plan and subject root.
2. Produce separately rooted native-plane reports for the applicable UGK, ESA, SRSA, COP, EVS, HeadlessRunner, test-control, and repair-control protocols.
3. Validate reports with `ucm integration-validate-adapter`.
4. Build an application capsule that names the plan, policies, active surfaces, and native reports.
5. Mint the operation permit with `request_root` equal to that exact `capsule_root`; supply the externally pinned integration-policy root to the runtime.
6. Ask `ConstitutionalIntegrationRuntime.prepare` to evaluate G1 and prepare the Operational Gateway.
7. Give the returned dispatch authorization to the externally selected executor.
8. Record the executor's signed dispatch and terminal receipts. The runtime derives G2 and G3 explanations over the gateway's authoritative state.
9. Export the gateway archive and read the ecosystem observatory. The progress JSONL and compact live summary are never evidence.

## Gate meanings

- **G1 Sentinel:** validates the signed permit, revocation generation, jurisdiction, requested effect set, budget, rollback root, idempotency key, required native-plane reports, and separate THR commitments before dispatch. The permit subject is the exact application capsule, and the capsule binds the externally pinned integration policy and native-plane result roots.
- **G2 Witness:** binds what the pinned external executor reports it actually did. It never infers effects from intent or progress.
- **G3 Diagnostic:** classifies the witnessed terminal state and binds the next safe action. An uncertain operation must be reconciled; it must not be redispatched. G2 and G3 reuse the exact native-plane result set bound at G1; actual effects come only from the signed external receipts.

Each semantic-gravity explanation keeps `state_root`, `admissibility_root`, `meaning_root`, `locality_root`, and `receipt_policy_root` distinct. A model may narrate these records, but its prose is not a decision input.

## Native control-plane boundary

Adapters preserve protocol identity. In particular, `EVS_EVENT_EVIDENCE_STREAM` and `EVS_EVIDENCE_VERIFICATION_SUBSYSTEM` are different protocols and cannot be merged into bare `EVS`. Adapter dispositions are `RETAIN`, `ADAPT`, `REPLACE_AFTER_EQUIVALENCE`, or `NOT_APPLICABLE`. Replacement is never implied by successful adaptation.

## Repair and test control

`build_control_plan` freezes finding IDs, impacted surfaces, test identities, selected lanes, and a fixed denominator. `build_control_result` requires one result for every test and one disposition for every finding. Live progress is best-effort and excluded from every root.

## Public entry points

- Python: `ConstitutionalIntegrationRuntime`, `build_adapter_result`, `build_semantic_gravity`, `build_control_plan`, `build_application_capsule`, `build_observatory`.
- CLI: `integration-validate-adapter`, `integration-validate-capsule`, `integration-validate-control-plan`, `integration-observatory`.
- Portable SDK: extract `sdk/`, verify `SDK-SOURCE-MANIFEST.json`, and use `sdk/src` as the Python source root. The kit carries the complete UCM/UCL source tree and package metadata.
- Operator review: double-click the sealed `.cmd` in the delivered operator kit. It extracts to a disposable directory, prints case progress, seals evidence, removes temporary files, and pauses. The builder does not run those adversarial cases.

The Memory Vault pilot is a deterministic read-only custody example. Its identities and jurisdiction are fixtures, no network is used, and it grants no real capability.
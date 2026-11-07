# Legacy capability surfaces

These predecessor routes remain available only for exact migration and historical replay. They are excluded from default discovery and require the explicit `COMPATIBILITY` profile.

| Legacy surface | Current surface | Historical route |
| --- | --- | --- |
| `DERIVE_STAGE_I4_ELIGIBILITY` | `BUILD_OPERATIONAL_CONTRACT` | `ucm stage4-derive-eligibility` |
| `VALIDATE_STAGE_I4_RUN_CONTRACT` | `BUILD_OPERATIONAL_CONTRACT` | `ucm stage4-validate-run-contract` |
| `VALIDATE_STAGE_I4_OBSERVATION` | `RECORD_OPERATIONAL_TERMINAL` | `ucm stage4-validate-observation` |
| `VALIDATE_NATIVE_HEADLESS_RUNNER_BINDING` | `BUILD_OPERATIONAL_CONTRACT` | `ucm.invoke` |
| `DERIVE_TRUSTED_STAGE_I4_ELIGIBILITY` | `BUILD_OPERATIONAL_CONTRACT` | `ucm stage4-c3-derive-eligibility` |
| `BUILD_STAGE_I4_EXACT_RUN_CONTRACT` | `BUILD_OPERATIONAL_CONTRACT` | `ucm stage4-c3-build-run-contract` |
| `BUILD_STAGE_I4_TERMINAL_REFUSAL` | `CANCEL_OPERATIONAL_GATEWAY` | `ucm stage4-c3-build-terminal-refusal` |
| `BUILD_NATIVE_HEADLESS_RUNNER_PREFLIGHT` | `PREPARE_OPERATIONAL_GATEWAY` | `ucm native-runner-preflight` |
| `VALIDATE_NATIVE_HEADLESS_RUNNER_RECEIPT` | `RECORD_OPERATIONAL_TERMINAL` | `ucm native-runner-validate-receipt` |
| `DERIVE_STAGE_I4_OPERATION_STATE` | `INSPECT_OPERATIONAL_STATE` | `ucm stage4-c3-derive-operation-state` |
| `VALIDATE_STAGE_I4_OPERATION_STATE` | `INSPECT_OPERATIONAL_STATE` | `ucm stage4-c3-validate-operation-state` |
| `BUILD_STAGE_I4_ANCHORED_RUN_CONTRACT` | `BUILD_OPERATIONAL_CONTRACT` | `ucm.invoke` |
| `BUILD_STAGE_I4_AUTHORITY_SAFE_PREFLIGHT` | `PREPARE_OPERATIONAL_GATEWAY` | `ucm.invoke` |
| `BUILD_STAGE_I4_RECEIPTED_REFUSAL` | `CANCEL_OPERATIONAL_GATEWAY` | `ucm.invoke` |
| `DERIVE_STAGE_I4_RECEIPT_STATE` | `INSPECT_OPERATIONAL_STATE` | `ucm.invoke` |
| `VALIDATE_STAGE_I4_RECEIPT_STATE` | `INSPECT_OPERATIONAL_STATE` | `ucm.invoke` |

Calling a legacy surface through the default AUTHORING, VERIFY_ONLY, or OPERATIONAL profile returns the typed refusal `UCM_LEGACY_SURFACE_REQUIRES_COMPATIBILITY_PROFILE` with the current replacement surface.

Registry root: `ff66212ba5557ef460d0b69f942579f0eb1ec249e9e1ded8b65c51fd7a42b6a7`

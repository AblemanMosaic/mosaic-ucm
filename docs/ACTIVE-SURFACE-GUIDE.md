# Active surface guide

Each entry supplies the fixed secondary documentation layer. Exact schemas and roots remain authoritative.

## `ORIENT`

**When to call.** Use this agent workbench surface when the request matches `mosaic.ucm.empty.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.empty.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"ORIENT","payload":{},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `DISCOVER_CAPABILITIES`

**When to call.** Use this agent workbench surface when the request matches `mosaic.ucm.empty.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.empty.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"DISCOVER_CAPABILITIES","payload":{},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `DISCOVER_LEGACY_CAPABILITIES`

**When to call.** Use this agent workbench surface when the request matches `mosaic.ucm.empty.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.empty.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"DISCOVER_LEGACY_CAPABILITIES","payload":{},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `DISCOVER_PRODUCT_PROFILES`

**When to call.** Use this agent workbench surface when the request matches `mosaic.ucm.empty.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.empty.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"DISCOVER_PRODUCT_PROFILES","payload":{},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `NEGOTIATE_FEATURE_LEVEL`

**When to call.** Use this constitutional core surface when the request matches `mosaic.ucm.feature-descriptor.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.feature-descriptor.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"NEGOTIATE_FEATURE_LEVEL","payload":{"descriptor":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_CONTRACT_LIFECYCLE_RECEIPT`

**When to call.** Use this constitutional core surface when the request matches `mosaic.ucm.contract-lifecycle-transition-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.contract-lifecycle-transition-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_CONTRACT_LIFECYCLE_RECEIPT","payload":{"contract_root":"…","from_state":"…","to_state":"…","predecessor_receipt_root":"…","evidence_roots":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `LINT_REALIZATION_CONTRACT`

**When to call.** Use this realization space surface when the request matches `mosaic.realization-space-contract.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.realization-space-contract.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"LINT_REALIZATION_CONTRACT","payload":{"contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `LINT_AMCAS_CONTRACT`

**When to call.** Use this amcas integration surface when the request matches `mosaic.amcas.integration-contract.v0.2` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.amcas.integration-contract.v0.2` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"LINT_AMCAS_CONTRACT","payload":{"contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `DIFF_SEMANTIC_CONTRACTS`

**When to call.** Use this constitutional core surface when the request matches `mosaic.ucm.semantic-contract-diff-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.semantic-contract-diff-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"DIFF_SEMANTIC_CONTRACTS","payload":{"before":"…","after":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `DIFF_CONTRACT_DOMAINS`

**When to call.** Use this constitutional core surface when the request matches `mosaic.ucm.domain-contract-diff-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.domain-contract-diff-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"DIFF_CONTRACT_DOMAINS","payload":{"before":"…","after":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `INITIALIZE_REALIZATION_CONTRACT`

**When to call.** Use this realization space surface when the request matches `mosaic.ucm.realization-contract-init-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.realization-contract-init-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"INITIALIZE_REALIZATION_CONTRACT","payload":{"contract_id":"…","subject_id":"…","subject_root":"…","description":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `COMPILE_CONTRACT_AUTHORING_PROFILE`

**When to call.** Use this realization space surface when the request matches `mosaic.ucm.authoring-profile-source.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.authoring-profile-source.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"COMPILE_CONTRACT_AUTHORING_PROFILE","payload":{"source":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `INITIALIZE_AMCAS_CONTRACT`

**When to call.** Use this amcas integration surface when the request matches `mosaic.ucm.amcas-contract-init-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.amcas-contract-init-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"INITIALIZE_AMCAS_CONTRACT","payload":{"integration_id":"…","application_id":"…","application_name":"…","subject_root":"…","manifest_root":"…","realization_contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `DOCTOR_CONTRACT`

**When to call.** Use this agent workbench surface when the request matches `mosaic.ucm.contract-doctor-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.contract-doctor-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"DOCTOR_CONTRACT","payload":{"kind":"…","contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `CLASSIFY_CONTRACT_COMPATIBILITY`

**When to call.** Use this constitutional core surface when the request matches `mosaic.ucm.contract-compatibility-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.contract-compatibility-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"CLASSIFY_CONTRACT_COMPATIBILITY","payload":{"predecessor":"…","successor":"…","known_roots":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `EXPLAIN_REALIZATION_SELECTION`

**When to call.** Use this realization space surface when the request matches `mosaic.ucm.realization-selection-explanation-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.realization-selection-explanation-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"EXPLAIN_REALIZATION_SELECTION","payload":{"contract":"…","candidates":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `DIFF_REALIZATION_CONFIGURATIONS`

**When to call.** Use this realization space surface when the request matches `mosaic.ucm.realization-configuration-diff-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.realization-configuration-diff-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"DIFF_REALIZATION_CONFIGURATIONS","payload":{"contract":"…","left":"…","right":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `INSPECT_ABI_STABILITY`

**When to call.** Use this constitutional core surface when the request matches `mosaic.ucm.empty.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.empty.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"INSPECT_ABI_STABILITY","payload":{},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `INSPECT_ENVIRONMENT_POLICY`

**When to call.** Use this agent workbench surface when the request matches `mosaic.ucm.environment-policy-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.environment-policy-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"INSPECT_ENVIRONMENT_POLICY","payload":{"environment":"…","strict":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `GENERATE_SHELL_COMPLETION`

**When to call.** Use this agent workbench surface when the request matches `mosaic.ucm.shell-completion-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.shell-completion-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"GENERATE_SHELL_COMPLETION","payload":{"shell":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `PRETTY_PRINT_RECORD`

**When to call.** Use this agent workbench surface when the request matches `mosaic.ucm.pretty-record-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pretty-record-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"PRETTY_PRINT_RECORD","payload":{"record":"…","title":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_EXTERNAL_TOOL_EVIDENCE`

**When to call.** Use this qualification control surface when the request matches `mosaic.ucm.external-tool-evidence-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.external-tool-evidence-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_EXTERNAL_TOOL_EVIDENCE","payload":{"tool":"…","subject_root":"…","invocation_root":"…","output_root":"…","environment_root":"…","verifier_root":"…","policy_root":"…","issuer_root":"…","exit_code":"…","counts":"…","issued_at":"…","not_after":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VERIFY_EXTERNAL_TOOL_EVIDENCE`

**When to call.** Use this qualification control surface when the request matches `mosaic.ucm.external-tool-evidence-subject.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.external-tool-evidence-subject.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VERIFY_EXTERNAL_TOOL_EVIDENCE","payload":{"evidence_subject":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VERIFY_EXTERNAL_APPROVAL`

**When to call.** Use this operational gateway surface when the request matches `mosaic.ucm.external-approval-verification-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.external-approval-verification-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VERIFY_EXTERNAL_APPROVAL","payload":{"approval":"…","expected_operation_root":"…","expected_policy_root":"…","now":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VALIDATE_EXTERNAL_EVIDENCE`

**When to call.** Use this qualification control surface when the request matches `mosaic.ucm.external-evidence-validation-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.external-evidence-validation-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VALIDATE_EXTERNAL_EVIDENCE","payload":{"evidence":"…","expected_subject_root":"…","expected_policy_root":"…","now":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `SUMMARIZE_JOURNAL`

**When to call.** Use this integration journal surface when the request matches `mosaic.ucm.journal-events.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.journal-events.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"SUMMARIZE_JOURNAL","payload":{"events":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `DIFF_JOURNALS`

**When to call.** Use this integration journal surface when the request matches `mosaic.ucm.journal-diff-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.journal-diff-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"DIFF_JOURNALS","payload":{"before":"…","after":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_JOURNAL_INCLUSION_PROOF`

**When to call.** Use this integration journal surface when the request matches `mosaic.ucm.journal-inclusion-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.journal-inclusion-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_JOURNAL_INCLUSION_PROOF","payload":{"events":"…","event_root":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VERIFY_JOURNAL_INCLUSION_PROOF`

**When to call.** Use this integration journal surface when the request matches `mosaic.ucm.journal-inclusion-proof.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.journal-inclusion-proof.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VERIFY_JOURNAL_INCLUSION_PROOF","payload":{"proof":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `RUN_FIELD_SMOKE`

**When to call.** Use this qualification control surface when the request matches `mosaic.ucm.empty.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.empty.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"RUN_FIELD_SMOKE","payload":{},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_ARCHITECTURE_STUDY_ROSTER`

**When to call.** Use this qualification control surface when the request matches `mosaic.ucm.architecture-study.v0.2` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.architecture-study.v0.2` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_ARCHITECTURE_STUDY_ROSTER","payload":{"protocol":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VALIDATE_ARCHITECTURE_STUDY_RESULT`

**When to call.** Use this qualification control surface when the request matches `mosaic.ucm.architecture-study-result-validation-request.v0.2` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.architecture-study-result-validation-request.v0.2` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VALIDATE_ARCHITECTURE_STUDY_RESULT","payload":{"protocol":"…","result":"…","context_registration":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `AGGREGATE_ARCHITECTURE_STUDY`

**When to call.** Use this qualification control surface when the request matches `mosaic.ucm.architecture-study-aggregate-request.v0.2` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.architecture-study-aggregate-request.v0.2` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"AGGREGATE_ARCHITECTURE_STUDY","payload":{"protocol":"…","results":"…","context_registration":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VALIDATE_ARCHITECTURE_CONTRACT`

**When to call.** Use this amcas integration surface when the request matches `mosaic.ucm.architecture-fidelity-contract.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.architecture-fidelity-contract.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VALIDATE_ARCHITECTURE_CONTRACT","payload":{"contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `CHECK_ARCHITECTURE_CHANGE`

**When to call.** Use this amcas integration surface when the request matches `mosaic.ucm.architecture-change-check-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.architecture-change-check-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"CHECK_ARCHITECTURE_CHANGE","payload":{"contract":"…","candidate":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VALIDATE_REALIZATION_CONTRACT`

**When to call.** Use this realization space surface when the request matches `mosaic.realization-contract-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.realization-contract-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VALIDATE_REALIZATION_CONTRACT","payload":{"contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `CHECK_REALIZATION`

**When to call.** Use this realization space surface when the request matches `mosaic.realization-check-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.realization-check-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"CHECK_REALIZATION","payload":{"contract":"…","configuration":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `SELECT_REALIZATION`

**When to call.** Use this realization space surface when the request matches `mosaic.realization-selection-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.realization-selection-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"SELECT_REALIZATION","payload":{"contract":"…","candidates":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `PROJECT_TO_UCL_TESSERA`

**When to call.** Use this tessera compilation surface when the request matches `mosaic.realization-projection-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.realization-projection-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"PROJECT_TO_UCL_TESSERA","payload":{"contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VERIFY_NATIVE_PROOF`

**When to call.** Use this native proof surface when the request matches `mosaic.native-proof-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.native-proof-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VERIFY_NATIVE_PROOF","payload":{"contract":"…","proof_bundle":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `PROJECT_DASHBOARD`

**When to call.** Use this project intelligence surface when the request matches `mosaic.project-dashboard-request.v0.1` and `READ_ONLY` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.project-dashboard-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"PROJECT_DASHBOARD","payload":{"project":"…","workspace":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `PREPARE_AUTONOMOUS_PLAN`

**When to call.** Use this autonomous project manager surface when the request matches `mosaic.autonomous-plan-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.autonomous-plan-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"PREPARE_AUTONOMOUS_PLAN","payload":{"changed_ids":"…","changed_paths":"…","objective":"…","project":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `PREPARE_GOVERNED_WORK_PACKAGE`

**When to call.** Use this agent workbench surface when the request matches `mosaic.ucm.governed-work-package-request.v0.1` and `READ_ONLY` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.governed-work-package-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"PREPARE_GOVERNED_WORK_PACKAGE","payload":{"architecture_candidate":"…","architecture_contract":"…","changed_ids":"…","changed_paths":"…","objective":"…","project":"…","workspace":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `PREPARE_MOSAICOS_M1`

**When to call.** Use this portable bootstrap surface when the request matches `mosaic.ucm.mosaicos-m1-preparation-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.mosaicos-m1-preparation-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"PREPARE_MOSAICOS_M1","payload":{"expected_archive_sha256":"…","m0_archive_base64":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VERIFY_MOSAICOS_M1_PREPARATION`

**When to call.** Use this portable bootstrap surface when the request matches `mosaic.ucm.mosaicos-m1-verification-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.mosaicos-m1-verification-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VERIFY_MOSAICOS_M1_PREPARATION","payload":{"expected_root":"…","preparation":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `EXPLAIN_CLAIM`

**When to call.** Use this constitutional core surface when the request matches `mosaic.claim-explanation-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.claim-explanation-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"EXPLAIN_CLAIM","payload":{"accepted_contract_roots":"…","assertions":"…","edges":"…","evidence_contracts":"…","proof_roots":"…","subject_root":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `TRACE_PRESERVATION`

**When to call.** Use this realization space surface when the request matches `mosaic.realization-preservation-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.realization-preservation-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"TRACE_PRESERVATION","payload":{"after":"…","before":"…","contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_PORTABLE_PROFILE`

**When to call.** Use this portable bootstrap surface when the request matches `mosaic.portable-profile-stage-contract.v0.1` and `LOCAL_ARTIFACT_PREPARATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.portable-profile-stage-contract.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_PORTABLE_PROFILE","payload":{"stage_contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `MANAGE_BOUNDED_CORRECTION`

**When to call.** Use this custody federation surface when the request matches `mosaic.ucm.correction-transaction-command.v0.1` and `LOCAL_ARTIFACT_PREPARATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.correction-transaction-command.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"MANAGE_BOUNDED_CORRECTION","payload":{"command":"…","transaction_dir":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `PLAN_INCREMENTAL_HOTFIX`

**When to call.** Use this qualification control surface when the request matches `mosaic.ucm.incremental-hotfix-plan-request.v0.1` and `READ_ONLY` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.incremental-hotfix-plan-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"PLAN_INCREMENTAL_HOTFIX","payload":{"transaction_dir":"…","test_catalog":"…","cache_records":"…","compiler_root":"…","contract_root":"…","policy_pack_roots":"…","toolchain_root":"…","environment_root":"…","configuration_root":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VALIDATE_INCREMENTAL_HOTFIX`

**When to call.** Use this qualification control surface when the request matches `mosaic.ucm.incremental-hotfix-validation-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.incremental-hotfix-validation-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VALIDATE_INCREMENTAL_HOTFIX","payload":{"plan":"…","compilation_results":"…","test_results":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `EXECUTE_INCREMENTAL_HOTFIX`

**When to call.** Use this court execution surface when the request matches `mosaic.ucm.incremental-hotfix-execution-request.v0.1` and `LOCAL_ARTIFACT_PREPARATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.incremental-hotfix-execution-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"EXECUTE_INCREMENTAL_HOTFIX","payload":{"plan":"…","workspace":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `DISCOVER_AMCAS_BASELINE`

**When to call.** Use this amcas integration surface when the request matches `mosaic.ucm.empty.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.empty.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"DISCOVER_AMCAS_BASELINE","payload":{},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `INSPECT_AMCAS_UCM_COVERAGE`

**When to call.** Use this amcas integration surface when the request matches `mosaic.ucm.empty.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.empty.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"INSPECT_AMCAS_UCM_COVERAGE","payload":{},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `COMPILE_AMCAS_BASELINE`

**When to call.** Use this amcas integration surface when the request matches `mosaic.amcas.integration-contract.v0.2` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.amcas.integration-contract.v0.2` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"COMPILE_AMCAS_BASELINE","payload":{"contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `DIFF_AMCAS_BASELINES`

**When to call.** Use this amcas integration surface when the request matches `mosaic.ucm.amcas-semantic-diff-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.amcas-semantic-diff-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"DIFF_AMCAS_BASELINES","payload":{"old_contract":"…","new_contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `CHECK_AMCAS_UCM_PARITY`

**When to call.** Use this amcas integration surface when the request matches `mosaic.ucm.empty.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.empty.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"CHECK_AMCAS_UCM_PARITY","payload":{},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `INSPECT_AMCAS_PORTFOLIO`

**When to call.** Use this amcas integration surface when the request matches `mosaic.ucm.amcas-portfolio-observatory-request.v0.1` and `READ_ONLY` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.amcas-portfolio-observatory-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"INSPECT_AMCAS_PORTFOLIO","payload":{"profile_sets":"…","parity_result":"…","consolidation_roots":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VALIDATE_AMCAS`

**When to call.** Use this amcas integration surface when the request matches `mosaic.amcas-validation-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.amcas-validation-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VALIDATE_AMCAS","payload":{"contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `COMPILE_AMCAS`

**When to call.** Use this amcas integration surface when the request matches `mosaic.amcas-compilation-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.amcas-compilation-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"COMPILE_AMCAS","payload":{"contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `INSPECT_MOSAIC_ID`

**When to call.** Use this identity session surface when the request matches `mosaic.identity-inspection-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.identity-inspection-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"INSPECT_MOSAIC_ID","payload":{"passport":"…","expected_mosaic_id":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `MANAGE_INTEGRATION_CAMPAIGN`

**When to call.** Use this integration journal surface when the request matches `mosaic.integration-campaign-stage.v0.1` and `LOCAL_ARTIFACT_PREPARATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.integration-campaign-stage.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"MANAGE_INTEGRATION_CAMPAIGN","payload":{"stage_contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BIND_INTEGRATION_SUBJECT`

**When to call.** Use this amcas integration surface when the request matches `mosaic.ucm.subject-binding-policy.v0.1` and `READ_ONLY` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.subject-binding-policy.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BIND_INTEGRATION_SUBJECT","payload":{"stage_contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `CHECK_CONTROL_PLANES`

**When to call.** Use this amcas integration surface when the request matches `mosaic.ucm.control-plane-disposition.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.control-plane-disposition.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"CHECK_CONTROL_PLANES","payload":{"stage_contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `RUN_CORRESPONDENCE_COURT`

**When to call.** Use this court execution surface when the request matches `mosaic.ucm.native-correspondence-cases.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.native-correspondence-cases.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"RUN_CORRESPONDENCE_COURT","payload":{"stage_contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VERIFY_STAGE_I1`

**When to call.** Use this amcas integration surface when the request matches `mosaic.ucm.stage-i1-bundle.v0.2` and `READ_ONLY` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.stage-i1-bundle.v0.2` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VERIFY_STAGE_I1","payload":{"stage_contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `GOVERN_INTEGRATION_PORTFOLIO`

**When to call.** Use this integration portfolio surface when the request matches `mosaic.ucm.integration-portfolio.v0.1` and `LOCAL_ARTIFACT_PREPARATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.integration-portfolio.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"GOVERN_INTEGRATION_PORTFOLIO","payload":{"stage_contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `PREFLIGHT_PORTFOLIO_COMPOSITION`

**When to call.** Use this integration portfolio surface when the request matches `mosaic.ucm.stage-i2-declaration.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.stage-i2-declaration.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"PREFLIGHT_PORTFOLIO_COMPOSITION","payload":{"stage_contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `PLAN_STAGE_I3_SHADOW`

**When to call.** Use this integration portfolio surface when the request matches `mosaic.ucm.stage-i3-shadow-instruction.v0.1` and `LOCAL_ARTIFACT_PREPARATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.stage-i3-shadow-instruction.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"PLAN_STAGE_I3_SHADOW","payload":{"stage_contract":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VALIDATE_STAGE_I3_PLAN`

**When to call.** Use this integration portfolio surface when the request matches `mosaic.ucm.stage-i3-plan-validation-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.stage-i3-plan-validation-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VALIDATE_STAGE_I3_PLAN","payload":{"instruction":"…","plan":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VALIDATE_NATIVE_CONTROL_PLANE_RESULT`

**When to call.** Use this constitutional integration surface when the request matches `mosaic.ucm.native-control-plane-result.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.native-control-plane-result.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VALIDATE_NATIVE_CONTROL_PLANE_RESULT","payload":{"adapter_result":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VALIDATE_APPLICATION_CAPSULE`

**When to call.** Use this constitutional integration surface when the request matches `mosaic.ucm.application-constitutionalization-capsule.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.application-constitutionalization-capsule.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VALIDATE_APPLICATION_CAPSULE","payload":{"capsule":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VALIDATE_INTEGRATION_CONTROL_PLAN`

**When to call.** Use this constitutional integration surface when the request matches `mosaic.ucm.integration-control-plan.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.integration-control-plan.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VALIDATE_INTEGRATION_CONTROL_PLAN","payload":{"plan":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `INSPECT_INTEGRATION_OBSERVATORY`

**When to call.** Use this constitutional integration surface when the request matches `mosaic.ucm.integration-observatory-request.v0.1` and `READ_ONLY` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.integration-observatory-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"INSPECT_INTEGRATION_OBSERVATORY","payload":{"capsules":"…","operation_states":"…","journal_heads":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_DEVELOPMENT_STANDARDS_CATALOG`

**When to call.** Use this development standards surface when the request matches `mosaic.ucm.development-standards-catalog-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.development-standards-catalog-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_DEVELOPMENT_STANDARDS_CATALOG","payload":{"catalog_id":"…","policy_root":"…","obligations":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `EVALUATE_DEVELOPMENT_STANDARDS`

**When to call.** Use this development standards surface when the request matches `mosaic.ucm.development-standards-evaluation-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.development-standards-evaluation-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"EVALUATE_DEVELOPMENT_STANDARDS","payload":{"catalog":"…","subject_root":"…","active_triggers":"…","check_results":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_PIPPI_CONTEXT`

**When to call.** Use this pippi mediation surface when the request matches `mosaic.ucm.pippi-context-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pippi-context-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_PIPPI_CONTEXT","payload":{"session_root":"…","subject_root":"…","policy_roots":"…","capability_registry_root":"…","profile_root":"…","jurisdiction_root":"…","retained_context_roots":"…","mediated_channels":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_PIPPI_HOST_ADAPTER_POLICY`

**When to call.** Use this pippi mediation surface when the request matches `mosaic.ucm.pippi-host-adapter-policy-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pippi-host-adapter-policy-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_PIPPI_HOST_ADAPTER_POLICY","payload":{"policy_id":"…","adapter_registry_root":"…","attestor_public_key_hex":"…","operation_issuer_public_key_hex":"…","operation_jurisdiction_root":"…","operation_revocation_registry_root":"…","maximum_validity_ns":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_ATTESTED_PIPPI_CONTEXT`

**When to call.** Use this pippi mediation surface when the request matches `mosaic.ucm.pippi-attested-context-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pippi-attested-context-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_ATTESTED_PIPPI_CONTEXT","payload":{"session_root":"…","subject_root":"…","policy_roots":"…","capability_registry_root":"…","profile_root":"…","jurisdiction_root":"…","retained_context_roots":"…","expected_host_policy_root":"…","host_policy":"…","host_attestation":"…","now_ns":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_PIPPI_HOST_LAUNCH_PROPOSAL`

**When to call.** Use this pippi mediation surface when the request matches `mosaic.ucm.pippi-host-launch-proposal-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pippi-host-launch-proposal-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_PIPPI_HOST_LAUNCH_PROPOSAL","payload":{"project_root":"…","session_root":"…","host_policy_root":"…","host_attestation_root":"…","kind":"…","payload":"…","expected_hub_head":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VALIDATE_PIPPI_HOST_LAUNCH_RESULT`

**When to call.** Use this pippi mediation surface when the request matches `mosaic.ucm.pippi-host-launch-result-validation-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pippi-host-launch-result-validation-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VALIDATE_PIPPI_HOST_LAUNCH_RESULT","payload":{"value":"…","proposal":"…","policy":"…","attestation":"…","now_ns":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_PIPPI_INTEGRATION_REGISTRY`

**When to call.** Use this pippi mediation surface when the request matches `mosaic.ucm.pippi-integration-availability-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pippi-integration-availability-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_PIPPI_INTEGRATION_REGISTRY","payload":{"entries":"…","source":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BIND_PIPPI_EXTERNAL_INTEGRATION`

**When to call.** Use this pippi mediation surface when the request matches `mosaic.ucm.pippi-integration-binding-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pippi-integration-binding-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BIND_PIPPI_EXTERNAL_INTEGRATION","payload":{"registry":"…","integration_id":"…","binding_root":"…","evidence_roots":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_PIPPI_MODEL_DRAFT`

**When to call.** Use this pippi mediation surface when the request matches `mosaic.ucm.pippi-model-draft-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pippi-model-draft-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_PIPPI_MODEL_DRAFT","payload":{"turn_id":"…","context":"…","text":"…","proposals":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `EVALUATE_PIPPI_DRAFT`

**When to call.** Use this pippi mediation surface when the request matches `mosaic.ucm.pippi-decision-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pippi-decision-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"EVALUATE_PIPPI_DRAFT","payload":{"draft":"…","policy_evaluation_roots":"…","proposal_dispositions":"…","semantic_resolution_root":"…","semantic_status":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_PIPPI_HUMAN_PROJECTION`

**When to call.** Use this pippi mediation surface when the request matches `mosaic.ucm.pippi-human-projection-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pippi-human-projection-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_PIPPI_HUMAN_PROJECTION","payload":{"draft":"…","decision":"…","view":"…","annotation_root":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_PIPPI_CONSTITUTIONAL_EXCEPTION`

**When to call.** Use this pippi mediation surface when the request matches `mosaic.ucm.pippi-constitutional-exception-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pippi-constitutional-exception-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_PIPPI_CONSTITUTIONAL_EXCEPTION","payload":{"draft_root":"…","proposal_id":"…","missing_rule_id":"…","requested_decision":"…","affected_obligation_ids":"…","external_decision_root":"…","successor_policy_root":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_PIPPI_TURN_ENVELOPE`

**When to call.** Use this pippi mediation surface when the request matches `mosaic.ucm.pippi-turn-envelope-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pippi-turn-envelope-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_PIPPI_TURN_ENVELOPE","payload":{"sequence":"…","previous_turn_root":"…","context":"…","draft":"…","decision":"…","projection":"…","tool_proposal_roots":"…","dispatch_receipt_roots":"…","tool_result_roots":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `DISCOVER_PIPPI_MEDIATION_LIBRARY`

**When to call.** Use this pippi mediation surface when the request matches `mosaic.ucm.empty.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.empty.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"DISCOVER_PIPPI_MEDIATION_LIBRARY","payload":{},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `NEGOTIATE_PIPPI_HOST_MODE`

**When to call.** Use this pippi mediation surface when the request matches `mosaic.ucm.pippi-host-negotiation-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pippi-host-negotiation-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"NEGOTIATE_PIPPI_HOST_MODE","payload":{"host_id":"…","requested_mode":"…","capability_ids":"…","adapter_root":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `PREPARE_PIPPI_TURN`

**When to call.** Use this pippi mediation surface when the request matches `mosaic.ucm.pippi-turn-prepare-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pippi-turn-prepare-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"PREPARE_PIPPI_TURN","payload":{"project":"…","host_profile":"…","sequence":"…","previous_turn_root":"…","scenario":"…","requested_rule_ids":"…","acceptance_case_roots":"…","journal_head":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_PIPPI_TURN_REPORT`

**When to call.** Use this pippi mediation surface when the request matches `mosaic.ucm.pippi-turn-report-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pippi-turn-report-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_PIPPI_TURN_REPORT","payload":{"opening":"…","summary":"…","changed_paths":"…","artifact_roots":"…","evidence_roots":"…","unresolved_items":"…","next_action":"…","claim_class":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `RECONCILE_PIPPI_TURN`

**When to call.** Use this pippi mediation surface when the request matches `mosaic.ucm.pippi-turn-reconcile-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pippi-turn-reconcile-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"RECONCILE_PIPPI_TURN","payload":{"opening":"…","report":"…","current_project_root":"…","current_journal_head":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_PIPPI_PROJECT_CAPSULE`

**When to call.** Use this portable bootstrap surface when the request matches `mosaic.ucm.pippi-project-capsule-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pippi-project-capsule-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_PIPPI_PROJECT_CAPSULE","payload":{"profile":"…","project":"…","host_profile":"…","ucm_root":"…","ugk_root":"…","mediation_library_root":"…","journal_head":"…","turn_root":"…","public_identity_roots":"…","members":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VERIFY_PIPPI_PROJECT_CAPSULE`

**When to call.** Use this portable bootstrap surface when the request matches `mosaic.ucm.pippi-project-capsule.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pippi-project-capsule.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VERIFY_PIPPI_PROJECT_CAPSULE","payload":{"value":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `INSPECT_PIPPI_INTERFACE_CONFORMANCE`

**When to call.** Use this agent workbench surface when the request matches `mosaic.ucm.empty.v0.1` and `READ_ONLY` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.empty.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"INSPECT_PIPPI_INTERFACE_CONFORMANCE","payload":{},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `DISCOVER_C_CODING_STANDARD`

**When to call.** Use this c coding preflight surface when the request matches `mosaic.ucm.empty.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.empty.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"DISCOVER_C_CODING_STANDARD","payload":{},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `PREFLIGHT_C_CHANGE`

**When to call.** Use this c coding preflight surface when the request matches `mosaic.ucm.c-change-preflight-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.c-change-preflight-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"PREFLIGHT_C_CHANGE","payload":{"proposal_id":"…","subject_root":"…","source_manifest_root":"…","language_standard":"…","compiler_profile_root":"…","architecture_contract_root":"…","change_classes":"…","changed_paths":"…","declared_write_paths":"…","declared_check_ids":"…","requested_effect_classes":"…","integration_mode":"…","mediated_channels":"…","native_semantic_authority":"…","python_role":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `EVALUATE_C_CHANGE_RESULTS`

**When to call.** Use this c coding preflight surface when the request matches `mosaic.ucm.c-check-evaluation-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.c-check-evaluation-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"EVALUATE_C_CHANGE_RESULTS","payload":{"preflight":"…","check_results":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_DEVELOPMENT_OBSERVATORY`

**When to call.** Use this development standards surface when the request matches `mosaic.ucm.development-observatory-request.v0.1` and `READ_ONLY` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.development-observatory-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_DEVELOPMENT_OBSERVATORY","payload":{"subject_root":"…","standards_evaluations":"…","pippi_decisions":"…","launch_states":"…","constitutional_exceptions":"…","journal_head_roots":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `PROJECT_DEVELOPMENT_OBSERVATORY`

**When to call.** Use this development standards surface when the request matches `mosaic.ucm.development-observatory-projection-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.development-observatory-projection-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"PROJECT_DEVELOPMENT_OBSERVATORY","payload":{"state":"…","view":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_DKN_LOCALITY_BINDING`

**When to call.** Use this process governance surface when the request matches `mosaic.ucm.process-locality-binding-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.process-locality-binding-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_DKN_LOCALITY_BINDING","payload":{"phase_code":"…","authority_public_key_hex":"…","semantic_namespace":"…","universe_root":"…","namespace_policy_root":"…","passport":"…","possession_receipt_root":"…","local_admission_root":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_EXACT_EXECUTION_CAPSULE`

**When to call.** Use this process governance surface when the request matches `mosaic.ucm.exact-execution-capsule-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.exact-execution-capsule-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_EXACT_EXECUTION_CAPSULE","payload":{"capsule_id":"…","executable_root":"…","runner_root":"…","argv":"…","normalized_cwd":"…","environment_projection":"…","dependencies":"…","missing_dependency_ids":"…","exact_input_roots":"…","policy_root":"…","profile_root":"…","authority_root":"…","jurisdiction_root":"…","effect_class":"…","expected_write_paths":"…","transaction_history_paths":"…","adapter_root":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_ARTIFACT_PRODUCER_RECEIPT`

**When to call.** Use this process governance surface when the request matches `mosaic.ucm.artifact-producer-receipt-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.artifact-producer-receipt-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_ARTIFACT_PRODUCER_RECEIPT","payload":{"artifact_path":"…","artifact_sha256":"…","producer_operation_root":"…","predecessor_artifact_sha256":"…","predecessor_producer_operation_root":"…","transaction_history_path":"…","supersession_kind":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_PROCESS_BASELINE`

**When to call.** Use this process governance surface when the request matches `mosaic.ucm.process-baseline-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.process-baseline-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_PROCESS_BASELINE","payload":{"project_id":"…","objective":"…","subject_root":"…","source_manifest_root":"…","architecture_contract_root":"…","amcas_contract_root":"…","standards_catalog_root":"…","policy_roots":"…","requirement_roots":"…","software_generation_root":"…","initial_journal_head_root":"…","user_identity_root":"…","session_identity_root":"…","locality_binding":"…","responsibilities":"…","deliverable_ids":"…","execution_capsule_roots":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_PROCESS_MILESTONE`

**When to call.** Use this process governance surface when the request matches `mosaic.ucm.process-milestone-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.process-milestone-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_PROCESS_MILESTONE","payload":{"milestone_id":"…","process_baseline_root":"…","title":"…","objective":"…","predecessor_milestone_ids":"…","entry_criteria":"…","deliverables":"…","standards_obligation_ids":"…","acceptance_role_id":"…","acceptance_policy_root":"…","rollback_required":"…","rollback_plan_root":"…","authority_ceiling":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `ASSESS_PROCESS_MILESTONE`

**When to call.** Use this process governance surface when the request matches `mosaic.ucm.process-milestone-assessment-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.process-milestone-assessment-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"ASSESS_PROCESS_MILESTONE","payload":{"milestone":"…","accepted_predecessors":"…","entry_evidence":"…","check_results":"…","standards_evaluation":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `RECORD_PROCESS_MILESTONE_DECISION`

**When to call.** Use this process governance surface when the request matches `mosaic.ucm.process-milestone-decision-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.process-milestone-decision-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"RECORD_PROCESS_MILESTONE_DECISION","payload":{"assessment":"…","decision":"…","reason_codes":"…","external_approval":"…","expected_acceptance_policy_root":"…","now":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_PROCESS_CHECKPOINT`

**When to call.** Use this process governance surface when the request matches `mosaic.ucm.process-checkpoint-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.process-checkpoint-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_PROCESS_CHECKPOINT","payload":{"baseline":"…","sequence":"…","predecessor_checkpoint":"…","lifecycle_state":"…","plan_root":"…","milestone_assessments":"…","milestone_decisions":"…","active_work_ids":"…","hold_codes":"…","evidence_roots":"…","decision_roots":"…","journal_head_root":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_PROCESS_REPLAN`

**When to call.** Use this process governance surface when the request matches `mosaic.ucm.process-replan-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.process-replan-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_PROCESS_REPLAN","payload":{"predecessor_checkpoint":"…","successor_plan_root":"…","reason_code":"…","scope_delta":"…","affected_dependency_ids":"…","invalidated_evidence_roots":"…","retained_evidence_roots":"…","unresolved_work_ids":"…","unresolved_dispositions":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_PROCESS_STANDARDS_SCHEDULE`

**When to call.** Use this process governance surface when the request matches `mosaic.ucm.process-standards-schedule-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.process-standards-schedule-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_PROCESS_STANDARDS_SCHEDULE","payload":{"catalog":"…","subject_root":"…","event_facts":"…","last_satisfied":"…","invalidations":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_PROCESS_OBSERVATORY`

**When to call.** Use this process governance surface when the request matches `mosaic.ucm.process-observatory-request.v0.1` and `READ_ONLY` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.process-observatory-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_PROCESS_OBSERVATORY","payload":{"checkpoint":"…","standards_schedule":"…","artifact_statuses":"…","replan_roots":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_COURTHOUSE_PROCESS_BINDING`

**When to call.** Use this process governance surface when the request matches `mosaic.ucm.process-courthouse-binding-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.process-courthouse-binding-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_COURTHOUSE_PROCESS_BINDING","payload":{"baseline":"…","checkpoint":"…","execution_capsule":"…","requested_surface":"…","authority_policy_root":"…","native_runner_binding_root":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_PROCESS_THR_MANIFEST`

**When to call.** Use this process governance surface when the request matches `mosaic.ucm.process-thr-manifest-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.process-thr-manifest-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_PROCESS_THR_MANIFEST","payload":{"baseline":"…","locality_binding":"…","checkpoint":"…","milestones":"…","assessments":"…","decisions":"…","standards_evaluation_roots":"…","evidence_receipt_roots":"…","interpretation_profile_root":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_SEMANTIC_PASSAGE`

**When to call.** Use this semantic passage surface when the request matches `mosaic.ucm.semantic-passage-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.semantic-passage-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_SEMANTIC_PASSAGE","payload":{"passage_id":"…","text":"…","context_root":"…","provider_mode":"…","provider_root":"…","spans":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_SEMANTIC_CLARIFICATION`

**When to call.** Use this semantic passage surface when the request matches `mosaic.ucm.semantic-clarification-request-builder.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.semantic-clarification-request-builder.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_SEMANTIC_CLARIFICATION","payload":{"passage":"…","turn":"…","unresolved_span_ids":"…","remaining_turns":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `RESOLVE_SEMANTIC_PASSAGE`

**When to call.** Use this semantic passage surface when the request matches `mosaic.ucm.semantic-passage-resolution-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.semantic-passage-resolution-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"RESOLVE_SEMANTIC_PASSAGE","payload":{"passage":"…","selections":"…","clarification_roots":"…","budget_exhausted":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_CONSTITUTIONAL_LAUNCH_CONTRACT`

**When to call.** Use this constitutional launch surface when the request matches `mosaic.ucm.constitutional-launch-contract-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.constitutional-launch-contract-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_CONSTITUTIONAL_LAUNCH_CONTRACT","payload":{"launch_id":"…","application_id":"…","subject_root":"…","executable_root":"…","argument_root":"…","environment_policy_root":"…","readiness_probe_id":"…","readiness_contract_root":"…","timeout_ms":"…","executor_binding_root":"…","branding":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_CONSTITUTIONAL_LAUNCH_OBSERVATION`

**When to call.** Use this constitutional launch surface when the request matches `mosaic.ucm.constitutional-launch-observation-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.constitutional-launch-observation-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_CONSTITUTIONAL_LAUNCH_OBSERVATION","payload":{"contract":"…","sequence":"…","state":"…","previous_observation_root":"…","executor_receipt_root":"…","g1_root":"…","g2_root":"…","g3_root":"…","readiness_evidence_root":"…","reason_codes":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `DERIVE_CONSTITUTIONAL_LAUNCH_STATE`

**When to call.** Use this constitutional launch surface when the request matches `mosaic.ucm.constitutional-launch-state-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.constitutional-launch-state-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"DERIVE_CONSTITUTIONAL_LAUNCH_STATE","payload":{"contract":"…","observations":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_BEHAVIORAL_HARNESS_CONTRACT`

**When to call.** Use this behavioral harness surface when the request matches `mosaic.ucm.behavioral-harness-contract-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.behavioral-harness-contract-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_BEHAVIORAL_HARNESS_CONTRACT","payload":{"harness_id":"…","subject_root":"…","state_adapter_root":"…","action_generator_root":"…","executor_binding_root":"…","required_controls":"…","allowed_write_paths":"…","scenario_ids":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_BEHAVIORAL_TRANSITION_RECEIPT`

**When to call.** Use this behavioral harness surface when the request matches `mosaic.ucm.behavioral-transition-receipt-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.behavioral-transition-receipt-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_BEHAVIORAL_TRANSITION_RECEIPT","payload":{"contract":"…","scenario_id":"…","pre_state_root":"…","action_root":"…","post_state_root":"…","observed_controls":"…","observed_write_paths":"…","executor_receipt_root":"…","status":"…","reason_codes":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_ADMISSIBILITY_JURISDICTION`

**When to call.** Use this point of use admissibility surface when the request matches `mosaic.ucm.admissibility-jurisdiction-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.admissibility-jurisdiction-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_ADMISSIBILITY_JURISDICTION","payload":{"profile_id":"…","application_id":"…","subject_root":"…","state_boundary_id":"…","state_root":"…","manifest_root":"…","path_policy":"…","governance_jurisdiction_root":"…","bound_policy_root":"…","bound_schema_registry_root":"…","bound_trust_root":"…","transition_rule_root":"…","allowed_operations":"…","evidence_modes":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_ADMISSIBILITY_ENFORCEMENT_PERIMETER`

**When to call.** Use this point of use admissibility surface when the request matches `mosaic.ucm.enforcement-perimeter-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.enforcement-perimeter-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_ADMISSIBILITY_ENFORCEMENT_PERIMETER","payload":{"perimeter_id":"…","jurisdiction_profile_root":"…","adapter_root":"…","intercepted_operations":"…","excluded_bypass_classes":"…","continuing_use_policy":"…","qualification_status":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_CHC_THR_CORRESPONDENCE`

**When to call.** Use this point of use admissibility surface when the request matches `mosaic.ucm.chc-thr-correspondence-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.chc-thr-correspondence-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_CHC_THR_CORRESPONDENCE","payload":{"correspondence_id":"…","correspondence_version":"…","chc_source_root":"…","chc_profile_root":"…","thr_contract_root":"…","role_mappings":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_ADMISSIBILITY_EVIDENCE_SNAPSHOT`

**When to call.** Use this point of use admissibility surface when the request matches `mosaic.ucm.admissibility-evidence-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.admissibility-evidence-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_ADMISSIBILITY_EVIDENCE_SNAPSHOT","payload":{"snapshot_id":"…","subject_root":"…","state_identity_root":"…","semantic_identity_root":"…","jurisdiction_profile_root":"…","enforcement_perimeter_root":"…","active_policy_root":"…","active_schema_registry_root":"…","active_trust_root":"…","checkpoint_root":"…","checkpoint_sequence":"…","persistent_maximum_sequence":"…","authenticated_epoch":"…","evidence":"…","status_evidence_ids":"…","unresolved_requirements":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_CURRENT_USE_SNAPSHOT`

**When to call.** Use this point of use admissibility surface when the request matches `mosaic.ucm.current-use-snapshot-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.current-use-snapshot-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_CURRENT_USE_SNAPSHOT","payload":{"request_id":"…","operation":"…","subject_root":"…","target_root":"…","handler_root":"…","runtime_root":"…","dependency_closure_root":"…","state_identity_root":"…","semantic_identity_root":"…","jurisdiction_profile_root":"…","enforcement_perimeter_root":"…","correspondence_root":"…","evidence_snapshot_root":"…","active_policy_root":"…","active_schema_registry_root":"…","active_trust_root":"…","checkpoint_root":"…","authenticated_epoch":"…","requested_effect_classes":"…","max_steps":"…","max_evidence_rows":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `EVALUATE_CURRENT_ADMISSIBILITY`

**When to call.** Use this point of use admissibility surface when the request matches `mosaic.ucm.current-admissibility-evaluation-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.current-admissibility-evaluation-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"EVALUATE_CURRENT_ADMISSIBILITY","payload":{"current_use_snapshot":"…","evidence_snapshot":"…","jurisdiction_profile":"…","enforcement_perimeter":"…","correspondence":"…","expected_subject_root":"…","expected_jurisdiction_profile_root":"…","expected_enforcement_perimeter_root":"…","expected_correspondence_root":"…","expected_policy_root":"…","expected_schema_registry_root":"…","expected_trust_root":"…","expected_checkpoint_root":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `EXPLAIN_CURRENT_ADMISSIBILITY`

**When to call.** Use this pippi mediation surface when the request matches `mosaic.ucm.current-admissibility-explanation-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.current-admissibility-explanation-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"EXPLAIN_CURRENT_ADMISSIBILITY","payload":{"decision":"…","current_use_snapshot":"…","evidence_snapshot":"…","jurisdiction_profile":"…","enforcement_perimeter":"…","correspondence":"…","expected_subject_root":"…","expected_jurisdiction_profile_root":"…","expected_enforcement_perimeter_root":"…","expected_correspondence_root":"…","expected_policy_root":"…","expected_schema_registry_root":"…","expected_trust_root":"…","expected_checkpoint_root":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_COURTHOUSE_ADMISSION_ENVELOPE`

**When to call.** Use this point of use admissibility surface when the request matches `mosaic.ucm.ccp-courthouse-admission-envelope-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.ccp-courthouse-admission-envelope-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_COURTHOUSE_ADMISSION_ENVELOPE","payload":{"workflow_request":"…","acceptance_case_root":"…","work_unit_root":"…","jurisdiction_profile":"…","enforcement_perimeter":"…","correspondence":"…","evidence_snapshot":"…","current_use_snapshot":"…","decision":"…","expected_subject_root":"…","expected_jurisdiction_profile_root":"…","expected_enforcement_perimeter_root":"…","expected_correspondence_root":"…","expected_policy_root":"…","expected_schema_registry_root":"…","expected_trust_root":"…","expected_checkpoint_root":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `COMPILE_ADMISSIBLE_COURTHOUSE_WORKFLOW`

**When to call.** Use this point of use admissibility surface when the request matches `mosaic.ucm.ccp-courthouse-workflow-submission-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.ccp-courthouse-workflow-submission-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"COMPILE_ADMISSIBLE_COURTHOUSE_WORKFLOW","payload":{"workflow_request":"…","admission_envelope":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `PROJECT_COURTHOUSE_ADMISSION_STATUS`

**When to call.** Use this pippi mediation surface when the request matches `mosaic.ucm.pippi-courthouse-admission-status-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.pippi-courthouse-admission-status-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"PROJECT_COURTHOUSE_ADMISSION_STATUS","payload":{"submission":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VERIFY_ADMISSIBLE_COURTHOUSE_RESULT`

**When to call.** Use this point of use admissibility surface when the request matches `mosaic.ucm.ccp-courthouse-result-import-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.ccp-courthouse-result-import-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VERIFY_ADMISSIBLE_COURTHOUSE_RESULT","payload":{"submission":"…","result":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `PREPARE_ADMISSIBILITY_BOUND_GATEWAY`

**When to call.** Use this operational gateway surface when the request matches `mosaic.ucm.admissibility-bound-prepare-request.v0.1` and `LOCAL_ARTIFACT_PREPARATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.admissibility-bound-prepare-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"PREPARE_ADMISSIBILITY_BOUND_GATEWAY","payload":{"contract":"…","decision":"…","current_use_snapshot":"…","evidence_snapshot":"…","jurisdiction_profile":"…","enforcement_perimeter":"…","correspondence":"…","expected_subject_root":"…","expected_jurisdiction_profile_root":"…","expected_enforcement_perimeter_root":"…","expected_correspondence_root":"…","expected_policy_root":"…","expected_schema_registry_root":"…","expected_trust_root":"…","expected_checkpoint_root":"…","expected_admissibility_decision_root":"…","expected_current_use_snapshot_root":"…","expected_issuer_public_key_hex":"…","expected_jurisdiction_root":"…","expected_revocation_registry_root":"…","progress_path":"…","workspace":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_OPERATIONAL_CONTRACT`

**When to call.** Use this operational gateway surface when the request matches `mosaic.ucm.operational-contract-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.operational-contract-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_OPERATIONAL_CONTRACT","payload":{"expected_issuer_public_key_hex":"…","expected_jurisdiction_root":"…","expected_result_root":"…","expected_revocation_registry_root":"…","idempotency_key":"…","now":"…","operation_id":"…","permit":"…","requested_effect_classes":"…","revocation_registry":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `PREPARE_OPERATIONAL_GATEWAY`

**When to call.** Use this operational gateway surface when the request matches `mosaic.ucm.operational-prepare-request.v0.1` and `LOCAL_ARTIFACT_PREPARATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.operational-prepare-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"PREPARE_OPERATIONAL_GATEWAY","payload":{"contract":"…","expected_issuer_public_key_hex":"…","expected_jurisdiction_root":"…","expected_revocation_registry_root":"…","progress_path":"…","workspace":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `RECORD_OPERATIONAL_DISPATCH`

**When to call.** Use this operational gateway surface when the request matches `mosaic.ucm.operational-dispatch-request.v0.1` and `LOCAL_ARTIFACT_PREPARATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.operational-dispatch-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"RECORD_OPERATIONAL_DISPATCH","payload":{"operation_id":"…","progress_path":"…","receipt":"…","workspace":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `RECORD_OPERATIONAL_TERMINAL`

**When to call.** Use this operational gateway surface when the request matches `mosaic.ucm.operational-terminal-request.v0.1` and `LOCAL_ARTIFACT_PREPARATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.operational-terminal-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"RECORD_OPERATIONAL_TERMINAL","payload":{"operation_id":"…","progress_path":"…","receipt":"…","workspace":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `FINALIZE_OPERATIONAL_TERMINAL`

**When to call.** Use this operational gateway surface when the request matches `mosaic.ucm.operational-finalization-request.v0.1` and `LOCAL_ARTIFACT_PREPARATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.operational-finalization-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"FINALIZE_OPERATIONAL_TERMINAL","payload":{"operation_id":"…","progress_path":"…","workspace":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `MARK_OPERATIONAL_UNCERTAIN`

**When to call.** Use this operational gateway surface when the request matches `mosaic.ucm.operational-uncertain-request.v0.1` and `LOCAL_ARTIFACT_PREPARATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.operational-uncertain-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"MARK_OPERATIONAL_UNCERTAIN","payload":{"operation_id":"…","progress_path":"…","reason_code":"…","workspace":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `RECONCILE_OPERATIONAL_OUTCOME`

**When to call.** Use this operational gateway surface when the request matches `mosaic.ucm.operational-reconcile-request.v0.1` and `LOCAL_ARTIFACT_PREPARATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.operational-reconcile-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"RECONCILE_OPERATIONAL_OUTCOME","payload":{"operation_id":"…","progress_path":"…","receipt":"…","workspace":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `CANCEL_OPERATIONAL_GATEWAY`

**When to call.** Use this operational gateway surface when the request matches `mosaic.ucm.operational-cancel-request.v0.1` and `LOCAL_ARTIFACT_PREPARATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.operational-cancel-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"CANCEL_OPERATIONAL_GATEWAY","payload":{"operation_id":"…","progress_path":"…","reason_code":"…","workspace":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `INSPECT_OPERATIONAL_STATE`

**When to call.** Use this operational gateway surface when the request matches `mosaic.ucm.operational-state-request.v0.1` and `READ_ONLY` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.operational-state-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"INSPECT_OPERATIONAL_STATE","payload":{"operation_id":"…","workspace":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `BUILD_OPERATIONAL_PROOF`

**When to call.** Use this operational gateway surface when the request matches `mosaic.ucm.operational-proof-request.v0.1` and `READ_ONLY` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.operational-proof-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"BUILD_OPERATIONAL_PROOF","payload":{"expected_issuer_public_key_hex":"…","expected_jurisdiction_root":"…","expected_revocation_registry_root":"…","operation_id":"…","workspace":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `EXPORT_OPERATIONAL_ARCHIVE`

**When to call.** Use this operational gateway surface when the request matches `mosaic.ucm.operational-archive-request.v0.1` and `READ_ONLY` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.operational-archive-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"EXPORT_OPERATIONAL_ARCHIVE","payload":{"expected_issuer_public_key_hex":"…","expected_jurisdiction_root":"…","expected_revocation_registry_root":"…","operation_id":"…","workspace":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `VERIFY_OPERATIONAL_ARCHIVE`

**When to call.** Use this operational gateway surface when the request matches `mosaic.ucm.operational-archive-verification-request.v0.1` and `PURE_COMPUTATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.operational-archive-verification-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"VERIFY_OPERATIONAL_ARCHIVE","payload":{"archive_base64":"…","expected_issuer_public_key_hex":"…","expected_jurisdiction_root":"…","expected_revocation_registry_root":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

## `RECOVER_OPERATIONAL_JOURNAL`

**When to call.** Use this operational gateway surface when the request matches `mosaic.ucm.operational-journal-recovery-request.v0.1` and `LOCAL_ARTIFACT_PREPARATION` is within the selected profile.

**When it refuses.** It refuses an unpinned registry, a profile that excludes the surface, missing or extra payload fields, invalid `mosaic.ucm.operational-journal-recovery-request.v0.1` data, or a separately staged effect invoked through a pure route.

**Minimal request.** `{"schema":"mosaic.ucm.request.v0.2","surface":"RECOVER_OPERATIONAL_JOURNAL","payload":{"expected_head":"…","progress_path":"…","workspace":"…"},"profile_selection":{"…":"pinned profile"},"request_id":"…"}`

**Common misuse.** Do not infer permission from a PASS result, substitute progress output for evidence, or call a compatibility route because its name resembles a current task.

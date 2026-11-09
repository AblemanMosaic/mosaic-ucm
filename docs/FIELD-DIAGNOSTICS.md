# Field diagnostics and journal navigation

`ucm smoke` runs a deterministic canary over canonicalization, realization
validation, the capability registry and product profiles. `ucm doctor` adds
host observations and optional dependency presence. A doctor result diagnoses
an installation; it is not qualification or host admission.

Journal tools are pure projections over verified event chains:

- `journal-summary` reports counts and last operation states;
- `journal-query` selects exact events without changing the journal;
- `journal-diff` distinguishes identical, fast-forward and diverged chains;
- `journal-prove` produces a suffix proof from one event to a journal head;
- `journal-verify-proof` rechecks that proof.

Progress remains nonsemantic. Only verified journal events and their roots may
satisfy custody claims.

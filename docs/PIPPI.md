# Pippi mediation boundary

Pippi is UCM's governed proposal, evaluation, presentation, and journal boundary for agentic work. It is an implementation of the CARA direction at the host boundary: context enters through a rooted capsule; observable model output becomes a draft; text, tool calls, capability grants, and policy changes become proposals; policies classify each proposal; the host displays only a rooted projection; and the complete observable turn enters the canonical journal.

Pippi does not claim access to hidden model reasoning. It does not call a model, execute tools, grant capabilities, or replace the Operational Gateway. Effectful proposals remain held until a declared contract and the external G1/G2/G3 effect path apply.

For work spanning several turns, Pippi's [process-governance layer](PIPPI-PROCESS-GOVERNANCE.md) binds the exact project baseline, execution dependency closure, milestones, evidence, acceptance, replanning, standards schedule, locality and journal-derived status. Courthouse vNext remains the native execution boundary.

## Honest integration modes

`ENFORCED_HOST` requires mediation of `MODEL_INPUT`, `MODEL_DRAFT`,
`VISIBLE_OUTPUT`, `TOOL_PROPOSAL`, `TOOL_DISPATCH`, `TOOL_RESULT`, and
`JOURNAL_WRITE` **plus** a current Ed25519 host-mediation attestation under a
host-adapter policy whose root is supplied independently by the host boundary.
A list of seven channels, or a self-contained signed capsule without that
external root, is treated as `SIDECAR_PARTIAL`. A chat instruction cannot
establish enforced-host status. See [the host adapter boundary](PIPPI-HOST-ADAPTER.md).

## Agent loop

1. Orient and bind the subject, policy, capability registry, profile, and jurisdiction.
2. Record the observable model draft and typed proposals.
3. Evaluate every proposal against the fixed standards and application contract.
4. Hold undeclared effectful proposals and emit a constitutional exception.
5. Preserve exact prose; attach semantic annotations without rewriting it.
6. Project a reading, integer, split, or audit view for the host.
7. Send effect proposals to the externally bound Operational Gateway. The
   dashboard disables launch controls while that integration is unbound.
8. Re-derive the completed operation from its permit, G1/G2/G3 history and
   signed executor receipts before recording the tool result.
9. Persist the turn in the canonical campaign journal.

For C engineering, run the C coding preflight before dispatching an editor,
compiler, analyzer, or test runner. It classifies the intended paths, derives
the mandatory check denominator, and returns a typed refusal when the proposal
violates the pinned C standard. See `docs/C-CODING-PREFLIGHT.md`.

## CLI entry points

- `ucm pippi-create CONTEXT WORKSPACE`
- `ucm pippi-record-turn WORKSPACE CONTEXT DRAFT DECISION PROJECTION TURN --event-id ID`
- `ucm pippi-status WORKSPACE --view HUMAN`
- `ucm pippi-next WORKSPACE`
- `ucm pippi-explain WORKSPACE`
- `ucm pippi-verify WORKSPACE`
- `ucm process-build ACTION REQUEST.json OUTPUT.json`
- `ucm c-standard`
- `ucm c-preflight REQUEST.json`
- `ucm c-check-results REQUEST.json`

Progress JSONL may be displayed live, but it is never evidence. Journal roots, receipts, and typed records are the durable facts.


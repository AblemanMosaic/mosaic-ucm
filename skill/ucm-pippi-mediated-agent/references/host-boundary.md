# Pippi host boundary

Pippi governs observable host channels. It does not inspect private model
reasoning and cannot enforce a channel that the host does not route through it.

## Coverage declaration

Record each channel as mediated or unmediated:

| Channel | Required for `ENFORCED_HOST` |
| --- | --- |
| `MODEL_INPUT` | yes |
| `MODEL_DRAFT` | yes |
| `VISIBLE_OUTPUT` | yes |
| `TOOL_PROPOSAL` | yes |
| `TOOL_DISPATCH` | yes |
| `TOOL_RESULT` | yes |
| `JOURNAL_WRITE` | yes |

If any channel is missing, use `SIDECAR_PARTIAL` and list the omissions. Even a
complete caller-supplied list remains `SIDECAR_PARTIAL`. `ENFORCED_HOST`
requires a current Ed25519 attestation signed by the key pinned in the host
adapter policy **and** an expected policy root supplied independently by the
host boundary. A policy that arrives only inside its own signed capsule is not
an external trust anchor. The attestation binds the adapter source and registry, subject,
session, channel denominator and validity interval. A host may still gain useful
projection and custody from partial coverage, but it must not claim that all
agent behavior was mediated.

## Adapter invariants

- Pin the UCM software and capability registry roots before accepting records.
- Refuse startup when the adapter's expected registry or profile root differs.
- Keep model transport, Pippi evaluation, operational dispatch, and journal
  persistence as distinguishable planes.
- Only the governed projection is the official Pippi output. Hosts may expose
  the raw draft in a separately labelled diagnostic view.
- Never treat progress output, host logs, or a chat transcript as journal
  evidence.
- Fail closed on malformed records, missing dispositions, context drift,
  journal-head mismatch, and undeclared effects.
- A host adapter is responsible for routing. Pippi remains responsible for
  deterministic records and validation; the Operational Gateway remains
  responsible for effect custody.
- Treat external ownership and runtime availability separately. Refuse launch
  when `UCM_OPERATIONAL_GATEWAY` is not `BOUND_EXTERNAL` to the exact host
  policy root.
- Accept a launch result only when the existing Operational Gateway re-derives
  a completed operation for the exact proposal, subject, session and effect set.

## Local IPC credential boundary

The P/PPI loopback service is authenticated by `IPC.key`. Treat the endpoint
as routing metadata and the key as a private local credential. A conforming
runtime verifies a protected current-user DACL on Windows or owner-only mode
`0600` on POSIX before every key read. Do not claim an authenticated P/PPI host
when this verification is absent, inherited, broadened, or failed.


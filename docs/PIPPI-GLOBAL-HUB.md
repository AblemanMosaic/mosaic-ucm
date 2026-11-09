# P/PPI global local hub

P/PPI is the **Mosaic Project / Process Pipeline Interface**. It gives local
agent sessions one constitutional process home without replacing the UCM
Gateway, AOK courthouse, Mosaic Memory Vault, Crystal Network, Mosaic UI, or
Mosaic Reader.

## The first five questions

1. What local label should identify the Governor of this installation?
2. Is a persistent MosaicID public artifact available, or is this session-only?
3. Is a DKN public key available for a stable cryptographic namespace?
4. Which external credential provider holds GitHub access? P/PPI stores only a
   provider reference and refuses raw tokens, passwords, and private keys.
5. Is the Memory Vault backend reachable? It is preferred and enabled by
   default; the local content store is the bounded fallback.

## One system, five ownership boundaries

| Owner | Responsibility |
| --- | --- |
| P/PPI | Project/session constitutions, context injection, milestones, causal journal roots, launch proposals, user projections |
| UCM Gateway | Local effects and three-gate receipts |
| AOK courthouse | Remote work orders and cross-jurisdiction correspondence |
| Memory Vault | Transtemporal bytes and deduplicated reconstruction |
| Crystal Network | Publication semantics, DKN publication names, provider dispatch |

P/PPI keeps the causal root that says *what was archived and why*. Memory Vault
owns the bytes. A remote task is compiled into a courthouse work order rather
than sent by a new P/PPI-specific Internet adapter.

These are ownership declarations, not availability claims. `INTEGRATIONS.json`
projects each fixed-denominator integration as `BUILT_IN`, `BOUND_EXTERNAL`,
`DECLARED_UNBOUND`, or `UNAVAILABLE`, with an exact binding root and evidence
roots when bound. The default install marks the operational gateway,
courthouse, Crystal Network, and Memory Vault as declared but unbound. See
[integration availability](PIPPI-INTEGRATION-AVAILABILITY.md).

The release boundary enforces that split. Runtime and SDK artifacts refuse
inline review/history custody. Review artifacts must declare reference-only or
self-contained custody, and every transtemporal reference separates semantic,
state, metadata, and governance commitments. See
[transtemporal archiving](PIPPI-TRANSTEMPORAL-ARCHIVING.md).

## User-visible context injection

Every injection is an inspectable record. It names its scenario, exact rules,
project root, entrypoints, version policy, courthouse rule, seven-channel
coverage, and visibility rule. No hidden prompt text is authoritative.

## Native dashboard

The dashboard uses Mosaic UI's native Win32 realization and Mosaic Reader's
native document projection. Dark mode is the default. Each project shows
identity, version/revision, verification freshness, adherence, proof level,
operational maturity, working spaces, a separately bound canonical revision
store, concurrent sessions, archive state, courthouse state, and journal roots.
The top of the workspace contains a rooted **Now** projection shared with
`pippi project-brief`: current state, exact reason, and one read-only navigation
recommendation. The run group names its gateway dependency whenever the
operational gateway is not bound.
Its actions are:

- Launch application
- Launch verification
- Verify, then launch
- Open GitHub
- Open the native file tree
- Read README or project documents in Mosaic Reader
- Verify or replay an exact review envelope with live phase progress
- Inspect findings, limitations, evidence, and reviewer identity from exact archives
- Import a courthouse return through the native file selector
- Create a held publication proposal that still requires human authorization

Every effectful dashboard action is first a non-authorizing launch proposal.
The launch controls remain disabled until the operational-gateway integration
is externally bound to the exact host policy. A host adapter must return the
complete operational history and proof bundle; P/PPI independently rechecks
the permit, subject, session, requested effects, G1/G2/G3, terminal result and
projection root before journaling completion. It journals typed refusal when
that proof is absent or invalid. Progress remains visible and is never promoted
into evidence.

`pippi dashboard-probe` constructs the native Win32 dashboard without showing
it or dispatching an effect. The release Windows smoke path installs the exact
runtime in a disposable location, verifies the authenticated loopback service,
runs that dashboard probe, uninstalls, and emits a rooted positive-path record.

The dashboard relayouts at native DPI changes and remains usable down to its
declared 1180 × 760-DIP minimum. Wide and compact views project the same rooted
records and expose the same lifecycle actions.

Existing P/PPI campaigns join the hub by verified reference. Their source
journals remain authoritative and byte-unchanged. See
[session migration](PIPPI-SESSION-MIGRATION.md).

## Version rule

The public line stays `v0.1`. Engineering changes use `r001`, `r002`, and so
on. P/PPI injects revision advancement as the preferred next-output rule for
turns and work loops. It refuses an implicit public-version bump. A version
transition requires a signed external approval whose operation root binds the
exact predecessor project root, successor public version, and revision.


# Start P/PPI

The Constitution tab is the navigation surface for P/PPI's rules and process
model. It shows the exact atlas and pipeline roots, rule and transition counts,
and the commands that explain why context was injected or why a transition is
held. The dashboard is a read-only projection: effects still cross the UCM
Gateway and remote correspondence still crosses the courthouse.

P/PPI is the sovereign local project and process hub beside UCM. It keeps
multiple agent sessions aligned to the same project constitution, current
journal head, context rules, entrypoints, evidence, and version policy.

## Install on Windows

Run `install/INSTALL-PIPPI.ps1 -ExpectedRuntimeRoot <root>` using the runtime
manifest root from the external `UCM-v0.1-release.json`. Only the local
Governor label is required. MosaicID, DKN public key, GitHub account, and the
**external credential reference** may all be skipped and bound later. Never
paste a GitHub token, password, private key, or seed into P/PPI.

After installation, open **P/PPI** from the Start menu. The background loopback
service starts at user login. Use `pippi.cmd` for the same operations in scripts.

Open **P/PPI Setup** or run `PIPPI-INSTALLER.vbs` to inspect optional
capabilities in the native dark Mosaic interface. Clicking the rainbow sun
opens the product and authority explanation. `PIPPI-HEADLESS.vbs` writes the
same rooted plan without a terminal window. The recommended local profile
includes the core and UGK standards; SemCrys, Memory Vault, Courthouse, the
native UGK runtime, and enforced-host adapters remain optional and separately
verified. Planning never downloads, binds, or grants.

Before a new implementation step, create a work-selection JSON and run
`pippi.cmd work-selection-verify WORK-SELECTION.json`. Every step must bind one
acceptance case it directly closes. Shared infrastructure is refused unless an
exact blocker record demonstrates that same case cannot proceed without it;
finishing the prerequisite still requires a following direct closure step.
See `docs/PIPPI-WORK-UNIT-PROTOCOL.md`.

## Ownership

- P/PPI coordinates local projects and sessions.
- UCM Gateway authorizes and receipts local effects.
- AOK courthouse carries remote and cross-jurisdiction work orders.
- Memory Vault stores transtemporal bytes; P/PPI stores their causal roots.
- Crystal Network owns publication semantics.
- Mosaic UI and Mosaic Reader provide the native interface and documents.

The current package is `v0.1 r027`, `INFORMATION_ONLY`, authority effect
`NONE`, real A5 false, and G0 closed.

## Adaptive host and portable cold boot

Before a turn changes shells, crosses Windows and WSL, writes governed text,
packages an artifact, or makes a portability claim, run
`pippi environment-observe` and bind the execution-context root into the turn
opening. P/PPI probes the current filesystem's case behavior and removes the
probe bytes before returning the execution-context record. The portable claim
requires corresponding Windows-native and
WSL-native witnesses; `/mnt/c` is not the native WSL leg. See
`docs/PORTABILITY-DETERMINISM.md`.

P/PPI supports three honest host modes. `EXECUTABLE_LOCAL` uses a local hub
and filesystem/process adapter. `ARTIFACT_MEDIATED_WEB` exchanges rooted JSON
turn records and project capsules without claiming tool interception.
`NATIVE_ENFORCED` refuses unless a verified host adapter proves both tool and
visible-output interposition.

For each adaptive turn, use `turn-prepare`, `turn-report`, and
`turn-reconcile`. A missing prior close is surfaced when the next turn is
prepared; the agent must close or explicitly carry the unresolved report
before proceeding. Use `mediation-library` to inspect the exact context rules,
`interface-doctor` to check ABI/CLI parity, and `completion SHELL` to obtain a
deterministic shell completion record.

`tools/build_pippi_cold_boot.py` builds the portable cold boot. It carries the
exact UCM runtime, the public non-authoritative UGK adaptive practice profile,
the P/PPI mediation library and skill, and an optional project capsule. It
never carries private keys, tokens, passwords, seeds, or provider credentials.
The canonical UGK runtime remains an explicit external dependency for native
enforcement and UGK receipt certification.

Install from an extracted `UCM-v0.1-runtime.zip`. Its `MANIFEST.json` is the
exact installation boundary; the installer refuses a source tree, partial copy,
or changed member. The SDK and review artifacts remain separate and are not
installed into the local runtime.

Dark mode is the dashboard default. To attach earlier local P/PPI campaigns,
use `pippi.cmd migrate-discover` first, then `pippi.cmd migrate-import`. The hub
stores verified references and never rewrites imported journals. Working
workspaces and canonical revision stores remain separate fields.

The dashboard's **Reviews** workspace manages deterministic exact-artifact
review envelopes, local disposable replay, courthouse dispatch preparation,
bound return import, comparisons, and publication proposals. Applications own
their courts and verdict meaning; publication remains a separate human effect.
See `docs/PIPPI-REVIEW-ENVELOPES.md`.

Dashboard launch controls fail closed until a separately supplied host adapter
and operational-gateway policy are bound in `INTEGRATIONS.json`. Naming UCM or
the courthouse in documentation does not mean those external systems are
installed or available.


The loopback authentication key is fail-closed: P/PPI verifies a protected
current-user DACL on Windows or mode `0600` on POSIX whenever it reads the key.


# P/PPI native UI outline

This is the review baseline for the v0.1-r020 native dashboard. The interface
is a projection over verified hub records. It does not become a second state or
authority system.

## 1. Persistent shell

The top bar is present in every dashboard state:

1. **Mosaic rainbow sun.** A verified, keyboard-focusable image control in the
   upper-left corner. It opens the About P/PPI modal.
2. **Product identity.** `P/PPI` and `Constitutional project operations` use
   stable role names rather than build-stage names.
3. **Routing boundary.** A quiet line states that coordination is local,
   effects are governed, and remote correspondence belongs to the courthouse.
4. **Portfolio summary.** Project, session, held-project, and attention counts
   remain visible without opening a project.
5. **Gateway state.** A persistent badge says whether effect routes are bound;
   the Run group repeats the dependency when they are unavailable.

The bottom status line reports the latest local UI operation. It is transient
progress, never evidence or authority.

## 2. About P/PPI modal

Activating the rainbow sun opens an owned native modal. It repeats the mark and
shows:

- the full product name and exact public version / engineering revision;
- a plain-language purpose statement;
- the four core functions: rooted state, observable-agent mediation, governed
  routing, and portable history;
- the constitutional boundary: no authority grant, no replacement of native
  validation, no promotion of progress into evidence;
- the current standing and authority posture.

The modal has one unambiguous **Close** action. Opening and closing it creates
no hub journal event because it is explanatory navigation only.

## 3. Portfolio and session navigation

The default left rail has two linked regions:

- **Projects:** title plus a compact `version · adherence` status column.
- **Concurrent sessions:** session identity plus a compact `state · updated`
  status column for the
  selected project.

The user may persist sessions across the top instead. This changes the view,
not the project or journal. Sessions remain grouped under their project.

## 4. Project workspace

Every selected project begins with **Now**: a rooted status badge, a short
headline, the exact reason in plain language, and one read-only next-context
button. This projection uses the same `mosaic.ucm.pippi-project-brief.v0.1`
record returned to agents and the loopback service. Its priority order is holds,
session attention, stale or absent verification, review returns, release
blockers, qualification gaps, then ready work.

The **Reviews** tab is a first-class custody workspace. A compact review queue on
the left selects one exact record; the right-hand panel projects its lifecycle
badge, exact review ID, class, subject role, subject manifest, envelope, courthouse
work order, return, reported outcome, authority interpretation, and publication
state. Machine identifiers stay available in the detail while the queue uses a
readable label. Reported outcomes remain visibly attributed to the reviewer; P/PPI
does not translate them into authority.

Review actions are grouped by lifecycle rather than placed in the application
launcher:

- **Review:** verify the externally pinned envelope or run its bundled reviewer in
  a disposable workspace with live phase progress.
- **Correspond:** prepare a courthouse work order or import an exact returned
  archive. Remote transport remains courthouse-owned.
- **Decide:** compare two custody records or prepare a publication proposal.
  Publication remains held for explicit human authorization.

Actions that do not apply to the selected lifecycle state are disabled. A constant
boundary line reminds the operator that the application owns its courts, P/PPI owns
exact custody, and a review outcome does not authorize publication.

**Substance…** opens a native disclosure surface whose findings, severity counts,
limitations, reviewer identity, and evidence inventory are re-read from the exact
envelope and returned archive. The disclosure is a projection; it is not a second
review store.

**Import return…** uses the native operating-system file selector and then applies
the same archive SHA-256, review ID, envelope, contents, and return-root checks as
the CLI. A cancelled or refused selection changes no custody state.

**Publication…** collects an exact artifact SHA-256, a bounded set of publication
targets, and an optional public DKN namespace. Submission creates a held proposal
only. It does not contact a provider or authorize publication; Crystal Network
remains the publication owner and explicit human authorization remains required.

Local replay runs off the UI thread. The persistent progress drawer shows the
current `VERIFY → EXTRACT → RUN → SEAL` phase, elapsed time, and evidence
destination. The drawer is explicitly non-evidentiary; the sealed replay archive is
the evidence.

Six stable tabs project one exact project profile:

- **Overview:** adherence, proof, maturity, freshness, subject roots, mutable
  workspaces, canonical store, revision, archive, courthouse, and GitHub.
- **Sessions:** verified session references, integration mode, last activity,
  context, subject, and journal head.
- **Timeline:** separate archive, courthouse, operation, and session lanes.
- **Evidence:** project/profile roots plus execution holds, release blockers,
  and qualification gaps as distinct classes.
- **Reviews:** exact envelope, replay, courthouse-return, comparison, and
  publication-proposal custody.
- **Constitution:** version policy, credential boundary, effect routing,
  archival rule, mediation denominator, progress rule, and storage separation.

The mutable workspace, imported session source, and canonical revision store
must never collapse into one ambiguous path.

## 5. Common actions

The project action shelf is grouped by intent so the safest common path remains
visually primary without flattening execution, inspection, and governance into one
undifferentiated button grid:

- **Run:** Verify, then launch; Launch application; Verify only.
- **Inspect:** README; Docs; Files; GitHub.
- **Govern:** Context & constitution; Advanced.

Refresh is a portfolio-level action in the header rather than a project operation.
The groups are a view-layer projection only; command identities and effect routes do
not change.

The common action strip stays visible:

1. Launch application.
2. Launch verification.
3. Verify, then launch (primary).
4. Open GitHub.
5. Open the file tree.
6. Read README in Mosaic Reader.
7. Read another project document in Mosaic Reader.
8. Open the context and constitution projection.
9. Reveal advanced controls.
10. Refresh from verified hub state.

Effectful launches are journaled before and after dispatch. The dashboard never
bypasses the UCM Gateway or treats a command exit as an authority grant.

## 6. Progressive disclosure

**Advanced…** reveals low-frequency preferences and administration while the
common path stays uncluttered. The current r020 controls are:

- session navigation placement;
- abbreviated or full hash display;
- dark-theme variant.

Future archive recovery, courthouse submission, context-rule inspection,
credential references, and publication controls belong here and must retain
their own preflight and receipt steps.

## 7. Empty and exceptional states

- With no projects, the main region says **No projects registered**; it must not
  fabricate sample state. Project-specific actions are disabled and the view
  points to project registration and verified-reference discovery.
- Unbound roots and stores say `unbound`.
- Missing entrypoints refuse with typed errors.
- Holds, blockers, gaps, and attention remain separately visible.
- An unmediated observable channel keeps the integration `SIDECAR_PARTIAL`.

## 8. Responsive native layout

The dashboard supports two native layouts from one exact state projection:

- **Wide:** 1400 DIPs and above, with the full left rail, master/detail review
  workspace, and expanded action labels.
- **Compact:** down to the declared 1180 × 760-DIP minimum, with fitted table
  columns and shortened action labels. No action is removed.

When a user prefers top session navigation but the available height is below 860
DIPs, sessions remain in the left rail and the status line explains the temporary
compact-height realization. The preference itself is not rewritten. DPI changes
rerun the same layout function in device-independent units.

## 9. Human and agent synchronization

Humans see selected facts and context pathways; agents may inspect the exact
roots and records behind them. Both views derive from the same hub state. The UI
must keep these pairs aligned:

- concise status ↔ exact receipt or root;
- project card ↔ complete project profile;
- timeline row ↔ cited event/session root;
- held action ↔ typed reason and next resolvable step;
- progress message ↔ explicitly non-evidentiary display.

No UI summary may silently clear a hold, widen a capability, change a version,
or replace the canonical journal.

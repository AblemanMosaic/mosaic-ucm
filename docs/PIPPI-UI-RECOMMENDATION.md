# P/PPI native dashboard contract

P/PPI uses Mosaic UI's native Win32 realization. Dark mode (`signature-dark`)
is the default. The dashboard is a projection over rooted hub state; changing a
layout never changes project, session, journal, custody, or authority records.

The verified Mosaic rainbow-sun mark remains visible at the top left of the
dashboard. It is a keyboard-focusable **About P/PPI** control. Activating it
opens a native modal that repeats the mark and explains the product's purpose,
its UCM Gateway and courthouse routing boundary, its portable-journal role, and
its current non-authorizing posture. The modal is explanatory only: opening or
closing it creates no project event, effect receipt, or authority transition.

## Persistent project facts

Every project view keeps these facts visible:

- public version and engineering revision;
- last material activity and last verified time;
- current and verified subject roots, with derived freshness;
- adherence status, proof level, and operational maturity;
- execution holds, release blockers, and qualification gaps as separate lists;
- active session count, archive status, and courthouse status;
- working workspaces and the canonical revision store in separate sections;
- GitHub, application, verification, README, document, and file-tree entrypoints.

The dashboard never calls a records folder a canonical software store merely
because it contains evidence. An unbound canonical store stays visibly unbound.

## The Now projection

The selected project always exposes one deterministic, rooted summary before
the detailed records: current state, a plain-language headline, the exact
reason, and one safe next navigation context. Holds take precedence over stale
verification, session attention, review returns, blockers, advisory gaps, and
ready work. The same projection is returned by `pippi project-brief` and the
authenticated loopback `project-brief` request, so agents and humans cannot be
shown competing priorities from the same state. The suggested action changes a
dashboard tab only; it never dispatches an effect or closes an acceptance case.

## Progressive disclosure

The default view contains common project and inspection actions. **Advanced…**
reveals layout, hash-display, context-rule, archive, credential-reference,
export/recovery, and courthouse/publication controls. Raw credentials, private
keys, and authority grants are never dashboard fields.

## Concurrent sessions

Sessions are grouped under their project and shown as cards/table rows with
status, last activity, integration mode, exact source path, context root,
subject root, journal head, and event count. Users may place session navigation
in the left rail or across the top. The preference is stored in the hub, not in
a project workspace.

## Timelines

The timeline has separate lanes for:

- archive preparation, custody, reconstruction, restore, and supersession;
- courthouse draft, preflight, submission, routing, review, return, disposition,
  hold, close, and supersession;
- local operations and user launches;
- imported or active session references.

Each timeline row cites a receipt or session-reference root. Progress text is
not promoted into the timeline as evidence.

## Personal layout

The hub persists theme, density, session-navigation placement, default tab,
hash-display mode, pinned projects, pinned sessions, and visible project fields.
The default is dark, comfortable, left-navigation, overview, and abbreviated
hashes. Full roots remain available without changing the underlying records.

## Common path

1. Select a project.
2. Read **Now**: current state, reason, and recommended context.
3. Distinguish its working spaces from its canonical revision store.
4. Check adherence, freshness, holds, blockers, and gaps.
5. Inspect concurrent sessions or the archive/courthouse timeline.
6. Launch verification, application, or verification then application.
7. Open project documentation through Mosaic Reader.

Every user launch is journaled before and after dispatch. The dashboard itself
does not grant authority or bypass the UCM Gateway.

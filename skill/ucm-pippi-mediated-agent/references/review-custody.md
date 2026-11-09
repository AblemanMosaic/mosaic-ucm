# Review custody and publication boundary

Use this reference when Pippi packages, replays, dispatches, imports, compares,
or projects a review, or when it prepares a publication proposal.

## Ownership boundary

- The subject application owns its court cases, expected refusal codes,
  qualification semantics, and verdict contract.
- Pippi owns exact envelope custody, deterministic local replay, progress,
  courthouse correspondence records, return verification, journal events, and
  human-readable projections.
- A reviewer owns the returned findings and verdict. Pippi preserves and shows
  them; it does not strengthen, weaken, or reinterpret them.

## Required custody chain

1. **PACKAGED** — verify the closed envelope and its externally supplied
   SHA-256, then register the exact archived bytes.
2. **DISPATCH_PREPARED** — create a courthouse work order bound to the envelope
   root. This is preparation, not proof that a remote reviewer received it.
3. **RETURNED** — verify the return archive, review ID, original envelope hash,
   closed contents inventory, evidence contents root, and return root before
   storing the exact bytes.
4. **PUBLICATION_PROPOSED** — create a held plan bound to the intended artifact
   hash and destinations. Keep `publication_authorized` false.

Do not infer these states from a filename, a dashboard label, chat memory, a
progress event, or an unverified external report.

## Local and operator review

`review-run-local` should verify, extract to a disposable workspace, execute the
declared runner, seal evidence, and remove temporary files. It provides process
isolation; claim an OS sandbox only when separately established.

For user-operated adversarial review, prepare a double-click entry point that:

- verifies its own sealed operator kit before extraction;
- reports each phase or case with flushed progress;
- runs only in a disposable workspace;
- preserves a deterministic evidence archive beside the entry point;
- removes temporary material on PASS or HOLD; and
- pauses so the user can read the terminal result.

The agent should not execute that adversarial leg when the user has reserved it
for manual operation. A PASS remains builder/user-authored evidence unless the
review contract establishes an independent reviewer boundary.

## Projection and publication rules

- Read findings, limitations, evidence filenames, and the reported outcome from
  the verified return archive whenever they are displayed.
- Keep progress JSONL, UI layout, and pretty reports outside authority and
  evidence roots unless an explicit contract says otherwise.
- A file chooser selects a candidate archive; the exact verifier decides
  whether it can be imported.
- Responsive or alternate UI layouts must show the same authority facts and
  actions.
- A review outcome can support a publication proposal but cannot itself publish,
  grant authority, open G0, or make real A5 true. The publishing system and an
  explicit human decision remain separate.

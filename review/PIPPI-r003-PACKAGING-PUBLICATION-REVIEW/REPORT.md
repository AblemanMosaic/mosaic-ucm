# P/PPI r003 packaging and UCM publication review

**Disposition: HOLD_FOR_PACKAGING.** P/PPI's positive runtime paths pass, but
the current working tree is not an exact release candidate and must not replace
the published UCM artifact yet. This was a passive and positive-path review; no
adversarial testing was performed.

## What holds

- The installed and packaged `ucm-pippi-mediated-agent` skill copies are
  byte-identical and both pass the Codex skill validator.
- All 37 P/PPI positive tests pass under Python 3.12 when the temporary
  workspace is placed inside the permitted workspace.
- The `pippi` CLI imports from a staged wheel and exposes the r003 commands,
  including review-envelope custody and held publication proposals.
- The governed source/spec/docs/tools/tests/install/skill text contains no
  build-host absolute paths detected by the audit scan.
- No credential material was found. The credential-like test string is an
  intentional negative fixture.
- P/PPI preserves the required ceiling: `INFORMATION_ONLY`, authority effect
  `NONE`, real A5 false, and G0 closed.

## Findings

### PPUB-01 — MED — frozen identity is still r002

`SOURCE-MANIFEST.json` declares
`mosaic.ucm.pippi-r002-source-manifest.v0.1`. Sixteen listed members have
changed and nineteen current members are absent. `QUALIFICATION.json` declares
the r002 qualification and binds 30 tests, while the current positive suite has
37 tests. The r003 bytes therefore have no exact source root or qualification
receipt.

### PPUB-02 — MED — the wheel does not contain its native runtime closure

The wheel builds and its CLI help works, but it contains no `vendor`, `spec`,
`docs`, or packaged skill material. Calling the advertised dashboard from the
staged wheel fails with `ModuleNotFoundError: mosaic_ui`. The source installer
works around this by copying the repository's `vendor/mosaic-native` tree, so
the wheel and installer currently describe different runtime envelopes.

### PPUB-03 — MED — installer verification is only a presence check

`INSTALL-PIPPI.ps1` labels its first phase “Verifying source envelope,” but it
only checks that `src/ucm/pippi_global.py` and
`vendor/mosaic-native/mosaic_ui/win32.py` exist. It does not validate the source
manifest, member hashes, release identity, or a closed runtime inventory before
copying files into the user installation.

### PPUB-04 — LOW — this snapshot is not a standalone publication tree

The package name is `mosaic-ucm` version `0.1.0`, the same identity as the UCM
repository. Several inherited release documents refer to `release/` and build
tools that are absent here. Publishing this directory as a separate Python
project would collide with UCM and present incomplete release instructions.

### PPUB-05 — LOW — the P/PPI and UCM workspaces need an explicit delta merge

Relative to the current UCM workspace, this P/PPI snapshot has 243 P/PPI-only
paths while UCM has 171 paths absent here; two common files differ. This is a
substantial assembly boundary, not a safe directory overwrite. It needs a
closed, hash-bound integration delta and a rebuilt UCM qualification.

### PPUB-06 — INFO — review and working residue must stay outside runtime

The snapshot contains 82 review files (about 1.65 MB), UI captures, and local
empty test directories. These are useful qualification or review inputs, but
they should not enter the parsimonious runtime profile. Review evidence should
ship separately from the runtime and SDK.

## Recommended release architecture

1. Use the canonical UCM repository as the publication base. Integrate P/PPI as
   a hash-bound successor delta rather than publishing this working directory
   independently.
2. Define three closed artifacts:
   - **runtime** — UCM/Pippi executable packages, required contracts, the
     mediated-agent skill, and the minimal Mosaic UI runtime/assets;
   - **SDK/source** — runtime plus tests, authoring schemas, tools, examples,
     and installer sources;
   - **review** — qualification source, work order, receipts, captures, and
     reviewer/operator evidence.
3. Either make the wheel contain the complete P/PPI runtime closure or stop
   advertising the dashboard in the wheel and make the verified UCM runtime
   archive the sole native installation artifact. The preferred result is one
   UCM distribution with both headless and native P/PPI entry points.
4. Replace installer presence checks with exact release verification. Stage to
   a new revision directory, verify every destination member, then switch the
   active launcher. Preserve the previous revision for rollback.
5. Regenerate an r003 source manifest, exact test identity list, qualification
   receipt, runtime/SDK manifests, and release receipt from a clean extraction.
   Run installed-artifact checks for CLI, dashboard, service, review replay,
   skill loading, and uninstall/data-preservation behavior.
6. Build each artifact twice, compare bytes, prepare the user's operator court,
   and request independent review at that meaningful boundary. Only then
   replace the public UCM commit and release assets.

## Publication conclusion

P/PPI is functionally ready to enter the UCM release-consolidation batch. It is
not yet ready to publish. The remaining work is release identity, runtime
closure, installer custody, and deterministic UCM integration rather than a
redesign of the P/PPI happy path.

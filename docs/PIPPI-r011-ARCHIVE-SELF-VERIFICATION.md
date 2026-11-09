# P/PPI r011 archive self-verification repair

P/PPI r011 directly closes `PIPPI-R011-ARCHIVE-SELF-VERIFY`: the standalone
`VERIFY.py` bundled in the SDK must accept each canonical archive emitted by
`tools/build_release.py`.

The predecessor verifier implemented the older stored-archive contract only.
The public release builder emits canonical deflated archives with the
`mosaic.ucm.artifact-manifest.v0.1` manifest. The verifier now recognizes both
contracts, recomputes the applicable manifest and member roots, rebuilds the
archive with its declared canonical compression policy, and requires byte
identity.

The direct closure check is
`test_sdk_bundled_verifier_accepts_all_canonical_release_archives`. It extracts
the verifier from the newly built SDK and uses that exact copy to verify the
runtime, SDK, review, and lineage archives. This is positive qualification, not
an independent adversarial verdict.

The public version remains v0.1. The engineering revision is r011. Standing is
`INFORMATION_ONLY`, authority effect is `NONE`, real A5 is false, and G0 is
closed.

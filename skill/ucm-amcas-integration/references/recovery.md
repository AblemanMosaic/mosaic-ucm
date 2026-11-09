# Recovery

1. Preserve the prior workspace, journal archive, stdout, stderr, exit code,
   and any external effect evidence.
2. Verify the full journal chain and recover only its HEAD projection.
3. Do not repeat an operation with uncertain effects. Reconcile the existing
   attempt through a witness or diagnostic first.
4. Use a new operation ID for a newly authorized attempt; retain the earlier
   interruption and recovery records.
5. Export a new canonical journal archive and return both old and new archive
   roots when the recovery changes campaign state.
6. When a generator or packager has no terminal record, inspect existing
   journal and output bytes without rerunning it. Return `INCOMPLETE_RETURN`
   with exact observed and missing artifacts. Retry only after a new explicit
   direction and with a bounded event identity.

No recovery step grants authority or relaxes CM1.

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

No recovery step grants authority or relaxes CM1.

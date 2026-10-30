# Stage I1 application return

Stage I1 is the first portable integration checkpoint. Its deterministic ZIP
contains the subject binding, AMCAS contract, compiled IR, control-plane
disposition, shadow correspondence court, capability/effect inventory, content
graph, canonical journal, session report, THR/CAS manifest, and cross-record
index.

The THR/CAS manifest keeps five claims separate: `H_s` binds exact state bytes,
`H_c` binds admissibility and governance, `H_m` binds normalized meaning, `H_j`
binds locality and jurisdiction, and `H_r` binds receipt identity. `h_body`
binds the whole envelope. No one commitment may be used as evidence for
another. Legacy v0.1 returns may be deterministically wrapped in this envelope;
that operation preserves their original status and grants no authority.

`integration-verify-stage1` refuses incomplete sets, mutable or zero-root
subjects, stale compilation, control-plane mismatches, altered court rows,
noncanonical journals, index mismatches, and authority expansion. Passing means
internally coherent, claim-separated, and ready for review; it does not mean
admitted, composed, or deployed.

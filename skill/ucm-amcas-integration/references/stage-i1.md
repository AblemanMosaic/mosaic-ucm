# Stage I1 return

Return the deterministic `APPLICATION_STAGE_I1_RETURN` archive. It contains
exactly the subject binding, AMCAS v0.2 contract and IR, control-plane
disposition, correspondence court, capability/effect inventory, content graph,
canonical journal, session report, and rooted index.

The current v0.2 envelope also contains `THR-CAS-MANIFEST.json`. Its five
commitments separate exact bytes, governance, meaning, locality, and receipt
identity. A deterministic upgrade of a verified v0.1 return changes only its
envelope. It does not change the subject, status, limitations, or authority.

The verifier recompiles the contract, rechecks control-plane ownership,
recomputes the court, and refuses unbound subjects or widened authority. A
bundle may be `READY_FOR_REVIEW` or `HOLD_FOR_REPAIR`; it never admits production.

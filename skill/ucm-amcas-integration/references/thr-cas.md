# THR and content-addressed custody

Use the canonical Three Hash Rule projection plus receipt and body commitments:

- `H_s` — exact state: paths and byte hashes of the Stage I1 records.
- `H_c` — admissibility and governance: control-plane disposition,
  correspondence result, Stage I1 status, and authority ceiling.
- `H_m` — meaning: subject, AMCAS contract, compiled IR, inventory, and content
  graph roots.
- `H_j` — locality: application, subject, identity/jurisdiction binding status,
  and gate namespace.
- `H_r` — receipt identity: canonical journal bytes and session report.
- `h_body` — integrity of the complete THR/CAS envelope.

Recompute every commitment from current bytes. Never accept a stored hash as
its own proof. Never substitute `H_s` for semantic identity, `H_m` for
admissibility, or `H_j` for permission. Content-addressed storage establishes
exact custody only; the stored object must still pass its typed verifier.

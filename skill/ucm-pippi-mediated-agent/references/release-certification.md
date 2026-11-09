# Canonical archive and publication certification

Use two identities and never collapse them.

1. The archive's internal `META/STATE-MANIFEST.json` inventories the logical
   payload members, excluding `META/` and the container manifest.
2. `META/THR-MANIFEST.json` keeps state, admissibility, meaning, locality, and
   receipt commitments separate as `H_s`, `H_c`, `H_m`, `H_j`, and `H_r`.
3. `META/DKN-BINDING.json` is either externally bound or explicitly
   `DECLARED_UNBOUND`. Identity and namespace never grant authority.
4. `META/SELF-CERTIFICATE.json` signs the THR body and DKN binding when an
   external publisher key is supplied. `READY_FOR_EXTERNAL_DKN_CERTIFICATION`
   is not a self-certified state.
5. The SHA-256 of the complete ZIP is an external transport commitment. Do not
   place it inside the same ZIP or bind storage URLs into semantic identity.
6. Storage locators are replaceable projections over the content address.

Preserve the public version by default. Use the next engineering revision for
successor outputs. A public-version transition requires a signed external
approval bound to the exact transition operation. Publication remains a
separate human-authorized effect even after self-certification passes.

The publication surface must open the exact local artifact, verify its external
SHA-256, manifest, payload denominator, and all four META records, then derive
the THR and certificate fields. Never accept a caller-asserted certificate
status or root. The artifact path is an input only and must not enter the
storage-agnostic publication plan.

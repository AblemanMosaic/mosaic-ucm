# P/PPI release certification

P/PPI treats a canonical release as a logical payload, a constitutional
interpretation, and a transport container with different identities.

- `H_s` binds the logical payload inventory.
- `H_c` binds source, release identity, policy, and authority ceiling.
- `H_m` binds the product, artifact role, public version, and revision.
- `H_j` binds the DKN namespace and external identity status.
- `H_r` binds the receipt classes expected outside the archive.
- `h_body` binds the complete THR record.
- The complete ZIP SHA-256 binds exact delivered bytes and remains external.

The r024 packages are intentionally `DECLARED_UNBOUND` until the Governor
supplies an external MosaicID/DKN public identity and signature. They are ready
for self-certification but do not claim it. A storage URL can change without
changing any of these constitutional commitments.

Publication planning never accepts certificate status as an argument. It opens
the exact local archive, checks the independently supplied ZIP SHA-256, closed
manifest, member bytes, logical payload denominator, and all four META records,
then derives the certificate status and roots. A requested DKN namespace must
equal the verified embedded namespace and the certificate must be
`PASS_SELF_CERTIFIED`; otherwise the held plan refuses. The local path is not
written into the plan.

P/PPI preserves `v0.1` by default. Work loops produce engineering revisions.
A public-version change requires a signed external approval over the exact
version-transition operation; chat wording, filenames, tags, and build scripts
cannot authorize that transition.


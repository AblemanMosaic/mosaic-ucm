# P/PPI transtemporal archiving

P/PPI keeps active software small without losing its causal history. Historical
review returns, operator evidence, and session handoffs are admitted once to a
content-addressed backend. Project journals retain a rooted reference instead
of another copy of the bytes.

## What is enforced

1. **Runtime and SDK are reference-only.** Their build refuses any member under
   the canonical custody prefixes. This is a release invariant, not a packaging
   convention.
2. **Review custody is explicit.** A review artifact declares either
   `REFERENCE_ONLY` or `SELF_CONTAINED_CUSTODY`. The latter must contain the
   complete fixed denominator of historical custody files.
3. **Each reference separates four commitments.** `state_root` is the exact
   object SHA-256; `semantic_root` states what it means; `metadata_root` binds
   descriptive and routing facts; `governance_root` binds policy and authority
   context. The reference has its own whole-record root.
4. **Availability is checked before use.** A missing object produces
   `HOLD_FOR_ARCHIVE_AVAILABILITY`. No journal reference is treated as the
   underlying evidence.
5. **Deduplication is observable.** Availability receipts report logical bytes,
   unique physical bytes, and bytes removed by content-addressed reuse.
6. **Reconstruction is exact.** Materialization resolves the object by SHA-256,
   verifies it, and then reconstructs the requested envelope. A locator is a
   retrieval hint; the content hash is the identity.

The default backend is the user-level local content store. Mosaic Memory Vault
is the preferred transtemporal backend when available. Backend choice changes
locality, not semantic identity or authority.

## Canonical release envelope

Every r024 release archive carries four ordinary canonical JSON members under
`META/`: `STATE-MANIFEST.json`, `THR-MANIFEST.json`, `DKN-BINDING.json`, and
`SELF-CERTIFICATE.json`. The state manifest inventories logical payload bytes;
the THR manifest separates state, admissibility, meaning, locality, and receipt
commitments; the DKN binding records namespace locality; and the certificate
binds those records without binding a storage provider.

The complete ZIP SHA-256 stays outside the ZIP as its transport identity. This
avoids self-reference and lets the same governed payload remain recognizable
when a future canonical container is reconstructed. An unbound DKN record is
reported as `READY_FOR_EXTERNAL_DKN_CERTIFICATION`, never as self-certified.
Publication under a DKN namespace requires a verified external signature and a
separate explicit human publication authorization.

## Release profiles

| Profile | Historical bytes | Intended use |
| --- | --- | --- |
| Runtime | Refused | Operate UCM and P/PPI |
| SDK | Refused | Build and integrate applications |
| Review, reference-only | Refused | Small handoff where the backend is available |
| Review, self-contained | Required complete set | Offline custody or independent review |

This is why the 42 MB of prior ecosystem returns belongs in the review custody
artifact or the transtemporal store, and not in every runtime or SDK copy.


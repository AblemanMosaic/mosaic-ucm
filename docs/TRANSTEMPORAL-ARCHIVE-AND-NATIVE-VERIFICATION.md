# Transtemporal Archive and Native Verification

## Purpose

P/PPI projects often accumulate many archives whose contents differ only in a
small set of files. The transtemporal archive represents that history as one
content-addressed object store plus immutable revision manifests. A revision is
still reconstructable byte for byte. Deduplication changes storage, not the
meaning or identity of the governed state.

## Constitutional boundary

- **BLAKE3-256** is the primary content address for performance and modern
  tree-hashing behavior.
- **SHA-256** is carried for interoperability, existing UCM custody, publication
  receipts, and a small independent C verifier.
- A stable `F000000001`-style identifier names a logical file across revisions
  while the path and digest remain independently visible.
- THR commits state (`H_s`), semantics (`H_m`), governance (`H_c`),
  jurisdiction (`H_j`), and the ingest receipt (`H_r`) separately.
- DKN defaults to namespace `mosaic.ucm.v0.1`, status `DECLARED_UNBOUND`.
  A namespace string is not a signature and does not self-certify an archive.
- Progress output, compression ratios, and a P/PPI plan are not evidence of
  reconstruction. `archive-verify` and a complete materialization are.

## P/PPI routes

```text
pippi archive-ingest SOURCE REPOSITORY r001 SEMANTIC_ROOT GOVERNANCE_ROOT JURISDICTION_ROOT
pippi archive-verify REPOSITORY r001
pippi archive-materialize REPOSITORY r001 EMPTY_DESTINATION
pippi archive-diff REPOSITORY r001 r002
pippi archive-report REPOSITORY
pippi archive-semcrys-plan REPOSITORY r001
pippi archive-native-manifest REPOSITORY r001 NATIVE-MANIFEST.tsv
```

`archive-ingest`, `archive-materialize`, and `archive-native-manifest` are
explicit write operations. They never delete source material. `archive-report`
is a read-only projection and never recommends deletion by itself.

## SemCrys and Memory Vault

These packs are optional. With no exact SemCrys manifest root and Memory Vault
binding root, P/PPI returns `HELD_OPTIONAL_PACK_UNBOUND`. With both roots it
returns a pure `READY_FOR_EXTERNAL_COMPRESSION` plan. The external realization
must return a receipt, restore bytes into a disposable location, and pass the
original dual-digest revision verifier before any redundant source is eligible
for a separately authorized retention decision.

SemCrys compression does not change the revision manifest, THR state root, DKN
binding, or file identifiers. Secret material and credentials are outside the
portable archive.

## Native C slice

`native/ucm_archive_verify.c` is a dependency-free C17 verifier for the emitted
line protocol. Build it with:

```text
gcc -std=c17 -O2 -Wall -Wextra -Wpedantic -Werror native/ucm_archive_verify.c -o ucm-archive-verify
```

`pippi archive-native-manifest` writes the manifest and a sibling
`.binding.json` receipt. Run the verifier with the receipt's independent pins:

`ucm-archive-verify NATIVE-MANIFEST.tsv MATERIALIZED_ROOT EXPECTED_MANIFEST_ROOT EXPECTED_ROWS_ROOT EXPECTED_MEMBER_COUNT`.

The manifest-root label, row-stream digest, and member denominator must all
match the external receipt. A truncated manifest cannot pass by resealing its
own header and trailer.
The external manifest-root pin, nonzero declared member count, exact trailer
count, and row-stream digest prevent a header-only or truncated projection from
passing. It checks
portable paths, sizes, and SHA-256 for every file. The reference Python verifier
is still required for BLAKE3 objects, manifest roots, THR, and DKN. This narrow
trust boundary is deliberate: native acceleration grows only when a defined
acceptance case and cross-implementation vectors justify it.

## Retention procedure

1. Ingest every source/release tree without deleting anything.
2. Verify every revision and materialize representative revisions elsewhere.
3. Compare materialized roots with the original source manifests.
4. Bind any SemCrys realization and test restoration.
5. Export the archive, THR records, DKN status, and external whole-archive
   SHA-256/BLAKE3 receipt.
6. Produce a human-reviewed retention proposal identifying exact originals.
7. Delete only under a separate, explicit authorization with rollback custody.

The r031 program performs steps 1–5 on a bounded UCM fixture and produces only a
dry-run report for step 6. It performs no deletion.

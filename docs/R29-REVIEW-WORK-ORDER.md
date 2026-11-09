# UCM v0.1 r029 collaboration-integrity review work order

Review the exact r029 subject identified by the transport manifest. Begin with
full 64-character identity preflight. Refuse on any mismatch. Keep all results
`INFORMATION_ONLY`, authority effect `NONE`, real A5 false, and G0 closed.

## Tier 0 and Tier 2

1. Verify the transport, release, four release archives, qualification receipt,
   cold boot, portability witnesses, program records, and operator kit without
   importing subject code during custody verification.
2. Reconstitute the complete source from SDK, review, and lineage partitions.
3. Confirm the r028 predecessor identity and qualification are byte exact.
4. Confirm the carried r028 independent return and user-run operator evidence
   against their provenance records without treating them as r029 evidence.
5. Replay the exact qualification on Python 3.12 and 3.13 and rebuild all
   release artifacts and the cold boot byte identically.
6. Confirm signer identity is derived from the verifying Ed25519 key for change,
   publication, and retrieval records.
7. Confirm retrieval opens and hashes the actual artifact and validates the
   signed publication receipt.
8. Confirm CCP-required transitions consume and validate the complete decision,
   use snapshot, evidence snapshot, jurisdiction, perimeter, correspondence,
   and independently supplied expected anchors.
9. Confirm credential sealing accepts no caller salt or nonce and local writes
   use exclusive staging with link/reparse refusal and private-file checks.
10. Confirm only `PUBLISHED` is terminal and the cold boot contains the complete
    Pippi skill, including every reference.
11. Confirm CLI, ABI, capability registry, completions, documentation, profiles,
    and generated contracts agree.

## Tier 1

Run the sealed double-click operator kit only when adversarial execution is
authorized by the reviewer or operator. Preserve its exact evidence ZIP. The
builder did not run it. Its cases cover identity/key substitution, publication
and retrieval tampering, CCP decision laundering, credential staging, cold-boot
skill closure, interface parity, and the authority ceiling.

No review result grants publication, deployment, provider access, credentials,
capabilities, or effect authority.

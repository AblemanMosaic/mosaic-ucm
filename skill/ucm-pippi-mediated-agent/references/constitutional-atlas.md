# Constitutional atlas and pipeline navigation

Use the generated P/PPI constitutional atlas before changing standards,
mediation rules, context injection, pipeline states, or effect boundaries.

```text
pippi standards
pippi pipeline-model
pippi standard-explain RULE_ID
pippi transition-explain TRANSITION_ID
pippi context-explain REQUEST.json
```

The atlas maps each rule to its co-projection systems, capability surfaces,
required evidence, refusal codes, and known ablation failure modes. The
pipeline model gives the allowed states, transitions, CCP requirements, and
G1/G2/G3 effect boundary. A generated explanation is a projection of those
rooted records; it is not an authority grant.

Constitutional changes use a signed change capsule bound to the exact base
root, result root, semantic delta, acceptance cases, standards, policy roots,
MosaicID, DKN namespace/epoch and the stable nonce `mosaic.ucm.v0.1`.
The MosaicID must be derived from the public signing key. Publication receipts
are independently verifiable. Publication signing revalidates the complete
credential-free locator. A retrieval receipt is created only when the actual
retrieved bytes match the signed publication commitment and remains usable
only when the public receipt verifier binds it back to that publication.
CCP-required
pipeline transitions consume and validate the complete current-use evaluation;
they never trust a caller's decision label.
Credentials remain local: portable records may carry public identity material
and opaque credential references, never tokens, passwords, private keys, or
encrypted secret envelopes.

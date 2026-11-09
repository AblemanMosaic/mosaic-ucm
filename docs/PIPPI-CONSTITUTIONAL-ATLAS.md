# P/PPI constitutional atlas and collaboration

P/PPI has two related maps. The **constitutional standards atlas** tells a
human or agent which rules apply, what each rule protects, which UCM surfaces
implement it, what evidence it needs, and what failure tends to appear when
the rule is removed. The **pipeline model** tells them where a project is now,
which transition is proposed, which standards govern that transition, whether
CCP must decide current-use admissibility, and which receipt gate applies.

These maps preserve co-projections. AMCAS, UGK, CCP, THR, DKN, Realization
Space, the Dependency and Evidence Graph, P/PPI, and the Operational Gateway
overlap usefully without becoming synonyms. Equal bytes do not establish equal
semantics, identity, governance, evidence, or authority.

## Common path

1. `pippi standards` lists the complete rule denominator and co-projections.
2. `pippi pipeline-model` shows states and allowed transitions.
3. `pippi standard-explain RULE_ID` explains when a rule is injected and what
   it prevents.
4. `pippi transition-explain TRANSITION_ID` explains the next gate.
5. `pippi context-explain REQUEST.json` shows the exact scenario, variables,
   triggered rules, explicit additions, and resulting context root.
6. A collaborator imports a MosaicID public passport and creates a DKN binding
   with the stable nonce `mosaic.ucm.v0.1`.
7. A signed constitutional change capsule binds the predecessor, result,
   changed objects, acceptance cases, standards, policy packs, identity, DKN
   namespace, epoch, and revision. The MosaicID is derived from the Ed25519
   public key that verifies the signature; a caller cannot merely name an
   unrelated identity. It remains a proposal until admitted.
8. Storage publication and retrieval receipts bind the same artifact hash to
   a provider-neutral locator. Retrieval opens and hashes the actual artifact,
   validates the signed publication receipt, and refuses any mismatch. Storage
   never becomes identity or authority.
9. A transition marked `ccp_current_use: REQUIRED` accepts the complete CCP
   evaluation envelope. P/PPI validates the real decision and its snapshots,
   anchors, jurisdiction, enforcement perimeter, and correspondence; a caller
   supplied `ADMIT` string cannot make a transition ready.

## Credential boundary

The generic ABI handles only opaque credential references. A trusted local
host may encrypt secret bytes with scrypt and AES-256-GCM and store the
envelope under a protected per-user file. Secret bytes, passphrases, provider
tokens, and private keys are forbidden in project journals, capsules, change
archives, CLI arguments, portable cold boots, and courthouse submissions.
SemCrys can encode semantic material; it is not encryption and never replaces
credential custody.

## Collaboration and storage

A collaborator needs only their public MosaicID passport in a portable
package. Possession proof and signing remain separate ceremonies. GitHub,
MEGA, SFTP, WebDAV, or ordinary HTTPS can carry identical CCP-compatible
manifests; their URLs and provider receipts are locators and custody evidence.
They do not define the artifact, signer, interpretation, or governing rules.

All surfaces remain `INFORMATION_ONLY`, have authority effect `NONE`, keep
real A5 false, and keep G0 closed. Effectful provider operations still require
the established gateway and external authorization.

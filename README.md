# Universal Constitutional Machine (UCM) v0.1

## Operational gateway successor

The canonical Stage I4 operational surface is now a **receipt-mediated gateway**.
UCM validates a bounded external permit, durably records G1 authorization and
dispatch intent, and then validates executor-signed dispatch and terminal
receipts. UCM does not select, install, or impersonate an executor. No AOK
HeadlessRunner, capability lattice, or adapter is required by this release.

Start with [docs/OPERATIONAL-GATEWAY.md](docs/OPERATIONAL-GATEWAY.md). Humans
and agents use the same `operational-invoke` CLI and `ucm.invoke` ABI. Every
external effect follows this order:

1. verify the issuer, permit, current revocation registry, identity/session,
   jurisdiction, effects, budget, rollback root, generation, and freshness;
2. append authorization, G1, and dispatch-intent records before any effect;
3. let an independently chosen executor act with the pinned idempotency key;
4. record its signed dispatch and terminal receipts;
5. derive G2, G3, proof obligations, THR commitments, and a portable archive.

The JSONL progress stream and its compact summary are nonsemantic. The journal,
receipts, proof bundle, THR manifest, and archive are semantic custody records.

## AMCAS integration workbench successor

This v0.1 release composes UCM into a portable application
integration pipeline. It adds executable AMCAS and CM1/CM2 contracts, durable
MosaicID sessions, G1 Sentinel → G2 Witness → G3 Diagnostic receipts, a
hash-chained integration journal, application kits, and separate canonical
software and journal archives. Begin with [AGENT-ACCESS.md](AGENT-ACCESS.md) or
[the workbench guide](docs/AMCAS-INTEGRATION-WORKBENCH.md).

Pipeline product work and Mosaic ecosystem migration are separate governed
tracks. The reusable pipeline may be released to other computers while the
seven-application portfolio continues through shadow integration. See
[the two-track roadmap](docs/TWO-TRACK-ROADMAP.md).

The current successor also implements [Stage I4 work 1–3](docs/STAGE-I4-WORK-1-3.md)
under the v0.2 exact-evidence contract:
review-bound eligibility, an exact effect-membrane run contract, and a
G1/G2/G3 observation contract. These are preparation and evidence surfaces.
They do not contact or execute an application and cannot turn a Stage I3 plan
into permission.

The portable agentic-adaptation sidecar is built with
`tools/build_agentic_adaptation_sidecar.py`. It is a slim companion to the UCM
core: it verifies exact core registries, carries agent/human orientation,
skills, schemas, and templates, and forwards integration work into the one UCM
implementation rather than copying constitutional execution machinery.

This operational-gateway release replaces the earlier public v0.1 candidate.
Its exact cold-boot subject completed the builder qualification and the sealed
operator Tier 1 court. Those results are engineering evidence rather than an
authority grant: the release remains `INFORMATION_ONLY`, with authority effect
`NONE`, real A5 false, and G0 closed.

The consolidated c3 operational surface is documented in
[`docs/STAGE-I4-C3-OPERATIONAL-SURFACE.md`](docs/STAGE-I4-C3-OPERATIONAL-SURFACE.md).
It binds trusted review provenance, full relation dependencies, operation
state, the external AOK HeadlessRunner, and shared qualification semantics.
No native runner is bundled or emulated: absence produces a typed refusal.

The C2 successor adds exact subject classification, explicit native
control-plane disposition, shadow native/UCM correspondence courts, AMCAS v0.2
semantic/effect/identity/jurisdiction boundaries, namespaced integration gates,
a fixed-denominator portfolio journal, a deterministic THR-separated Stage I1 return,
bundle. It retains the C1 source as its frozen predecessor and does not replace
application-native semantics or effect execution without equivalence evidence.

UCM is Ableman Mosaic's portable substrate for deterministic constitutional computation. It gives humans and agents one coherent way to describe intent, preserve obligations through compilation, verify bounded proofs, select courts, maintain custody, explain results, and move exact artifacts between environments.

This repository is the slim public v0.1 review candidate. It contains the active runtime, stable agent interfaces, contracts, examples, and public conformance tests. Frozen predecessor transports and review archives are intentionally kept out of the runtime and SDK; their hashes and custody records are listed under [`audit/`](audit/README.md), and a separate complete audit archive can be built when historical bytes are supplied.

## Start here

```powershell
python tools/ucm.py orient
python tools/ucm.py capabilities
python tools/ucm.py validate-amcas examples/amcas/portable-agent.integration.json
python tools/ucm.py compile-amcas examples/amcas/portable-agent.integration.json
python tools/ucm.py validate-realization examples/realization/portable-agent-environment.json
python tools/ucm.py check-realization examples/realization/portable-agent-environment.json examples/realization/portable-agent-environment.configuration.json
python -m unittest discover -s tests -v
```

Stage I4 preparation begins with `stage4-derive-eligibility`. It consumes the
exact review archive bytes and derives the verdict and reviewed subject from
those bytes. A hash or verdict string by itself is insufficient. A run contract
can be built only after an exact qualified Stage I3 review and clearance of all
plan holds. Even then, the contract records `execution_authorized: false`; a
separate authority envelope is required before application contact.

New integrations use the anchored Stage I4 surface documented in
[`docs/STAGE-I4-ANCHORED-OPERATION.md`](docs/STAGE-I4-ANCHORED-OPERATION.md).
Its role-named commands require an external trust-anchor root, derive preflight
from the whole sealed contract, validate complete G1/G2/G3 receipt bodies, and
store those bodies in durable operation state. The current authority policy can
only refuse; it cannot be changed into permission by a caller flag. Earlier
Stage I4 commands remain labeled compatibility-only.

For application integration, continue with the command sequence in
[`docs/AMCAS-INTEGRATION-WORKBENCH.md`](docs/AMCAS-INTEGRATION-WORKBENCH.md).

Runtime orientation and contract checks use only the Python standard library. The complete developer suite supports Python 3.12 and 3.13 and requires `pip` plus `setuptools` for its clean-wheel installation test; it refuses that test when the host lacks the build tool instead of silently skipping it.

The first command returns the same machine-readable orientation agents receive. The realization contract is the conceptual interface: it describes what must remain invariant, what may vary, how a valid implementation is selected, and what evidence must be returned. Direct capability surfaces expose the actual proof, project, custody, workbench, and integration operations.

- Humans: [`docs/HUMAN-START.md`](docs/HUMAN-START.md)
- Agents: [`docs/AGENT-START.md`](docs/AGENT-START.md)
- Architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Capability surfaces: [`docs/CAPABILITY-SURFACES.md`](docs/CAPABILITY-SURFACES.md)
- Realization contracts: [`docs/REALIZATION-SPACE.md`](docs/REALIZATION-SPACE.md)
- UCL, Tessera, and proof: [`docs/LANGUAGES-AND-PROOF.md`](docs/LANGUAGES-AND-PROOF.md)
- Application integration: [`docs/APPLICATION-INTEGRATION.md`](docs/APPLICATION-INTEGRATION.md)
- Authority ceiling: [`docs/AUTHORITY-CEILING.md`](docs/AUTHORITY-CEILING.md)

## Stable system names

The public architecture is named by role, not by the build batch in which a subsystem appeared:

1. Constitutional Core
2. UCL Language System
3. Tessera Compilation System
4. Native Proof Kernel
5. Realization Space Engine
6. Court Execution Engine
7. Qualification Control Plane
8. Custody and Federation System
9. Agent Workbench
10. Project Intelligence System
11. Autonomous Project Manager
12. Portable Bootstrap System
13. Application Integration Gateway
14. AMCAS Integration Compiler
15. MosaicID Session System
16. Integration Journal System

The `uclop` and `uclsh` packages preserve the frozen predecessor implementation plus a closed, declared v0.1 repair delta. Build-era names may remain in frozen preimages and the audit record; they are not public architectural identities.

## Assurance boundary

The public tests cover the stable facade, realization semantics, installed runtime resources, deterministic packaging, and release verification. The much larger predecessor qualification is bound by hash and can be replayed only with the separately held frozen c4 workspace. Its archives are not embedded in this repository.

The predecessor review of the first published commit returned `HOLD_FOR_REPAIR`; its exact hashes and dispositions are recorded under [`review/`](review/README.md). The current source must earn a new independent result. “Review candidate” does not mean independently recommended, admitted, or authorized.

The current builder qualification receipt is [`release/UCM-v0.1-QUALIFICATION.json`](release/UCM-v0.1-QUALIFICATION.json). It binds the public source, exact test identities, declared compatibility delta, frozen predecessor custody, the reproducible public-lineage release root, the separate complete-audit release root, and the shared runtime and SDK artifacts. Its `PASS` is builder evidence pending independent review.

## Standing

This v0.1 repository is an engineering release candidate for review and integration. It is `INFORMATION_ONLY`, has `authority_effect: NONE`, does not bind real A5, and keeps G0 closed. It creates no identities, admits no deployment target, and grants no network, publication, or production authority.

The package version remains `0.1.0` while this public candidate is repaired in place. The exact candidate identity is its source-manifest root and Git commit. The `v0.1.0` tag is reserved for the exact commit that completes the terminal independent review; earlier commits do not share that release identity merely because they use the same human-readable version.

Copyright 2026 Ableman Mosaic. Licensed under the Apache License 2.0.

`CANONICAL_SOFTWARE` is the installable runtime. `QUALIFICATION_SOURCE` is the
larger exact source, test, court, and build-input closure. Neither role implies
the other, and review material identifies both explicitly.

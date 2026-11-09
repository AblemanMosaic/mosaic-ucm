# CCP source binding and point-of-use admissibility

## Purpose

Revision r015 applies the present-admissibility answer at the actual
P/PPI–Courthouse submission boundary. See
[CCP-COURTHOUSE-BOUNDARY.md](CCP-COURTHOUSE-BOUNDARY.md) for the admission
envelope, required G1 roots, human status projection, and the explicit split
between UCM admissibility and external Courthouse authority.

The CCP-JM r001 packet is a source-bound construction program for a future
jurisdiction and point-of-use admissibility system. UCM r014 preserves that
program as exact input and projects its complete planning denominator into
native P/PPI records. The projection answers a narrow first question: **what
must remain present and distinct before UCM can truthfully ask “Can I use this
now?”**

The exact source archive is
`qualification/inputs/ccp-jm/CCP_JM_PIPELINE_v0_1_r001.zip`, SHA-256
`9a38419d655b9306c7216554081a6c869e12c0dcab1e08b961b8d645115e985e`.
It is carried in the SDK/source envelope and is intentionally absent from the
runtime payload. Runtime users receive the compact generated records, not a
second embedded source distribution.

## What is preserved

`tools/build_ccp_native_program.py` opens the packet as data without importing
or invoking packet code. It verifies the outer pin, closed packet manifest,
every member hash, and the exact denominators before producing records:

- 6 batches;
- 13 stages;
- 32 requirements;
- 116 product acceptance specifications; and
- 0 executed product acceptance cases.

The complete source stage, requirement, and acceptance rows remain in
`program/ccp-admissibility-r014/NATIVE-PROGRAM.json`. A deterministic milestone
projection adds P/PPI identifiers without dropping, broadening, or declaring
any source obligation complete.

Run the non-mutating check with:

```powershell
python tools/build_ccp_native_program.py --check
```

`--write` regenerates the governed records after an intentional source or UCM
interface change. A changed archive pin, member set, obligation denominator, or
record root refuses generation.

## Record set

| Record | Role |
| --- | --- |
| `SOURCE-INVENTORY.json` | Exact archive and 45-member custody inventory. |
| `NATIVE-PROGRAM.json` | Lossless information-only planning projection. |
| `POINT-OF-USE-IMPLEMENTATION.json` | Exact five-file implementation boundary, eight public surfaces, and remaining release gates. |
| `NATIVE-BINDING.json` | Explicit P/PPI/UCM point-of-use binding and all remaining unbound product interfaces. |
| `SOURCE-RECONCILIATION.json` | Stage, requirement, and case denominator comparison plus source-issue dispositions. |
| `JURISDICTION-PROFILE.json` | Keeps StateJurisdiction, GovernanceJurisdiction, and EnforcementPerimeter separate. |
| `CHC-THR-CORRESPONDENCE.json` | Versioned, non-equating correspondence between CHC and UCM THR roles. |
| `LAW-AND-ORACLE-LOCK.json` | Blocks wire/interoperability claims pending normative profile and policy adjudication. |
| `REQUIREMENT.json` | The one requirement governing this construction batch. |
| `ACCEPTANCE-CASE.json` | The direct acceptance case for a replayable point-of-use decision. |
| `WORK-SELECTION.json` | P/PPI selection of direct case closure rather than unrelated infrastructure. |
| `WORK-UNIT-STATE.json` | Construction state and the remaining qualification/review/operator gates. |
| `INVENTORY.json` | Rooted index over the complete generated set. |

## CHC and THR stay distinct

The retained CHC source uses `Hs` and `Hm`. UCM THR uses separate `H_s`, `H_c`,
`H_m`, `H_j`, and `H_r` commitments plus `h_body`. Similar names do not make
these fields identical. In particular, CHC `Hm` includes state, dimensions,
and bound policy/root context, while UCM deliberately separates meaning,
admissibility context, and jurisdiction/locality.

The correspondence record therefore carries partial and one-to-many role
relationships with `identity_equivalence: false`. It also separates immutable
historical binding context from active point-of-use evaluation context. A
future normative transition rule may connect them; this construction does not
invent one.

## Point-of-use boundary

The source projection is only the denominator for the runtime decision path.
The runtime evaluator must receive independently supplied expected policy,
schema, trust-root, jurisdiction, and checkpoint anchors. A historical
decision can be valid for its original time while current use is refused,
deferred, or unresolved. Evidence acquisition over LAN, Internet, or P2P is a
separate effectful operation and must pass through the Operational Gateway
before pure evaluation.

The six state, semantic, revocation, checkpoint, policy, and schema statuses
are not caller-authored booleans or labels. Each is linked to a distinct
evidence row by `status_evidence_ids`; the evaluator derives the status from
the row's typed observation, verification outcome, and validity interval.
Rows and links are committed by the evidence-snapshot root.

An enforcement perimeter marked `DECLARED_ONLY` cannot yield `ADMIT`; it stays
`UNRESOLVED` until the exact scoped adapter is qualified. The evaluator also
consumes the snapshot's logical step budget and reports the evaluated step
count, so `max_steps` is a checked bound rather than descriptive metadata.

Only a current `ADMIT` decision rooted into G1 can make a separately authorized
operation eligible for dispatch. The evaluator does not grant authority, and
G2/G3 must still bind the observed result and diagnostic classification. The
human Pippi projection is an explanation of the same rooted decision, never an
alternate authority record.

## Present standing

- standing: `INFORMATION_ONLY`
- authority effect: `NONE`
- real A5: `false`
- G0: `CLOSED`
- source-program projection: bound and reproducible
- native point-of-use evaluator and gateway binding: implemented,
  information-only, pending qualification
- complete CCP product program/admission: not claimed; all 116 source product
  cases remain unexecuted
- CHC wire compatibility: unresolved
- DKN runtime binding: unresolved
- native target witness: absent
- operator Tier 1, independent review, and cache-free qualification: required


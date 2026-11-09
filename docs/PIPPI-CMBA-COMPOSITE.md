# P/PPI CMBA composite boundary

The r036 composite binds one exact common-turn record to the surrounding
constitutional systems without declaring them semantically identical. Its
profile is `PIPPI.CMBA.COMPOSITE.V1`.

## Co-projections

| Projection | What is checked | What it does not establish |
| --- | --- | --- |
| CMBA | Exact wheel, profile, values, structural evaluation and replay | Truth of the reported work |
| DKN | Exact keyed locality record and namespace context | Namespace authority or permission |
| THR | Separate state, admissibility, meaning, locality and receipt commitments | Equivalence between commitments |
| CHC | Exact role correspondence with THR and explicit non-equivalence | Native CHC wire compatibility |
| CCP | Rebuilt point-of-use decision under independently supplied anchors | Effect permission |
| G1/G2/G3 | Revalidated operational history and derived proof bundle | New authority from the composite |

`pippi cmba-composite-profile` displays the frozen profile. Build with
`pippi cmba-composite-build REQUEST.json` and verify with
`pippi cmba-composite-verify REQUEST.json`.

## Modes

`OBSERVATIONAL` binds the turn, CMBA, DKN, CHC, CCP and THR records with no
operation history. It says `NO_EFFECT_HISTORY_DECLARED`.

`EFFECT_BOUND` additionally revalidates the complete operational journal. The
operation permit's request root must equal the common-turn root. The authorized
event must contain an admissibility bundle whose decision is the exact CCP
decision in this composite. A terminal operation is accepted only when G1, G2,
G3 and the re-derived proof bundle are complete.

The composite always has `effect_authorized: false`. It records and verifies
cross-links; it does not grant authority, and the Operational Gateway remains
the only effect mediator.

## THR mapping

- `H_s` commits the exact canonical bytes of the opening, report, turn, CMBA,
  DKN, CHC, CCP and optional operational records.
- `H_c` commits CCP status and CHC/THR correspondence.
- `H_m` commits CMBA and turn meaning roots.
- `H_j` commits DKN locality and the CHC profile root.
- `H_r` commits the G1/G2/G3 and proof roots.
- `h_body` binds the complete THR envelope.

The CHC correspondence must name the composite THR contract root supplied by
the profile. A caller cannot substitute a generic or predecessor THR contract.

Standing remains `INFORMATION_ONLY`, authority effect `NONE`, real A5 false,
and G0 closed.

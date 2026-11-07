# CCP at the P/PPI–Courthouse boundary

## The operational question

CCP point-of-use admissibility answers **whether the exact evidence available
now permits this exact work order to enter Courthouse preflight**. It does not
grant authority and it does not execute the work order.

The boundary is deliberately placed after P/PPI has bound an exact work unit
and before Courthouse G1 Sentinel may pass:

```text
P/PPI acceptance case and work unit
        |
        v
exact Workflow IR request
        |
        v
CCP current-use evidence + jurisdiction + perimeter + correspondence
        |
        v
ADMIT decision bound into an admission envelope
        |
        v
Courthouse submission (not dispatched)
        |
        v
external Courthouse resolves its capability lattice and authority
        |
        v
G1 must carry admission-envelope, decision, and current-use roots
        |
        v
G2 witnesses effects; G3 diagnoses the result
```

An `ADMIT` result means only **current evidence permits preflight**. The
external Courthouse still owns capability resolution, authority, executor
selection, effect custody, and adjudication. A missing, stale, refused, or
cross-bound record stops compilation before dispatch.

## Active surfaces

| Surface | Purpose |
| --- | --- |
| `BUILD_COURTHOUSE_ADMISSION_ENVELOPE` | Bind one exact CCP decision to one P/PPI acceptance case, work unit, and Workflow IR request. |
| `COMPILE_ADMISSIBLE_COURTHOUSE_WORKFLOW` | Add the point-of-use step and the roots G1 must carry. |
| `PROJECT_COURTHOUSE_ADMISSION_STATUS` | Give humans and agents a concise, non-authorizing status. |
| `VERIFY_ADMISSIBLE_COURTHOUSE_RESULT` | Confirm that a returned Workflow result carries the required CCP roots at G1. |

Role-named CLI entry points are:

```powershell
python -m ucm.cli courthouse-compile-admissible REQUEST.json ADMISSION.json SUBMISSION.json
python -m ucm.cli courthouse-admission-status SUBMISSION.json STATUS.json
python -m ucm.cli courthouse-import-admissible-result SUBMISSION.json RESULT.json IMPORT.json
```

The admission envelope itself can be produced through `ucm invoke`, which
keeps its complete typed request visible rather than hiding the jurisdiction,
evidence, and trust anchors behind command-line flags.

## Exact roots that cross the boundary

The submission requires G1 to carry three roots:

1. the complete admission-envelope root;
2. the derived CCP decision root; and
3. the exact current-use snapshot root.

These roots bind the subject, operation, application, requested effect set,
authenticated epoch, jurisdiction profile, enforcement perimeter, CHC/THR
correspondence, policy, schema registry, trust basis, checkpoint, evidence
snapshot, acceptance case, and P/PPI work unit.

The human status is a projection. It is neither evidence nor authority.
Progress JSONL is also never evidence.

## Current installation status

This release stages a portable adapter and handoff. It does not install a
Courthouse route. The local AOK orientation found no capability lattice in
this workspace, so the submission truthfully records:

- `courthouse_lattice_status: EXTERNAL_RESOLUTION_REQUIRED`;
- `dispatch_status: NOT_DISPATCHED`; and
- `courthouse_route: STAGED_NOT_INSTALLED`.

The Courthouse session must bind the adapter to its own current lattice and
authority policy. That later binding cannot alter the CCP evidence silently;
it must consume the exact submission and return the exact three-gate roots.

Everything here remains `INFORMATION_ONLY`, with authority effect `NONE`,
real A5 false, and G0 closed.

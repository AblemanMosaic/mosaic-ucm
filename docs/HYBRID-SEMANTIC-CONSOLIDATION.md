# Hybrid semantic consolidation

UCM separates cross-application consolidation into three different kinds of
work so semantic similarity cannot silently become implementation authority.

## The boundary

1. **Deterministic discovery** applies a hash-bound policy to exact AMCAS
   application plans. It can say that capabilities share declared tokens and
   should be compared. It cannot say they mean the same thing.
2. **Modeled judgment** lets FSC, an LLM, or a human record a rooted
   interpretation. FSC/LLM output is a hypothesis. Only an explicit human or
   composite decision may mark a candidate `CONFIRMED_FOR_CORRESPONDENCE`.
3. **Correspondence evidence** compiles confirmed candidates into CM1
   obligations over exact application pairs. A court must discharge those
   obligations before a later proposal can claim behavioral correspondence.
4. **Consolidation design** remains a separate CM2 decision among a shared
   contract, adapter, service, or intentionally separate implementations.
   This pipeline never performs that change and never grants execution.

The comparison obligations cover subject binding, input and output schemas,
decisions and refusals, effects and budgets, authority and jurisdiction,
recovery and uncertainty, and privacy and disclosure. A name match is never
enough.

## CLI

```text
ucm semantic-discover POLICY OUT PLAN...
ucm semantic-judgment-packet DISCOVERY OUT
ucm semantic-build-judgment-submission PACKET INTENT OUT
ucm semantic-record-judgments PACKET SUBMISSION OUT
ucm semantic-compile-consolidation DISCOVERY REGISTER OUT
```

The judgment intent is the authoring surface. UCM fills candidate roots,
judgment roots, and the submission root. A modeling system should use
`FSC_LLM_HYPOTHESIS` with `human_confirmed: false`. A human confirmation
must name evidence roots and still produces only a program awaiting
correspondence evidence.

All hybrid CLI `--help` paths are observation-only. They parse before workspace
discovery or output creation and emit no candidate roots, receipts, or files.

## Near-term demonstration

`examples/consolidation/memory-vault-custody/` applies the policy pack
`SEMANTIC-CONSOLIDATION-CUSTODY-v0.1` to the seven frozen Stage I3 plans.

It reproducibly finds:

- four candidate roles: archive composition, archive replay, evidence reading,
  and vault custody;
- thirteen application-to-Memory-Vault comparison pairs;
- 104 CM1 obligations, eight per pair;
- zero human-confirmed candidates and zero court-ready programs.

This is useful now because it converts semantic gravity into a bounded work
queue without deduplicating code by intuition. It identifies where a common
contract or adapter may pay off while preserving application-local authority.

## Evidence and authority

Discovery records, hypothesis submissions, judgment registers, and compiled
programs are content-addressed. Progress output and chat summaries are not
evidence. Every artifact remains `INFORMATION_ONLY`, authority effect
`NONE`, real A5 false, and G0 closed.

The next operational boundary is Courthouse vNext Workflow IR: after human
confirmation, each program can be translated into exact correspondence-court
workflows. UCM imports only signed or otherwise externally rooted court
results. It does not execute application effects or mint their authority.

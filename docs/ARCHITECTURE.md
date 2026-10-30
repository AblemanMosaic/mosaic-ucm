# Architecture

```text
Intent / application / project
          |
          v
Realization Space Engine -----> selected, rooted configuration
          |                                  |
          v                                  v
UCL Language System -> Tessera Compilation -> obligations and evidence subjects
          |                                  |
          v                                  v
Native Proof Kernel                Court Execution Engine
          \                                  /
           v                                v
             Qualification Control Plane
                         |
          receipts, freeze, replay, handoff
                         |
          Agent Workbench + Project Intelligence
                         |
           AMCAS Integration Compiler (CM1 / CM2)
                         |
           MosaicID Session + Integration Journal
                         |
           Application Integration Gateway
```

The Constitutional Core supplies canonical values, identity, authority ceilings, and receipt rules. Custody and Federation preserve identity and replay state across machines. Portable Bootstrap stages content-addressed profiles without treating installation as authority.

## Compatibility strategy

The stable `ucm` package is the public facade. `uclop` and `uclsh` preserve the implementation inherited from frozen Operational Canonical c4 plus the closed repair delta in `compatibility/PUBLIC-COMPATIBILITY-DELTA.json`. Runtime resources live with their consuming packages; compatibility contracts remain under `compatibility/spec` for reconstruction and migration.

Redundant mechanisms are retired only after semantic equivalence is demonstrated. Until then, the stable facade chooses one canonical route and names any retained predecessor route as compatibility.

The AMCAS compiler projects rooted realization contracts into the retained
UCL/Tessera correspondence surface, preserves immutable obligation subjects,
and routes proof-bearing obligations to the Native Proof Kernel. The durable
journal is the cross-session source of truth. Its live JSONL progress channel
is explicitly nonsemantic and can never substitute for a receipt.


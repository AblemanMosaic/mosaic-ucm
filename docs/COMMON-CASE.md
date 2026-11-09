# The common UCM path

## You are here

```text
human or agent
      |
      v
orient + current capabilities
      |
      v
describe the intended result and what must remain true
      |
      v
check and select an admissible realization
      |
      v
capture complete dependency snapshot
and explain exact impact / next checks
      |
      v
compile application obligations and prepare governed work
      |
      +---- read-only work --------------------> evidence + journal
      |
      +---- external effect requested
                 |
                 v
        authority decision outside UCM
                 |
                 v
        Operational Gateway receipts
        authorize -> witness -> diagnose
                 |
                 v
          proof + portable archive
```

For most work, use these stable roles:

1. **Constitutional Core** describes identity, limits, and receipt rules.
2. **Realization Space** checks which configurations satisfy the contract.
3. **UCL and Tessera** turn intent into executable obligations and evidence subjects.
4. **Native Proof and Courts** check exact claims.
5. **AMCAS** adapts an application without silently replacing its native meaning.
6. **Operational Gateway** records any externally authorized effect through receipts.
7. **Journal and Portable Bootstrap** let another session verify and continue the work.
8. **Dependency and Evidence Graph** shows what changed, what needs checking,
   and what may be retained without treating history as permission.

Run `python tools/ucm.py capabilities` for current routes. Historical routes do
not appear there. Use `legacy-capabilities` only when reconstructing or migrating
an older subject.

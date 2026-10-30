# UCL, Tessera, and native proof

**UCL** is the deterministic executable language. It represents bounded constitutional programs, values, functions, and effects. The `uclsh` package contains the self-hosted compiler and VM compatibility implementation.

**Tessera** is the obligation-preserving compilation layer. It turns intent and clauses into typed intermediate representations, obligation inventories, evidence subjects, constitutional runtime units, and bound result records. A compiler pass may refine representation but may not silently drop an obligation or swap its evidence subject.

**Native Proof** verifies bounded claims. Contracts compile into proof obligations; certificates and traces are rechecked against exact formulas and subject roots. An assumption-bound or unknown result remains visible and cannot discharge an obligation as an unconditional proof.

These systems compose as:

```text
intent -> UCL executable meaning
      -> Tessera obligations and preservation maps
      -> proof certificates and evidence checks
      -> court and qualification receipts
```

UCM's proof system is intentionally native and small. External solvers may propose certificates, but their outputs remain untrusted until the kernel rechecks them.


# AMCAS–UCM Parity Court

The parity court prevents AMCAS and UCM from drifting silently.

Its denominator is fixed at build time as:

- one check for every versioned AMCAS baseline element; plus
- one check for every active UCM capability surface.

Every active surface must map to exactly one baseline element. Every baseline element must have an explicit UCM coverage status: `IMPLEMENTED`, `PARTIAL`, `APPLICATION_ADAPTER_REQUIRED`, or `UNIMPLEMENTED`. `PARTIAL` and `APPLICATION_ADAPTER_REQUIRED` are visible gaps, not failures hidden by a pass label. `UNIMPLEMENTED` refuses the court.

The court is pure and deterministic. It does not execute applications, mint authority, contact sessions, or perform adversarial review. Its result binds the AMCAS registry root and UCM coverage root. The operator Tier 1 kit separately tests resealing, denominator shrinkage, coverage laundering, profile broadening, and observatory rebinding; that kit is prepared here but run by the operator.

A successor changes the registry through an explicit version and migration delta. It must regenerate coverage, profiles, documentation, and the parity result. Old journals may retain their predecessor contract roots; they are never silently rewritten.

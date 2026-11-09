# Realization Space Engine

A Realization Space Contract (RSC) is UCM's substrate-neutral conceptual interface. It describes one authoritative subject and a bounded space of valid ways to implement, present, configure, or adapt it.

An RSC states:

- preserved identity and forbidden overrides;
- typed axes and their domains;
- ownership and mutability of each axis;
- hard constraints and preferred regions;
- selection policy, locks, objectives, and seed;
- target lowering, preservation, approximation, and loss;
- evidence and claim boundaries;
- an explicit authority ceiling.

The direct interface validates contracts and complete configurations, evaluates every supported hard constraint, then applies the contract's declared selection policy. Selection receipts bind the full evaluated candidate set. It does not make a representation authoritative, grant deployment authority, or silently trade an invariant for a better score.

## Exact v0.1 executable subset

- Axis types: `BOOLEAN`, `INTEGER`, `ENUM`, `SEED`, and SHA-256 `ROOT`.
- Constraint operators: `EQUALS`, `NOT_EQUALS`, `IN`, `RANGE`, `REQUIRES`, and `FORBIDS_COMBINATION`.
- Selection policies: `EXACT_DEFAULTS`, `OBJECTIVE_PRIORITY`, and `LEXICOGRAPHIC_CONFIGURATION_ROOT`.
- Objective metrics are signed 64-bit integers with `MINIMIZE` or `MAXIMIZE`.
- Preferred regions and active adaptation policies are not executable in v0.1 and refuse if supplied.

`PASS_ADMISSIBLE` establishes axis-domain validity and all declared hard constraints in that subset. Lowering, evidence production, deployment, and authority remain separate results. Unsupported semantics produce typed refusals rather than favorable partial verdicts.

The normative schema is `spec/realization-space-contract-v0.1.schema.json`. The executable example includes two checked hard constraints at `examples/realization/portable-agent-environment.json`.

MosaiCOS M1 may bind Genesis, target-profile, Ethernet-bootstrap, and agent-hosting artifacts through this interface later. v0.1 keeps those identities unbound.

The UCL/Tessera projection and preservation trace are conceptual correspondence surfaces. The projection produces obligation-shaped configuration records; it is not a UCL compilation, a Tessera preservation proof, or target execution. The trace compares two configurations under the realization contract; it is not an implementation-semantics proof or compiler proof. Their result records state these non-claims directly.


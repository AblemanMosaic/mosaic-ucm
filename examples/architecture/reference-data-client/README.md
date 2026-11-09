# Architecture-fidelity reference

This synthetic data client demonstrates the application-owned architecture boundary.
`ARCHITECTURE-CONTRACT.json` states the exact subject, permitted impact paths,
protected paths, abstractions that a change must reuse, and required test and proof evidence.

`CONFORMING-CHANGE.json` reuses the client and response-decoder abstractions, stays
inside the declared path set, and supplies a test-evidence root plus a Native Proof
Kernel verification root. It passes. The architecture checker binds the proof root;
the proof subsystem remains responsible for producing and verifying that receipt.

`DRIFTING-CHANGE.json` creates a parallel client outside the declared impact set and
does not supply the required evidence. It is refused. These manifests are fixtures;
they do not claim that UCM inferred source semantics or executed application tests.

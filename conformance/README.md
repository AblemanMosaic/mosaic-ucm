# Language-neutral conformance

`CANONICAL-JSON-GOLDEN-VECTORS-v0.1.json` contains raw inputs, canonical outputs,
and expected SHA-256 values as base64 and lowercase hex. A non-Python verifier
must decode the input, enforce the canonical restrictions documented in
`docs/STABILITY-PORTABILITY-AND-ROBUSTNESS.md`, reproduce the exact canonical
bytes, and match the hash. Verification-only interoperability is the goal; a
second implementation does not need to reproduce the Python authoring runtime.

Cross-language implementations must preserve code points rather than silently
normalizing Unicode, reject floats and duplicate keys, enforce signed 64-bit
integers, and distinguish missing fields from empty values.

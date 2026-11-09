# Parser and verifier fuzz targets

These targets are reviewer/operator apparatus. Builder qualification syntax-
checks them and carries the seed corpus; it does not execute adversarial fuzzing.

Success for arbitrary bytes is either a valid typed result or a typed refusal.
An unhandled exception, timeout, process crash, or authority-ceiling change is a
failure. Run the targets only in a disposable workspace and preserve the exact
seed, implementation root, runtime, and crashing input.

- `fuzz_canonical.py`: canonical JSON parser and serializer.
- `fuzz_contracts.py`: realization and AMCAS validators.
- `corpus/`: known-good canonical seeds. Reviewer-generated failures belong in
  evidence, not in the runtime corpus until dispositioned.


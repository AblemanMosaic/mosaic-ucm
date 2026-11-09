# UCM Native Completion

UCM v0.1 r033 supplies two corresponding realizations for its closed native
constitutional core:

```text
constitutional program JSON
        |
        +-- Python authoring/reference evaluator (portable fallback)
        |
        +-- canonical UCMN projection -> dependency-free C17 VM
                                      -> exact result correspondence
```

The native profile is intentionally bounded. It provides signed 64-bit values,
canonical booleans represented by `0` and `1`, fixed registers and stack,
checked arithmetic, comparisons, boolean operators, bounded branches and a
single terminal result. It has no I/O instructions, allocator, network,
filesystem, clock, randomness, subprocess or authority primitive. A program
must declare its instruction and step denominators and end in `HALT`. The C reader accepts the full declared limits: 256 registers, 4,096 instructions, 1,024 stack values and 1,000,000 execution steps.

The C runtime validates the projection header, instruction count, instruction
digest and terminal body commitment before evaluation. Its arrays are fixed at
compile time. Signed overflow, division by zero, a noncanonical boolean,
invalid jump, stack error, missing trailer, noncanonical integer spelling, unbound trailing bytes, a wrong external projection SHA-256, or exhausted step budget refuses.

Python remains the portable representation when a host cannot compile or run
an executable. It is the authoring implementation and correspondence oracle;
it is not allowed to silently widen the C profile. The frozen corpus covers
three-receipt conjunction, a held gate, budget comparison, typed branching and
truncating signed division. Qualification compiles the C17 runtime with all
warnings treated as errors and requires its result record to equal Python's for
every corpus member. Four boundary programs exercise the maximum register, instruction, stack and step denominators, bringing the correspondence corpus to nine programs.

This completes a deployable native path for `UCM_NATIVE_CORE_I64_V0_1`. It does
not claim that the full UCL-SH compiler, every UCM capability, P/PPI, AMCAS or
the Operational Gateway has been translated to C. Those systems can lower
settled integer constitutional predicates into this profile while retaining
the full Python runtime for broader authoring and verification.

## Entry points

```text
python -m ucm.cli native-profile
python -m ucm.cli native-compile PROGRAM.json PROGRAM.ucln
python -m ucm.cli native-reference PROGRAM.json
```

The compiled native runtime accepts the resulting `.ucln` file directly:

```text
ucm-native-core PROGRAM.ucln EXPECTED_PROGRAM_SHA256
```

P/PPI's C standard governs modifications to the runtime. Any change must bind
the exact source and toolchain, use C17, compile warning-clean, preserve checked
arithmetic and ownership rules, run the fixed correspondence corpus and retain
the Python fallback.

Qualification imports `ucm` from the exact governed `src/` tree under isolated Python and records that module's path and hash. An installed or user-site copy cannot satisfy the source qualification.

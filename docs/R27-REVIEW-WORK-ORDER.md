# UCM v0.1 r027 discovery-parity review work order

## Subject

r027 is a focused successor to r026. It closes one acceptance case:
`R27-01`, requiring every adaptive P/PPI CLI route to be discoverable in the
generated P/PPI surface registry with its exact registered route.

The r026 operator HOLD evidence is carried byte-exact. The r026 failures were
`CONTROL-GENERATED-CONTRACTS` and the consequent aggregate
`CONTROL-AUTHORITY-CEILING`; neither failure granted authority or executed an
external effect.

## Review boundaries

1. Verify the transport and every nested archive before loading subject code.
2. Recompute the generated adaptive contracts from the live capability and
   adaptive-route registries.
3. Confirm that every entry in `ADAPTIVE_CLI_ROUTES` appears exactly once in
   `PIPPI-CAPABILITY-SURFACE-REGISTRY.json` and that its route is
   `pippi <command>`.
4. Confirm runtime and cold-boot copies are byte-identical.
5. Confirm the frozen r026 operator and program directories are preserved.
6. Use the complete-replay transport for source reconstruction, qualification
   replay, and deterministic release rebuild. The focused transport does not
   claim those legs are possible.
7. Treat the operator kit as builder-authored and operator-runnable. Its
   launcher must extract to disposable storage, preserve sealed evidence, and
   remove disposable files.

The filesystem case probe intentionally operates in the current governed
directory. A read-only current directory is a typed limitation; reviewers must
not substitute a different filesystem and claim equivalent observation.

Standing remains `INFORMATION_ONLY`; authority effect `NONE`; real A5 false;
G0 closed. No review or court grants publication or execution authority.

# Portability-determinism boundary

Read this reference when work changes shells, crosses Windows and WSL, writes
governed text, builds archives, or makes a portability claim.

1. Run `pippi environment-observe` in the current environment and bind the
   resulting execution-context root into the turn opening. Require local case
   behavior to be marked `PROBED_CURRENT_FILESYSTEM`; the probe must be removed
   before the context is returned.
2. Re-observe after a shell, host, or filesystem transition. Never apply shell
   quoting, path, newline, encoding, or case rules from memory.
3. Use relative POSIX code-point keys for deterministic file ordering. Never
   sort `Path` objects directly.
4. Use UTF-8 without BOM and LF for governed source. Windows launcher files may
   use CRLF. Use the single canonical JSON function for rooted records.
5. For a Windows/WSL claim, execute the same pinned source and test denominator
   on Windows-native storage and on source copied into the native WSL
   filesystem. `/mnt/c` does not satisfy the WSL-native leg.
6. Recompute canonical outputs from the exact source on each native leg and
   compare those outputs. Preserve platform-specific execution receipts as
   separate evidence; do not require their roots to match.
7. Refuse a portable claim if a required leg is missing, unavailable, failed,
   uses the wrong filesystem class, or produces divergent canonical outputs.
8. Run `pippi portability-source-doctor` on changed deterministic source. Its
   PASS is a lint result, not cross-platform execution evidence.
9. Before qualification, run the generated adaptive-contract check. The live
   capability registry, mediation library, cold-boot contract, and completions
   must match the checked-in bytes and the cold boot must carry those exact
   files.
10. Use a declared turn scenario. Pippi injects every mediation rule required
    by that scenario; an unknown scenario or an opening missing a required rule
    must refuse.

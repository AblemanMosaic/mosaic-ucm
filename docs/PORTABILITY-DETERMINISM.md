# Portability determinism

P/PPI records the execution context before work crosses a shell, filesystem,
text-serialization boundary, packaging boundary, or portability claim. This
keeps host facts out of agent memory and makes platform assumptions reviewable.

The execution-context capsule separates observed facts from declared external
facts. It records the host and shell families, path flavour, filesystem class,
case policy, Python implementation and patch version, WSL distribution, and the
fixed text policy. Local case behavior is probed on the current filesystem and
the probe bytes are removed before the record is returned. Declared external
contexts remain explicitly labelled declarations. The capsule is evidence,
never authority.

Deterministic filesystem inventories sort by relative POSIX code-point keys.
They never sort `Path` objects directly. Governed Python and JSON source uses
UTF-8 without a byte-order mark and LF line endings. Windows launchers may use
CRLF. Canonical JSON remains compact, sorted-key UTF-8 with no trailing newline.

The portable claim requires two positive witnesses over the same source root,
test denominator, policy root, and canonical outputs recomputed from the exact
source by the shipped leg runner:

- `WINDOWS_NATIVE`, executed on the Windows filesystem;
- `WSL_NATIVE`, executed after the exact source is staged into the native WSL
  filesystem. Running Linux against `/mnt/c` is not the WSL-native leg.

Execution receipt roots are expected to differ. The gate compares canonical
outputs and reports the platform-specific receipts separately. Missing,
mounted-filesystem, failed, or divergent legs refuse the portable claim.

Qualification recomputes the same output denominator and refuses a witness
whose roots were copied or substituted. It also runs the adaptive-contract
generator in check mode. The checked-in capability registry, mediation library,
cold-boot contract, and shell completions must therefore correspond to live
code before a release can qualify.

Turn preparation maps each declared scenario to required mediation triggers.
Callers may request extra rules, but cannot omit the rules required by the
scenario. Unknown scenarios refuse rather than creating an ungoverned context.

Use `pippi environment-observe`, `pippi portability-policy`,
`pippi portability-witness`, `pippi portability-gate`, and
`pippi portability-source-doctor`. A source-doctor pass does not replace the
Windows/WSL correspondence witnesses or the ordinary qualification.

These checks remain `INFORMATION_ONLY`, with authority effect `NONE`, real A5
false, and G0 closed.
# Filesystem case probe boundary

The execution-context observer tests case sensitivity on the governed current
filesystem, because Windows case sensitivity can vary by directory. The probe
creates and removes a uniquely named file in the current directory. Run the
observer from a writable directory on the same governed filesystem. A read-only
directory produces the typed refusal `PIPPI_CASE_SENSITIVITY_PROBE_FAILED`;
P/PPI does not silently probe a host temporary directory and misstate the
governed filesystem's behavior.


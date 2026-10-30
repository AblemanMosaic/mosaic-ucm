# Audit boundary

The Git repository carries custody manifests and review orientation.

- `tools/build_release.py` without historical bytes emits a **lineage metadata** ZIP. It is not an audit evidence bundle.
- `tools/build_release.py --audit-source <frozen-c4-workspace>` verifies the supplied files against `C4-FROZEN-LINEAGE.json` and emits a **complete frozen-custody audit** ZIP.

This keeps the runtime and SDK parsimonious while preserving byte-identical historical evidence when requested. The audit archive is not imported or executed by UCM.


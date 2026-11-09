# Governed work package

The work-package surface consolidates three retained mechanisms without replacing
their semantics:

1. Project Intelligence validates the declared project graph and computes impact.
2. The architecture fidelity contract checks application-owned scope and reuse rules.
3. Autonomous Project Manager builds a bounded, simulation-only task plan.

The package is `READY_FOR_REVIEW` only when the change is known to the project graph
and passes the architecture contract. It remains information-only, cannot execute a
task, cannot close a real verification obligation, and cannot authorize a release.

```powershell
python tools/ucm.py work-package PROJECT.json ARCHITECTURE-CONTRACT.json `
  CHANGE-MANIFEST.json . "Review the declared change" WORK-PACKAGE.json `
  --changed-path src/reference_client.py
```

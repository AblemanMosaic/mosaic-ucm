# P/PPI modular installation

P/PPI v0.1 r024 separates the constitutional project/process core from optional capability realizations.

The built-in core includes P/PPI, UCM, the native/headless Mosaic UI correspondence, and the recommended UGK standards profile. It is useful without a network, a courthouse, a native orchestration host, SemCrys, or Memory Vault.

Optional packs are selected through a deterministic plan:

1. read the fixed pack registry and current inventory;
2. select a named profile and any additional packs;
3. close dependencies without downloading anything;
4. report exact local actions and typed holds;
5. require explicit user authorization before any remote acquisition;
6. treat a known manifest hash only as a verification target, never as the artifact itself;
7. verify an artifact before recording its exact installed root;
8. require an external binding receipt for capabilities owned by another system.

The native installer uses the Mosaic rainbow sun and dark Mosaic UI. The same registry, inventory, and plan are available headlessly through the CLI and ABI. `.VBS` launchers suppress terminal windows for the installer, dashboard, service, and headless status entrypoints. `.BAT` files remain inspectable fallbacks.

Read-only inventory, planning, portability, and probe commands do not create an
inventory file. `pack-record` is the explicit, exact-head mutation surface.
The `.VBS` launchers invoke the corresponding BAT or command entrypoint with a
hidden window; the BAT entrypoints remain visible-console alternatives.

## Common commands

```text
PIPPI-INSTALLER.vbs
PIPPI-HEADLESS.vbs
python -m ucm.pippi_cli pack-list
python -m ucm.pippi_cli pack-inventory
python -m ucm.pippi_cli install-plan RECOMMENDED_LOCAL
python -m ucm.pippi_cli project-portability --required-pack PIPPI_CORE --required-pack UCM_CORE --required-pack UGK_STANDARDS
```

## Optional systems

- **UGK standards** are built in and recommended. They supply claim discipline, Three Hash Rule practice, and semantic/state/governance separation. The canonical native UGK runtime is a separate optional binding.
- **SemCrys Core** is optional. P/PPI carries exact public release metadata and can plan an offline or explicitly authorized acquisition; it does not reimplement SemCrys.
- **Mosaic Memory Vault** is optional. Its adapter requires SemCrys plus an independently rooted binding to the vault. P/PPI does not claim that a local pack is durable or available merely because its bytes exist.
- **AOK Courthouse** and **native host mediation** are optional external bindings. Their presence never grants P/PPI their authority.

## Recovery and custody

The inventory is an atomic, content-rooted state file. Every mutation requires the caller's expected inventory head, verified evidence roots, and—where applicable—a binding root. A stale writer receives a typed head-mismatch refusal. Component effects occur outside the resolver and must return their own custody evidence before the inventory can advance.

All material remains `INFORMATION_ONLY`, with authority effect `NONE`, real A5 false, and G0 closed.

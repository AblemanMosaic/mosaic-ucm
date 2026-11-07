# Migrating existing P/PPI sessions

P/PPI r004 imports **verified references**, not copied histories. The original
campaign remains authoritative at its source path.

## What qualifies

A candidate must contain `PIPPI-CONTEXT.json` and a valid canonical campaign
journal. P/PPI validates the context, complete event chain, journal head, and
derived observatory. A context-shaped file without its journal is refused and
retained in the migration report as a quarantined candidate.

## Preview

```powershell
pippi.cmd migrate-discover C:\path\to\existing-pippi-root
```

This is read-only. It returns verified session references and typed refusals.

## Import into a project

```powershell
pippi.cmd migrate-import PROJECT_ID C:\path\to\existing-pippi-root
```

Import stores the source path and exact roots under the global P/PPI data root.
It does not edit, rename, normalize, or relocate the source campaign. Use
`pippi.cmd sessions --project-id PROJECT_ID` to inspect the references.

For several mappings with a sealed report:

```powershell
python tools/migrate_pippi_existing_sessions.py `
  --data-root "$env:LOCALAPPDATA\Ableman Mosaic\Pippi\data" `
  --map "mara=C:\path\to\MARA-PIPPI" `
  --map "semcrys=C:\path\to\SEMCRYS-PIPPI" `
  --out MIGRATION-INVENTORY.json
```

## Workspaces and canonical stores

A session source path is neither a working workspace nor a canonical software
revision store. A project profile records all three independently:

- **working workspace** — mutable source where current work occurs;
- **session source** — immutable-by-policy journal and records being referenced;
- **canonical revision store** — accepted version/revision artifacts, Git
  identity, or Memory Vault address.

If the canonical store is unknown, it remains `UNBOUND` and appears as a release
blocker. P/PPI does not infer it from nearby archives or record folders.

## Portability

Absolute local paths are installation metadata. Portable handoffs bind content
roots and reconstruction artifacts; a receiving installation rebinds local
paths after verifying those roots. Migration never changes standing or grants
execution, publication, courthouse, or archive authority.

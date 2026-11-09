# P/PPI capability packs

P/PPI works as a complete constitutional project and process interface with only its built-in core. Optional packs add realizations; they never relax a contract when absent.

## Profiles

| Profile | Packs |
| --- | --- |
| `COURTHOUSE_CONNECTED` | `COURTHOUSE_ADAPTER`, `MOSAIC_UI`, `PIPPI_CORE`, `UCM_CORE`, `UGK_STANDARDS` |
| `FULL_MOSAIC` | `CMBA_EVIDENCE`, `COURTHOUSE_ADAPTER`, `MEMORY_VAULT_ADAPTER`, `MOSAIC_UI`, `NATIVE_HOST_ADAPTER`, `PIPPI_CORE`, `SEMCRYS_CORE`, `UCM_CORE`, `UGEL_EXECUTOR`, `UGK_RUNTIME`, `UGK_STANDARDS` |
| `MINIMAL_CORE` | `MOSAIC_UI`, `PIPPI_CORE`, `UCM_CORE` |
| `PORTABLE_AGENT` | `MOSAIC_UI`, `PIPPI_CORE`, `UCM_CORE`, `UGK_STANDARDS` |
| `RECOMMENDED_LOCAL` | `MOSAIC_UI`, `PIPPI_CORE`, `UCM_CORE`, `UGK_STANDARDS` |
| `TRANSTEMPORAL_PROJECT` | `MEMORY_VAULT_ADAPTER`, `MOSAIC_UI`, `PIPPI_CORE`, `SEMCRYS_CORE`, `UCM_CORE`, `UGK_STANDARDS` |

## Packs

| Pack | Default | Distribution | Purpose |
| --- | --- | --- | --- |
| `CMBA_EVIDENCE` | no | `OFFLINE_ARTIFACT` | Optional exact offline CMBA wheel for structural bindings and replay over common turn records; no policy, authority or host-enforcement grant. |
| `COURTHOUSE_ADAPTER` | no | `EXTERNAL_BINDING` | Optional governed cross-jurisdiction work-order and result correspondence. |
| `MEMORY_VAULT_ADAPTER` | no | `EXTERNAL_BINDING` | Optional transtemporal persistence, availability checks, exact retrieval, and cross-session reconstruction. |
| `MOSAIC_UI` | yes | `BUILT_IN` | Dark native dashboard and installer with headless semantic correspondence. |
| `NATIVE_HOST_ADAPTER` | no | `EXTERNAL_BINDING` | Optional verified tool and visible-output interposition supplied by a compatible orchestration host. |
| `PIPPI_CORE` | yes | `BUILT_IN` | Project, turn, journal, capsule, CLI, ABI, and local coordination machinery. |
| `SEMCRYS_CORE` | no | `EXTERNAL_DOWNLOAD` | Optional exact reconstruction, semantic compression, reusable legends, and compact project transport. |
| `UCM_CORE` | yes | `BUILT_IN` | Typed contracts, capability registry, verification, and non-authorizing operational boundaries. |
| `UGEL_EXECUTOR` | no | `EXTERNAL_BINDING` | Optional exact external executor contract and receipt adapter; UCM discovers and binds it but never selects it or mints its grants. |
| `UGK_RUNTIME` | no | `EXTERNAL_BINDING` | Optional separately pinned native UGK implementation and certification surfaces. |
| `UGK_STANDARDS` | yes | `BUILT_IN` | Three Hash Rule, FGA/IEL, claim discipline, and context-injection practices without claiming the canonical UGK runtime. |

## Effect boundary

The resolver creates a content-rooted plan only. It does not download, install, bind, register a service, use a credential, or grant authority. Remote acquisition requires explicit user authorization and an external effect gateway. External bindings require their owner's independently verified receipt.

An installed project records its required pack IDs. Opening it on another host yields `READY` or `NEEDS_PACKS`; view-only inspection remains available. Missing packs do not delete requirements or silently select a weaker realization.

Registry root: `b043fa8284bbf87b10d9d9b5377fbd93a0084b6ba3a1fc47ad1391487d03d84f`

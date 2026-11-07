# P/PPI integration availability

Architectural ownership does not prove installation or availability. P/PPI
therefore carries one exact six-entry registry for `PIPPI_CORE`,
`UCM_OPERATIONAL_GATEWAY`, `AOK_COURTHOUSE`, `CRYSTAL_NETWORK`, `MEMORY_VAULT`
and `MOSAIC_READER`.

Each entry has one status:

- `BUILT_IN` — the surface is carried by this exact runtime;
- `BOUND_EXTERNAL` — a governed binding root and evidence roots are present;
- `DECLARED_UNBOUND` — the architecture names the owner but no usable binding
  is present;
- `UNAVAILABLE` — the integration is explicitly unavailable.

The default install marks only P/PPI Core and Mosaic Reader built in. Binding an
external system is a pure registry transition and grants no capability. The
consumer must still verify the external system's own authority and effect
receipts. The dashboard projects these statuses directly and disables host
effects while the operational gateway is unbound.

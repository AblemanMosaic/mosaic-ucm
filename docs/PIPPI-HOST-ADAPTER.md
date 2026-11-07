# P/PPI host adapter boundary

P/PPI distinguishes a declaration about observable channels from evidence that
a host actually mediates them. `BUILD_PIPPI_CONTEXT` always produces
`SIDECAR_PARTIAL`, even when all seven channels are listed. A host may produce
`ENFORCED_HOST` only through `BUILD_ATTESTED_PIPPI_CONTEXT`, with an expected
host-policy root supplied by the host boundary. Consumers must pass that same
external root to `effective_integration_mode`; a self-contained signed capsule
without the external anchor remains effectively `SIDECAR_PARTIAL`.

The attested path binds:

- an Ed25519 attestor key and adapter-registry root in a host policy;
- the exact adapter source, subject, session and seven-channel denominator;
- a bounded validity interval;
- the UCM operational issuer, jurisdiction and revocation-registry roots.

The attestation grants no authority. It proves only that the named adapter made
the named coverage claim under the pinned policy.

## Dashboard effects

The native dashboard contains no direct process-launch, shell-open, browser, or
review-run route. It constructs a `pippi-host-launch-proposal` with
`dispatch_authorized: false`, records that proposal durably, and hands it to an
injected host adapter. The adapter remains external to P/PPI.

Before accepting completion, P/PPI verifies the complete UCM Operational
Gateway history and proof bundle. The permit must bind the proposal root,
project, session and exact effect set; the terminal executor receipt must bind
the result projection. Missing, partial, changed or unbound results are typed
refusals. `verify_then_launch` is two separately receipted operations.

The default dashboard uses `RefusingHostLaunchAdapter`. Launch controls remain
disabled until `UCM_OPERATIONAL_GATEWAY` is `BOUND_EXTERNAL` to the exact host
policy root. This package supplies the protocol and positive fixtures; it does
not manufacture an external permit or executor.

All records remain `INFORMATION_ONLY`, with authority effect `NONE`, real A5
false and G0 closed.

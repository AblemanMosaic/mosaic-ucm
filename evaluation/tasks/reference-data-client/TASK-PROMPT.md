# Reference data client task

Add a bounded in-memory cache to `ReferenceDataService`.

The cache must:

- avoid a second transport call for the same key while the entry is live;
- expire entries after the injected clock advances beyond the configured TTL;
- preserve the existing transport protocol and public service method;
- keep the domain module free of transport, filesystem, environment, and network imports;
- avoid unrelated source changes; and
- include focused tests for cache hit and expiry behavior.

Do not add network access, install dependencies, change authority policy, or weaken an
existing test. Return the changed tree, test output, and a short architecture rationale.

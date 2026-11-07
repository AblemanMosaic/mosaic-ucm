# Parsimony and artifact boundaries

The public repository contains active source, contracts, examples, tests, and documentation. It does not embed predecessor transports, old cold-boot archives, or reviewer evidence ZIPs.

Release tooling produces three independent artifacts:

- **runtime**: stable public code, contracts, examples, and essential documentation;
- **SDK**: runtime plus tests and developer tooling;
- **lineage metadata**: hashes and lineage declarations only, explicitly marked `METADATA_ONLY`;
- **complete audit**: frozen predecessor custody artifacts, review evidence, and lineage manifests, emitted only when pinned source bytes are supplied.

Each artifact has its own closed manifest and SHA-256. The release index binds them without placing the audit archive inside the runtime or SDK. Frozen predecessor bytes are never rewritten to make their internal names look current.


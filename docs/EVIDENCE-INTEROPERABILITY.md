# Evidence interoperability

UCM can bind evidence produced by ordinary software tools without claiming to
understand more than the adapter proves. The reference envelope supports
pytest, unittest, tsc, eslint, coverage, SBOM, and CI result subjects.

The evidence subject records:

- exact software subject root;
- invocation and output roots;
- environment and verifier roots;
- policy and issuer roots;
- exit code and declared counters;
- issuance and freshness interval.

The default interpretation is `PRESENCE_AND_HASH_ONLY`. A court may require a
named result subject with an accepted root and PASS status. It does not infer
that the tests were sufficient, the typechecker was sound, or an SBOM was
complete.

A custom verifier must be deterministic for its declared input, reject unknown
fields, bind its exact implementation root, bind the subject and policy roots,
return typed status, preserve the authority ceiling, and state every semantic
claim it does not establish.

Example: a project runs pytest outside UCM, stores stdout as a content-addressed
artifact, and records the invocation/environment roots. The adapter builds an
external-tool evidence subject. A CM1 requirement checks that exact evidence
subject is present and current. The external execution remains external.


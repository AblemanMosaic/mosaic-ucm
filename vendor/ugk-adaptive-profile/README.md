# UGK adaptive profile

This directory is P/PPI's portable, non-authoritative UGK practice profile. It
does not claim to contain the canonical UGK runtime. It gives adaptive hosts the
governance rules they must preserve when the separately pinned native kernel is
unavailable. A `FULL_REFERENCE` or native-enforced package must supply and pin an
exact canonical UGK release separately.

The profile covers FGA transition form, the separated Three Hash Rule
commitments, IEL validate-before-mutate behavior, CK portability, CGP posture,
and claim discipline. P/PPI uses the profile for context and record validation;
it never treats the profile as an authority grant.

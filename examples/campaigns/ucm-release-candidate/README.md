# UCM release candidate as a UCM campaign

This repository dogfoods its custody model. The source-controlled campaign under
`program/maturity-evolution/` binds the exact predecessor, compiles the accepted
feedback register through CM1/CM2 and AMCAS, separates the THR commitments, and
starts an append-only journal.

The campaign deliberately stops before qualification. After the one cache-free
qualification, `tools/finalize_maturity_evolution_campaign.py` copies that frozen
campaign, attaches the qualification as an ordinary external-tool evidence
subject, dispositions all 56 requirements, advances the copied journal, and
seals `UCM-SELF-RELEASE-CAMPAIGN.zip`.

This split prevents the qualification result from changing the source it claims
to qualify. The archive remains `INFORMATION_ONLY`, grants no authority, and
still records operator Tier 1 and independent review as pending.

# MosaicID sessions

A MosaicID passport is a public identity descriptor: BLAKE3 of the raw Ed25519
public key plus declared context. It contains no private key and grants no
rights. UCM pins the expected user ID, issues a fresh challenge bound to a
distinct agent/session ID and integration contract, verifies possession, and
records one-time consumption in the durable journal.

Declared universe, epoch, and semantic namespace remain declarations until
local namespace and delegation checks admit them. Key rotation creates a new
MosaicID unless a separately verified succession record links it. Session
authentication proves key possession for one bounded session; it does not
authorize an effect or capability grant.

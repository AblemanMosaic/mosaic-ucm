# P/PPI local IPC security

P/PPI's local coordination service listens only on an OS-assigned loopback
port. Possession of the 32-byte `IPC.key` authenticates a client. The endpoint
record is discoverable local routing information; the key is not.

The service creates `IPC.key` exclusively and forces its bytes to disk before
opening the listener. It then establishes and verifies the platform boundary:

- **Windows:** inheritance is removed and the file receives one explicit
  `Allow FullControl` rule for the current user's SID. P/PPI verifies that the
  DACL is protected, contains exactly that rule, is not inherited, and names
  the current SID.
- **POSIX:** the file is mode `0600` and owned by the current effective user.

P/PPI re-verifies this boundary before every key read. Missing, linked,
wrong-owner, inherited, broadened, or otherwise unverifiable protection fails
closed before a service or client can authenticate. If protection fails while
creating a new key, the unprotected key file is deleted.

This is local authentication, not identity, authority, encryption-at-rest, or
permission to execute project effects. Effectful work remains outside the
read-only service and must pass through the separately bound UCM gateway.

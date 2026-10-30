# Exact subject binding

An integration starts from bytes, not a project name. A binding policy selects
included and excluded paths, symlink handling, Git observation, and one mode:
immutable archive, immutable snapshot, or working baseline. UCM records every
selected path, byte count, SHA-256, tree root, manifest root, and authority
ceiling. Any changed byte creates a new subject.

If a session has only a description or a path it cannot access, it returns
`SOURCE_BOUNDARY_REQUIRED`. No Stage I1 claim is possible until bytes are bound.

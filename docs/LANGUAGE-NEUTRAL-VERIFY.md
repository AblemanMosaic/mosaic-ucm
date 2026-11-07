# Language-neutral verify path

UCM custody artifacts are not Python-specific. A verify-only implementation in
another language must:

1. parse UTF-8 JSON while refusing duplicate keys, floats, non-finite numbers,
   BOMs, invalid Unicode, excessive depth, and integers outside signed 64-bit;
2. serialize compact JSON with keys ordered by Unicode code point and no trailing
   newline before hashing;
3. compute SHA-256 over the exact canonical bytes;
4. validate every archive member path as portable POSIX-relative, reject aliases,
   duplicates and undeclared members, and compare size and SHA-256 to the manifest;
5. rebuild typed roots only from the fields named by that schema; and
6. preserve `INFORMATION_ONLY`, `NONE`, `real_a5=false`, and `g0=CLOSED`.

The golden vectors in `conformance/CANONICAL-JSON-GOLDEN-VECTORS-v0.1.json`
are the cross-language starting point. A non-Python verifier may report PASS
only when every accepted vector has the listed canonical bytes/root and every
refusal vector is rejected with no partial result.

Pseudocode:

```text
value = strict_parse(input_bytes)
canonical = encode_sorted_compact_utf8(value)
assert sha256(canonical) == expected_root
for member in archive:
    assert portable(member.path)
    assert sha256(member.bytes) == manifest[member.path].sha256
assert set(archive.paths) == set(manifest.paths) + {manifest_path}
```

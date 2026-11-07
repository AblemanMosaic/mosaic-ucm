# Agent adapter and loop

The reference adapter is a thin enforcement layer around the existing ABI. It
does not copy UCM mechanics into a coding-agent plugin. At construction it pins
the active capability registry and product-profile registry. A mismatch fails
closed before a tool is exposed.

The common agent loop is:

```text
orient → bind exact subject → validate/compile → plan
       → external gateway for any effect → export journal
```

An adapter tool result carries exact typed status, result roots, and the journal
head after a state change. Chat memory may retain those roots and a human
summary. Before continuing, the next session reloads the canonical journal.
Progress JSONL is live observability only; it is never evidence, permission, or
a journal substitute.

MCP, Codex, Claude Code, Cursor, and other hosts may wrap
`AgentToolAdapter.call`. They should generate strict input schemas from the
registry and expose only the selected profile. The Operational profile still
does not grant permission: effects require the receipt-mediated gateway and an
external authority source.

See `spec/AGENT-LOOP-CONTRACT.json` for the machine-readable form.


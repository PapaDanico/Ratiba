# ADR 0001: Record architecture decisions

* **Status:** Accepted — 2026-05-27
* **Deciders:** Capt. Dan Ng'ong'a, Claude Code

## Context

Ratiba will be audited by KCAA and reviewed by future operators. Material
architectural choices need a durable, dated record so that any reader —
including a regulator — can trace why the system looks the way it does.

## Decision

We adopt the Markdown ADR format. Every non-trivial design decision gets a
file in `docs/adr/` numbered sequentially, with: status, context, decision,
consequences. Claude Code is responsible for proposing ADRs as part of any
PR that introduces, removes, or materially changes a component.

## Consequences

- A new contributor (or KCAA inspector) can read `docs/adr/` end-to-end and
  understand the system without reading code.
- Reversing a decision requires a new ADR that explicitly supersedes the
  prior one — no silent rewrites of history.

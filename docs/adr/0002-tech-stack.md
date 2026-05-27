# ADR 0002: Technical stack

* **Status:** Accepted — 2026-05-27
* **Deciders:** Capt. Dan Ng'ong'a, Claude Code
* **Reference:** Ratiba Project Plan v1.0, §2

## Context

We need a stack that supports:

1. A deterministic, auditable constraint solver suitable for KCAA scrutiny.
2. LLM-anchored configuration without locking the solver behind the LLM.
3. Regional hosting that satisfies KDPA 2019 data residency.
4. A crew-facing channel that crews already use (Telegram in EAC).
5. A small team (effectively one engineer + Claude Code) shipping in 16
   weeks.

## Decision

- **Backend:** Python 3.12 + FastAPI. Strong ecosystem for OR-Tools,
  Anthropic SDK, async; OpenAPI for free.
- **Optimiser:** Google OR-Tools (CP-SAT). Open source, deterministic, the
  industry standard for constraint scheduling.
- **LLM:** Anthropic Claude — Sonnet 4.5 for OM-A parsing (heavy lift),
  Haiku 4.5 for bot conversational routing (low cost). The optimiser never
  depends on the LLM.
- **Database:** PostgreSQL 16. ACID required for crew records + audit trail.
- **Cache / queue:** Redis 7 + `rq`.
- **Frontend:** React 18 + TypeScript + Tailwind + shadcn/ui.
- **Crew interface:** Telegram bot + responsive web. No native app at MVP.
- **Auth:** JWT (self-hosted) for MVP; Auth0 as a deliberate upgrade path.
- **Hosting:** AWS Cape Town (`af-south-1`) **or** Africa Data Centres /
  Liquid (Nairobi). Final choice in Phase 6, driven by KDPA verification.
- **CI/CD:** GitHub Actions.
- **Observability:** Sentry + structlog JSON logging.
- **PDF generation:** WeasyPrint — HTML → PDF with clean styling control.

## Consequences

- The system stays auditable end-to-end: every roster decision traces to
  rule code, every rule traces to a KCARs citation, every change traces to
  the immutable `audit_events` log.
- LLM outages cannot stop rosters from being generated or audit packs from
  being produced. They at worst degrade the bot to command-only mode.
- A future commercial solver (Gurobi) can replace OR-Tools without
  touching the API surface, if Phase 7 stress tests demand it.

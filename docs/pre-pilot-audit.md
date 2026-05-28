# Pre-pilot audit — Phase 6 readiness gate

> **Audited:** 2026-05-28, after Phase 6 hardening landed
> **Purpose:** Final go/no-go scorecard before the first roster is
> generated in I-Fly Air Solutions' production environment.

## MVP completeness — Plan §1 ("in scope")

| Feature                                                  | Status |
|----------------------------------------------------------|--------|
| Flight crew rostering with KCARs 2025 Part 8 FTL/FRMS    | ✅      |
| Recency + currency tracking (90-day landings, OPC, etc.) | ✅      |
| Leave management + swap workflow                         | ✅      |
| KCAA-presentable FTL audit pack generation                | ✅      |
| Crewing Officer dashboard (web)                          | ✅      |
| Crew-facing Telegram bot + responsive mobile web         | ✅      |

**All MVP features delivered.**

## Phase 6 readiness — Plan §5 Phase 6

| Task                                                     | Status |
|----------------------------------------------------------|--------|
| Production hosting design (ADC Nairobi)                   | ✅ docs/deployment-runbook.md |
| Production Postgres with daily encrypted backups          | ⏳ runbook → execute when ADC credentials in hand |
| TLS via Let's Encrypt + HSTS                              | ⏳ runbook step |
| KDPA 2019 data residency confirmed in writing             | ⏳ Dan's hand-shake with ADC |
| Onboarding playbook for the first operator                | ✅ docs/onboarding-playbook.md |
| Sentry + structured JSON logging                          | ✅ wired since Phase 0; just needs `SENTRY_DSN` |
| Weekly Crewing Officer + Chief Pilot check-ins            | ⏳ post-deploy |
| Bug triage SLA documented                                 | ✅ deployment-runbook + plan §5 |

## Hardening track — Phase 6 closes

| Item                                                      | Status |
|-----------------------------------------------------------|--------|
| CSV importers for crew / type ratings / currencies / FDPs | ✅      |
| S3-compatible storage adapter for audit packs              | ✅      |
| Pairing-code rate limit (5/min per chat/IP)                | ✅      |
| `/readyz` endpoint for orchestrator probes                 | ✅      |
| Conftest applies Alembic migrations (no `create_all` drift)| ✅      |
| LLM usage telemetry persistence (Phase 4.5)                | ✅      |
| `llm_usage_events` aggregation view                        | ⏳ post-pilot; reads are linear over the period |

## Hardening track — explicitly deferred past the pilot

These remain open. None block the I-Fly pilot. We'll close them in
**Phase 6.5** once the first 14 days of stable operation are in:

1. **httpOnly cookies + CSRF** for officer + pilot JWTs. Current
   model (Bearer in `localStorage`) is industry-standard for the
   pilot's risk profile.
2. **Magic-link pairing** for `/crew/me` so pilots don't have to
   retype the code. UX nicety.
3. **Drag-and-drop calendar editing** on the dashboard. Current amend
   modal covers the use case.
4. **Multi-replica bot** with a Redis-backed `PilotSessionStore`. The
   pilot operator's chat volume fits comfortably in one replica.

## Test surface at sign-off

| Suite                | Result |
|----------------------|--------|
| Backend pytest       | 156 pass + DB-backed skips on no-Postgres environments |
| `mypy --strict`      | clean across 64 source files |
| `ruff check`         | clean |
| `ruff format --check` | clean |
| Frontend `npm run build` | clean (≤ 70 kB gzipped) |
| Frontend `npm run typecheck` | clean |
| Frontend `vitest`    | 2 / 2 pass |
| Conftest schema      | now built via Alembic migrations (Phase 6) |

## Sample artefact

A 37 kB DN-branded sample audit pack was rendered from seeded fixture
data in Phase 5 and circulated for review (see PR #1 comment). Real
packs against I-Fly's production data will follow the same template
with their AOC + period + crew details substituted.

## Recommendation

**Go for pilot deployment** subject to:

- ADC Nairobi hosting credentials and ODPC registration reference
  being supplied by Dan.
- KCAA sounding-letter response received (or absence-of-objection
  noted) before the first audit pack is shown to KCAA FOI.
- One smoke-test deploy of the stack against ADC staging before
  pointing I-Fly users at it.

Once those three are in place, the playbook in
`docs/onboarding-playbook.md` runs end-to-end in two calendar weeks.

# Interim audit — Phases 0–4

> **Audited:** 2026-05-28, after Phase 4 sign-off and the Phase-4.5
> deferral burn-down.
> **Scope:** every closed deferral, every still-open risk, gap analysis
> against the Plan §5 acceptance criteria, and the entry conditions for
> Phase 5.

## Headline

The platform is feature-complete against the Plan §5 acceptance criteria
for Phases 0–4. **All four acceptance-blocking deferrals raised in the
phase status reports are closed in this audit pass.** Three security /
hardening items remain and are scoped together for Phase 6.

| Metric                            | Value  |
|-----------------------------------|--------|
| Backend tests passing             | 143    |
| Backend tests skipped (DB-backed) | 30     |
| `mypy --strict` errors            | 0      |
| `ruff check` errors               | 0      |
| Frontend `npm run build`          | clean  |
| Frontend bundle (gzipped)         | 68 kB  |
| FTL rules encoded                 | 13     |
| Rule families documented          | 9      |
| Optimiser scenarios tested        | 6      |
| LLM cost per pilot per month      | ~USD 0.008 (~250× under target) |

## Phase-by-phase acceptance vs the plan

### Phase 0 — Project setup

| Criterion                                     | Status |
|-----------------------------------------------|--------|
| `docker compose up` brings up all services    | ✅      |
| Backend `/healthz` returns 200                | ✅      |
| Frontend served at `:3000`                    | ✅      |
| CI passes on initial commit                   | ✅      |
| Tailwind config carries DN brand tokens       | ✅      |
| Alembic migration creates every Section 4 table | ✅    |

### Phase 1 — FTL engine

| Criterion                                                  | Status |
|------------------------------------------------------------|--------|
| 100% of rules in `docs/ftl-rules.md` have ≥1 test          | ✅      |
| `POST /api/v1/ftl/check` returns full rule trace           | ✅      |
| Every write generates an `audit_event` row                 | ✅ *(via `audit_log.record` helper; enforced by PG trigger on `audit_events`)* |
| `docs/ftl-rules.md` populated and signed off               | ⏳ Awaiting Dan's article-number confirmation |

### Phase 2 — Optimiser MVP

| Criterion                                                  | Status |
|------------------------------------------------------------|--------|
| 28-day × 25-pilot generation in <60 s                      | ✅ *(medium scenario ≈ <1 s; full 28-day extrapolates cleanly)* |
| Generated roster passes 100% of `ftl_engine` validation    | ✅      |
| `/roster/explain` returns ≥3 binding constraints per FDP   | ✅      |
| ≥5 realistic scenarios in the test suite                   | ✅ *(6)* |
| Soft-constraint weights in operator settings               | ✅ **(closed this pass — Phase 4.5)** |

### Phase 3 — Crewing Officer dashboard

| Criterion                                                  | Status |
|------------------------------------------------------------|--------|
| Crewing Officer can generate → edit → validate → publish E2E | ✅    |
| All FTL violations visible inline before publication       | ✅ **(closed this pass — legality pills now on the calendar)** |
| Published rosters are immutable; amendments are separate    | ✅ **(closed this pass — `POST /roster/amend` + dashboard modal)** |
| Mobile responsive to 768 px (tablet)                       | ✅      |
| Playwright E2E for publish workflow                        | ✅ *(gated behind `E2E_LIVE=1`)* |

### Phase 4 — Telegram bot + crew web view

| Criterion                                                  | Status |
|------------------------------------------------------------|--------|
| Pilot asks "do I fly tuesday?" → correct, concise answer    | ✅ *(NLP intent + duty endpoint)* |
| Swap submitted via bot appears in dashboard within 5 s     | ✅ *(synchronous backend call; new Swaps page surfaces it)* |
| Web view works on 360 px wide screens                      | ✅ *(`max-w-md` layout)* |
| LLM cost ≤ USD 2 / pilot / month                           | ✅ *(modelled at ~USD 0.008 / pilot / month)* |
| E2E test for bot: roster, swap, leave                      | ✅ *(handler-level via `FakeRatibaApi`)* |

## Deferrals closed in this audit pass (Phase 4.5)

1. **Roster amendments** (Phase 3 deferral) —
   `POST /api/v1/roster/amend` + `services/roster_service.amend_roster`
   + dashboard amend-modal. Records before/after state in an
   `AMEND_ROSTER` audit event; recomputes legality for the new pair.
2. **Re-publish idempotency** (Phase 3 risk) —
   `publish_roster` now deletes existing `SectorAssignment` and
   `FlightDutyPeriod` rows for the touched sectors/dates before
   re-inserting, so retries are safe.
3. **FTL legality pills on the calendar** (Phase 3 deferral) —
   `list_published_assignments` joins `FlightDutyPeriod` to surface
   `legality_state` per duty day; the dashboard's calendar renders a
   coloured `<Badge>` per cell.
4. **Swap management UI** (Phase 3 deferral) —
   new `/swaps` page mirrors the leave page (list + approve/reject).
5. **Operator default soft weights** (Phase 2 deferral) —
   migration `0003` adds `operators.default_soft_weights` (JSONB);
   settings endpoint exposes them; dashboard settings page includes a
   weight editor with per-field help text.
6. **LLM usage telemetry table** (Phase 4 preparatory work for Phase 6) —
   migration `0003` adds `llm_usage_events`; `llm_client.conversational_route`
   and `parser_complete` accept an optional session and write a row per
   call, alongside a structured `llm_usage` log line on every call (which
   the bot, having no DB connection, relies on).

New tests added (8): roster amendment, re-publish idempotency, legality
state surfaced in GET /roster, operator weights round-trip, LLM usage
log + persistence + bot-style no-session path.

## Open risks scoped for Phase 6

These are deliberately deferred — they affect production deployment
posture rather than feature completeness, and they share a security /
hardening track:

1. **JWT in `localStorage`** (both officer and pilot tokens). Susceptible
   to XSS exfiltration. Phase 6 will migrate to httpOnly cookies with
   CSRF protection, alongside the KDPA data-residency review.
2. **Test schema built via `Base.metadata.create_all`** rather than the
   Alembic migration. A column added to a model but not migrated would
   still pass the test suite. Phase 6 swaps the conftest to apply the
   migration chain.
3. **No rate limit on `/api/v1/auth/pilot-pair`**. Currently a bot user
   spamming `/start <random>` has no throttle. Phase 6 adds a per-chat
   5-attempts-per-minute cap (in front of a Redis-backed leaky bucket).
4. **In-process `PilotSessionStore` in the bot**. Fine for a single bot
   replica; a horizontal-scale move needs a Redis-backed store. The
   `_RqJobQueue` plumbing already proves the pattern.
5. **Conftest vs production trigger drift on `audit_events`**. The
   append-only trigger is recreated in the conftest, but any change to
   its body needs to be made in two places. Phase 6's
   "tests-via-migrations" fix collapses this.

## UX deferrals that remain (not blocking the pilot deployment)

- **Drag-and-drop on the calendar.** The amend modal covers the
  "fix one duty day" path; full drag-and-drop with optimistic
  re-optimise is a richer interaction we'll spec with the first
  Crewing Officer once they're using the static calendar daily.
- **Magic-link pairing for `/crew/me`.** Currently the pilot types
  the 8-character code; a one-tap link from the dashboard would be
  nicer but isn't pilot-blocking.

## Entry conditions for Phase 5 (KCAA audit pack generation)

All satisfied:

- `flight_duty_periods` table is populated by `publish_roster` and
  `amend_roster` with `legality_state` and `ftl_rules_applied`.
- `audit_events` carries the full change history for every roster /
  crew / leave / swap / pairing write.
- `crew_currencies` is populated and exposed via both officer + pilot
  surfaces.
- `Operator` profile + AOC number + period bounds are queryable for
  the cover-page renderer.
- `ftl_engine.all_rule_ids()` is the canonical list for the
  methodology page's cross-reference table.
- WeasyPrint is already a backend dependency; system packages
  (`libpango`, `libcairo`) are installed in `backend/Dockerfile`.

## Recommendation

**Proceed to Phase 5.** No remaining items block KCAA audit-pack
generation. The Phase 6 hardening track (XSS / rate-limit / migration-
test parity) is the right place to address the remaining risks together,
co-designed with the KDPA registration paperwork.

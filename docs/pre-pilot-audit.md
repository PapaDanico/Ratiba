# Pre-feedback audit — readiness for prospective-user evaluation

> **Audited:** 2026-05-28, after ADR 0006 redirected from "deploy to
> first pilot operator" to "gather feedback from 1–2 prospective users".
> **Purpose:** Final scorecard before sharing Ratiba with prospective
> Crewing Officers / Chief Pilots / DFOs.

## Headline

**The MVP is feature-complete against Plan §1 and ready for prospective-
user evaluation.** Anyone with Docker can clone the repo, run one
command, and have a populated dashboard within 10 minutes.

## MVP completeness — Plan §1 ("in scope")

| Feature                                                  | Status |
|----------------------------------------------------------|--------|
| Flight crew rostering with KCARs 2025 Part 8 FTL/FRMS    | ✅      |
| Recency + currency tracking (90-day landings, OPC, etc.) | ✅      |
| Leave management + swap workflow                         | ✅      |
| KCAA-presentable FTL audit pack generation                | ✅      |
| Crewing Officer dashboard (web)                          | ✅      |
| Crew-facing Telegram bot + responsive mobile web         | ✅      |

## Prospective-user evaluation readiness

| Item                                                      | Status |
|-----------------------------------------------------------|--------|
| One-command `docker compose up` brings the stack live      | ✅      |
| `scripts/seed.py --demo` populates two fictional operators with realistic data | ✅      |
| `docs/getting-started.md` — 10-minute clone-to-dashboard guide | ✅      |
| `docs/walkthrough.md` — guided click-path + feedback questions | ✅      |
| Sample CSVs at `docs/sample-csvs/` for the importers       | ✅      |
| Sample audit pack PDF circulated (Phase 5 status report)   | ✅      |
| KCAA sounding-letter draft for operators to send their FOI | ✅      |
| FTL rule cross-reference shipped with every audit pack     | ✅      |

## Test surface at sign-off

| Suite                | Result |
|----------------------|--------|
| Backend pytest       | 149 pass + DB-backed skips on no-Postgres envs |
| `mypy --strict`      | clean across 66 source files |
| `ruff check` + format | clean |
| Conftest schema      | built via Alembic migration chain (no `create_all` drift) |
| Frontend pipeline    | lint + prettier + typecheck + vitest + build all clean |

## What's intentionally deferred until 1–2 user conversations have happened

Per ADR 0006:

1. **First-pilot contractual lock-in** — operator selection (I-Fly,
   Jubba, or another) and hosting region (ADC Nairobi, AWS Cape Town).
   Both decisions wait for actual user feedback to refine them.
2. **ODPC (KDPA 2019) registration** — required for a paid pilot;
   not required for an evaluation against operator-supplied data on
   their own infrastructure.
3. **httpOnly cookies + CSRF migration** for JWTs — the LocalStorage
   token model is industry-standard for evaluations; we'll close this
   when we're moving toward the first paid pilot.
4. **Drag-and-drop calendar editing**, **magic-link pairing**,
   **multi-replica bot** with Redis-backed session store — all UX
   niceties that don't block evaluation.

## Recommendation

**Share Ratiba with 1–2 prospective users.** The minimum-viable
evaluation experience is:

- Send them this repo URL + the [`docs/walkthrough.md`](walkthrough.md)
  link.
- (Optional) host the demo somewhere they can hit without running
  Docker themselves — e.g. a temporary `fly.io` or single-VM deploy.
- Schedule a 30-minute follow-up to walk through their answers to the
  four feedback questions in the walkthrough.

The product surface won't change between this audit and the start of
those conversations.

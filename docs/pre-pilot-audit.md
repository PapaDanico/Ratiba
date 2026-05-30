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

> **Addendum (post-audit, this cycle):** items 3 and 4 below were listed
> here as *deferred* but have since been **delivered** — see the dated
> addendum at the foot of this document.

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

---

## Addendum — capabilities delivered after the audit

This pass shipped several items the audit above had marked deferred or
roadmap, all verified (backend suite + live browser checks) and CI-green:

- **Security hardening:** JWTs moved off `localStorage` to **httpOnly
  cookies with CSRF** (double-submit) for both officer and pilot web
  surfaces; refresh-token logout-revocation fix; **Redis-backed bot
  session store** for multi-replica.
- **FTL engine:** the two roadmap rules — **reserve sleep-opportunity**
  (CAA-AC-OPS033 §4.6.8) and **weekly recovery rest** (§4.6.2) — plus a
  weekly-rest constraint in the optimiser and a cascading FTL recompute
  on amendments.
- **Roster UX:** **drag-and-drop** crew reassignment with live FTL
  re-check + role guard, and a comfortable/compact density toggle.
- **Crew comms:** **one-tap magic-link pairing** and **WhatsApp / SMS /
  email** sharing of duties, rosters and the pairing link; an Africa's
  Talking **WhatsApp** notify channel (credential-gated).
- **UI polish:** calm-grid tables (rhythm, hover-reveal actions, mobile
  card-collapse fix), `EmptyState` component, sticky headers, loading
  skeletons, a dashboard "one thing that needs you" attention hero, and
  column sort.

Net effect on the recommendation: unchanged — **still ready to share with
1–2 prospective users**, now with a more complete and polished surface.

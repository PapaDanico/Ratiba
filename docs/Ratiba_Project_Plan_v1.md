# Ratiba — AI-Anchored Crew Rostering Platform
## Project Plan v1.0 for Claude Code Execution

**Working name:** Ratiba *(Swahili for "schedule" — to be confirmed by Capt. Dan)*
**Sponsor:** Capt. Dan Ng'ong'a / DN Consultancy
**Plan version:** 1.0
**Issued:** 27 May 2026
**Target first deployment:** ~16 weeks from kick-off (Phase 0 → Phase 6)

---

## 0. How To Use This Document

This is a complete execution spec. Claude Code should read the whole document before starting, then execute phase-by-phase. Before Phase 1, ask Capt. Dan the three confirmation questions in Section 11. At the end of each phase, produce a short status report and wait for Dan to approve the merge before moving to the next.

No work outside this spec without an explicit instruction from Capt. Dan. If a design decision is required that isn't covered here, propose two options with trade-offs and wait.

---

## 1. Product Purpose

Ratiba is a crew rostering platform purpose-built for sub-scale aviation operators (3–10 aircraft, 15–60 flight crew) in East Africa. It combines a deterministic optimiser (Google OR-Tools CP-SAT) with LLM-anchored configuration and a conversational crew interface, priced and implemented for the segment that existing enterprise tools (Sabre AirOps, Jeppesen NetLine, AIMS) structurally cannot serve.

### In scope (MVP — this plan)
- Flight crew rostering with KCARs 2025 Part 8 FTL/FRMS compliance
- Recency and currency tracking (90-day landings, OPC/LPC, line check, route familiarisation)
- Leave management and swap workflow
- KCAA-presentable FTL audit pack generation
- Crewing Officer dashboard (web)
- Crew-facing Telegram bot + responsive mobile web

### Explicitly out of scope (deferred)
- Cabin crew, engineers, ground staff (future versions)
- Real-time disruption recovery with predictive elements
- Full FOS/FRMS biomathematical fatigue modelling
- Integration with Sabre, Amadeus, or other PSS systems
- Native iOS/Android apps (Telegram + web first)

---

## 2. Technical Stack and Rationale

| Layer | Choice | Rationale |
|---|---|---|
| Backend language | Python 3.12 | Strong ecosystem for OR-Tools, Anthropic SDK, FastAPI |
| API framework | FastAPI | Clean async APIs; OpenAPI auto-generated; matches Python stack |
| Optimiser | Google OR-Tools (CP-SAT solver) | Open source, deterministic, fully auditable for KCAA. Industry-standard for constraint scheduling. |
| LLM | Anthropic Claude API | Claude Sonnet 4.5 for OM-A parsing (complex); Claude Haiku 4.5 for conversational routing (low cost) |
| Database | PostgreSQL 16 | ACID guarantees required for crew records + audit trail; supported on regional cloud |
| Cache / job queue | Redis 7 | Async job queue for optimiser runs; session cache |
| Frontend framework | React 18 + TypeScript | Mature, well-supported, matches DN brand standards |
| Frontend styling | Tailwind CSS + shadcn/ui | Production-grade UI; uses DN brand palette |
| Crew interface | Telegram Bot API + responsive web | Telegram widely used by EAC crew; zero app-store friction |
| Auth | JWT (self-hosted) for MVP; Auth0 as upgrade path | KDPA 2019 compliance; strict on sensitive data |
| Container | Docker + docker-compose | Standard dev environment |
| Production hosting | AWS Cape Town (af-south-1) OR Africa Data Centres / Liquid (Nairobi) | KDPA data residency; KCAA expectation |
| CI/CD | GitHub Actions | Standard; lint + test + build on every PR |
| Testing | pytest (Python), Playwright (E2E) | Comprehensive unit + integration + E2E coverage |
| Observability | Sentry + structured JSON logging | Sufficient for MVP scale |
| PDF generation | WeasyPrint | HTML → PDF; clean styling control for audit pack |

### Linting and code quality
- Python: `ruff` + `mypy --strict`
- TypeScript: `eslint` + `prettier` + strict `tsconfig`
- All PRs must pass CI before merge

---

## 3. Repository Structure

Initialise the repo exactly as below in Phase 0:

```
ratiba/
├── README.md
├── docker-compose.yml
├── .env.example
├── .github/
│   └── workflows/
│       ├── backend-ci.yml
│       ├── frontend-ci.yml
│       └── deploy.yml
├── pyproject.toml
├── backend/
│   ├── Dockerfile
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI entry
│   │   ├── core/
│   │   │   ├── config.py            # Pydantic Settings
│   │   │   ├── security.py          # JWT, password hashing
│   │   │   └── database.py          # SQLAlchemy session
│   │   ├── models/                  # SQLAlchemy ORM
│   │   │   ├── crew.py
│   │   │   ├── roster.py
│   │   │   ├── ftl.py
│   │   │   ├── training.py
│   │   │   ├── leave.py
│   │   │   ├── swap.py
│   │   │   └── audit.py
│   │   ├── schemas/                 # Pydantic models for API
│   │   ├── api/v1/
│   │   │   ├── crew.py
│   │   │   ├── roster.py
│   │   │   ├── ftl.py
│   │   │   ├── training.py
│   │   │   ├── leave.py
│   │   │   ├── audit.py
│   │   │   └── auth.py
│   │   ├── services/
│   │   │   ├── ftl_engine.py        # KCARs 2025 Part 8 rules
│   │   │   ├── optimiser.py         # OR-Tools CP-SAT
│   │   │   ├── constraint_parser.py # LLM → constraint set (Phase 7)
│   │   │   ├── audit_pack.py        # WeasyPrint PDF generation
│   │   │   ├── audit_log.py         # Immutable event log
│   │   │   └── llm_client.py        # Anthropic SDK wrapper
│   │   └── tasks/                   # Async jobs (Redis Q)
│   ├── tests/
│   │   ├── ftl/                     # ~50 FTL rule tests
│   │   ├── optimiser/
│   │   ├── api/
│   │   └── integration/
│   └── alembic/                     # DB migrations
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── src/
│   │   ├── pages/
│   │   │   ├── dashboard/
│   │   │   ├── crew/
│   │   │   ├── roster/
│   │   │   ├── currency/
│   │   │   ├── audit/
│   │   │   └── settings/
│   │   ├── components/
│   │   ├── lib/                     # API client, hooks, utils
│   │   └── styles/
│   └── tests/
├── bot/
│   ├── Dockerfile
│   ├── telegram_bot.py
│   ├── nlp_router.py                # LLM-fronted intent routing
│   └── commands/
│       ├── roster.py
│       ├── duty.py
│       ├── currency.py
│       ├── swap.py
│       └── leave.py
├── docs/
│   ├── ftl-rules.md                 # KCARs 2025 Part 8 distilled
│   ├── data-model.md
│   ├── api.md
│   ├── audit-pack-spec.md
│   ├── brand-tokens.md              # DN palette + typography
│   └── adr/                         # Architecture Decision Records
└── scripts/
    ├── seed.py                      # Sample data for dev
    └── generate_sample_om_a.py      # For Phase 7 testing
```

---

## 4. Data Model (Core Entities)

All tables include `id` (UUID), `created_at`, `updated_at`, `created_by_user_id`. All write actions immutably journalled to `audit_events`.

### `crew`
- `employee_no` (unique per operator)
- `first_name`, `last_name`
- `role` (enum: CAPT, FO, SO)
- `date_of_hire`, `date_of_birth`
- `base_station` (ICAO code: HKJK, HKWJ, etc.)
- `contract_type` (enum: FULL_TIME, CONTRACT, FREELANCE)
- `active` (bool)
- `languages` (array)
- `faith_observance_flags` (jsonb: `{sunday_protected: bool, ramadan_sensitive: bool, family_school_term: bool}`)

### `crew_type_rating`
- `crew_id`, `aircraft_type`, `valid_from`, `valid_until`, `evidence_ref`

### `crew_currency`
- `crew_id`
- `currency_type` (enum: LANDINGS_90D, ROUTE_FAM, MEL_COMP, LINE_CHECK, OPC, LPC, EMERG_PROC, FIRST_AID, DG, CRM, SEC_TRAINING)
- `last_completed_date`, `expires_date`, `evidence_ref`

### `flight_duty_period` (FDP)
- `crew_id`, `date`, `report_time`, `off_duty_time`
- `sectors_count`, `flight_hours`, `duty_hours`
- `type` (enum: FDP, STANDBY, POSITIONING, TRAINING, OFF, LEAVE, SICK)
- `legality_state` (enum: LEGAL, AT_LIMIT, REQUIRES_FRMS_DEROGATION, ILLEGAL)
- `ftl_rules_applied` (array of rule_id strings)

### `sector`
- `flight_no`, `date`, `origin`, `destination`
- `std`, `sta`, `atd`, `ata` (scheduled vs actual)
- `aircraft_reg`, `aircraft_type`
- `status` (enum: PLANNED, PUBLISHED, OPERATING, COMPLETED, CANCELLED)

### `sector_assignment`
- `sector_id`, `crew_id`, `role_on_sector` (CAPT, FO, RELIEF, etc.)

### `leave_request`
- `crew_id`, `type` (ANNUAL, SICK, COMPASSIONATE, FAITH, OTHER)
- `date_from`, `date_to`, `status` (PENDING, APPROVED, REJECTED)
- `note`, `approver_id`

### `swap_request`
- `crew_id_initiator`, `crew_id_counterparty`, `fdp_or_sector_ref`
- `reason`, `status`, `approver_id`

### `ftl_rule`
- `rule_id` (e.g., `KCAR-P8-FDP-MAX-13H`)
- `description`, `regulation_ref` (e.g., `KCARs 2025 Part 8 §8.X.Y`)
- `calculation_logic_ref` (function name in `ftl_engine.py`)
- `applies_to` (array: CAPT, FO, etc.)
- `source` (enum: MANUAL_REVIEW, LLM_PARSED, OM_A_REVISION_X)

### `audit_event`
- `actor_user_id`, `action`, `entity_type`, `entity_id`
- `before_state` (jsonb), `after_state` (jsonb)
- Timestamps immutable; no UPDATE or DELETE on this table.

### `operator`
- For multi-tenancy from Day 1. Every row in every other table has `operator_id`.
- `aoc_number`, `name`, `base`, `contact_email`, `tier` (ENTRY, STANDARD, PLUS)

---

## 5. Phase-Gated Delivery Plan

### Phase 0 — Project Setup (Week 0)

**Goal:** Repo and full dev environment live.

Tasks:
1. Initialise git repo, structure as in Section 3
2. `docker-compose.yml` with services: postgres, redis, backend (FastAPI), frontend (Vite dev), bot
3. `.env.example` with every required key (see Section 7)
4. GitHub Actions CI: lint (ruff, mypy, eslint), test (pytest, Playwright placeholders), build
5. `README.md` with one-command getting-started: `docker compose up`
6. Initial Alembic migration creating all tables from Section 4
7. Skeleton FastAPI app with `/healthz` returning 200
8. Skeleton React app with DN brand colours wired in Tailwind config

**Acceptance criteria:**
- Fresh clone runs `docker compose up`; all services healthy
- Frontend loads at `http://localhost:3000`
- Backend healthcheck returns 200 at `http://localhost:8000/healthz`
- CI passes on the initial commit
- Tailwind config has DN brand tokens loaded from `docs/brand-tokens.md`

---

### Phase 1 — FTL Engine + Core Data Model (Weeks 1–3)

**Goal:** Every KCARs 2025 Part 8 FTL rule encoded, tested, queryable via API.

Tasks:
1. Complete SQLAlchemy models for all entities in Section 4
2. Implement `ftl_engine.py`:
   - Each rule a pure function with explicit inputs and a structured verdict
   - Verdict includes: `legality_state`, `rule_id`, `reason`, `regulation_ref`
3. Encode KCARs 2025 Part 8 rules from `docs/ftl-rules.md`. Baseline rules (minimum set):
   - Max FDP by start time + sectors flown
   - Mandatory rest before next FDP (minimum hours, augmented vs basic)
   - Cumulative duty hours (7 days, 28 days, 365 days)
   - Cumulative block hours (28 days, 365 days)
   - Standby duty rules (short-call vs long-call)
   - Split duty allowances
   - Time-zone crossing recovery
   - Discretion / commander's discretion logging
4. Write at least 50 pytest test cases covering edge cases for each rule
5. API endpoints:
   - `POST /api/v1/ftl/check` — accepts a roster slice, returns legality per FDP
   - `POST /api/v1/ftl/validate-fdp` — single FDP check with full rule trace
6. Audit log on every write

**Acceptance criteria:**
- 100% of FTL rules in `docs/ftl-rules.md` have ≥1 test
- All tests pass on CI
- `POST /api/v1/ftl/check` returns full rule trace per FDP
- Every write to any table generates an `audit_event` row
- Documentation: `docs/ftl-rules.md` complete and reviewed (Dan signs off)

**Open dependency for Dan:** confirm whether the `ftl-rules.md` baseline should reflect generic KCARs 2025 Part 8, OR the specific OM-A FTL chapter of the first pilot operator. Default = generic, customised in Phase 6.

---

### Phase 2 — Optimiser MVP (Weeks 4–6)

**Goal:** Given a sector schedule and a crew pool, produce a legal, well-optimised roster.

Tasks:
1. Build OR-Tools CP-SAT model in `optimiser.py` encoding **hard constraints**:
   - Every sector covered by required crew complement (Captain + FO at minimum)
   - No FTL breach (calls into `ftl_engine`)
   - Required type rating on the aircraft
   - Required currency (90-day landings on type, etc.)
   - No conflicting commitments (leave, training, off-day)
2. **Soft constraints** (objective function weights, all configurable per operator):
   - Balanced block hours across crew
   - Faith-observance respect (Sunday protection, Ramadan, etc.)
   - Minimum positioning
   - Honoured leave requests
3. API endpoints:
   - `POST /api/v1/roster/generate` (async) → returns `job_id`
   - `GET /api/v1/roster/jobs/{job_id}` → status + result when ready
   - `POST /api/v1/roster/explain` → for a given FDP, return the binding constraints (which rules drove this assignment)
4. Implement async job runner using Redis as queue
5. Optimiser run timeout: 60 seconds for 28-day × 25-pilot input; fail clearly if exceeded

**Acceptance criteria:**
- Generate a 28-day roster for a 25-pilot, 5-aircraft operator in <60 seconds
- Generated roster passes 100% of `ftl_engine` validation
- `POST /api/v1/roster/explain` returns ≥3 binding constraints per FDP
- Test suite includes at least 5 realistic operator scenarios (small / medium / edge cases)
- Soft-constraint weights surfaced in operator settings table for tuning

---

### Phase 3 — Crewing Officer Dashboard (Weeks 7–8)

**Goal:** Crewing Officer can do their full job in the dashboard.

Tasks:
1. React + TypeScript + Tailwind + shadcn/ui
2. DN brand palette wired (steel blue `#4A7FA5`, gold `#C9A84C`, dark `#1C1C1C`, fog `#F4F4F2`, plus state colours green/red/amber from `docs/brand-tokens.md`)
3. Cormorant Garamond (display) + DM Sans (body) — Google Fonts
4. Pages:
   - **Login** (JWT auth)
   - **Roster calendar** (28-day rolling grid, drag-and-drop, re-optimise on change)
   - **Inline FTL violation indicators** with rule references
   - **Currency dashboard** — every crew member's status, expiry traffic-light
   - **Leave management** — pending requests, approve/reject
   - **Swap management** — pending swaps, approve/reject with FTL impact preview
   - **Publish roster** workflow — once published, immutable; further changes are amendments with full audit trail
   - **Audit pack** generation button (links to Phase 5)
   - **Settings** — operator profile, FTL rule tuning (with warning gate), faith-observance toggles per crew member
5. Branded loading states, error states, success states

**Acceptance criteria:**
- Crewing Officer can generate → edit → validate → publish a 28-day roster end-to-end in the app, no need to drop to Excel
- All FTL violations visible inline before publication is permitted
- Published rosters are immutable; amendments are recorded as separate entities with reason
- Mobile responsive down to 768px (tablet); pilots use the bot, this dashboard is desktop-first
- E2E Playwright test covers the full publish workflow

---

### Phase 4 — Crew-Facing Telegram Bot + Web View (Weeks 9–10)

**Goal:** Every pilot sees their own roster and can interact in plain language via Telegram.

Tasks:
1. Telegram bot setup; pilots link account via one-time token from dashboard
2. Bot commands:
   - `/roster` — current 14-day view
   - `/duty` — today's duty
   - `/currency` — own currency status
   - `/swap` — initiate a swap request
   - `/leave` — initiate a leave request
   - `/help` — list available actions
3. **LLM-fronted free-text handling** via Claude Haiku 4.5:
   - Route plain-language queries (e.g. "do I fly tuesday?", "swap mike for me on the 15th", "when does my opc expire?")
   - Intent extraction → backend call → natural-language response
   - Always include a structured fallback ("here are the commands I understand")
4. **Web view** at `/crew/me` — mirrors bot capability, responsive mobile-first to 360px width
5. Swap and leave requests created via bot flow to the dashboard for approval

**Acceptance criteria:**
- A pilot asks "do I fly tuesday?" in Telegram and gets a correct, concise answer with the sector details
- Swap request submitted via bot appears in the dashboard within 5 seconds
- Web view works on a 360px-wide mobile screen
- LLM cost per pilot per month modelled and documented in `docs/cost-model.md` (target: ≤USD 2/pilot/month at Haiku 4.5 prices)
- E2E test for bot covers: roster query, swap initiation, leave request

---

### Phase 5 — KCAA Audit Pack Generation (Weeks 11–12)

**Goal:** One-click generation of a KCAA-presentable FTL compliance audit pack.

Tasks:
1. PDF generator using WeasyPrint
2. DN-branded template (matches Calibri Universal Template + DN palette)
3. **Audit pack contents:**
   - Cover page: operator AOC, period, generation timestamp, generator hash signature
   - Executive summary: period overview, total FDPs, anomaly count, currency exceptions count
   - Per-crew FTL summary: FDP utilisation vs limits over rolling 7 / 28 / 365 days
   - Anomaly log: every FDP flagged AT_LIMIT or above; corrective action notes
   - Currency status snapshot at period close
   - Audit trail extract: every roster change in the period with actor, timestamp, before/after
   - Methodology page: which rules applied, regulatory references, generator version
4. API: `POST /api/v1/audit/generate` with `{ period_from, period_to, crew_filter }` → returns PDF
5. Storage: completed audit packs versioned in object storage (S3-compatible) with retention

**Acceptance criteria:**
- A 90-day audit pack for a 25-pilot operator generates in <30 seconds
- Pack is visually professional, DN-branded, self-contained (no external assets)
- Pack includes a regulatory cross-reference table mapping every assertion to a KCARs 2025 article
- Hash signature ensures pack tamper-evidence; verification endpoint provided

**Critical dependency for Dan (before this phase):** send a 1-page sounding letter to KCAA Flight Operations Inspectorate (FOI) on audit-pack format acceptability. Use template at `docs/kcaa-sounding-letter.md` (Claude Code to draft in Phase 0).

---

### Phase 6 — Pilot Deployment + 30-Day Stability (Weeks 13–16)

**Goal:** Ratiba is in production at the first paying operator.

Tasks:
1. Production hosting setup (AWS Cape Town or Africa Data Centres Nairobi — Dan to confirm)
2. Production PostgreSQL with daily encrypted backups
3. TLS via Let's Encrypt; HSTS enabled
4. KDPA 2019 data residency confirmed in writing from hosting provider
5. **Onboarding playbook** for first operator (auto-generated from manual implementation experience):
   - Import existing crew records (CSV template)
   - Import type ratings and currencies
   - Manual constraint set configuration (Phase 7 will automate this)
   - Roster historical import (last 90 days for context)
6. Sentry integration + structured logging in CloudWatch / equivalent
7. Weekly Crewing Officer + Chief Pilot check-ins (Capt. Dan facilitates)
8. Bug triage SLA: critical = 4 hours; high = 24 hours; medium = 5 days

**Acceptance criteria:**
- One full roster cycle (28 days) generated, published, and operated **without manual override**
- Zero critical bugs in production for 14 consecutive days before sign-off
- Crewing Officer self-reports ≥50% reduction in rostering hours vs Excel baseline
- KCAA audit pack generated and presented (at least informally) to the operator's regulatory contact

---

### Phase 7 — LLM Constraint Parser (Months 4–6, post-pilot)

**Goal:** New operator onboarding collapses from 6 weeks to 2 weeks.

Tasks:
1. **Constraint parser pipeline** using Claude Sonnet 4.5:
   - Input: operator OM-A FTL chapter (PDF or DOCX)
   - Output: proposed constraint set (YAML/JSON) mapped to internal rule schema
2. **Human-review interface**:
   - Diff against KCARs 2025 baseline
   - Accept / reject / edit each proposed rule
   - Comment trail on every decision
3. **Round-trip validation**:
   - Parsed constraint set applied to a known historical roster
   - Must match human-coded baseline within ±2% on FTL legality verdicts
4. Constraint set versioning tied to OM-A revision number
5. Reduced onboarding playbook: 2 weeks elapsed for operator #2

**Acceptance criteria:**
- ≥90% of FTL rules in a real OM-A correctly parsed and proposed (measured against human-coded ground truth)
- Total human review time for new operator constraint set: <8 hours
- Operator #2 fully configured in ≤2 weeks elapsed vs ≥6 weeks for operator #1

---

## 6. API Surface (v1)

All endpoints under `/api/v1/`. JWT required except `/auth/login`.

```
POST   /auth/login
POST   /auth/refresh
POST   /auth/logout

GET    /crew
POST   /crew
GET    /crew/{id}
PATCH  /crew/{id}
GET    /crew/{id}/currency
POST   /crew/{id}/currency

GET    /roster?from=&to=
POST   /roster/generate              # async, returns job_id
GET    /roster/jobs/{job_id}
POST   /roster/publish               # makes roster immutable
POST   /roster/amend                 # post-publication amendment
POST   /roster/explain               # binding constraints for an FDP

POST   /ftl/check                    # roster slice → legality verdict
POST   /ftl/validate-fdp             # single FDP → full rule trace

POST   /leave                        # crew submits
GET    /leave?status=PENDING
PATCH  /leave/{id}                   # approver action

POST   /swap                         # crew submits
GET    /swap?status=PENDING
PATCH  /swap/{id}                    # approver action

POST   /audit/generate               # async PDF generation
GET    /audit/packs?from=&to=
GET    /audit/packs/{id}/download
GET    /audit/packs/{id}/verify      # hash verification

GET    /settings/operator
PATCH  /settings/operator
GET    /settings/ftl-rules
PATCH  /settings/ftl-rules/{rule_id}
```

OpenAPI spec auto-generated by FastAPI; published to `/docs`.

---

## 7. Environment Variables (.env.example)

```bash
# Database
DATABASE_URL=postgresql://ratiba:dev_password@db:5432/ratiba
TEST_DATABASE_URL=postgresql://ratiba:dev_password@db:5432/ratiba_test

# Redis
REDIS_URL=redis://redis:6379/0

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL_PARSER=claude-sonnet-4-5
ANTHROPIC_MODEL_CONVERSATIONAL=claude-haiku-4-5

# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_WEBHOOK_URL=https://api.ratiba.aero/bot/webhook

# Security
SECRET_KEY=...                     # generate via openssl rand -hex 32
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# Compliance
KDPA_DATA_REGION=ke-1
KDPA_REGISTRATION_REF=...           # ODPC registration number

# Observability
SENTRY_DSN=...
LOG_LEVEL=INFO

# URLs
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

---

## 8. Brand Tokens

Wire these into `docs/brand-tokens.md` and `tailwind.config.ts` in Phase 0.

```
DN_DARK     #1C1C1C   (primary text, headers)
DN_STEEL    #4A7FA5   (secondary, section banners)
DN_STEEL_LT #D6E4F0   (tint backgrounds)
DN_GOLD     #C9A84C   (accents, dividers)
DN_GOLD_LT  #FFF8E6   (callout panels)
DN_FOG      #F4F4F2   (alternating rows, panels)
DN_MUTED    #6B7280   (body text, captions)
DN_GREEN    #1E8449   (compliant / positive)
DN_RED      #C0392B   (alerts / critical)
DN_AMBER    #D4AC0D   (watch items)

Display font: Cormorant Garamond
Body font:    DM Sans
Code/data:    JetBrains Mono
```

---

## 9. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| KCAA does not accept generated audit pack as evidence | Medium | High | Phase 0: Claude Code drafts sounding letter; Dan sends before Phase 5; co-design pack format with KCAA feedback |
| OM-A too unstructured for LLM parser to hit 90% accuracy | Medium | Medium | Phase 7 spike on real OM-A before commitment; manual fallback always available |
| First operator does not pay agreed monthly fee post-pilot | High | High | Pilot fee paid up-front for 90 days; 6-month minimum commitment in contract |
| Telegram bot fails at scale (>50 pilots) | Low | Medium | Web fallback always works; native app deferred to Phase 8+ if multi-operator demand |
| Anthropic API outage interrupts conversational interface | Low | Low | Bot falls back to command-only mode; roster generation never depends on LLM |
| Crew data leak (KDPA violation) | Low | Critical | Phase 1 hardening — encryption at rest, TLS, audit log, KDPA registration, regional hosting |
| OR-Tools fails at >10 aircraft operators | Low | Medium | Phase 7 stress test; alternative solvers (Gurobi commercial) as upgrade path |
| Working name "Ratiba" already trademarked in Kenya/region | Medium | Low | Dan to do a quick trademark check before Phase 1 |

---

## 10. What Capt. Dan Does (vs. Claude Code)

| Activity | Owner |
|---|---|
| Confirm working name (Ratiba or alternative) | Dan |
| Confirm first pilot operator (Jetways or Jubba) | Dan |
| Supply OM-A FTL chapter for first operator | Dan |
| Sounding letter to KCAA FOI on audit-pack acceptability | Dan sends; Claude Code drafts |
| Negotiate pilot contract with first operator | Dan |
| ODPC (KDPA) registration | Dan |
| Code all software | Claude Code |
| Write all tests | Claude Code |
| Build CI/CD | Claude Code |
| Architecture Decision Records (ADRs) for every non-trivial choice | Claude Code |
| PR descriptions with full context | Claude Code |
| Final review + merge on PRs | Dan |
| Production deployment | Joint — Dan supplies credentials; Claude Code executes |
| Weekly phase-end status report | Claude Code |
| Phase sign-off | Dan |

---

## 11. Three Questions Before Phase 1

Claude Code should complete Phase 0, then **pause and ask Capt. Dan** the following three questions before proceeding to Phase 1:

1. **Working name confirmed?** Is "Ratiba" approved, or should the project be renamed? (Quick trademark search advised.)
2. **First pilot operator confirmed?** Jetways or Jubba — which is the Phase 6 deployment target? This affects whose OM-A is used as the constraint baseline.
3. **OM-A baseline for `docs/ftl-rules.md`?** Should Phase 1 build the generic KCARs 2025 Part 8 baseline (recommended), with the first operator's specifics layered in Phase 6 — or should we start with the operator's OM-A from Day 1?

Default assumptions if Dan does not respond within the day:
- Name: Ratiba (proceed)
- Pilot operator: Jetways (proceed)
- Baseline: generic KCARs 2025 Part 8 (proceed)

---

## 12. Phase Sign-Off Protocol

At the end of each phase, Claude Code produces a status report containing:

1. **What was built** — files added/changed, key design decisions
2. **What was tested** — test results, coverage delta
3. **What's open** — anything explicitly deferred to a later phase
4. **Risks surfaced** — anything discovered that changes a future-phase assumption
5. **Next phase plan** — concrete first three tasks for the upcoming phase

Dan reviews, signs off (or pushes back), and Claude Code proceeds.

---

## 13. Document Versioning

This plan is version 1.0. Material changes (scope, stack, phasing) require a new version number and a changelog entry. Minor clarifications can be inline-edited with a date stamp.

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-27 | Capt. Dan Ng'ong'a + Claude | Initial plan |

---

**End of Project Plan v1.0**

# Ratiba

> *Swahili for "schedule"* — AI-anchored crew rostering for sub-scale East African aviation operators.

Ratiba is a working MVP for the segment that enterprise tools (Sabre AirOps,
Jeppesen NetLine, AIMS) structurally cannot serve: 3–10 aircraft, 15–60 flight
crew, KCARs 2025 Part 8 compliance, run by a single Crewing Officer on Excel
today.

It combines a deterministic optimiser (Google OR-Tools CP-SAT) with LLM-anchored
configuration (Claude Haiku 4.5 for the bot, Claude Sonnet 4.5 for OM-A
parsing) and a conversational crew interface (Telegram + responsive mobile web).

## Try it — 10 minutes

You need Docker and Docker Compose. Nothing else — no cloud credentials,
no API keys, no contracts.

```bash
git clone https://github.com/papadanico/ratiba.git
cd ratiba
cp .env.example .env
docker compose up --build
# wait for "Application startup complete." then in a second terminal:
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed.py --demo
```

Open http://localhost:3000 and log in:

- **Acacia Air** — `officer@demo-aoc-ac.example.aero` / `hunter2pass`
- **Maendeleo Aviation** — `officer@demo-aoc-ma.example.aero` / `hunter2pass`

You'll find two fictional operators with realistic crew, mixed currency states,
a 14-day published roster, pending leave + swap requests, and a generated KCAA
audit pack ready to download.

See [`docs/walkthrough.md`](docs/walkthrough.md) for a guided click-path through
every screen + the questions whose answers we want from you.

## What's in the box

| Capability                                | Where                                     |
|-------------------------------------------|-------------------------------------------|
| KCARs 2025 Part 8 FTL engine — 13 rules   | `backend/app/services/ftl_engine.py`      |
| OR-Tools CP-SAT roster optimiser           | `backend/app/services/optimiser.py`       |
| Crewing-Officer dashboard                  | `frontend/src/pages/`                     |
| `/crew/me` mobile-first pilot web view     | `frontend/src/pages/me/`                  |
| Telegram bot + LLM intent routing          | `bot/`                                    |
| KCAA-presentable audit pack (PDF)          | `backend/app/services/audit_pack.py`      |
| Append-only audit trail (PG trigger)       | `backend/alembic/versions/0001_initial_schema.py` |
| CSV importers for onboarding               | `backend/app/services/imports.py`         |

For the full plan see [`docs/Ratiba_Project_Plan_v1.md`](docs/Ratiba_Project_Plan_v1.md).

---

## Service map

| Service  | URL                        | Description                       |
|----------|----------------------------|-----------------------------------|
| frontend | http://localhost:3000      | React + Vite dashboard            |
| backend  | http://localhost:8000      | FastAPI; OpenAPI at `/docs`       |
| backend healthcheck | http://localhost:8000/healthz |                      |
| backend readiness  | http://localhost:8000/readyz  |                      |
| db       | localhost:5432             | PostgreSQL 16                     |
| redis    | localhost:6379             | Redis 7                           |
| bot      | (long-poll, no port)       | Telegram bot worker (idle until token set) |

---

## Repository layout

```
ratiba/
├── backend/          FastAPI + SQLAlchemy + OR-Tools + Anthropic SDK
├── frontend/         React 18 + TypeScript + Tailwind + shadcn/ui
├── bot/              Telegram bot + LLM-fronted NLP routing
├── docs/             Project plan, FTL rules, brand tokens, ADRs
├── scripts/          Dev seeds, sample OM-A generation
└── .github/          CI workflows
```

---

## Development

Backend (Python 3.12):

```bash
cd backend
pip install -e ../[dev]      # installs from root pyproject.toml
ruff check .
mypy app
pytest
```

Frontend (Node 20):

```bash
cd frontend
npm install
npm run lint
npm run typecheck
npm test
npm run build
```

---

## Phase status

| Phase | Description                                | Status        |
|-------|--------------------------------------------|---------------|
| 0     | Project setup                              | Done          |
| 1     | FTL engine + core data model               | Done          |
| 2     | Optimiser MVP                              | Done          |
| 3     | Crewing Officer dashboard                  | Done          |
| 4     | Telegram bot + crew web view               | Done          |
| 5     | KCAA audit pack generation                 | Done          |
| 6     | Pilot deployment + 30-day stability        | In progress   |
| 7     | LLM constraint parser (post-pilot)         | Not started   |

---

## Licence

Proprietary. © DN Consultancy. All rights reserved.

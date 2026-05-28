# Ratiba

> *Swahili for "schedule"* — AI-anchored crew rostering for sub-scale East African aviation operators.

Ratiba combines a deterministic optimiser (Google OR-Tools CP-SAT) with LLM-anchored
configuration and a conversational crew interface, purpose-built for operators with
3–10 aircraft and 15–60 flight crew, and KCARs 2025 Part 8 FTL/FRMS compliance.

See [`docs/Ratiba_Project_Plan_v1.md`](docs/Ratiba_Project_Plan_v1.md) for the full plan.

---

## Quick start

You need Docker and Docker Compose.

```bash
cp .env.example .env          # fill in ANTHROPIC_API_KEY etc. when you need them
docker compose up --build
```

That brings up:

| Service  | URL                        | Description                       |
|----------|----------------------------|-----------------------------------|
| frontend | http://localhost:3000      | React + Vite dashboard            |
| backend  | http://localhost:8000      | FastAPI; OpenAPI at `/docs`       |
| backend healthcheck | http://localhost:8000/healthz |                      |
| db       | localhost:5432             | PostgreSQL 16                     |
| redis    | localhost:6379             | Redis 7                           |
| bot      | (long-poll, no port)       | Telegram bot worker               |

To apply database migrations:

```bash
docker compose exec backend alembic upgrade head
```

To seed sample data for development:

```bash
docker compose exec backend python scripts/seed.py
```

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
| 2     | Optimiser MVP                              | In progress   |
| 3     | Crewing Officer dashboard                  | Not started   |
| 4     | Telegram bot + crew web view               | Not started   |
| 5     | KCAA audit pack generation                 | Not started   |
| 6     | Pilot deployment + 30-day stability        | Not started   |
| 7     | LLM constraint parser (post-pilot)         | Not started   |

---

## Licence

Proprietary. © DN Consultancy. All rights reserved.

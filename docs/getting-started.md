# Getting started — 10 minutes from clone to dashboard

This guide takes you from a fresh `git clone` to a populated dashboard
with two operators, mixed currency states, a 14-day published roster,
pending leave + swap requests, and a downloadable KCAA audit pack.

## Prerequisites

- Docker + Docker Compose
- ~2 GB free disk for the containers + node_modules

That's it. No cloud credentials, no Anthropic API key, no Telegram bot
token. Ratiba runs end-to-end on your laptop.

## Steps

```bash
# 1. Clone
git clone https://github.com/papadanico/ratiba.git
cd ratiba

# 2. Seed the environment file (defaults are fine for local).
cp .env.example .env

# 3. Bring up the stack.
docker compose up --build

# Wait for the "Application startup complete." line from the backend
# service (about 30 s on a warm machine). Then in a second terminal:

# 4. Apply the database migrations.
docker compose exec backend alembic upgrade head

# 5. Populate two demo operators with crew, currencies, a roster, and
#    a generated audit pack.
docker compose exec backend python scripts/seed.py --demo
```

## What you have now

- **Backend API:** http://localhost:8000
  - OpenAPI explorer: http://localhost:8000/docs
  - Health probe: http://localhost:8000/healthz
- **Dashboard:** http://localhost:3000

Log in to the dashboard with either:

| Operator          | Email                                     | Password    |
|-------------------|-------------------------------------------|-------------|
| Acacia Air        | `officer@demo-aoc-ac.example.aero`        | `hunter2pass` |
| Maendeleo Aviation | `officer@demo-aoc-ma.example.aero`        | `hunter2pass` |

(Both are clearly fictional — see `scripts/seed.py` for the names.)

Once logged in, see `docs/walkthrough.md` for the suggested click-path
through the dashboard for a 10-minute evaluation.

## Bot + crew web view (optional)

The Telegram bot stays idle unless you set `TELEGRAM_BOT_TOKEN` — fine
for the evaluation. To try the `/crew/me` mobile-first web view:

1. Click into a crew member from the dashboard's Crew page.
2. Issue a pairing code (button on the crew row).
3. Open http://localhost:3000/crew/me in a phone-sized browser window.
4. Enter the code.

You're now seeing the same surface a pilot would see in Telegram.

## NLP routing (optional)

If you set `ANTHROPIC_API_KEY=sk-ant-...` in `.env`, the bot's free-text
handler uses Claude Haiku 4.5 to route plain-language questions. Without
it, the bot falls back to a keyword-based intent matcher — works fine
for evaluation, just less natural.

## Resetting

```bash
docker compose down -v   # nukes the postgres volume
```

That's it — no state outside Docker.

## Common stumbles

- **`docker compose up` hangs on the frontend** — first build pulls
  npm packages; expect ~60 s on a cold cache.
- **`/audit/generate` fails with WeasyPrint errors** — `apt`-installed
  libraries (`libpango`, `libcairo`) are baked into the backend Docker
  image; if you've rebuilt from a slim base image, see the backend
  Dockerfile for the canonical apt list.
- **CSV import returns 401** — log in first; the importers require a
  Crewing Officer JWT in the `Authorization: Bearer …` header.

#!/bin/sh
set -e

# Render injects DATABASE_URL as postgres:// (psycopg2 dialect).
# Rewrite to postgresql+psycopg:// for the psycopg v3 driver we ship.
if [ -n "$DATABASE_URL" ]; then
    DATABASE_URL=$(echo "$DATABASE_URL" | sed \
        's|^postgres://|postgresql+psycopg://|; s|^postgresql://|postgresql+psycopg://|')
    export DATABASE_URL
fi

# Schema migration must finish before we serve (fast: a no-op when current).
alembic upgrade head

# Demo seed runs in the BACKGROUND so it never blocks the API from listening.
# On Render free tier the service cold-starts on the first request; previously
# the ~7s seed ran before uvicorn, so nginx's /api proxy got a 502 during wake
# and login showed "Something went wrong". Now uvicorn starts immediately and
# the (idempotent) seed catches up behind it. Non-fatal by design.
(
    PYTHONPATH=/app python scripts/seed.py --demo \
        && echo "demo seed complete" \
        || echo "WARN: demo seed step failed; API already serving"
) &

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

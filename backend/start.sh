#!/bin/sh
set -e

# Render injects DATABASE_URL as postgres:// (psycopg2 dialect).
# Rewrite to postgresql+psycopg:// for the psycopg v3 driver we ship.
if [ -n "$DATABASE_URL" ]; then
    DATABASE_URL=$(echo "$DATABASE_URL" | sed \
        's|^postgres://|postgresql+psycopg://|; s|^postgresql://|postgresql+psycopg://|')
    export DATABASE_URL
fi

alembic upgrade head

# Load demo data on first run (idempotent — safe to run every startup).
PYTHONPATH=/app python scripts/seed.py --demo

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

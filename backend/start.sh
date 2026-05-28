#!/bin/sh
set -e

# Render (and many PaaS) inject DATABASE_URL as postgres:// or postgresql://,
# which SQLAlchemy routes to the psycopg2 driver. We ship psycopg v3, which
# requires the postgresql+psycopg:// scheme. Rewrite before anything runs.
if [ -n "$DATABASE_URL" ]; then
    DATABASE_URL=$(echo "$DATABASE_URL" | sed \
        's|^postgres://|postgresql+psycopg://|; s|^postgresql://|postgresql+psycopg://|')
    export DATABASE_URL
fi

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

#!/bin/sh
set -e

# Mirror start.sh's DSN rewrite (Render injects postgres:// → psycopg v3).
if [ -n "$DATABASE_URL" ]; then
    DATABASE_URL=$(echo "$DATABASE_URL" | sed \
        's|^postgres://|postgresql+psycopg://|; s|^postgresql://|postgresql+psycopg://|')
    export DATABASE_URL
fi

exec python scripts/run_digests.py "${DIGEST_WITHIN_DAYS:-30}"

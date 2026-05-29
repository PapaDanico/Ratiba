#!/bin/sh
set -e

# Render injects DATABASE_URL as postgres:// (psycopg2 dialect); rewrite to the
# psycopg v3 dialect the app uses (mirrors start.sh). The worker's tasks open
# their own DB session, so they need the same rewrite.
if [ -n "$DATABASE_URL" ]; then
    DATABASE_URL=$(echo "$DATABASE_URL" | sed \
        's|^postgres://|postgresql+psycopg://|; s|^postgresql://|postgresql+psycopg://|')
    export DATABASE_URL
fi

# Consume the background job queue (notifications, recurrency digest,
# roster-publish broadcast). Matches the queue name used by the API.
exec rq worker --url "$REDIS_URL" ratiba

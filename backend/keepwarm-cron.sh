#!/bin/sh
set -e

# Keep the free-tier ratiba-api web service warm so it doesn't cold-start (and
# return 502 during the ~30-60s wake) on a real user's first request.
#
# Render free web services spin down after ~15 min idle; this cron pings the
# public /healthz every 10 min to keep it up. /healthz needs no auth.
#
# API_URL is the public base URL of the ratiba-api service, e.g.
#   https://ratiba-api.onrender.com
# Set it on this cron service after the first deploy (sync: false in render.yaml).

API_URL="${API_URL:-https://ratiba-api.onrender.com}"

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Pinging $API_URL/healthz to keep warm..."

if curl -sf "$API_URL/healthz" > /dev/null 2>&1; then
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] ✓ Healthz OK (200)"
    exit 0
else
    STATUS=$?
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] ✗ Healthz failed (exit code: $STATUS)"
    # Non-fatal: a single failed ping (e.g. mid-deploy) must not fail the cron run.
    exit 0
fi

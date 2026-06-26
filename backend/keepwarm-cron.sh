#!/bin/sh
set -e

# Keep-warm cron: ping API healthz every 10 min to prevent Render free-tier cold-start.
# Invoked by: render.yaml ratiba-keepwarm cron service, schedule: "*/10 * * * *"

API_URL="${API_URL:-https://ratiba-api.onrender.com}"

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Pinging $API_URL/healthz to keep warm..."

if curl -sf "$API_URL/healthz" > /dev/null 2>&1; then
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] ✓ Healthz OK (200)"
    exit 0
else
    STATUS=$?
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] ✗ Healthz failed (exit code: $STATUS)"
    # Don't fail the cron (exit 0) even if unreachable — Render will log it.
    exit 0
fi

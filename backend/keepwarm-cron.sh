#!/bin/sh
# Keep the free-tier ratiba-api web service warm so it doesn't cold-start (and
# return 502 during the ~30-60s wake) on a real user's first request.
#
# Render free web services spin down after ~15 min idle; this cron pings the
# public /healthz every 10 min to keep it up. /healthz needs no auth.
#
# API_URL is the public base URL of the ratiba-api service, e.g.
#   https://ratiba-api.onrender.com
# Set it on this cron service after the first deploy (sync: false in render.yaml).
set -u

if [ -z "${API_URL:-}" ]; then
    echo "keepwarm: API_URL not set — skipping"
    exit 0
fi

URL="${API_URL%/}/healthz"
code=$(curl -fsS -o /dev/null -w "%{http_code}" --max-time 60 "$URL" 2>/dev/null || echo "000")
echo "keepwarm: GET $URL -> $code"
# Non-fatal: a single failed ping (e.g. mid-deploy) must not fail the cron run.
exit 0

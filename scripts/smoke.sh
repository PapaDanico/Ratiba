#!/usr/bin/env bash
# Post-deploy smoke check. Verifies a Ratiba deployment can actually serve a
# login. Run against any base URL:
#
#   scripts/smoke.sh https://ratiba-api.onrender.com
#   SMOKE_EMAIL=officer@jetways.example.aero scripts/smoke.sh http://localhost:8000
#
# Exits non-zero on the first failed check (suitable for CI / a deploy gate).
set -uo pipefail

BASE="${1:-http://localhost:8000}"
EMAIL="${SMOKE_EMAIL:-officer@demo-aoc-ac.example.aero}"
PASSWORD="${SMOKE_PASSWORD:-hunter2pass}"
fail=0

check() { # name  expected_code  curl-args...
  local name="$1" expect="$2"; shift 2
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 "$@")
  if [ "$code" = "$expect" ]; then
    echo "  ✅ $name ($code)"
  else
    echo "  ❌ $name (got $code, want $expect)"; fail=1
  fi
}

echo "Smoke check: $BASE"
check "liveness  /healthz" 200 "$BASE/healthz"
check "readiness /readyz"  200 "$BASE/readyz"

# Login round-trip must return an access token.
token=$(curl -s --max-time 20 -X POST "$BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | grep -o '"access_token"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1)
if [ -n "$token" ]; then
  echo "  ✅ login round-trip ($EMAIL)"
else
  echo "  ❌ login round-trip ($EMAIL) — no access_token returned"; fail=1
fi

[ "$fail" = 0 ] && echo "Smoke check PASSED" || echo "Smoke check FAILED"
exit "$fail"

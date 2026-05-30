#!/usr/bin/env bash
# Idempotently bring up the local Ratiba demo stack: Postgres -> migrate ->
# seed -> API (:8000) -> web (:3000). Safe to re-run; each step is skipped when
# already satisfied. Used by the web SessionStart hook and handy for manual dev.
#
# Why this exists: Claude Code on the web runs in an ephemeral container that is
# cloned fresh per session and reclaims processes on idle. Without this, the
# demo's backend is down and the login page has nothing to talk to.
set -uo pipefail  # intentionally not -e: best-effort, continue past soft failures

REPO="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$REPO"

PGDATA=/tmp/ratiba_pg
PGSOCK=/tmp/pgsock
PGBIN="$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | sort -V | tail -1)"
VENV="$REPO/.venv-ci"
PY="$VENV/bin/python"
DBURL="postgresql+psycopg://ratiba:dev_password@127.0.0.1:5432/ratiba"
export PGPASSWORD=dev_password

log() { echo "[dev-up] $*"; }
psql_q() { psql -h 127.0.0.1 -p 5432 -U ratiba -d "$1" -tAc "$2" 2>/dev/null; }

# 1) Python deps -----------------------------------------------------------
if [ ! -x "$PY" ]; then
  log "creating Python venv + installing backend deps"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q -U pip
  "$VENV/bin/pip" install -q -e "$REPO/backend[dev]" \
    || "$VENV/bin/pip" install -q -r "$REPO/backend/requirements.txt"
fi

# 2) Frontend deps ---------------------------------------------------------
if [ ! -d "$REPO/frontend/node_modules" ]; then
  log "npm install (frontend)"
  (cd "$REPO/frontend" && npm install --no-audit --no-fund)
fi

# 3) Postgres --------------------------------------------------------------
if ! pg_isready -h 127.0.0.1 -p 5432 >/dev/null 2>&1; then
  mkdir -p "$PGSOCK"
  id pguser >/dev/null 2>&1 || useradd -m pguser 2>/dev/null || true
  if [ ! -s "$PGDATA/PG_VERSION" ]; then
    log "initdb (fresh cluster)"
    mkdir -p "$PGDATA"
    chown -R pguser "$PGDATA" "$PGSOCK" 2>/dev/null || true
    sudo -u pguser "$PGBIN/initdb" -D "$PGDATA" -U ratiba --auth=trust >/dev/null 2>&1 || true
  fi
  chown -R pguser "$PGSOCK" "$PGDATA" 2>/dev/null || true
  log "starting Postgres"
  sudo -u pguser "$PGBIN/pg_ctl" -D "$PGDATA" \
    -o "-p 5432 -k $PGSOCK -c listen_addresses=127.0.0.1" -l /tmp/ratiba-pg.log -w start \
    >/dev/null 2>&1 || true
fi
for _ in $(seq 1 20); do pg_isready -h 127.0.0.1 -p 5432 >/dev/null 2>&1 && break; sleep 1; done

# 4) Databases -------------------------------------------------------------
for db in ratiba ratiba_test; do
  [ "$(psql_q postgres "SELECT 1 FROM pg_database WHERE datname='$db'")" = "1" ] \
    || createdb -h 127.0.0.1 -p 5432 -U ratiba "$db" 2>/dev/null || true
done
psql_q postgres "ALTER ROLE ratiba WITH PASSWORD 'dev_password'" >/dev/null 2>&1 || true

# 5) Migrate + seed --------------------------------------------------------
log "alembic upgrade head"
(cd "$REPO/backend" && DATABASE_URL="$DBURL" "$VENV/bin/alembic" upgrade head) >/dev/null 2>&1 || true
if [ "$(psql_q ratiba 'SELECT count(*) FROM users' || echo 0)" = "0" ]; then
  log "seeding demo data"
  (cd "$REPO/backend" && DATABASE_URL="$DBURL" "$PY" scripts/seed.py --demo) >/dev/null 2>&1 || true
fi

# 6) App servers -----------------------------------------------------------
# Cookie policy. The Claude Code web preview serves the app over HTTPS inside a
# cross-site iframe (under claude.ai), where browsers drop SameSite=Lax cookies
# as third-party — which would silently break login (cookies set, never sent
# back). There we need SameSite=None + Secure. Local-machine dev serves over
# plain HTTP, where Secure cookies can't travel, so it stays Lax/insecure.
if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then
  COOKIE_SAMESITE="none"; COOKIE_SECURE="true"
else
  COOKIE_SAMESITE="lax"; COOKIE_SECURE="false"
fi
if ! curl -s -o /dev/null http://127.0.0.1:8000/healthz 2>/dev/null; then
  log "starting backend (:8000)  [cookies: samesite=$COOKIE_SAMESITE secure=$COOKIE_SECURE]"
  (cd "$REPO/backend" && DATABASE_URL="$DBURL" \
    SECRET_KEY="change_me_dev_only_change_me_dev_only_change_me_dev_only_12345" \
    FRONTEND_URL="http://localhost:3000" ENVIRONMENT="development" \
    COOKIE_SAMESITE="$COOKIE_SAMESITE" COOKIE_SECURE="$COOKIE_SECURE" \
    nohup "$VENV/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000 \
    >/tmp/ratiba-backend.log 2>&1 &)
fi
if ! curl -s -o /dev/null http://127.0.0.1:3000 2>/dev/null; then
  log "starting frontend (:3000)"
  (cd "$REPO/frontend" && VITE_BACKEND_URL="http://127.0.0.1:8000" \
    nohup node node_modules/.bin/vite --host 127.0.0.1 --port 3000 \
    >/tmp/ratiba-frontend.log 2>&1 &)
fi

log "stack up — web http://localhost:3000  api http://localhost:8000"

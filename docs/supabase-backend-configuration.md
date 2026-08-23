# Supabase Postgres backend configuration

Ratiba uses FastAPI, SQLAlchemy, and psycopg v3. It connects to Postgres from
the backend only; the Vite frontend does not use Supabase browser clients,
Supabase Auth, or `@supabase/ssr`.

## Required runtime variable

Set `DATABASE_URL` for every backend process that accesses the database:

- `ratiba-api`
- `ratiba-worker`
- `ratiba-digest`

Use the Supabase project host and a percent-encoded database password. TLS is
required:

```text
postgresql+psycopg://postgres:[PERCENT_ENCODED_PASSWORD]@db.ntqtkgunwdvqmmgvrxjv.supabase.co:5432/postgres?sslmode=require
```

Do not commit this value or expose the password in client-side variables.

## Deployment sequence

1. Add `DATABASE_URL` as a secret environment variable to all three backend
   services.
2. Deploy `ratiba-api`. Its startup command runs `alembic upgrade head` before
   serving requests.
3. Confirm `GET /readyz` reports `status: "ready"` and `checks.postgres: "ok"`.
4. Deploy the worker and daily digest only after the API readiness check passes.

`/healthz` verifies process liveness only; `/readyz` is the database-backed
health signal. A database failure returns HTTP 503 and `status: "not_ready"`.

## Frontend configuration

The current frontend uses same-origin `/api` requests routed by its nginx
container to the FastAPI backend. Do not add `@supabase/supabase-js`,
`@supabase/ssr`, Next.js middleware, or `NEXT_PUBLIC_SUPABASE_*` variables
unless Ratiba is intentionally redesigned to use Supabase Auth, Storage, or
Realtime from the browser.

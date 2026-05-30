# Deployment runbook (hosting-agnostic)

> **Plan reference:** §5 Phase 6 — "Production hosting setup".
> ADR 0006 paused the ADC Nairobi-specific commitment until at least
> one round of prospective-user feedback has shaped the product; the
> previous ADC-specific notes are preserved as an appendix below.

The default Ratiba deployment is `docker compose` on a single host
with the four services it ships with (postgres, redis, backend, bot)
plus the frontend served via the same Docker stack. That works for
trial deployments and for "let one prospective user try it on their
own VM". Below are the operating tasks that apply regardless of
where the host lives.

## Topology

```
[ users + bot ]
       │  HTTPS  (TLS terminator of your choice)
       ▼
[ Caddy / nginx / Cloudflare Tunnel ]
       │
       ▼
[ Docker host running:
    backend (uvicorn × N workers)
    frontend (Vite preview / served by reverse proxy)
    bot (long-poll worker; optional)
    rq worker (one replica)
    Sentry SDK (in-process)
  ]
       │
       ▼
[ Postgres 16 — VM-hosted, daily encrypted backups ]
       │
       ▼
[ Redis 7 — same VM as Postgres for trial scale ]
```

## Pre-flight checklist

Before the first deploy:

- [ ] Tenant provisioned: two VMs (app + database).
      App VM: 4 vCPU / 8 GB RAM. DB VM: 4 vCPU / 16 GB RAM, 200 GB SSD.
- [ ] DNS records pointing at the app VM's public IP.
- [ ] TLS certificate: Let's Encrypt + ACME DNS-01 challenge, or
      front the stack behind a managed proxy (Cloudflare Tunnel,
      similar).
- [ ] Sentry project provisioned; `SENTRY_DSN` in env.
- [ ] (Optional) S3-compatible object storage configured for audit
      packs — any provider with an S3 API will do.
- [ ] (Optional, deferred to first paid pilot) KDPA / ODPC
      registration paperwork if the host is in Kenya.

## Environment variables (production)

`/etc/ratiba/production.env`, loaded by docker-compose:

```bash
DATABASE_URL=postgresql+psycopg://ratiba:<strong-pass>@db:5432/ratiba
REDIS_URL=redis://redis:6379/0

ANTHROPIC_API_KEY=<sk-ant-…>
ANTHROPIC_MODEL_PARSER=claude-sonnet-4-5
ANTHROPIC_MODEL_CONVERSATIONAL=claude-haiku-4-5

TELEGRAM_BOT_TOKEN=<…>            # optional — bot stays idle if unset

SECRET_KEY=<openssl rand -hex 32 output>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
COOKIE_SECURE=true               # HTTPS in prod → mark session cookies Secure
COOKIE_SAMESITE=lax              # see "Cookie auth & origins" below

KDPA_DATA_REGION=<region tag>
KDPA_REGISTRATION_REF=<ODPC reference if registered>

AUDIT_PACK_S3_BUCKET=<bucket>      # optional — falls back to local FS
AUDIT_PACK_S3_ENDPOINT=<…>
AUDIT_PACK_S3_REGION=<…>

FRONTEND_URL=https://app.<host>
BACKEND_URL=https://api.<host>

SENTRY_DSN=<…>
LOG_LEVEL=INFO
```

## Cookie auth & origins

Browser sessions authenticate with **httpOnly cookies** (officer dashboard +
`/crew/me`), so the deployment's origin shape matters:

- **Default (recommended): same site.** Serve the SPA and proxy `/api` to the
  backend under **one registrable domain** (the shipped nginx does this). Then
  `COOKIE_SAMESITE=lax` is correct and the cookies "just work". The dashboard
  and API can be different *hosts/ports* (e.g. `app.host` ↔ `api.host` is still
  same-site under `host`) as long as they share the registrable domain; set
  `FRONTEND_URL` to the exact dashboard origin for CORS.
- **Cross-domain** (SPA and API on genuinely different domains): set
  `COOKIE_SAMESITE=none` (which forces Secure on), and `FRONTEND_URL` to the
  dashboard origin so CORS returns it with `Allow-Credentials`. Without this the
  browser drops the session cookies on cross-site XHR and login appears to
  "succeed" but every subsequent request is 401.

The Telegram bot and any API client use `Authorization: Bearer` and are
unaffected by either setting.

## First deploy

```bash
# 1. Clone onto the app VM.
git clone https://github.com/papadanico/ratiba.git
cd ratiba
git checkout main

# 2. Drop the production env file in place.
sudo install -m 600 production.env /etc/ratiba/production.env
ln -s /etc/ratiba/production.env .env

# 3. Build + bring up the stack.
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 4. Apply migrations.
docker compose exec backend alembic upgrade head

# 5. Seed the first operator + crewing-officer user
#    (see docs/onboarding-playbook.md for the full operator data flow).
docker compose exec backend python scripts/seed.py

# 6. Verify health + readiness.
curl https://api.<host>/healthz   # → {"status":"ok"}
curl https://api.<host>/readyz    # → status: "ready"
curl https://api.<host>/version

# 7. Smoke-test login via the dashboard.
```

## Day-2 operations

### Daily

- Encrypted Postgres backup to a separate host or storage tenant
  (cron 02:00 local).
- Sentry digest review.

### Weekly

- Crewing Officer + Chief Pilot 30-minute check-in.
- Audit-pack rehearsal run (`/audit/generate` for the last 7 days).
- `pg_dump` integrity check via test-restore into a staging VM.

### Monthly

- Rotate `SECRET_KEY` (invalidates active JWTs — coordinate with
  Crewing Officer).
- Review `llm_usage_events` against the cost-model target.
- Walk through the open-risks register; close any no-longer-relevant.

## Rollback

Each deploy creates a Git tag `prod-<YYYYMMDD-HHMMSS>`:

```bash
git checkout prod-<previous-tag>
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose exec backend alembic downgrade -1  # only if needed
```

Migrations are forward-compatible unless the migration's docstring
explicitly says otherwise.

## Incident response

- **Critical** (production down, data loss risk): page the on-call
  channel. 4 h first response.
- **High** (single feature broken, no data risk): GitHub issue with
  `prod-incident` label. 24 h first response.
- **Medium**: weekly triage. 5 d first response.

All incidents close with a written post-mortem in `docs/postmortems/`.

## Appendix A — ADC Nairobi specifics (deferred per ADR 0006)

When/if the first paid pilot lands and Kenyan data residency becomes a
contractual requirement, ADR 0005 documents the ADC Nairobi
deployment shape we'd target:

- Two VMs in ADC's Nairobi region (Liquid tenant).
- KDPA 2019 data-residency confirmation in writing from ADC.
- Off-site encrypted backups to a separate ADC tenant.
- ODPC registration reference recorded in `KDPA_REGISTRATION_REF`.

That work is paused until the user-feedback round confirms which
operator (if any) commits to a paid pilot.

## Appendix B — AWS Cape Town `af-south-1` (upgrade path)

When the operator base grows past a single tenant + the managed-RDS
shape becomes worth the cost:

- RDS Postgres 16, multi-AZ.
- ElastiCache Redis.
- ECS Fargate or EKS for the app stack.
- S3 (`af-south-1`) for audit packs.
- WAF + CloudFront in front of the public surface.

Not blocking anything; just a clean migration path when scale demands.

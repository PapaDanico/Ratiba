# Production deployment runbook — ADC Nairobi

> **Target environment:** Africa Data Centres Nairobi (Liquid)
> **Owner:** Capt. Dan Ng'ong'a (credentials), Claude Code (execution)
> **Plan reference:** §5 Phase 6 — "Production hosting setup"

## Topology

Three tiers, all in ADC Nairobi for KDPA 2019 data-residency cleanliness:

```
[ users + bot ]
       │  HTTPS (Let's Encrypt + HSTS)
       ▼
[ Caddy / nginx reverse proxy ]        ← TLS termination + static
       │
       ▼
[ Docker host running:
    backend (uvicorn × N workers)
    frontend (Vite preview / served by Caddy)
    bot (long-poll worker)
    rq worker (1 replica for now)
    Sentry agent
  ]
       │
       ▼
[ Postgres 16 — VM-hosted, daily encrypted backups to a
  separate ADC tenant ]
       │
       ▼
[ Redis 7 — same VM as Postgres for the pilot;
  separate node post-pilot ]
```

## Pre-flight checklist

Before the first deploy:

- [ ] ADC Nairobi tenant provisioned with two VMs (app + database).
      App VM: 4 vCPU / 8 GB RAM. DB VM: 4 vCPU / 16 GB RAM, 200 GB SSD.
- [ ] KDPA 2019 data-residency confirmed in writing from ADC (their
      standard hosting agreement covers this; attach to the operator
      contract).
- [ ] DNS records: `api.ratiba.aero`, `app.ratiba.aero`,
      `crew.ratiba.aero` pointing at the app VM's public IP.
- [ ] Let's Encrypt: ACME DNS-01 challenge configured against the
      domain registrar.
- [ ] ODPC registration reference recorded in
      `KDPA_REGISTRATION_REF` env var.
- [ ] Bug triage on-call rotation agreed (Dan + Claude Code via
      `subscribe_pr_activity` listener).
- [ ] Sentry project provisioned; `SENTRY_DSN` in env.
- [ ] S3-compatible object storage configured for audit packs
      (ADC's S3-compat or DigitalOcean Spaces with Kenya region).

## Environment variables (production)

All set via `/etc/ratiba/production.env`, loaded by docker-compose:

```bash
# Database
DATABASE_URL=postgresql+psycopg://ratiba:<strong-pass>@db:5432/ratiba

# Redis
REDIS_URL=redis://redis:6379/0

# Anthropic
ANTHROPIC_API_KEY=<sk-ant-…>
ANTHROPIC_MODEL_PARSER=claude-sonnet-4-5
ANTHROPIC_MODEL_CONVERSATIONAL=claude-haiku-4-5

# Telegram
TELEGRAM_BOT_TOKEN=<…>

# Security — generate via `openssl rand -hex 32`
SECRET_KEY=<…>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# Compliance
KDPA_DATA_REGION=ke-1
KDPA_REGISTRATION_REF=<ODPC reference>

# Audit pack storage (S3-compatible)
AUDIT_PACK_S3_BUCKET=ratiba-audit-packs-prod
AUDIT_PACK_S3_ENDPOINT=https://s3.adc-nairobi.example.aero
AUDIT_PACK_S3_REGION=ke-1

# URLs
FRONTEND_URL=https://app.ratiba.aero
BACKEND_URL=https://api.ratiba.aero

# Observability
SENTRY_DSN=<…>
LOG_LEVEL=INFO
```

## First deploy

```bash
# 1. Clone the repo onto the app VM (auth via deploy key).
git clone git@github.com:papadanico/ratiba.git
cd ratiba
git checkout main  # or the release tag

# 2. Drop the production env file in place.
sudo install -m 600 production.env /etc/ratiba/production.env
ln -s /etc/ratiba/production.env .env

# 3. Build + bring up the stack.
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 4. Apply migrations.
docker compose exec backend alembic upgrade head

# 5. Seed the first operator + crewing-officer user (see onboarding-playbook.md).
docker compose exec backend python scripts/seed.py

# 6. Verify health + readiness.
curl https://api.ratiba.aero/healthz   # → {"status":"ok"}
curl https://api.ratiba.aero/readyz    # → status: "ready", checks: {postgres: ok, redis: ok}
curl https://api.ratiba.aero/version   # → phase "6"

# 7. Smoke-test login through the dashboard at https://app.ratiba.aero.
```

## Day-2 operations

### Daily

- Encrypted Postgres backup to the separate ADC tenant (cron 02:00 UTC).
- Sentry digest review.

### Weekly

- Crewing Officer + Chief Pilot 30-minute check-in (Dan facilitates).
- Audit-pack rehearsal run (`/audit/generate` for the last 7 days).
- `pg_dump` integrity check via test-restore into the staging VM.

### Monthly

- Rotate ``SECRET_KEY`` (invalidates active JWTs — coordinate with
  Crewing Officer).
- Review ``llm_usage_events`` against the cost-model target
  (≤ USD 2 / pilot / month per Plan §5 Phase 4).
- Walk through the open-risks register; close any that are no
  longer relevant.

## Rollback

Each deploy creates a Git tag `prod-<YYYYMMDD-HHMMSS>`. Rolling back:

```bash
git checkout prod-<previous-tag>
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose exec backend alembic downgrade -1  # only if the new revision misbehaved
```

Migrations are forward-compatible at the previous version unless the
ADR for the migration explicitly says otherwise; default is to leave
the DB at the new revision and downgrade only the application.

## Incident response

- **Critical (production down, data loss risk):** page Dan via the
  on-call channel. 4 h first response.
- **High (single feature broken, no data risk):** GitHub issue with
  the `prod-incident` label. 24 h first response.
- **Medium:** GitHub issue, no label. Picked up in the weekly
  triage. 5 days first response.

All incidents close with a written post-mortem in `docs/postmortems/`.

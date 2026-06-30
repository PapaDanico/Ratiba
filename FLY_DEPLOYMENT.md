# Fly.io Backend Deployment — Complete Guide

Deploy Ratiba backend to Fly.io (simpler than Railway, better auto-scaling).

## Architecture

```
Netlify Frontend (React SPA)
        ↓
API Proxy Function (Netlify Functions)
        ↓
Fly.io Backend (FastAPI + uvicorn)
        ↓
Neon PostgreSQL (Pooled connection)
```

---

## Prerequisites

✅ **Already Done:**
- Neon database: `postgresql://neondb_owner:npg_jnLiHFc1D5PA@ep-small-dawn-ass7d4h3-pooler.c-4.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`
- `fly.toml` configuration file
- `Dockerfile` (Python 3.12-slim)
- GitHub repository: `papadanico/Ratiba`

---

## Phase 1: Install Fly.io CLI

### macOS
```bash
brew install flyctl
```

### Linux
```bash
curl -L https://fly.io/install.sh | sh
```

### Windows
```bash
iwr https://fly.io/install.ps1 -useb | iex
```

---

## Phase 2: Login to Fly.io

```bash
flyctl auth login
```

This opens a browser to authenticate. Complete the login flow.

---

## Phase 3: Create Fly.io App

If you don't have an app yet, create one:

```bash
flyctl apps create ratiba-backend
```

(Or use existing app from your screenshot)

---

## Phase 4: Set Environment Variables

### Set Database URL
```bash
flyctl secrets set \
  DATABASE_URL="postgresql://neondb_owner:npg_jnLiHFc1D5PA@ep-small-dawn-ass7d4h3-pooler.c-4.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
```

### Set Security Variables
```bash
flyctl secrets set \
  SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

### Set Frontend URL
```bash
flyctl secrets set \
  FRONTEND_URL="https://ratiacrewmanagement.netlify.app"
```

### Optional: Set other variables
```bash
flyctl secrets set \
  LOG_LEVEL="INFO" \
  ENVIRONMENT="production" \
  JWT_ALGORITHM="HS256" \
  JWT_ACCESS_TOKEN_EXPIRE_MINUTES="60" \
  JWT_REFRESH_TOKEN_EXPIRE_DAYS="30"
```

### Verify secrets set
```bash
flyctl secrets list
```

---

## Phase 5: Deploy

### Option A: Deploy from CLI (Recommended)
```bash
flyctl deploy
```

This will:
1. Build Docker image
2. Push to Fly.io registry
3. Deploy to your app
4. Wait for healthcheck to pass

### Option B: Deploy from GitHub (Auto-deploys on push)
```bash
flyctl apps create ratiba-backend --builder-classic
# Or configure in web dashboard
```

---

## Phase 6: Monitor Deployment

### Watch logs in real-time
```bash
flyctl logs --follow
```

### Check app status
```bash
flyctl status
```

### Expected output when successful:
```
2026-06-30T... [app] Uvicorn running on 0.0.0.0:8000
2026-06-30T... [app] Application startup complete
```

### Get public URL
```bash
flyctl info
```

Look for: `Hostname: ratiba-backend.fly.dev`

Your backend URL will be:
```
https://ratiba-backend.fly.dev
```

---

## Phase 7: Update Netlify Backend URL

1. Go to Netlify dashboard → **ratibacrewmanagement**
2. **Site settings** → **Build & deploy** → **Environment**
3. Update or add:
   - **Key:** `BACKEND_URL`
   - **Value:** `https://ratiba-backend.fly.dev` (or your app name)
4. **Save**

Netlify will automatically redeploy with the new backend URL.

---

## Phase 8: Test Integration

### Test backend directly
```bash
curl https://ratiba-backend.fly.dev/healthz
# Response: {"status": "ok"}
```

### Test API proxy
```bash
curl https://ratiacrewmanagement.netlify.app/api/health
# Should proxy to backend and return: {"status": "ok"}
```

### Test in browser
1. Open https://ratiacrewmanagement.netlify.app
2. Click **Login**
3. Enter: `demo@ratiba-demo.com` / `DemoPass123`
4. Should see dashboard with data from database

### Run E2E tests
```bash
npm run playwright
```

---

## Troubleshooting

### Build fails: "pip install failed"
**Problem:** Docker build fails during pip install
**Solution:**
```bash
# Check Dockerfile is correct
cat Dockerfile | head -30

# Rebuild with more verbose output
flyctl deploy --verbose
```

**Common causes:**
- Missing system dependencies
- Old pip cache
- Network timeout during download

**Fix:**
```bash
flyctl deploy --remote-only
```

### Healthcheck fails: "504 Gateway Timeout"
**Problem:** Healthcheck `/healthz` not responding
**Solution:**
```bash
# Check logs for startup errors
flyctl logs --follow

# Increase grace period in fly.toml
# grace_period = 120000 (2 minutes)

# Redeploy
flyctl deploy
```

### Database connection fails
**Problem:** "failed to connect to postgres"
**Solution:**
```bash
# Verify DATABASE_URL is set
flyctl secrets list

# Check exact error
flyctl logs --follow

# Test connection manually
flyctl ssh console
psql $DATABASE_URL -c "SELECT 1"
```

### High latency between Netlify and Fly.io
**Solution:**
```bash
# Deploy to region closer to your users
flyctl regions list
flyctl regions set ams  # Amsterdam for EU users
```

---

## Scaling Configuration

### Minimum Resources (Free Tier)
```bash
flyctl scale memory 512 --region ams
flyctl scale count 1
```

### Production Resources
```bash
flyctl scale memory 2048 --region ams
flyctl scale count 2  # 2 instances for redundancy
```

### Auto-scaling
Fly.io automatically scales based on demand:
- Min instances: 1
- Max instances: 3 (configurable)

---

## Monitoring

### Real-time logs
```bash
flyctl logs --follow
```

### Metrics
```bash
flyctl status
```

### Deploy history
```bash
flyctl releases
```

### Rollback to previous version
```bash
flyctl releases list
flyctl releases rollback <VERSION_NUMBER>
```

---

## Database Backups

Neon handles backups automatically. Access in Neon console:
1. Go to neon.tech
2. Select project
3. **Backups** tab
4. View/restore from automatic backups

---

## Security Checklist

- [x] HTTPS enforced (automatic)
- [x] Database secrets not logged
- [x] CORS headers configured
- [x] Authentication tokens httpOnly cookies
- [x] Secrets stored securely (flyctl secrets)

---

## Cost Estimate

| Service | Cost | Notes |
|---------|------|-------|
| Fly.io | Free tier included | $10-50/month if scaling |
| Neon | Free tier included | $10-50/month if scaling |
| Netlify | Free tier | $20+ if custom domain |
| **Total** | **Free - $100/month** | Depending on traffic |

---

## Useful Commands

```bash
# Deploy from current directory
flyctl deploy

# Deploy from GitHub (after setup)
git push  # Auto-deploys if configured

# SSH into running container
flyctl ssh console

# Execute command in container
flyctl ssh console
# Then: bash ./start.sh

# View recent releases
flyctl releases

# Rollback to previous version
flyctl releases rollback 5

# Scale up
flyctl scale memory 2048

# Monitor logs
flyctl logs --follow

# View metrics
flyctl status

# Get app info
flyctl info
```

---

## After Successful Deployment

✅ **Checklist:**
- [x] Fly.io app created
- [x] Environment variables set
- [x] Docker image built successfully
- [x] App deployed and running
- [x] Healthcheck passing
- [x] Public URL accessible
- [x] Netlify BACKEND_URL updated
- [x] Frontend loads and connects to backend
- [x] Login flow works
- [x] E2E tests passing

---

## Next Steps

1. **Deploy to Fly.io** (follow Phase 1-7)
2. **Update Netlify BACKEND_URL** (Phase 7)
3. **Test integration** (Phase 8)
4. **Run E2E tests** (Phase 8)
5. **Monitor in production** (ongoing)

---

## Quick Start (TL;DR)

```bash
# 1. Install Fly CLI
brew install flyctl  # or your OS

# 2. Login
flyctl auth login

# 3. Create app (if needed)
flyctl apps create ratiba-backend

# 4. Set secrets
flyctl secrets set DATABASE_URL="your_neon_url"
flyctl secrets set SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
flyctl secrets set FRONTEND_URL="https://ratiacrewmanagement.netlify.app"

# 5. Deploy
flyctl deploy

# 6. Get URL
flyctl info | grep Hostname

# 7. Update Netlify with BACKEND_URL
# Go to Netlify dashboard and set BACKEND_URL to your fly.dev URL

# 8. Test
curl https://YOUR_FLY_URL/healthz
```

---

## Support

- Fly.io Docs: https://fly.io/docs/
- Fly CLI Reference: https://fly.io/docs/reference/flyctl/
- Community: https://community.fly.io/

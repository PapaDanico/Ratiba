# Complete Deployment Checklist

Track your progress through the Ratiba deployment process.

## Current Status (June 30, 2026)

- ✅ **Frontend:** Deployed to Netlify (Live)
- ✅ **Frontend Build:** GitHub Actions CI passing
- ✅ **Netlify Configuration:** Complete with SPA routing and API proxy
- ⏳ **Backend:** Needs fresh Railway setup
- ⏳ **Database:** Neon connection string ready
- ⏳ **Integration:** Awaiting backend deployment

---

## Pre-Deployment Checklist

### Code Repository
- [x] Code committed to `main` branch
- [x] GitHub Actions CI passing (ESLint, TypeScript, Build)
- [x] netlify.toml configured for SPA + API proxy
- [x] Dockerfile ready for Railway
- [x] railway.json configured with healthcheck
- [x] Backend requirements.txt up to date
- [x] Environment variables documented

### Local Development
- [x] Frontend builds locally: `npm run build`
- [x] Backend runs locally: `uvicorn app.main:app --port 8000`
- [x] API proxy functions locally
- [x] Database migrations work: `alembic upgrade head`

---

## Neon Database Setup

### Phase 1: Create Neon Project
- [ ] Create project at https://console.neon.tech
- [ ] Project name: `ratiba-production`
- [ ] Database: `neondb`
- [ ] Region: EU-Central-1 (or your region)
- [ ] Copy connection string

### Phase 2: Configure Connection Pooler
- [ ] Enable pooler in Neon console
- [ ] Mode: **Transaction** (required for serverless)
- [ ] Pool size: 10+
- [ ] Copy pooler connection string
- [ ] Format: `postgresql://user:password@host/db?sslmode=require&channel_binding=require`

### Phase 3: Security (Optional)
- [ ] Configure IP allowlist in Neon settings
- [ ] Allow Railway IPs or use `0.0.0.0/0`

**Neon Status:**
```
Connection String: postgresql://neondb_owner:npg_jnLiHFc1D5PA@ep-small-dawn-ass7d4h3-pooler.c-4.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```
✅ Ready

---

## Railway Backend Setup

### Phase 1: Create Railway Project
- [ ] Go to https://railway.app
- [ ] Create new project
- [ ] Connect GitHub → select `papadanico/Ratiba`
- [ ] Select branch: `main`
- [ ] Wait for auto-detection of `railway.json` and `Dockerfile`

### Phase 2: Verify Service Configuration
- [ ] Service name detected
- [ ] Build method: Dockerfile ✅
- [ ] Start command: `bash ./start.sh` ✅
- [ ] Port: 8000 ✅
- [ ] Healthcheck endpoint: `/healthz` ✅

### Phase 3: Set Environment Variables

**Required:**
```
DATABASE_URL = postgresql://neondb_owner:npg_jnLiHFc1D5PA@ep-small-dawn-ass7d4h3-pooler.c-4.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require

SECRET_KEY = <GENERATE: python -c "import secrets; print(secrets.token_urlsafe(32))">

FRONTEND_URL = https://ratiacrewmanagement.netlify.app

BACKEND_URL = <YOUR_RAILWAY_PUBLIC_URL>
```

**Recommended:**
```
PORT = 8000
LOG_LEVEL = INFO
ENVIRONMENT = production
JWT_ALGORITHM = HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30
```

**Optional (for features):**
```
ANTHROPIC_API_KEY = <if using Claude integration>
AT_API_KEY = <if using Africa's Talking SMS>
SENTRY_DSN = <if using error tracking>
```

**Checklist:**
- [ ] Create all required environment variables in Railway dashboard
- [ ] After adding each variable, click **Save**
- [ ] Verify all variables appear in the **Variables** tab

### Phase 4: Deploy & Monitor
- [ ] Click **Deploy** to trigger build
- [ ] Monitor build logs in **Deployments** tab
- [ ] Watch for:
  - [ ] Docker image builds
  - [ ] Python dependencies install
  - [ ] Alembic migrations run
  - [ ] Demo seed runs
  - [ ] Uvicorn starts on 0.0.0.0:8000
  - [ ] Healthcheck passes ✅
- [ ] Get public URL from **Settings** → **Domains**
- [ ] Copy URL: `https://ratiba-app-production-xxxx.up.railway.app`

### Phase 5: Test Backend
- [ ] Test healthcheck: `curl https://YOUR_RAILWAY_URL/healthz`
- [ ] Response should be: `{"status": "ok"}`
- [ ] Check logs for errors

**Railway Status:**
- [ ] Deployment: Pending
- [ ] Public URL: Pending

---

## Netlify Configuration

### Current Status
- ✅ Frontend deployed and live
- ✅ API proxy function bundled
- ✅ SPA routing configured
- ⏳ BACKEND_URL needs to be set

### Add Backend URL
- [ ] Go to Netlify dashboard → **ratibacrewmanagement**
- [ ] Click **Site settings** → **Build & deploy** → **Environment**
- [ ] Click **Add a variable**
- [ ] Key: `BACKEND_URL`
- [ ] Value: `https://YOUR_RAILWAY_URL` (from Railway Phase 4)
- [ ] Click **Save**
- [ ] Trigger new deployment (Netlify will redeploy automatically)

### Verify Configuration
- [ ] `BACKEND_URL` shows in Environment variables
- [ ] Frontend redeploys successfully
- [ ] Netlify build succeeds (check build logs)

**Netlify Status:**
- ✅ Frontend: Live at https://ratiacrewmanagement.netlify.app
- ⏳ Backend URL: Pending Railway setup

---

## Integration Testing

### Phase 1: Backend Connectivity
- [ ] Test API proxy responds: `curl https://ratiacrewmanagement.netlify.app/api/health`
- [ ] No 502 errors
- [ ] Check browser console for CORS errors

### Phase 2: Frontend Access
- [ ] Open https://ratiacrewmanagement.netlify.app
- [ ] Landing page loads
- [ ] Navigation works
- [ ] No console errors

### Phase 3: Authentication
- [ ] Click **Login**
- [ ] Enter demo credentials:
  - Email: `demo@ratiba-demo.com`
  - Password: `DemoPass123`
- [ ] Login succeeds
- [ ] Redirects to dashboard

### Phase 4: Data Access
- [ ] View crew list
- [ ] Data loads from database
- [ ] No API errors

### Phase 5: E2E Tests
- [ ] Run: `npm run playwright`
- [ ] All tests pass
- [ ] No flaky tests

**Integration Status:**
- [ ] Backend connectivity verified
- [ ] Frontend-backend communication working
- [ ] Authentication flow complete
- [ ] Database queries successful
- [ ] E2E tests passing

---

## Monitoring & Observability

### Railway Logs
- [ ] Access **Logs** tab in Railway service
- [ ] Monitor for errors
- [ ] Search for specific requests

### Error Tracking
- [ ] Set `SENTRY_DSN` if using Sentry
- [ ] Monitor error reports
- [ ] Alert on critical errors

### Performance Monitoring
- [ ] Check Netlify Lighthouse scores (90+)
- [ ] Monitor Railway CPU/memory usage
- [ ] Track API response times

---

## Post-Deployment Steps

### Phase 1: Smoke Tests
- [ ] Test login flow end-to-end
- [ ] Create/edit crew member
- [ ] Export compliance report
- [ ] Test notification channels (if configured)

### Phase 2: Performance Baseline
- [ ] Record Lighthouse scores
- [ ] Record API response times
- [ ] Document cold start performance

### Phase 3: Security
- [ ] Verify HTTPS on all endpoints
- [ ] Check security headers (X-Frame-Options, CSP, etc.)
- [ ] Test CORS configuration
- [ ] Verify credentials are not logged

### Phase 4: Backup & Recovery
- [ ] Enable Neon automated backups
- [ ] Test restore procedure
- [ ] Document recovery steps

---

## Troubleshooting Quick Links

| Issue | Debug Command | Solution Link |
|-------|---------------|---------------|
| Backend unreachable | `curl https://YOUR_RAILWAY_URL/healthz` | Check Railway logs |
| CORS errors | Browser F12 → Network tab | Verify CORS headers in api-proxy.ts |
| Database connection | Check Railway environment variables | Verify `DATABASE_URL` format |
| Frontend build fails | Check Netlify build logs | Verify Node version compatibility |
| Healthcheck timeout | Increase `initialDelaySeconds` in railway.json | Redeploy to Railway |

---

## Sign-Off Checklist

- [ ] Neon database ready
- [ ] Railway backend deployed
- [ ] Netlify frontend updated
- [ ] Backend URL configured
- [ ] Integration tests passing
- [ ] E2E tests passing
- [ ] Monitoring configured
- [ ] Documentation updated

**Deployment Ready:** ⏳ Awaiting Railway setup completion

---

## Notes

- **Netlify Frontend:** Successfully deployed (June 29, 2026 @ 10:38 PM UTC)
- **Neon Database:** Connection string provided, ready for Railway
- **Railway Backend:** Requires fresh setup (project deleted)
- **Next Step:** Begin Phase 1 of `RAILWAY_SETUP_FRESH.md`

---

**Last Updated:** June 30, 2026
**Status:** Awaiting Railway Backend Setup

# Netlify Deployment Guide — Ratiba Frontend Migration

**Phase:** 6 (Pilot deployment + 30-day stability)  
**Target:** Migrate frontend to Netlify, use Neon for database, keep backend on Render  
**Timeline:** ~20 minutes (deploy + verify)

---

## 🎯 Architecture Overview

After migration, Ratiba runs on a hybrid platform:

| Component | Platform | Why |
|-----------|----------|-----|
| **Frontend (React SPA)** | Netlify | ✅ Faster deploys, better CDN, native SPA support |
| **Backend API (FastAPI)** | Render | ✅ Persistent connections, workers, cron jobs |
| **Database** | Neon | ✅ Managed Postgres, auto-scaling, better than Render free tier |
| **Cache (Redis)** | Render | ✅ Coupled with backend |
| **Workers & Crons** | Render | ✅ Background jobs, scheduled tasks |

---

## 📋 Pre-Deployment Checklist

### Accounts & Credentials
- [ ] Netlify account created (free tier sufficient)
- [ ] Neon account created with database initialized
- [ ] Render account (backend stays here; database migrates out)
- [ ] GitHub personal access token (for Netlify <→ GitHub integration)

### Code Quality
- [ ] `npm run lint && npm run typecheck` (frontend) — pass
- [ ] `npm run build` (frontend) — builds successfully
- [ ] Backend environment variables ready for Neon database

---

## 🚀 Step 1: Migrate Database to Neon

### 1a. Create Neon Project
1. Go to **neon.tech** → Sign up / Log in
2. Create a new project (choose region closest to users, e.g., Europe/Frankfurt)
3. Note the **connection string**: `postgresql://user:password@host/dbname`

### 1b. Dump Existing Database (Optional, if you have live data)
```bash
# If you have Render Postgres running
pg_dump $OLD_DATABASE_URL > ratiba_backup.sql

# Or get from Render dashboard:
# Render → ratiba-db → Connections → Database URL
```

### 1c. Restore to Neon (Optional)
```bash
# If you dumped data above
psql $NEON_DATABASE_URL < ratiba_backup.sql
```

### 1d. Run Migrations
```bash
# Run Alembic migrations on the new database
export DATABASE_URL=$NEON_DATABASE_URL
cd backend
alembic upgrade head
python scripts/seed.py --demo  # Optional: seed demo data
```

### 1e. Update Render Backend
In Render dashboard:
1. Go to **ratiba-api** service → **Environment**
2. Update `DATABASE_URL` to the Neon connection string
3. Save (triggers redeploy)

---

## 🌐 Step 2: Deploy Frontend to Netlify

### 2a. Connect GitHub Repository
1. Go to **netlify.com** → Sign in
2. Click **New site from Git** → **GitHub**
3. Authorize Netlify to access GitHub
4. Select repository: `papadanico/ratiba`
5. Select branch: `claude/netlify-migration-4vvflr` (or main once ready)

### 2b. Configure Build Settings
Netlify should auto-detect these, but verify:

| Setting | Value |
|---------|-------|
| **Base directory** | `frontend` |
| **Build command** | `npm run build` |
| **Publish directory** | `dist` |
| **Functions directory** | `netlify/functions` |

### 2c. Set Environment Variables
In Netlify dashboard → **Site settings** → **Build & deploy** → **Environment**:

| Name | Value |
|------|-------|
| `VITE_BACKEND_URL` | `https://ratiba-api.onrender.com` |

**Note:** Update this AFTER the first deploy (see verification steps).

### 2d. Deploy
1. Click **Deploy**
2. Wait ~3–5 minutes for build to complete
3. Note the Netlify URL (e.g., `https://ratiba-abc123.netlify.app`)

---

## ✅ Verification Tests

### Test 1: Frontend Loads
```bash
curl -I https://ratiba-abc123.netlify.app/
# Expected: HTTP/1.1 200 OK (from cache or origin)
```

### Test 2: Check Build
1. Netlify dashboard → **Deployments**
2. Verify latest deploy shows **Published** ✅

### Test 3: SPA Routes Work
1. Open `https://ratiba-abc123.netlify.app/` in browser
2. Navigate to `/login`, `/dashboard`, etc.
3. Expected: ✅ Routes served (no 404)
4. Check browser console: no errors

### Test 4: API Proxy Works (After Configuring Backend)
1. Ensure `VITE_BACKEND_URL` is set in Netlify
2. Attempt login: `officer@demo-aoc-ac.example.aero` / `hunter2pass`
3. Expected:
   - ✅ POST /api/v1/auth/login forwarded to backend
   - ✅ Backend authenticates successfully
   - ✅ Dashboard loads

### Test 5: Health Check
```bash
curl https://ratiba-api.onrender.com/healthz
# Expected: 200 OK (backend alive)
```

### Test 6: Set Custom Domain (Optional)
1. Netlify dashboard → **Site settings** → **Domain management**
2. Add custom domain (e.g., `ratiba.example.com`)
3. Point DNS records as instructed
4. Wait 1–5 minutes for SSL provisioning

---

## 🔄 Setting Up Continuous Deployment

### GitHub Workflow (Optional — Netlify auto-deploys from Git)
Netlify watches your repository and auto-deploys on:
- Push to `main` (or your default branch)
- Approved PRs (preview deployments)

**No manual action needed** — just push and Netlify builds automatically.

If you want a custom workflow, create `.github/workflows/netlify-deploy.yml`:

```yaml
name: Deploy to Netlify

on:
  push:
    branches: [main, claude/netlify-migration-4vvflr]
    paths:
      - 'frontend/**'
      - 'netlify/**'
      - '.github/workflows/netlify-deploy.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: cd frontend && npm ci && npm run build
      - uses: nwtgck/actions-netlify@v2.1.0
        with:
          publish-dir: 'frontend/dist'
          deploy-message: 'Deploy from GitHub Actions'
          netlify-token: ${{ secrets.NETLIFY_AUTH_TOKEN }}
          site-id: ${{ secrets.NETLIFY_SITE_ID }}
```

Then set secrets in GitHub:
- `NETLIFY_AUTH_TOKEN` — get from Netlify → **User settings** → **Applications** → **Tokens**
- `NETLIFY_SITE_ID` — find in Netlify → **Site settings** → **General**

---

## 🔧 Environment Variables

### Frontend (`VITE_*` prefix — exposed to client)
| Variable | Scope | Example |
|----------|-------|---------|
| `VITE_BACKEND_URL` | Client | `https://ratiba-api.onrender.com` |

Set in Netlify dashboard.

### Backend (Hidden from client)
Keep these on Render (already configured):
- `DATABASE_URL` — Neon connection string
- `REDIS_URL` — Render Redis service
- `ANTHROPIC_API_KEY` — API key
- `SECRET_KEY` — auto-generated
- `FRONTEND_URL` — Netlify frontend URL
- Other configs (Telegram token, compliance settings, etc.)

---

## 📊 Performance & Monitoring

### Netlify Dashboards
- **Analytics** — Netlify → Site settings → Analytics (page views, errors)
- **Functions** — Netlify → Functions → api-proxy (invocation count, duration)
- **Builds** — Netlify → Deployments (build time, success/failure)

### Render Backend Monitoring
- **API Logs** — Render → ratiba-api → Logs
- **Worker Logs** — Render → ratiba-worker → Logs
- **Database** — Neon dashboard → Monitoring (connections, queries)

### Key Metrics to Track
| Metric | Target | Where to Check |
|--------|--------|-----------------|
| Frontend page load | < 2s | Netlify Analytics |
| API response time | < 500ms | Render logs |
| Database response | < 100ms | Neon dashboard |
| Build time | < 3 min | Netlify Deployments |
| Cron reliability | 100% | Render logs (digest, keepwarm) |

---

## 🛡️ Security Checklist

- ✅ **HTTPS only** — Netlify auto-enforces TLS; API on Render also HTTPS
- ✅ **CORS** — `netlify.toml` sets `Access-Control-Allow-Origin: *` (tighten as needed)
- ✅ **API proxy** — Netlify function forwards to backend with auth headers intact
- ✅ **Cookies** — `Set-Cookie` headers from backend preserved
- ✅ **Environment secrets** — `VITE_BACKEND_URL` (public) vs backend secrets (on Render, private)
- ✅ **Database credentials** — Neon connection string in Render backend env only

---

## 🚨 Troubleshooting

### Issue: API Proxy Returns 502
**Symptoms:** Login fails with "Bad Gateway"

**Debug:**
1. Check `VITE_BACKEND_URL` is set in Netlify
2. Verify backend URL is reachable: `curl https://ratiba-api.onrender.com/healthz`
3. Check Netlify function logs: **Netlify → Functions → api-proxy → Latest invocation**

**Fix:**
- Ensure backend is running on Render
- Verify `FRONTEND_URL` is set on backend to the Netlify URL

### Issue: API Calls Fail with CORS Error
**Symptoms:** Browser console shows "Access to XMLHttpRequest blocked by CORS"

**Debug:**
1. Check browser Network tab: POST /api/* should show `Access-Control-Allow-Origin: *` header
2. If missing, netlify.toml headers section may not be applied

**Fix:**
- Redeploy on Netlify (Netlify → Deployments → Trigger deploy)
- Clear browser cache (Ctrl+Shift+Delete)

### Issue: Frontend Builds Successfully But API Calls Fail
**Symptoms:** Page loads, login redirects, but fails after form submit

**Debug:**
1. Check `VITE_BACKEND_URL` is correct in Netlify environment
2. Check Netlify function logs: **Functions → api-proxy → Logs**

**Fix:**
- If env var is missing/wrong, update it and redeploy
- If backend URL is wrong, update and redeploy

### Issue: Database Connection Fails
**Symptoms:** Backend returns "502 Bad Gateway" or "500 Internal Server Error"

**Debug:**
1. Check Render backend logs: look for "DATABASE_URL" errors
2. Test Neon connection: `psql $NEON_DATABASE_URL -c "SELECT 1;"`

**Fix:**
- Verify Neon connection string is correct
- Check Neon dashboard for active connections (may hit limit)
- Run migrations: `alembic upgrade head` on the new database

---

## 📝 Post-Migration: Cleanup

### 1. Scale Down Render Database
Once database is migrated to Neon, you can delete the Render Postgres:
1. Render → **ratiba-db** → **Settings** → **Delete Database**
2. Saves resources and costs

### 2. Update DNS (If Using Custom Domain)
If you're moving from `ratiba-app.onrender.com` to a custom domain:
1. Update DNS records to point to Netlify
2. Update `FRONTEND_URL` on backend

### 3. Archive This Migration Guide
Once verified for 7 days, move to `docs/archived/NETLIFY_DEPLOYMENT_v1.md`

---

## ✨ Summary: What Changed

| Before | After | Benefit |
|--------|-------|---------|
| Frontend on Render Docker | Frontend on Netlify (static + functions) | ✅ Faster deploys, better CDN |
| Postgres on Render free tier | Postgres on Neon | ✅ Auto-scaling, better DX, cheaper |
| Backend + frontend tightly coupled | Decoupled (separate deployments) | ✅ Independent scaling, faster iterations |
| Manual Render redeploys | Auto-deploy on Git push | ✅ Continuous deployment out-of-box |

---

## 🎯 Success Criteria

**MVP is LIVE when:**
- ✅ Frontend loads from `https://ratiba-*.netlify.app`
- ✅ Login works (no CORS/502 errors)
- ✅ Demo crew roster loads
- ✅ Dashboard tiles display correctly
- ✅ API calls reach backend via Netlify function proxy
- ✅ Database queries work via Neon
- ✅ Backend crons still run on Render

**Estimated total time:** **25–30 minutes** (Neon setup + Netlify deploy + verify)

---

## 📞 Support

- **Netlify Docs:** https://docs.netlify.com
- **Neon Docs:** https://neon.tech/docs
- **Frontend Build Issues:** Check Netlify deployment logs
- **Backend Issues:** Check Render service logs
- **Database Issues:** Check Neon dashboard

---

*Last updated: 2026-06-27*  
*Architecture: Netlify (Frontend) + Render (Backend) + Neon (Database)*  
*Target Market: East African aviation operators*

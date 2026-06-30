# Railway Backend Deployment — Fresh Setup Guide

Complete step-by-step guide to deploy the Ratiba backend to Railway with Neon PostgreSQL.

## Architecture Overview

```
Netlify Frontend (React SPA)
        ↓
API Proxy Function (Netlify Functions)
        ↓
Railway Backend (FastAPI + uvicorn on port 8000)
        ↓
Neon PostgreSQL (Serverless managed database)
```

---

## Phase 1: Neon Database Setup

### Step 1: Create Neon Database Project

1. Go to [https://console.neon.tech](https://console.neon.tech)
2. Sign up or log in
3. Create a new project:
   - **Project name:** `ratiba-production` (or your preference)
   - **Database name:** `neondb` (default)
   - **Region:** Choose closest to your users (EU-Central recommended for African operations)
   - **Postgres version:** 15 or 16

### Step 2: Configure Connection Pooler

1. In Neon console, go to your project → **Pooler** tab
2. Create a new pooler:
   - **Name:** `pooler`
   - **Branch:** `main`
   - **Mode:** `Transaction` (best for serverless)
   - **Pool size:** 10 (default is fine)

3. Copy the pooler connection string (you'll need this soon):
   ```
   postgresql://neondb_owner:PASSWORD@POOLER_HOST/neondb?sslmode=require&channel_binding=require
   ```

### Step 3: Enable IP Allowlist (Optional but Recommended)

1. In Neon console → **Settings** → **IP Allowlist**
2. Add Railway's IP ranges (Railway uses AWS, so allow all AWS IPs or use `0.0.0.0/0` for maximum compatibility)

---

## Phase 2: Railway Project Setup

### Step 1: Create Railway Project

1. Go to [https://railway.app](https://railway.app)
2. Sign up or log in
3. Create a new project:
   - Click **"Create a new project"**
   - Select **"Deploy from GitHub"**
   - Connect your GitHub account if not already connected
   - Select repository: `papadanico/Ratiba`
   - Choose branch: `main` (or your desired branch)

### Step 2: Configure Railway Services

After GitHub integration, Railway will auto-detect the `railway.json` and Dockerfile.

**Service Configuration Should Show:**
- ✅ **Service name:** `ratiba-app` (detected from Dockerfile comment or auto-assigned)
- ✅ **Build:** Dockerfile (auto-detected)
- ✅ **Start command:** `bash ./start.sh` (from railway.json)
- ✅ **Port:** 8000 (exposed in Dockerfile)

---

## Phase 3: Environment Variables Configuration

### Critical Variables for Railway

Set these in Railway dashboard → **Environment** tab:

#### Database Connection
```
DATABASE_URL=postgresql://neondb_owner:PASSWORD@POOLER_HOST/neondb?sslmode=require&channel_binding=require
```

#### Security & Auth
```
SECRET_KEY=<generate_a_strong_random_key>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
```

#### Deployment & Observability
```
PORT=8000
LOG_LEVEL=INFO
ENVIRONMENT=production
```

#### URLs
```
FRONTEND_URL=https://ratiacrewmanagement.netlify.app
BACKEND_URL=<YOUR_RAILWAY_PUBLIC_URL>
```

#### Optional: Anthropic Integration (if using Claude features)
```
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL_PARSER=claude-sonnet-4-5
ANTHROPIC_MODEL_CONVERSATIONAL=claude-haiku-4-5
```

#### Optional: Telegram Bot (if configured)
```
TELEGRAM_BOT_TOKEN=<your_token>
TELEGRAM_WEBHOOK_URL=https://<railway-domain>/telegram
```

#### Optional: SMS/Email (if configured)
```
AT_API_KEY=<africa_talking_key>
AT_USERNAME=<africa_talking_user>
SMTP_HOST=<smtp_server>
SMTP_PORT=587
SMTP_USER=<email>
SMTP_PASSWORD=<password>
SMTP_FROM=noreply@ratiba.app
```

### Where to Set Variables in Railway

1. Go to your Railway project
2. Select **ratiba-app** service
3. Click **Variables** tab
4. Click **Add variable** for each key-value pair
5. **Important:** After adding, click **Deploy** to trigger a new deployment with the new variables

---

## Phase 4: Deploy & Verify

### Step 1: Trigger Initial Deployment

After setting environment variables:
1. Go to **Deployments** tab
2. Click **"Deploy"** button to trigger a build
3. Monitor the build logs

### Step 2: Check Build Logs

Watch for:
- ✅ Docker image builds successfully
- ✅ Python dependencies install
- ✅ Alembic migrations run (`alembic upgrade head`)
- ✅ Demo seed runs in background
- ✅ Uvicorn starts on port 8000
- ✅ Healthcheck passes

**Common Issues & Solutions:**

| Issue | Solution |
|-------|----------|
| `DATABASE_URL not set` | Verify env variable is set in Railway dashboard |
| `Alembic migration fails` | Check DATABASE_URL format (must be `postgresql+psycopg://`) |
| `Healthcheck timeout` | Increase `initialDelaySeconds` to 90 in railway.json |
| `Module not found` | Check `backend/requirements.txt` is properly formatted |

### Step 3: Get Public URL

Once deployment succeeds:
1. Go to **Settings** → **Domains**
2. Railway should have assigned a public URL like:
   ```
   https://ratiba-app-production-xxxx.up.railway.app
   ```
3. **Copy this URL** — you'll need it for Netlify configuration

### Step 4: Test Backend

Verify backend is responding:
```bash
curl https://YOUR_RAILWAY_URL/healthz
```

Expected response:
```json
{"status": "ok"}
```

---

## Phase 5: Netlify Configuration

### Set Backend URL in Netlify

1. Go to Netlify dashboard → **ratibacrewmanagement** project
2. Click **Site settings** → **Build & deploy** → **Environment**
3. Add/Update variable:
   - **Key:** `BACKEND_URL`
   - **Value:** `https://YOUR_RAILWAY_URL` (from Step 4 above)
4. Click **Save**
5. Trigger a new Netlify deployment

### Verify Netlify Configuration

Check that:
- ✅ `BACKEND_URL` is set in Environment variables
- ✅ Frontend builds with `npm run build`
- ✅ Functions are bundled (`netlify/functions/api-proxy.ts`)

---

## Phase 6: End-to-End Integration Testing

### Test 1: API Proxy Connection

```bash
# Should proxy to your Railway backend
curl https://ratiacrewmanagement.netlify.app/api/health
```

### Test 2: Frontend Access

1. Open https://ratiacrewmanagement.netlify.app in browser
2. Verify landing page loads
3. Check browser console for errors (F12 → Console tab)

### Test 3: Login Flow

1. Click **Login**
2. Use demo credentials:
   - **Email:** `demo@ratiba-demo.com`
   - **Password:** `DemoPass123`
3. Should redirect to dashboard if successful

### Test 4: Database Query

In the app, perform an action that queries the database (e.g., view crew list). Check:
- Data loads without errors
- No 502/503 errors from API proxy

---

## Phase 7: Monitoring & Debugging

### View Railway Logs

1. Go to Railway project → **ratiba-app** service
2. Click **Logs** tab
3. Watch real-time logs during requests

### Common Log Messages

| Message | Meaning |
|---------|---------|
| `Uvicorn running on 0.0.0.0:8000` | Server started successfully ✅ |
| `alembic upgrade head` | Database migrations completed |
| `demo seed complete` | Demo data seeded (background task) |
| `POST /api/auth/login` | API request received |

### Enable Detailed Logging

Set in Railway environment:
```
LOG_LEVEL=DEBUG
```

This increases verbosity for troubleshooting.

---

## Checklist: Deployment Completion

Use this checklist to verify everything is working:

### Neon Database
- [ ] Neon project created
- [ ] Connection pooler configured
- [ ] Connection string obtained
- [ ] IP allowlist configured (if needed)

### Railway Backend
- [ ] Railway project created
- [ ] GitHub repository connected
- [ ] `railway.json` detected
- [ ] `Dockerfile` detected
- [ ] Environment variables set:
  - [ ] `DATABASE_URL`
  - [ ] `SECRET_KEY`
  - [ ] `PORT=8000`
  - [ ] `FRONTEND_URL`
  - [ ] `BACKEND_URL` (set to Railway public URL)
- [ ] Initial deployment triggered and succeeded
- [ ] Public URL obtained

### Netlify Frontend
- [ ] `BACKEND_URL` environment variable set
- [ ] Frontend deployed successfully
- [ ] Lighthouse scores good (90+)

### Integration
- [ ] API proxy responds to requests
- [ ] Frontend loads without errors
- [ ] Login flow works
- [ ] Database queries execute

### Monitoring
- [ ] Logs accessible in Railway dashboard
- [ ] Healthcheck passing
- [ ] No error messages in logs

---

## Emergency Procedures

### If Backend Build Fails

1. Check build logs for specific error
2. Common causes:
   - Missing Python dependency → add to `backend/requirements.txt`
   - DATABASE_URL format wrong → use `postgresql+psycopg://` not `postgres://`
   - Permission denied on scripts → check `RUN chmod +x` in Dockerfile

### If Healthcheck Fails

1. Increase `initialDelaySeconds` to 90 in `railway.json`
2. Verify uvicorn starts: check logs for `Uvicorn running`
3. Test endpoint manually: `curl http://localhost:8000/healthz`

### If Frontend Can't Reach Backend

1. Verify `BACKEND_URL` is set in Netlify
2. Test URL directly: `curl $BACKEND_URL/healthz`
3. Check CORS headers in api-proxy.ts
4. Verify no firewall blocking (IP allowlist in Neon)

### Database Connection Issues

1. Verify `DATABASE_URL` format is `postgresql+psycopg://`
2. Test connection with `psql` or check Railway logs
3. Ensure Neon pooler mode is `Transaction`
4. Check IP allowlist in Neon

---

## Performance Tuning (After Successful Deployment)

### Database Optimization
- Monitor slow queries in Neon dashboard
- Increase pooler size if connection exhaustion occurs
- Enable query plan analysis

### Railway Optimization
- Monitor memory/CPU usage
- Adjust Python worker count if needed
- Enable caching headers in API responses

### Netlify Optimization
- Monitor Lighthouse scores
- Enable HTTP/2 server push
- Configure cache headers for assets

---

## Next Steps

Once deployment is complete:

1. **Run Playwright E2E Tests:**
   ```bash
   npm run playwright
   ```

2. **Monitor in Production:**
   - Set up error tracking (Sentry)
   - Monitor performance metrics
   - Enable log aggregation

3. **Plan for Scale:**
   - Database connection pooling tuning
   - API rate limiting configuration
   - Cache strategy implementation

---

## Support & Troubleshooting

### Documentation
- Railway docs: https://docs.railway.app
- Neon docs: https://neon.tech/docs
- Netlify docs: https://docs.netlify.com

### Quick Diagnostic Commands

```bash
# Test Railway backend connectivity
curl -v https://YOUR_RAILWAY_URL/healthz

# Test database connection (from Railway logs)
# Should show successful psycopg connection

# Test API proxy (from browser console)
fetch('/api/health').then(r => r.json()).then(console.log)
```

---

**Ready to deploy?** Start with Phase 1 (Neon Database Setup) and work through each phase sequentially.

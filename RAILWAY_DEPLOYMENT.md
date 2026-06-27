# Railway Backend Deployment Guide

**Platform:** Railway (ratiba-api-railway)  
**Region:** Recommended - Eastern US (closest to Africa)  
**Cost:** Free tier available ($5 credit)  

---

## 🚀 Quick Start (5 minutes)

### Step 1: Create Railway Account

1. Go to https://railway.app
2. Click **"Start Project"**
3. Sign in with GitHub (recommended) or email
4. Authorize Railway to access your repositories

### Step 2: Deploy from GitHub

1. Click **"+ New Project"**
2. Select **"Deploy from GitHub repo"**
3. Select `PapaDanico/Ratiba`
4. Select `main` branch
5. Click **"Deploy"**

Railway will automatically:
- ✅ Detect Python project
- ✅ Read requirements.txt
- ✅ Build Docker image
- ✅ Start the app
- ✅ Assign a Railway domain

### Step 3: Set Environment Variables

In Railway Dashboard:

1. Click your **ratiba-api-railway** project
2. Go to **Variables** tab
3. Add these variables:

```
DATABASE_URL = postgresql+psycopg://user:password@host/dbname
FRONTEND_URL = https://ratiacrewmanagement.netlify.app
PORT = 8000
PYTHONUNBUFFERED = 1
```

**Get Neon connection string:**
- Go to https://console.neon.tech
- Select your project → **Connection string**
- Choose **Pooler** (important!)
- Copy the full URL starting with `postgresql://`

### Step 4: Get Your API URL

In Railway Dashboard:

1. Go to **Deployments** tab
2. Look for the **Domain** URL
   - Format: `https://ratiba-api-railway.up.railway.app`
   - Or custom domain if configured

### Step 5: Update Netlify

1. Go to Netlify → ratiacrewmanagement
2. **Site settings** → **Build & deploy** → **Environment**
3. Update variable:
   ```
   VITE_BACKEND_URL = https://ratiba-api-railway.up.railway.app
   ```
4. Click **Trigger deploy**

### Step 6: Test

```bash
# Check API is running
curl https://ratiba-api-railway.up.railway.app/healthz

# Should return 200 OK
```

Then test login at: https://ratiacrewmanagement.netlify.app/login

---

## 📋 Complete Step-by-Step Instructions

### 1. GitHub Integration Setup

Railway needs access to your GitHub repo:

1. Go to https://railway.app/dashboard
2. Click **Account** → **GitHub Integrations**
3. Click **Connect GitHub**
4. Authorize Railway application
5. Select repository access (entire account or specific repos)

### 2. Create New Project

1. Railway Dashboard → **+ New Project**
2. Choose **"Deploy from GitHub repo"**
3. Search for and select `PapaDanico/Ratiba`
4. Choose branch: `main`
5. Click **Deploy**

Railway will:
- Clone your repo
- Detect Python (`requirements.txt`, `Dockerfile`)
- Auto-build Docker image
- Deploy to their infrastructure
- Assign public domain

### 3. Configure Database Connection

**Get Neon Connection String:**

1. Go to https://console.neon.tech
2. Sign in → Select **Ratiba** project
3. Click **Databases** → Select your database
4. Click **Connection string**
5. Select **Pooler** mode (important for serverless/docker)
6. Copy the full URL (starts with `postgresql://`)

**Add to Railway:**

1. Railway Dashboard → Your project
2. Click **Variables** tab
3. Click **+ New Variable**
4. Name: `DATABASE_URL`
5. Value: Paste Neon connection string
6. Click **Add**

### 4. Add Other Environment Variables

In Railway **Variables** tab, add:

| Variable | Value | Description |
|----------|-------|-------------|
| `DATABASE_URL` | `postgresql+psycopg://...` | Neon connection |
| `FRONTEND_URL` | `https://ratiacrewmanagement.netlify.app` | CORS origin |
| `PORT` | `8000` | API port |
| `PYTHONUNBUFFERED` | `1` | Python logging |

### 5. Monitor Deployment

1. Go to **Deployments** tab
2. Watch build progress in real-time
3. Check **Logs** for any errors
4. Wait for "✅ Deployment successful"

### 6. Get Your API URL

In Railway Dashboard:

1. Click **Deployments**
2. Find the active deployment
3. Scroll down to find **Domain URL**
   - Example: `https://ratiba-api-railway.up.railway.app`
4. Copy this URL

### 7. Update Netlify Backend URL

1. Go to Netlify Dashboard
2. Select **ratiacrewmanagement** site
3. **Site settings** → **Build & deploy** → **Environment**
4. Edit `VITE_BACKEND_URL`:
   ```
   VITE_BACKEND_URL=https://ratiba-api-railway.up.railway.app
   ```
5. Click **Save**

### 8. Trigger Netlify Rebuild

1. Netlify Dashboard → **Deployments**
2. Click **Trigger deploy** → **Clear cache and redeploy**
3. Wait for build to complete
4. Check **Deploy log** for success

### 9. Verification

**Test API directly:**
```bash
curl https://ratiba-api-railway.up.railway.app/healthz
# Expected: 200 OK
```

**Test full flow:**
1. Go to https://ratiacrewmanagement.netlify.app/login
2. Click **"Create workspace"**
3. Fill in form with test credentials
4. Click **"Create workspace & enter"**
5. Should navigate to dashboard (/app)
6. Should load crew data

---

## 🔧 Railway Dashboard Features

### Monitoring

- **Logs** tab: Real-time application logs
- **Metrics** tab: CPU, memory, network usage
- **Health** tab: Service health status

### Environment Variables

- **Variables** tab: Manage all env vars
- **Raw editor** or **Form editor** options
- Auto-redeploys on variable changes

### Deployments

- **Deployments** tab: View all deploys
- **Rollback** capability (1-click restore)
- **Manual deploy** option
- **CI/CD** integration with GitHub

### Networking

- **Domain** tab: Public URL and custom domains
- **Protected Services** for security
- **Webhooks** for integrations

---

## ✅ Complete Deployment Checklist

### Pre-Deployment
- [ ] GitHub account connected to Railway
- [ ] Ratiba repository accessible
- [ ] Neon database created and configured
- [ ] Neon connection string copied (Pooler mode)

### Deployment
- [ ] Created Railway account at railway.app
- [ ] Authorized Railway with GitHub
- [ ] Selected PapaDanico/Ratiba repo
- [ ] Deployment started and completed
- [ ] Railway assigned domain URL (ratiba-api-railway.up.railway.app)

### Configuration
- [ ] Added `DATABASE_URL` to Railway Variables
- [ ] Added `FRONTEND_URL` to Railway Variables
- [ ] Added `PORT=8000` to Railway Variables
- [ ] Verified variables in Railway dashboard

### Netlify Update
- [ ] Updated `VITE_BACKEND_URL` in Netlify
- [ ] Triggered Netlify redeploy
- [ ] Build completed successfully

### Verification
- [ ] curl https://ratiba-api-railway.up.railway.app/healthz → 200
- [ ] Login page loads at frontend URL
- [ ] Can create account and login
- [ ] Dashboard loads and displays data
- [ ] No console errors in browser

---

## 🚨 Troubleshooting

### "Deployment failed"
1. Check **Logs** tab in Railway
2. Look for Python/Docker build errors
3. Ensure requirements.txt is in root
4. Check Dockerfile exists

### "502 Bad Gateway" at API
1. Check if Railway deployment is running
2. Verify **PORT** environment variable = 8000
3. Check **Logs** for application errors
4. Check DATABASE_URL is set correctly

### "Cannot connect to database"
1. Verify DATABASE_URL format: `postgresql+psycopg://...`
2. Check Neon database is running
3. Test connection: `psql <DATABASE_URL>`
4. Verify firewall allows connections

### "Login doesn't work"
1. Check Network tab in browser DevTools
2. Verify FRONTEND_URL is set in Railway
3. Check `/api/v1/auth/me` endpoint exists
4. Verify Neon database has user data

---

## 📊 Railway vs Render vs Fly.io

| Feature | Railway | Render | Fly.io |
|---------|---------|--------|--------|
| Setup Time | 5 min | 5 min | 10 min |
| Free Tier | $5 credit | Sleeps | Always on |
| Cold Start | ~500ms | ~30s | ~200ms |
| Auto-Deploy | GitHub push | GitHub push | CLI deploy |
| Cost | Pay-as-you-go | Free (sleepy) | Free (shared) |
| Best For | Beginners | Hobby projects | Production |
| Support | Good | Good | Excellent |

---

## 💡 Pro Tips

1. **Monitor logs regularly** - Railway shows real-time logs
2. **Enable auto-deploy** - Railway redeploys on `main` push
3. **Use environment variables** - Don't hardcode secrets
4. **Test migrations** - Alembic runs automatically on deploy
5. **Set resource limits** - Monitor CPU/memory usage
6. **Use Pooler connection** - Railway runs in containers (not always-on)

---

## 🎯 Success Criteria

Your deployment is complete when:

✅ API responds to health check  
✅ Frontend can reach backend  
✅ Users can create accounts  
✅ Login succeeds  
✅ Dashboard displays crew data  
✅ No "Cannot GET" or 404 errors  

---

**Need help?** Railway support: https://railway.app/support

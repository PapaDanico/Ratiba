# Netlify Automatic Deployment Setup

**Status:** ✅ Merged to main (automatic deployment ready)

This guide walks you through the final setup steps to enable automatic Netlify deployment.

---

## 📋 Prerequisites

- Netlify account created (free tier available at netlify.com)
- Netlify site linked to GitHub repository
- GitHub account with admin access to papadanico/ratiba

---

## 🔑 Step 1: Get Netlify Secrets

### 1a. Get NETLIFY_AUTH_TOKEN

1. Go to **Netlify** → **User Menu** (top right) → **User Settings**
2. Click **Applications** → **Tokens**
3. Click **New access token** → Give it a name (e.g., "GitHub Actions Deploy")
4. Copy the token (⚠️ won't be shown again)

### 1b. Get NETLIFY_SITE_ID

1. Go to **Netlify** → Select your site → **Site Settings**
2. Find **General** → Scroll to **Site details**
3. Copy the **Site ID** (looks like `abc123-def456`)

---

## 🔐 Step 2: Add GitHub Secrets

### Add Secrets via GitHub UI

1. Go to **GitHub** → `papadanico/ratiba` → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**

#### Secret 1: NETLIFY_AUTH_TOKEN
- **Name:** `NETLIFY_AUTH_TOKEN`
- **Value:** Paste your Netlify token from Step 1a
- Click **Add secret**

#### Secret 2: NETLIFY_SITE_ID
- **Name:** `NETLIFY_SITE_ID`
- **Value:** Paste your site ID from Step 1b
- Click **Add secret**

### Verify Secrets

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. You should see both secrets listed (values hidden)

---

## ✅ Step 3: Verify Automatic Deployment

### Test 1: Check Workflow Status

1. Go to **GitHub** → `papadanico/ratiba` → **Actions**
2. Look for **Deploy** workflow
3. You should see recent runs (triggered on merges to main)

### Test 2: Trigger a Deployment

Make a small change to `frontend/` and push to main:

```bash
git checkout main
git pull origin main

# Make a small change to frontend (e.g., update a comment)
echo "// Updated" >> frontend/vite.config.ts

# Commit and push
git add frontend/vite.config.ts
git commit -m "chore: test automatic deployment"
git push origin main
```

Then check:
1. **GitHub Actions** → **Deploy** workflow should start
2. **Netlify** → **Deployments** should show a new deploy
3. Build should complete in ~2–3 minutes

### Test 3: Check Frontend URL

After deploy completes:
1. Go to **Netlify** → **Deployments**
2. Click latest deploy → **Preview**
3. Frontend should load at `https://ratiba-*.netlify.app`

---

## 🚀 How Automatic Deployment Works

**Trigger:** Push to `main` in `frontend/`, `netlify/`, or `.github/workflows/deploy.yml`

**Workflow:**
1. GitHub Actions downloads code
2. Runs `npm install` in `frontend/`
3. Runs `npm run lint` (optional, continues on error)
4. Runs `npm run typecheck` (optional, continues on error)
5. Runs `npm run build` (builds to `frontend/dist`)
6. Calls Netlify API to deploy `dist/` folder
7. Netlify publishes to CDN (takes ~30–60 sec)

**Netlify Environment Variables:**
- `VITE_BACKEND_URL=https://ratiba-api.onrender.com` — Set in GitHub Actions

---

## 🔍 Monitoring & Troubleshooting

### Check Workflow Logs

1. **GitHub** → **Actions** → **Deploy** → Click recent run
2. Expand **Deploy Frontend to Netlify** step
3. See build output and any errors

### Common Issues

#### Issue: "NETLIFY_AUTH_TOKEN not found"
**Solution:** Check GitHub Secrets are correctly added (Settings → Secrets)

#### Issue: Build fails with "npm ci failed"
**Solution:** Check `frontend/package-lock.json` is committed and up-to-date
```bash
cd frontend
npm ci  # Should work locally
```

#### Issue: Deploy to Netlify fails but build succeeds
**Solution:** Verify Netlify secrets:
1. GitHub Secrets → Check `NETLIFY_AUTH_TOKEN` is correct
2. Netlify → Check token is valid and not expired
3. Regenerate token if needed: Netlify → User Settings → Tokens

#### Issue: Netlify deploy succeeds but site still shows old version
**Solution:** Clear Netlify cache
1. Netlify → **Deployments** → **Trigger new deploy**
2. Or wait 5 minutes for cache invalidation

---

## 📊 Monitoring Deployment

### GitHub Actions Dashboard
- **URL:** `https://github.com/papadanico/ratiba/actions`
- **Workflow:** Deploy
- Shows: Build time, logs, success/failure status

### Netlify Dashboard
- **URL:** `https://app.netlify.com`
- **Site:** ratiba-*
- **Deployments:** History, status, logs, preview URLs

### Performance Metrics
| Metric | Target | Where to Check |
|--------|--------|-----------------|
| Build time | < 3 min | GitHub Actions logs |
| Deploy time | < 1 min | Netlify Deployments |
| Site load time | < 2s | Netlify Analytics |

---

## 🎯 Next Steps

### Phase 1: Verify (Today)
- ✅ Secrets added to GitHub
- ✅ First deployment succeeds
- ✅ Frontend loads at Netlify URL
- ✅ API proxy works (login works)

### Phase 2: Monitor (Next 7 days)
- Track deployment success rate
- Monitor site performance
- Test on real devices
- Check browser console for errors

### Phase 3: Optimize (Optional)
- Add performance monitoring (Sentry)
- Set up custom domain
- Add automated testing
- Enable preview deployments for PRs

---

## 📝 Enable Preview Deployments (Optional)

To get auto-preview URLs for every PR:

1. **Netlify** → **Site settings** → **Build & deploy** → **Deploy contexts**
2. Enable **Deploy previews**
3. Now every PR will get its own preview URL

Then GitHub workflow comment will show:
```
✅ Preview: https://deploy-preview-42--ratiba.netlify.app
```

---

## 🛑 Disable Automatic Deployment (If Needed)

Edit `.github/workflows/deploy.yml`:

```yaml
on:
  push:
    branches: [main]
    paths:  # ← Remove or comment out to disable auto-trigger
      - 'frontend/**'
      - 'netlify/**'
```

Then manual deploy via:
```bash
# Trigger manually in GitHub Actions UI
# Or use Netlify CLI:
netlify deploy --prod --dir=frontend/dist
```

---

## ✨ Success!

Once setup is complete:
1. Push changes to main
2. GitHub Actions auto-builds and deploys
3. Netlify CDN serves the frontend
4. No manual deployment steps needed

**Estimated deployment time:** 3–5 minutes (from push to live)

---

*Last updated: 2026-06-27*  
*Deployment: Netlify (automatic on main push)*  
*Target Market: East African aviation operators*

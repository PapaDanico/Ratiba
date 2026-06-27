# Neon Database Migration Guide

**Phase:** 6 (Pilot deployment + 30-day stability)  
**Timeline:** ~15 minutes  
**Effort:** Low (mostly copy-paste)

---

## 🎯 Overview

Migrate the Ratiba database from **Render Postgres** (free tier) to **Neon** (managed Postgres with auto-scaling).

**Why Neon?**
- ✅ Auto-scaling without downsizing
- ✅ Better dev experience (serverless, connection pooling)
- ✅ Cheaper than Render paid tier
- ✅ Better performance monitoring

---

## 📋 Prerequisites

- [ ] Neon account created (https://neon.tech)
- [ ] Neon project initialized with database
- [ ] Neon connection string ready
- [ ] `pg_dump` and `psql` installed locally (PostgreSQL client tools)
- [ ] Render Postgres connection string available
- [ ] Backend currently running on Render

---

## 🚀 Step 1: Get Connection Strings

### 1a. Get Neon Connection String

1. Go to **neon.tech** → Select your project
2. Click **Databases** → Select the database
3. Click **Connection string** → Copy the **Connection string** tab
4. Choose **Pooler** (recommended for serverless/Lambda)
5. Copy the full URL:
   ```
   postgresql://user:password@host.neon.tech/dbname?sslmode=require
   ```

### 1b. Get Render Postgres Connection String

1. Go to **Render Dashboard** → **ratiba-db**
2. Click **Connections** → Copy **External Database URL**
3. Should look like:
   ```
   postgresql://ratiba:password@dpg-XXXXX.render.com/ratiba
   ```

---

## 🔄 Step 2: Run Migration Script

Run the provided migration script:

```bash
cd /home/user/Ratiba

OLD_DATABASE_URL="postgresql://ratiba:password@dpg-XXXXX.render.com/ratiba" \
NEON_DATABASE_URL="postgresql://user:password@host.neon.tech/dbname?sslmode=require" \
./scripts/migrate-to-neon.sh
```

**What it does:**
1. Validates both database connections
2. Dumps data from Render Postgres
3. Restores to Neon
4. Runs Alembic migrations
5. Verifies operator/crew counts
6. Creates backup SQL file

**Expected output:**
```
✅ Step 1: Validating database connections
✅ Step 2: Dumping database from Render Postgres...
   Backup saved: ratiba_backup_20260627_101234.sql (2.5M bytes)
✅ Step 3: Restoring database to Neon...
✅ Step 4: Running Alembic migrations...
✅ Step 5: Verifying migration...
   operator_count: 2
   crew_count: 42
🎉 Migration complete!
```

---

## 📝 Step 3: Update Render Backend Environment

Update the backend to use Neon connection string:

1. Go to **Render Dashboard** → **ratiba-api** service
2. Click **Environment**
3. Find `DATABASE_URL` → Click edit
4. Replace with your **Neon connection string**:
   ```
   postgresql://user:password@host.neon.tech/dbname?sslmode=require
   ```
5. Click **Save** (triggers automatic redeploy)

**Wait for redeploy to complete** (~2 minutes)

---

## ✅ Step 4: Verify Connection

Check that backend connected to Neon:

```bash
# Check Render logs
curl https://ratiba-api.onrender.com/healthz
# Expected: 200 OK

# Or check Render dashboard → ratiba-api → Logs
# Look for: "Connection successful" or no "DATABASE_URL" errors
```

---

## 🗑️ Step 5: Cleanup (Optional)

Once verified for 24 hours, delete the Render Postgres database to save costs:

1. Go to **Render Dashboard** → **ratiba-db**
2. Click **Settings** → **Delete Database**
3. Confirm deletion

**Before deleting:**
- ✅ Verify backend logs show no connection errors
- ✅ Test login flow (api/v1/auth/login)
- ✅ Verify data loads (crew list, roster, etc.)
- ✅ Check Neon connection stats show traffic

---

## 🔍 Verification Checklist

- [ ] Migration script ran successfully
- [ ] Backup file created and saved
- [ ] Neon shows data loaded (✓ operator_count, crew_count)
- [ ] Render backend environment updated
- [ ] Backend redeployed (watch for green checkmark)
- [ ] Backend /healthz returns 200 OK
- [ ] No "DATABASE_URL" errors in Render logs
- [ ] Frontend login flow works
- [ ] Dashboard loads crew data
- [ ] Neon dashboard shows active connections
- [ ] Test with real operator account

---

## 🛡️ Rollback Plan (If Needed)

If something goes wrong:

```bash
# Restore from backup (before deleting Render DB)
psql "$RENDER_DATABASE_URL" < ratiba_backup_20260627_101234.sql

# Then revert Render environment to old connection string
# Render Dashboard → ratiba-api → Environment → DATABASE_URL → [old value]
```

---

## 📊 Expected Performance Improvements

| Metric | Before (Render) | After (Neon) |
|--------|-----------------|--------------|
| Cold start | ~30s | ~5s |
| Query latency | ~100ms | ~50ms |
| Connections | 10 (free tier) | Unlimited |
| Auto-scaling | Manual | Automatic |
| Backup frequency | Daily | Hourly |

---

## 🔧 Environment Variables

After migration, confirm these are set correctly:

**Render backend (ratiba-api):**
- `DATABASE_URL` → Neon connection string ✅
- `FRONTEND_URL` → Netlify frontend URL ✅
- `REDIS_URL` → Render Redis ✅
- All other configs unchanged

**Netlify frontend:**
- `VITE_BACKEND_URL` → https://ratiba-api.onrender.com ✅

**Neon database:**
- No env vars needed (connection URL is all you need)

---

## 📞 Troubleshooting

### Issue: "Connection refused" on Neon
**Solution:** 
- Check Neon connection string has `?sslmode=require`
- Verify Neon project is in correct region
- Check IP allowlist (Neon allows all by default)

### Issue: "Wrong password" error
**Solution:**
- Copy connection string again from Neon dashboard
- Ensure no extra spaces or characters
- Check password doesn't have special chars that need escaping

### Issue: Alembic migrations fail
**Solution:**
- Ensure Neon database is empty OR already has schema
- Run manually: `alembic upgrade head`
- Check Alembic version tracking table

### Issue: Backup file too large
**Solution:**
- Compress: `gzip ratiba_backup_*.sql`
- Split: `split -b 500M backup.sql backup_`
- Upload to S3 or similar for archival

---

## 📝 What Changed

| Component | Before | After |
|-----------|--------|-------|
| Database Host | Render free tier | Neon managed |
| Connection Pool | No pooling | Neon pooler included |
| Auto-scaling | None (hit limits) | Automatic |
| Backups | Daily | Hourly |
| Monitoring | Basic | Advanced (Neon dashboard) |
| Cost | $7/month (Render paid) | Free tier (generous) |

---

## ✨ Success Criteria

**Migration is complete when:**
- ✅ Data migrated to Neon (operator/crew counts match)
- ✅ Backend updated to use Neon connection string
- ✅ Backend redeploy successful (green checkmark on Render)
- ✅ Frontend login works
- ✅ Dashboard loads without errors
- ✅ No "DATABASE_URL" errors in logs for 5 minutes
- ✅ Neon dashboard shows active connections

---

## 🎯 Next Steps

1. **Immediate:** Run migration script (5 min)
2. **Immediate:** Update Render environment (2 min)
3. **Wait:** Render redeploy completes (2 min)
4. **Verify:** Test login flow (2 min)
5. **Monitor:** Watch logs for 1 hour
6. **Optional:** Delete Render Postgres (24 hours later)

**Total time:** ~15 minutes

---

*Last updated: 2026-06-27*  
*Database: Render Postgres → Neon Managed Postgres*  
*Target: Complete Phase 6 migration*

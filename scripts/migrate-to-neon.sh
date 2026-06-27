#!/bin/bash
# ═════════════════════════════════════════════════════════════════════════════
# Migrate Ratiba database from Render Postgres to Neon
# ═════════════════════════════════════════════════════════════════════════════

set -e

echo "🔄 Ratiba Database Migration: Render → Neon"
echo "═══════════════════════════════════════════"
echo ""

# Step 1: Validate inputs
if [ -z "$OLD_DATABASE_URL" ]; then
  echo "❌ Error: OLD_DATABASE_URL not set (Render Postgres connection string)"
  echo "Usage: OLD_DATABASE_URL=postgresql://... NEON_DATABASE_URL=postgresql://... $0"
  exit 1
fi

if [ -z "$NEON_DATABASE_URL" ]; then
  echo "❌ Error: NEON_DATABASE_URL not set (Neon connection string)"
  echo "Usage: OLD_DATABASE_URL=postgresql://... NEON_DATABASE_URL=postgresql://... $0"
  exit 1
fi

echo "✅ Step 1: Validating database connections"
echo "   Old (Render): ${OLD_DATABASE_URL%%@*}@***"
echo "   New (Neon):   ${NEON_DATABASE_URL%%@*}@***"
echo ""

# Step 2: Dump from Render
echo "✅ Step 2: Dumping database from Render Postgres..."
BACKUP_FILE="ratiba_backup_$(date +%Y%m%d_%H%M%S).sql"
pg_dump "$OLD_DATABASE_URL" > "$BACKUP_FILE"
echo "   Backup saved: $BACKUP_FILE ($(wc -c < "$BACKUP_FILE" | numfmt --to=iec 2>/dev/null || wc -c < "$BACKUP_FILE") bytes)"
echo ""

# Step 3: Restore to Neon
echo "✅ Step 3: Restoring database to Neon..."
psql "$NEON_DATABASE_URL" < "$BACKUP_FILE"
echo "   Restore complete ✓"
echo ""

# Step 4: Run migrations
echo "✅ Step 4: Running Alembic migrations..."
export DATABASE_URL="$NEON_DATABASE_URL"
cd "$(dirname "$0")/.."
python -m alembic upgrade head
echo "   Migrations complete ✓"
echo ""

# Step 5: Verify
echo "✅ Step 5: Verifying migration..."
psql "$NEON_DATABASE_URL" -c "SELECT COUNT(*) as operator_count FROM operator;"
psql "$NEON_DATABASE_URL" -c "SELECT COUNT(*) as crew_count FROM crew;"
psql "$NEON_DATABASE_URL" -c "SELECT version();" | head -1
echo ""

echo "🎉 Migration complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Update Render backend environment:"
echo "      Render Dashboard → ratiba-api → Environment"
echo "      Set DATABASE_URL to your Neon connection string"
echo "   2. Save and trigger redeploy"
echo "   3. Verify backend connects to Neon (check logs)"
echo "   4. Delete Render Postgres database (optional, saves costs)"
echo ""
echo "💾 Backup location: $BACKUP_FILE"
echo "   Keep this safe until you verify everything works!"

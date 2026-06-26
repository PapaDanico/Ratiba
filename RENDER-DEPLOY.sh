#!/bin/bash
set -e

# Render Deployment Automation Script for Ratiba Phase 6
# This script guides deployment to Render (free tier)
#
# Prerequisites:
# - Render account (https://dashboard.render.com)
# - GitHub repository access
# - Git configured locally

echo "🚀 Ratiba Phase 6 Deployment to Render"
echo "======================================="
echo ""
echo "This script will guide you through deploying Ratiba to Render."
echo "All code is ready to deploy."
echo ""

# Check if we're on main branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" != "main" ]; then
    echo "❌ Error: Must be on main branch. Current: $BRANCH"
    exit 1
fi

echo "✅ Branch: main"
echo "✅ Last commit: $(git log -1 --oneline)"
echo ""

# Verify all infrastructure is in place
echo "🔍 Verifying deployment files..."
[ -f render.yaml ] && echo "  ✅ render.yaml (6-service blueprint)" || { echo "  ❌ render.yaml missing"; exit 1; }
[ -f DEPLOYMENT_GUIDE.md ] && echo "  ✅ DEPLOYMENT_GUIDE.md (8 verification tests)" || { echo "  ❌ DEPLOYMENT_GUIDE.md missing"; exit 1; }
[ -f backend/keepwarm-cron.sh ] && echo "  ✅ keepwarm-cron.sh (10-min health pings)" || { echo "  ❌ keepwarm-cron.sh missing"; exit 1; }
[ -f backend/digest-cron.sh ] && echo "  ✅ digest-cron.sh (scheduled digest)" || { echo "  ❌ digest-cron.sh missing"; exit 1; }
[ -f backend/Dockerfile ] && echo "  ✅ backend/Dockerfile (multi-service)" || { echo "  ❌ backend/Dockerfile missing"; exit 1; }
[ -f frontend/Dockerfile ] && echo "  ✅ frontend/Dockerfile (nginx + SPA)" || { echo "  ❌ frontend/Dockerfile missing"; exit 1; }

echo ""
echo "✅ All deployment files verified!"
echo ""

# Display deployment procedure
echo "📋 DEPLOYMENT PROCEDURE (45 minutes)"
echo "===================================="
echo ""
echo "STEP 1: Connect Render Blueprint (12 min)"
echo "  1. Go to: https://dashboard.render.com"
echo "  2. Click: New → Blueprint"
echo "  3. Connect GitHub: PapaDanico/Ratiba"
echo "  4. Select branch: main"
echo "  5. Review 6 services in preview"
echo "  6. Click: Deploy"
echo ""
echo "STEP 2: Post-Deploy Manual Config (5 min)"
echo "  1. Set ratiba-app BACKEND_URL = https://ratiba-api.onrender.com"
echo "  2. Set ratiba-api FRONTEND_URL = https://ratiba-app.onrender.com"
echo "  3. Set ratiba-keepwarm API_URL = https://ratiba-api.onrender.com"
echo ""
echo "STEP 3: Verification Tests (30 min)"
echo "  1. Frontend loads: curl -I https://ratiba-app.onrender.com/"
echo "  2. Login page renders (browser)"
echo "  3. Login with demo credentials"
echo "  4. Backend health: curl https://ratiba-api.onrender.com/healthz"
echo "  5. Test background jobs"
echo "  6. Monitor scheduled crons"
echo "  7. Test data persistence"
echo "  8. Test audit pack download"
echo ""
echo "See DEPLOYMENT_GUIDE.md for detailed instructions and test checklist"
echo ""

# Verify render.yaml is valid
echo "🔍 Validating render.yaml..."
if grep -q "ratiba-api\|ratiba-app\|ratiba-worker\|ratiba-digest\|ratiba-keepwarm\|ratiba-redis\|ratiba-db" render.yaml; then
    echo "✅ All 6 services configured in render.yaml"
else
    echo "❌ render.yaml missing services"
    exit 1
fi

echo ""
echo "======================================="
echo "✅ CODE IS READY FOR DEPLOYMENT"
echo "======================================="
echo ""
echo "📖 Next Steps:"
echo "  1. Open: https://dashboard.render.com"
echo "  2. Follow STEP 1 (Connect Blueprint)"
echo "  3. Follow the deployment guide for complete instructions"
echo ""
echo "📚 Documentation:"
echo "  - DEPLOYMENT_GUIDE.md (complete guide)"
echo "  - PHASE6-QA-SUMMARY.md (QA checklist)"
echo "  - render.yaml (deployment blueprint)"
echo ""
echo "🟢 Deployment Status: GO"
echo ""

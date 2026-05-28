#!/bin/sh
set -e

# Extract hostname from BACKEND_URL (e.g. https://ratiba-api.onrender.com → ratiba-api.onrender.com)
# so nginx sends the correct Host header to Render's edge router.
if [ -n "$BACKEND_URL" ]; then
    BACKEND_HOST=$(echo "$BACKEND_URL" | sed 's|^https\?://||' | cut -d'/' -f1)
    export BACKEND_HOST
fi

envsubst '$BACKEND_URL $BACKEND_HOST' \
  < /app/nginx.conf.template \
  > /etc/nginx/conf.d/default.conf

exec nginx -g "daemon off;"

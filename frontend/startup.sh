#!/bin/sh
set -e

# Substitute only $BACKEND_URL — nginx variables ($uri, $http_host, etc.) are
# left as-is for nginx to resolve at request time.
envsubst '$BACKEND_URL' \
  < /app/nginx.conf.template \
  > /etc/nginx/conf.d/default.conf

exec nginx -g "daemon off;"

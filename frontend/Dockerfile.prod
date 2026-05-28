# ── Stage 1: build Vite app ──────────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

# ── Stage 2: nginx to serve static files + proxy /api to backend ─────────────
FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html

# nginx config template — $BACKEND_URL is substituted at container start.
# Other nginx vars ($uri, $http_host, etc.) are left untouched.
COPY nginx.conf.template /app/nginx.conf.template

# Startup: run envsubst on the template then hand off to nginx.
COPY startup.sh /startup.sh
RUN chmod +x /startup.sh

EXPOSE 80

CMD ["/startup.sh"]

# Ratiba Backend — Deploy to Railway
# This Dockerfile builds the Python FastAPI backend
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps (WeasyPrint, psycopg, build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        shared-mime-info \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cached layer)
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

# Copy application source
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./
COPY backend/scripts ./scripts

EXPOSE 8000

COPY backend/start.sh ./
COPY backend/worker.sh ./
COPY backend/digest-cron.sh ./
COPY backend/keepwarm-cron.sh ./
RUN chmod +x start.sh worker.sh digest-cron.sh keepwarm-cron.sh

CMD ["./start.sh"]

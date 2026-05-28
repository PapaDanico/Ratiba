FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps:
#  - WeasyPrint: pango, cairo, gdk-pixbuf
#  - psycopg: libpq
#  - build-essential for any source wheels
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

WORKDIR /workspace

# Install python deps from root pyproject.toml. We copy only the project metadata
# first to keep this layer cacheable.
COPY pyproject.toml ./
COPY backend ./backend

RUN pip install -e ".[dev]"

WORKDIR /app

EXPOSE 8000

# Default CMD overridden by docker-compose for dev with --reload.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

"""FastAPI application entry point."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

import sentry_sdk
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app import __version__
from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.job_queue import use_redis_queue
from app.core.logging import configure_logging
from app.schemas.health import HealthResponse, ReadyResponse, VersionResponse


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging()
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=0.0,
            send_default_pii=False,
        )
    # Wire the Redis-backed job queue when Redis is actually reachable. The
    # in-process queue (default) stays the fallback for local dev without
    # Redis and for tests.
    if settings.redis_url:
        try:
            import redis

            redis.from_url(settings.redis_url, socket_connect_timeout=1).ping()
            use_redis_queue(settings.redis_url)
        except Exception:
            pass
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    # Defense-in-depth: never run a real deployment on the baked-in dev secret
    # (it would let anyone forge JWTs). Render sets RENDER=true; on Render the
    # secret is injected (render.yaml generateValue), so this only trips on a
    # genuine misconfig. Local dev/tests (no RENDER var) are unaffected.
    if os.getenv("RENDER") and settings.secret_key.startswith("change_me_dev_only"):
        raise RuntimeError(
            "SECRET_KEY is the insecure dev default in a deployed environment — "
            "set a strong SECRET_KEY before starting."
        )

    app = FastAPI(
        title="Ratiba",
        description="AI-anchored crew rostering platform.",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz", response_model=HealthResponse, tags=["meta"])
    async def healthz() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/version", response_model=VersionResponse, tags=["meta"])
    async def version() -> VersionResponse:
        return VersionResponse(name="ratiba", version=__version__, phase="6")

    @app.get("/readyz", response_model=ReadyResponse, tags=["meta"])
    async def readyz(response: Response) -> ReadyResponse:
        """Orchestrator readiness probe — verifies DB + Redis are reachable.

        Returns 503 when the database is unreachable (``not_ready``) so a
        platform health check won't route to an instance that can't serve.
        Redis-only failure is ``degraded`` but still 200 — Redis is optional
        (the job queue falls back to in-process)."""
        checks: dict[str, str] = {}
        db_ok = True
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            checks["postgres"] = "ok"
        except Exception as exc:
            checks["postgres"] = f"unreachable: {exc!r}"
            db_ok = False

        redis_ok = True
        if settings.redis_url:
            try:
                import redis

                redis.from_url(settings.redis_url, socket_connect_timeout=1).ping()
                checks["redis"] = "ok"
            except Exception as exc:
                checks["redis"] = f"unreachable: {exc!r}"
                redis_ok = False

        status_str: Literal["ready", "degraded", "not_ready"]
        if not db_ok:
            status_str = "not_ready"
        elif not redis_ok:
            status_str = "degraded"
        else:
            status_str = "ready"
        if status_str == "not_ready":
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadyResponse(status=status_str, checks=checks)

    app.include_router(api_router)
    return app


app = create_app()

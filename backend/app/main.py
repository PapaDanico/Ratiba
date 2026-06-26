"""FastAPI application entry point."""

from __future__ import annotations

import os
import secrets
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Literal

import sentry_sdk
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import __version__
from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.cookies import AUTH_COOKIES, CSRF_COOKIE, CSRF_HEADER
from app.core.database import engine
from app.core.job_queue import use_redis_queue
from app.core.logging import configure_logging
from app.schemas.health import HealthResponse, ReadyResponse, VersionResponse

_CSRF_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

#: Public session-establishment endpoints. They are authorised by body
#: credentials (email/password, pairing code), never by an ambient session
#: cookie, so CSRF doesn't apply — and a request may legitimately arrive
#: carrying an unrelated, stale auth cookie (e.g. logging in as an officer on a
#: device that still holds a pilot cookie).
_CSRF_EXEMPT_PATHS = frozenset(
    {
        "/api/v1/auth/login",
        "/api/v1/auth/pilot-pair",
        "/api/v1/auth/demo-workspace",
    }
)


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

    # CSRF (double-submit token). Registered before CORS so CORS stays the
    # outermost layer (Starlette runs the last-added middleware first) and even
    # a rejected request still carries the right CORS headers.
    #
    # Only cookie-authenticated unsafe requests are checked: an explicit
    # ``Authorization: Bearer`` header is not an ambient credential (so the bot,
    # API clients, and the Bearer-based test suite are exempt), and an
    # unauthenticated request (login, pairing) carries no auth cookie yet.
    @app.middleware("http")
    async def csrf_protect(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method not in _CSRF_SAFE_METHODS and request.url.path not in _CSRF_EXEMPT_PATHS:
            auth = request.headers.get("Authorization", "")
            is_bearer = auth.lower().startswith("bearer ")
            has_auth_cookie = any(name in request.cookies for name in AUTH_COOKIES)
            if not is_bearer and has_auth_cookie:
                header = request.headers.get(CSRF_HEADER)
                cookie = request.cookies.get(CSRF_COOKIE)
                if not header or not cookie or not secrets.compare_digest(header, cookie):
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": "CSRF token missing or invalid"},
                    )
        return await call_next(request)

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

"""Shared pytest fixtures."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import create_app
from app.models import Operator, User
from app.models.operator import OperatorTier
from app.models.user import UserRole


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> Iterator[None]:
    """Reset the in-process rate limiters between tests.

    They're process-global state; without this, tests sharing a key
    (the constant TestClient host, or a reused telegram_chat_id) exhaust
    the per-window budget and later ones spuriously 429.
    """
    from app.core.rate_limit import LOGIN_LIMITER, PAIRING_LIMITER

    PAIRING_LIMITER.reset()
    LOGIN_LIMITER.reset()
    yield
    PAIRING_LIMITER.reset()
    LOGIN_LIMITER.reset()


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app) as c:
        yield c


# -- DB-backed fixtures (Phase 3+) -------------------------------------------
#
# These tests need a live PostgreSQL because the schema uses JSONB, ARRAY,
# and an append-only trigger on audit_events. The fixtures probe for
# reachability and skip cleanly when the DB isn't available — so local devs
# without `docker compose up db` still get a green run.


def _test_database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL") or os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://ratiba:dev_password@localhost:5432/ratiba_test"
    )


@pytest.fixture(scope="session")
def db_engine():  # type: ignore[no-untyped-def]
    """Build the test schema by applying the real Alembic migration chain.

    Phase 6 closes the Phase 3 risk where conftest used
    ``Base.metadata.create_all`` — a column added to a model but not
    migrated would have still passed tests. We now run the same migrations
    production runs.
    """
    url = _test_database_url()
    try:
        engine = create_engine(url, future=True)
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL not reachable at {url}: {exc!r}")

    # Drop everything (tables, types, functions) so each test session
    # starts from a clean slate.
    with engine.begin() as c:
        c.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        c.execute(text("CREATE SCHEMA public"))

    # Apply the migration chain. Alembic picks up the URL from settings,
    # which in CI is TEST_DATABASE_URL, in local dev it's
    # postgresql+psycopg://...localhost.
    from pathlib import Path

    from alembic.config import Config

    from alembic import command

    backend_dir = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")

    yield engine

    with engine.begin() as c:
        c.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        c.execute(text("CREATE SCHEMA public"))


@pytest.fixture
def db_session(db_engine) -> Iterator[Session]:  # type: ignore[no-untyped-def]
    """Function-scoped session that rolls back after each test for isolation."""
    SessionLocal = sessionmaker(bind=db_engine, expire_on_commit=False, future=True)
    session = SessionLocal()
    # Truncate every table before the test runs so cross-test bleed is zero.
    with db_engine.begin() as c:
        c.execute(
            text(
                "TRUNCATE TABLE "
                + ", ".join(t for t in Base.metadata.tables if t != "alembic_version")
                + " RESTART IDENTITY CASCADE"
            )
        )
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seeded_operator(db_session: Session) -> Operator:
    op = Operator(
        aoc_number=f"TEST-{uuid.uuid4().hex[:8]}",
        name="Test Aviation Ltd.",
        base="HKJK",
        contact_email="ops@test.example",
        tier=OperatorTier.ENTRY,
    )
    db_session.add(op)
    db_session.commit()
    db_session.refresh(op)
    return op


@pytest.fixture
def seeded_user(db_session: Session, seeded_operator: Operator) -> User:
    user = User(
        operator_id=seeded_operator.id,
        email="officer@test.example",
        hashed_password=hash_password("hunter2pass"),
        full_name="Test Crewing Officer",
        role=UserRole.CREWING_OFFICER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_client(
    db_engine,  # type: ignore[no-untyped-def]
    db_session: Session,
    seeded_user: User,
) -> Iterator[tuple[TestClient, User]]:
    """FastAPI TestClient bound to ``db_session`` and logged in as ``seeded_user``."""
    app = create_app()

    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        resp = c.post(
            "/api/v1/auth/login",
            json={"email": seeded_user.email, "password": "hunter2pass"},
        )
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c, seeded_user
    app.dependency_overrides.clear()


@pytest.fixture
def web_client(
    db_engine,  # type: ignore[no-untyped-def]
    db_session: Session,
    seeded_user: User,
) -> Iterator[tuple[TestClient, User]]:
    """Browser-style client bound to ``db_session`` — *not* pre-authenticated and
    with no forced ``Authorization`` header, so it exercises the httpOnly-cookie
    session + CSRF path the dashboard actually uses.

    Pins the cookie policy to ``SameSite=Lax`` / not-Secure for the duration of
    the test: ``TestClient`` speaks plain HTTP, and a ``Secure`` cookie is never
    returned over HTTP — so without this the cookie round-trip would break
    whenever the ambient ``COOKIE_SECURE`` / ``COOKIE_SAMESITE`` env is set for a
    real deployment (e.g. the web preview, which uses ``None``/Secure)."""
    from app.core.config import get_settings

    settings = get_settings()
    prev = (settings.cookie_secure, settings.cookie_samesite)
    object.__setattr__(settings, "cookie_secure", False)
    object.__setattr__(settings, "cookie_samesite", "lax")

    app = create_app()

    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as c:
            yield c, seeded_user
    finally:
        app.dependency_overrides.clear()
        object.__setattr__(settings, "cookie_secure", prev[0])
        object.__setattr__(settings, "cookie_samesite", prev[1])

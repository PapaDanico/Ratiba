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

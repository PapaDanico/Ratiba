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
    url = _test_database_url()
    try:
        engine = create_engine(url, future=True)
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL not reachable at {url}: {exc!r}")
    Base.metadata.drop_all(engine)
    with engine.begin() as c:
        c.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
    Base.metadata.create_all(engine)
    # Install the append-only trigger production uses on audit_events.
    with engine.begin() as c:
        c.execute(
            text(
                "CREATE OR REPLACE FUNCTION audit_events_append_only() "
                "RETURNS trigger AS $$ BEGIN RAISE EXCEPTION "
                "'audit_events is append-only (operation: %)', TG_OP; END; "
                "$$ LANGUAGE plpgsql"
            )
        )
        c.execute(
            text(
                "CREATE TRIGGER audit_events_no_update BEFORE UPDATE ON audit_events "
                "FOR EACH ROW EXECUTE FUNCTION audit_events_append_only()"
            )
        )
        c.execute(
            text(
                "CREATE TRIGGER audit_events_no_delete BEFORE DELETE ON audit_events "
                "FOR EACH ROW EXECUTE FUNCTION audit_events_append_only()"
            )
        )
    yield engine
    Base.metadata.drop_all(engine)


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

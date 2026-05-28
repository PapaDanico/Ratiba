"""Self-serve demo workspace provisioning."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import DEMO_WORKSPACE_LIMITER
from app.main import create_app


@pytest.fixture(autouse=True)
def _reset_limiter() -> Iterator[None]:
    DEMO_WORKSPACE_LIMITER.reset()
    yield
    DEMO_WORKSPACE_LIMITER.reset()


@pytest.fixture
def anon_client(
    db_engine,  # type: ignore[no-untyped-def]
    db_session: Session,
) -> Iterator[TestClient]:
    """Unauthenticated client bound to the transactional test session."""
    app = create_app()

    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_create_workspace_then_login_and_use(anon_client: TestClient) -> None:
    resp = anon_client.post(
        "/api/v1/auth/demo-workspace",
        json={
            "full_name": "Test Evaluator",
            "email": "eval1@evaluator.example",
            "password": "supersecret1",
            "operator_name": "Savanna Air",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["operator_name"] == "Savanna Air"
    assert body["email"] == "eval1@evaluator.example"

    # The returned credentials log in.
    login = anon_client.post(
        "/api/v1/auth/login",
        json={"email": "eval1@evaluator.example", "password": "supersecret1"},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Seeded sandbox is ready: crew, fleet, and type ratings exist.
    crew = anon_client.get("/api/v1/crew", headers=headers).json()
    assert len(crew) == 4
    ratings = anon_client.get("/api/v1/training/type-ratings", headers=headers).json()
    assert len(ratings) == 4

    # And auto-generate runs cleanly against the seeded sandbox.
    today = date.today()
    auto = anon_client.post(
        "/api/v1/roster/auto-generate",
        headers=headers,
        json={
            "horizon_from": today.isoformat(),
            "horizon_to": (today + timedelta(days=7)).isoformat(),
        },
    )
    assert auto.status_code == 200, auto.text
    assert auto.json()["result"]["status"] in {"OPTIMAL", "FEASIBLE", "INFEASIBLE"}


def test_duplicate_email_conflicts(anon_client: TestClient) -> None:
    payload = {
        "full_name": "Dup User",
        "email": "dup@evaluator.example",
        "password": "supersecret1",
    }
    assert anon_client.post("/api/v1/auth/demo-workspace", json=payload).status_code == 201
    assert anon_client.post("/api/v1/auth/demo-workspace", json=payload).status_code == 409


def test_short_password_rejected(anon_client: TestClient) -> None:
    resp = anon_client.post(
        "/api/v1/auth/demo-workspace",
        json={"full_name": "Shorty", "email": "short@evaluator.example", "password": "abc"},
    )
    assert resp.status_code == 422


def test_rate_limited_after_burst(anon_client: TestClient) -> None:
    # Limiter allows 10/hour; the 11th from the same IP is blocked.
    last = None
    for i in range(11):
        last = anon_client.post(
            "/api/v1/auth/demo-workspace",
            json={
                "full_name": f"Burst {i}",
                "email": f"burst{i}@evaluator.example",
                "password": "supersecret1",
            },
        )
    assert last is not None
    assert last.status_code == 429

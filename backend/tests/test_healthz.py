"""Phase 0 acceptance — backend healthcheck returns 200."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_healthz_returns_ok(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_ready_when_db_up(client: TestClient) -> None:
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["status"] in {"ready", "degraded"}
    assert response.json()["checks"]["postgres"] == "ok"


def test_readyz_503_when_db_unreachable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Force the DB probe to fail; readiness must report 503 so the platform
    # health check pulls the instance out of rotation.
    import app.main as main

    def _boom() -> object:
        raise RuntimeError("db down")

    monkeypatch.setattr(main.engine, "connect", _boom)
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert "unreachable" in response.json()["checks"]["postgres"]


def test_version_reports_current_phase(client: TestClient) -> None:
    response = client.get("/version")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "ratiba"
    assert body["phase"] == "6"
    assert "version" in body


def test_openapi_published_under_docs(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Ratiba"

"""Phase 0 acceptance — backend healthcheck returns 200."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz_returns_ok(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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

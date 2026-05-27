"""Phase 0 acceptance — every API v1 route group is wired into the app."""

from __future__ import annotations

from fastapi.testclient import TestClient

REQUIRED_PREFIXES = [
    "/api/v1/auth",
    "/api/v1/crew",
    "/api/v1/roster",
    "/api/v1/ftl",
    "/api/v1/training",
    "/api/v1/leave",
    "/api/v1/audit",
]


def test_every_v1_router_appears_in_openapi(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"].keys()
    for prefix in REQUIRED_PREFIXES:
        assert any(p.startswith(prefix) for p in paths), f"missing prefix: {prefix}"

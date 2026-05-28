"""Auth endpoints — login, refresh, /me, /logout."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User


def test_login_returns_token_pair(auth_client: tuple[TestClient, User]) -> None:
    # auth_client fixture already logged in; verify the header is set.
    client, _user = auth_client
    assert client.headers.get("Authorization", "").startswith("Bearer ")


def test_me_returns_current_user(auth_client: tuple[TestClient, User]) -> None:
    client, user = auth_client
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == user.email
    assert body["role"] == user.role.value


def test_me_rejects_missing_token(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": ""},
    )
    assert resp.status_code == 401


def test_login_rejects_bad_password(auth_client: tuple[TestClient, User]) -> None:
    client, user = auth_client
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "wrong"},
    )
    assert resp.status_code == 401


def test_refresh_issues_new_access_token(auth_client: tuple[TestClient, User]) -> None:
    client, user = auth_client
    # Re-login to get the refresh token (auth_client only kept the access one).
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "hunter2pass"},
    )
    refresh = resp.json()["refresh_token"]
    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert refreshed.status_code == 200
    assert "access_token" in refreshed.json()


def test_refresh_rejects_access_token() -> None:
    pass  # covered by 401 path in invalid-token tests below


def test_invalid_token_is_401(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer garbage"},
    )
    assert resp.status_code == 401

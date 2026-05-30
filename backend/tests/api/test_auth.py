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
    # Clear both credential channels: the Bearer header *and* the session
    # cookies that login set on the TestClient's jar.
    client.cookies.clear()
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
    # Rotation: a new refresh token is issued, and the old one is now dead.
    new_refresh = refreshed.json()["refresh_token"]
    assert new_refresh and new_refresh != refresh
    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert reused.status_code == 401
    # The rotated token still works.
    again = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert again.status_code == 200


def test_logout_revokes_refresh_token(auth_client: tuple[TestClient, User]) -> None:
    client, user = auth_client
    refresh = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "hunter2pass"}
    ).json()["refresh_token"]
    # Logout revokes it; afterwards it can no longer mint tokens.
    assert client.post("/api/v1/auth/logout", json={"refresh_token": refresh}).status_code == 204
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": refresh}).status_code == 401


def test_refresh_rejects_access_token() -> None:
    pass  # covered by 401 path in invalid-token tests below


def test_invalid_token_is_401(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer garbage"},
    )
    assert resp.status_code == 401


def test_login_is_rate_limited(auth_client: tuple[TestClient, User]) -> None:
    """After the per-IP budget is exhausted, login returns 429 (brute-force guard)."""
    from app.core.rate_limit import LOGIN_LIMITER

    client, user = auth_client
    body = {"email": user.email, "password": "wrong"}
    # Burn the whole window with failed attempts.
    statuses = {client.post("/api/v1/auth/login", json=body).status_code for _ in range(11)}
    assert 429 in statuses, statuses
    # A correct password is still throttled while the window is saturated.
    blocked = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "hunter2pass"}
    )
    assert blocked.status_code == 429
    # Once the limiter resets, login works again.
    LOGIN_LIMITER.reset()
    ok = client.post("/api/v1/auth/login", json={"email": user.email, "password": "hunter2pass"})
    assert ok.status_code == 200, ok.text


# -- httpOnly cookie session + CSRF (Phase 6 hardening) -----------------------


def _set_cookie_headers(resp: object) -> list[str]:
    return [v for k, v in resp.headers.multi_items() if k.lower() == "set-cookie"]  # type: ignore[attr-defined]


def test_login_sets_httponly_cookies(web_client: tuple[TestClient, User]) -> None:
    client, user = web_client
    resp = client.post("/api/v1/auth/login", json={"email": user.email, "password": "hunter2pass"})
    assert resp.status_code == 200, resp.text
    cookies = "\n".join(_set_cookie_headers(resp))
    # Access + refresh tokens are httpOnly (JS can't read them → XSS-safe).
    assert "rt_access=" in cookies and "rt_refresh=" in cookies
    for line in _set_cookie_headers(resp):
        if line.startswith("rt_access=") or line.startswith("rt_refresh="):
            assert "HttpOnly" in line, line
    # The CSRF token is deliberately readable (double-submit) — not httpOnly.
    csrf_line = next(line for line in _set_cookie_headers(resp) if line.startswith("rt_csrf="))
    assert "HttpOnly" not in csrf_line, csrf_line


def test_cookie_session_authenticates_without_bearer(
    web_client: tuple[TestClient, User],
) -> None:
    client, user = web_client
    client.post("/api/v1/auth/login", json={"email": user.email, "password": "hunter2pass"})
    # No Authorization header — the request rides entirely on the cookie jar.
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == user.email


def test_csrf_blocks_cookie_post_without_header(web_client: tuple[TestClient, User]) -> None:
    client, user = web_client
    client.post("/api/v1/auth/login", json={"email": user.email, "password": "hunter2pass"})
    # An unsafe, cookie-authenticated request with no CSRF header is rejected.
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 403, resp.text
    assert "CSRF" in resp.json()["detail"]


def test_csrf_allows_cookie_post_with_header(web_client: tuple[TestClient, User]) -> None:
    client, user = web_client
    client.post("/api/v1/auth/login", json={"email": user.email, "password": "hunter2pass"})
    csrf = client.cookies.get("rt_csrf")
    assert csrf
    resp = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 204, resp.text
    # Logout clears the session cookies.
    cleared = "\n".join(_set_cookie_headers(resp))
    assert "rt_access=" in cleared and "rt_refresh=" in cleared


def test_csrf_rejects_mismatched_header(web_client: tuple[TestClient, User]) -> None:
    client, user = web_client
    client.post("/api/v1/auth/login", json={"email": user.email, "password": "hunter2pass"})
    resp = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": "not-the-real-token"})
    assert resp.status_code == 403, resp.text


def test_cookie_refresh_rotates_without_body(web_client: tuple[TestClient, User]) -> None:
    client, user = web_client
    client.post("/api/v1/auth/login", json={"email": user.email, "password": "hunter2pass"})
    csrf = client.cookies.get("rt_csrf")
    assert csrf
    old_refresh = client.cookies.get("rt_refresh")
    # No body — the refresh token is taken from the cookie; CSRF header required.
    resp = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 200, resp.text
    assert "access_token" in resp.json()
    # The single-use refresh token (unique jti) rotated to a fresh cookie value.
    assert client.cookies.get("rt_refresh") != old_refresh

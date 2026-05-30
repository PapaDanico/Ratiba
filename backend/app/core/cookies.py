"""httpOnly auth cookies + CSRF double-submit token.

Browser sessions (the crewing-officer dashboard and the ``/crew/me`` pilot
web view) carry their JWTs in **httpOnly** cookies rather than ``localStorage``
so that a cross-site-scripting bug can't exfiltrate a token. JavaScript can't
read an httpOnly cookie, so the usual CSRF exposure of cookie auth is closed
with a **double-submit token**: a *readable* ``rt_csrf`` cookie whose value the
frontend echoes in an ``X-CSRF-Token`` header on every unsafe request. The
middleware in :mod:`app.main` compares the two.

The bot and any direct API client keep using ``Authorization: Bearer`` — an
explicit header is not an ambient credential, so it is exempt from CSRF. These
helpers only ever *add* cookies; the token pair is still returned in the
response body for those non-browser callers.
"""

from __future__ import annotations

import secrets

from fastapi import Request, Response

from app.core.config import get_settings

ACCESS_COOKIE = "rt_access"
REFRESH_COOKIE = "rt_refresh"
PILOT_COOKIE = "rt_pilot"
CSRF_COOKIE = "rt_csrf"
CSRF_HEADER = "x-csrf-token"

#: Cookies that mark a request as carrying an *ambient* credential. Their
#: presence on an unsafe request is what arms the CSRF check.
AUTH_COOKIES = (ACCESS_COOKIE, REFRESH_COOKIE, PILOT_COOKIE)


def _seconds(*, minutes: int = 0, days: int = 0) -> int:
    return minutes * 60 + days * 86_400


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _set(response: Response, key: str, value: str, *, max_age: int, http_only: bool) -> None:
    response.set_cookie(
        key=key,
        value=value,
        max_age=max_age,
        httponly=http_only,
        secure=get_settings().cookie_secure,
        samesite="lax",
        path="/",
    )


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> str:
    """Set the officer/admin session cookies and return the CSRF token issued.

    The CSRF cookie outlives the short access cookie (it matches the refresh
    lifetime) so the frontend can still authorise the ``/auth/refresh`` POST
    once the access token has lapsed.
    """
    settings = get_settings()
    access_age = _seconds(minutes=settings.jwt_access_token_expire_minutes)
    refresh_age = _seconds(days=settings.jwt_refresh_token_expire_days)
    csrf = new_csrf_token()
    _set(response, ACCESS_COOKIE, access_token, max_age=access_age, http_only=True)
    _set(response, REFRESH_COOKIE, refresh_token, max_age=refresh_age, http_only=True)
    _set(response, CSRF_COOKIE, csrf, max_age=refresh_age, http_only=False)
    return csrf


def set_pilot_cookie(response: Response, pilot_token: str, *, days: int = 30) -> str:
    """Set the pilot ``/crew/me`` session cookie + CSRF token; return the CSRF."""
    age = _seconds(days=days)
    csrf = new_csrf_token()
    _set(response, PILOT_COOKIE, pilot_token, max_age=age, http_only=True)
    _set(response, CSRF_COOKIE, csrf, max_age=age, http_only=False)
    return csrf


def _clear(response: Response, *keys: str) -> None:
    for key in keys:
        response.delete_cookie(key, path="/")


def clear_auth_cookies(response: Response) -> None:
    _clear(response, ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE)


def clear_pilot_cookie(response: Response) -> None:
    _clear(response, PILOT_COOKIE, CSRF_COOKIE)


def bearer_or_cookie(request: Request, cookie_name: str) -> str | None:
    """Extract a JWT from the ``Authorization`` header, falling back to a cookie.

    An explicit ``Bearer`` header always wins (and is used as-is even if
    invalid, so a bad explicit token still 401s rather than silently falling
    back to a cookie session).
    """
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return request.cookies.get(cookie_name)

"""JWT and password hashing primitives.

Uses the ``bcrypt`` library directly rather than ``passlib`` — passlib
1.7.4 is incompatible with bcrypt >= 4.1 (it feeds bcrypt a >72-byte
self-calibration value that modern bcrypt hard-rejects).
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import jwt

from app.core.config import get_settings

# bcrypt only considers the first 72 bytes of a password and raises on
# anything longer; truncate to keep hashing + verification consistent.
_BCRYPT_MAX_BYTES = 72


def _prepare(plain: str) -> bytes:
    return plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt."""
    result: bytes = bcrypt.hashpw(_prepare(plain), bcrypt.gensalt())
    return result.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        result: bool = bcrypt.checkpw(_prepare(plain), hashed.encode("utf-8"))
        return result
    except ValueError:
        return False


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    """Issue a short-lived JWT access token."""
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    to_encode: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    if extra:
        to_encode.update(extra)
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    """Issue a long-lived JWT refresh token."""
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.jwt_refresh_token_expire_days)
    to_encode: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "refresh",
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_pilot_token(crew_id: str, operator_id: str, days: int = 30) -> str:
    """Issue a long-lived pilot JWT used by the bot and the /crew/me web view.

    ``sub`` carries the ``crew:<uuid>`` prefix so it can't collide with
    user tokens (whose ``sub`` is a bare uuid).
    """
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + timedelta(days=days)
    payload: dict[str, Any] = {
        "sub": f"crew:{crew_id}",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "pilot",
        "operator_id": operator_id,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_ical_token(crew_id: str, days: int = 730) -> str:
    """Long-lived capability token embedded in a crew member's calendar-feed URL.

    Calendar clients can't send auth headers, so the token rides in the query
    string. Scoped to a single crew's read-only roster feed; ``sub`` carries
    the ``ical:<uuid>`` prefix so it can't be replayed as any other token type.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + timedelta(days=days)
    payload: dict[str, Any] = {
        "sub": f"ical:{crew_id}",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "ical",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises ``jose.JWTError`` on failure."""
    settings = get_settings()
    payload: dict[str, Any] = jwt.decode(
        token, settings.secret_key, algorithms=[settings.jwt_algorithm]
    )
    return payload

"""JWT and password hashing primitives. Phase 3 wires these into endpoints."""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bool(_pwd_context.verify(plain, hashed))


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


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises ``jose.JWTError`` on failure."""
    settings = get_settings()
    payload: dict[str, Any] = jwt.decode(
        token, settings.secret_key, algorithms=[settings.jwt_algorithm]
    )
    return payload

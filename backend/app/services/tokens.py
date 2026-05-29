"""Refresh-token revocation: a small allow-once registry keyed by ``jti``.

Used for refresh-token rotation (each refresh revokes the token that minted it)
and logout (revokes the presented refresh token). Access tokens stay stateless
and short-lived; revoking the refresh token stops new access tokens being
minted, and the current access token lapses at its own short expiry.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RevokedToken


def is_revoked(session: Session, jti: str) -> bool:
    return session.scalar(select(RevokedToken.jti).where(RevokedToken.jti == jti)) is not None


def revoke(session: Session, jti: str, expires_at: datetime) -> None:
    """Record ``jti`` as revoked. Idempotent — re-revoking is a no-op."""
    if is_revoked(session, jti):
        return
    session.add(RevokedToken(jti=jti, expires_at=expires_at))
    session.flush()

"""Revoked refresh-token registry.

Refresh tokens carry a unique ``jti``. When one is rotated (on /refresh) or a
user logs out, its ``jti`` is recorded here; /refresh rejects any token whose
``jti`` is present. ``expires_at`` mirrors the token's own expiry so the table
can be pruned of entries that are already dead.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

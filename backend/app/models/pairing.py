"""Pilot pairing token — short-lived single-use code for bot/web crew linking."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import OperatorScopedMixin, TimestampMixin, UUIDMixin


class PairingToken(UUIDMixin, TimestampMixin, OperatorScopedMixin, Base):
    __tablename__ = "pairing_tokens"

    crew_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("crew.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    redeemed_telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

"""Operator (tenant) model."""

from __future__ import annotations

import enum
from typing import Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class OperatorTier(enum.StrEnum):
    ENTRY = "ENTRY"
    STANDARD = "STANDARD"
    PLUS = "PLUS"


class Operator(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "operators"

    aoc_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base: Mapped[str] = mapped_column(String(8), nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Africa/Nairobi", server_default="Africa/Nairobi"
    )
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    tier: Mapped[OperatorTier] = mapped_column(
        SAEnum(OperatorTier, name="operator_tier"),
        nullable=False,
        default=OperatorTier.ENTRY,
    )
    default_soft_weights: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

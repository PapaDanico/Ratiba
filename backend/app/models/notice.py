"""Crew notices — operational comms, fleet notices, safety, morale/social."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import OperatorScopedMixin, TimestampMixin, UUIDMixin


class NoticeCategory(enum.StrEnum):
    OPERATIONAL = "OPERATIONAL"
    FLEET = "FLEET"
    SAFETY = "SAFETY"
    SOCIAL = "SOCIAL"  # morale posts, memes, social comms


class NoticeSeverity(enum.StrEnum):
    INFO = "INFO"
    IMPORTANT = "IMPORTANT"
    CRITICAL = "CRITICAL"


class Notice(UUIDMixin, TimestampMixin, OperatorScopedMixin, Base):
    __tablename__ = "notices"

    category: Mapped[NoticeCategory] = mapped_column(
        SAEnum(NoticeCategory, name="notice_category"), nullable=False
    )
    severity: Mapped[NoticeSeverity] = mapped_column(
        SAEnum(NoticeSeverity, name="notice_severity"),
        nullable=False,
        default=NoticeSeverity.INFO,
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    requires_ack: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NoticeAcknowledgement(Base):
    __tablename__ = "notice_acknowledgements"
    __table_args__ = (UniqueConstraint("notice_id", "crew_id", name="uq_notice_ack_notice_crew"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    notice_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("notices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    crew_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("crew.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

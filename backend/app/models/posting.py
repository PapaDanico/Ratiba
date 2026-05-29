"""Outstation / detachment postings (e.g. long-term ACMI wet-lease).

A posting deploys a team of crew (pilots + cabin + engineer) away from base for
a bounded period — typically a 3–4 week rotation. Duties flown during a posting
are away-from-base for FTL purposes; that per-duty wiring is a later phase.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import OperatorScopedMixin, TimestampMixin, UUIDMixin

# A rotation longer than this needs relief crew rotated in. 4 weeks.
MAX_POSTING_DAYS = 28


class PostingType(enum.StrEnum):
    ACMI_WET_LEASE = "ACMI_WET_LEASE"
    DETACHMENT = "DETACHMENT"
    TRAINING = "TRAINING"


class Posting(UUIDMixin, TimestampMixin, OperatorScopedMixin, Base):
    __tablename__ = "postings"

    location_icao: Mapped[str] = mapped_column(String(8), nullable=False)
    country: Mapped[str] = mapped_column(String(64), nullable=False)
    base_tz: Mapped[str] = mapped_column(String(64), nullable=False, default="Africa/Nairobi")
    type: Mapped[PostingType] = mapped_column(SAEnum(PostingType, name="posting_type"))
    lessee_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PostingAssignment(UUIDMixin, TimestampMixin, OperatorScopedMixin, Base):
    __tablename__ = "posting_assignments"
    __table_args__ = (UniqueConstraint("posting_id", "crew_id", name="uq_posting_assignment"),)

    posting_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("postings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    crew_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("crew.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

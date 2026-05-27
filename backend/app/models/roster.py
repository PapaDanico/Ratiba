"""Sector (flight leg) and sector assignment models."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import OperatorScopedMixin, TimestampMixin, UUIDMixin


class SectorStatus(enum.StrEnum):
    PLANNED = "PLANNED"
    PUBLISHED = "PUBLISHED"
    OPERATING = "OPERATING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Sector(UUIDMixin, TimestampMixin, OperatorScopedMixin, Base):
    __tablename__ = "sectors"

    flight_no: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    origin: Mapped[str] = mapped_column(String(8), nullable=False)
    destination: Mapped[str] = mapped_column(String(8), nullable=False)
    std: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sta: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    atd: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ata: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    aircraft_reg: Mapped[str] = mapped_column(String(16), nullable=False)
    aircraft_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[SectorStatus] = mapped_column(
        SAEnum(SectorStatus, name="sector_status"),
        nullable=False,
        default=SectorStatus.PLANNED,
    )


class SectorAssignment(UUIDMixin, TimestampMixin, OperatorScopedMixin, Base):
    __tablename__ = "sector_assignments"
    __table_args__ = (
        UniqueConstraint("sector_id", "crew_id", name="uq_sector_assignment_sector_crew"),
    )

    sector_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sectors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    crew_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("crew.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    role_on_sector: Mapped[str] = mapped_column(String(16), nullable=False)

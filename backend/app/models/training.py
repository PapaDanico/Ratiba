"""Crew training: type ratings and recurrent currencies."""

from __future__ import annotations

import enum
import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import OperatorScopedMixin, TimestampMixin, UUIDMixin


class CurrencyType(enum.StrEnum):
    LANDINGS_90D = "LANDINGS_90D"
    ROUTE_FAM = "ROUTE_FAM"
    MEL_COMP = "MEL_COMP"
    LINE_CHECK = "LINE_CHECK"
    OPC = "OPC"
    LPC = "LPC"
    EMERG_PROC = "EMERG_PROC"
    FIRST_AID = "FIRST_AID"
    DG = "DG"
    CRM = "CRM"
    SEC_TRAINING = "SEC_TRAINING"


class CrewTypeRating(UUIDMixin, TimestampMixin, OperatorScopedMixin, Base):
    __tablename__ = "crew_type_ratings"

    crew_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("crew.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    aircraft_type: Mapped[str] = mapped_column(String(32), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    evidence_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)


class CrewCurrency(UUIDMixin, TimestampMixin, OperatorScopedMixin, Base):
    __tablename__ = "crew_currencies"

    crew_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("crew.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    currency_type: Mapped[CurrencyType] = mapped_column(
        SAEnum(CurrencyType, name="currency_type"), nullable=False
    )
    last_completed_date: Mapped[date] = mapped_column(Date, nullable=False)
    expires_date: Mapped[date] = mapped_column(Date, nullable=False)
    evidence_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)

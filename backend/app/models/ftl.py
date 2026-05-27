"""Flight Duty Period and FTL rule models."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import ARRAY, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import OperatorScopedMixin, TimestampMixin, UUIDMixin


class FdpType(enum.StrEnum):
    FDP = "FDP"
    STANDBY = "STANDBY"
    POSITIONING = "POSITIONING"
    TRAINING = "TRAINING"
    OFF = "OFF"
    LEAVE = "LEAVE"
    SICK = "SICK"


class LegalityState(enum.StrEnum):
    LEGAL = "LEGAL"
    AT_LIMIT = "AT_LIMIT"
    REQUIRES_FRMS_DEROGATION = "REQUIRES_FRMS_DEROGATION"
    ILLEGAL = "ILLEGAL"


class RuleSource(enum.StrEnum):
    MANUAL_REVIEW = "MANUAL_REVIEW"
    LLM_PARSED = "LLM_PARSED"
    OM_A_REVISION_X = "OM_A_REVISION_X"


class FlightDutyPeriod(UUIDMixin, TimestampMixin, OperatorScopedMixin, Base):
    __tablename__ = "flight_duty_periods"

    crew_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("crew.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    report_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    off_duty_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sectors_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    flight_hours: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    duty_hours: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    type: Mapped[FdpType] = mapped_column(
        SAEnum(FdpType, name="fdp_type"), nullable=False, default=FdpType.FDP
    )
    legality_state: Mapped[LegalityState] = mapped_column(
        SAEnum(LegalityState, name="legality_state"),
        nullable=False,
        default=LegalityState.LEGAL,
    )
    ftl_rules_applied: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )


class FtlRule(UUIDMixin, TimestampMixin, OperatorScopedMixin, Base):
    __tablename__ = "ftl_rules"

    rule_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(2048), nullable=False)
    regulation_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    calculation_logic_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    applies_to: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    source: Mapped[RuleSource] = mapped_column(
        SAEnum(RuleSource, name="rule_source"),
        nullable=False,
        default=RuleSource.MANUAL_REVIEW,
    )

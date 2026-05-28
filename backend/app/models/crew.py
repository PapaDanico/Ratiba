"""Crew member model."""

from __future__ import annotations

import enum
from datetime import date
from typing import Any

from sqlalchemy import ARRAY, BigInteger, Boolean, Date, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import OperatorScopedMixin, TimestampMixin, UUIDMixin


class CrewRole(enum.StrEnum):
    CAPT = "CAPT"
    FO = "FO"
    SO = "SO"


class ContractType(enum.StrEnum):
    FULL_TIME = "FULL_TIME"
    CONTRACT = "CONTRACT"
    FREELANCE = "FREELANCE"


class Crew(UUIDMixin, TimestampMixin, OperatorScopedMixin, Base):
    __tablename__ = "crew"
    __table_args__ = (
        UniqueConstraint("operator_id", "employee_no", name="uq_crew_operator_employee_no"),
    )

    employee_no: Mapped[str] = mapped_column(String(32), nullable=False)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[CrewRole] = mapped_column(SAEnum(CrewRole, name="crew_role"), nullable=False)
    date_of_hire: Mapped[date] = mapped_column(Date, nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    base_station: Mapped[str] = mapped_column(String(8), nullable=False)
    contract_type: Mapped[ContractType] = mapped_column(
        SAEnum(ContractType, name="contract_type"), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    languages: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    faith_observance_flags: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)

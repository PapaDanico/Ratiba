"""Per-operator aircraft fleet registry."""

from __future__ import annotations

from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import OperatorScopedMixin, TimestampMixin, UUIDMixin


class Aircraft(UUIDMixin, TimestampMixin, OperatorScopedMixin, Base):
    __tablename__ = "aircraft"
    __table_args__ = (
        UniqueConstraint("operator_id", "registration", name="uq_aircraft_operator_registration"),
    )

    registration: Mapped[str] = mapped_column(String(16), nullable=False)
    # ICAO type designator from app.services.aircraft_types (e.g. DH8D, AT76).
    aircraft_type: Mapped[str] = mapped_column(String(32), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

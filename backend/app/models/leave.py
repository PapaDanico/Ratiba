"""Leave request model."""

from __future__ import annotations

import enum
import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import OperatorScopedMixin, TimestampMixin, UUIDMixin


class LeaveType(enum.StrEnum):
    ANNUAL = "ANNUAL"
    SICK = "SICK"
    COMPASSIONATE = "COMPASSIONATE"
    FAITH = "FAITH"
    OTHER = "OTHER"


class LeaveStatus(enum.StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class LeaveRequest(UUIDMixin, TimestampMixin, OperatorScopedMixin, Base):
    __tablename__ = "leave_requests"

    crew_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("crew.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[LeaveType] = mapped_column(SAEnum(LeaveType, name="leave_type"), nullable=False)
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[LeaveStatus] = mapped_column(
        SAEnum(LeaveStatus, name="leave_status"),
        nullable=False,
        default=LeaveStatus.PENDING,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    approver_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

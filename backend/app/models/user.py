"""Dashboard-user model (Crewing Officers, Chief Pilot, etc.).

Pilots themselves are represented by :class:`app.models.crew.Crew`. A pilot
may also have a ``User`` row if they need dashboard access.
"""

from __future__ import annotations

import enum

from sqlalchemy import Boolean, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import OperatorScopedMixin, TimestampMixin, UUIDMixin


class UserRole(enum.StrEnum):
    CREWING_OFFICER = "CREWING_OFFICER"
    CHIEF_PILOT = "CHIEF_PILOT"
    ADMIN = "ADMIN"
    PILOT = "PILOT"


class User(UUIDMixin, TimestampMixin, OperatorScopedMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, name="user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

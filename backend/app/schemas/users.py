"""Team / user-management schemas (operator-admin surface)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole

# Staff roles that can hold a dashboard login. PILOT is excluded — crew
# authenticate via their own scoped pilot token, not a staff user account.
ASSIGNABLE_ROLES: frozenset[UserRole] = frozenset(
    {UserRole.CREWING_OFFICER, UserRole.CHIEF_PILOT, UserRole.ADMIN}
)


def _check_assignable(role: UserRole) -> UserRole:
    if role not in ASSIGNABLE_ROLES:
        allowed = ", ".join(sorted(r.value for r in ASSIGNABLE_ROLES))
        raise ValueError(f"role must be one of: {allowed}")
    return role


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=128)
    role: UserRole
    password: str = Field(min_length=8, max_length=128)

    @field_validator("role")
    @classmethod
    def _role_assignable(cls, v: UserRole) -> UserRole:
        return _check_assignable(v)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=128)
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("role")
    @classmethod
    def _role_assignable(cls, v: UserRole | None) -> UserRole | None:
        return None if v is None else _check_assignable(v)
